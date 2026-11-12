import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List

import numpy as np

from dataset_pipeline.common import DATA, stream_read
from retrieval.bm25_index import BM25Retriever
from retrieval.dense_index import DenseRetriever
from retrieval.hybrid_retriever import HybridRetriever


def evaluate_engine_on_queries(
    retriever_search_fn,
    queries: List[Dict[str, Any]],
    top_k: int = 10
) -> Dict[str, Any]:
    """Run search function on queries and compute Recall@1, 5, 10, MRR, Precision@5, and language splits."""
    r1, r5, r10 = 0, 0, 0
    reciprocal_ranks = []
    p5_scores = []
    lang_mrr = defaultdict(list)
    successful_examples = []
    failed_examples = []

    for q in queries:
        qtext = q.get("question", "")
        ground_truth = set(q.get("relevant_chunk_ids", []))
        if not ground_truth:
            continue

        lang = q.get("language") or ("python" if "python" in q.get("relevant_files", [""])[0] or ".py" in q.get("relevant_files", [""])[0] else "java")

        results = retriever_search_fn(query=qtext, top_k=top_k)
        retrieved_cids = [r["chunk_id"] for r in results]

        # Check ranks
        hit_rank = None
        for rank_idx, cid in enumerate(retrieved_cids, 1):
            if cid in ground_truth:
                hit_rank = rank_idx
                break

        if hit_rank is not None:
            if hit_rank == 1:
                r1 += 1
            if hit_rank <= 5:
                r5 += 1
            if hit_rank <= 10:
                r10 += 1
            rr = 1.0 / hit_rank
            reciprocal_ranks.append(rr)
            lang_mrr[lang].append(rr)

            if len(successful_examples) < 3:
                successful_examples.append({
                    "question": qtext,
                    "target_chunk": list(ground_truth)[0],
                    "hit_rank": hit_rank,
                    "top_retrieved": retrieved_cids[:3]
                })
        else:
            reciprocal_ranks.append(0.0)
            lang_mrr[lang].append(0.0)

            if len(failed_examples) < 3:
                failed_examples.append({
                    "question": qtext,
                    "target_chunk": list(ground_truth)[0],
                    "top_retrieved": retrieved_cids[:3]
                })

        # Precision@5: fraction of retrieved top 5 that are relevant
        top5 = retrieved_cids[:5]
        hits_in_5 = sum(1 for cid in top5 if cid in ground_truth)
        p5_scores.append(hits_in_5 / max(1, len(top5)))

    n = len(queries)
    return {
        "query_count": n,
        "recall@1": round(r1 / max(1, n), 4),
        "recall@5": round(r5 / max(1, n), 4),
        "recall@10": round(r10 / max(1, n), 4),
        "mrr": round(float(np.mean(reciprocal_ranks)), 4) if reciprocal_ranks else 0.0,
        "precision@5": round(float(np.mean(p5_scores)), 4) if p5_scores else 0.0,
        "per_language_mrr": {
            lang: round(float(np.mean(scores)), 4) if scores else 0.0
            for lang, scores in lang_mrr.items()
        },
        "successful_examples": successful_examples,
        "failed_examples": failed_examples
    }


def compare_retrieval_engines(
    bm25: BM25Retriever,
    dense: DenseRetriever,
    hybrid: HybridRetriever,
    eval_qa_path: Path,
    max_eval_queries: int = 200
) -> Dict[str, Any]:
    """Execute head-to-head comparison between BM25, Dense, and Hybrid on identical queries."""
    queries = list(stream_read(eval_qa_path))[:max_eval_queries]
    if not queries:
        raise ValueError(f"No evaluation queries found in {eval_qa_path}")

    print(f"Running comparative retrieval evaluation on {len(queries)} queries...")

    print("Evaluating BM25...")
    bm25_metrics = evaluate_engine_on_queries(
        lambda query, top_k: bm25.search(query=query, top_k=top_k),
        queries
    )

    print("Evaluating Dense...")
    dense_metrics = evaluate_engine_on_queries(
        lambda query, top_k: dense.search(query=query, top_k=top_k),
        queries
    )

    print("Evaluating Hybrid (RRF)...")
    hybrid_metrics = evaluate_engine_on_queries(
        lambda query, top_k: hybrid.search(query=query, top_k=top_k, mode="hybrid"),
        queries
    )

    report = {
        "evaluation_summary": {
            "eval_query_count": len(queries),
            "eval_source": str(eval_qa_path)
        },
        "metrics_comparison": {
            "bm25": bm25_metrics,
            "dense": dense_metrics,
            "hybrid": hybrid_metrics
        }
    }
    return report


