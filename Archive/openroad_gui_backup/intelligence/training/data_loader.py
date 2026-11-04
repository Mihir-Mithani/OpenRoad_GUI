"""Data loading utilities for training pipeline."""

from __future__ import annotations

import torch
from torch.utils.data import Dataset, DataLoader
import polars as pl
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class DataLoaderConfig:
    """Configuration for data loaders."""
    batch_size: int = 32
    val_split: float = 0.2
    shuffle: bool = True
    num_workers: int = 0  # 0 for M1 MPS compatibility
    pin_memory: bool = False
    seed: int = 42


class FlowDataset(Dataset):
    """Dataset for flow optimization training data."""

    def __init__(self, features_path: str, labels_path: Optional[str] = None):
        self.df = pl.read_parquet(features_path)

        # Prepare features
        feature_cols = [c for c in self.df.columns if c not in [
            "run_id", "design_name", "platform", "timestamp",
            "final_wns_ns", "final_tns_ns", "final_area_um2",
            "final_power_mw", "final_drc_violations",
            "total_runtime_sec", "timing_closure_bin",
            "drc_clean_bin", "lvs_clean_bin",
        ]]

        self.feature_cols = [c for c in self.df.columns if c in [
            "log_instances", "log_nets", "seq_ratio", "macro_ratio",
            "core_utilization", "core_aspect_ratio", "core_margin",
            "platform_cat", "design_name"
        ] + [c for c in self.df.columns if c.startswith("log_") or c.endswith("_normalized")]
        ]

        self.features = self.df.select(self.feature_cols).to_numpy()

        # Targets: PPA metrics
        self.targets = self.df.select([
            "final_wns_ns", "final_tns_ns", "final_area_um2",
            "final_power_mw", "final_drc_violations",
            "timing_closure_bin", "drc_clean_bin"
        ]).to_numpy()

        print(f"Dataset: {len(self)} samples, {self.features.shape[1]} features, {self.targets.shape[1]} targets")

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            "features": torch.tensor(self.features[idx], dtype=torch.float32),
            "targets": torch.tensor(self.targets[idx], dtype=torch.float32),
        }


class FlowDatasetRL(Dataset):
    """Dataset for RL training (state-action-reward tuples)."""

    def __init__(self, data_path: str):
        # Load preprocessed RL transitions
        # (state, action, reward, next_state, done)
        pass

    def __len__(self) -> int:
        return 0

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {}


def create_dataloaders(
    features_path: str,
    config: 'DataLoaderConfig',
) -> Tuple[DataLoader, DataLoader]:
    """Create train and validation dataloaders."""

    dataset = FlowDataset(features_path)

    # Split indices
    n = len(dataset)
    indices = list(range(len(dataset)))
    split = int(n * (1 - config.val_split))

    if config.shuffle:
        np.random.seed(config.seed)
        np.random.shuffle(indices)

    train_indices = indices[:split]
    val_indices = indices[split:]

    train_dataset = torch.utils.data.Subset(dataset, train_indices)
    val_dataset = torch.utils.data.Subset(dataset, val_indices)

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=config.shuffle,
        num_workers=config.num_workers,
        pin_memory=config.pin_memory,
        persistent_workers=False,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=config.pin_memory,
    )

    return train_loader, val_loader


def create_rl_dataloaders(
    data_path: str,
    batch_size: int = 32,
    val_split: float = 0.2,
) -> Tuple[DataLoader, DataLoader]:
    """Create dataloaders for RL training (placeholder)."""
    # Placeholder for RL-specific dataloaders
    pass


# Type imports
from typing import Tuple, Optional, List
import numpy as np
from torch.utils.data import Dataset, DataLoader, Subset
import numpy as np