import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict

from dataset_pipeline.common import DATA, stream_read
from retrieval.bm25_index import BM25Retriever, build_and_save_bm25_index
from retrieval.dense_index import DenseRetriever
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.context_expander import ContextExpander
from retrieval.answer_engine import AnswerEngine
from retrieval.symbol_graph import SymbolGraphIndex


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
        self.symbol_graph: Optional[SymbolGraphIndex] = None

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

        # Context expander & Symbol graph
        if self.bm25 and self.bm25.corpus_meta:
            chunk_dict = {m["chunk_id"]: m for m in self.bm25.corpus_meta}
            self.expander = ContextExpander(chunk_dict)
            self.symbol_graph = SymbolGraphIndex(self.bm25.corpus_meta)
            if self.hybrid:
                self.answer_engine = AnswerEngine(self.hybrid, self.expander, self.symbol_graph)

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

        # 3. Rebuild Hybrid & Context Expander & Symbol Graph
        self.hybrid = HybridRetriever(self.bm25, self.dense)
        chunk_dict = {m["chunk_id"]: m for m in self.bm25.corpus_meta}
        self.expander = ContextExpander(chunk_dict)
        self.symbol_graph = SymbolGraphIndex(self.bm25.corpus_meta)
        self.answer_engine = AnswerEngine(self.hybrid, self.expander, self.symbol_graph)

        return {
            "bm25_count": len(self.bm25.corpus_meta),
            "dense_count": len(self.dense.store),
            "status": "success"
        }

    def add_repository_chunks(self, new_chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """Incrementally update BM25 index, Dense index, and ContextExpander with new repository chunks."""
        if not new_chunks:
            return {"bm25_added": 0, "dense_added": 0}

        bm25_added = 0
        dense_added = 0

        if self.bm25:
            bm25_added = self.bm25.add_chunks(new_chunks)

        if self.dense:
            dense_added = self.dense.build_index(new_chunks)
            self.dense.store.save()

        # Hot-reload ContextExpander, SymbolGraph, and AnswerEngine with updated metadata
        if self.bm25 and self.bm25.corpus_meta:
            chunk_dict = {m["chunk_id"]: m for m in self.bm25.corpus_meta}
            self.expander = ContextExpander(chunk_dict)
            if self.symbol_graph:
                self.symbol_graph.build_graph(new_chunks)
            else:
                self.symbol_graph = SymbolGraphIndex(self.bm25.corpus_meta)
            if self.hybrid:
                self.answer_engine = AnswerEngine(self.hybrid, self.expander, self.symbol_graph)

        return {
            "bm25_added": bm25_added,
            "dense_added": dense_added
        }

    def remove_and_update_repository_chunks(
        self,
        remove_chunk_ids: Set[str],
        new_chunks: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Atomically remove outdated chunks and add new chunks across BM25 and Dense indexes."""
        bm25_removed = 0
        bm25_added = 0
        dense_removed = 0
        dense_added = 0

        if self.bm25:
            bm25_removed, bm25_added = self.bm25.remove_and_update_chunks(remove_chunk_ids, new_chunks)

        if self.dense:
            if remove_chunk_ids:
                dense_removed = self.dense.store.remove_chunks(remove_chunk_ids)
            if new_chunks:
                dense_added = self.dense.build_index(new_chunks)
            self.dense.store.save()

        # Hot-reload ContextExpander, SymbolGraph, and AnswerEngine with updated metadata
        if self.bm25 and self.bm25.corpus_meta:
            chunk_dict = {m["chunk_id"]: m for m in self.bm25.corpus_meta}
            self.expander = ContextExpander(chunk_dict)
            if self.symbol_graph:
                if remove_chunk_ids:
                    self.symbol_graph.remove_chunks(remove_chunk_ids)
                if new_chunks:
                    self.symbol_graph.build_graph(new_chunks)
            else:
                self.symbol_graph = SymbolGraphIndex(self.bm25.corpus_meta)
            if self.hybrid:
                self.answer_engine = AnswerEngine(self.hybrid, self.expander, self.symbol_graph)

        return {
            "bm25_removed": bm25_removed,
            "bm25_added": bm25_added,
            "dense_removed": dense_removed,
            "dense_added": dense_added
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

    def get_symbol_relationships(self, symbol_name: str, repo_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch static relationships (definitions, callers, callees, inheritance, tests) for a symbol."""
        if not self.symbol_graph:
            if self.bm25 and self.bm25.corpus_meta:
                self.symbol_graph = SymbolGraphIndex(self.bm25.corpus_meta)
            else:
                self.symbol_graph = SymbolGraphIndex()
        return self.symbol_graph.get_symbol_relationships(symbol_name=symbol_name, repo_id=repo_id)
