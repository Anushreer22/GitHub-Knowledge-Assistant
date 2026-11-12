import random
import re
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple, Iterator

from .common import DATA, stream_read, stream_write, sid


def tokenize_name(name: str) -> List[str]:
    """Break camelCase or snake_case identifiers into lowercase word tokens."""
    # Split on underscores and camelCase boundaries
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+", name)
    return [p.lower() for p in parts if len(p) >= 3]


class NegativeSamplerIndex:
    """Lightweight in-memory indexing of 200k+ chunks for fast negative sampling."""

    def __init__(self, chunks_path: Path):
        self.chunks_meta: List[Dict[str, Any]] = []
        self.id_to_idx: Dict[str, int] = {}
        self.by_repo: Dict[str, List[int]] = defaultdict(list)
        self.by_lang: Dict[str, List[int]] = defaultdict(list)
        self.by_file: Dict[Tuple[str, str], List[int]] = defaultdict(list)
        self.by_token: Dict[str, List[int]] = defaultdict(list)
        self.by_split: Dict[str, List[int]] = defaultdict(list)

        print(f"Indexing chunks metadata from {chunks_path}...")
        for idx, c in enumerate(stream_read(chunks_path)):
            cid = c["chunk_id"]
            repo = c["repo_id"]
            lang = c.get("language", "unknown").lower()
            fpath = c.get("file_path", "")
            name = c.get("chunk_name", "")
            split = c.get("split")

            meta = {
                "chunk_id": cid,
                "repo_id": repo,
                "language": lang,
                "file_path": fpath,
                "chunk_name": name,
                "chunk_type": c.get("chunk_type", ""),
                "split": split
            }
            self.chunks_meta.append(meta)
            self.id_to_idx[cid] = idx
            self.by_repo[repo].append(idx)
            self.by_lang[lang].append(idx)
            self.by_file[(repo, fpath)].append(idx)
            if split:
                self.by_split[split].append(idx)

            for tok in tokenize_name(name):
                # Cap token list size to keep indexing lightweight
                if len(self.by_token[tok]) < 200:
                    self.by_token[tok].append(idx)

        print(f"Indexed {len(self.chunks_meta)} chunks across {len(self.by_repo)} repositories.")

    def sample_negative(
        self,
        pos_id: str,
        pos_repo: str,
        pos_lang: str,
        strategy: str,
        rng: random.Random,
        target_split: Optional[str] = None
    ) -> Optional[Tuple[Dict[str, Any], str]]:
        """Sample a negative chunk matching the chosen strategy."""
        pos_idx = self.id_to_idx.get(pos_id)
        if pos_idx is None:
            return None

        pos_meta = self.chunks_meta[pos_idx]
        pos_file = pos_meta["file_path"]
        pos_name = pos_meta["chunk_name"]

        chosen_idx = None
        method = strategy

        if strategy == "random":
            # 1. Random negative across valid pool
            pool = self.by_split[target_split] if target_split and target_split in self.by_split else range(len(self.chunks_meta))
            if len(pool) > 1:
                for _ in range(10):
                    cand = rng.choice(pool)
                    if cand != pos_idx:
                        chosen_idx = cand
                        break

        elif strategy == "same_language_different_repo":
            # 2. Same language, different repo
            pool = self.by_lang.get(pos_lang, [])
            candidates = [i for i in pool if self.chunks_meta[i]["repo_id"] != pos_repo]
            if target_split:
                candidates = [i for i in candidates if self.chunks_meta[i]["split"] == target_split]
            if candidates:
                chosen_idx = rng.choice(candidates)

        elif strategy == "same_repo_hard_negative":
            # 3. Same repository, different file
            pool = self.by_repo.get(pos_repo, [])
            candidates = [i for i in pool if self.chunks_meta[i]["file_path"] != pos_file]
            if target_split:
                candidates = [i for i in candidates if self.chunks_meta[i]["split"] == target_split]
            if candidates:
                chosen_idx = rng.choice(candidates)

        elif strategy == "similar_name_different_purpose":
            # 4. Similar name tokens, but different chunk and function
            tokens = tokenize_name(pos_name)
            candidates = []
            for tok in tokens:
                for cand_idx in self.by_token.get(tok, []):
                    if cand_idx != pos_idx and self.chunks_meta[cand_idx]["chunk_name"] != pos_name:
                        candidates.append(cand_idx)
            if target_split:
                candidates = [i for i in candidates if self.chunks_meta[i]["split"] == target_split]
            if candidates:
                chosen_idx = rng.choice(candidates)
            else:
                # Fallback to same repo hard negative if no similar name exists
                return self.sample_negative(pos_id, pos_repo, pos_lang, "same_repo_hard_negative", rng, target_split)

        elif strategy == "different_function_same_file":
            # 5. Different function in same file
            file_pool = self.by_file.get((pos_repo, pos_file), [])
            candidates = [i for i in file_pool if i != pos_idx]
            if candidates:
                chosen_idx = rng.choice(candidates)
            else:
                # Fallback to same repo hard negative if only 1 chunk in file
                return self.sample_negative(pos_id, pos_repo, pos_lang, "same_repo_hard_negative", rng, target_split)

        if chosen_idx is not None:
            neg_meta = self.chunks_meta[chosen_idx]
            # Safety check: Prevent leakage of validation or test data into training
            if target_split and neg_meta.get("split") and neg_meta["split"] != target_split:
                return None
            return neg_meta, method

        return None


