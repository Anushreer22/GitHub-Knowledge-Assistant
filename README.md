# GitHub Knowledge Assistant

A production-ready repository question-answering system built from scratch with custom-trained code embeddings, hybrid retrieval (BM25 + Dense RRF), exact symbol disambiguation, AST-aware context expansion, evidence-grounded answers with verifiable file/line citations, live GitHub integration with incremental git sync, static symbol relationship graph (callers, callees, inheritance, related tests), cross-file execution flow synthesis, rate-limited FastAPI backend, and a modern React + TypeScript web application.

---

## 1. System Architecture

```
                                  +-----------------------------------------------+
                                  |         React + TypeScript Frontend           |
                                  |    (Tailwind CSS, Prism.js, Lucide Icons)     |
                                  |  Landing • Dashboard • Assistant • Search ... |
                                  |  Live Ingestion Modal • History Drawer • Auth |
                                  +-----------------------+-----------------------+
                                                          | HTTP REST / JSON (JWT Optional)
                                                          v
                                  +-----------------------------------------------+
                                  |              FastAPI Backend                  |
                                  |  (RateLimiter, Auth, Live Ingestion, Sync API)|
                                  +-----------------------+-----------------------+
                                                          |
                                                          v
                                  +-----------------------------------------------+
                                  |        Evidence-Grounded Answer Engine        |
                                  |   (Cross-file flow synthesis, missing-evidence|
                                  |    detection, exact line citations)           |
                                  +-----------------------+-----------------------+
                                                          |
                                                          v
                                  +-----------------------------------------------+
                                  |             Static Symbol Graph               |
                                  | (Callers, callees, inheritance, related tests,|
                                  |  verified vs inferred vs unverified status)   |
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
                                          |     Indexed Code Chunks       |
                                          |   (AST & Tree-Sitter Parsed)  |
                                          +-------------------------------+
```

---

## 2. Core Capabilities & Phase 5 Deliverables

### Phase 5A — Live GitHub Repository Integration
- **Direct GitHub Ingestion:** Ingest any public GitHub repository via its HTTPS URL (`https://github.com/owner/repo`) or `owner/repo`.
- **Security & Integrity Checks:**
  - URL regex filtering prohibiting flags, argument injection, path traversal, or non-GitHub domains.
  - Controlled shallow clone (`--depth 1`) with disk size cap ($\le 250$ MB).
  - Strict sandboxing: Cloned source code is never executed.
  - AST chunk extraction and incremental index ingestion into BM25 and Dense stores.

### Phase 5B — Incremental Repository Updates & History Tracking
- **Git Diff Sync:** Compares previous commit SHA with remote `HEAD`, extracts added, modified, and deleted files (`git diff --name-status`).
- **Selective Pruning & Index Compaction:** Prunes outdated chunks from BM25 and Dense embedding stores without rebuilding from scratch.
- **Persistent History Log:** Records SHA changes, chunk counts, durations, and status in `data/metadata/indexing_history.jsonl`.

### Phase 5C — Optional Non-Blocking User Authentication
- **Security-First Architecture:** PBKDF2-HMAC-SHA256 password hashing with unique salts (100,000 iterations) and RFC 7519 HS256 JWT tokens.
- **Non-Blocking Access:** Anonymous users have full access; authenticated users get personalized saved repositories and search history logging.

### Phase 5D — Dense Semantic Retrieval Audit & Root-Cause Analysis
- **Empirical Benchmark:** Audit across 50 test queries pinpointed root causes of custom encoder performance:
  - BM25 Baseline: Recall@1 = 100%, MRR = 1.000.
  - From-scratch 4-layer CodeEncoder: Recall@1 = 22.0%, MRR = 0.3257 (trained on 35 quality-gated QA pairs, 500-chunk store cap).
  - Hybrid + Exact Symbol Boost: Recall@1 = 100%, MRR = 1.000.

