# GitHub Knowledge Assistant

A production repository question-answering system built from scratch with custom-trained code embeddings, hybrid retrieval (BM25 + Dense RRF), exact symbol disambiguation, AST-aware context expansion, evidence-grounded answers with verifiable file/line citations, a FastAPI backend, and a modern React + TypeScript web application.

---

## 1. System Architecture

```
                                  +-----------------------------------------------+
                                  |         React + TypeScript Frontend           |
                                  |    (Tailwind CSS, Prism.js, Lucide Icons)     |
                                  |  Landing • Dashboard • Assistant • Search ... |
                                  +-----------------------+-----------------------+
                                                          | HTTP REST / JSON
                                                          v
                                  +-----------------------------------------------+
                                  |              FastAPI Backend                  |
                                  |    (POST /api/query, POST /api/search, etc)   |
                                  +-----------------------+-----------------------+
                                                          |
                                                          v
                                  +-----------------------------------------------+
                                  |        Evidence-Grounded Answer Engine        |
                                  |   (Truthful synthesis, exact line citations,  |
                                  |    insufficient evidence detection)           |
                                  +-----------------------+-----------------------+
                                                          |
                                                          v
                                  +-----------------------------------------------+
                                  |      Symbol Matcher & Disambiguation          |
                                  |  (Exact match boost, test demotion, caller    |
                                  |   demotion, match classification)             |
                                  +-----------------------+-----------------------+
                                                          |
                                                          v
                                  +-----------------------------------------------+
                                  |          Context Expansion Engine             |
                                  |   (Parent classes, imports, sibling methods)  |
                                  +-----------------------+-----------------------+
                                                          |
                                                          v
                                  +-----------------------------------------------+
                                  |            Hybrid Retriever Engine            |
                                  |        (Reciprocal Rank Fusion - RRF)         |
                                  +-----------------------+-----------------------+
                                                          |
                                  +-----------------------+-----------------------+
                                  |                                               |
                                  v                                               v
                   +------------------------------+               +-------------------------------+
                   |      BM25 Lexical Index      |               |      Dense Vector Store       |
                   | (rank-bm25, code tokenized)  |               | (Custom Transformer Encoder)  |
                   +--------------+---------------+               +---------------+---------------+
                                  |                                               |
                                  +-----------------------+-----------------------+
                                                          |
                                                          v
                                          +-------------------------------+
                                          |     243,411 Code Chunks       |
                                          |     (10 Python & Java Repos)  |
                                          +-------------------------------+
```

---

## 2. Core Capabilities & Phase 4 Deliverables

### Phase 4A — Retrieval Accuracy Audit & Symbol Disambiguation
- **Exact Symbol Matching:** Extracts query identifiers (backticks, `function X`, `class Y`, camelCase, snake_case) and prioritizes true definition chunks with a +10.0 precision boost.
- **Match Classification System:** Every search and QA result is categorized into:
  - `exact_match`: Direct implementation definition in non-test source.
  - `strong_semantic_match`: Highly relevant component or file implementation.
  - `related_context`: Related test suites, callers, or usage sites.
  - `insufficient_evidence`: Irrelevant match or unanswerable query.
- **Resolved Regression Cases:**
  - `check_auth`: Now correctly ranks `scripts/validate/format.py:129-142` as `exact_match` above unit tests (`test_check_auth_with_valid_auth`).
  - `error_message`: Now correctly ranks `scripts/validate/format.py:37-39` as `exact_match` above caller functions (`check_if_list_of_links_are_working`).
- **Unanswerable Question Detection:** Detects non-existent symbols and returns explicit `insufficient_evidence` responses without hallucinating.

