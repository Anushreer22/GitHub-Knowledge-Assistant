import json
import random
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Set, Optional

from .common import DATA, stream_read, stream_write


def partition_repositories(
    repos: List[str],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
    allow_small_splits: bool = False
) -> Dict[str, List[str]]:
    """Partition repository IDs into train, validation, and test sets.
    Ensures no repository occurs in multiple splits.
    """
    if len(repos) < 3:
        raise ValueError(
            f"Insufficient repositories ({len(repos)}). At least 3 repositories are strictly required "
            "to create non-empty train, validation, and test splits without repository leakage."
        )

    # Deterministic shuffle
    rng = random.Random(seed)
    shuffled = list(sorted(repos))
    rng.shuffle(shuffled)

    n_total = len(shuffled)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    n_test = n_total - n_train - n_val

    # Check for empty splits
    if (n_val == 0 or n_test == 0 or n_train == 0) and not allow_small_splits:
        raise ValueError(
            f"Limitation: {n_total} repositories cannot satisfy an {int(train_ratio*100)}/{int(val_ratio*100)}/{int((1-train_ratio-val_ratio)*100)} "
            f"split without producing empty sets (train: {n_train}, val: {n_val}, test: {n_test}). "
            f"At least 10 repositories are recommended for strict 80/10/10 splits. "
            f"To partition the current {n_total} repositories with at least 1 repository in each split, pass --allow-small-splits."
        )

    if allow_small_splits and (n_val == 0 or n_test == 0 or n_train == 0):
        # Guarantee at least 1 repository in test, 1 in validation, and rest in train
        n_test = max(1, n_test)
        n_val = max(1, n_val)
        n_train = n_total - n_test - n_val
        if n_train < 1:
            raise ValueError(f"Cannot allocate even 1 repository to train with {n_total} repos.")

    train_repos = sorted(shuffled[:n_train])
    val_repos = sorted(shuffled[n_train:n_train + n_val])
    test_repos = sorted(shuffled[n_train + n_val:])

    return {
        "train": train_repos,
        "validation": val_repos,
        "test": test_repos
    }


def split_dataset(
    chunks_path: Path,
    qa_path: Optional[Path],
    splits_dir: Path,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
    allow_small_splits: bool = False
) -> Dict[str, Any]:
    """Stream chunks and QA records into train/validation/test files according to repository partitions."""
    splits_dir.mkdir(parents=True, exist_ok=True)

    # 1. Discover all unique repository IDs from chunks
    repos_set: Set[str] = set()
    repo_lang_counter: Dict[str, Counter] = defaultdict(Counter)

    print(f"Scanning repository IDs in {chunks_path}...")
    for c in stream_read(chunks_path):
        rid = c["repo_id"]
        repos_set.add(rid)
        repo_lang_counter[rid][c.get("language", "unknown")] += 1

    all_repos = sorted(list(repos_set))
    print(f"Found {len(all_repos)} repositories: {all_repos}")

    # 2. Partition repositories
    split_repos = partition_repositories(
        repos=all_repos,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        seed=seed,
        allow_small_splits=allow_small_splits
    )

    repo_to_split: Dict[str, str] = {}
    for s_name, r_list in split_repos.items():
        for r in r_list:
            repo_to_split[r] = s_name

    print("\nRepository Split Assignment:")
    for s_name, r_list in split_repos.items():
        print(f"  {s_name.upper()} ({len(r_list)} repos): {r_list}")

    # 3. Stream write chunks into split files
    chunk_writers = {
        "train": (splits_dir / "train_chunks.jsonl").open("w", encoding="utf-8"),
        "validation": (splits_dir / "validation_chunks.jsonl").open("w", encoding="utf-8"),
        "test": (splits_dir / "test_chunks.jsonl").open("w", encoding="utf-8"),
    }

    chunk_counts = Counter()
    chunk_lang_counts: Dict[str, Counter] = defaultdict(Counter)

    try:
        print("\nStreaming chunks into split files...")
        for c in stream_read(chunks_path):
            target_split = repo_to_split.get(c["repo_id"])
            if target_split:
                c["split"] = target_split
                chunk_writers[target_split].write(json.dumps(c, ensure_ascii=False) + "\n")
                chunk_counts[target_split] += 1
                chunk_lang_counts[target_split][c.get("language", "unknown")] += 1
    finally:
        for f in chunk_writers.values():
            f.close()

    # 4. Stream write QA into split files
    qa_counts = Counter()
    if qa_path and qa_path.exists():
        qa_writers = {
            "train": (splits_dir / "train_qa.jsonl").open("w", encoding="utf-8"),
            "validation": (splits_dir / "validation_qa.jsonl").open("w", encoding="utf-8"),
            "test": (splits_dir / "test_qa.jsonl").open("w", encoding="utf-8"),
        }
        try:
            print("Streaming QA candidates into split files...")
            for q in stream_read(qa_path):
                target_split = repo_to_split.get(q["repo_id"])
                if target_split:
                    q["split"] = target_split
                    qa_writers[target_split].write(json.dumps(q, ensure_ascii=False) + "\n")
                    qa_counts[target_split] += 1
        finally:
            for f in qa_writers.values():
                f.close()

    # 5. Build summary and manifest
    summary = {
        "seed": seed,
        "strategy": "repository_level_split",
        "small_splits_allowed": allow_small_splits,
        "repository_partitions": split_repos,
        "repository_counts": {s: len(r) for s, r in split_repos.items()},
        "chunk_counts": dict(chunk_counts),
        "chunk_languages": {s: dict(c) for s, c in chunk_lang_counts.items()},
        "qa_counts": dict(qa_counts),
        "leakage_guarantee": "Strict: No repository overlaps across splits; all positive chunks belong to QA repository.",
        "limitations": [
            "Repository count is small (4 repositories). Standard 80/10/10 split requires 10+ repositories.",
            "Evaluation on validation/test evaluates out-of-repository generalization."
        ]
    }

    # Write summary files
    summary_path = splits_dir / "split_summary.json"
    manifest_path = splits_dir / "split_manifest.json"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Split dataset at repository level.")
    parser.add_argument("--chunks", type=str, default=str(DATA / "processed" / "code_chunks.jsonl"), help="Chunks file")
    parser.add_argument("--qa", type=str, default=str(DATA / "qa" / "qa_candidates.jsonl"), help="QA candidates file")
    parser.add_argument("--splits-dir", type=str, default=str(DATA / "splits"), help="Output directory for splits")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio (default 0.8)")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Val split ratio (default 0.1)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--allow-small-splits", action="store_true", help="Allow fallback partition for small repo counts")
    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    qa_path = Path(args.qa) if Path(args.qa).exists() else None
    splits_dir = Path(args.splits_dir)

    if not chunks_path.exists():
        raise SystemExit(f"Chunks file not found: {chunks_path}")

    summary = split_dataset(
        chunks_path=chunks_path,
        qa_path=qa_path,
        splits_dir=splits_dir,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
        allow_small_splits=args.allow_small_splits
    )

    print("\n--- DATASET SPLIT COMPLETE ---")
    print("Repository counts:", summary["repository_counts"])
    print("Chunk counts:", summary["chunk_counts"])
    print("QA counts:", summary["qa_counts"])
    print(f"Summary written to: {splits_dir / 'split_summary.json'}")


if __name__ == "__main__":
    main()
