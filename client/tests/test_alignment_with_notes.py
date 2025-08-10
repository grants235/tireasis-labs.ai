import base64
import re
from typing import Dict

import pytest


@pytest.mark.integration
@pytest.mark.timeout(60)
def test_initialize_alignment(make_client):
    client = make_client()
    resp = client.initialize()

    # Alignment checks against notes/diagram
    assert "client_id" in resp and resp["client_id"], "Server must assign client_id"
    assert "random_planes" in resp and resp["random_planes"], "Server should provide LSH random planes"
    assert "lsh_config" in resp, "Server returns LSH config"

    # LSH config properties
    lsh = resp["lsh_config"]
    assert lsh.get("num_tables") > 0
    assert lsh.get("hash_size") >= 8


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_add_embedding_alignment(make_client, dataset_small):
    client = make_client()
    client.initialize()

    item = dataset_small[0]
    add_resp = client.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"]})

    # Server acknowledges success and returns index position
    assert add_resp.get("status") == "success"
    assert "embedding_id" in add_resp


@pytest.mark.integration
@pytest.mark.timeout(180)
def test_search_returns_encrypted_similarity_and_metadata(make_client, dataset_small):
    client = make_client()
    client.initialize()

    # Upload a small set
    for item in dataset_small:
        client.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"], "topic": item["topic"]})

    # Perform a search
    q = "artificial intelligence and machine learning methods"
    res = client.search(q, top_k=5, rerank_candidates=50)

    # Should return encrypted similarity that is base64 text, not plaintext numbers
    assert isinstance(res, dict) and "results" in res
    for r in res["results"]:
        enc = r.get("encrypted_similarity", "")
        assert isinstance(enc, str) and len(enc) > 0
        # validate base64 encoding
        base64.b64decode(enc)
        # ensure server didn’t decrypt (we cannot assert decryption here, but we assert format)

    # Metadata should be present for ranking/debug
    assert all("metadata" in r for r in res["results"])  


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_lsh_candidate_efficiency(make_client, dataset_medium):
    client = make_client()
    client.initialize()

    # Upload medium set
    for item in dataset_medium:
        client.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"], "topic": item["topic"]})

    # Query
    res = client.search("cloud distributed systems pipelines", top_k=5, rerank_candidates=40)

    total = len(dataset_medium)
    checked = res.get("candidates_checked", total)

    # Efficiency: candidates_checked should be significantly less than total
    assert checked <= min(total, 40), "Server must not return thousands of candidates for HE"


@pytest.mark.integration
@pytest.mark.timeout(180)
def test_similarity_relevance_heuristic(make_client, dataset_medium):
    client = make_client()
    client.initialize()

    # Upload
    for item in dataset_medium:
        client.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"], "topic": item["topic"]})

    # For a tech query, expect some tech category in top results
    tech_query = "AI cryptography machine learning"
    res = client.search(tech_query, top_k=5, rerank_candidates=50)

    categories = [r.get("metadata", {}).get("category") for r in res.get("results", [])]
    # Robustness: check that results exist and are at least somewhat coherent (>=2 share same category)
    assert len(res.get("results", [])) > 0
    if len(categories) >= 2:
        dominant = max({c: categories.count(c) for c in categories if c}.items(), key=lambda kv: kv[1])[1]
        assert dominant >= 2


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_security_no_plaintext_leak_in_server_format(make_client, dataset_small):
    client = make_client()
    client.initialize()

    for item in dataset_small:
        client.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"]})

    res = client.search("finance operations marketing", top_k=3, rerank_candidates=20)

    # Ensure server does not include any obvious plaintext floats in similarity
    # We accept only base64-looking strings
    base64_re = re.compile(r"^[A-Za-z0-9+/=]+$")
    for r in res.get("results", []):
        enc = r.get("encrypted_similarity", "")
        assert base64_re.match(enc), "Similarity must be base64 payload, not plaintext" 