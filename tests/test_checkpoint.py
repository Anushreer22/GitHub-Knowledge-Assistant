import torch
import pytest
from pathlib import Path

from training.model import CodeEncoder, CodeEncoderConfig


def test_checkpoint_saving_and_loading(tmp_path):
    config = CodeEncoderConfig(
        vocab_size=100,
        hidden_dim=32,
        num_layers=1,
        num_heads=2,
        ff_dim=64,
        max_seq_len=16
    )
    model = CodeEncoder(config)
    model.eval()

    test_input = torch.randint(1, 99, (2, 8))
    with torch.no_grad():
        orig_out = model(test_input)

    ckpt_path = tmp_path / "model_ckpt.pt"
    torch.save({
        "epoch": 1,
        "config": config.to_dict(),
        "model_state_dict": model.state_dict()
    }, ckpt_path)

    # Reload into new instance
    loaded_data = torch.load(ckpt_path, weights_only=False)
    loaded_config = CodeEncoderConfig.from_dict(loaded_data["config"])
    loaded_model = CodeEncoder(loaded_config)
    loaded_model.load_state_dict(loaded_data["model_state_dict"])
    loaded_model.eval()

    with torch.no_grad():
        loaded_out = loaded_model(test_input)

    assert torch.allclose(orig_out, loaded_out, atol=1e-6)