def generate_negatives_stream(
    qa_path: Path,
    index: NegativeSamplerIndex,
    negatives_per_qa: int = 2,
    limit: Optional[int] = None,
    seed: int = 42
) -> Iterator[Dict[str, Any]]:
    """Generate negative pairs for QA records."""
    rng = random.Random(seed)
    strategies = [
        "same_repo_hard_negative",
        "similar_name_different_purpose",
        "same_language_different_repo",
        "different_function_same_file",
        "random"
    ]

    count = 0
    for qa in stream_read(qa_path):
        rel_chunks = qa.get("relevant_chunk_ids", [])
        if not rel_chunks:
            continue
        pos_id = rel_chunks[0]
        pos_idx = index.id_to_idx.get(pos_id)
        if pos_idx is None:
            continue

        pos_meta = index.chunks_meta[pos_idx]
        pos_lang = pos_meta["language"]
        pos_repo = pos_meta["repo_id"]
        split = qa.get("split")

        # Pick distinct strategies for this QA
        selected_strategies = rng.sample(strategies, min(negatives_per_qa, len(strategies)))
        for strat in selected_strategies:
            res = index.sample_negative(
                pos_id=pos_id,
                pos_repo=pos_repo,
                pos_lang=pos_lang,
                strategy=strat,
                rng=rng,
                target_split=split
            )
            if res:
                neg_meta, actual_method = res
                neg_record = {
                    "schema_version": "1.0",
                    "pair_id": f"neg_{sid(qa['question_id'], neg_meta['chunk_id'], actual_method)}",
                    "question_id": qa["question_id"],
                    "repo_id": qa["repo_id"],
                    "question": qa["question"],
                    "positive_chunk_id": pos_id,
                    "negative_chunk_id": neg_meta["chunk_id"],
                    "negative_repo_id": neg_meta["repo_id"],
                    "negative_file_path": neg_meta["file_path"],
                    "negative_chunk_name": neg_meta["chunk_name"],
                    "negative_generation_method": actual_method,
                    "label_status": "candidate_needs_review",
                    "split": split
                }
                yield neg_record
                count += 1
                if limit and count >= limit:
                    return


def main():
    parser = argparse.ArgumentParser(description="Generate negative samples for contrastive training.")
    parser.add_argument("--qa-path", type=str, default=str(DATA / "qa" / "qa_candidates.jsonl"), help="Path to QA pairs")
    parser.add_argument("--chunks-path", type=str, default=str(DATA / "processed" / "code_chunks.jsonl"), help="Path to code chunks")
    parser.add_argument("--output", type=str, default=str(DATA / "qa" / "hard_negative_candidates.jsonl"), help="Output negatives path")
    parser.add_argument("--negatives-per-qa", type=int, default=2, help="Number of negatives per QA record")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on total negative pairs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    qa_path = Path(args.qa_path)
    chunks_path = Path(args.chunks_path)
    output_path = Path(args.output)

    if not qa_path.exists():
        raise SystemExit(f"QA file not found: {qa_path}")
    if not chunks_path.exists():
        raise SystemExit(f"Chunks file not found: {chunks_path}")

    index = NegativeSamplerIndex(chunks_path)
    print(f"Generating negatives from {qa_path} into {output_path}...")
    written = stream_write(
        output_path,
        generate_negatives_stream(
            qa_path=qa_path,
            index=index,
            negatives_per_qa=args.negatives_per_qa,
            limit=args.limit,
            seed=args.seed
        )
    )
    print(f"Generated {written} negative candidates saved to {output_path}")


if __name__ == "__main__":
    main()
