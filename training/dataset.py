from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import torch
from torch.utils.data import Dataset
from tokenizers import Tokenizer

from dataset_pipeline.common import stream_read


class CodeQATripletDataset(Dataset):
    """Dataset of (Query, Positive Code, Negative Code) triplets for contrastive learning."""

    def __init__(
        self,
        qa_records: List[Dict[str, Any]],
        chunks_lookup: Dict[str, str],  # chunk_id -> code_text
        tokenizer: Tokenizer,
        negatives_lookup: Optional[Dict[str, List[str]]] = None, # question_id -> list of negative chunk_ids
        max_seq_len: int = 512
    ):
        self.qa_records = qa_records
        self.chunks_lookup = chunks_lookup
        self.tokenizer = tokenizer
        self.negatives_lookup = negatives_lookup or {}
        self.max_seq_len = max_seq_len
        self.pad_id = tokenizer.token_to_id("<pad>") or 0

    def __len__(self) -> int:
        return len(self.qa_records)

    def _tokenize_text(self, text: str) -> Tuple[torch.Tensor, torch.Tensor]:
        encoding = self.tokenizer.encode(text)
        ids = encoding.ids[:self.max_seq_len]
        mask = [1] * len(ids)

        # Pad to max_seq_len or keep dynamic in collate
        pad_len = self.max_seq_len - len(ids)
        if pad_len > 0:
            ids = ids + [self.pad_id] * pad_len
            mask = mask + [0] * pad_len

        return torch.tensor(ids, dtype=torch.long), torch.tensor(mask, dtype=torch.long)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        qa = self.qa_records[idx]
        qid = qa["question_id"]
        q_text = qa["question"]

        pos_cid = qa["relevant_chunk_ids"][0]
        pos_code = self.chunks_lookup.get(pos_cid, "")

        q_ids, q_mask = self._tokenize_text(q_text)
        pos_ids, pos_mask = self._tokenize_text(pos_code)

        item: Dict[str, Any] = {
            "question_id": qid,
            "query_ids": q_ids,
            "query_mask": q_mask,
            "pos_ids": pos_ids,
            "pos_mask": pos_mask,
        }

        # If explicit hard negative exists
        neg_cids = self.negatives_lookup.get(qid, [])
        if neg_cids:
            neg_code = self.chunks_lookup.get(neg_cids[0], "")
            neg_ids, neg_mask = self._tokenize_text(neg_code)
            item["neg_ids"] = neg_ids
            item["neg_mask"] = neg_mask

        return item


class CodeCorpusDataset(Dataset):
    """Dataset of standalone code chunks for evaluation corpus encoding."""

    def __init__(self, chunks: List[Dict[str, Any]], tokenizer: Tokenizer, max_seq_len: int = 512):
        self.chunks = chunks
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self.pad_id = tokenizer.token_to_id("<pad>") or 0

    def __len__(self) -> int:
        return len(self.chunks)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        c = self.chunks[idx]
        code = c.get("code_text", "")
        encoding = self.tokenizer.encode(code)
        ids = encoding.ids[:self.max_seq_len]
        mask = [1] * len(ids)

        pad_len = self.max_seq_len - len(ids)
        if pad_len > 0:
            ids = ids + [self.pad_id] * pad_len
            mask = mask + [0] * pad_len

        return {
            "chunk_id": c["chunk_id"],
            "repo_id": c["repo_id"],
            "input_ids": torch.tensor(ids, dtype=torch.long),
            "attention_mask": torch.tensor(mask, dtype=torch.long)
        }
