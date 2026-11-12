import pytest
from retrieval.context_expander import ContextExpander


def test_context_expansion_enclosing_class_and_siblings():
    chunks = {
        "class_1": {
            "chunk_id": "class_1",
            "repo_id": "repoA",
            "file_path": "services/UserService.java",
            "chunk_name": "UserService",
            "chunk_type": "class_declaration",
            "start_line": 1,
            "end_line": 50,
            "symbols_defined": ["UserService"],
            "symbols_used": [],
            "imports": ["java.util.List"]
        },
        "method_1": {
            "chunk_id": "method_1",
            "repo_id": "repoA",
            "file_path": "services/UserService.java",
            "chunk_name": "findUser",
            "chunk_type": "method_declaration",
            "start_line": 10,
            "end_line": 20,
            "symbols_defined": ["findUser"],
            "symbols_used": ["User", "DatabaseClient"],
            "imports": ["java.util.List"]
        },
        "method_2": {
            "chunk_id": "method_2",
            "repo_id": "repoA",
            "file_path": "services/UserService.java",
            "chunk_name": "deleteUser",
            "chunk_type": "method_declaration",
            "start_line": 25,
            "end_line": 35,
            "symbols_defined": ["deleteUser"],
            "symbols_used": ["id"],
            "imports": ["java.util.List"]
        },
        "target_db": {
            "chunk_id": "target_db",
            "repo_id": "repoA",
            "file_path": "db/DatabaseClient.java",
            "chunk_name": "DatabaseClient",
            "chunk_type": "class_declaration",
            "start_line": 1,
            "end_line": 30,
            "symbols_defined": ["DatabaseClient"],
            "symbols_used": []
        }
    }

    expander = ContextExpander(chunks)
    ctx = expander.expand_context(chunks["method_1"])

    # 1. Enclosing class verified
    assert ctx["parent_class"] is not None
    assert ctx["parent_class"]["class_name"] == "UserService"
    assert ctx["parent_class"]["relationship_type"] == "inferred_enclosing_class"

    # 2. Sibling methods
    sibling_names = [s["name"] for s in ctx["same_file_siblings"]]
    assert "deleteUser" in sibling_names

    # 3. Imports
    assert "java.util.List" in ctx["imports"]["items"]
    assert ctx["imports"]["relationship_type"] == "directly_declared_imports"

    # 4. Resolved cross-file reference
    refs = ctx["resolved_symbol_references"]
    assert any(r["symbol"] == "DatabaseClient" and r["target_file"] == "db/DatabaseClient.java" for r in refs)
    assert refs[0]["relationship_type"] == "verified_symbol_definition"
