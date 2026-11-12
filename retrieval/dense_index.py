import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

import torch
import numpy as np
from tokenizers import Tokenizer

from dataset_pipeline.common import DATA, stream_read
from training.model import CodeEncoder, CodeEncoderConfig
from .embedding_store import EmbeddingStore


class DenseRetriever:
    """Dense Semantic Retrieval Engine using custom Transformer CodeEncoder and BPE Tokenizer."""

    def __init__(
        self,
        checkpoint_path: Path = Path("models/best_code_encoder.pt"),
        tokenizer_path: Path = Path("models/tokenizer/tokenizer.json"),
        store_dir: Path = Path("data/indexes/dense_store"),
        device: Optional[str] = None
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.checkpoint_path = Path(checkpoint_path)
        self.tokenizer_path = Path(tokenizer_path)
        self.store = EmbeddingStore(Path(store_dir))

        # 1. Validate checkpoint and tokenizer presence
        if not self.tokenizer_path.exists():
            raise FileNotFoundError(
                f"Required custom tokenizer missing at {self.tokenizer_path}.\n"
                "Please run 'python -m training.train_tokenizer' first."
            )
        if not self.checkpoint_path.exists():
            raise FileNotFoundError(
                f"Required custom CodeEncoder checkpoint missing at {self.checkpoint_path}.\n"
                "Please run 'python -m training.train_encoder' first."
            )

        # 2. Load custom tokenizer and model
        self.tokenizer = Tokenizer.from_file(str(self.tokenizer_path))
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
        self.config = CodeEncoderConfig.from_dict(checkpoint.get("config", {}))

        self.model = CodeEncoder(self.config)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.pad_id = self.tokenizer.token_to_id("<pad>") or 0
        print(f"DenseRetriever loaded custom encoder from {self.checkpoint_path} on {self.device}.")

    def encode_texts(self, texts: List[str], batch_size: int = 32, max_seq_len: int = 512) -> np.ndarray:
        """Tokenize and encode text strings into L2-normalized dense embeddings."""
        all_embeddings = []

        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_ids = []
                batch_masks = []

                for text in batch_texts:
                    enc = self.tokenizer.encode(text or "")
                    ids = enc.ids[:max_seq_len]
                    mask = [1] * len(ids)
                    pad_len = max_seq_len - len(ids)
                    ids += [self.pad_id] * pad_len
                    mask += [0] * pad_len
                    batch_ids.append(ids)
                    batch_masks.append(mask)

                inp = torch.tensor(batch_ids, dtype=torch.long, device=self.device)
                att = torch.tensor(batch_masks, dtype=torch.long, device=self.device)
                embs = self.model(inp, attention_mask=att)
                all_embeddings.append(embs.cpu().numpy())

        if not all_embeddings:
            return np.empty((0, self.config.hidden_dim))
        return np.vstack(all_embeddings)

    def build_index(self, chunks: List[Dict[str, Any]], batch_size: int = 32, max_snippet_len: int = 400) -> int:
        """Incrementally encode and store chunks."""
        new_chunks = [c for c in chunks if not self.store.contains(c["chunk_id"])]
        if not new_chunks:
            print("All chunks are already indexed in dense store.")
            return 0

        print(f"Encoding {len(new_chunks)} new chunks for dense index...")
        texts_to_encode = [c.get("code_text", "") for c in new_chunks]
        embs = self.encode_texts(texts_to_encode, batch_size=batch_size, max_seq_len=self.config.max_seq_len)

        metadata_list = []
        for c in new_chunks:
            meta = {
                "chunk_id": c["chunk_id"],
                "repo_id": c.get("repo_id", ""),
                "file_path": c.get("file_path", ""),
                "start_line": c.get("start_line", 1),
                "end_line": c.get("end_line", 1),
                "chunk_type": c.get("chunk_type", ""),
                "chunk_name": c.get("chunk_name", ""),
                "language": c.get("language", ""),
                "symbols_defined": c.get("symbols_defined", []),
                "symbols_used": c.get("symbols_used", []),
                "imports": c.get("imports", []),
                "code_snippet": c.get("code_text", "")[:max_snippet_len],
                "code_text": c.get("code_text", "")
            }
            metadata_list.append(meta)

        added = self.store.add_batch(embs, metadata_list)
        self.store.save()
        return added

    def search(
        self,
        query: str,
        top_k: int = 10,
        repo_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Dense semantic search using cosine similarity (dot product on unit vectors)."""
        if self.store.embeddings is None or len(self.store.embeddings) == 0:
            return []

        query_emb = self.encode_texts([query], batch_size=1, max_seq_len=self.config.max_seq_len)[0]
        # Dot product similarity against corpus
        scores = np.dot(self.store.embeddings, query_emb)

        ranked_indices = np.argsort(-scores)

        results = []
        rank = 1
        for idx in ranked_indices:
            score = float(scores[idx])
            meta = self.store.metadata[idx]
            if repo_id and meta.get("repo_id") != repo_id:
                continue

            item = dict(meta)
            item["score"] = round(score, 4)
            item["retrieval_method"] = "dense"
            item["rank"] = rank
            results.append(item)
            rank += 1
            if len(results) >= top_k:
                break

        return results


def build_and_save_dense_index(
    chunks_path: Path,
    store_dir: Path,
    max_chunks: Optional[int] = None
) -> DenseRetriever:
    """Convenience function to load chunks and construct dense vector index."""
    retriever = DenseRetriever(store_dir=store_dir)
    chunks = []
    print(f"Reading chunks from {chunks_path}...")
    for c in stream_read(chunks_path):
        chunks.append(c)
        if max_chunks and len(chunks) >= max_chunks:
            break

    retriever.build_index(chunks)
    return retriever


def main():
    parser = argparse.ArgumentParser(description="Build or query persistent dense index.")
    parser.add_argument("--chunks", type=str, default=str(DATA / "processed" / "code_chunks.jsonl"), help="Chunks JSONL path")
    parser.add_argument("--store-dir", type=str, default=str(DATA / "indexes" / "dense_store"), help="Dense store dir")
    parser.add_argument("--query", type=str, default=None, help="Query text to search")
    parser.add_argument("--max-chunks", type=int, default=5000, help="Max chunks to index")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K results")
    args = parser.parse_args()

    store_dir = Path(args.store_dir)
    retriever = DenseRetriever(store_dir=store_dir)

    if not retriever.store.exists() or len(retriever.store) == 0:
        chunks = []
        for c in stream_read(Path(args.chunks)):
            chunks.append(c)
            if args.max_chunks and len(chunks) >= args.max_chunks:
                break
        retriever.build_index(chunks)

    if args.query:
        print(f"\nQuery: '{args.query}'")
        results = retriever.search(args.query, top_k=args.top_k)
        for r in results:
            print(f"[{r['rank']}] Score: {r['score']} | {r['repo_id']} | {r['file_path']}:{r['start_line']}-{r['end_line']} | {r['chunk_name']}")


if __name__ == "__main__":
    main()
