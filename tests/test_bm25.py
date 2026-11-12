import pytest
from retrieval.bm25_index import BM25Retriever, tokenize_code


def test_tokenize_code():
    text = "public class UserProfileManager { def get_user_by_id(int user_id) {} }"
    tokens = tokenize_code(text)
    assert "public" in tokens
    assert "class" in tokens
    assert "userprofilemanager" in tokens
    assert "user" in tokens
    assert "profile" in tokens
    assert "manager" in tokens
    assert "get_user_by_id" in tokens
    assert "user_id" in tokens


def test_bm25_exact_identifier_search(tmp_path):
    chunks = [
        {
            "chunk_id": "c1",
            "repo_id": "repoA",
            "file_path": "auth/service.py",
            "chunk_name": "authenticate_user",
            "chunk_type": "FunctionDef",
            "code_text": "def authenticate_user(username, password):\n    return verify(username, password)",
            "start_line": 1,
            "end_line": 3,
            "symbols_defined": ["authenticate_user"],
            "symbols_used": ["verify"]
        },
        {
            "chunk_id": "c2",
            "repo_id": "repoA",
            "file_path": "db/connector.py",
            "chunk_name": "DatabaseConnector",
            "chunk_type": "ClassDef",
            "code_text": "class DatabaseConnector:\n    def connect(self): pass",
            "start_line": 10,
            "end_line": 15,
            "symbols_defined": ["DatabaseConnector"],
            "symbols_used": []
        }
    ]

    retriever = BM25Retriever()
    retriever.build_index(chunks)

    # Search for exact function name
    results = retriever.search("authenticate_user", top_k=2)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "c1"
    assert results[0]["file_path"] == "auth/service.py"
    assert results[0]["start_line"] == 1
    assert results[0]["end_line"] == 3

    # Test persistence
    index_file = tmp_path / "bm25_test.pkl"
    retriever.save(index_file)

    loaded = BM25Retriever(index_file)
    results_loaded = loaded.search("DatabaseConnector", top_k=1)
    assert len(results_loaded) == 1
    assert results_loaded[0]["chunk_id"] == "c2"
