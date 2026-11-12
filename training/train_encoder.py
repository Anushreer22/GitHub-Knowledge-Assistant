import os
import json
import time
import random
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tokenizers import Tokenizer

from dataset_pipeline.common import DATA, stream_read
from .model import CodeEncoder, CodeEncoderConfig, InfoNCELoss
from .dataset import CodeQATripletDataset
from .evaluate_retrieval import evaluate_retrieval


def load_approved_qa_data(
    review_path: Path,
    fallback_qa_path: Optional[Path],
    min_approved: int = 10,
    allow_candidate_training: bool = False
) -> List[Dict[str, Any]]:
    """Enforce data quality gating:
    Only train on human-approved or explicitly verified QA pairs.
    Stops and reports missing data if approved count is insufficient.
    """
    approved_records = []

    # 1. Check human review store first
    if review_path.exists():
        for r in stream_read(review_path):
            if r.get("review_status") == "approved":
                approved_records.append(r)

    print(f"Found {len(approved_records)} approved QA pairs in {review_path}")

    # 2. Check fallback or stop
    if len(approved_records) < min_approved:
        if allow_candidate_training and fallback_qa_path and fallback_qa_path.exists():
            print(f"[WARNING] --allow-candidate-training is enabled. Loading unreviewed candidates from {fallback_qa_path} as experimental baseline.")
            candidates = list(stream_read(fallback_qa_path))
            return candidates
        else:
            raise RuntimeError(
                f"\n[DATA QUALITY GATE ENFORCED]\n"
                f"Training stopped: Insufficient approved QA pairs ({len(approved_records)} found, minimum {min_approved} required).\n"
                f"The system strictly prohibits training on unreviewed candidate QA pairs to ensure ground-truth integrity.\n\n"
                f"Required next steps:\n"
                f"1. Export pending QA pairs for review:  python -m dataset_pipeline.export_review\n"
                f"2. Mark approved QA pairs and import: python -m dataset_pipeline.import_review\n"
                f"3. Re-run training once verified QA pairs are present in {review_path}.\n"
                f"(For experimental debugging with unverified candidates only, pass --allow-candidate-training)."
            )

    return approved_records


def train(
    config: CodeEncoderConfig,
    train_qa: List[Dict[str, Any]],
    val_qa: List[Dict[str, Any]],
    chunks_lookup: Dict[str, str],
    val_corpus_chunks: List[Dict[str, Any]],
    tokenizer: Tokenizer,
    output_dir: Path,
    epochs: int = 5,
    batch_size: int = 16,
    lr: float = 1e-4,
    patience: int = 3,
    seed: int = 42,
    device: str = "cpu"
) -> Dict[str, Any]:
    """Train custom code encoder from scratch using InfoNCE contrastive learning."""
    # Reproducibility
    torch.manual_seed(seed)
    random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir = output_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    # Initialize model from scratch (NO pretrained weights!)
    model = CodeEncoder(config)
    model.to(device)

    loss_fn = InfoNCELoss(temperature=config.temperature)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)

    train_dataset = CodeQATripletDataset(
        qa_records=train_qa,
        chunks_lookup=chunks_lookup,
        tokenizer=tokenizer,
        max_seq_len=config.max_seq_len
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        drop_last=(len(train_dataset) > batch_size)
    )

    history = {
        "epochs": [],
        "train_loss": [],
        "val_loss": [],
        "recall@1": [],
        "recall@5": [],
        "recall@10": [],
        "mrr": []
    }

    best_mrr = -1.0
    best_epoch = 0
    patience_counter = 0

    print(f"\nStarting training on {device} ({len(train_dataset)} training pairs, {epochs} epochs)...")

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        step_count = 0

        for batch in train_loader:
            optimizer.zero_grad()

            q_ids = batch["query_ids"].to(device)
            q_mask = batch["query_mask"].to(device)
            pos_ids = batch["pos_ids"].to(device)
            pos_mask = batch["pos_mask"].to(device)

            # Encode query and positive code
            q_emb = model(q_ids, attention_mask=q_mask)
            pos_emb = model(pos_ids, attention_mask=pos_mask)

            loss = loss_fn(q_emb, pos_emb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += loss.item()
            step_count += 1

        avg_train_loss = total_loss / max(1, step_count)

        # Validation Evaluation
        metrics = evaluate_retrieval(
            model=model,
            tokenizer=tokenizer,
            qa_records=val_qa,
            corpus_chunks=val_corpus_chunks,
            batch_size=batch_size,
            device=device,
            max_seq_len=config.max_seq_len
        )

        curr_mrr = metrics.get("mrr", 0.0)

        history["epochs"].append(epoch)
        history["train_loss"].append(round(avg_train_loss, 4))
        history["recall@1"].append(metrics.get("recall@1", 0.0))
        history["recall@5"].append(metrics.get("recall@5", 0.0))
        history["recall@10"].append(metrics.get("recall@10", 0.0))
        history["mrr"].append(curr_mrr)

        print(
            f"Epoch {epoch:2d}/{epochs:2d} | "
            f"Train Loss: {avg_train_loss:.4f} | "
            f"Val Recall@1: {metrics.get('recall@1', 0.0):.4f} | "
            f"Val Recall@5: {metrics.get('recall@5', 0.0):.4f} | "
            f"Val MRR: {curr_mrr:.4f}"
        )

        # Save epoch checkpoint
        ckpt_path = checkpoints_dir / f"encoder_epoch_{epoch}.pt"
        torch.save({
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "config": config.to_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": metrics
        }, ckpt_path)

        # Track best model checkpoint based on MRR
        if curr_mrr > best_mrr or epoch == 1:
            best_mrr = curr_mrr
            best_epoch = epoch
            patience_counter = 0
            best_model_path = output_dir / "best_code_encoder.pt"
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "config": config.to_dict(),
                "metrics": metrics
            }, best_model_path)
            print(f"  --> Saved new best checkpoint to {best_model_path} (MRR: {best_mrr:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping triggered at epoch {epoch} (no MRR improvement for {patience} epochs).")
                break

    # Save training history
    history_path = output_dir / "training_history.json"
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    return {
        "best_epoch": best_epoch,
        "best_mrr": best_mrr,
        "history": history
    }


