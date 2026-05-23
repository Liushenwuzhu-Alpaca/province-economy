"""RAG retrieval smoke tests."""

from src.agent.rag import get_context, search


def test_search_returns_results():
    results = search("熵权法", top_k=3)
    assert len(results) > 0
    for r in results:
        assert "text" in r
        assert "source" in r
        assert len(r["text"]) > 0


def test_search_relevance():
    results = search("广东省经济竞争力排名", top_k=3)
    assert len(results) > 0
    # Cosine distance should be reasonable
    for r in results:
        assert r.get("distance", 1.0) < 1.0


def test_get_context_not_empty():
    context = get_context("GDP增速", top_k=3)
    assert len(context) > 0
    assert "---" in context


def test_search_unknown_topic():
    results = search("火星经济数据xyz", top_k=3)
    # Should still return something (best-effort retrieval)
    assert isinstance(results, list)
    if len(results) > 0:
        for r in results:
            assert r.get("distance", 1.0) < 1.0
