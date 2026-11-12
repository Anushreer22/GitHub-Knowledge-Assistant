import csv
import json
import argparse
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List

from .common import DATA, stream_read, stream_write

VALID_STATUSES = {"pending", "approved", "rejected", "needs_correction"}


def import_review_from_csv(
    csv_path: Path,
    review_store_path: Path,
    raw_qa_path: Path
) -> Dict[str, Any]:
    """Import reviewed records from CSV into the human review store (data/review/qa_review.jsonl).
    Preserves the raw qa_candidates.jsonl file untouched.
    """
    review_store_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing review records if present to allow incremental updates
    existing_reviews: Dict[str, Dict[str, Any]] = {}
    if review_store_path.exists():
        for r in stream_read(review_store_path):
            existing_reviews[r["question_id"]] = r

    # Also build index of raw records for fallback fields
    raw_index: Dict[str, Dict[str, Any]] = {}
    if raw_qa_path.exists():
        for q in stream_read(raw_qa_path):
            raw_index[q["question_id"]] = q

    status_counts = Counter()
    imported_count = 0

    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row.get("question_id", "").strip()
            if not qid:
                continue

            raw_item = raw_index.get(qid, {})
            decision = (row.get("reviewer_decision") or row.get("review_status") or "pending").strip().lower()
            if decision not in VALID_STATUSES:
                decision = "pending"

            status_counts[decision] += 1
            imported_count += 1

            corrected_q = row.get("corrected_question", "").strip()
            corrected_ans = row.get("corrected_expected_answer", "").strip()
            verified_chunks_str = row.get("verified_relevant_chunk_ids", "").strip()
            verified_chunks = [c.strip() for c in verified_chunks_str.split(";") if c.strip()] if verified_chunks_str else None

            # Build canonical review record
            record: Dict[str, Any] = {
                "schema_version": "1.0",
                "question_id": qid,
                "repo_id": row.get("repo_id") or raw_item.get("repo_id"),
                "question": corrected_q if (decision == "approved" and corrected_q) else (row.get("question") or raw_item.get("question")),
                "expected_answer": corrected_ans if (decision == "approved" and corrected_ans) else (row.get("expected_answer") or raw_item.get("expected_answer")),
                "relevant_chunk_ids": verified_chunks or raw_item.get("relevant_chunk_ids", [c for c in row.get("relevant_chunk_ids", "").split(";") if c]),
                "relevant_files": raw_item.get("relevant_files", [f for f in row.get("relevant_files", "").split(";") if f]),
                "difficulty": row.get("difficulty") or raw_item.get("difficulty", "medium"),
                "answerable": row.get("answerable", "TRUE").upper() == "TRUE",
                "generation_method": row.get("generation_method") or raw_item.get("generation_method", "manual_review"),
                "review_status": decision,
                "reviewer_decision": decision,
                "corrected_question": corrected_q or None,
                "corrected_expected_answer": corrected_ans or None,
                "verified_relevant_chunk_ids": verified_chunks,
                "reviewer_notes": row.get("reviewer_notes", "").strip() or None,
                "source_chunk_id": raw_item.get("source_chunk_id"),
                "split": raw_item.get("split")
            }

            existing_reviews[qid] = record

    # Write out updated review store
    stream_write(review_store_path, existing_reviews.values())

    return {
        "imported_rows": imported_count,
        "total_in_review_store": len(existing_reviews),
        "status_distribution": dict(status_counts)
    }


def main():
    parser = argparse.ArgumentParser(description="Import human reviews into review store.")
    parser.add_argument("--csv", type=str, default=str(DATA / "review" / "pending_qa_review.csv"), help="Reviewed CSV input file")
    parser.add_argument("--review-store", type=str, default=str(DATA / "review" / "qa_review.jsonl"), help="Path to qa_review.jsonl")
    parser.add_argument("--raw-qa", type=str, default=str(DATA / "qa" / "qa_candidates.jsonl"), help="Raw QA candidates path")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    review_store_path = Path(args.review_store)
    raw_qa_path = Path(args.raw_qa)

    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    summary = import_review_from_csv(csv_path, review_store_path, raw_qa_path)
    print("\n--- HUMAN REVIEW IMPORT SUMMARY ---")
    print(f"Imported records from CSV: {summary['imported_rows']}")
    print(f"Total records in review store: {summary['total_in_review_store']}")
    print(f"Status distribution: {summary['status_distribution']}")
    print(f"Review store updated at: {review_store_path}")
    print("Raw candidates preserved at:", raw_qa_path)


if __name__ == "__main__":
    main()
