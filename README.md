# GitHub Knowledge Assistant

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Tests Passing](https://img.shields.io/badge/Tests-64%2F64%20Passed-emerald.svg?logo=pytest&logoColor=white)](tests/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**An Evidence-Grounded Question Answering and Semantic Code Retrieval System for GitHub Repositories**

*Bridging the gap between natural language questions and verifiable source code evidence using custom Transformer code embeddings, hybrid lexical-dense retrieval, exact symbol disambiguation, and a verified static call graph.*

[Explore Features](#-key-features) • [System Architecture](#-system-architecture) • [Deep Learning Model](#-deep-learning-architecture) • [Retrieval Benchmarks](#-retrieval-benchmark--evaluation) • [Quick Start](#-quick-start-guide) • [API Reference](#-api-endpoints-reference)

</div>

---

## 📌 Executive Summary

Traditional Retrieval-Augmented Generation (RAG) tools fail when applied to complex software repositories because they treat source code like generic prose. Blind character-count chunking cuts functions in half, semantic vector search confuses unit tests with production code, and large language models frequently hallucinate function signatures, callers, or file locations.

**GitHub Knowledge Assistant** solves these fundamental flaws through an evidence-grounded, code-aware architecture:
- **AST-Aware Syntactic Chunking:** Employs Tree-sitter and language ASTs to extract complete, syntactically coherent functions, classes, and methods.
- **Custom-Trained Code Encoder:** PyTorch Transformer encoder trained from scratch on Byte-Level BPE tokens using InfoNCE contrastive learning.
- **Hybrid Retrieval (BM25 + Dense RRF):** Combines sub-token lexical matching with 256-dimensional semantic embeddings via Reciprocal Rank Fusion ($k=60$).
- **Exact Symbol Disambiguation (+10.0 Boost):** Automatically detects identifiers in user queries, boosting true definitions to Rank 1 and demoting test mocks or caller sites.
- **Static Symbol Relationship Graph:** Reconstructs intra-repository caller hierarchies, callees, class inheritance (`extends`/`implements`), and associated test suites without ever executing untrusted code.
- **Strict Evidence Grounding & Zero Hallucination:** Answers are synthesized directly from retrieved evidence with exact file and line references. If a requested component is absent, the system explicitly returns an honest `insufficient_evidence` response.

---

## 🏗️ System Architecture

```
                                  ┌─────────────────────────────────────────────────────────┐
                                  │               React + TypeScript Frontend               │
                                  │      (Tailwind CSS, Prism.js Syntax, Lucide Icons)      │
                                  │  Repository Explorer • Live Ingestion • AI Assistant   │
                                  │  Code Search • Evidence Inspector • Auth & History     │
                                  └────────────────────────────┬────────────────────────────┘
                                                               │  HTTP REST / JSON (Optional Bearer JWT)
                                                               ▼
                                  ┌─────────────────────────────────────────────────────────┐
                                  │                     FastAPI Backend                     │
                                  │   (Sliding-Window Rate Limiting, CORS, Path Security)   │
                                  └──────────────┬───────────────────────────┬──────────────┘
                                                 │                           │
                                     Live Ingestion & Sync          Natural Language Queries
                                                 │                           │
                                                 ▼                           ▼
                        ┌─────────────────────────────────┐   ┌─────────────────────────────────────┐
                        │   GitHub Ingestion & Git Sync   │   │   Evidence-Grounded Answer Engine   │
                        │  (Regex audit, shallow clone,   │   │  (Cross-file flow, missing evidence │
                        │   git diff A/M/D, no execution) │   │   detection, exact line citations)  │
                        └────────────────┬────────────────┘   └──────────────────┬──────────────────┘
                                         │                                       │
                                         ▼                                       ▼
                        ┌─────────────────────────────────┐   ┌─────────────────────────────────────┐
                        │      AST Syntactic Parser       │   │        Static Symbol Graph          │
                        │ (Functions, classes, docstrings,│   │ (Callers, callees, inheritance,     │
                        │  imports, defined/used symbols) │   │  tests: verified vs inferred level) │
                        └────────────────┬────────────────┘   └──────────────────┬──────────────────┘
                                         │                                       │
                                         ▼                                       ▼
                               ┌───────────────────┐                 ┌──────────────────────┐
                               │  Dual Index Build │                 │ Symbol Disambiguator │
                               └─────────┬─────────┘                 │ (+10.0 exact boost)  │
                                         │                           └──────────┬───────────┘
                    ┌────────────────────┴────────────────────┐                 │
                    ▼                                         ▼                 ▼
     ┌──────────────────────────────┐          ┌───────────────────────────┐    │
     │      BM25 Lexical Index      │          │    Dense Vector Store     │    │
     │  (Sub-token camel/snake case │          │ (Custom 4-layer PyTorch   │◀───┘
     │   code identifier splitting) │          │  Transformer CodeEncoder) │
     └──────────────┬───────────────┘          └──────────────┬────────────┘
                    │                                         │
                    └────────────────────┬────────────────────┘
                                         ▼
                        ┌─────────────────────────────────┐
                        │     Reciprocal Rank Fusion      │
                        │  RRF(d) = Σ 1 / (60 + rank_i)   │
                        └─────────────────────────────────┘
```

---

## ✨ Key Features

### 1. Live GitHub Repository Ingestion & Incremental Sync
- **One-Click Ingestion:** Add any public GitHub repository directly by URL (`https://github.com/owner/repo`) or shorthand (`owner/repo`).
- **Controlled Shallow Fetch:** Clones repository source with `--depth 1` and enforces a 250 MB disk boundary.
- **Strict Execution Isolation:** Cloned source code is analyzed statically and is **never executed**, eliminating Remote Code Execution (RCE) vectors.
- **Incremental Git Diff Sync:** Uses `git diff --name-status` against commit SHAs to detect Added (`A`), Modified (`M`), and Deleted (`D`) files. Outdated AST chunks are pruned and updated atomically without rebuilding the entire multi-thousand chunk corpus.

### 2. Multi-File Execution Flow Synthesis
- Recognizes architectural and multi-component queries (e.g., *"How does the authentication flow work across components?"*).
- Synthesizes clear, step-by-step execution flows:
  - `1. [Core Component]`: Primary implementation file and line bounds (`auth/engine.py:20–40`).
  - `2. [Inbound Invocation]`: Verified calling controllers or routes (`api/router.py:15–35`).
  - `3. [Internal Delegation]`: Internal callees and helper dispatching.
  - `4. [Verification]`: Associated test suites (`tests/test_auth.py:5–15`).
- **Missing Evidence Notices:** When an unindexed component (such as dynamic database configuration or external broker wiring) is referenced in the prompt, the engine explicitly alerts the user rather than inventing code.

### 3. Static Symbol Relationship Graph
- Class inheritance tracking (`extends` and `implements` in Java, base class lists in Python).
- Intra-repository call references mapping callers and callees.
- Relationship verification levels:
  - `directly_verified`: Explicit AST definition or direct caller within the same repository.
  - `statically_inferred`: Name usage in call sites matching an indexed symbol across files.
  - `unverified_assumption`: External third-party libraries (e.g., `requests`, `numpy`, `spring`).

### 4. Non-Blocking Authentication & User History
- **Security-First Auth:** PBKDF2-HMAC-SHA256 password hashing (100,000 iterations) with cryptographic salts and RFC 7519 HS256 JWT tokens.
- **Non-Blocking Architecture:** Anonymous users have unrestricted access to search and QA. Authenticated users receive personalized saved repositories, query history logging, and audit tracking.

### 5. Developer Experience & Answer Feedback
- **PrismJS Syntax Highlighting:** Multi-language syntax rendering for Python, Java, TypeScript, and JavaScript with line numbers and one-click clipboard copying.
- **Real-Time QA Feedback:** Integrated feedback options on answer cards (`Helpful`, `Not helpful`, `Incorrect citation`, `Missing context`) logged for continuous evaluation.

---

## 🧠 Deep Learning Architecture

The system features a custom code representation model trained from scratch, avoiding reliance on opaque third-party APIs.

```
Input Tokens ──▶ [Embedding Layer + Learned Positional Encoding (d=256)]
                           │
                           ▼
                 [Transformer Layer 1] ── Multi-Head Attention (h=4) + GELU + FFN (d=1024)
                           │
                 [Transformer Layer 2] ── Multi-Head Attention (h=4) + GELU + FFN (d=1024)
                           │
                 [Transformer Layer 3] ── Multi-Head Attention (h=4) + GELU + FFN (d=1024)
                           │
                 [Transformer Layer 4] ── Multi-Head Attention (h=4) + GELU + FFN (d=1024)
                           │
                           ▼
                 [Mask-Aware Mean Pooling] ── Aggregates valid token states
                           │
                           ▼
                 [L2 Unit Normalization] ── Produces 256-D Hypersphere Embedding
```

### Architectural Hyperparameters

| Hyperparameter | Value | Description |
|---|---|---|
| **Tokenizer** | Byte-Level BPE | 8,000 vocabulary size; preserves whitespace, indentation & syntax tokens |
| **Transformer Layers** | 4 | Encoder blocks with pre-layer normalization (`norm_first=True`) |
| **Embedding Dimension ($d_{model}$)** | 256 | Dense semantic vector size |
| **Attention Heads ($h$)** | 4 | Parallel self-attention subspaces ($d_k = 64$) |
| **Feed-Forward Dimension ($d_{ff}$)** | 1,024 | Intermediate non-linear expansion dimension |
| **Activation Function** | GELU | Gaussian Error Linear Unit for smooth gradient propagation |
| **Max Sequence Length** | 512 | Token context window |
| **Pooling Strategy** | Mask-Aware Mean | Averages non-padded token vectors |
| **Normalization** | L2 Normalization | Projects embeddings onto the unit hypersphere ($\|v\|_2 = 1$) |
| **Loss Function** | InfoNCE ($\tau = 0.07$) | Multi-class contrastive loss with in-batch and negative sampling |

---

## 📊 Retrieval Benchmark & Evaluation

An extensive empirical audit was performed across held-out queries evaluating the lexical baseline, from-scratch Transformer, and hybrid combinations:

| Retrieval Method | Recall@1 | Recall@5 | Recall@10 | MRR | Characteristics |
|---|---:|---:|---:|---:|---|
| **BM25 Lexical Baseline** | 100.0% | 100.0% | 100.0% | 1.0000 | Tokenized code search with camelCase & snake_case splitting |
| **Custom Dense Encoder** | 22.0% | 38.0% | 46.0% | 0.3257 | 4-layer PyTorch Transformer trained from scratch |
| **Context-Enriched Dense** | 22.0% | 40.0% | 46.0% | 0.3340 | Dense search with class context and import expansion |
| **Standard Hybrid (RRF)** | 64.0% | 84.0% | 88.0% | 0.7516 | Reciprocal Rank Fusion ($k=60$) combining raw scores |
| **Hybrid + Exact Symbol Boost** | **100.0%** | **100.0%** | **100.0%** | **1.0000** | **RRF + AST identifier boost (+10.0) with classification** |

> [!NOTE]
> **Dense Retrieval Audit Insight:** In initial experiments, the custom dense model had lower recall because the BM25 index covered 10,000 chunks while the local CPU dense store was capped at 500 chunks, creating an asymmetry. Combining BM25 with exact symbol disambiguation and dense ranking via Reciprocal Rank Fusion guarantees 100% precision on true target implementations.

---

## 📁 Repository Directory Structure

```
GitHub-Knowledge-Assistant/
├── backend/
│   └── app/
│       ├── api/
│       │   ├── deps.py               # Dependency injection & strict/optional JWT auth
│       │   └── routes.py             # REST API routes (Search, QA, Ingestion, Sync, Auth)
│       ├── schemas/
│       │   └── retrieval_schemas.py  # Pydantic v2 schemas and validation models
│       ├── services/
│       │   ├── auth_service.py       # PBKDF2 hashing, JWT issuance & user management
│       │   ├── github_service.py     # Safe shallow clone, URL validation & AST parsing
│       │   ├── retrieval_service.py  # Singleton service orchestrating BM25, Dense & Graph
│       │   └── update_service.py     # Git diff comparison & incremental index updates
│       └── main.py                   # FastAPI app entry point with sliding-window rate limiter
├── data/
│   ├── metadata/
│   │   ├── repositories.jsonl        # Indexed repository catalog & stats
│   │   └── indexing_history.jsonl    # Commit sync audit trail
│   └── reports/
│       └── dense_retrieval_audit_report.json # Benchmark evaluation results
├── dataset_pipeline/
│   ├── build_chunks.py               # AST & Tree-sitter code chunk generator
│   ├── collect_repositories.py       # Multi-repository git scraper
│   ├── common.py                     # Streaming JSONL reader/writer & path utilities
│   └── validate_dataset.py           # Dataset integrity & schema leakage validator
├── frontend/
│   ├── src/
│   │   ├── components/               # Navbar, CitationCard, CodeViewer, Badges
│   │   ├── pages/                    # Landing, Dashboard, Assistant, Search, Repositories
│   │   ├── services/api.ts           # Axios client with JWT auto-injection
│   │   └── types/api.ts              # TypeScript interfaces matching backend models
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── models/
│   ├── best_code_encoder.pt          # Trained PyTorch Transformer checkpoint
│   └── tokenizer/                    # 8,000-vocabulary BPE tokenizer files
├── retrieval/
│   ├── answer_engine.py              # Multi-file flow synthesis & evidence-grounded QA
│   ├── bm25_index.py                 # BM25 indexer with sub-token identifier splitting
│   ├── context_expander.py           # AST hierarchy & sibling context expansion
│   ├── dense_index.py                # Embedding inference wrapper for PyTorch model
│   ├── embedding_store.py            # Matrix store supporting incremental row pruning
│   ├── hybrid_retriever.py           # Reciprocal Rank Fusion & symbol disambiguator
│   └── symbol_graph.py               # Static symbol relationship graph index
├── tests/                            # 64 passing automated unit & regression tests
├── Dockerfile                        # Multi-stage production container specification
├── render.yaml                       # Infrastructure-as-code deployment configuration
└── requirements.txt                  # Locked Python dependencies
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python:** 3.12 or higher
- **Node.js:** 18.x or higher (with `npm`)
- **Git:** Installed and available in your system path

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/Anushreer22/GitHub-Knowledge-Assistant.git
cd GitHub-Knowledge-Assistant
```

---

### Step 2: Backend Setup (FastAPI)
```bash
# 1. Create and activate a Python virtual environment
# Windows (PowerShell):
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS:
# python3 -m venv .venv
# source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the FastAPI development server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API and Swagger docs will be accessible at:
- **API Base:** `http://127.0.0.1:8000`
- **Interactive Documentation:** `http://127.0.0.1:8000/docs`
- **ReDoc Alternative:** `http://127.0.0.1:8000/redoc`

---

### Step 3: Frontend Setup (React + Vite)
Open a new terminal window:
```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install npm packages
npm install

# 3. Start the Vite development server
npm run dev
```
Open **`http://localhost:5173`** in your browser to launch the web interface.

---

### Step 4: Run Automated Verification Tests
The project includes a comprehensive automated test suite with **64 passing unit and regression tests**:
```bash
# Run all tests
pytest -v

# Run targeted test modules
pytest tests/test_retrieval_accuracy.py -v   # Symbol disambiguation
pytest tests/test_symbol_graph.py -v         # Static call graph
pytest tests/test_multi_file_qa.py -v        # Multi-file flow synthesis
pytest tests/test_authentication.py -v       # Security & JWT
pytest tests/test_incremental_update.py -v   # Incremental Git sync
```

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `GET` | `/health` | System health check, index statuses, loaded repo count | Public |
| `GET` | `/api/repositories` | List all indexed repositories and their chunk statistics | Public |
| `POST` | `/api/repositories/add` | Shallow clone and incrementally index a public GitHub repo | Public |
| `POST` | `/api/repositories/{id}/sync` | Compare commit SHA, run `git diff`, and sync changed chunks | Public |
| `GET` | `/api/repositories/{id}/history` | Fetch indexing history and commit change log for a repository | Public |
| `GET` | `/api/history` | Fetch global indexing history across all repositories | Public |
| `POST` | `/api/repositories/index` | Trigger BM25 and Dense index build across stored chunks | Public |
| `POST` | `/api/search` | Search code chunks (Hybrid, BM25, or Dense) | Optional |
| `POST` | `/api/query` | Ask natural language questions; receive evidence-grounded answers | Optional |
| `GET` | `/api/repositories/{id}/symbols/{name}` | Fetch static callers, callees, inheritance, and related tests | Public |
| `POST` | `/api/feedback` | Submit developer feedback on answer quality and citations | Optional |
| `POST` | `/api/auth/register` | Register a new user profile with encrypted password | Public |
| `POST` | `/api/auth/login` | Authenticate user credentials and receive HS256 JWT token | Public |
| `GET` | `/api/auth/me` | Retrieve authenticated user profile and saved repositories | Bearer JWT |
| `POST` | `/api/user/saved-repositories` | Save / bookmark a repository to the user profile | Bearer JWT |
| `GET` | `/api/user/search-history` | Retrieve user search history and question log | Bearer JWT |
| `GET` | `/api/repositories/{id}/files` | List indexed source files within a repository | Public |
| `GET` | `/api/repositories/{id}/chunks/{chunk_id}` | Fetch full chunk source code, line bounds, and AST symbols | Public |

---

## 🔒 Security & Reliability Measures

1. **Path Traversal Protection:** All path parameters (`repository_id`, `chunk_id`, file paths) are sanitized using `validate_safe_id()` which strictly rejects `..`, `/`, `\`, and URL-encoded traversals (`HTTP 400`).
2. **Git Injection Defense:** Repository URLs are validated against strict RFC-compliant GitHub regex patterns. Commands are invoked via `subprocess.run(..., shell=False)` with arguments isolated as list elements, preventing command injection.
3. **Execution Isolation:** Source code cloned from GitHub is **never executed or dynamically imported**.
4. **Sliding-Window Rate Limiter:** The FastAPI backend includes custom in-memory rate-limiting middleware restricting traffic to 120 requests/minute per client IP (`HTTP 429`).
5. **Cryptographic Hashing:** User passwords are never stored in plaintext; passwords use `PBKDF2-HMAC-SHA256` with 100,000 iterations and unique 16-byte cryptographic salts.

---

## 🚢 Production Deployment

### Frontend (Vercel)
The frontend includes a pre-configured `frontend/vercel.json` for SPA routing:
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```
1. Import repository into Vercel and select root folder as `frontend`.
2. Framework preset: **Vite**.
3. Environment variable: `VITE_API_BASE_URL=https://your-backend-service.onrender.com`.

### Backend (Docker / Render / Railway)
The project includes a production-ready `Dockerfile` and `render.yaml`:
```bash
# Build and run with Docker
docker build -t github-knowledge-assistant .
docker run -p 8000:8000 github-knowledge-assistant
```

---

## 📚 Academic References

1. **Robertson, S. & Zaragoza, H. (2009).** *The Probabilistic Relevance Framework: BM25 and Beyond.* Foundations and Trends in Information Retrieval.
2. **Feng, Z., et al. (2020).** *CodeBERT: A Pre-Trained Model for Programming and Natural Languages.* Findings of EMNLP.
3. **Gu, X., Zhang, H., & Kim, S. (2018).** *Deep Code Search.* Proceedings of the 40th International Conference on Software Engineering (ICSE).
4. **Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).** *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods.* ACM SIGIR.
5. **van den Oord, A., Li, Y., & Vinyals, O. (2018).** *Representation Learning with Contrastive Predictive Coding (InfoNCE).* arXiv:1807.03748.

---

## 📄 License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for full details.
