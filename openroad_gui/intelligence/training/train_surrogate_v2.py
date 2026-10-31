#!/usr/bin/env python3
"""
Surrogate Models Training Script v2 — Real + Synthetic Data
Regression ensemble (LightGBM + PyTorch MLP) for PPA prediction with real ORFS data integration.

Key improvements over v1:
- Integrates real ORFS data from collect_real_data.py
- Proper target normalization (log-transform area/power, clip WNS/TNS)
- Better feature engineering matching real flow reports
- Domain adaptation: real data weighted higher
- Cross-validation with real-design holdout
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
from sklearn.model_selection import train_test_split, GroupKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

warnings.filterwarnings('ignore')

# M1/M2 compatibility
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['LIGHTGBM_NUM_THREADS'] = '1'

# ── Project paths ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SYNTHETIC_DATA_PATH = PROJECT_ROOT / "dataset_genration" / "output" / "training_data.parquet"
REAL_DATA_PATH = PROJECT_ROOT / "openroad_gui" / "intelligence" / "data" / "real_runs.json"
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

# Target columns in the combined dataset
REGRESSION_TARGETS = {
    'wns': 'final_wns_ns',
    'tns': 'final_tns_ns',
    'area': 'final_area_um2',
    'power': 'final_power_mw',
}

# Columns to drop (not features, not targets)
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
# Data Loading & Processing
# ═══════════════════════════════════════════════════════════════════════════

def load_real_data(real_data_path: Path) -> pd.DataFrame:
    """Load and process real ORFS data from collect_real_data.py output."""
    if not real_data_path.exists():
        print(f"  Real data not found at {real_data_path}")
        return pd.DataFrame()

    try:
        with open(real_data_path, 'r') as f:
            real_records = json.load(f)

        if not real_records:
            print("  Real data file is empty")
            return pd.DataFrame()

        df_real = pd.DataFrame(real_records)
        print(f"  Loaded {len(df_real)} real ORFS runs")

        # Ensure required columns exist
        required_cols = ['design_name', 'platform', 'core_utilization', 'core_aspect_ratio',
                         'core_margin', 'num_instances', 'num_nets', 'num_sequential',
                         'num_macros', 'macro_area_ratio', 'final_wns_ns', 'final_tns_ns',
                         'final_area_um2', 'final_power_mw', 'final_drc_violations',
                         'final_congestion_pct', 'final_setup_violations', 'final_hold_violations',
                         'stage_runtimes', 'total_runtime_sec', 'timing_closure', 'drc_clean', 'lvs_clean']

        missing = [c for c in required_cols if c not in df_real.columns]
        if missing:
            print(f"  Warning: Missing columns in real data: {missing}")
            # Add missing with defaults
            for col in missing:
                if col in ['final_congestion_pct', 'final_setup_violations', 'final_hold_violations']:
                    df_real[col] = 0
                elif col in ['stage_runtimes']:
                    df_real[col] = '{}'
                elif col in ['total_runtime_sec']:
                    df_real[col] = 0
                elif col in ['timing_closure']:
                    df_real[col] = df_real.get('final_wns_ns', 0) >= 0
                elif col in ['drc_clean']:
                    df_real[col] = df_real.get('final_drc_violations', 1) == 0
                elif col in ['lvs_clean']:
                    df_real[col] = True

        import numpy as np
        from datetime import datetime, timedelta

        # Add engineered features
        df_real['log_instances'] = np.log1p(df_real['num_instances']) / 20
        df_real['log_nets'] = np.log1p(df_real['num_nets']) / 20
        df_real['seq_ratio'] = df_real['num_sequential'] / np.maximum(df_real['num_instances'], 1)
        df_real['macro_ratio'] = df_real['num_macros'] / np.maximum(df_real['num_instances'], 1)
        df_real['log_area'] = np.log1p(df_real['final_area_um2']) / 20
        df_real['log_power'] = np.log1p(df_real['final_power_mw']) / 20
        df_real['wns_normalized'] = np.clip(df_real['final_wns_ns'] / 10, -1, 1)
        df_real['tns_normalized'] = np.clip(df_real['final_tns_ns'] / 1000, -1, 1)
        df_real['timing_closure_bin'] = (df_real['final_wns_ns'] >= 0).astype(int)
        df_real['drc_clean_bin'] = (df_real['final_drc_violations'] == 0).astype(int)
        df_real['lvs_clean_bin'] = df_real['lvs_clean'].astype(int)
        df_real['platform_cat'] = df_real['platform']
        df_real['design_name_config'] = df_real['design_name']
        df_real['platform_config'] = df_real['platform']

        # Generate run_id and timestamp if missing
        if 'run_id' not in df_real.columns:
            df_real['run_id'] = [f"{d}_{p}_real_{i:08x}" for i, (d, p) in enumerate(zip(df_real['design_name'], df_real['platform']))]
        if 'timestamp' not in df_real.columns:
            from datetime import datetime, timedelta
            import numpy as np
            rng = np.random.default_rng(42)
            anchor = datetime.now()
            df_real['timestamp'] = [(anchor - timedelta(seconds=float(s))).isoformat()
                                     for s in rng.uniform(0, 365 * 86400, len(df_real))]

        return df_real

    except Exception as e:
        print(f"  Error loading real data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_synthetic_data(synthetic_path: Path) -> pd.DataFrame:
    """Load synthetic training data."""
    if not synthetic_path.exists():
        print(f"  Synthetic data not found at {synthetic_path}")
        return pd.DataFrame()

    try:
        df_syn = pl.read_parquet(synthetic_path).to_pandas()
        print(f"  Loaded {len(df_syn)} synthetic samples")
        return df_syn
    except Exception as e:
        print(f"  Error loading synthetic data: {e}")
        return pd.DataFrame()


def combine_datasets(df_real: pd.DataFrame, df_syn: pd.DataFrame, real_weight: float = 5.0) -> pd.DataFrame:
    """
    Combine real and synthetic datasets with domain adaptation weighting.

    Args:
        df_real: Real ORFS data
        df_syn: Synthetic data
        real_weight: Weight multiplier for real samples (higher = more important)

    Returns:
        Combined DataFrame with sample_weight column
    """
    if len(df_real) == 0:
        print("  No real data, using synthetic only")
        df_syn['sample_weight'] = 1.0
        df_syn['data_source'] = 'synthetic'
        return df_syn

    if len(df_syn) == 0:
        print("  No synthetic data, using real only")
        df_real['sample_weight'] = real_weight
        df_real['data_source'] = 'real'
        return df_real

    # Align columns
    all_cols = set(df_real.columns) | set(df_syn.columns)
    for df in [df_real, df_syn]:
        for col in all_cols:
            if col not in df.columns:
                df[col] = np.nan

    # Ensure consistent column order
    df_real = df_real[sorted(all_cols)]
    df_syn = df_syn[sorted(all_cols)]

    # Add source and weight
    df_real['data_source'] = 'real'
    df_real['sample_weight'] = real_weight
    df_syn['data_source'] = 'synthetic'
    df_syn['sample_weight'] = 1.0

    # Combine
    df_combined = pd.concat([df_real, df_syn], ignore_index=True)
    df_combined = df_combined.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"  Combined: {len(df_real)} real (weight={real_weight}) + {len(df_syn)} synthetic (weight=1.0)")
    print(f"  Total: {len(df_combined)} samples")

    return df_combined


def normalize_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply target transformations for better regression:
    - WNS/TNS: Clip to reasonable range, no transform (can be negative)
    - Area/Power: Log-transform (positive, skewed)
    """
    df = df.copy()

    # Clip WNS/TNS to reasonable range for training stability
    df['final_wns_ns'] = np.clip(df['final_wns_ns'], -500, 100)
    df['final_tns_ns'] = np.clip(df['final_tns_ns'], -10000, 100)

    # Log transform area and power (they're positive and skewed)
    df['final_area_um2_log'] = np.log1p(np.maximum(df['final_area_um2'], 0))
    df['final_power_mw_log'] = np.log1p(np.maximum(df['final_power_mw'], 0))

    return df