def main():
    parser = argparse.ArgumentParser(description="Train custom code encoder from scratch.")
    parser.add_argument("--train-qa", type=str, default=str(DATA / "splits" / "train_qa.jsonl"), help="Training QA file")
    parser.add_argument("--val-qa", type=str, default=str(DATA / "splits" / "validation_qa.jsonl"), help="Validation QA file")
    parser.add_argument("--chunks", type=str, default=str(DATA / "processed" / "code_chunks.jsonl"), help="Code chunks path")
    parser.add_argument("--review-store", type=str, default=str(DATA / "review" / "qa_review.jsonl"), help="Approved review store")
    parser.add_argument("--tokenizer-dir", type=str, default="models/tokenizer", help="Tokenizer directory")
    parser.add_argument("--output-dir", type=str, default="models", help="Output directory for model")
    parser.add_argument("--experiments-dir", type=str, default="experiments", help="Experiments output directory")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--hidden-dim", type=int, default=256, help="Hidden dimension")
    parser.add_argument("--num-layers", type=int, default=4, help="Transformer layers")
    parser.add_argument("--num-heads", type=int, default=4, help="Attention heads")
    parser.add_argument("--max-seq-len", type=int, default=512, help="Max sequence length")
    parser.add_argument("--min-approved", type=int, default=10, help="Minimum approved QA pairs required to train")
    parser.add_argument("--allow-candidate-training", action="store_true", help="Allow training on candidates for experimental testing")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="Device (cpu/cuda)")
    args = parser.parse_args()

    review_path = Path(args.review_store)
    train_qa_path = Path(args.train_qa)
    val_qa_path = Path(args.val_qa)
    chunks_path = Path(args.chunks)
    tok_dir = Path(args.tokenizer_dir)
    output_dir = Path(args.output_dir)
    exp_dir = Path(args.experiments_dir)

    # 1. Enforce Data Quality Gate
    train_qa = load_approved_qa_data(
        review_path=review_path,
        fallback_qa_path=train_qa_path,
        min_approved=args.min_approved,
        allow_candidate_training=args.allow_candidate_training
    )

    # 2. Check tokenizer
    tok_file = tok_dir / "tokenizer.json"
    if not tok_file.exists():
        raise SystemExit(
            f"Tokenizer not found at {tok_file}.\n"
            "Please run 'python -m training.train_tokenizer' first."
        )
    tokenizer = Tokenizer.from_file(str(tok_file))

    # 3. Build code lookup
    print(f"Loading code chunks from {chunks_path}...")
    chunks_lookup = {}
    val_corpus_chunks = []
    val_cids = set()

    val_qa_records = list(stream_read(val_qa_path)) if val_qa_path.exists() else []
    for q in val_qa_records:
        for cid in q.get("relevant_chunk_ids", []):
            val_cids.add(cid)

    for c in stream_read(chunks_path):
        cid = c["chunk_id"]
        chunks_lookup[cid] = c.get("code_text", "")
        if cid in val_cids or len(val_corpus_chunks) < 200:
            val_corpus_chunks.append(c)

    # 4. Configuration
    config = CodeEncoderConfig(
        vocab_size=tokenizer.get_vocab_size(),
        hidden_dim=args.hidden_dim,
        num_layers=args.num_layers,
        num_heads=args.num_heads,
        ff_dim=1024,
        max_seq_len=args.max_seq_len,
        pad_token_id=tokenizer.token_to_id("<pad>") or 0
    )

    # 5. Train model
    start_time = time.time()
    results = train(
        config=config,
        train_qa=train_qa,
        val_qa=val_qa_records,
        chunks_lookup=chunks_lookup,
        val_corpus_chunks=val_corpus_chunks,
        tokenizer=tokenizer,
        output_dir=output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        seed=args.seed,
        device=args.device
    )
    elapsed = time.time() - start_time

    # 6. Experiment Tracking
    exp_dir.mkdir(parents=True, exist_ok=True)
    exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    exp_record = {
        "experiment_id": exp_id,
        "timestamp": datetime.now().isoformat(),
        "model_architecture": {
            "type": "CustomTransformerEncoderFromScratch",
            "hidden_dim": args.hidden_dim,
            "num_layers": args.num_layers,
            "num_heads": args.num_heads,
            "ff_dim": config.ff_dim,
            "max_seq_len": args.max_seq_len,
            "vocab_size": config.vocab_size,
            "pretrained": False
        },
        "tokenizer_config": {
            "type": "ByteLevelBPE",
            "vocab_size": tokenizer.get_vocab_size()
        },
        "dataset_version": "v1.0",
        "training_parameters": {
            "batch_size": args.batch_size,
            "lr": args.lr,
            "epochs": args.epochs,
            "seed": args.seed,
            "training_samples": len(train_qa),
            "device": args.device,
            "elapsed_seconds": round(elapsed, 2)
        },
        "results": results
    }

    exp_path = exp_dir / f"{exp_id}.json"
    exp_path.write_text(json.dumps(exp_record, indent=2), encoding="utf-8")
    print(f"\nExperiment log recorded at {exp_path}")


if __name__ == "__main__":
    main()
