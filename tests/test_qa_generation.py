import pytest
from dataset_pipeline.generate_qa import generate_candidates_for_chunk, extract_python_details, extract_java_details, detect_design_pattern


def test_python_details_extraction():
    code = """
def calculate_metrics(values: list, scale: float = 1.0) -> dict:
    \"\"\"Compute summary metrics.\"\"\"
    try:
        return {"mean": sum(values) / len(values) * scale}
    except ZeroDivisionError as e:
        raise ValueError("empty values")
"""
    details = extract_python_details(code, "calculate_metrics")
    assert "values" in details["params"]
    assert "scale" in details["params"]
    assert "ValueError" in details["raises"]
    assert "ZeroDivisionError" in details["catches"]


def test_java_details_extraction():
    code = """
public User findUser(int id, String tenant) throws UserNotFoundException {
    try {
        return db.query(id);
    } catch (SQLException e) {
        throw new UserNotFoundException(e);
    }
}
"""
    details = extract_java_details(code, "findUser")
    assert details["returns"] == "User"
    assert any("int id" in p for p in details["params"])
    assert "UserNotFoundException" in details["throws"]
    assert "SQLException" in details["catches"]


def test_detect_design_pattern():
    assert detect_design_pattern("com/patterns/factory/CarFactory.java", "CarFactory", "class CarFactory") == "Factory"
    assert detect_design_pattern("com/patterns/singleton/AppConfig.java", "AppConfig", "private static AppConfig instance") == "Singleton"
    assert detect_design_pattern("utils/helpers.py", "parse_data", "def parse_data(): pass") is None


def test_generate_candidates_for_chunk():
    chunk = {
        "repo_id": "test_repo",
        "commit_sha": "abc1234",
        "file_path": "services/UserService.java",
        "language": "java",
        "chunk_id": "chunk_java_1",
        "chunk_type": "method_declaration",
        "chunk_name": "findUser",
        "code_text": "public User findUser(int id) throws UserNotFoundException { return null; }",
        "start_line": 10,
        "end_line": 20,
        "imports": ["java.util.List", "com.example.User"],
        "symbols_defined": ["findUser"],
        "symbols_used": ["User", "id"],
        "parser_status": "tree_sitter_java"
    }

    candidates = generate_candidates_for_chunk(chunk, max_per_chunk=3)
    assert len(candidates) >= 1

    for c in candidates:
        assert c["repo_id"] == "test_repo"
        assert c["source_chunk_id"] == "chunk_java_1"
        assert "relevant_chunk_ids" in c
        assert c["relevant_chunk_ids"] == ["chunk_java_1"]
        assert c["relevant_files"] == ["services/UserService.java"]
        assert c["review_status"] == "pending"
        assert c["expected_answer"] is not None
        assert "findUser" in c["question"] or "services/UserService.java" in c["expected_answer"]
