import pytest
from unittest.mock import MagicMock

from retrieval.answer_engine import AnswerEngine
from retrieval.evidence_builder import EvidenceBuilder


def test_evidence_builder_formatting():
    chunk = {
        "chunk_id": "c1",
        "repo_id": "pallets__werkzeug",
        "file_path": "src/werkzeug/routing.py",
        "start_line": 50,
        "end_line": 85,
        "chunk_name": "Map",
        "chunk_type": "ClassDef",
        "score": 0.045,
        "code_snippet": "class Map:\n    pass"
    }
    expanded = {
        "parent_class": None,
        "imports": {"items": ["typing.Optional"]},
        "same_file_siblings": [{"name": "Rule"}]
    }

    item = EvidenceBuilder.build_evidence_item(chunk, expanded)
    assert item["citation"] == "pallets__werkzeug:src/werkzeug/routing.py#L50-L85"
    assert item["file_path"] == "src/werkzeug/routing.py"
    assert item["start_line"] == 50
    assert item["end_line"] == 85
    assert item["chunk_name"] == "Map"

    md = EvidenceBuilder.format_citations_markdown([item])
    assert "pallets__werkzeug" in md
    assert "routing.py" in md
    assert "Lines 50–85" in md


def test_answer_engine_grounded_answer():
    mock_retriever = MagicMock()
    mock_expander = MagicMock()

    mock_retriever.search.return_value = [
        {
            "chunk_id": "c100",
            "repo_id": "google__gson",
            "file_path": "gson/src/main/java/com/google/gson/Gson.java",
            "start_line": 100,
            "end_line": 150,
            "chunk_name": "fromJson",
            "chunk_type": "method_declaration",
            "score": 0.035,
            "code_snippet": "public <T> T fromJson(String json, Class<T> classOfT) {}"
        }
    ]
    mock_expander.expand_context.return_value = {
        "parent_class": {"class_name": "Gson"},
        "imports": {"items": ["java.io.Reader"]},
        "same_file_siblings": []
    }

    engine = AnswerEngine(mock_retriever, mock_expander)
    result = engine.answer_question("Where is the fromJson method implemented?")

    assert result["is_answered"] is True
    assert "google__gson" in result["answer"]
    assert "Gson.java" in result["answer"]
    assert "100–150" in result["answer"]
    assert len(result["citations"]) == 1
    assert "fromJson" in result["answer"]


def test_answer_engine_unanswerable_handling():
    mock_retriever = MagicMock()
    mock_expander = MagicMock()

    # Returns empty or low score
    mock_retriever.search.return_value = []

    engine = AnswerEngine(mock_retriever, mock_expander)
    result = engine.answer_question("What is the quantum encryption protocol?")

    assert result["is_answered"] is False
    assert result["confidence_indicator"] == "insufficient_evidence"
    assert "Insufficient evidence" in result["answer"]
    assert len(result["evidence"]) == 0