def prepare_features_targets(df: pd.DataFrame, target_col: str):
    """Prepare features and target for a specific regression target."""
    drop_cols = [c for c in DROP_COLS if c in df.columns]
    X_df = df.drop(columns=drop_cols, errors='ignore')

    # Ensure all expected features exist
    expected_features = set(CATEGORICAL_FEATURES + NUMERIC_FEATURES)
    missing = expected_features - set(X_df.columns)
    if missing:
        raise ValueError(f"Missing expected features: {missing}")

    # Handle target column - use log-transformed version for area/power
    if target_col == 'final_area_um2':
        y_col = 'final_area_um2_log'
    elif target_col == 'final_power_mw':
        y_col = 'final_power_mw_log'
    else:
        y_col = target_col

    y = df[y_col].values
    weights = df['sample_weight'].values if 'sample_weight' in df.columns else None
    groups = df['design_name'].values if 'design_name' in df.columns else None

    return X_df, y, weights, groups


# ═══════════════════════════════════════════════════════════════════════════
# Main training function
# ═══════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Train surrogate models for PPA prediction (v2: real + synthetic)")
    parser.add_argument('--synthetic-data', type=Path, default=SYNTHETIC_DATA_PATH,
                        help='Path to synthetic training_data.parquet')
    parser.add_argument('--real-data', type=Path, default=REAL_DATA_PATH,
                        help='Path to real ORFS runs JSON')
    parser.add_argument('--real-weight', type=float, default=5.0,
                        help='Weight multiplier for real samples')
    parser.add_argument('--epochs', type=int, default=200, help='MLP training epochs')
    parser.add_argument('--lr', type=float, default=1e-3, help='MLP learning rate')
    parser.add_argument('--batch-size', type=int, default=64, help='MLP batch size')
    parser.add_argument('--ensemble', action='store_true', help='Train LightGBM + MLP ensemble')
    parser.add_argument('--device', type=str, default='cpu', choices=['cpu', 'mps', 'cuda'],
                        help='Device for PyTorch training')
    parser.add_argument('--cv-folds', type=int, default=5, help='CV folds for evaluation')
    args = parser.parse_args()

    print("=" * 70)
    print("SURROGATE MODELS TRAINING v2 — Real + Synthetic Data")
    print("=" * 70)
    print(f"Synthetic data: {args.synthetic_data}")
    print(f"Real data:      {args.real_data}")
    print(f"Real weight:    {args.real_weight}x")
    print(f"Device:         {args.device}")
    print(f"Ensemble:       {args.ensemble}")
    print(f"CV folds:       {args.cv_folds}")
    print("=" * 70)

    # ── Load data ────────────────────────────────────────────────────────
    df_real = load_real_data(args.real_data)
    df_syn = load_synthetic_data(args.synthetic_data)

    if len(df_real) == 0 and len(df_syn) == 0:
        raise FileNotFoundError("No training data available!")

    # Combine datasets
    df = combine_datasets(df_real, df_syn, args.real_weight)

    # Normalize targets
    df = normalize_targets(df)

    # Fill any NaN values
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna('unknown')
    for col in NUMERIC_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    # ── Preprocessor ────────────────────────────────────────────────────
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL_FEATURES),
            ('num', StandardScaler(), NUMERIC_FEATURES),
        ],
        remainder='drop'
    )

    # Fit on all data
    X_all = df
    preprocessor.fit(X_all)

    # Save preprocessor
    joblib.dump(preprocessor, MODEL_DIR / "surrogate_preprocessor_v2.pkl")
    print(f"Saved preprocessor to {MODEL_DIR / 'surrogate_preprocessor_v2.pkl'}")

    # Transform features
    X_processed = preprocessor.transform(X_all)
    print(f"Processed feature shape: {X_processed.shape}")

    # ── Cross-validation with GroupKFold (by design) ────────────────────
    groups = df['design_name'].values if 'design_name' in df.columns else None

    if args.cv_folds > 1 and groups is not None and len(np.unique(groups)) >= args.cv_folds:
        print(f"\nRunning {args.cv_folds}-fold GroupKFold CV (by design)...")
        gkf = GroupKFold(n_splits=args.cv_folds)
        cv_results = {target: [] for target in REGRESSION_TARGETS}
    else:
        print("\nUsing simple train/test split (insufficient groups for GroupKFold)...")
        gkf = None
        indices = np.arange(len(df))
        train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42)

    # ── Train models per target ────────────────────────────────────────
    all_results = {}

    for short_name, target_col in REGRESSION_TARGETS.items():
        print(f"\n{'='*70}")
        print(f"TARGET: {target_col} ({short_name.upper()})")
        print(f"{'='*70}")

        X_df, y, weights, group_labels = prepare_features_targets(df, target_col)

        if gkf is not None:
            # Cross-validation
            fold_results = []
            for fold, (train_idx, test_idx) in enumerate(gkf.split(X_processed, y, groups=group_labels)):
                print(f"\n  --- Fold {fold+1}/{args.cv_folds} ---")

                X_train, X_test = X_processed[train_idx], X_processed[test_idx]
                y_train, y_test = y[train_idx], y[test_idx]
                w_train = weights[train_idx] if weights is not None else None
                w_test = weights[test_idx] if weights is not None else None

                fold_res = train_target_fold(
                    X_train, y_train, w_train,
                    X_test, y_test,
                    short_name, target_col,
                    fold, args
                )
                fold_results.append(fold_res)

            # Average CV results
            avg_r2 = np.mean([r.get('r2', 0) for r in fold_results])
            avg_rmse = np.mean([r.get('rmse', 0) for r in fold_results])
            print(f"\n  CV Average: RMSE={avg_rmse:.4f}, R²={avg_r2:.4f}")

            # Retrain on full data
            print("\n  Retraining on full dataset...")
            final_res = train_target_fold(
                X_processed, y, weights,
                X_processed, y,  # dummy test
                short_name, target_col,
                'final', args,
                is_final=True
            )
            all_results[short_name] = final_res

        else:
            # Simple train/test
            X_train, X_test = X_processed[train_idx], X_processed[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            w_train = weights[train_idx] if weights is not None else None

            res = train_target_fold(
                X_train, y_train, w_train,
                X_test, y_test,
                short_name, target_col,
                0, args
            )
            all_results[short_name] = res

    # ── Save results summary ────────────────────────────────────────────
    results_path = LOG_DIR / "surrogate_results_v2.json"
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


def train_target_fold(X_train, y_train, w_train, X_test, y_test,
                      short_name, target_col, fold, args, is_final=False):
    """Train models for a single target (and fold)."""
    target_results = {}

    # ── LightGBM ────────────────────────────────────────────────────
    print(f"\n--- LightGBM {'(Final)' if is_final else f'(Fold {fold+1})'} ---")
    lgb_train = lgb.Dataset(X_train, label=y_train, weight=w_train)
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
    lgb_metrics = evaluate_regression(y_test, y_pred_lgb, f"{short_name.upper()} LGB")
    save_residual_plot(y_test, y_pred_lgb, short_name, 'lgb', LOG_DIR)

    # Save LightGBM model
    model_suffix = '' if is_final else f'_fold{fold}'
    joblib.dump(
        {'model': lgb_model, 'target': target_col, 'preprocessor': None, 'target_transform': target_col},
        MODEL_DIR / f"surrogate_{short_name}_lgb{model_suffix}.pkl"
    )
    target_results['lightgbm'] = lgb_metrics

    # ── PyTorch MLP ─────────────────────────────────────────────────
    if args.ensemble:
        print(f"\n--- PyTorch MLP {'(Final)' if is_final else f'(Fold {fold+1})'} ---")
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

        mlp_metrics = evaluate_regression(y_test, y_pred_mlp, f"{short_name.upper()} MLP")
        save_residual_plot(y_test, y_pred_mlp, short_name, 'mlp', LOG_DIR)

        # Save MLP model
        torch.save({
            'model_state': mlp_model.state_dict(),
            'input_dim': X_train.shape[1],
            'target': target_col,
            'target_transform': target_col,
        }, MODEL_DIR / f"surrogate_{short_name}_mlp{model_suffix}.pt")
        target_results['mlp'] = mlp_metrics

        # ── Ensemble (simple average) ───────────────────────────────────
        y_pred_ensemble = (y_pred_lgb + y_pred_mlp) / 2
        ens_metrics = evaluate_regression(y_test, y_pred_ensemble, f"{short_name.upper()} (Ensemble)")
        target_results['ensemble'] = ens_metrics

    return target_results


if __name__ == '__main__':
    main()