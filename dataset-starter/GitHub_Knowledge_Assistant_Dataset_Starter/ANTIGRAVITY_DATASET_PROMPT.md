You are a senior data-engineering and ML engineer. Work inside this existing GitHub Knowledge Assistant repository.

TASK
Implement and verify a reproducible public-GitHub dataset pipeline for Python and Java. Inspect the existing repository first. Preserve existing files and do not overwrite working code without explaining why.

PIPELINE REQUIREMENTS
1. Search public GitHub repositories for Python and Java using GitHub's official API. Support optional GITHUB_TOKEN from .env; never print or commit it. Respect API rate limits. Record full_name, html_url, clone_url, default branch, primary language, stars, licence SPDX/name, collection timestamp, and collection source.
2. Prefer repositories with an explicit licence, but mark licence_review_status=needs_human_review. Do not claim public means unrestricted. Do not redistribute or train on code until licence obligations have been reviewed.
3. Shallow-clone repositories; record exact commit SHA. Never execute downloaded repository code.
4. Filter to .py and .java. Exclude .git, virtual environments, node_modules, vendor, generated/build output, binaries, files over a configurable size, and obvious secret-like content. Document that secret scanning is heuristic and cannot guarantee removal of all secrets.
5. Parse Python using the built-in ast module. Parse Java using Tree-sitter Java when available. Include safe fallback chunking and record parser_status.
6. Create stable code chunk records with: schema_version, repo_id, repo_full_name, commit_sha, file_path, language, chunk_id, chunk_type, chunk_name, code_text, start_line, end_line, imports, symbols_defined, symbols_used, parser_status, licence metadata, split.
7. Generate QA candidates from symbols and code structure. Each record must include question_id, repo_id, question, expected_answer (nullable until reviewed), relevant_chunk_ids, relevant_files, difficulty, answerable, generation_method, review_status, reviewer_notes, source_chunk_id, split. Set review_status=needs_review. Never represent template-generated questions as verified labels.
8. Generate negative candidates from same-language chunks. Avoid choosing the positive chunk; store positive_chunk_id, negative_chunk_id, sampling method and review status. Treat negatives as candidates because a sampled chunk may accidentally be relevant.
9. Validate JSONL schemas, unique IDs, referenced chunk IDs, language, non-empty code and line ranges. Add licence and secret-scan review warnings.
10. Split by repository, never random chunks. Ensure repository IDs are disjoint across train, validation and test. For tiny collections, warn that evaluation is statistically weak; do not silently claim all splits are useful.
11. Add reproducible CLI commands, structured logs, tests and documentation. Include synthetic fixture data clearly marked synthetic.
12. Do not invent collected repository counts, licence approvals, QA correctness or benchmark metrics.

EXPECTED OUTPUTS
data/metadata/repositories.jsonl
data/processed/code_chunks.jsonl
data/qa/qa_candidates.jsonl
data/qa/qa_review_template.jsonl
data/qa/hard_negative_candidates.jsonl
data/splits/train_chunks.jsonl
data/splits/val_chunks.jsonl
data/splits/test_chunks.jsonl
data/splits/train_pairs.jsonl
data/splits/val_pairs.jsonl
data/splits/test_pairs.jsonl
data/splits/split_manifest.json
schemas/code_chunk.schema.json
schemas/qa_pair.schema.json
schemas/hard_negative.schema.json

IMPLEMENTATION ORDER
Phase A: inspect current workspace, report files and dependencies.
Phase B: implement/fix repository collection and cloning.
Phase C: implement parsing/chunking for Python and Java.
Phase D: implement QA candidate and negative candidate generation.
Phase E: implement validation, licence/secret review reports and repository-level split.
Phase F: add tests and run them.
Phase G: document exact PowerShell commands for Windows and limitations.

ACCEPTANCE CRITERIA
- Every code chunk traces to a repository URL, commit SHA, file and line range.
- Python and Java are both supported; parser fallback is explicit.
- No downloaded code is executed.
- QA candidates are clearly marked needs_review.
- Split repositories do not overlap.
- Validation tests actually run and their real output is reported.
- No fabricated metrics or licence claims.
- Provide changed-file list, commands run, test results and remaining risks.

FIRST ACTION
Inspect the current repository and compare it with this specification. Write docs/DATASET_IMPLEMENTATION_PLAN.md and wait for approval before broad changes. After approval, implement Phase B only, then proceed one phase at a time.