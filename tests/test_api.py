import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "repositories_count" in data
    assert "version" in data


def test_list_repositories():
    response = client.get("/api/repositories")
    assert response.status_code == 200
    repos = response.json()
    assert isinstance(repos, list)
    assert len(repos) >= 4
    first = repos[0]
    assert "repo_id" in first
    assert "language" in first


def test_search_endpoint():
    payload = {
        "query": "validate_format",
        "top_k": 3,
        "mode": "bm25"
    }
    response = client.post("/api/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "validate_format"
    assert data["retrieval_method"] == "bm25"
    assert "results" in data
    assert len(data["results"]) >= 1
    assert "citation" in data["results"][0]


def test_query_endpoint():
    payload = {
        "question": "Where is error_message implemented?",
        "top_k": 3,
        "mode": "bm25"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "is_answered" in data
    assert "citations" in data


def test_query_invalid_payload():
    # Empty question should fail validation with 422
    response = client.post("/api/query", json={"question": ""})
    assert response.status_code == 422


def test_repository_files_not_found():
    response = client.get("/api/repositories/non_existent_repo/files")
    assert response.status_code == 404
    detail = response.json()["detail"].lower()
    assert "not found" in detail or "no files" in detail


def test_chunk_detail_not_found():
    response = client.get("/api/repositories/public-apis__public-apis/chunks/non_existent_chunk_id")
    assert response.status_code == 404


def test_feedback_endpoint():
    payload = {
        "query_or_question": "Where is check_auth defined?",
        "feedback_type": "helpful",
        "citation": "repo:file.py#L1-L10",
        "notes": "Exact line matches"
    }
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert "feedback_id" in data
