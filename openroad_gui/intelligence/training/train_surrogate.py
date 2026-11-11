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

# Cross-validation settings
N_SPLITS = 5
RANDOM_STATE = 42
TEST_SIZE = 0.1  # Hold-out test set never used in CV


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
def create_preprocessor():
    """Create a fresh preprocessor (no fitting)."""
    return ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL_FEATURES),
            ('num', StandardScaler(), NUMERIC_FEATURES),
        ],
        remainder='drop'
    )


def run_cv_for_target(df_pd, target_col, short_name, args, log_dir):
    """Run stratified K-fold CV for a single target."""
    from sklearn.model_selection import StratifiedKFold

    # Create stratification key: platform + timing_closure_bin (binned WNS for regression)
    # For regression, bin WNS into quantiles for stratification
    y = df_pd[target_col].values
    platform = df_pd['platform'].values

    # Create stratification bins: platform + WNS quantile (for WNS/TNS) or area/power quantile
    if short_name in ('wns', 'tns'):
        # Bin target into 5 quantiles for stratification
        try:
            y_binned = pd.qcut(y, q=5, labels=False, duplicates='drop')
        except ValueError:
            y_binned = pd.cut(y, bins=5, labels=False)
    else:
        try:
            y_binned = pd.qcut(y, q=5, labels=False, duplicates='drop')
        except ValueError:
            y_binned = pd.cut(y, bins=5, labels=False)

    stratify_key = platform.astype(str) + '_' + y_binned.astype(str)

    # Prepare feature matrix (without fitting preprocessor yet)
    drop_cols = [c for c in DROP_COLS if c in df_pd.columns]
    X_df = df_pd.drop(columns=drop_cols, errors='ignore')

    expected_features = set(CATEGORICAL_FEATURES + NUMERIC_FEATURES)
    missing = expected_features - set(X_df.columns)
    if missing:
        raise ValueError(f"Missing expected features: {missing}")

    # Outer CV split
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    # Hold-out test set (never used in CV)
    cv_indices = list(cv.split(X_df, stratify_key))
    # Use last fold as hold-out test
    train_val_idx, test_idx = cv_indices[-1]
    cv_indices = cv_indices[:-1]  # First N-1 folds for CV

    print(f"  CV folds: {len(cv_indices)}, Hold-out test: {len(test_idx)} samples")

    cv_results = {'lightgbm': [], 'mlp': [], 'ensemble': []}
    fold_models = []

    for fold, (train_idx, val_idx) in enumerate(cv_indices):
        print(f"\n  --- Fold {fold + 1}/{len(cv_indices)} ---")

        X_train_df = X_df.iloc[train_idx]
        X_val_df = X_df.iloc[val_idx]
        y_train = y[train_idx]
        y_val = y[val_idx]

        # Fit preprocessor ONLY on training data (no leakage!)
        preprocessor = create_preprocessor()
        X_train = preprocessor.fit_transform(X_train_df)
        X_val = preprocessor.transform(X_val_df)

        fold_result = {}

        # ── LightGBM ────────────────────────────────────────────────────
        print("    LightGBM...")
        lgb_train = lgb.Dataset(X_train, label=y_train)
        lgb_val = lgb.Dataset(X_val, label=y_val, reference=lgb_train)

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
            callbacks=[lgb.early_stopping(30), lgb.log_evaluation(0)],  # Quiet during CV
        )

        y_pred_lgb = lgb_model.predict(X_val, num_iteration=lgb_model.best_iteration)
        lgb_metrics = evaluate_regression(y_val, y_pred_lgb, f"{short_name.upper()} (LGB Fold {fold+1})")
        cv_results['lightgbm'].append(lgb_metrics)
        fold_models.append(('lgb', lgb_model, preprocessor))

        # ── PyTorch MLP ─────────────────────────────────────────────────
        if args.ensemble:
            print("    PyTorch MLP...")
            device = args.device if torch.cuda.is_available() or args.device == 'cpu' else 'cpu'
            if device == 'mps' and not torch.backends.mps.is_available():
                device = 'cpu'

            mlp_model = train_mlp(
                X_train, y_train, X_val, y_val,
                epochs=args.epochs, lr=args.lr, batch_size=args.batch_size,
                device=device
            )

            mlp_model.eval()
            with torch.no_grad():
                y_pred_mlp = mlp_model(torch.FloatTensor(X_val).to(device)).cpu().numpy()

            mlp_metrics = evaluate_regression(y_val, y_pred_mlp, f"{short_name.upper()} (MLP Fold {fold+1})")
            cv_results['mlp'].append(mlp_metrics)
            fold_models.append(('mlp', mlp_model, preprocessor))

            # ── Ensemble ────────────────────────────────────────────────
            y_pred_ensemble = (y_pred_lgb + y_pred_mlp) / 2
            ens_metrics = evaluate_regression(y_val, y_pred_ensemble, f"{short_name.upper()} (Ensemble Fold {fold+1})")
            cv_results['ensemble'].append(ens_metrics)

    # ── Train final models on full train+val data ───────────────────────
    print(f"\n  --- Training final models on {len(train_val_idx)} samples ---")
    X_trainval_df = X_df.iloc[train_val_idx]
    y_trainval = y[train_val_idx]

    final_preprocessor = create_preprocessor()
    X_trainval = final_preprocessor.fit_transform(X_trainval_df)
    X_test_final = final_preprocessor.transform(X_df.iloc[test_idx])
    y_test_final = y[test_idx]

    final_models = {}

    # Final LightGBM
    lgb_train_full = lgb.Dataset(X_trainval, label=y_trainval)
    lgb_val_full = lgb.Dataset(X_test_final, label=y_test_final, reference=lgb_train_full)

    lgb_model_final = lgb.train(
        lgb_params,
        lgb_train_full,
        num_boost_round=500,
        valid_sets=[lgb_train_full, lgb_val_full],
        valid_names=['train', 'val'],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(50)],
    )

    y_pred_lgb_final = lgb_model_final.predict(X_test_final, num_iteration=lgb_model_final.best_iteration)
    lgb_metrics_final = evaluate_regression(y_test_final, y_pred_lgb_final, f"{short_name.upper()} (Final LGB)")
    final_models['lightgbm'] = lgb_model_final

    # Final MLP
    if args.ensemble:
        device = args.device if torch.cuda.is_available() or args.device == 'cpu' else 'cpu'
        if device == 'mps' and not torch.backends.mps.is_available():
            device = 'cpu'

        mlp_model_final = train_mlp(
            X_trainval, y_trainval, X_test_final, y_test_final,
            epochs=args.epochs, lr=args.lr, batch_size=args.batch_size,
            device=device
        )

        mlp_model_final.eval()
        with torch.no_grad():
            y_pred_mlp_final = mlp_model_final(torch.FloatTensor(X_test_final).to(device)).cpu().numpy()

        mlp_metrics_final = evaluate_regression(y_test_final, y_pred_mlp_final, f"{short_name.upper()} (Final MLP)")
        final_models['mlp'] = mlp_model_final

        y_pred_ensemble_final = (y_pred_lgb_final + y_pred_mlp_final) / 2
        ens_metrics_final = evaluate_regression(y_test_final, y_pred_ensemble_final, f"{short_name.upper()} (Final Ensemble)")
        final_models['ensemble_metrics'] = ens_metrics_final

    # Save final models with preprocessor
    joblib.dump(
        {'model': lgb_model_final, 'target': target_col, 'preprocessor': final_preprocessor},
        MODEL_DIR / f"surrogate_{short_name}_lgb.pkl"
    )
    if args.ensemble:
        torch.save({
            'model_state': mlp_model_final.state_dict(),
            'input_dim': X_trainval.shape[1],
            'target': target_col,
            'preprocessor': final_preprocessor,
        }, MODEL_DIR / f"surrogate_{short_name}_mlp.pt")

    # Save preprocessor separately for inference
    joblib.dump(final_preprocessor, MODEL_DIR / "surrogate_preprocessor.pkl")

    # Aggregate CV results
    print(f"\n  {'='*50}")
    print(f"  CV RESULTS SUMMARY ({short_name.upper()})")
    print(f"  {'='*50}")
    for model_type, metrics_list in cv_results.items():
        if not metrics_list:
            continue
        mean_r2 = np.mean([m['r2'] for m in metrics_list])
        std_r2 = np.std([m['r2'] for m in metrics_list])
        mean_rmse = np.mean([m['rmse'] for m in metrics_list])
        mean_mae = np.mean([m['mae'] for m in metrics_list])
        print(f"    {model_type:12s}: R² = {mean_r2:.4f} ± {std_r2:.4f}, RMSE = {mean_rmse:.4f}, MAE = {mean_mae:.4f}")

    # Return final test metrics
    final_metrics = {
        'lightgbm': lgb_metrics_final,
        'cv_results': cv_results,
    }
    if args.ensemble:
        final_metrics['mlp'] = mlp_metrics_final
        final_metrics['ensemble'] = final_models['ensemble_metrics']

    return final_metrics


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
    parser.add_argument('--no-cv', action='store_true', help='Disable cross-validation (single split)')
    args = parser.parse_args()

    print("=" * 70)
    print("SURROGATE MODELS TRAINING — PPA Regression Ensemble")
    print("=" * 70)
    print(f"Data: {args.data_path}")
    print(f"Device: {args.device}")
    print(f"Ensemble: {args.ensemble}")
    print(f"Cross-validation: {not args.no_cv} ({N_SPLITS}-fold stratified)")
    print("=" * 70)

    # ── Load data ────────────────────────────────────────────────────────
    if not args.data_path.exists():
        raise FileNotFoundError(f"Data not found: {args.data_path}. Run generate_dataset.py first.")

    df = pl.read_parquet(args.data_path)
    df_pd = df.to_pandas()
    print(f"Loaded {len(df_pd)} samples, {df_pd.shape[1]} columns")

    # ── Train models per target ────────────────────────────────────────
    all_results = {}

    for short_name, target_col in REGRESSION_TARGETS.items():
        print(f"\n{'='*70}")
        print(f"TARGET: {target_col} ({short_name.upper()})")
        print(f"{'='*70}")

        if args.no_cv:
            # Original single-split logic (for backward compatibility)
            drop_cols = [c for c in DROP_COLS if c in df_pd.columns]
            X_df = df_pd.drop(columns=drop_cols, errors='ignore')

            expected_features = set(CATEGORICAL_FEATURES + NUMERIC_FEATURES)
            missing = expected_features - set(X_df.columns)
            if missing:
                raise ValueError(f"Missing expected features: {missing}")

            preprocessor = ColumnTransformer(
                transformers=[
                    ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL_FEATURES),
                    ('num', StandardScaler(), NUMERIC_FEATURES),
                ],
                remainder='drop'
            )

            X_processed = preprocessor.fit_transform(df_pd)
            print(f"Processed feature shape: {X_processed.shape}")

            joblib.dump(preprocessor, MODEL_DIR / "surrogate_preprocessor.pkl")

            indices = np.arange(len(df_pd))
            train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42)
            X_train, X_test = X_processed[train_idx], X_processed[test_idx]

            y = df_pd[target_col].values
            y_train, y_test = y[train_idx], y[test_idx]

            target_results = {}

            # LightGBM
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

            joblib.dump(
                {'model': lgb_model, 'target': target_col, 'preprocessor': preprocessor},
                MODEL_DIR / f"surrogate_{short_name}_lgb.pkl"
            )
            target_results['lightgbm'] = lgb_metrics

            if args.ensemble:
                # MLP
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

                mlp_model.eval()
                with torch.no_grad():
                    y_pred_mlp = mlp_model(torch.FloatTensor(X_test).to(device)).cpu().numpy()

                mlp_metrics = evaluate_regression(y_test, y_pred_mlp, short_name.upper())
                save_residual_plot(y_test, y_pred_mlp, short_name, 'mlp', LOG_DIR)

                torch.save({
                    'model_state': mlp_model.state_dict(),
                    'input_dim': X_train.shape[1],
                    'target': target_col,
                    'preprocessor': preprocessor,
                }, MODEL_DIR / f"surrogate_{short_name}_mlp.pt")
                target_results['mlp'] = mlp_metrics

                y_pred_ensemble = (y_pred_lgb + y_pred_mlp) / 2
                ens_metrics = evaluate_regression(y_test, y_pred_ensemble, f"{short_name.upper()} (Ensemble)")
                target_results['ensemble'] = ens_metrics

            all_results[short_name] = target_results

        else:
            # New CV-based training
            target_results = run_cv_for_target(df_pd, target_col, short_name, args, LOG_DIR)
            all_results[short_name] = target_results

    # ── Save results summary ────────────────────────────────────────────
    results_path = LOG_DIR / "surrogate_results.json"
    with open(results_path, 'w') as f:
        # Convert numpy types to Python for JSON serialization
        def convert(obj):
            if isinstance(obj, (np.floating, np.integer)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj

        json.dump(convert(all_results), f, indent=2)

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE — SUMMARY")
    print("=" * 70)
    for target, res in all_results.items():
        if 'cv_results' in res:
            # CV mode
            cv = res['cv_results']
            for model_type, metrics_list in cv.items():
                if not metrics_list:
                    continue
                mean_r2 = np.mean([m['r2'] for m in metrics_list])
                std_r2 = np.std([m['r2'] for m in metrics_list])
                print(f"  {target:5s} CV {model_type:12s}: R² = {mean_r2:.4f} ± {std_r2:.4f}")
            print(f"  {target:5s} Final LGB Test R²: {res['lightgbm']['r2']:.4f}")
            if 'ensemble' in res:
                print(f"  {target:5s} Final Ensemble Test R²: {res['ensemble']['r2']:.4f}")
        else:
            # Single split mode
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