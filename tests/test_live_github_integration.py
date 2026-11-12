import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.github_service import (
    validate_and_parse_github_url,
    fetch_github_metadata,
    add_and_index_github_repo
)
from backend.app.services.retrieval_service import RetrievalService
from retrieval.bm25_index import BM25Retriever


@pytest.fixture(scope="module")
def client():
    RetrievalService.get_instance()
    with TestClient(app) as c:
        yield c


def test_url_validation_valid():
    """Verify valid GitHub URLs and short forms parse correctly."""
    assert validate_and_parse_github_url("https://github.com/psf/requests") == ("psf", "requests")
    assert validate_and_parse_github_url("http://github.com/pallets/flask.git") == ("pallets", "flask")
    assert validate_and_parse_github_url("https://www.github.com/google/gson") == ("google", "gson")
    assert validate_and_parse_github_url("octocat/Hello-World") == ("octocat", "Hello-World")
    assert validate_and_parse_github_url("https://github.com/encode/starlette/") == ("encode", "starlette")


def test_url_validation_rejections():
    """Verify malicious or invalid URLs are strictly rejected."""
    invalid_cases = [
        ("https://gitlab.com/owner/repo", "Invalid GitHub repository URL"),
        ("https://github.com/owner/repo;rm -rf /", "Contains prohibited command injection"),
        ("https://github.com/owner/repo&&echo 1", "Contains prohibited command injection"),
        ("https://github.com/owner/../repo", "Directory traversal sequences"),
        ("--upload-pack=evil", "URL cannot start with a dash flag"),
        ("file:///etc/passwd", "Invalid GitHub repository URL"),
        ("https://attacker.com/github.com/owner/repo", "Invalid GitHub repository URL"),
        ("", "non-empty string"),
    ]

    for bad_url, expected_err in invalid_cases:
        with pytest.raises(ValueError) as exc_info:
            validate_and_parse_github_url(bad_url)
        assert any(term in str(exc_info.value).lower() for term in expected_err.lower().split())


def test_duplicate_repository_rejected(client):
    """Verify attempting to add an already indexed repository is rejected with HTTP 400."""
    res = client.post("/api/repositories/add", json={
        "url": "https://github.com/public-apis/public-apis",
        "max_chunks": 100
    })
    assert res.status_code == 400
    assert "already indexed" in res.json()["detail"].lower()


def test_api_invalid_url_rejected(client):
    """Verify POST /api/repositories/add rejects malicious or invalid URLs with HTTP 400."""
    res = client.post("/api/repositories/add", json={
        "url": "https://gitlab.com/attacker/malware",
        "max_chunks": 100
    })
    assert res.status_code == 400
    assert "Invalid GitHub repository URL" in res.json()["detail"]


def test_bm25_incremental_add_chunks():
    """Verify that BM25Retriever.add_chunks incrementally indexes new documents and makes them searchable."""
    retriever = BM25Retriever()
    initial_chunks = [
        {
            "chunk_id": "init_1",
            "repo_id": "demo__repo",
            "file_path": "main.py",
            "start_line": 1,
            "end_line": 10,
            "chunk_type": "function_definition",
            "chunk_name": "initial_bootstrap",
            "language": "python",
            "symbols_defined": ["initial_bootstrap"],
            "symbols_used": ["print"],
            "code_text": "def initial_bootstrap(): print('ready')"
        }
    ]
    retriever.build_index(initial_chunks)
    assert len(retriever.corpus_meta) == 1

    # Add a new chunk incrementally
    new_chunks = [
        {
            "chunk_id": "new_2",
            "repo_id": "demo__repo",
            "file_path": "calc.py",
            "start_line": 1,
            "end_line": 5,
            "chunk_type": "function_definition",
            "chunk_name": "compute_matrix_dot",
            "language": "python",
            "symbols_defined": ["compute_matrix_dot"],
            "symbols_used": ["numpy"],
            "code_text": "def compute_matrix_dot(a, b): return a @ b"
        }
    ]
    added = retriever.add_chunks(new_chunks)
    assert added == 1
    assert len(retriever.corpus_meta) == 2

    # Query for the new symbol
    results = retriever.search("compute_matrix_dot", top_k=2)
    assert len(results) > 0
    assert results[0]["chunk_name"] == "compute_matrix_dot"
