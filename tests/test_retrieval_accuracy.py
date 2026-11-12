import pytest
from fastapi.testclient import TestClient

from dataset_pipeline.common import DATA
from retrieval.bm25_index import BM25Retriever
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.symbol_matcher import extract_query_symbols, classify_candidate_match, rerank_and_classify_candidates
from backend.app.main import app
from backend.app.services.retrieval_service import RetrievalService


@pytest.fixture(scope="module")
def client():
    # Warm up retrieval service instance
    RetrievalService.get_instance()
    with TestClient(app) as c:
        yield c


def test_symbol_extraction():
    q1 = "Where is the check_auth function implemented?"
    info1 = extract_query_symbols(q1)
    assert "check_auth" in info1["explicit_symbols"]
    assert info1["target_type"] == "function"

    q2 = "Where is the `error_message` defined?"
    info2 = extract_query_symbols(q2)
    assert "error_message" in info2["explicit_symbols"]

    q3 = "Show me the unit test for check_auth in format.py"
    info3 = extract_query_symbols(q3)
    assert info3["is_test_query"] is True
    assert info3["file_hint"] == "format.py"


def test_regression_query_check_auth(client):
    """Regression test: verify 'check_auth' returns the exact implementation in format.py,
    NOT test_check_auth_with_valid_auth.
    """
    res = client.post("/api/query", json={
        "question": "Where is the check_auth function implemented?",
        "mode": "hybrid",
        "top_k": 5
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_answered"] is True
    assert len(data["evidence"]) > 0

    top_evidence = data["evidence"][0]
    assert top_evidence["chunk_name"] == "check_auth"
    assert "format.py" in top_evidence["file_path"]
    assert top_evidence["match_classification"] == "exact_match"
    assert "test_validate_format.py" not in top_evidence["file_path"]

    # Verify citations
    assert any("scripts/validate/format.py" in cit for cit in data["citations"])


def test_regression_query_error_message(client):
    """Regression test: verify 'error_message' returns the exact implementation in format.py,
    NOT the caller check_if_list_of_links_are_working.
    """
    res = client.post("/api/query", json={
        "question": "Where is the error_message function implemented?",
        "mode": "hybrid",
        "top_k": 5
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_answered"] is True
    assert len(data["evidence"]) > 0

    top_evidence = data["evidence"][0]
    assert top_evidence["chunk_name"] == "error_message"
    assert "format.py" in top_evidence["file_path"]
    assert top_evidence["match_classification"] == "exact_match"
    assert top_evidence["chunk_name"] != "check_if_list_of_links_are_working"


def test_insufficient_evidence_unanswerable(client):
    """Verify that asking for a non-existent mystery symbol yields insufficient evidence."""
    res = client.post("/api/query", json={
        "question": "Where is the non_existent_quantum_teleportation_function_xyz implemented?",
        "mode": "hybrid",
        "top_k": 5
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_answered"] is False
    assert data["confidence_indicator"] == "insufficient_evidence"
    assert "Insufficient evidence" in data["answer"]


def test_match_classification_categories():
    """Verify that match classification correctly tags exact, test, and caller chunks."""
    q_info = extract_query_symbols("Where is check_auth implemented?")

    exact_candidate = {
        "chunk_id": "c1",
        "chunk_name": "check_auth",
        "chunk_type": "function_definition",
        "file_path": "scripts/validate/format.py",
        "symbols_defined": ["check_auth"],
        "symbols_used": ["print"]
    }
    classif, score = classify_candidate_match(exact_candidate, q_info, base_score=5.0)
    assert classif == "exact_match"
    assert score >= 15.0

    test_candidate = {
        "chunk_id": "c2",
        "chunk_name": "test_check_auth_with_valid_auth",
        "chunk_type": "function_definition",
        "file_path": "tests/test_format.py",
        "symbols_defined": ["test_check_auth_with_valid_auth"],
        "symbols_used": ["check_auth"]
    }
    classif_test, score_test = classify_candidate_match(test_candidate, q_info, base_score=5.0)
    assert classif_test == "related_context"
    assert score_test < score

    caller_candidate = {
        "chunk_id": "c3",
        "chunk_name": "run_all_checks",
        "chunk_type": "function_definition",
        "file_path": "scripts/validate/main.py",
        "symbols_defined": ["run_all_checks"],
        "symbols_used": ["check_auth"]
    }
    classif_caller, score_caller = classify_candidate_match(caller_candidate, q_info, base_score=5.0)
    assert classif_caller == "related_context"


def test_path_traversal_protection(client):
    """Verify that path traversal attempts in repository_id and chunk_id are rejected with HTTP 400."""
    res1 = client.get("/api/repositories/..traversal/files")
    assert res1.status_code == 400
    assert "Security violation" in res1.json()["detail"]

    res2 = client.get("/api/repositories/public-apis/chunks/..traversal")
    assert res2.status_code == 400
    assert "Security violation" in res2.json()["detail"]
