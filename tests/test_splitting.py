import pytest
from dataset_pipeline.split_dataset import partition_repositories


def test_partition_repositories_disjoint():
    repos = [f"repo_{i}" for i in range(10)]
    res = partition_repositories(repos, train_ratio=0.8, val_ratio=0.1, seed=42)

    train = set(res["train"])
    val = set(res["validation"])
    test = set(res["test"])

    assert len(train) > 0
    assert len(val) > 0
    assert len(test) > 0

    # Ensure complete disjointness (no repository leakage across splits)
    assert train.isdisjoint(val)
    assert train.isdisjoint(test)
    assert val.isdisjoint(test)
    assert train | val | test == set(repos)


def test_partition_small_repo_count_raises_limitation():
    repos = ["repoA", "repoB", "repoC", "repoD"]  # 4 repos
    with pytest.raises(ValueError, match="Limitation: 4 repositories cannot satisfy"):
        partition_repositories(repos, train_ratio=0.8, val_ratio=0.1, seed=42, allow_small_splits=False)


def test_partition_small_repo_count_with_fallback():
    repos = ["repoA", "repoB", "repoC", "repoD"]
    res = partition_repositories(repos, train_ratio=0.8, val_ratio=0.1, seed=42, allow_small_splits=True)

    assert len(res["train"]) >= 1
    assert len(res["validation"]) >= 1
    assert len(res["test"]) >= 1
    assert set(res["train"]).isdisjoint(set(res["validation"]))
    assert set(res["train"]).isdisjoint(set(res["test"]))
