from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict

from dataset_pipeline.common import DATA, stream_read


class ContextExpander:
    """Enriches retrieved code chunks with parent class, sibling methods, imports, and cross-references.
    Strictly distinguishes directly verified references from inferred structural relationships.
    """

    def __init__(self, chunks_index: Optional[Dict[str, Dict[str, Any]]] = None):
        self.chunk_by_id: Dict[str, Dict[str, Any]] = chunks_index or {}
        self.file_to_chunks: Dict[tuple, List[str]] = defaultdict(list)
        self.repo_symbol_defs: Dict[tuple, List[str]] = defaultdict(list)

        if self.chunk_by_id:
            self._build_relational_indices()

    @classmethod
    def from_chunks_path(cls, chunks_path: Path, max_chunks: Optional[int] = None) -> "ContextExpander":
        """Build context expander from chunks JSONL."""
        index = {}
        count = 0
        print(f"Indexing relational context from {chunks_path}...")
        for c in stream_read(chunks_path):
            index[c["chunk_id"]] = c
            count += 1
            if max_chunks and count >= max_chunks:
                break
        print(f"ContextExpander initialized with {len(index)} chunks.")
        return cls(index)

    def _build_relational_indices(self) -> None:
        """Construct file and symbol definition inverted indices."""
        for cid, c in self.chunk_by_id.items():
            repo = c.get("repo_id", "")
            fpath = c.get("file_path", "")
            self.file_to_chunks[(repo, fpath)].append(cid)

            for sym in c.get("symbols_defined", []):
                self.repo_symbol_defs[(repo, sym)].append(cid)

    def expand_context(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Expand a single chunk into rich context without hallucinated relations."""
        cid = chunk.get("chunk_id", "")
        repo = chunk.get("repo_id", "")
        fpath = chunk.get("file_path", "")
        chunk_name = chunk.get("chunk_name", "")
        chunk_type = chunk.get("chunk_type", "")
        symbols_used = chunk.get("symbols_used", [])
        imports = chunk.get("imports", [])

        # 1. Sibling Methods in the same file
        sibling_chunks = []
        file_cids = self.file_to_chunks.get((repo, fpath), [])
        parent_class_candidate = None

        for sibling_id in file_cids:
            if sibling_id == cid:
                continue
            sc = self.chunk_by_id.get(sibling_id)
            if not sc:
                continue

            stype = sc.get("chunk_type", "")
            sname = sc.get("chunk_name", "")

            # Check if this sibling is an enclosing class
            if any(k in stype.lower() for k in ["class", "interface", "enum"]):
                if sc.get("start_line", 1) <= chunk.get("start_line", 1) and sc.get("end_line", 1) >= chunk.get("end_line", 1):
                    parent_class_candidate = {
                        "class_name": sname,
                        "class_type": stype,
                        "file_path": fpath,
                        "start_line": sc.get("start_line"),
                        "end_line": sc.get("end_line"),
                        "relationship_type": "inferred_enclosing_class"
                    }

            sibling_chunks.append({
                "chunk_id": sibling_id,
                "name": sname,
                "type": stype,
                "start_line": sc.get("start_line"),
                "end_line": sc.get("end_line"),
                "relationship_type": "verified_same_file_sibling"
            })

        # 2. Cross-referenced Symbol Definitions in the same repository
        resolved_references = []
        for sym in symbols_used[:10]:
            target_cids = self.repo_symbol_defs.get((repo, sym), [])
            for tcid in target_cids:
                if tcid != cid:
                    tc = self.chunk_by_id.get(tcid)
                    if tc:
                        resolved_references.append({
                            "symbol": sym,
                            "target_chunk_id": tcid,
                            "target_file": tc.get("file_path"),
                            "start_line": tc.get("start_line"),
                            "end_line": tc.get("end_line"),
                            "relationship_type": "verified_symbol_definition"
                        })
                        if len(resolved_references) >= 5:
                            break
            if len(resolved_references) >= 5:
                break

        return {
            "source_chunk": {
                "chunk_id": cid,
                "repo_id": repo,
                "file_path": fpath,
                "chunk_name": chunk_name,
                "chunk_type": chunk_type,
                "start_line": chunk.get("start_line"),
                "end_line": chunk.get("end_line"),
                "language": chunk.get("language")
            },
            "parent_class": parent_class_candidate,
            "imports": {
                "items": imports[:10],
                "relationship_type": "directly_declared_imports"
            },
            "same_file_siblings": sibling_chunks[:6],
            "resolved_symbol_references": resolved_references
        }
