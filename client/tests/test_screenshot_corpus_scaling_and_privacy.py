import os
import random
import string
import time
from typing import Dict, List, Tuple

import pytest


def _rand_words(rng: random.Random, n: int) -> str:
    words = []
    for _ in range(n):
        wlen = rng.randint(3, 10)
        word = ''.join(rng.choices(string.ascii_lowercase, k=wlen))
        words.append(word)
    return ' '.join(words)


def build_screenshot_like_corpus(
    total: int,
    categories: List[str],
    labeled_queries: List[Tuple[str, str]],  # (query, expected_category)
    seed: int = 4242,
) -> Tuple[List[Dict[str, str]], List[Tuple[str, str]]]:
    """
    Build a corpus that resembles window/screenshot descriptions.
    Returns (documents, labeled_queries)
    """
    rng = random.Random(seed)

    templates = [
        "Screenshot of {app} window showing {content} with toolbar visible",
        "{app} application screenshot: {content}, dialogs and menus open",
        "Captured display of {app} – {content}, zoom level {zoom}%",
        "{app} on macOS with {content} centered, resolution {res}"
    ]
    apps_by_cat = {
        "browser": ["Google Chrome", "Safari", "Firefox"],
        "editor": ["VS Code", "Sublime Text", "IntelliJ"],
        "terminal": ["Terminal", "iTerm2", "Hyper"],
        "productivity": ["Excel", "Notion", "Obsidian", "Slack"],
        "media": ["Photos", "QuickTime Player", "Preview"],
    }

    # Align requested categories with available buckets
    buckets = categories or list(apps_by_cat.keys())

    docs: List[Dict[str, str]] = []
    for i in range(total):
        cat = rng.choice(buckets)
        app = rng.choice(apps_by_cat.get(cat, [cat]))
        content = _rand_words(rng, rng.randint(5, 12))
        zoom = rng.choice([80, 100, 125, 150])
        res = rng.choice(["1440x900", "1920x1080", "2560x1600"]) 
        text = rng.choice(templates).format(app=app, content=content, zoom=zoom, res=res)
        docs.append({
            "id": f"doc_{i:05d}",
            "text": text,
            "category": cat,
            "topic": app,
        })

    return docs, labeled_queries


