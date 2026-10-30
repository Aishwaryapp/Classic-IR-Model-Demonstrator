import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as ir

def test_tokenization_and_stopwords():
    assert "the" not in ir.tokenize("The information retrieval system")
    assert "information" in ir.tokenize("The information retrieval system")

def test_boolean_and():
    docs = [{"id": 1, "title": "A", "content": "information retrieval system"},
            {"id": 2, "title": "B", "content": "database system"}]
    results, error = ir.boolean_search("information AND retrieval", docs)
    assert error is None
    assert [x["doc"]["id"] for x in results] == [1]

def test_boolean_or_and_not():
    docs = [{"id": 1, "title": "A", "content": "information retrieval"},
            {"id": 2, "title": "B", "content": "database system"}]
    results, error = ir.boolean_search("information OR database", docs)
    assert error is None and len(results) == 2
    results, error = ir.boolean_search("information AND NOT database", docs)
    assert error is None and len(results) == 1

def test_vector_search_ranks_relevant():
    docs = [{"id": 1, "title": "A", "content": "information retrieval search system"},
            {"id": 2, "title": "B", "content": "database storage table"}]
    results, error = ir.vector_search("information retrieval", docs)
    assert error is None
    assert results[0]["doc"]["id"] == 1
    assert results[0]["score"] > 0

def test_fuzzy_search():
    docs = [{"id": 1, "title": "A", "content": "information retrieval search"},
            {"id": 2, "title": "B", "content": "database storage"}]
    results, error = ir.fuzzy_search("information search", docs)
    assert error is None
    assert results[0]["doc"]["id"] == 1

def test_health_route():
    client = ir.app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"
