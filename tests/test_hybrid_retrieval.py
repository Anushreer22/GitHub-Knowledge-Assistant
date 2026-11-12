import pytest
from unittest.mock import MagicMock
from retrieval.hybrid_retriever import HybridRetriever


def test_hybrid_rrf_merging():
    mock_bm25 = MagicMock()
    mock_dense = MagicMock()

    # BM25 returns [c1 (rank 1), c2 (rank 2)]
    mock_bm25.search.return_value = [
        {"chunk_id": "c1", "rank": 1, "score": 10.0, "file_path": "a.py", "start_line": 1, "end_line": 10},
        {"chunk_id": "c2", "rank": 2, "score": 5.0, "file_path": "b.py", "start_line": 1, "end_line": 20}
    ]

    # Dense returns [c2 (rank 1), c3 (rank 2)]
    mock_dense.search.return_value = [
        {"chunk_id": "c2", "rank": 1, "score": 0.95, "file_path": "b.py", "start_line": 1, "end_line": 20},
        {"chunk_id": "c3", "rank": 2, "score": 0.80, "file_path": "c.py", "start_line": 1, "end_line": 30}
    ]

    hybrid = HybridRetriever(mock_bm25, mock_dense, rrf_k=60)
    results = hybrid.search(query="test query", top_k=3, mode="hybrid")

    assert len(results) == 3
    # c2 is rank 2 in BM25 and rank 1 in Dense -> RRF score: 1/(60+2) + 1/(60+1) = 0.01613 + 0.01639 = 0.03252
    # c1 is rank 1 in BM25 only -> 1/(60+1) = 0.01639
    # c3 is rank 2 in Dense only -> 1/(60+2) = 0.01613
    assert results[0]["chunk_id"] == "c2"
    assert results[1]["chunk_id"] == "c1"
    assert results[2]["chunk_id"] == "c3"

    # Verify no duplicate chunk results
    cids = [r["chunk_id"] for r in results]
    assert len(cids) == len(set(cids))
    assert results[0]["retrieval_method"] == "hybrid_rrf"


def test_hybrid_mode_switching():
    mock_bm25 = MagicMock()
    mock_dense = MagicMock()

    mock_bm25.search.return_value = [{"chunk_id": "c_bm25", "score": 5.0}]
    mock_dense.search.return_value = [{"chunk_id": "c_dense", "score": 0.9}]

    hybrid = HybridRetriever(mock_bm25, mock_dense)

    bm25_res = hybrid.search("test", mode="bm25")
    assert bm25_res[0]["chunk_id"] == "c_bm25"
    mock_bm25.search.assert_called_once()

    dense_res = hybrid.search("test", mode="dense")
    assert dense_res[0]["chunk_id"] == "c_dense"
    mock_dense.search.assert_called_once()
