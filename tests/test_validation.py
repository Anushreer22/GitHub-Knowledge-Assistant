import json
import pytest
from pathlib import Path

from dataset_pipeline.validate_dataset import validate_dataset


def test_validate_dataset_on_valid_data(tmp_path):
    chunks_path = tmp_path / "code_chunks.jsonl"
    qa_path = tmp_path / "qa_candidates.jsonl"
    reports_dir = tmp_path / "reports"

    chunk = {
        "repo_id": "test_repo",
        "commit_sha": "abc1234",
        "file_path": "main.py",
        "language": "python",
        "chunk_id": "c_valid_1",
        "chunk_type": "FunctionDef",
        "chunk_name": "run",
        "code_text": "def run():\n    return 42",
        "start_line": 1,
        "end_line": 2,
        "imports": [],
        "symbols_defined": ["run"],
        "symbols_used": [],
        "parser_status": "python_ast"
    }

    qa = {
        "question_id": "q_valid_1",
        "repo_id": "test_repo",
        "question": "Where is the run function implemented?",
        "expected_answer": "In main.py at line 1.",
        "relevant_chunk_ids": ["c_valid_1"],
        "relevant_files": ["main.py"],
        "difficulty": "easy",
        "answerable": True,
        "generation_method": "function_method_identification",
        "review_status": "pending",
        "source_chunk_id": "c_valid_1",
        "split": None
    }

    chunks_path.write_text(json.dumps(chunk) + "\n", encoding="utf-8")
    qa_path.write_text(json.dumps(qa) + "\n", encoding="utf-8")

    report = validate_dataset(chunks_path=chunks_path, qa_path=qa_path)
    assert report["status"] == "PASS"
    assert report["chunk_validation"]["total_chunks"] == 1
    assert report["qa_validation"]["total_qa"] == 1
    assert len(report["structural_errors"]) == 0


def test_validate_dataset_detects_unknown_chunk_ref(tmp_path):
    chunks_path = tmp_path / "code_chunks.jsonl"
    qa_path = tmp_path / "qa_candidates.jsonl"

    chunk = {
        "repo_id": "test_repo", "commit_sha": "abc1234", "file_path": "main.py",
        "language": "python", "chunk_id": "c1", "chunk_type": "FunctionDef",
        "chunk_name": "run", "code_text": "def run(): pass", "start_line": 1,
        "end_line": 2, "imports": [], "symbols_defined": ["run"], "symbols_used": [],
        "parser_status": "python_ast"
    }

    qa = {
        "question_id": "q1", "repo_id": "test_repo", "question": "Where?",
        "expected_answer": "Nowhere", "relevant_chunk_ids": ["non_existent_chunk"],
        "relevant_files": ["main.py"], "difficulty": "easy", "answerable": True,
        "generation_method": "manual", "review_status": "pending",
        "source_chunk_id": "non_existent_chunk", "split": None
    }

    chunks_path.write_text(json.dumps(chunk) + "\n", encoding="utf-8")
    qa_path.write_text(json.dumps(qa) + "\n", encoding="utf-8")

    report = validate_dataset(chunks_path=chunks_path, qa_path=qa_path)
    assert report["status"] == "FAIL"
    assert any("references unknown chunk_id 'non_existent_chunk'" in e for e in report["structural_errors"])
