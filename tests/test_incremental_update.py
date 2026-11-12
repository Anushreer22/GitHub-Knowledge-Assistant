import pytest
from fastapi.testclient import TestClient
import numpy as np

from backend.app.main import app
from backend.app.services.retrieval_service import RetrievalService
from backend.app.services.update_service import sync_repository, get_indexing_history
from retrieval.bm25_index import BM25Retriever
from retrieval.embedding_store import EmbeddingStore


@pytest.fixture(scope="module")
def client():
    RetrievalService.get_instance()
    with TestClient(app) as c:
        yield c


def test_sync_repository_not_found(client):
    """Verify that syncing a non-existent repository yields HTTP 404."""
    res = client.post("/api/repositories/non_existent__repo__xyz/sync")
    assert res.status_code == 404
    assert "not indexed" in res.json()["detail"].lower()


def test_sync_repository_up_to_date(client):
    """Verify that syncing an unchanged repository detects up-to-date status and records history."""
    res = client.post("/api/repositories/public-apis__public-apis/sync")
    assert res.status_code == 200
    data = res.json()
    assert data["repo_id"] == "public-apis__public-apis"
    assert data["status"] in ["up_to_date", "success"]
    assert "current_commit" in data

    # Verify history was recorded
    history_res = client.get("/api/repositories/public-apis__public-apis/history")
    assert history_res.status_code == 200
    history_items = history_res.json()
    assert len(history_items) > 0
    assert history_items[0]["repo_id"] == "public-apis__public-apis"


def test_global_history_endpoint(client):
    """Verify GET /api/history returns global indexing history."""
    res = client.get("/api/history")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)


def test_bm25_remove_and_update_chunks():
    """Verify atomic removal of outdated chunks and addition of new chunks in BM25 index."""
    retriever = BM25Retriever()
    initial_chunks = [
        {
            "chunk_id": "c1",
            "repo_id": "test_repo",
            "file_path": "a.py",
            "start_line": 1,
            "end_line": 5,
            "chunk_type": "function_definition",
            "chunk_name": "alpha_apple",
            "language": "python",
            "symbols_defined": ["alpha_apple"],
            "symbols_used": [],
            "code_text": "def alpha_apple(): return 1"
        },
        {
            "chunk_id": "c2",
            "repo_id": "test_repo",
            "file_path": "b.py",
            "start_line": 1,
            "end_line": 5,
            "chunk_type": "function_definition",
            "chunk_name": "beta_banana",
            "language": "python",
            "symbols_defined": ["beta_banana"],
            "symbols_used": [],
            "code_text": "def beta_banana(): return 2"
        }
    ]
    retriever.build_index(initial_chunks)
    assert len(retriever.corpus_meta) == 2

    # Verify c2 is searchable
    assert len(retriever.search("banana", top_k=2)) == 1

    # Prune c2 and add c3
    new_chunks = [
        {
            "chunk_id": "c3",
            "repo_id": "test_repo",
            "file_path": "c.py",
            "start_line": 1,
            "end_line": 5,
            "chunk_type": "function_definition",
            "chunk_name": "gamma_cherry",
            "language": "python",
            "symbols_defined": ["gamma_cherry"],
            "symbols_used": [],
            "code_text": "def gamma_cherry(): return 3"
        }
    ]
    removed, added = retriever.remove_and_update_chunks(remove_chunk_ids={"c2"}, new_chunks=new_chunks)
    assert removed == 1
    assert added == 1
    assert len(retriever.corpus_meta) == 2

    # Verify c2 is no longer found, but c1 and c3 are found
    assert len(retriever.search("banana", top_k=2)) == 0
    assert len(retriever.search("cherry", top_k=2)) == 1
    assert len(retriever.search("apple", top_k=2)) == 1


def test_embedding_store_remove_chunks(tmp_path):
    """Verify incremental removal of chunks from EmbeddingStore."""
    store = EmbeddingStore(tmp_path)
    embs = np.random.randn(3, 16).astype(np.float32)
    meta = [
        {"chunk_id": "ch1", "name": "f1"},
        {"chunk_id": "ch2", "name": "f2"},
        {"chunk_id": "ch3", "name": "f3"}
    ]
    store.add_batch(embs, meta)
    assert len(store) == 3
    assert store.contains("ch2") is True

    # Remove ch2
    removed = store.remove_chunks({"ch2"})
    assert removed == 1
    assert len(store) == 2
    assert store.contains("ch2") is False
    assert store.contains("ch1") is True
    assert store.contains("ch3") is True
    assert store.embeddings.shape[0] == 2
