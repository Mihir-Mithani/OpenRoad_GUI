#!/usr/bin/env python3
"""
Surrogate Models Training Script
Regression ensemble (LightGBM + PyTorch MLP) for PPA prediction:
- WNS (Worst Negative Slack) in ns
- TNS (Total Negative Slack) in ns
- Area in um²
- Power in mW

Usage:
    python -m openroad_gui.intelligence.training.train_surrogate
    python -m openroad_gui.intelligence.training.train_surrogate --data-path ./data/training_data.parquet
    python -m openroad_gui.intelligence.training.train_surrogate --epochs 200 --ensemble
"""

import argparse
import json
import os
import warnings
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import polars as pl
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

warnings.filterwarnings('ignore')

# M1/M2 compatibility
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['LIGHTGBM_NUM_THREADS'] = '1'

# ── Project paths ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "dataset_genration" / "output" / "training_data.parquet"
MODEL_DIR = PROJECT_ROOT / "openroad_gui" / "intelligence" / "models" / "saved"
CHECKPOINT_DIR = PROJECT_ROOT / "openroad_gui" / "intelligence" / "training" / "checkpoints"
LOG_DIR = PROJECT_ROOT / "openroad_gui" / "intelligence" / "training" / "logs"

for d in (MODEL_DIR, CHECKPOINT_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Feature / Target definitions ─────────────────────────────────────────
CATEGORICAL_FEATURES = ['platform', 'core_aspect_ratio']
NUMERIC_FEATURES = [
    'core_utilization', 'core_margin',
    'num_instances', 'num_nets', 'num_sequential', 'num_macros', 'macro_area_ratio',
    'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
]

REGRESSION_TARGETS = {
    'wns': 'final_wns_ns',
    'tns': 'final_tns_ns',
    'area': 'final_area_um2',
    'power': 'final_power_mw',
}

DROP_COLS = {
    'run_id', 'design_name', 'timestamp', 'design_name_config', 'platform_config',
    'final_drc_violations', 'total_runtime_sec', 'timing_closure', 'drc_clean', 'lvs_clean',
    'wns_normalized', 'tns_normalized', 'log_area', 'log_power',
    'timing_closure_bin', 'drc_clean_bin', 'lvs_clean_bin', 'platform_cat',
}


# ═══════════════════════════════════════════════════════════════════════════
# PyTorch MLP Regressor
# ═══════════════════════════════════════════════════════════════════════════
class MLPRegressor(nn.Module):
    """Multi-layer perceptron for tabular regression."""

    def __init__(self, input_dim: int, hidden_dims=(256, 128, 64), dropout=0.2):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev_dim, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev_dim = h
        layers.append(nn.Linear(prev_dim, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_mlp(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    epochs: int = 200,
    lr: float = 1e-3,
    batch_size: int = 64,
    patience: int = 20,
    device: str = 'cpu',
) -> nn.Module:
    """Train PyTorch MLP with early stopping."""
    input_dim = X_train.shape[1]
    model = MLPRegressor(input_dim).to(device)

    train_tensor = torch.utils.data.TensorDataset(
        torch.FloatTensor(X_train), torch.FloatTensor(y_train)
    )
    val_tensor = torch.utils.data.TensorDataset(
        torch.FloatTensor(X_val), torch.FloatTensor(y_val)
    )
    train_loader = torch.utils.data.DataLoader(train_tensor, batch_size=batch_size, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_tensor, batch_size=batch_size, shuffle=False)

    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)

    best_val_loss = float('inf')
    best_state = None
    wait = 0

    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * xb.size(0)
        train_loss /= len(train_loader.dataset)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                pred = model(xb)
                val_loss += criterion(pred, yb).item() * xb.size(0)
        val_loss /= len(val_loader.dataset)

        scheduler.step(val_loss)

        if epoch % 20 == 0:
            print(f"  Epoch {epoch:3d}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}")

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                print(f"  Early stopping at epoch {epoch}")
                break

    # Load best weights
    if best_state:
        model.load_state_dict(best_state)

    return model


def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray, target_name: str) -> dict:
    """Compute regression metrics."""
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1e-8))) * 100

    print(f"  {target_name}: RMSE={rmse:.4f}, MAE={mae:.4f}, R²={r2:.4f}, MAPE={mape:.2f}%")
    return {'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape}


def save_residual_plot(y_true, y_pred, target_name, model_type, log_dir: Path):
    """Save residual plot."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.figure(figsize=(5, 4))
        plt.scatter(y_true, y_true - y_pred, alpha=0.5, s=10)
        plt.axhline(y=0, color='r', linestyle='--')
        plt.xlabel('Actual')
        plt.ylabel('Residual')
        plt.title(f'{target_name} - Residuals ({model_type})')
        plt.tight_layout()
        plt.savefig(log_dir / f'residuals_{target_name}_{model_type}.png', dpi=150, bbox_inches='tight')
        plt.close()
    except Exception as e:
        print(f"  Warning: Could not save residual plot: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# Main training function
# ══════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Train surrogate models for PPA prediction")
    parser.add_argument('--data-path', type=Path, default=DEFAULT_DATA_PATH,
                        help='Path to training_data.parquet')
    parser.add_argument('--epochs', type=int, default=200, help='MLP training epochs')
    parser.add_argument('--lr', type=float, default=1e-3, help='MLP learning rate')
    parser.add_argument('--batch-size', type=int, default=64, help='MLP batch size')
    parser.add_argument('--ensemble', action='store_true', help='Train LightGBM + MLP ensemble')
    parser.add_argument('--device', type=str, default='cpu', choices=['cpu', 'mps', 'cuda'],
                        help='Device for PyTorch training')
    args = parser.parse_args()

    print("=" * 70)
    print("SURROGATE MODELS TRAINING — PPA Regression Ensemble")
    print("=" * 70)
    print(f"Data: {args.data_path}")
    print(f"Device: {args.device}")
    print(f"Ensemble: {args.ensemble}")
    print("=" * 70)

    # ── Load data ────────────────────────────────────────────────────────
    if not args.data_path.exists():
        raise FileNotFoundError(f"Data not found: {args.data_path}. Run generate_dataset.py first.")

    df = pl.read_parquet(args.data_path)
    df_pd = df.to_pandas()
    print(f"Loaded {len(df_pd)} samples, {df_pd.shape[1]} columns")

    # ── Prepare features ────────────────────────────────────────────────
    drop_cols = [c for c in DROP_COLS if c in df_pd.columns]
    X_df = df_pd.drop(columns=drop_cols, errors='ignore')

    # Ensure all expected features exist
    expected_features = set(CATEGORICAL_FEATURES + NUMERIC_FEATURES)
    missing = expected_features - set(X_df.columns)
    if missing:
        raise ValueError(f"Missing expected features: {missing}")

    # ── Preprocessor ────────────────────────────────────────────────────
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL_FEATURES),
            ('num', StandardScaler(), NUMERIC_FEATURES),
        ],
        remainder='drop'
    )

    X_processed = preprocessor.fit_transform(df_pd)
    print(f"Processed feature shape: {X_processed.shape}")

    # Save preprocessor
    joblib.dump(preprocessor, MODEL_DIR / "surrogate_preprocessor.pkl")
    print(f"Saved preprocessor to {MODEL_DIR / 'surrogate_preprocessor.pkl'}")

    # ── Train/test split (same indices for all targets) ─────────────────
    indices = np.arange(len(df_pd))
    train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42)
    X_train, X_test = X_processed[train_idx], X_processed[test_idx]

    print(f"Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")

    # ── Train models per target ────────────────────────────────────────
    all_results = {}

    for short_name, target_col in REGRESSION_TARGETS.items():
        print(f"\n{'='*70}")
        print(f"TARGET: {target_col} ({short_name.upper()})")
        print(f"{'='*70}")

        y = df_pd[target_col].values
        y_train, y_test = y[train_idx], y[test_idx]

        target_results = {}

        # ── LightGBM ────────────────────────────────────────────────────
        print("\n--- LightGBM ---")
        lgb_train = lgb.Dataset(X_train, label=y_train)
        lgb_val = lgb.Dataset(X_test, label=y_test, reference=lgb_train)

        lgb_params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 63,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'min_child_samples': 20,
            'lambda_l1': 0.1,
            'lambda_l2': 1.0,
            'verbose': -1,
            'seed': 42,
            'num_threads': 1,
            'force_col_wise': True,
        }

        lgb_model = lgb.train(
            lgb_params,
            lgb_train,
            num_boost_round=500,
            valid_sets=[lgb_train, lgb_val],
            valid_names=['train', 'val'],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(50)],
        )

        y_pred_lgb = lgb_model.predict(X_test, num_iteration=lgb_model.best_iteration)
        lgb_metrics = evaluate_regression(y_test, y_pred_lgb, short_name.upper())
        save_residual_plot(y_test, y_pred_lgb, short_name, 'lgb', LOG_DIR)

        # Save LightGBM model
        joblib.dump(
            {'model': lgb_model, 'target': target_col, 'preprocessor': preprocessor},
            MODEL_DIR / f"surrogate_{short_name}_lgb.pkl"
        )
        target_results['lightgbm'] = lgb_metrics

        # ── PyTorch MLP ─────────────────────────────────────────────────
        if args.ensemble:
            print("\n--- PyTorch MLP ---")
            device = args.device if torch.cuda.is_available() or args.device == 'cpu' else 'cpu'
            if device == 'mps' and not torch.backends.mps.is_available():
                device = 'cpu'
                print("  MPS not available, falling back to CPU")

            mlp_model = train_mlp(
                X_train, y_train, X_test, y_test,
                epochs=args.epochs, lr=args.lr, batch_size=args.batch_size,
                device=device
            )

            # Evaluate MLP
            mlp_model.eval()
            with torch.no_grad():
                y_pred_mlp = mlp_model(torch.FloatTensor(X_test).to(device)).cpu().numpy()

            mlp_metrics = evaluate_regression(y_test, y_pred_mlp, short_name.upper())
            save_residual_plot(y_test, y_pred_mlp, short_name, 'mlp', LOG_DIR)

            # Save MLP model
            torch.save({
                'model_state': mlp_model.state_dict(),
                'input_dim': X_train.shape[1],
                'target': target_col,
                'preprocessor': preprocessor,
            }, MODEL_DIR / f"surrogate_{short_name}_mlp.pt")
            target_results['mlp'] = mlp_metrics

        # ── Ensemble (simple average) ───────────────────────────────────
        if args.ensemble:
            y_pred_ensemble = (y_pred_lgb + y_pred_mlp) / 2
            ens_metrics = evaluate_regression(y_test, y_pred_ensemble, f"{short_name.upper()} (Ensemble)")
            target_results['ensemble'] = ens_metrics

        all_results[short_name] = target_results

    # ── Save results summary ────────────────────────────────────────────
    results_path = LOG_DIR / "surrogate_results.json"
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2)

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE — SUMMARY")
    print("=" * 70)
    for target, res in all_results.items():
        if 'ensemble' in res:
            print(f"  {target:5s}: LGB R²={res['lightgbm']['r2']:.4f}  "
                  f"MLP R²={res['mlp']['r2']:.4f}  "
                  f"Ensemble R²={res['ensemble']['r2']:.4f}")
        else:
            print(f"  {target:5s}: LGB R²={res['lightgbm']['r2']:.4f}")

    print(f"\nModels saved to: {MODEL_DIR}")
    print(f"Logs saved to:   {LOG_DIR}")


if __name__ == '__main__':
    main()