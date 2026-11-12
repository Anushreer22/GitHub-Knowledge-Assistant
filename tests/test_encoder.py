import torch
import pytest

from training.model import CodeEncoder, CodeEncoderConfig


def test_code_encoder_forward():
    config = CodeEncoderConfig(
        vocab_size=1000,
        hidden_dim=128,
        num_layers=2,
        num_heads=2,
        ff_dim=256,
        max_seq_len=64,
        pad_token_id=0
    )
    model = CodeEncoder(config)
    model.eval()

    batch_size = 4
    seq_len = 32
    input_ids = torch.randint(1, 999, (batch_size, seq_len))
    # Add padding to second half of last sample
    input_ids[-1, 16:] = 0
    attention_mask = (input_ids != 0).long()

    with torch.no_grad():
        embeddings = model(input_ids, attention_mask=attention_mask)

    assert embeddings.shape == (batch_size, 128)

    # Check L2 normalization: norm of each embedding should be ~1.0
    norms = torch.norm(embeddings, p=2, dim=-1)
    assert torch.allclose(norms, torch.ones_like(norms), atol=1e-5)


def test_code_encoder_max_seq_len_truncation():
    config = CodeEncoderConfig(
        vocab_size=500,
        hidden_dim=64,
        num_layers=1,
        num_heads=2,
        ff_dim=128,
        max_seq_len=16
    )
    model = CodeEncoder(config)
    model.eval()

    # Pass sequence longer than max_seq_len
    long_input = torch.randint(1, 400, (2, 32))
    with torch.no_grad():
        out = model(long_input)
    assert out.shape == (2, 64)
