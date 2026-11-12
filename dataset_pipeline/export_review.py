import csv
import argparse
from pathlib import Path
from typing import List, Dict, Any

from .common import DATA, stream_read


def export_pending_qa_to_csv(
    input_path: Path,
    output_csv: Path,
    limit: int = 200,
    review_status_filter: str = "pending"
) -> int:
    """Export pending QA records to a CSV formatted for human review."""
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "question_id",
        "repo_id",
        "question",
        "expected_answer",
        "relevant_chunk_ids",
        "relevant_files",
        "difficulty",
        "answerable",
        "generation_method",
        "review_status",
        "reviewer_decision",
        "corrected_question",
        "corrected_expected_answer",
        "verified_relevant_chunk_ids",
        "reviewer_notes"
    ]

    count = 0
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for q in stream_read(input_path):
            curr_status = q.get("review_status", "pending")
            if curr_status in {review_status_filter, "needs_review"}:
                row = {
                    "question_id": q.get("question_id", ""),
                    "repo_id": q.get("repo_id", ""),
                    "question": q.get("question", ""),
                    "expected_answer": q.get("expected_answer", "") or "",
                    "relevant_chunk_ids": ";".join(q.get("relevant_chunk_ids", [])),
                    "relevant_files": ";".join(q.get("relevant_files", [])),
                    "difficulty": q.get("difficulty", "medium"),
                    "answerable": "TRUE" if q.get("answerable", True) else "FALSE",
                    "generation_method": q.get("generation_method", ""),
                    "review_status": curr_status,
                    "reviewer_decision": "",  # To be filled by reviewer: approved / rejected / needs_correction
                    "corrected_question": "",
                    "corrected_expected_answer": "",
                    "verified_relevant_chunk_ids": "",
                    "reviewer_notes": ""
                }
                writer.writerow(row)
                count += 1
                if limit and count >= limit:
                    break

    return count


def main():
    parser = argparse.ArgumentParser(description="Export pending QA candidates for human review.")
    parser.add_argument("--input", type=str, default=str(DATA / "qa" / "qa_candidates.jsonl"), help="Input QA file")
    parser.add_argument("--output", type=str, default=str(DATA / "review" / "pending_qa_review.csv"), help="Output CSV path")
    parser.add_argument("--limit", type=int, default=200, help="Number of records to export for review batch")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input QA file not found: {input_path}")

    exported = export_pending_qa_to_csv(input_path, output_path, limit=args.limit)
    print(f"Exported {exported} pending QA records to {output_path}")


if __name__ == "__main__":
    main()
