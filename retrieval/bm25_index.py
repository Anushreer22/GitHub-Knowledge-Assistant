import re
import pickle
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

from rank_bm25 import BM25Okapi
from dataset_pipeline.common import DATA, stream_read

KEYWORDS = {
    "class", "def", "function", "return", "import", "from", "public", "private",
    "protected", "static", "final", "void", "int", "string", "boolean", "async",
    "await", "try", "catch", "except", "finally", "throws", "throw", "raise",
    "extends", "implements", "interface", "enum", "const", "let", "var", "new"
}


def tokenize_code(text: str) -> List[str]:
    """Code-aware tokenizer splitting camelCase, snake_case, paths, and preserving keywords."""
    if not text:
        return []

    tokens: List[str] = []
    # Extract words, identifiers, and path components
    raw_terms = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|/|[0-9]+", text)

    for term in raw_terms:
        term_lower = term.lower()
        tokens.append(term_lower)

        # Break camelCase / snake_case into sub-tokens
        sub_tokens = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+", term)
        for st in sub_tokens:
            st_lower = st.lower()
            if len(st_lower) >= 2 and st_lower != term_lower:
                tokens.append(st_lower)

    return tokens


class BM25Retriever:
    """Persistent BM25 Lexical Retrieval Engine for source code chunks."""

    def __init__(self, index_file: Optional[Path] = None):
        self.bm25: Optional[BM25Okapi] = None
        self.corpus_meta: List[Dict[str, Any]] = []
        self.corpus_tokens: List[set] = []
        self.chunk_id_to_idx: Dict[str, int] = {}
        self.index_file = index_file

        if index_file and index_file.exists():
            self.load(index_file)

    def build_index(self, chunks: List[Dict[str, Any]], max_snippet_len: int = 400) -> None:
        """Construct BM25 index from chunk records."""
        tokenized_corpus = []
        self.corpus_meta = []
        self.corpus_tokens = []
        self.chunk_id_to_idx = {}

        print(f"Tokenizing {len(chunks)} chunks for BM25...")
        for idx, c in enumerate(chunks):
            cid = c["chunk_id"]
            code_text = c.get("code_text", "")
            fpath = c.get("file_path", "")
            name = c.get("chunk_name", "")
            symbols = " ".join(c.get("symbols_defined", []) + c.get("symbols_used", []))

            doc_text = f"{fpath} {name} {symbols}\n{code_text}"
            tokens = tokenize_code(doc_text)
            tokenized_corpus.append(tokens)
            self.corpus_tokens.append(set(tokens))

            meta = {
                "chunk_id": cid,
                "repo_id": c.get("repo_id", ""),
                "file_path": fpath,
                "start_line": c.get("start_line", 1),
                "end_line": c.get("end_line", 1),
                "chunk_type": c.get("chunk_type", ""),
                "chunk_name": name,
                "language": c.get("language", ""),
                "symbols_defined": c.get("symbols_defined", []),
                "symbols_used": c.get("symbols_used", []),
                "imports": c.get("imports", []),
                "code_snippet": code_text[:max_snippet_len],
                "code_text": code_text,
                "citation": f"{c.get('repo_id', '')}:{fpath}#L{c.get('start_line', 1)}-L{c.get('end_line', 1)}"
            }
            self.corpus_meta.append(meta)
            self.chunk_id_to_idx[cid] = idx

        self.tokenized_corpus = tokenized_corpus
        self.bm25 = BM25Okapi(tokenized_corpus)
        print(f"BM25 index built with {len(self.corpus_meta)} documents.")

    def add_chunks(self, new_chunks: List[Dict[str, Any]], max_snippet_len: int = 400) -> int:
        """Incrementally add new chunks to existing BM25 index and rebuild internal ranking structures."""
        if not new_chunks:
            return 0

        unique_new = [c for c in new_chunks if c["chunk_id"] not in self.chunk_id_to_idx]
        if not unique_new:
            return 0

        # Reconstruct tokenized corpus for existing documents if not in memory
        tokenized_corpus = getattr(self, "tokenized_corpus", None)
        if tokenized_corpus is None or len(tokenized_corpus) != len(self.corpus_meta):
            tokenized_corpus = []
            for m in self.corpus_meta:
                symbols = " ".join(m.get("symbols_defined", []) + m.get("symbols_used", []))
                doc_text = f"{m.get('file_path', '')} {m.get('chunk_name', '')} {symbols}\n{m.get('code_text', '')}"
                tokenized_corpus.append(tokenize_code(doc_text))

        start_idx = len(self.corpus_meta)
        for idx_offset, c in enumerate(unique_new):
            cid = c["chunk_id"]
            code_text = c.get("code_text", "")
            fpath = c.get("file_path", "")
            name = c.get("chunk_name", "")
            symbols = " ".join(c.get("symbols_defined", []) + c.get("symbols_used", []))

            doc_text = f"{fpath} {name} {symbols}\n{code_text}"
            tokens = tokenize_code(doc_text)
            tokenized_corpus.append(tokens)
            self.corpus_tokens.append(set(tokens))

            meta = {
                "chunk_id": cid,
                "repo_id": c.get("repo_id", ""),
                "file_path": fpath,
                "start_line": c.get("start_line", 1),
                "end_line": c.get("end_line", 1),
                "chunk_type": c.get("chunk_type", ""),
                "chunk_name": name,
                "language": c.get("language", ""),
                "symbols_defined": c.get("symbols_defined", []),
                "symbols_used": c.get("symbols_used", []),
                "imports": c.get("imports", []),
                "code_snippet": code_text[:max_snippet_len],
                "code_text": code_text,
                "citation": f"{c.get('repo_id', '')}:{fpath}#L{c.get('start_line', 1)}-L{c.get('end_line', 1)}"
            }
            self.corpus_meta.append(meta)
            self.chunk_id_to_idx[cid] = start_idx + idx_offset

        self.tokenized_corpus = tokenized_corpus
        self.bm25 = BM25Okapi(tokenized_corpus)

        if self.index_file:
            self.save(self.index_file)

        print(f"BM25 index incrementally updated: added {len(unique_new)} chunks (total: {len(self.corpus_meta)}).")
        return len(unique_new)

    def remove_and_update_chunks(
        self,
        remove_chunk_ids: Set[str],
        new_chunks: List[Dict[str, Any]],
        max_snippet_len: int = 400
    ) -> Tuple[int, int]:
        """Atomically remove outdated chunks and add new chunks in BM25 index."""
        initial_count = len(self.corpus_meta)

        # 1. Keep chunks not in remove_chunk_ids
        kept_meta = [m for m in self.corpus_meta if m["chunk_id"] not in remove_chunk_ids]
        removed_count = initial_count - len(kept_meta)

        # 2. Add new chunks (excluding any already present in kept)
        kept_cids = {m["chunk_id"] for m in kept_meta}
        unique_new = [c for c in new_chunks if c["chunk_id"] not in kept_cids]

        full_meta = list(kept_meta)
        tokenized_corpus = []

        # Tokenize kept chunks
        for m in kept_meta:
            symbols = " ".join(m.get("symbols_defined", []) + m.get("symbols_used", []))
            doc_text = f"{m.get('file_path', '')} {m.get('chunk_name', '')} {symbols}\n{m.get('code_text', '')}"
            tokenized_corpus.append(tokenize_code(doc_text))

        # Tokenize and format new chunks
        for c in unique_new:
            cid = c["chunk_id"]
            code_text = c.get("code_text", "")
            fpath = c.get("file_path", "")
            name = c.get("chunk_name", "")
            symbols = " ".join(c.get("symbols_defined", []) + c.get("symbols_used", []))
            doc_text = f"{fpath} {name} {symbols}\n{code_text}"
            tokenized_corpus.append(tokenize_code(doc_text))

            meta = {
                "chunk_id": cid,
                "repo_id": c.get("repo_id", ""),
                "file_path": fpath,
                "start_line": c.get("start_line", 1),
                "end_line": c.get("end_line", 1),
                "chunk_type": c.get("chunk_type", ""),
                "chunk_name": name,
                "language": c.get("language", ""),
                "symbols_defined": c.get("symbols_defined", []),
                "symbols_used": c.get("symbols_used", []),
                "imports": c.get("imports", []),
                "code_snippet": code_text[:max_snippet_len],
                "code_text": code_text,
                "citation": f"{c.get('repo_id', '')}:{fpath}#L{c.get('start_line', 1)}-L{c.get('end_line', 1)}"
            }
            full_meta.append(meta)

        self.corpus_meta = full_meta
        self.corpus_tokens = [set(t) for t in tokenized_corpus]
        self.chunk_id_to_idx = {m["chunk_id"]: idx for idx, m in enumerate(full_meta)}
        self.tokenized_corpus = tokenized_corpus
        self.bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else BM25Okapi([[]])

        if self.index_file:
            self.save(self.index_file)

        return removed_count, len(unique_new)

    def search(
        self,
        query: str,
        top_k: int = 10,
        repo_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search code chunks using BM25 scoring."""
        if not self.bm25 or not self.corpus_meta:
            return []

        query_tokens = tokenize_code(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        q_set = set(query_tokens)

        # Pair scores with metadata indices
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results = []
        rank = 1
        for idx in ranked_indices:
            score = float(scores[idx])
            has_token_overlap = bool(self.corpus_tokens[idx].intersection(q_set)) if self.corpus_tokens else False

            # If score is 0 due to small-corpus zero IDF, but term is present, assign positive score
            if score <= 0.0:
                if has_token_overlap:
                    score = 0.5
                else:
                    continue

            meta = self.corpus_meta[idx]
            if repo_id and meta.get("repo_id") != repo_id:
                continue

            item = dict(meta)
            item["score"] = round(score, 4)
            item["retrieval_method"] = "bm25"
            item["rank"] = rank
            results.append(item)
            rank += 1
            if len(results) >= top_k:
                break

        return results

    def save(self, output_path: Path) -> None:
        """Serialize BM25 index and corpus metadata to disk."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "bm25": self.bm25,
            "corpus_meta": self.corpus_meta,
            "corpus_tokens": self.corpus_tokens,
            "chunk_id_to_idx": self.chunk_id_to_idx
        }
        with output_path.open("wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"BM25 index saved to {output_path}")

    def load(self, index_path: Path) -> None:
        """Load persistent BM25 index from disk."""
        with index_path.open("rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]
        self.corpus_meta = data["corpus_meta"]
        self.corpus_tokens = data.get("corpus_tokens", [])
        self.chunk_id_to_idx = data["chunk_id_to_idx"]
        self.index_file = index_path
        print(f"BM25 index loaded from {index_path} ({len(self.corpus_meta)} chunks).")


def build_and_save_bm25_index(
    chunks_path: Path,
    output_index: Path,
    max_chunks: Optional[int] = None
) -> BM25Retriever:
    """Convenience function to load chunks, build index, and persist."""
    print(f"Streaming chunks from {chunks_path}...")
    chunks = []
    for c in stream_read(chunks_path):
        chunks.append(c)
        if max_chunks and len(chunks) >= max_chunks:
            break

    retriever = BM25Retriever()
    retriever.build_index(chunks)
    retriever.save(output_index)
    return retriever


def main():
    parser = argparse.ArgumentParser(description="Build or test persistent BM25 index.")
    parser.add_argument("--chunks", type=str, default=str(DATA / "processed" / "code_chunks.jsonl"), help="Chunks JSONL path")
    parser.add_argument("--index-path", type=str, default=str(DATA / "indexes" / "bm25_index.pkl"), help="Path to BM25 index")
    parser.add_argument("--query", type=str, default=None, help="Optional test query to run")
    parser.add_argument("--max-chunks", type=int, default=15000, help="Max chunks to index for fast testing")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve")
    args = parser.parse_args()

    index_path = Path(args.index_path)

    if not index_path.exists() or not args.query:
        retriever = build_and_save_bm25_index(Path(args.chunks), index_path, max_chunks=args.max_chunks)
    else:
        retriever = BM25Retriever(index_path)

    if args.query:
        print(f"\nQuery: '{args.query}'")
        results = retriever.search(args.query, top_k=args.top_k)
        for r in results:
            print(f"[{r['rank']}] Score: {r['score']} | {r['repo_id']} | {r['file_path']}:{r['start_line']}-{r['end_line']} | {r['chunk_name']}")


if __name__ == "__main__":
    main()
