# GitHub Knowledge Assistant - Frontend

Modern React + TypeScript + Vite + Tailwind CSS web application for the GitHub Knowledge Assistant.

## Features
- **Landing Page (`/`)**: Value proposition, interactive QA demo, architecture summary.
- **System Dashboard (`/dashboard`)**: Statistics for 10 repositories, 243,411 chunks, and retrieval evaluation benchmarks.
- **Repository Explorer (`/repositories`)**: Filter repositories by language and browse file structures.
- **AI Code Assistant (`/assistant`)**: Natural language question answering with mode selection (Hybrid/BM25/Dense), suggested prompts, and source code evidence inspector.
- **Code Search Explorer (`/search`)**: Real-time code search across AST chunks with score rankings and match classifications.
- **Code Evidence Viewer (`/evidence/:repoId/:chunkId`)**: Full syntax-highlighted code chunk viewer with line numbers and AST symbol inspection.
- **Repository Indexing (`/indexing`)**: Live index status and triggers for re-indexing BM25 and Dense stores.

## Quick Start

### 1. Install Dependencies
```bash
npm install
```

### 2. Run Development Server
```bash
npm run dev
```
The app will run at `http://localhost:5173`. API requests to `/api` and `/health` are proxied to `http://127.0.0.1:8000`.

### 3. Build for Production
```bash
npm run build
```
Generates production build in `dist/`.
