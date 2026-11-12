import json
import pytest
from pathlib import Path

from training.train_tokenizer import train_code_tokenizer
from tokenizers import Tokenizer


def test_train_tokenizer(tmp_path):
    train_chunks = tmp_path / "train_chunks.jsonl"
    out_dir = tmp_path / "tokenizer"

    snippets = [
        "public class UserService { public User findUser(int id) { return null; } }",
        "def calculate_total(items: list, tax: float = 0.05) -> float:\n    return sum(items) * (1 + tax)",
        "import os\nimport sys\nfrom pathlib import Path\ndef main(): pass",
        "try { runTask(); } catch (TaskExecutionException e) { logger.error(e); }"
    ]

    with train_chunks.open("w", encoding="utf-8") as f:
        for idx, text in enumerate(snippets):
            f.write(json.dumps({
                "chunk_id": f"c_{idx}",
                "repo_id": "test_repo",
                "code_text": text
            }) + "\n")

    tokenizer = train_code_tokenizer(train_chunks, out_dir, vocab_size=200, min_frequency=1)
    assert tokenizer is not None
    assert (out_dir / "tokenizer.json").exists()
    assert (out_dir / "tokenizer_config.json").exists()

    # Test encoding / decoding
    test_code = "def findUser(id): return id"
    encoding = tokenizer.encode(test_code)
    assert len(encoding.ids) > 0
    decoded = tokenizer.decode(encoding.ids)
    assert "findUser" in decoded or "id" in decoded