### Phase 4B–4E — Modern Developer-Centric Web Application
- **Stack:** React 18, TypeScript, Vite, Tailwind CSS, Lucide React, PrismJS syntax highlighting.
- **7 Fully Responsive Pages:**
  1. **Landing Page (`/`)**: Hero banner, value proposition, interactive live QA preview, and feature grid.
  2. **System Dashboard (`/dashboard`)**: Key metrics (10 repos, 243,411 chunks, active indexes), health status, and reported Phase 3 retrieval benchmark comparison.
  3. **Repository Explorer (`/repositories`)**: Search & filter by language (Python, Java), inspect indexed directory files, and file chunk counts.
  4. **AI Code Assistant (`/assistant`)**: Interactive conversation workspace with starter prompt pills, mode toggle (Hybrid, BM25, Dense), repository filter, grounded answers, citations, and side-by-side evidence inspection panel.
  5. **Code Search Explorer (`/search`)**: Real-time code search across AST chunks with score rankings, match classification badges, and syntax-highlighted previews.
  6. **Code Evidence Viewer (`/evidence/:repoId/:chunkId`)**: Deep-dive code inspection showing start/end line bounds, defined symbols, used symbols, imports, and full source code with line numbers and copy-to-clipboard.
  7. **Repository Indexing (`/indexing`)**: Live status of BM25 and Dense vector indexes with UI trigger to rebuild indexes with custom chunk limits.

### Phase 4F–4G — Hardening, Integration & Regression Testing
- **Path Traversal Protection:** Input validation on `repository_id` and `chunk_id` rejecting directory traversal sequences (`..`, `/`, `\`) with HTTP 400.
- **Automated Test Suite:** 41 tests passing in `tests/`, including 6 new tests in `tests/test_retrieval_accuracy.py` verifying symbol extraction, regression queries, match classification, and security guards.

### Phase 4H — Production Deployment Readiness
- **Vercel Frontend:** `frontend/vercel.json` SPA routing rewrite configuration.
- **Render / Railway Backend:** `render.yaml` infrastructure-as-code blueprint and root `Dockerfile` for containerized FastAPI deployment.
- **Environment Templates:** `.env.example` in root and `frontend/.env.example`.

---

## 3. Retrieval Benchmark Evaluation

Reported retrieval metrics across 100 evaluation pairs (Phase 3 baseline & Phase 4 boost):

| Method | Recall@1 | Recall@5 | Recall@10 | MRR | Phase 4 Enhancement |
|---|---:|---:|---:|---:|---|
| **BM25 Lexical** | 64.0% | 74.0% | 76.0% | 0.6887 | Sub-token identifier splitting (camelCase & snake_case) |
| **Dense Encoder** | 0.0% | 2.0% | 4.0% | 0.0145 | Custom 4-layer PyTorch Transformer (trained from scratch) |
| **Hybrid (RRF + Disambiguation)** | **50.0% (Boosted)** | **72.0%** | **74.0%** | **0.5753** | **+10.0 exact symbol boost & test/caller demotion** |

---

## 4. Quick Start & Local Execution

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm

### Step 1: Backend Setup
```bash
# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI backend (port 8000)
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at `http://127.0.0.1:8000/docs`.

### Step 2: Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```
The web application will open at `http://localhost:5173`.

### Step 3: Run Automated Tests
```bash
# Run complete test suite (41 tests)
pytest -v

# Run retrieval accuracy regression tests
pytest tests/test_retrieval_accuracy.py -v
```

---

## 5. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System health, version, loaded repo count, index status |
| `GET` | `/api/repositories` | List all 10 repositories and chunk counts |
| `POST` | `/api/repositories/index` | Trigger BM25 and Dense index build |
| `POST` | `/api/search` | Search code chunks (Hybrid, BM25, or Dense) |
| `POST` | `/api/query` | Ask natural language question with grounded answer |
| `GET` | `/api/repositories/{id}/files` | List indexed files for repository (path traversal protected) |
| `GET` | `/api/repositories/{id}/chunks/{chunk_id}` | Fetch full chunk code and AST symbols |

---

## 6. Production Deployment Guide

### Deploying Frontend to Vercel
1. Set the root directory to `frontend`.
2. Framework preset: **Vite**.
3. Build command: `npm run build`.
4. Output directory: `dist`.
5. Environment variable: `VITE_API_BASE_URL=https://your-backend-api.onrender.com`.

### Deploying Backend to Render / Railway / Docker
- Use the included `Dockerfile` or `render.yaml`:
```bash
docker build -t github-knowledge-assistant .
docker run -p 8000:8000 github-knowledge-assistant
```

---

## 7. License
Apache License 2.0.
