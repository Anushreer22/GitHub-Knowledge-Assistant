import json
import argparse
from pathlib import Path
from typing import Iterator

from tokenizers import Tokenizer, models, pre_tokenizers, trainers, decoders, processors
from dataset_pipeline.common import DATA, stream_read


def get_training_code_corpus(train_chunks_path: Path, max_lines: int = 50000) -> Iterator[str]:
    """Stream code snippets from training chunks ONLY to avoid test leakage."""
    count = 0
    for chunk in stream_read(train_chunks_path):
        code = chunk.get("code_text", "")
        if code and code.strip():
            yield code
            count += 1
            if count >= max_lines:
                break


def train_code_tokenizer(
    train_chunks_path: Path,
    output_dir: Path,
    vocab_size: int = 16000,
    min_frequency: int = 2
) -> Tokenizer:
    """Train a code-aware Byte-Level BPE tokenizer on training chunks only."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Initializing Byte-Level BPE tokenizer (vocab_size={vocab_size})...")
    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()

    special_tokens = ["<pad>", "<s>", "</s>", "<unk>", "<mask>"]

    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=special_tokens,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet()
    )

    print(f"Training tokenizer on corpus from {train_chunks_path}...")
    corpus = list(get_training_code_corpus(train_chunks_path))
    if not corpus:
        raise ValueError(f"No code chunks found in {train_chunks_path} to train tokenizer!")

    print(f"Collected {len(corpus)} training snippets. Running BPE trainer...")
    tokenizer.train_from_iterator(corpus, trainer=trainer)

    # Post-processor to handle <s> and </s>
    tokenizer.post_processor = processors.ByteLevel(trim_offsets=False)

    # Save tokenizer artifacts
    tokenizer_json_path = output_dir / "tokenizer.json"
    tokenizer.save(str(tokenizer_json_path))

    # Save tokenizer configuration metadata
    meta = {
        "tokenizer_type": "ByteLevelBPE",
        "vocab_size": tokenizer.get_vocab_size(),
        "special_tokens": special_tokens,
        "pad_token": "<pad>",
        "pad_token_id": tokenizer.token_to_id("<pad>"),
        "bos_token": "<s>",
        "bos_token_id": tokenizer.token_to_id("<s>"),
        "eos_token": "</s>",
        "eos_token_id": tokenizer.token_to_id("</s>"),
        "unk_token": "<unk>",
        "unk_token_id": tokenizer.token_to_id("<unk>"),
        "trained_on": str(train_chunks_path),
        "leakage_safe": True
    }
    (output_dir / "tokenizer_config.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Tokenizer saved successfully to {output_dir}")
    print(f"Vocabulary size: {tokenizer.get_vocab_size()}")
    return tokenizer


def main():
    parser = argparse.ArgumentParser(description="Train custom code tokenizer on training split only.")
    parser.add_argument("--train-chunks", type=str, default=str(DATA / "splits" / "train_chunks.jsonl"), help="Training split chunks")
    parser.add_argument("--output-dir", type=str, default="models/tokenizer", help="Directory to save tokenizer")
    parser.add_argument("--vocab-size", type=int, default=16000, help="Vocabulary size")
    parser.add_argument("--min-frequency", type=int, default=2, help="Min token frequency")
    args = parser.parse_args()

    train_path = Path(args.train_chunks)
    out_dir = Path(args.output_dir)

    if not train_path.exists() or train_path.stat().st_size == 0:
        raise SystemExit(
            f"Training chunks file missing or empty: {train_path}\n"
            "Please run 'python -m dataset_pipeline.split_dataset' first to generate repository-safe splits."
        )

    train_code_tokenizer(
        train_chunks_path=train_path,
        output_dir=out_dir,
        vocab_size=args.vocab_size,
        min_frequency=args.min_frequency
    )


if __name__ == "__main__":
    main()
