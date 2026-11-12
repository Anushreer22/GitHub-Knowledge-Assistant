import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

from dataset_pipeline.common import DATA
from .bm25_index import BM25Retriever
from .dense_index import DenseRetriever
from .symbol_matcher import rerank_and_classify_candidates


class HybridRetriever:
    """Hybrid Retrieval Engine fusing BM25 lexical and dense semantic signals via Reciprocal Rank Fusion (RRF)
    with exact symbol matching and match classification.
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        dense_retriever: DenseRetriever,
        rrf_k: int = 60,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0
    ):
        self.bm25 = bm25_retriever
        self.dense = dense_retriever
        self.rrf_k = rrf_k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

    def search(
        self,
        query: str,
        top_k: int = 10,
        mode: str = "hybrid",
        repo_id: Optional[str] = None,
        min_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Retrieve code chunks using specified mode: 'bm25', 'dense', or 'hybrid'."""
        mode_clean = mode.lower().strip()
        fetch_k = max(top_k * 3, 30)

        if mode_clean == "bm25":
            raw_results = self.bm25.search(query=query, top_k=fetch_k, repo_id=repo_id)
            return rerank_and_classify_candidates(raw_results, query=query, top_k=top_k)

        if mode_clean == "dense":
            raw_results = self.dense.search(query=query, top_k=fetch_k, repo_id=repo_id)
            return rerank_and_classify_candidates(raw_results, query=query, top_k=top_k)

        # Hybrid RRF Fusion
        bm25_results = self.bm25.search(query=query, top_k=fetch_k, repo_id=repo_id)
        dense_results = self.dense.search(query=query, top_k=fetch_k, repo_id=repo_id)

        combined_scores: Dict[str, float] = {}
        metadata_map: Dict[str, Dict[str, Any]] = {}
        details_map: Dict[str, Dict[str, Any]] = {}

        # 1. Score BM25 candidates
        for r in bm25_results:
            cid = r["chunk_id"]
            rank = r["rank"]
            rrf_term = self.bm25_weight * (1.0 / (self.rrf_k + rank))
            combined_scores[cid] = combined_scores.get(cid, 0.0) + rrf_term
            metadata_map[cid] = r
            details_map[cid] = {
                "bm25_rank": rank,
                "bm25_score": r["score"],
                "dense_rank": None,
                "dense_score": None
            }

        # 2. Score Dense candidates
        for r in dense_results:
            cid = r["chunk_id"]
            rank = r["rank"]
            rrf_term = self.dense_weight * (1.0 / (self.rrf_k + rank))
            combined_scores[cid] = combined_scores.get(cid, 0.0) + rrf_term

            if cid not in metadata_map:
                metadata_map[cid] = r
                details_map[cid] = {
                    "bm25_rank": None,
                    "bm25_score": None,
                    "dense_rank": rank,
                    "dense_score": r["score"]
                }
            else:
                details_map[cid]["dense_rank"] = rank
                details_map[cid]["dense_score"] = r["score"]

        # 3. Sort by fused score
        sorted_cids = sorted(
            combined_scores.keys(),
            key=lambda cid: combined_scores[cid],
            reverse=True
        )

        fused_candidates = []
        rank = 1
        for cid in sorted_cids:
            score = combined_scores[cid]
            if score < min_threshold:
                continue

            item = dict(metadata_map[cid])
            item["score"] = round(score, 6)
            item["retrieval_method"] = "hybrid_rrf"
            item["rank"] = rank
            item["rrf_details"] = details_map[cid]
            fused_candidates.append(item)
            rank += 1

        # 4. Apply precision reranking and match classification
        return rerank_and_classify_candidates(fused_candidates, query=query, top_k=top_k)


def main():
    parser = argparse.ArgumentParser(description="Query using Hybrid Retrieval.")
    parser.add_argument("--query", type=str, required=True, help="Query string")
    parser.add_argument("--bm25-index", type=str, default=str(DATA / "indexes" / "bm25_index.pkl"), help="BM25 index path")
    parser.add_argument("--dense-dir", type=str, default=str(DATA / "indexes" / "dense_store"), help="Dense store dir")
    parser.add_argument("--mode", type=str, default="hybrid", choices=["hybrid", "bm25", "dense"], help="Retrieval mode")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    args = parser.parse_args()

    bm25 = BM25Retriever(Path(args.bm25_index))
    dense = DenseRetriever(store_dir=Path(args.dense_dir))
    retriever = HybridRetriever(bm25, dense)

    print(f"\nSearching '{args.query}' (Mode: {args.mode})...")
    results = retriever.search(query=args.query, top_k=args.top_k, mode=args.mode)
    for r in results:
        print(f"[{r['rank']}] [{r.get('match_classification', 'match')}] Score: {r['score']} | {r['repo_id']} | {r['file_path']}:{r['start_line']}-{r['end_line']} | {r['chunk_name']}")


if __name__ == "__main__":
    main()
