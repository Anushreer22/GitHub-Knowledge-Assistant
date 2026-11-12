import pytest
from unittest.mock import MagicMock

from retrieval.answer_engine import AnswerEngine, is_multi_file_query
from retrieval.symbol_graph import SymbolGraphIndex
from retrieval.context_expander import ContextExpander


@pytest.fixture
def mock_retriever_and_chunks():
    chunks = [
        {
            "chunk_id": "c_core",
            "repo_id": "test__flow_repo",
            "file_path": "auth/engine.py",
            "chunk_name": "authenticate_user",
            "chunk_type": "function_definition",
            "start_line": 20,
            "end_line": 40,
            "code_text": "def authenticate_user(token):\n    return verify_token(token)",
            "symbols_defined": ["authenticate_user"],
            "symbols_used": ["verify_token"],
            "imports": ["auth.crypto"],
            "score": 0.08,
            "match_classification": "exact_match"
        },
        {
            "chunk_id": "c_caller",
            "repo_id": "test__flow_repo",
            "file_path": "api/router.py",
            "chunk_name": "login_endpoint",
            "chunk_type": "function_definition",
            "start_line": 15,
            "end_line": 35,
            "code_text": "def login_endpoint(req):\n    return authenticate_user(req.token)",
            "symbols_defined": ["login_endpoint"],
            "symbols_used": ["authenticate_user"],
            "imports": ["auth.engine"],
            "score": 0.05,
            "match_classification": "related_context"
        },
        {
            "chunk_id": "c_test",
            "repo_id": "test__flow_repo",
            "file_path": "tests/test_auth.py",
            "chunk_name": "test_authenticate_user_valid",
            "chunk_type": "function_definition",
            "start_line": 5,
            "end_line": 15,
            "code_text": "def test_authenticate_user_valid():\n    assert authenticate_user('valid_token')",
            "symbols_defined": ["test_authenticate_user_valid"],
            "symbols_used": ["authenticate_user"],
            "imports": ["auth.engine"],
            "score": 0.04,
            "match_classification": "related_context"
        }
    ]

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = chunks

    chunk_dict = {c["chunk_id"]: c for c in chunks}
    expander = ContextExpander(chunk_dict)
    symbol_graph = SymbolGraphIndex(chunks)

    return mock_retriever, expander, symbol_graph, chunks


def test_is_multi_file_query_detection():
    assert is_multi_file_query("How does the authentication flow work in this repository?") is True
    assert is_multi_file_query("What classes implement the worker pipeline?") is True
    assert is_multi_file_query("Where is check_auth defined?") is False
    assert is_multi_file_query("Explain registration and dispatch across files") is True


def test_multi_file_flow_synthesis(mock_retriever_and_chunks):
    retriever, expander, symbol_graph, chunks = mock_retriever_and_chunks
    engine = AnswerEngine(retriever, expander, symbol_graph=symbol_graph)

    res = engine.answer_question(
        question="How does the authentication flow work across components?",
        repo_id="test__flow_repo"
    )

    assert res["is_answered"] is True
    assert "Architecture & Execution Flow" in res["answer"]
    assert "[Core Component]" in res["answer"]
    assert "auth/engine.py" in res["answer"]
    assert "[Inbound Invocation]" in res["answer"] or "[Supporting Component]" in res["answer"]
    assert "[Verification]" in res["answer"]
    assert len(res["citations"]) >= 2


def test_missing_evidence_statement(mock_retriever_and_chunks):
    retriever, expander, symbol_graph, chunks = mock_retriever_and_chunks
    engine = AnswerEngine(retriever, expander, symbol_graph=symbol_graph)

    # Query asking about registration wiring which is not present in chunks
    res = engine.answer_question(
        question="How does the authentication flow register its backend handler?",
        repo_id="test__flow_repo"
    )

    assert res["is_answered"] is True
    assert "missing evidence" in res["answer"].lower()
    assert "registration" in res["answer"].lower()


def test_strict_citation_discipline(mock_retriever_and_chunks):
    retriever, expander, symbol_graph, chunks = mock_retriever_and_chunks
    engine = AnswerEngine(retriever, expander, symbol_graph=symbol_graph)

    res = engine.answer_question(
        question="Explain the authentication flow step by step",
        repo_id="test__flow_repo"
    )

    # All files mentioned in answer must have a corresponding citation
    answer = res["answer"]
    citations = res["citations"]
    
    for c in chunks:
        fpath = c["file_path"]
        if fpath in answer:
            # Check there is a citation matching this file
            assert any(fpath in cit for cit in citations), f"File {fpath} mentioned in answer but missing from citations"
