import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np


class EmbeddingStore:
    """Persistent on-disk vector store with incremental indexing support."""

    def __init__(self, store_dir: Path):
        self.store_dir = store_dir
        self.embeddings: Optional[np.ndarray] = None
        self.metadata: List[Dict[str, Any]] = []
        self.chunk_id_to_idx: Dict[str, int] = {}

        if (store_dir / "embeddings.npy").exists() and (store_dir / "metadata.json").exists():
            self.load()

    def exists(self) -> bool:
        return (self.store_dir / "embeddings.npy").exists() and (self.store_dir / "metadata.json").exists()

    def __len__(self) -> int:
        return len(self.metadata)

    def contains(self, chunk_id: str) -> bool:
        return chunk_id in self.chunk_id_to_idx

    def add_batch(self, new_embeddings: np.ndarray, new_metadata: List[Dict[str, Any]]) -> int:
        """Incrementally append new embeddings and metadata."""
        if len(new_embeddings) != len(new_metadata):
            raise ValueError("Mismatched embeddings and metadata counts")

        valid_embs = []
        valid_meta = []
        start_idx = len(self.metadata)

        for i, meta in enumerate(new_metadata):
            cid = meta["chunk_id"]
            if cid in self.chunk_id_to_idx:
                continue
            valid_embs.append(new_embeddings[i])
            valid_meta.append(meta)
            self.chunk_id_to_idx[cid] = start_idx + len(valid_meta) - 1

        if not valid_embs:
            return 0

        valid_embs_mat = np.vstack(valid_embs)
        if self.embeddings is None or len(self.embeddings) == 0:
            self.embeddings = valid_embs_mat
        else:
            self.embeddings = np.vstack([self.embeddings, valid_embs_mat])

        self.metadata.extend(valid_meta)
        return len(valid_meta)

    def save(self) -> None:
        """Persist embeddings matrix and metadata to disk."""
        self.store_dir.mkdir(parents=True, exist_ok=True)
        if self.embeddings is not None:
            np.save(str(self.store_dir / "embeddings.npy"), self.embeddings)
        (self.store_dir / "metadata.json").write_text(
            json.dumps(self.metadata, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"Embedding store saved to {self.store_dir} ({len(self.metadata)} records).")

    def load(self) -> None:
        """Load persistent vector store from disk."""
        emb_file = self.store_dir / "embeddings.npy"
        meta_file = self.store_dir / "metadata.json"

        if emb_file.exists():
            self.embeddings = np.load(str(emb_file))
        if meta_file.exists():
            self.metadata = json.loads(meta_file.read_text(encoding="utf-8"))
            self.chunk_id_to_idx = {m["chunk_id"]: idx for idx, m in enumerate(self.metadata)}
        print(f"Loaded EmbeddingStore from {self.store_dir} ({len(self.metadata)} records).")
