import sys
from typing import Dict

import pytest


@pytest.mark.integration
@pytest.mark.timeout(180)
def test_top_k_is_respected_and_payload_size(make_client, dataset_large):
    client = make_client()
    client.initialize()

    for item in dataset_large:
        client.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"], "topic": item["topic"]})

    top_k = 7
    res = client.search("wellness telemedicine cardiology", top_k=top_k, rerank_candidates=60)

    # Cardinality
    assert len(res.get("results", [])) <= top_k

    # Payload size bound (rough heuristic): ensure not thousands of results nor huge payload
    # Note: encrypted_similarity is base64; enforce a per-result limit as a sanity check
    total_size = 0
    for r in res.get("results", []):
        enc = r.get("encrypted_similarity", "")
        total_size += len(enc)
        assert len(enc) < 50000, "Encrypted score payload unexpectedly large"

    # Overall response size should be modest for speed
    # Allow generous 1MB budget
    assert total_size < 1_000_000 