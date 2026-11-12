import pytest
from fastapi.testclient import TestClient

from retrieval.symbol_graph import SymbolGraphIndex, RelationshipType
from backend.app.main import app
from backend.app.services.retrieval_service import RetrievalService


@pytest.fixture
def sample_chunks():
    return [
        {
            "chunk_id": "c_base",
            "repo_id": "test__repo",
            "file_path": "models/base.py",
            "chunk_name": "BaseService",
            "chunk_type": "class_definition",
            "start_line": 1,
            "end_line": 15,
            "code_text": "class BaseService:\n    def execute(self):\n        pass",
            "imports": ["typing"],
            "symbols_defined": ["BaseService", "execute"],
            "symbols_used": []
        },
        {
            "chunk_id": "c_auth",
            "repo_id": "test__repo",
            "file_path": "services/auth_service.py",
            "chunk_name": "AuthService",
            "chunk_type": "class_definition",
            "start_line": 1,
            "end_line": 25,
            "code_text": "class AuthService(BaseService):\n    def verify_token(self, token):\n        return validate_signature(token)",
            "imports": ["models.base", "security.crypto"],
            "symbols_defined": ["AuthService", "verify_token"],
            "symbols_used": ["BaseService", "validate_signature"]
        },
        {
            "chunk_id": "c_api",
            "repo_id": "test__repo",
            "file_path": "api/routes.py",
            "chunk_name": "login_route",
            "chunk_type": "function_definition",
            "start_line": 10,
            "end_line": 20,
            "code_text": "def login_route():\n    auth = AuthService()\n    return auth.verify_token('xyz')",
            "imports": ["services.auth_service"],
            "symbols_defined": ["login_route"],
            "symbols_used": ["AuthService", "verify_token"]
        },
        {
            "chunk_id": "c_test_auth",
            "repo_id": "test__repo",
            "file_path": "tests/test_auth.py",
            "chunk_name": "test_verify_token_success",
            "chunk_type": "function_definition",
            "start_line": 5,
            "end_line": 15,
            "code_text": "def test_verify_token_success():\n    svc = AuthService()\n    assert svc.verify_token('valid')",
            "imports": ["services.auth_service"],
            "symbols_defined": ["test_verify_token_success"],
            "symbols_used": ["AuthService", "verify_token"]
        }
    ]


def test_symbol_inheritance_extraction(sample_chunks):
    graph = SymbolGraphIndex(sample_chunks)
    res = graph.get_symbol_relationships("AuthService")
    
    assert res["is_defined"] is True
    assert "BaseService" in res["inheritance"]["base_classes"]
    
    base_res = graph.get_symbol_relationships("BaseService")
    assert "AuthService" in base_res["inheritance"]["subclasses"]


def test_symbol_callers_and_callees(sample_chunks):
    graph = SymbolGraphIndex(sample_chunks)
    
    # Query verify_token
    res = graph.get_symbol_relationships("verify_token")
    assert res["is_defined"] is True
    
    # login_route should be caller
    caller_names = [c["caller_name"] for c in res["callers"]]
    assert "login_route" in caller_names
    
    # Check verification status
    for c in res["callers"]:
        if c["caller_name"] == "login_route":
            assert c["verification"] == RelationshipType.DIRECTLY_VERIFIED

    # Check callees of AuthService (which calls validate_signature)
    auth_res = graph.get_symbol_relationships("AuthService")
    callee_names = [c["symbol_name"] for c in auth_res["callees"]]
    assert "validate_signature" in callee_names
    # validate_signature has no definition in sample_chunks, so unverified_assumption
    sig_callee = next(c for c in auth_res["callees"] if c["symbol_name"] == "validate_signature")
    assert sig_callee["verification"] == RelationshipType.UNVERIFIED_ASSUMPTION


def test_symbol_related_tests(sample_chunks):
    graph = SymbolGraphIndex(sample_chunks)
    res = graph.get_symbol_relationships("verify_token")
    
    test_names = [t["test_name"] for t in res["related_tests"]]
    assert "test_verify_token_success" in test_names
    assert res["related_tests"][0]["verification"] == RelationshipType.DIRECTLY_VERIFIED


def test_symbol_graph_pruning(sample_chunks):
    graph = SymbolGraphIndex(sample_chunks)
    assert graph.get_symbol_relationships("verify_token")["is_defined"] is True
    
    # Prune c_auth
    graph.remove_chunks({"c_auth"})
    res = graph.get_symbol_relationships("verify_token")
    assert res["is_defined"] is False
    assert res["definitions_count"] == 0


def test_api_symbol_relationships_endpoint(sample_chunks):
    client = TestClient(app)
    service = RetrievalService.get_instance()
    service.symbol_graph = SymbolGraphIndex(sample_chunks)
    
    response = client.get("/api/repositories/test__repo/symbols/verify_token")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol_name"] == "verify_token"
    assert data["is_defined"] is True
    assert len(data["callers"]) >= 1
    assert len(data["related_tests"]) >= 1
