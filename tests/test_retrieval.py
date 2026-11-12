import json
import pytest
from pathlib import Path

from training.evaluate_retrieval import evaluate_retrieval
from training.model import CodeEncoder, CodeEncoderConfig
from training.train_tokenizer import train_code_tokenizer


def test_evaluate_retrieval_synthetic(tmp_path):
    train_chunks_file = tmp_path / "corpus.jsonl"
    tok_dir = tmp_path / "tok"

    corpus = [
        {"chunk_id": "c1", "repo_id": "r1", "code_text": "def calculate_sum(a, b): return a + b"},
        {"chunk_id": "c2", "repo_id": "r1", "code_text": "def multiply(a, b): return a * b"},
        {"chunk_id": "c3", "repo_id": "r1", "code_text": "class DatabaseConnection: pass"}
    ]
    with train_chunks_file.open("w", encoding="utf-8") as f:
        for c in corpus:
            f.write(json.dumps(c) + "\n")

    tokenizer = train_code_tokenizer(train_chunks_file, tok_dir, vocab_size=100, min_frequency=1)

    config = CodeEncoderConfig(
        vocab_size=tokenizer.get_vocab_size(),
        hidden_dim=32,
        num_layers=1,
        num_heads=2,
        ff_dim=64,
        max_seq_len=32,
        pad_token_id=tokenizer.token_to_id("<pad>") or 0
    )
    model = CodeEncoder(config)

    qa_records = [
        {"question_id": "q1", "question": "calculate_sum", "relevant_chunk_ids": ["c1"]},
        {"question_id": "q2", "question": "multiply", "relevant_chunk_ids": ["c2"]}
    ]

    metrics = evaluate_retrieval(
        model=model,
        tokenizer=tokenizer,
        qa_records=qa_records,
        corpus_chunks=corpus,
        batch_size=2,
        device="cpu",
        max_seq_len=32
    )

    assert "recall@1" in metrics
    assert "recall@5" in metrics
    assert "recall@10" in metrics
    assert "mrr" in metrics
    assert metrics["eval_count"] == 2
    assert 0.0 <= metrics["mrr"] <= 1.0
