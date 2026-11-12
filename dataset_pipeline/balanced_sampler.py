import json
import random
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Iterator, Optional, Tuple

from .common import DATA, stream_read, stream_write


class LanguageBalancedSampler:
    """Configurable language-aware sampling to address extreme dataset imbalance
    (e.g., 213k Java vs 2.9k Python) without discarding the raw dataset.
    """

    def __init__(self, items: List[Dict[str, Any]], language_key: str = "language", seed: int = 42):
        self.language_key = language_key
        self.seed = seed
        self.rng = random.Random(seed)
        self.by_lang: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for item in items:
            lang = item.get(language_key, "unknown").lower()
            self.by_lang[lang].append(item)

    @classmethod
    def from_jsonl(cls, path: Path, language_key: str = "language", seed: int = 42) -> "LanguageBalancedSampler":
        """Instantiate sampler from a JSONL file."""
        items = list(stream_read(path))
        return cls(items, language_key=language_key, seed=seed)

    def get_distribution(self) -> Dict[str, int]:
        """Return raw item counts per language."""
        return {lang: len(records) for lang, records in self.by_lang.items()}

    def sample_balanced_subset(
        self,
        max_per_lang: Optional[int] = None,
        exact_balance: bool = False
    ) -> List[Dict[str, Any]]:
        """Return a sampled subset with balanced or capped representation per language.
        Avoids duplicates within each language pool.
        """
        sampled: List[Dict[str, Any]] = []
        counts = self.get_distribution()

        # If exact balance requested, use minimum count across available languages
        target_count = min(counts.values()) if exact_balance and counts else (max_per_lang or float("inf"))

        for lang, records in self.by_lang.items():
            pool = list(records)
            self.rng.shuffle(pool)

            k = min(len(pool), int(target_count) if target_count != float("inf") else (max_per_lang or len(pool)))
            sampled.extend(pool[:k])

        # Shuffle the combined result reproducibly
        self.rng.shuffle(sampled)
        return sampled

    def stream_balanced_batches(
        self,
        batch_size: int = 32,
        max_batches: Optional[int] = None
    ) -> Iterator[List[Dict[str, Any]]]:
        """Generate training batches containing equal numbers of samples from each language."""
        languages = [l for l, pool in self.by_lang.items() if pool]
        if not languages:
            return

        per_lang_per_batch = max(1, batch_size // len(languages))

        # Copy and shuffle pools
        shuffled_pools = {
            lang: list(pool) for lang, pool in self.by_lang.items()
        }
        for pool in shuffled_pools.values():
            self.rng.shuffle(pool)

        indices = {lang: 0 for lang in languages}
        batches_yielded = 0

        while True:
            batch: List[Dict[str, Any]] = []

            for lang in languages:
                pool = shuffled_pools[lang]
                idx = indices[lang]

                for _ in range(per_lang_per_batch):
                    if idx >= len(pool):
                        # Reshuffle when pool exhausted
                        self.rng.shuffle(pool)
                        idx = 0
                    batch.append(pool[idx])
                    idx += 1

                indices[lang] = idx

            self.rng.shuffle(batch)
            yield batch
            batches_yielded += 1

            if max_batches and batches_yielded >= max_batches:
                break


def main():
    parser = argparse.ArgumentParser(description="Sample balanced dataset subsets across languages.")
    parser.add_argument("--input", type=str, default=str(DATA / "processed" / "code_chunks.jsonl"), help="Input chunks path")
    parser.add_argument("--output", type=str, default=str(DATA / "processed" / "code_chunks_balanced_sample.jsonl"), help="Output path")
    parser.add_argument("--max-per-lang", type=int, default=3000, help="Max samples per language")
    parser.add_argument("--exact-balance", action="store_true", help="Force strictly equal count per language")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    print(f"Reading chunks from {input_path}...")
    sampler = LanguageBalancedSampler.from_jsonl(input_path, seed=args.seed)
    raw_dist = sampler.get_distribution()
    print("Raw language distribution:", raw_dist)

    sampled = sampler.sample_balanced_subset(
        max_per_lang=args.max_per_lang,
        exact_balance=args.exact_balance
    )

    sampled_dist = defaultdict(int)
    for s in sampled:
        sampled_dist[s.get("language", "unknown")] += 1

    print(f"Sampled {len(sampled)} items. Sampled distribution:", dict(sampled_dist))
    stream_write(output_path, sampled)
    print(f"Wrote balanced sample to {output_path}")


if __name__ == "__main__":
    main()
