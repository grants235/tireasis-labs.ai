import time
from typing import List, Dict

import pytest


@pytest.mark.integration
@pytest.mark.timeout(300)
def test_multi_client_isolation(make_client):
    # Create two clients with separate sessions
    client_a = make_client()
    client_b = make_client()

    client_a.initialize()
    client_b.initialize()

    data_a = [
        {"id": "a1", "text": "AI machine learning cryptography", "category": "technology", "topic": "AI"},
        {"id": "a2", "text": "cloud distributed systems", "category": "technology", "topic": "cloud"},
    ]

    data_b = [
        {"id": "b1", "text": "nutrition wellness cardiology", "category": "health", "topic": "wellness"},
        {"id": "b2", "text": "e-learning pedagogy curriculum", "category": "education", "topic": "pedagogy"},
    ]

    for item in data_a:
        client_a.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"], "topic": item["topic"]})
    for item in data_b:
        client_b.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"], "topic": item["topic"]})

    # Queries should not cross-contaminate; results reference embedding_ids uploaded by the same client
    res_a = client_a.search("cryptography", top_k=3, rerank_candidates=10)
    res_b = client_b.search("curriculum", top_k=3, rerank_candidates=10)

    ids_a = {str(r.get("embedding_id")) for r in res_a.get("results", [])}
    ids_b = {str(r.get("embedding_id")) for r in res_b.get("results", [])}

    # There should be no shared embedding ids between clients' results
    assert ids_a.isdisjoint(ids_b)


@pytest.mark.integration
@pytest.mark.timeout(300)
def test_basic_performance_budget(make_client):
    client = make_client()
    client.initialize()

    # Upload a moderate set
    payloads: List[Dict[str, str]] = [
        {"id": f"p{i}", "text": f"AI systems scalability pipelines {i}", "category": "technology", "topic": "AI"}
        for i in range(80)
    ]
    for p in payloads:
        client.add_embedding(text=p["text"], embedding_id=p["id"], metadata={"category": p["category"], "topic": p["topic"]})

    start = time.time()
    res = client.search("scalability pipelines in cloud AI", top_k=10, rerank_candidates=50)
    elapsed_ms = (time.time() - start) * 1000

    # Basic budgets (non-strict; environment dependent)
    assert elapsed_ms < 5000, f"Search too slow: {elapsed_ms:.1f}ms"
    assert res.get("candidates_checked", 999999) <= 50 