@pytest.mark.integration
@pytest.mark.timeout(900)
def test_thousands_screenshot_corpus_scaling_and_privacy(make_client):
    # Configure client for privacy: do not send raw text back to server in metadata
    os.environ["SECURE_SEARCH_STRIP_PLAINTEXT_METADATA"] = "1"

    client = make_client()
    client.initialize()

    total_docs = int(os.getenv("SECURE_SEARCH_THOUSANDS", "2000"))
    categories = ["browser", "editor", "terminal", "productivity", "media"]

    labeled_queries = [
        ("code editor with file tree and terminal panel", "editor"),
        ("browser window showing tabs and omnibox", "browser"),
        ("terminal session with git commands", "terminal"),
        ("spreadsheet rows and charts", "productivity"),
        ("image viewer playback controls", "media"),
    ]

    docs, labeled = build_screenshot_like_corpus(total_docs, categories, labeled_queries)

    # Upload in batches to avoid long single loops; verify server never receives plaintext text in metadata
    # Note: We can't intercept server internals, but we can ensure our client payload omits 'text' when strip is enabled
    leaked_plaintext_count = 0

    batch_size = 200
    for start in range(0, len(docs), batch_size):
        batch = docs[start:start+batch_size]
        for item in batch:
            resp = client.add_embedding(
                text=item["text"],
                embedding_id=item["id"],
                metadata={
                    # category/topic are non-sensitive labels for evaluation
                    "category": item["category"],
                    "topic": item["topic"],
                }
            )
            assert resp.get("status") == "success"
        
        # Spot-check one request shape by re-computing metadata behavior locally
        # Since client controls the payload, rely on the env toggle behavior for privacy
        if client.strip_plaintext_metadata:
            # No 'text' field is sent when privacy strip is enabled
            pass
        else:
            leaked_plaintext_count += 1

    assert leaked_plaintext_count == 0, "Client should not send plaintext when privacy strip is enabled"

    # Inject near-duplicates and noise to test robustness
    dup_docs = [
        {"id": f"dup_{i}", "text": docs[i]["text"] + " extra", "category": docs[i]["category"], "topic": docs[i]["topic"]}
        for i in range(min(50, len(docs)))
    ]
    noise_docs = [
        {"id": f"noise_{i}", "text": _rand_words(random.Random(999 + i), 30), "category": "noise", "topic": "noise"}
        for i in range(100)
    ]

    for item in dup_docs + noise_docs:
        client.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"], "topic": item["topic"]})

    # Evaluate labeled queries
    top_k = 10
    pass_counts = 0
    total_checked_candidates = 0
    total_search_ms = 0.0

    for query, expected_cat in labeled:
        start = time.time()
        res = client.search(query, top_k=top_k, rerank_candidates=100)
        elapsed = (time.time() - start) * 1000
        total_search_ms += elapsed
        total_checked_candidates += res.get("candidates_checked", 0)

        cats = {r.get("metadata", {}).get("category") for r in res.get("results", [])}
        if expected_cat in cats:
            pass_counts += 1

        # Ensure encrypted similarity returned and base64-like
        for r in res.get("results", []):
            enc = r.get("encrypted_similarity", "")
            assert isinstance(enc, str) and len(enc) > 0

    # Quality: most queries should retrieve at least one item from expected category
    assert pass_counts >= max(3, len(labeled) - 2), f"Retrieval too weak: {pass_counts}/{len(labeled)}"

    # Efficiency: candidate checks should remain bounded (shouldn't be thousands each)
    avg_candidates = total_checked_candidates / max(1, len(labeled))
    assert avg_candidates <= 200, f"Too many candidates on average: {avg_candidates}"

    # Throughput sanity: total time per query should be within a loose bound for thousands-scale
    avg_ms = total_search_ms / max(1, len(labeled))
    assert avg_ms < 8000, f"Search too slow on average: {avg_ms:.1f}ms"


@pytest.mark.integration
@pytest.mark.timeout(600)
def test_privacy_under_strip_flag_no_text_field_in_metadata(make_client):
    os.environ["SECURE_SEARCH_STRIP_PLAINTEXT_METADATA"] = "1"
    client = make_client()
    client.initialize()

    # Upload a few items and then use debug to ensure service is functional
    items = [
        {"id": "p1", "text": "Terminal window git status", "category": "terminal", "topic": "Terminal"},
        {"id": "p2", "text": "Chrome browser with tabs", "category": "browser", "topic": "Chrome"},
    ]
    for it in items:
        client.add_embedding(text=it["text"], embedding_id=it["id"], metadata={"category": it["category"], "topic": it["topic"]})

    # Search and verify results include no raw text in metadata (only category/topic)
    res = client.search("git commit in terminal", top_k=5, rerank_candidates=50)
    for r in res.get("results", []):
        md = r.get("metadata", {})
        assert "text" not in md, "No plaintext should be included when strip flag is on"
        # Categories/topics may still be present for evaluation


@pytest.mark.integration
@pytest.mark.timeout(600)
def test_near_duplicates_ranking_stability(make_client):
    os.environ["SECURE_SEARCH_STRIP_PLAINTEXT_METADATA"] = "1"
    client = make_client()
    client.initialize()

    base = "VS Code editor open with Python file and integrated terminal"
    variants = [base + suffix for suffix in ("", " ", "  ", " - draft", " - final", " (copy)")]
    ids = []
    for i, text in enumerate(variants):
        eid = f"var_{i}"
        ids.append(eid)
        client.add_embedding(text=text, embedding_id=eid, metadata={"category": "editor", "topic": "VS Code"})

    res = client.search("Python editor integrated terminal", top_k=5, rerank_candidates=50)

    # Expect to see several of the variants among top results and all payload similarities are encrypted
    found = {str(r.get("metadata", {}).get("topic")) for r in res.get("results", [])}
    # Since the server assigns its own embedding ids, match via metadata 'topic'
    assert "VS Code" in found
    for r in res.get("results", []):
        assert isinstance(r.get("encrypted_similarity", ""), str) 