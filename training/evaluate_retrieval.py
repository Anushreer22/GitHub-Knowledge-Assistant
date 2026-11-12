import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

import torch
import numpy as np
from tokenizers import Tokenizer

from dataset_pipeline.common import DATA, stream_read
from .model import CodeEncoder, CodeEncoderConfig


def evaluate_retrieval(
    model: CodeEncoder,
    tokenizer: Tokenizer,
    qa_records: List[Dict[str, Any]],
    corpus_chunks: List[Dict[str, Any]],
    batch_size: int = 32,
    device: str = "cpu",
    max_seq_len: int = 512
) -> Dict[str, float]:
    """Compute Recall@1, Recall@5, Recall@10, and MRR for code retrieval."""
    model.eval()
    model.to(device)

    pad_id = tokenizer.token_to_id("<pad>") or 0

    # 1. Encode Corpus Chunks
    corpus_ids = [c["chunk_id"] for c in corpus_chunks]
    corpus_id_to_idx = {cid: idx for idx, cid in enumerate(corpus_ids)}
    corpus_embeddings_list = []

    print(f"Encoding corpus of {len(corpus_chunks)} code chunks on {device}...")
    with torch.no_grad():
        for i in range(0, len(corpus_chunks), batch_size):
            batch = corpus_chunks[i:i + batch_size]
            batch_input_ids = []
            batch_masks = []
            for c in batch:
                enc = tokenizer.encode(c.get("code_text", ""))
                ids = enc.ids[:max_seq_len]
                mask = [1] * len(ids)
                pad_len = max_seq_len - len(ids)
                ids += [pad_id] * pad_len
                mask += [0] * pad_len
                batch_input_ids.append(ids)
                batch_masks.append(mask)

            inp = torch.tensor(batch_input_ids, dtype=torch.long, device=device)
            att = torch.tensor(batch_masks, dtype=torch.long, device=device)
            emb = model(inp, attention_mask=att)
            corpus_embeddings_list.append(emb.cpu().numpy())

    corpus_mat = np.vstack(corpus_embeddings_list) if corpus_embeddings_list else np.empty((0, model.config.hidden_dim))

    # 2. Encode Queries
    query_embeddings_list = []
    ground_truth_indices = []

    print(f"Encoding {len(qa_records)} evaluation queries on {device}...")
    valid_qa = []
    with torch.no_grad():
        for q in qa_records:
            rel_chunks = q.get("relevant_chunk_ids", [])
            if not rel_chunks or rel_chunks[0] not in corpus_id_to_idx:
                continue
            valid_qa.append(q)
            ground_truth_indices.append(corpus_id_to_idx[rel_chunks[0]])

        for i in range(0, len(valid_qa), batch_size):
            batch = valid_qa[i:i + batch_size]
            batch_input_ids = []
            batch_masks = []
            for q in batch:
                enc = tokenizer.encode(q.get("question", ""))
                ids = enc.ids[:max_seq_len]
                mask = [1] * len(ids)
                pad_len = max_seq_len - len(ids)
                ids += [pad_id] * pad_len
                mask += [0] * pad_len
                batch_input_ids.append(ids)
                batch_masks.append(mask)

            inp = torch.tensor(batch_input_ids, dtype=torch.long, device=device)
            att = torch.tensor(batch_masks, dtype=torch.long, device=device)
            emb = model(inp, attention_mask=att)
            query_embeddings_list.append(emb.cpu().numpy())

    if not query_embeddings_list or len(corpus_mat) == 0:
        return {"recall@1": 0.0, "recall@5": 0.0, "recall@10": 0.0, "mrr": 0.0, "eval_count": 0}

    query_mat = np.vstack(query_embeddings_list)

    # 3. Compute Similarity Matrix (Cosine Similarity via dot product since embeddings are L2-normalized)
    sim_matrix = np.dot(query_mat, corpus_mat.T)  # (N_queries, N_corpus)

    r1_count = 0
    r5_count = 0
    r10_count = 0
    reciprocal_ranks = []

    for q_idx in range(len(valid_qa)):
        target_idx = ground_truth_indices[q_idx]
        scores = sim_matrix[q_idx]

        # Descending sort indices
        ranked_indices = np.argsort(-scores)

        rank_pos = np.where(ranked_indices == target_idx)[0]
        if len(rank_pos) > 0:
            rank = rank_pos[0] + 1  # 1-based rank
            if rank == 1:
                r1_count += 1
            if rank <= 5:
                r5_count += 1
            if rank <= 10:
                r10_count += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

    n = len(valid_qa)
    return {
        "recall@1": round(r1_count / n, 4) if n > 0 else 0.0,
        "recall@5": round(r5_count / n, 4) if n > 0 else 0.0,
        "recall@10": round(r10_count / n, 4) if n > 0 else 0.0,
        "mrr": round(float(np.mean(reciprocal_ranks)), 4) if n > 0 else 0.0,
        "eval_count": n,
        "corpus_size": len(corpus_chunks)
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate code retrieval performance.")
    parser.add_argument("--model-checkpoint", type=str, default="models/best_code_encoder.pt", help="Path to model checkpoint")
    parser.add_argument("--tokenizer-dir", type=str, default="models/tokenizer", help="Path to tokenizer directory")
    parser.add_argument("--eval-qa", type=str, default=str(DATA / "splits" / "validation_qa.jsonl"), help="Path to evaluation QA")
    parser.add_argument("--eval-chunks", type=str, default=str(DATA / "splits" / "validation_chunks.jsonl"), help="Path to evaluation chunks")
    parser.add_argument("--output-report", type=str, default=str(DATA / "reports" / "retrieval_evaluation_report.json"), help="Output metrics path")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="Device (cpu/cuda)")
    parser.add_argument("--max-queries", type=int, default=500, help="Max queries to evaluate")
    args = parser.parse_args()

    ckpt_path = Path(args.model_checkpoint)
    tok_dir = Path(args.tokenizer_dir)
    qa_path = Path(args.eval_qa)
    chunks_path = Path(args.eval_chunks)

    if not ckpt_path.exists():
        raise SystemExit(f"Model checkpoint not found: {ckpt_path}")
    if not (tok_dir / "tokenizer.json").exists():
        raise SystemExit(f"Tokenizer not found in {tok_dir}")

    print(f"Loading checkpoint {ckpt_path}...")
    checkpoint = torch.load(ckpt_path, map_location=args.device, weights_only=False)
    config = CodeEncoderConfig.from_dict(checkpoint.get("config", {}))
    model = CodeEncoder(config)
    model.load_state_dict(checkpoint["model_state_dict"])

    tokenizer = Tokenizer.from_file(str(tok_dir / "tokenizer.json"))

    qa_records = list(stream_read(qa_path))[:args.max_queries]
    corpus_chunks = list(stream_read(chunks_path))

    metrics = evaluate_retrieval(
        model=model,
        tokenizer=tokenizer,
        qa_records=qa_records,
        corpus_chunks=corpus_chunks,
        device=args.device
    )

    print("\n--- RETRIEVAL EVALUATION RESULTS ---")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    report_path = Path(args.output_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
