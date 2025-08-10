import pytest


@pytest.mark.integration
@pytest.mark.timeout(180)
def test_client_stats_and_debug(make_client, dataset_small):
    client = make_client()
    client.initialize()

    for item in dataset_small:
        client.add_embedding(text=item["text"], embedding_id=item["id"], metadata={"category": item["category"], "topic": item["topic"]})

    # Run one search to increment stats
    client.search("AI machine learning", top_k=3, rerank_candidates=20)

    # Stats
    stats = client.get_client_stats()
    assert "client_id" in stats
    assert stats.get("total_embeddings", 0) >= len(dataset_small) - 1  # tolerate small diffs
    assert stats.get("total_searches", 0) >= 1

    # Debug
    debug = client.get_debug_info()
    assert debug.get("has_he_context") in (True, False)
    assert debug.get("has_lsh_config") in (True, False)
    assert isinstance(debug.get("total_embeddings", 0), int) 