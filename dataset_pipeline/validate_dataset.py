import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Set, Optional

from .common import DATA, stream_read


def validate_dataset(
    chunks_path: Path,
    qa_path: Optional[Path] = None,
    negatives_path: Optional[Path] = None,
    splits_dir: Optional[Path] = None,
    repos_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Perform rigorous structural and integrity checks across the dataset pipeline."""
    report: Dict[str, Any] = {
        "status": "PASS",
        "timestamp": None,
        "summary": {},
        "chunk_validation": {},
        "qa_validation": {},
        "negative_validation": {},
        "split_validation": {},
        "structural_errors": [],
        "warnings": [],
        "human_review_summary": {}
    }

    errors: List[str] = []
    warnings: List[str] = []

    # 1. Validate Repositories Metadata
    known_repos: Set[str] = set()
    if repos_path and repos_path.exists():
        for r in stream_read(repos_path):
            rid = r.get("repo_id")
            if rid:
                known_repos.add(rid)

    # 2. Validate Code Chunks
    if not chunks_path.exists():
        errors.append(f"Code chunks file does not exist: {chunks_path}")
        report["status"] = "FAIL"
        report["structural_errors"] = errors
        return report

    chunk_ids: Set[str] = set()
    chunk_to_repo: Dict[str, str] = {}
    chunk_to_file: Dict[str, str] = {}
    lang_counter: Counter = Counter()
    repo_counter: Counter = Counter()
    chunk_type_counter: Counter = Counter()
    total_chunks = 0
    duplicate_chunks = 0
    empty_code_chunks = 0
    invalid_line_ranges = 0

    required_chunk_fields = [
        "repo_id", "commit_sha", "file_path", "language", "chunk_id",
        "chunk_type", "chunk_name", "code_text", "start_line", "end_line",
        "imports", "symbols_defined", "symbols_used", "parser_status"
    ]

    for i, c in enumerate(stream_read(chunks_path)):
        total_chunks += 1
        cid = c.get("chunk_id")
        repo = c.get("repo_id")
        lang = c.get("language")
        fpath = c.get("file_path")
        code = c.get("code_text", "")
        start = c.get("start_line")
        end = c.get("end_line")

        # Check required fields
        for field in required_chunk_fields:
            if field not in c:
                errors.append(f"Chunk {i} missing field '{field}'")

        if not cid:
            errors.append(f"Chunk {i} has empty or missing chunk_id")
            continue

        if cid in chunk_ids:
            duplicate_chunks += 1
            if duplicate_chunks <= 10:
                errors.append(f"Duplicate chunk_id: {cid}")
        else:
            chunk_ids.add(cid)
            chunk_to_repo[cid] = repo or ""
            chunk_to_file[cid] = fpath or ""

        if not code or not code.strip():
            empty_code_chunks += 1
            if empty_code_chunks <= 10:
                errors.append(f"Chunk {cid} has empty code_text")

        if lang not in {"python", "java"}:
            errors.append(f"Chunk {cid} has invalid language '{lang}'")
        else:
            lang_counter[lang] += 1

        if repo:
            repo_counter[repo] += 1
            if known_repos and repo not in known_repos:
                warnings.append(f"Chunk {cid} references unknown repository {repo}")

        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
            invalid_line_ranges += 1
            if invalid_line_ranges <= 10:
                errors.append(f"Chunk {cid} has invalid line range ({start}-{end})")

        chunk_type_counter[c.get("chunk_type", "unknown")] += 1

    if total_chunks == 0:
        errors.append("Dataset error: code_chunks.jsonl is completely empty!")

    report["chunk_validation"] = {
        "total_chunks": total_chunks,
        "unique_chunk_ids": len(chunk_ids),
        "duplicate_chunk_count": duplicate_chunks,
        "empty_code_count": empty_code_chunks,
        "invalid_line_range_count": invalid_line_ranges,
        "languages": dict(lang_counter),
        "repositories": dict(repo_counter),
        "top_chunk_types": chunk_type_counter.most_common(10)
    }

    # 3. Validate QA Candidates
    total_qas = 0
    unique_qas: Set[str] = set()
    duplicate_questions = 0
    missing_chunk_refs = 0
    missing_answers = 0
    qa_review_status_counter: Counter = Counter()
    qa_methods_counter: Counter = Counter()

    required_qa_fields = [
        "question_id", "repo_id", "question", "expected_answer",
        "relevant_chunk_ids", "relevant_files", "difficulty",
        "answerable", "generation_method", "review_status",
        "source_chunk_id", "split"
    ]

    if qa_path and qa_path.exists():
        for i, q in enumerate(stream_read(qa_path)):
            total_qas += 1
            qid = q.get("question_id")
            qtext = q.get("question")
            ans = q.get("expected_answer")
            rel_chunks = q.get("relevant_chunk_ids", [])
            status = q.get("review_status", "unknown")
            method = q.get("generation_method", "unknown")

            qa_review_status_counter[status] += 1
            qa_methods_counter[method] += 1

            for field in required_qa_fields:
                if field not in q:
                    errors.append(f"QA {i} missing required field '{field}'")

            if not qid or qid in unique_qas:
                duplicate_questions += 1
                if duplicate_questions <= 10:
                    errors.append(f"Duplicate or empty question_id: {qid}")
            else:
                unique_qas.add(qid)

            if not qtext or not qtext.strip():
                errors.append(f"QA {qid} has empty question text")

            if not ans and q.get("answerable") is True:
                missing_answers += 1
                if missing_answers <= 10:
                    warnings.append(f"QA {qid} marked answerable=True but expected_answer is null")

            for rc in rel_chunks:
                if rc not in chunk_ids:
                    missing_chunk_refs += 1
                    if missing_chunk_refs <= 10:
                        errors.append(f"QA {qid} references unknown chunk_id '{rc}'")

    report["qa_validation"] = {
        "total_qa": total_qas,
        "unique_questions": len(unique_qas),
        "duplicate_question_count": duplicate_questions,
        "missing_chunk_reference_count": missing_chunk_refs,
        "missing_answer_count": missing_answers,
        "review_statuses": dict(qa_review_status_counter),
        "generation_methods": dict(qa_methods_counter)
    }

    # 4. Validate Negatives
    total_negs = 0
    unique_pairs: Set[str] = set()
    invalid_neg_refs = 0
    false_negative_risks = 0
    neg_methods_counter: Counter = Counter()

    if negatives_path and negatives_path.exists():
        for i, neg in enumerate(stream_read(negatives_path)):
            total_negs += 1
            pid = neg.get("pair_id")
            pos_id = neg.get("positive_chunk_id")
            neg_id = neg.get("negative_chunk_id")
            method = neg.get("negative_generation_method", "unknown")

            neg_methods_counter[method] += 1

            if not pid or pid in unique_pairs:
                errors.append(f"Negative {i} has duplicate or empty pair_id '{pid}'")
            else:
                unique_pairs.add(pid)

            if pos_id not in chunk_ids:
                invalid_neg_refs += 1
                errors.append(f"Negative pair {pid} references unknown positive chunk {pos_id}")
            if neg_id not in chunk_ids:
                invalid_neg_refs += 1
                errors.append(f"Negative pair {pid} references unknown negative chunk {neg_id}")

            if pos_id == neg_id:
                false_negative_risks += 1
                errors.append(f"Negative pair {pid} has identical positive and negative chunk_id: {pos_id}")

    report["negative_validation"] = {
        "total_negatives": total_negs,
        "unique_pairs": len(unique_pairs),
        "invalid_negative_references": invalid_neg_refs,
        "identical_pos_neg_errors": false_negative_risks,
        "generation_methods": dict(neg_methods_counter)
    }

    # 5. Validate Repository-Level Splits & Leakage
    split_repos: Dict[str, Set[str]] = defaultdict(set)
    split_chunks: Dict[str, Set[str]] = defaultdict(set)
    split_leakage_errors = 0

    if splits_dir and splits_dir.exists():
        for split_name in ["train", "validation", "test"]:
            # Check chunks
            chunk_file = splits_dir / f"{split_name}_chunks.jsonl"
            if chunk_file.exists():
                for c in stream_read(chunk_file):
                    cid = c.get("chunk_id")
                    rid = c.get("repo_id")
                    if rid:
                        split_repos[split_name].add(rid)
                    if cid:
                        split_chunks[split_name].add(cid)

            # Check pairs
            qa_file = splits_dir / f"{split_name}_qa.jsonl"
            if qa_file.exists():
                for q in stream_read(qa_file):
                    q_repo = q.get("repo_id")
                    if q_repo:
                        split_repos[split_name].add(q_repo)
                    for pos_c in q.get("relevant_chunk_ids", []):
                        pos_repo = chunk_to_repo.get(pos_c)
                        if pos_repo and pos_repo != q_repo:
                            split_leakage_errors += 1
                            errors.append(f"Split {split_name} QA {q.get('question_id')} positive chunk repo mismatch: {pos_repo} vs {q_repo}")

        # Check repository disjointness
        train_repos = split_repos.get("train", set())
        val_repos = split_repos.get("validation", set())
        test_repos = split_repos.get("test", set())

        train_val_overlap = train_repos.intersection(val_repos)
        train_test_overlap = train_repos.intersection(test_repos)
        val_test_overlap = val_repos.intersection(test_repos)

        if train_val_overlap:
            errors.append(f"Leakage detected: Repositories in both train and validation: {train_val_overlap}")
        if train_test_overlap:
            errors.append(f"Leakage detected: Repositories in both train and test: {train_test_overlap}")
        if val_test_overlap:
            errors.append(f"Leakage detected: Repositories in both validation and test: {val_test_overlap}")

    report["split_validation"] = {
        "train_repositories": sorted(list(split_repos.get("train", set()))),
        "validation_repositories": sorted(list(split_repos.get("validation", set()))),
        "test_repositories": sorted(list(split_repos.get("test", set()))),
        "train_chunks": len(split_chunks.get("train", set())),
        "validation_chunks": len(split_chunks.get("validation", set())),
        "test_chunks": len(split_chunks.get("test", set())),
        "leakage_errors": split_leakage_errors
    }

    # Final Status
    if errors:
        report["status"] = "FAIL"
    report["structural_errors"] = errors
    report["warnings"] = warnings
    report["summary"] = {
        "status": report["status"],
        "total_chunks": total_chunks,
        "total_qa": total_qas,
        "total_negatives": total_negs,
        "total_errors": len(errors),
        "total_warnings": len(warnings)
    }

    report["human_review_summary"] = {
        "note": "Structural validation checks schema, references, line ranges, and leakage. Semantic accuracy and license compliance require human review.",
        "pending_review_count": qa_review_status_counter.get("pending", 0) + qa_review_status_counter.get("needs_review", 0),
        "approved_count": qa_review_status_counter.get("approved", 0),
        "rejected_count": qa_review_status_counter.get("rejected", 0)
    }

    return report


def generate_markdown_report(report: Dict[str, Any]) -> str:
    """Render validation results into GitHub Flavored Markdown."""
    status_emoji = "✅ PASS" if report["status"] == "PASS" else "❌ FAIL"
    s = report["summary"]
    cv = report["chunk_validation"]
    qv = report["qa_validation"]
    nv = report["negative_validation"]
    sp = report["split_validation"]
    hr = report["human_review_summary"]

    lines = [
        "# Dataset Quality and Validation Report",
        "",
        f"**Validation Status:** {status_emoji}  ",
        f"**Total Chunks:** {s.get('total_chunks', 0):,}  ",
        f"**Total QA Candidates:** {s.get('total_qa', 0):,}  ",
        f"**Total Negative Candidates:** {s.get('total_negatives', 0):,}  ",
        f"**Errors:** {s.get('total_errors', 0)} | **Warnings:** {s.get('total_warnings', 0)}",
        "",
        "---",
        "",
        "## 1. Code Chunks Breakdown",
        "",
        f"- **Unique Chunk IDs:** {cv.get('unique_chunk_ids', 0):,}",
        f"- **Duplicate Chunks:** {cv.get('duplicate_chunk_count', 0)}",
        f"- **Empty Code Chunks:** {cv.get('empty_code_count', 0)}",
        f"- **Invalid Line Ranges:** {cv.get('invalid_line_range_count', 0)}",
        "",
        "### Language Distribution",
        "| Language | Chunks |",
        "|---|---|",
    ]
    for lang, count in cv.get("languages", {}).items():
        lines.append(f"| {lang} | {count:,} |")

    lines.extend([
        "",
        "### Repository Distribution",
        "| Repository ID | Chunks |",
        "|---|---|",
    ])
    for repo, count in cv.get("repositories", {}).items():
        lines.append(f"| {repo} | {count:,} |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. QA Candidates Integrity",
        "",
        f"- **Total Generated QA:** {qv.get('total_qa', 0):,}",
        f"- **Unique Questions:** {qv.get('unique_questions', 0):,}",
        f"- **Missing Chunk References:** {qv.get('missing_chunk_reference_count', 0)}",
        f"- **Missing Answers (Answerable=True):** {qv.get('missing_answer_count', 0)}",
        "",
        "### Review Statuses",
        "| Review Status | Count |",
        "|---|---|",
    ])
    for st, count in qv.get("review_statuses", {}).items():
        lines.append(f"| {st} | {count:,} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Negative Sampling Verification",
        "",
        f"- **Total Negative Pairs:** {nv.get('total_negatives', 0):,}",
        f"- **Unique Pairs:** {nv.get('unique_pairs', 0):,}",
        f"- **Invalid Negative References:** {nv.get('invalid_negative_references', 0)}",
        f"- **False Negative Risks (Pos == Neg):** {nv.get('identical_pos_neg_errors', 0)}",
        "",
        "---",
        "",
        "## 4. Repository Split & Leakage Verification",
        "",
        f"- **Train Repositories ({len(sp.get('train_repositories', []))}):** {', '.join(sp.get('train_repositories', [])) or 'None'}",
        f"- **Validation Repositories ({len(sp.get('validation_repositories', []))}):** {', '.join(sp.get('validation_repositories', [])) or 'None'}",
        f"- **Test Repositories ({len(sp.get('test_repositories', []))}):** {', '.join(sp.get('test_repositories', [])) or 'None'}",
        f"- **Leakage Detected:** {'YES - VIOLATION' if report.get('structural_errors') and any('Leakage' in e for e in report['structural_errors']) else 'None (Clean Disjoint Sets)'}",
        "",
        "---",
        "",
        "## 5. Structural vs Semantic Human Review",
        "",
        "> [!IMPORTANT]",
        f"> {hr.get('note')}",
        f"> Pending Human Review: **{hr.get('pending_review_count', 0):,}** | Approved: **{hr.get('approved_count', 0):,}** | Rejected: **{hr.get('rejected_count', 0):,}**",
        ""
    ])

    if report["structural_errors"]:
        lines.extend([
            "",
            "## Structural Errors (Top 50)",
            ""
        ])
        for err in report["structural_errors"][:50]:
            lines.append(f"- ❌ {err}")

    if report["warnings"]:
        lines.extend([
            "",
            "## Warnings (Top 50)",
            ""
        ])
        for warn in report["warnings"][:50]:
            lines.append(f"- ⚠️ {warn}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate dataset quality and integrity.")
    parser.add_argument("--chunks", type=str, default=str(DATA / "processed" / "code_chunks.jsonl"), help="Path to code chunks")
    parser.add_argument("--qa", type=str, default=str(DATA / "qa" / "qa_candidates.jsonl"), help="Path to QA candidates")
    parser.add_argument("--negatives", type=str, default=str(DATA / "qa" / "hard_negative_candidates.jsonl"), help="Path to negatives")
    parser.add_argument("--splits", type=str, default=str(DATA / "splits"), help="Path to splits directory")
    parser.add_argument("--repos", type=str, default=str(DATA / "metadata" / "repositories.jsonl"), help="Path to repositories metadata")
    parser.add_argument("--json-report", type=str, default=str(DATA / "reports" / "dataset_validation_report.json"), help="Output JSON report")
    parser.add_argument("--md-report", type=str, default=str(DATA / "reports" / "dataset_validation_report.md"), help="Output Markdown report")
    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    qa_path = Path(args.qa) if Path(args.qa).exists() else None
    negatives_path = Path(args.negatives) if Path(args.negatives).exists() else None
    splits_dir = Path(args.splits) if Path(args.splits).exists() else None
    repos_path = Path(args.repos) if Path(args.repos).exists() else None

    report = validate_dataset(
        chunks_path=chunks_path,
        qa_path=qa_path,
        negatives_path=negatives_path,
        splits_dir=splits_dir,
        repos_path=repos_path
    )

    json_out = Path(args.json_report)
    md_out = Path(args.md_report)

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md_text = generate_markdown_report(report)
    md_out.write_text(md_text, encoding="utf-8")

    print(f"\nDataset Validation Finished: Status = {report['status']}")
    print(f"JSON Report written to: {json_out}")
    print(f"Markdown Report written to: {md_out}")

    if report["status"] != "PASS":
        print(f"Found {len(report['structural_errors'])} structural errors!")
        for e in report["structural_errors"][:10]:
            print(" -", e)
        raise SystemExit(1)
    else:
        print("All structural validation checks passed successfully.")


if __name__ == "__main__":
    main()
