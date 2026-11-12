import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict

from dataset_pipeline.common import DATA, stream_read
from retrieval.bm25_index import BM25Retriever, build_and_save_bm25_index
from retrieval.dense_index import DenseRetriever
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.context_expander import ContextExpander
from retrieval.answer_engine import AnswerEngine


class RetrievalService:
    """Singleton service orchestrating retrieval, context expansion, and QA."""

    _instance: Optional["RetrievalService"] = None

    def __init__(self):
        self.bm25_index_path = DATA / "indexes" / "bm25_index.pkl"
        self.dense_store_dir = DATA / "indexes" / "dense_store"
        self.chunks_path = DATA / "processed" / "code_chunks.jsonl"
        self.repos_path = DATA / "metadata" / "repositories.jsonl"

        self.bm25: Optional[BM25Retriever] = None
        self.dense: Optional[DenseRetriever] = None
        self.hybrid: Optional[HybridRetriever] = None
        self.expander: Optional[ContextExpander] = None
        self.answer_engine: Optional[AnswerEngine] = None

        self._load_or_init()

    @classmethod
    def get_instance(cls) -> "RetrievalService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_or_init(self) -> None:
        """Initialize components if indexes exist on disk."""
        if self.bm25_index_path.exists():
            self.bm25 = BM25Retriever(self.bm25_index_path)

        try:
            self.dense = DenseRetriever(store_dir=self.dense_store_dir)
        except Exception as e:
            print(f"[WARN] Dense retriever not initialized: {e}")
            self.dense = None

        if self.bm25 and self.dense:
            self.hybrid = HybridRetriever(self.bm25, self.dense)

        # Context expander
        if self.bm25 and self.bm25.corpus_meta:
            chunk_dict = {m["chunk_id"]: m for m in self.bm25.corpus_meta}
            self.expander = ContextExpander(chunk_dict)
            if self.hybrid:
                self.answer_engine = AnswerEngine(self.hybrid, self.expander)

    def trigger_indexing(self, max_chunks: Optional[int] = 10000) -> Dict[str, Any]:
        """Build or update persistent BM25 and Dense indexes."""
        chunks = []
        for c in stream_read(self.chunks_path):
            chunks.append(c)
            if max_chunks and len(chunks) >= max_chunks:
                break

        # 1. Build and persist BM25
        self.bm25 = BM25Retriever()
        self.bm25.build_index(chunks)
        self.bm25.save(self.bm25_index_path)

        # 2. Build and persist Dense
        self.dense = DenseRetriever(store_dir=self.dense_store_dir)
        dense_added = self.dense.build_index(chunks)

        # 3. Rebuild Hybrid & Context Expander
        self.hybrid = HybridRetriever(self.bm25, self.dense)
        chunk_dict = {m["chunk_id"]: m for m in self.bm25.corpus_meta}
        self.expander = ContextExpander(chunk_dict)
        self.answer_engine = AnswerEngine(self.hybrid, self.expander)

        return {
            "bm25_count": len(self.bm25.corpus_meta),
            "dense_count": len(self.dense.store),
            "status": "success"
        }

    def list_repositories(self) -> List[Dict[str, Any]]:
        """List all collected repositories and their chunk counts."""
        repos = list(stream_read(self.repos_path)) if self.repos_path.exists() else []
        repo_counts = defaultdict(int)

        if self.bm25 and self.bm25.corpus_meta:
            for m in self.bm25.corpus_meta:
                repo_counts[m["repo_id"]] += 1

        results = []
        for r in repos:
            rid = r["repo_id"]
            results.append({
                "repo_id": rid,
                "full_name": r.get("full_name", rid),
                "language": r.get("language"),
                "stars": r.get("stars"),
                "license_spdx_id": r.get("license_spdx_id"),
                "default_branch": r.get("default_branch"),
                "clone_status": r.get("clone_status", "unknown"),
                "chunk_count": repo_counts[rid]
            })
        return results

    def list_files(self, repo_id: str) -> List[Dict[str, Any]]:
        """List files in repository with chunk counts."""
        file_counts = defaultdict(int)
        file_lang = {}

        if self.bm25 and self.bm25.corpus_meta:
            for m in self.bm25.corpus_meta:
                if m["repo_id"] == repo_id:
                    fpath = m["file_path"]
                    file_counts[fpath] += 1
                    file_lang[fpath] = m.get("language")

        return [
            {
                "file_path": fpath,
                "repo_id": repo_id,
                "chunk_count": count,
                "language": file_lang.get(fpath)
            }
            for fpath, count in sorted(file_counts.items())
        ]

    def get_chunk(self, repo_id: str, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full chunk record by ID."""
        if self.bm25 and chunk_id in self.bm25.chunk_id_to_idx:
            idx = self.bm25.chunk_id_to_idx[chunk_id]
            meta = self.bm25.corpus_meta[idx]
            if meta.get("repo_id") == repo_id:
                return meta

        # Fallback to linear scan if not in memory
        for c in stream_read(self.chunks_path):
            if c["chunk_id"] == chunk_id and c.get("repo_id") == repo_id:
                return c
        return None

    def search(self, query: str, top_k: int = 10, mode: str = "hybrid", repo_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.hybrid:
            raise RuntimeError("Retrieval engine is not initialized. Please trigger indexing first.")
        return self.hybrid.search(query=query, top_k=top_k, mode=mode, repo_id=repo_id)

    def query_qa(self, question: str, top_k: int = 5, mode: str = "hybrid", repo_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.answer_engine:
            raise RuntimeError("Answer engine is not initialized. Please trigger indexing first.")
        return self.answer_engine.answer_question(question=question, repo_id=repo_id, top_k=top_k, mode=mode)