### Phase 5E — Static Symbol Graph Index & Advanced Code Understanding
- **Relationship Extraction:** Parses function calls, class inheritance (`extends`, `implements`, Python bases), file imports, and test suites.
- **Truthful Verification Levels:**
  - `directly_verified`: Explicit definitions and intra-repo references.
  - `statically_inferred`: Identifier usage matching repo symbols across files.
  - `unverified_assumption`: Dynamic or external third-party library calls.

### Phase 5F — Multi-File Flow Synthesis & Missing Evidence Detection
- **Architectural Flow Presentation:** Labels multi-component queries with `[Core Component]`, `[Inbound Invocation]`, `[Internal Delegation]`, and `[Verification]`.
- **Missing Evidence Notices:** Explicitly flags unindexed registration or dispatch mechanisms without hallucinating.
- **Citation Discipline:** Guarantees 100% of mentioned files have matching citations.

### Phase 5H & 5I — Production Hardening & Product Experience
- **Rate Limiting:** Built-in sliding window rate limiter (120 req/min per IP).
- **Answer Feedback:** In-app feedback buttons (`Helpful`, `Not helpful`, `Incorrect citation`, `Missing context`).
- **Automated Tests:** 64 passing automated tests in `tests/`.

---

## 3. Retrieval Benchmark Evaluation

Reported retrieval metrics across test suites and audit queries:

| Method | Recall@1 | Recall@5 | Recall@10 | MRR | Description |
|---|---:|---:|---:|---:|---|
| **BM25 Lexical** | 100.0% | 100.0% | 100.0% | 1.0000 | Sub-token identifier splitting (camelCase & snake_case) |
| **Custom Dense Encoder** | 22.0% | 38.0% | 46.0% | 0.3257 | Custom 4-layer PyTorch Transformer (trained from scratch) |
| **Hybrid Standard RRF** | 64.0% | 84.0% | 88.0% | 0.7516 | Reciprocal rank fusion ($k=60$) |
| **Hybrid + Exact Symbol Boost** | **100.0%** | **100.0%** | **100.0%** | **1.0000** | **Exact symbol boost (+10.0) with match classification** |

---

## 4. Quick Start & Local Execution

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Git

### Step 1: Backend Setup
```bash
# Activate virtual environment
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Start FastAPI backend (port 8000)
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation is available at `http://127.0.0.1:8000/docs`.

### Step 2: Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
The application opens at `http://localhost:5173`.

### Step 3: Run Automated Tests
```bash
# Run entire test suite (64 tests)
pytest -v
```

---

## 5. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System health, version, loaded repo count, index status |
| `GET` | `/api/repositories` | List all indexed repositories and chunk counts |
| `POST` | `/api/repositories/add` | Ingest live GitHub repository by URL or owner/repo |
| `POST` | `/api/repositories/{id}/sync` | Incremental Git update detection and index sync |
| `GET` | `/api/repositories/{id}/history` | Fetch indexing history for a repository |
| `GET` | `/api/history` | Fetch global indexing history across all repositories |
| `POST` | `/api/repositories/index` | Trigger BM25 and Dense index build |
| `POST` | `/api/search` | Search code chunks (Hybrid, BM25, or Dense) |
| `POST` | `/api/query` | Ask natural language question with grounded answer |
| `GET` | `/api/repositories/{id}/symbols/{name}` | Fetch symbol callers, callees, inheritance, and tests |
| `POST` | `/api/feedback` | Submit answer accuracy and citation feedback |
| `POST` | `/api/auth/register` | Register new user account |
| `POST` | `/api/auth/login` | Authenticate user and receive JWT token |
| `GET` | `/api/auth/me` | Fetch authenticated user profile |
| `GET` | `/api/repositories/{id}/files` | List indexed files for repository |
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
Use the included `Dockerfile` or `render.yaml`:
```bash
docker build -t github-knowledge-assistant .
docker run -p 8000:8000 github-knowledge-assistant
```

---

## 7. License
Apache License 2.0.
