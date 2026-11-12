import torch
import pytest

from training.model import InfoNCELoss


def test_infonce_loss_in_batch():
    loss_fn = InfoNCELoss(temperature=0.07)
    batch_size = 4
    dim = 64

    # Identical queries and positives should yield minimal loss
    queries = torch.randn(batch_size, dim)
    queries = torch.nn.functional.normalize(queries, p=2, dim=-1)
    positives = queries.clone()

    loss = loss_fn(queries, positives)
    assert loss.item() >= 0.0

    # Orthogonal queries and positives should have much higher loss
    negatives = torch.randn(batch_size, dim)
    negatives = torch.nn.functional.normalize(negatives, p=2, dim=-1)
    high_loss = loss_fn(queries, negatives)
    assert high_loss.item() > loss.item()


def test_infonce_loss_explicit_negatives():
    loss_fn = InfoNCELoss(temperature=0.07)
    batch_size = 3
    num_neg = 2
    dim = 32

    queries = torch.randn(batch_size, dim)
    queries = torch.nn.functional.normalize(queries, p=2, dim=-1)
    positives = queries.clone()

    explicit_negs = torch.randn(batch_size, num_neg, dim)
    explicit_negs = torch.nn.functional.normalize(explicit_negs, p=2, dim=-1)

    loss = loss_fn(queries, positives, explicit_negs)
    assert loss.item() >= 0.0
    assert not torch.isnan(loss)