def render_markdown_comparison_report(report: Dict[str, Any]) -> str:
    """Format comparison results into clean GitHub Flavored Markdown."""
    m = report["metrics_comparison"]
    bm = m["bm25"]
    dm = m["dense"]
    hm = m["hybrid"]
    count = report["evaluation_summary"]["eval_query_count"]

    lines = [
        "# Retrieval Engine Comparison Report (Phase 3)",
        "",
        f"**Evaluated Queries:** {count:,}  ",
        f"**Evaluation Split:** `{report['evaluation_summary']['eval_source']}`",
        "",
        "---",
        "",
        "## 1. Overall Performance Metrics",
        "",
        "| Metric | BM25 Lexical | Dense Semantic | Hybrid (RRF) |",
        "|---|---|---|---|",
        f"| **Recall@1** | {bm['recall@1']:.4f} | {dm['recall@1']:.4f} | **{hm['recall@1']:.4f}** |",
        f"| **Recall@5** | {bm['recall@5']:.4f} | {dm['recall@5']:.4f} | **{hm['recall@5']:.4f}** |",
        f"| **Recall@10** | {bm['recall@10']:.4f} | {dm['recall@10']:.4f} | **{hm['recall@10']:.4f}** |",
        f"| **MRR** | {bm['mrr']:.4f} | {dm['mrr']:.4f} | **{hm['mrr']:.4f}** |",
        f"| **Precision@5** | {bm['precision@5']:.4f} | {dm['precision@5']:.4f} | **{hm['precision@5']:.4f}** |",
        "",
        "---",
        "",
        "## 2. Per-Language MRR Breakdown",
        "",
        "| Language | BM25 MRR | Dense MRR | Hybrid MRR |",
        "|---|---|---|---|",
    ]

    all_langs = sorted(list(set(bm["per_language_mrr"].keys()) | set(dm["per_language_mrr"].keys())))
    for lang in all_langs:
        b_score = bm["per_language_mrr"].get(lang, 0.0)
        d_score = dm["per_language_mrr"].get(lang, 0.0)
        h_score = hm["per_language_mrr"].get(lang, 0.0)
        lines.append(f"| {lang} | {b_score:.4f} | {d_score:.4f} | **{h_score:.4f}** |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Representative Query Analysis",
        "",
        "### Hybrid Hits (Rank 1):",
    ])
    for ex in hm["successful_examples"]:
        lines.append(f"- **Query:** *\"{ex['question']}\"* -> Target Chunk `{ex['target_chunk']}` found at Rank 1")

    if hm["failed_examples"]:
        lines.extend([
            "",
            "### Difficult Queries (Low Recall):"
        ])
        for ex in hm["failed_examples"]:
            lines.append(f"- **Query:** *\"{ex['question']}\"* (Target Chunk `{ex['target_chunk']}` not in top 10)")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate and compare BM25, Dense, and Hybrid retrieval.")
    parser.add_argument("--bm25-index", type=str, default=str(DATA / "indexes" / "bm25_index.pkl"), help="BM25 index path")
    parser.add_argument("--dense-dir", type=str, default=str(DATA / "indexes" / "dense_store"), help="Dense store directory")
    parser.add_argument("--eval-qa", type=str, default=str(DATA / "splits" / "test_qa.jsonl"), help="Evaluation QA file")
    parser.add_argument("--json-report", type=str, default=str(DATA / "reports" / "retrieval_comparison_report.json"), help="Output JSON report")
    parser.add_argument("--md-report", type=str, default=str(DATA / "reports" / "retrieval_comparison_report.md"), help="Output Markdown report")
    parser.add_argument("--max-queries", type=int, default=150, help="Max queries to evaluate")
    args = parser.parse_args()

    bm25 = BM25Retriever(Path(args.bm25_index))
    dense = DenseRetriever(store_dir=Path(args.dense_dir))
    hybrid = HybridRetriever(bm25, dense)

    report = compare_retrieval_engines(
        bm25=bm25,
        dense=dense,
        hybrid=hybrid,
        eval_qa_path=Path(args.eval_qa),
        max_eval_queries=args.max_queries
    )

    json_path = Path(args.json_report)
    md_path = Path(args.md_report)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md_text = render_markdown_comparison_report(report)
    md_path.write_text(md_text, encoding="utf-8")

    print("\n--- RETRIEVAL COMPARISON SUMMARY ---")
    m = report["metrics_comparison"]
    print(f"BM25:   Recall@1={m['bm25']['recall@1']:.4f} | Recall@5={m['bm25']['recall@5']:.4f} | MRR={m['bm25']['mrr']:.4f}")
    print(f"Dense:  Recall@1={m['dense']['recall@1']:.4f} | Recall@5={m['dense']['recall@5']:.4f} | MRR={m['dense']['mrr']:.4f}")
    print(f"Hybrid: Recall@1={m['hybrid']['recall@1']:.4f} | Recall@5={m['hybrid']['recall@5']:.4f} | MRR={m['hybrid']['mrr']:.4f}")
    print(f"\nSaved JSON report: {json_path}")
    print(f"Saved Markdown report: {md_path}")


if __name__ == "__main__":
    main()
