#!/usr/bin/env python3
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['LIGHTGBM_NUM_THREADS'] = '1'
"""
Bootstrap CI (VERBOSE) — Standalone, no external imports.
Run from: /Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/training/
"""

import argparse
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from pathlib import Path
from sklearn.metrics import r2_score

# ========== MLP DEFINITION (exact copy from train_surrogate_v2.py) ==========
class MLPRegressor(torch.nn.Module):
    def __init__(self, input_dim: int, hidden_dims=(256, 128, 64), dropout=0.2):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h in hidden_dims:
            layers.append(torch.nn.Linear(prev_dim, h))
            layers.append(torch.nn.BatchNorm1d(h))
            layers.append(torch.nn.ReLU())
            layers.append(torch.nn.Dropout(dropout))
            prev_dim = h
        layers.append(torch.nn.Linear(prev_dim, 1))
        self.net = torch.nn.Sequential(*layers)
    def forward(self, x):
        return self.net(x).squeeze(-1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true', help='Print every resample')
    parser.add_argument('--progress-every', type=int, default=100, help='Print every N resamples')
    args = parser.parse_args()

    # ========== PATHS ==========
    DATA_PATH = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json")
    MODEL_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved")

    print("=" * 70)
    print("BOOTSTRAP CI (VERBOSE)")
    print("=" * 70)

    # ========== LOAD DATA ==========
    df = pd.read_json("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json")
    if 'suitable_for_regression' in df.columns:
        df = df[df['suitable_for_regression']].copy()

    df = df.copy()
    df['final_wns_ns'] = np.clip(df['final_wns_ns'], -500, 100)
    df['final_tns_ns'] = np.clip(df['final_tns_ns'], -10000, 100)
    df['final_area_um2_log'] = np.log1p(np.maximum(df['final_area_um2'], 0))
    df['final_power_mw_log'] = np.log1p(np.maximum(df['final_power_mw'], 0))
    df['log_instances'] = np.log1p(df['num_instances']) / 20
    df['log_nets'] = np.log1p(df['num_nets']) / 20
    df['seq_ratio'] = df['num_sequential'] / np.maximum(df['num_instances'], 1)
    df['macro_ratio'] = df['num_macros'] / np.maximum(df['num_instances'], 1)
    df['log_area'] = np.log1p(df['final_area_um2']) / 20
    df['log_power'] = np.log1p(df['final_power_mw']) / 20
    df['wns_normalized'] = np.clip(df['final_wns_ns'] / 10, -1, 1)
    df['tns_normalized'] = np.clip(df['final_tns_ns'] / 1000, -1, 1)
    df['sample_weight'] = 1.0

    # Preprocessor
    preprocessor = joblib.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_preprocessor_v2.pkl")
    X_all = df.copy()
    X_processed = preprocessor.transform(X_all)

    # ========== LOAD ALL MODELS ==========
    print("Loading models...")
    short_names = ['wns', 'tns', 'area', 'power']
    target_cols = {
        'wns': 'final_wns_ns',
        'tns': 'final_tns_ns',
        'area': 'final_area_um2',
        'power': 'final_power_mw',
    }

    # Load all models into memory
    lgb_models = {}
    mlp_models = {}
    for short_name in ['wns', 'tns', 'area', 'power']:
        # LightGBM
        lgb_obj = joblib.load(f"{MODEL_DIR}/surrogate_{short_name}_lgb.pkl")
        lgb_models[short_name] = lgb_obj['model'] if isinstance(lgb_obj, dict) else lgb_obj

        # MLP
        checkpoint = torch.load(
            f"/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_{short_name}_mlp.pt",
            map_location='cpu'
        )
        mlp = MLPRegressor(input_dim=X_processed.shape[1])
        mlp.load_state_dict(checkpoint['model_state'])
        mlp.eval()
        mlp_models[short_name] = mlp

    # ========== PREDICT ON FULL DATASET ==========
    print("Computing predictions on full dataset...")
    preprocessor = joblib.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_preprocessor_v2.pkl")

    # Load & preprocess data
    df = pd.read_json("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json")
    df = df[df['suitable_for_regression']].copy()
    df = df.copy()
    df['final_wns_ns'] = np.clip(df['final_wns_ns'], -500, 100)
    df['final_tns_ns'] = np.clip(df['final_tns_ns'], -10000, 100)
    df['final_area_um2_log'] = np.log1p(np.maximum(df['final_area_um2'], 0))
    df['final_power_mw_log'] = np.log1p(np.maximum(df['final_power_mw'], 0))
    df['log_instances'] = np.log1p(df['num_instances']) / 20
    df['log_nets'] = np.log1p(df['num_nets']) / 20
    df['seq_ratio'] = df['num_sequential'] / np.maximum(df['num_instances'], 1)
    df['macro_ratio'] = df['num_macros'] / np.maximum(df['num_instances'], 1)
    df['log_area'] = np.log1p(df['final_area_um2']) / 20
    df['log_power'] = np.log1p(df['final_power_mw']) / 20
    df['wns_normalized'] = np.clip(df['final_wns_ns'] / 10, -1, 1)
    df['tns_normalized'] = np.clip(df['final_tns_ns'] / 1000, -1, 1)
    df['sample_weight'] = 1.0

    preprocessor = joblib.load("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_preprocessor_v2.pkl")
    X_all = df
    X_processed = preprocessor.transform(X_all)

    # Load all models into memory for speed
    print("Loading all models into memory...")
    lgb_models = {}
    mlp_models = {}
    for short_name in ['wns', 'tns', 'area', 'power']:
        # LightGBM
        lgb_obj = joblib.load(f"{MODEL_DIR}/surrogate_{short_name}_lgb.pkl")
        lgb_models[short_name] = lgb_obj['model'] if isinstance(lgb_obj, dict) else lgb_obj

        # MLP
        checkpoint = torch.load(
            f"/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_{short_name}_mlp.pt",
            map_location='cpu'
        )
        mlp = MLPRegressor(input_dim=X_processed.shape[1])
        mlp.load_state_dict(checkpoint['model_state'])
        mlp.eval()
        mlp_models[short_name] = mlp

    # Compute predictions ONCE
    print("Computing ensemble predictions...")
    y_pred_dict = {}
    y_true_dict = {}

    for short_name in ['wns', 'tns', 'area', 'power']:
        target_col = {'wns':'final_wns_ns','tns':'final_tns_ns','area':'final_area_um2','power':'final_power_mw'}[short_name]

        # True values (original scale)
        y_true = df[target_col].values
        y_true_dict[short_name] = y_true

        # LightGBM prediction
        lgb_model = joblib.load(f"{MODEL_DIR}/surrogate_{short_name}_lgb.pkl")
        if isinstance(lgb_model, dict): lgb_model = lgb_model['model']
        y_pred_lgb = lgb_model.predict(X_processed)

        # MLP prediction
        checkpoint = torch.load(f"{MODEL_DIR}/surrogate_{short_name}_mlp.pt", map_location='cpu')
        mlp = MLPRegressor(input_dim=X_processed.shape[1])
        mlp.load_state_dict(checkpoint['model_state'])
        mlp.eval()
        with torch.no_grad():
            y_pred_mlp = mlp(torch.FloatTensor(X_processed)).cpu().numpy()

        # Ensemble
        y_pred_ensemble = (y_pred_lgb + y_pred_mlp) / 2

        # Convert back from log-space for area/power
        target_col = target_cols[short_name]
        if target_col == 'final_area_um2':
            y_pred = np.expm1(y_pred_ensemble)
        elif target_col == 'final_power_mw':
            y_pred = np.expm1(y_pred_ensemble)
        else:
            y_pred = y_pred_ensemble

        y_pred_dict[short_name] = y_pred

    # ========== BOOTSTRAP ==========
    print("\nStarting bootstrap...\n")

    for short_name in ['wns', 'tns', 'area', 'power']:
        target_col = target_cols[short_name]
        y_true = df[target_col].values
        y_pred = y_pred_dict[short_name]

        print(f"\n{'='*60}")
        print(f"BOOTSTRAP: {short_name.upper()} ({len(y_true)} samples)")
        print(f"{'='*60}")

        boots = []
        rng = np.random.default_rng(42)

        for i in range(1000):
            idx = np.random.choice(len(y_true), len(y_true), replace=True)
            r2 = r2_score(y_true[idx], y_pred[idx])
            boots.append(r2)

            if args.verbose or (i + 1) % args.progress_every == 0:
                mean_so_far = np.mean(boots)
                print(f"  Resample {i+1:4d}/1000: R² = {r2:.4f} | Running mean: {mean_so_far:.4f}")

        boots = np.array(boots)
        mean_r2 = np.mean(boots)
        ci_low, ci_high = np.percentile(boots, [2.5, 97.5])
        std = np.std(boots)

        print(f"\n  RESULT: R² = {mean_r2:.4f} [{np.percentile(boots,2.5):.4f}, {np.percentile(boots,97.5):.4f}]")
        print(f"  Std: {std:.4f}")
        print(f"  Min/Max: {np.min(boots):.4f} / {np.max(boots):.4f}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true', help='Print every resample')
    parser.add_argument('--progress-every', type=int, default=100, help='Print every N resamples')
    args = parser.parse_args()
    main()
