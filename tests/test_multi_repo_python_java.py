import pytest
from pathlib import Path
from typing import Dict, Any, List

from dataset_pipeline.build_chunks import py_chunks, java_chunks
from backend.app.services.github_service import validate_and_parse_github_url
from retrieval.bm25_index import BM25Retriever
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.answer_engine import AnswerEngine
from retrieval.context_expander import ContextExpander


# ============================================================================
# 1. GitHub Ingestion & URL Validation Tests
# ============================================================================

def test_github_url_validation_valid():
    """Verify standard GitHub URLs and shorthand notation parse successfully."""
    valid_cases = [
        ("https://github.com/psf/requests", ("psf", "requests")),
        ("https://github.com/pallets/flask.git", ("pallets", "flask")),
        ("http://github.com/google/gson/", ("google", "gson")),
        ("tiangolo/fastapi", ("tiangolo", "fastapi")),
        ("square/retrofit.git", ("square", "retrofit"))
    ]
    for url, (expected_owner, expected_repo) in valid_cases:
        owner, repo = validate_and_parse_github_url(url)
        assert owner == expected_owner
        assert repo == expected_repo


def test_github_url_validation_security_rejections():
    """Ensure directory traversal, command injection, and invalid schemes are rejected."""
    invalid_cases = [
        "",
        "   ",
        "https://malicious.com/owner/repo",
        "https://github.com/owner/repo; rm -rf /",
        "owner/repo&whoami",
        "owner/repo|calc",
        "../traversal/repo",
        "-flag/repo",
        "https://github.com/owner/repo\nmalicious"
    ]
    for bad_url in invalid_cases:
        with pytest.raises(ValueError):
            validate_and_parse_github_url(bad_url)


# ============================================================================
# 2. Python Language-Aware AST Parsing Tests
# ============================================================================

def test_python_ast_parsing_complete():
    """Verify Python AST parser extracts classes, methods, decorators, and line numbers."""
    code = """import os
from typing import Optional

@decorator_a
@decorator_b
class AuthManager:
    def __init__(self, secret_key: str):
        self.key = secret_key

    @property
    def is_configured(self) -> bool:
        return bool(self.key)

    async def authenticate(self, token: str) -> Optional[str]:
        def decode_header():
            return token[:5]
        return decode_header()
"""
    chunks = py_chunks(code)
    chunk_names = [c[1] for c in chunks]
    chunk_types = [c[0] for c in chunks]

    # Class and method hierarchy
    assert "AuthManager" in chunk_names
    assert "AuthManager.__init__" in chunk_names
    assert "AuthManager.is_configured" in chunk_names
    assert "AuthManager.authenticate" in chunk_names
    assert "AuthManager.authenticate.decode_header" in chunk_names

    # Types
    assert "class_definition" in chunk_types
    assert "method_definition" in chunk_types
    assert "async_method_definition" in chunk_types

    # Decorator line preservation: AuthManager starts at line 4 where @decorator_a is
    cls_chunk = next(c for c in chunks if c[1] == "AuthManager")
    assert cls_chunk[3] == 4  # Start line covers decorator
    assert cls_chunk[4] == 17 # End line covers class body


def test_python_pyi_stub_parsing():
    """Verify type stub (.pyi) files are parsed cleanly."""
    stub_code = """from typing import List

class BaseService:
    def execute(self, params: List[str]) -> bool: ...
"""
    chunks = py_chunks(stub_code)
    assert len(chunks) >= 2
    assert any(c[1] == "BaseService" for c in chunks)
    assert any(c[1] == "BaseService.execute" for c in chunks)


def test_python_syntax_error_fallback():
    """Verify syntax error in unparseable Python falls back gracefully without crashing."""
    corrupt_code = "def broken( \n this is totally invalid python {["
    chunks = py_chunks(corrupt_code)
    assert len(chunks) > 0
    assert chunks[0][8] == "line_fallback"


# ============================================================================
# 3. Java Language-Aware tree-sitter Parsing Tests
# ============================================================================

def test_java_tree_sitter_parsing_complete():
    """Verify Java parser extracts classes, interfaces, constructors, methods, and overloads."""
    java_code = """package com.example.service;

import java.util.List;

public class OrderProcessor implements IProcessor {
    private final String config;

    public OrderProcessor(String config) {
        this.config = config;
    }

    @Override
    @Transactional
    public boolean process(Long orderId, double amount) {
        return true;
    }

    public boolean process(String orderRef) {
        return false;
    }

    public static class InnerConfig {
        public void apply() {}
    }
}
"""
    chunks = java_chunks(java_code)
    chunk_names = [c[1] for c in chunks]
    chunk_types = [c[0] for c in chunks]

    # Verify extraction
    assert "OrderProcessor" in chunk_names
    assert any("OrderProcessor(String)" in name for name in chunk_names)
    # Overloaded methods differentiated by parameter signatures
    assert any("process(Long, double)" in name for name in chunk_names)
    assert any("process(String)" in name for name in chunk_names)
    # Nested class and nested method
    assert "OrderProcessor.InnerConfig" in chunk_names
    assert any("InnerConfig.apply()" in name for name in chunk_names)

    # Line numbers preservation
    method_chunk = next(c for c in chunks if "process(Long, double)" in c[1])
    assert method_chunk[3] >= 11 # Starts around annotations
    assert method_chunk[4] <= 17


