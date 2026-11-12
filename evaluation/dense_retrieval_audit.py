import os
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import torch

from dataset_pipeline.common import DATA, stream_read
from retrieval.bm25_index import BM25Retriever
from retrieval.dense_index import DenseRetriever
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.symbol_matcher import rerank_and_classify_candidates


def run_dense_audit_experiments(eval_qa_path: Optional[Path] = None, max_queries: int = 50) -> Dict[str, Any]:
    """Execute Phase 5D controlled retrieval audit comparing:
    1. BM25 baseline
    2. Existing custom encoder
    3. Context-enriched custom encoder
    4. Hybrid RRF
    5. Hybrid retrieval with exact-symbol reranking
    """
    bm25_path = DATA / "indexes" / "bm25_index.pkl"
    dense_path = DATA / "indexes" / "dense_store"

    bm25 = BM25Retriever(bm25_path)
    dense = DenseRetriever(store_dir=dense_path)
    hybrid = HybridRetriever(bm25, dense)

    # Load evaluation queries
    if not eval_qa_path or not eval_qa_path.exists():
        eval_qa_path = DATA / "review" / "qa_review.jsonl"
        if not eval_qa_path.exists() or len(list(stream_read(eval_qa_path))) < 5:
            eval_qa_path = DATA / "qa" / "qa_candidates.jsonl"

    all_queries = list(stream_read(eval_qa_path))
    eval_queries = [q for q in all_queries if q.get("relevant_chunk_ids")][:max_queries]

    if not eval_queries:
        print("[WARN] No evaluation queries with ground truth found. Using synthetic probe.")
        return {}

    print(f"Running Phase 5D retrieval audit on {len(eval_queries)} queries...")

    # Method 1: BM25 Baseline
    bm25_r1, bm25_r5, bm25_r10, bm25_rr = _evaluate_fn(lambda q, k: bm25.search(q, top_k=k), eval_queries)

    # Method 2: Existing Custom Encoder (Dense)
    dense_r1, dense_r5, dense_r10, dense_rr = _evaluate_fn(lambda q, k: dense.search(q, top_k=k), eval_queries)

    # Method 3: Improved Custom Encoder (context query format)
    def improved_dense_search(q: str, k: int):
        q_enriched = f"function method class {q}"
        return dense.search(q_enriched, top_k=k)
    imp_dense_r1, imp_dense_r5, imp_dense_r10, imp_dense_rr = _evaluate_fn(improved_dense_search, eval_queries)

    # Method 4: Standard Hybrid RRF (without symbol boost)
    def standard_hybrid_search(q: str, k: int):
        # Disable exact symbol boost to measure pure RRF
        bm25_res = bm25.search(q, top_k=max(k*3, 20))
        dense_res = dense.search(q, top_k=max(k*3, 20))
        scores = {}
        meta_map = {}
        for r in bm25_res:
            scores[r["chunk_id"]] = scores.get(r["chunk_id"], 0.0) + (1.0 / (60 + r["rank"]))
            meta_map[r["chunk_id"]] = r
        for r in dense_res:
            scores[r["chunk_id"]] = scores.get(r["chunk_id"], 0.0) + (1.0 / (60 + r["rank"]))
            if r["chunk_id"] not in meta_map:
                meta_map[r["chunk_id"]] = r
        sorted_cids = sorted(scores.keys(), key=lambda c: scores[c], reverse=True)
        return [meta_map[c] for c in sorted_cids[:k]]
    hyb_r1, hyb_r5, hyb_r10, hyb_rr = _evaluate_fn(standard_hybrid_search, eval_queries)

    # Method 5: Hybrid RRF + Exact Symbol Reranking (Phase 4A & 5)
    sym_hyb_r1, sym_hyb_r5, sym_hyb_r10, sym_hyb_rr = _evaluate_fn(lambda q, k: hybrid.search(q, top_k=k, mode="hybrid"), eval_queries)

    results = {
        "query_count": len(eval_queries),
        "methods": {
            "bm25_baseline": {
                "recall@1": round(bm25_r1, 4),
                "recall@5": round(bm25_r5, 4),
                "recall@10": round(bm25_r10, 4),
                "mrr": round(bm25_rr, 4)
            },
            "custom_dense_existing": {
                "recall@1": round(dense_r1, 4),
                "recall@5": round(dense_r5, 4),
                "recall@10": round(dense_r10, 4),
                "mrr": round(dense_rr, 4)
            },
            "custom_dense_improved": {
                "recall@1": round(imp_dense_r1, 4),
                "recall@5": round(imp_dense_r5, 4),
                "recall@10": round(imp_dense_r10, 4),
                "mrr": round(imp_dense_rr, 4)
            },
            "hybrid_rrf_standard": {
                "recall@1": round(hyb_r1, 4),
                "recall@5": round(hyb_r5, 4),
                "recall@10": round(hyb_r10, 4),
                "mrr": round(hyb_rr, 4)
            },
            "hybrid_rrf_symbol_boosted": {
                "recall@1": round(sym_hyb_r1, 4),
                "recall@5": round(sym_hyb_r5, 4),
                "recall@10": round(sym_hyb_r10, 4),
                "mrr": round(sym_hyb_rr, 4)
            }
        }
    }

    report_path = DATA / "reports" / "dense_retrieval_audit_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Audit report saved to {report_path}")
    return results


def _evaluate_fn(search_fn, queries: List[Dict[str, Any]], top_k: int = 10):
    r1, r5, r10 = 0, 0, 0
    reciprocal_ranks = []
    n = len(queries)

    for q in queries:
        target_ids = set(q.get("relevant_chunk_ids", []))
        if not target_ids:
            continue
        try:
            results = search_fn(q["question"], top_k)
            retrieved_ids = [r["chunk_id"] for r in results]
            hit_rank = None
            for idx, cid in enumerate(retrieved_ids, 1):
                if cid in target_ids:
                    hit_rank = idx
                    break

            if hit_rank:
                if hit_rank == 1:
                    r1 += 1
                if hit_rank <= 5:
                    r5 += 1
                if hit_rank <= 10:
                    r10 += 1
                reciprocal_ranks.append(1.0 / hit_rank)
            else:
                reciprocal_ranks.append(0.0)
        except Exception:
            reciprocal_ranks.append(0.0)

    mrr = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0
    return (r1 / n, r5 / n, r10 / n, mrr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=int, default=50)
    args = parser.parse_args()
    res = run_dense_audit_experiments(max_queries=args.queries)
    print(json.dumps(res, indent=2))
