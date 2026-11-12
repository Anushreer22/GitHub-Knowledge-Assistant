# GitHub Knowledge Assistant Dataset Starter (Python + Java)

This pipeline collects public GitHub repos, clones them, extracts Python/Java functions/classes into JSONL chunks, creates QA *candidates*, creates negative candidates, validates records, and splits by repository.

## Setup (PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Optional: add GITHUB_TOKEN to .env (never commit it)
```

## Run from the repository root
```powershell
python -m dataset_pipeline.collect_repositories --per-language 10
python -m dataset_pipeline.extract_repositories
python -m dataset_pipeline.build_chunks
python -m dataset_pipeline.generate_qa
python -m dataset_pipeline.generate_negatives
python -m dataset_pipeline.validate_dataset
python -m dataset_pipeline.split_dataset
```
Start with `--per-language 2` to smoke-test. Git must be installed.

## Important
Publicly accessible code is not automatically free of licence obligations. The collector records licence metadata; inspect each licence and comply with its terms before using/redistributing code. Never execute downloaded code. Secret scanning is heuristic, not a guarantee. Automated QA are candidate labels, not gold truth. Human-review evaluation questions. Split by repository to prevent leakage.

Outputs: `data/metadata/repositories.jsonl`, `data/processed/code_chunks.jsonl`, `data/qa/qa_candidates.jsonl`, `data/qa/hard_negative_candidates.jsonl`, `data/splits/*`.
