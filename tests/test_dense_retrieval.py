import pytest
from pathlib import Path
import numpy as np

from retrieval.embedding_store import EmbeddingStore
from retrieval.dense_index import DenseRetriever


def test_embedding_store_incremental(tmp_path):
    store = EmbeddingStore(tmp_path)
    assert len(store) == 0

    embs_1 = np.random.randn(2, 64).astype(np.float32)
    meta_1 = [
        {"chunk_id": "c1", "repo_id": "r1", "file_path": "a.py"},
        {"chunk_id": "c2", "repo_id": "r1", "file_path": "b.py"}
    ]
    added = store.add_batch(embs_1, meta_1)
    assert added == 2
    assert len(store) == 2
    assert store.contains("c1")

    # Add duplicate and one new
    embs_2 = np.random.randn(2, 64).astype(np.float32)
    meta_2 = [
        {"chunk_id": "c1", "repo_id": "r1", "file_path": "a.py"},
        {"chunk_id": "c3", "repo_id": "r1", "file_path": "c.py"}
    ]
    added_2 = store.add_batch(embs_2, meta_2)
    assert added_2 == 1
    assert len(store) == 3

    # Test persistence
    store.save()
    loaded_store = EmbeddingStore(tmp_path)
    assert len(loaded_store) == 3
    assert loaded_store.contains("c3")


def test_dense_retriever_missing_checkpoint():
    with pytest.raises(FileNotFoundError, match="Required custom CodeEncoder checkpoint missing"):
        DenseRetriever(
            checkpoint_path=Path("non_existent_checkpoint.pt"),
            tokenizer_path=Path("models/tokenizer/tokenizer.json")
        )