def test_java_interface_and_enum_parsing():
    """Verify Java interfaces, enums, and records parse accurately."""
    java_code = """package com.example.model;

public interface UserApi {
    void registerUser(String email);
}

public enum UserStatus {
    ACTIVE, SUSPENDED, DELETED
}
"""
    chunks = java_chunks(java_code)
    names = [c[1] for c in chunks]
    assert "UserApi" in names
    assert any("registerUser" in n for n in names)
    assert "UserStatus" in names


# ============================================================================
# 4. Multi-Repository Isolation Tests
# ============================================================================

def test_multi_repository_isolation():
    """Verify search queries strictly filter by repo_id without cross-contamination."""
    corpus = [
        {
            "chunk_id": "chunk_py_1",
            "repo_id": "psf__requests",
            "file_path": "requests/auth.py",
            "chunk_name": "HTTPBasicAuth",
            "chunk_type": "class_definition",
            "language": "python",
            "code_text": "class HTTPBasicAuth:\n    def __init__(self, username, password):\n        self.username = username",
            "start_line": 1,
            "end_line": 3,
            "symbols_defined": ["HTTPBasicAuth"],
            "symbols_used": []
        },
        {
            "chunk_id": "chunk_java_1",
            "repo_id": "google__gson",
            "file_path": "gson/src/main/java/Gson.java",
            "chunk_name": "Gson.fromJson",
            "chunk_type": "method_declaration",
            "language": "java",
            "code_text": "public <T> T fromJson(String json, Class<T> classOfT) {\n    return null;\n}",
            "start_line": 10,
            "end_line": 12,
            "symbols_defined": ["fromJson"],
            "symbols_used": []
        }
    ]

    retriever = BM25Retriever()
    retriever.build_index(corpus)

    # 1. Query scoped to psf__requests
    res_py = retriever.search(query="auth username", top_k=5, repo_id="psf__requests")
    assert len(res_py) > 0
    assert all(r["repo_id"] == "psf__requests" for r in res_py)

    # 2. Query scoped to google__gson
    res_java = retriever.search(query="fromJson json", top_k=5, repo_id="google__gson")
    assert len(res_java) > 0
    assert all(r["repo_id"] == "google__gson" for r in res_java)

    # 3. Querying with wrong repo_id returns empty (strict isolation guarantee)
    res_isolated = retriever.search(query="HTTPBasicAuth", top_k=5, repo_id="google__gson")
    assert len(res_isolated) == 0


# ============================================================================
# 5. Evidence-Grounded Answering & Missing Evidence Tests
# ============================================================================

def test_evidence_grounded_answer_success():
    """Verify successful QA query returns factual answer grounded in code citations."""
    corpus = [
        {
            "chunk_id": "c1",
            "repo_id": "repo__app",
            "file_path": "auth/service.py",
            "chunk_name": "AuthService.validate_token",
            "chunk_type": "method_definition",
            "language": "python",
            "code_text": "class AuthService:\n    def validate_token(self, token: str) -> bool:\n        return token.startswith('bearer_')",
            "start_line": 1,
            "end_line": 3,
            "symbols_defined": ["AuthService", "validate_token"],
            "symbols_used": []
        }
    ]

    bm25 = BM25Retriever()
    bm25.build_index(corpus)

    # Mock hybrid with BM25
    class MockHybrid:
        def search(self, query, top_k=5, mode="hybrid", repo_id=None):
            return bm25.search(query, top_k=top_k, repo_id=repo_id)

    chunk_dict = {"c1": corpus[0]}
    expander = ContextExpander(chunk_dict)
    engine = AnswerEngine(retriever=MockHybrid(), expander=expander, min_evidence_threshold=0.001)

    result = engine.answer_question(
        question="Where is validate_token implemented?",
        repo_id="repo__app"
    )

    assert result["is_answered"] is True
    assert "AuthService.validate_token" in result["answer"]
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["file_path"] == "auth/service.py"
    assert result["evidence"][0]["start_line"] == 1


def test_insufficient_evidence_state():
    """Verify asking about code not present in repository triggers insufficient_evidence."""
    corpus = [
        {
            "chunk_id": "c1",
            "repo_id": "repo__calc",
            "file_path": "calc/math.py",
            "chunk_name": "add",
            "chunk_type": "function_definition",
            "language": "python",
            "code_text": "def add(a, b):\n    return a + b",
            "start_line": 1,
            "end_line": 2,
            "symbols_defined": ["add"],
            "symbols_used": []
        }
    ]

    bm25 = BM25Retriever()
    bm25.build_index(corpus)

    class MockHybrid:
        def search(self, query, top_k=5, mode="hybrid", repo_id=None):
            return bm25.search(query, top_k=top_k, repo_id=repo_id)

    chunk_dict = {"c1": corpus[0]}
    expander = ContextExpander(chunk_dict)
    engine = AnswerEngine(retriever=MockHybrid(), expander=expander)

    result = engine.answer_question(
        question="Where is blockchain cryptocurrency mining configured?",
        repo_id="repo__calc"
    )

    assert result["is_answered"] is False
    assert result["confidence_indicator"] == "insufficient_evidence"
    assert "Insufficient evidence" in result["answer"]
    assert len(result["evidence"]) == 0
