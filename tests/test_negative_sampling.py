import json
import random
import pytest
from pathlib import Path

from dataset_pipeline.generate_negatives import NegativeSamplerIndex, tokenize_name


def test_tokenize_name():
    tokens = tokenize_name("test_validate_format_error")
    assert "test" in tokens
    assert "validate" in tokens
    assert "format" in tokens
    assert "error" in tokens

    camel_tokens = tokenize_name("AbstractDatabaseConnectorFactory")
    assert "abstract" in camel_tokens
    assert "database" in camel_tokens
    assert "connector" in camel_tokens
    assert "factory" in camel_tokens


def test_negative_sampler_index(tmp_path):
    chunks_path = tmp_path / "test_chunks.jsonl"
    chunks = [
        {
            "chunk_id": "c1", "repo_id": "repoA", "language": "python",
            "file_path": "auth/login.py", "chunk_name": "authenticate_user",
            "chunk_type": "FunctionDef", "code_text": "def authenticate_user(): pass",
            "split": "train"
        },
        {
            "chunk_id": "c2", "repo_id": "repoA", "language": "python",
            "file_path": "db/connect.py", "chunk_name": "database_connect",
            "chunk_type": "FunctionDef", "code_text": "def database_connect(): pass",
            "split": "train"
        },
        {
            "chunk_id": "c3", "repo_id": "repoB", "language": "python",
            "file_path": "models/user.py", "chunk_name": "user_model_authenticate",
            "chunk_type": "FunctionDef", "code_text": "def user_model_authenticate(): pass",
            "split": "train"
        },
        {
            "chunk_id": "c4", "repo_id": "repoC", "language": "java",
            "file_path": "App.java", "chunk_name": "main",
            "chunk_type": "method_declaration", "code_text": "void main() {}",
            "split": "train"
        }
    ]
    with chunks_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")

    index = NegativeSamplerIndex(chunks_path)
    assert len(index.chunks_meta) == 4

    rng = random.Random(42)

    # 1. Same repo hard negative
    res = index.sample_negative("c1", "repoA", "python", "same_repo_hard_negative", rng, target_split="train")
    assert res is not None
    neg_meta, method = res
    assert neg_meta["chunk_id"] == "c2"
    assert neg_meta["repo_id"] == "repoA"

    # 2. Same language different repo
    res2 = index.sample_negative("c1", "repoA", "python", "same_language_different_repo", rng, target_split="train")
    assert res2 is not None
    neg_meta2, _ = res2
    assert neg_meta2["chunk_id"] == "c3"
    assert neg_meta2["repo_id"] == "repoB"

    # 3. Negative must not equal positive
    for _ in range(5):
        res_rnd = index.sample_negative("c1", "repoA", "python", "random", rng)
        assert res_rnd is not None
        neg_m, _ = res_rnd
        assert neg_m["chunk_id"] != "c1"
