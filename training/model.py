import math
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class CodeEncoderConfig:
    vocab_size: int = 16000
    hidden_dim: int = 256
    num_layers: int = 4
    num_heads: int = 4
    ff_dim: int = 1024
    max_seq_len: int = 512
    dropout: float = 0.1
    pad_token_id: int = 0
    temperature: float = 0.07

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CodeEncoderConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CodeEncoder(nn.Module):
    """Custom compact Transformer code encoder built from scratch.
    NO pretrained weights used - trained strictly via random initialization.
    """

    def __init__(self, config: CodeEncoderConfig):
        super().__init__()
        self.config = config

        # Trainable token and position embeddings
        self.token_embeddings = nn.Embedding(
            config.vocab_size,
            config.hidden_dim,
            padding_idx=config.pad_token_id
        )
        self.position_embeddings = nn.Embedding(
            config.max_seq_len,
            config.hidden_dim
        )

        self.embedding_norm = nn.LayerNorm(config.hidden_dim)
        self.dropout = nn.Dropout(config.dropout)

        # 4-layer Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.hidden_dim,
            nhead=config.num_heads,
            dim_feedforward=config.ff_dim,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.num_layers
        )

        # Output projection and layer norm
        self.output_norm = nn.LayerNorm(config.hidden_dim)

        self._init_weights()

    def _init_weights(self):
        """Initialize parameters with standard normal / Xavier."""
        nn.init.normal_(self.token_embeddings.weight, mean=0.0, std=0.02)
        if self.token_embeddings.padding_idx is not None:
            with torch.no_grad():
                self.token_embeddings.weight[self.token_embeddings.padding_idx].fill_(0)
        nn.init.normal_(self.position_embeddings.weight, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Forward pass.
        Args:
            input_ids: (batch_size, seq_len)
            attention_mask: (batch_size, seq_len) where 1 is valid token, 0 is pad
        Returns:
            L2-normalized embeddings of shape (batch_size, hidden_dim)
        """
        batch_size, seq_len = input_ids.shape
        if seq_len > self.config.max_seq_len:
            input_ids = input_ids[:, :self.config.max_seq_len]
            if attention_mask is not None:
                attention_mask = attention_mask[:, :self.config.max_seq_len]
            seq_len = self.config.max_seq_len

        # Position indices
        positions = torch.arange(seq_len, dtype=torch.long, device=input_ids.device)
        positions = positions.unsqueeze(0).expand(batch_size, seq_len)

        # Token + Positional embeddings
        x = self.token_embeddings(input_ids) + self.position_embeddings(positions)
        x = self.embedding_norm(x)
        x = self.dropout(x)

        # Create padding mask for Transformer: True for padded positions to ignore
        src_key_padding_mask = None
        if attention_mask is not None:
            src_key_padding_mask = (attention_mask == 0)

        # Transformer layers
        hidden_states = self.transformer(x, src_key_padding_mask=src_key_padding_mask)
        hidden_states = self.output_norm(hidden_states)

        # Mask-aware Mean Pooling
        if attention_mask is not None:
            mask_expanded = attention_mask.unsqueeze(-1).expand_as(hidden_states).float()
            sum_embeddings = torch.sum(hidden_states * mask_expanded, dim=1)
            sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
            pooled = sum_embeddings / sum_mask
        else:
            pooled = hidden_states.mean(dim=1)

        # L2-normalize final embedding
        normalized = F.normalize(pooled, p=2, dim=-1)
        return normalized


class InfoNCELoss(nn.Module):
    """InfoNCE Contrastive Loss supporting both in-batch negatives and explicit hard negatives.
    Minimizes: -log( exp(q . p / tau) / (exp(q . p / tau) + sum_j exp(q . n_j / tau)) )
    """

    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature

    def forward(
        self,
        query_embeddings: torch.Tensor,
        positive_embeddings: torch.Tensor,
        negative_embeddings: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Args:
            query_embeddings: (batch_size, hidden_dim)
            positive_embeddings: (batch_size, hidden_dim)
            negative_embeddings: Optional (batch_size, num_negatives, hidden_dim)
        """
        # Cosine similarity for positive pairs
        pos_sim = torch.sum(query_embeddings * positive_embeddings, dim=-1, keepdim=True) / self.temperature

        if negative_embeddings is not None and negative_embeddings.dim() == 3:
            # Explicit hard negatives: (batch_size, num_neg, hidden_dim)
            # Dot product with queries: (batch_size, num_neg)
            neg_sim = torch.bmm(negative_embeddings, query_embeddings.unsqueeze(-1)).squeeze(-1) / self.temperature
            # Concatenate pos and neg similarities: [pos_sim, neg_sim_1, neg_sim_2, ...]
            logits = torch.cat([pos_sim, neg_sim], dim=-1)
            # Target is index 0 (positive pair)
            targets = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)
            return F.cross_entropy(logits, targets)
        else:
            # In-batch contrastive learning
            # Sim matrix: (batch_size, batch_size)
            logits = torch.matmul(query_embeddings, positive_embeddings.transpose(0, 1)) / self.temperature
            targets = torch.arange(logits.size(0), dtype=torch.long, device=logits.device)
            return F.cross_entropy(logits, targets)
