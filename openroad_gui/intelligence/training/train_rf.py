#!/usr/bin/env python3
"""
Random Forest Training for PPA Prediction & Timing Closure Classification
OpenROAD Flow GUI - ML Models

Usage:
    python train_rf.py --target wns --tune
    python train_rf.py --target timing_closure --tune
    python train_rf.py --target all --compare
"""

import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
from sklearn.metrics import (
    r2_score, mean_squared_error, mean_absolute_error,
    roc_auc_score, accuracy_score, precision_score, recall_score, f1_score,
    classification_report, roc_curve, auc
)
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_predict, StratifiedKFold, KFold
from sklearn.inspection import permutation_importance
import optuna
from optuna.samplers import TPESampler

warnings.filterwarnings('ignore')

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_PATH = PROJECT_ROOT / "dataset_genration" / "output" / "training_data.parquet"
MODEL_DIR = PROJECT_ROOT / "openroad_gui" / "intelligence" / "models" / "saved"
LOG_DIR = PROJECT_ROOT / "openroad_gui" / "intelligence" / "training" / "logs"

for d in (MODEL_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Target definitions
REGRESSION_TARGETS = {
    'wns': 'final_wns_ns',
    'tns': 'final_tns_ns',
    'area': 'final_area_um2',
    'power': 'final_power_mw',
}

CLASSIFICATION_TARGETS = {
    'timing_closure': 'timing_closure_bin',
    'drc_clean': 'drc_clean_bin',
}

ALL_TARGETS = {**REGRESSION_TARGETS, **CLASSIFICATION_TARGETS}

DROP_COLS = {
    'run_id', 'design_name', 'timestamp', 'design_name_config', 'platform_config',
    'final_drc_violations', 'total_runtime_sec', 'timing_closure', 'drc_clean', 'lvs_clean',
    'wns_normalized', 'tns_normalized', 'log_area', 'log_power',
    'timing_closure_bin', 'drc_clean_bin', 'lvs_clean_bin', 'platform_cat',
}

# Feature columns (must match training data)
CATEGORICAL_FEATURES = ['platform', 'core_aspect_ratio']
NUMERIC_FEATURES = [
    'core_utilization', 'core_margin',
    'num_instances', 'num_nets', 'num_sequential', 'num_macros', 'macro_area_ratio',
    'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
]

ALL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

# RF Default Hyperparameters
RF_REG_DEFAULTS = {
    'n_estimators': 500,
    'max_depth': 15,
    'min_samples_split': 5,
    'min_samples_leaf': 2,
    'max_features': 'sqrt',
    'bootstrap': True,
    'random_state': 42,
    'n_jobs': -1,
}

RF_CLF_DEFAULTS = {
    'n_estimators': 500,
    'max_depth': 15,
    'min_samples_split': 5,
    'min_samples_leaf': 2,
    'max_features': 'sqrt',
    'class_weight': 'balanced',
    'bootstrap': True,
    'random_state': 42,
    'n_jobs': -1,
}

# Optuna Search Spaces
RF_REG_SEARCH_SPACE = {
    'n_estimators': (200, 1000),
    'max_depth': (10, 30),
    'min_samples_split': (2, 10),
    'min_samples_leaf': (1, 5),
    'max_features': ['sqrt', 'log2', 0.3, 0.5],
    'min_impurity_decrease': (0.0, 0.01),
}

RF_CLF_SEARCH_SPACE = {
    'n_estimators': (200, 1000),
    'max_depth': (10, 30),
    'min_samples_split': (2, 10),
    'min_samples_leaf': (1, 5),
    'max_features': ['sqrt', 'log2', 0.3, 0.5],
    'class_weight': ['balanced', 'balanced_subsample', None],
    'min_impurity_decrease': (0.0, 0.01),
}

# ── Utility Functions ─────────────────────────────────────────────────────────
def load_data():
    """Load and prepare training data."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Data not found: {DATA_PATH}. Run generate_dataset.py first.")

    df = pd.read_parquet(DATA_PATH)
    print(f"Loaded {len(df)} samples, {df.shape[1]} columns")

    # Prepare feature matrix
    drop_cols = [c for c in DROP_COLS if c in df.columns]
    X_df = df.drop(columns=drop_cols, errors='ignore')

    # Ensure all expected features exist
    expected_features = set(ALL_FEATURES)
    missing = expected_features - set(X_df.columns)
    if missing:
        raise ValueError(f"Missing expected features: {missing}")

    # Handle categorical features
    for cat in CATEGORICAL_FEATURES:
        if cat in X_df.columns:
            X_df[cat] = X_df[cat].astype('category')

    return df, X_df


def prepare_targets(df, target_name):
    """Extract target variable."""
    target_col = ALL_TARGETS[target_name]
    if target_col not in df.columns:
        raise ValueError(f"Target column {target_col} not found in data")
    return df[target_col].values, target_col


def get_cv_splitter(target_name, y):
    """Get appropriate CV splitter for target type."""
    if target_name in CLASSIFICATION_TARGETS:
        return StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    else:
        return KFold(n_splits=5, shuffle=True, random_state=42)


def evaluate_regression(y_true, y_pred, target_name):
    """Compute regression metrics."""
    mse = np.mean((y_true - y_pred) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(y_true - y_pred))
    r2 = r2_score(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1e-8))) * 100

    print(f"  {target_name}: RMSE={rmse:.4f}, MAE={mae:.4f}, R²={r2:.4f}, MAPE={mape:.2f}%")
    return {'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape}


def evaluate_classification(y_true, y_pred, y_proba, target_name):
    """Compute classification metrics."""
    auc = roc_auc_score(y_true, y_proba)
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    print(f"  {target_name}: AUC={auc:.4f}, Acc={acc:.4f}, Prec={prec:.4f}, Rec={rec:.4f}, F1={f1:.4f}")
    print(classification_report(y_true, y_pred, zero_division=0))

    return {'auc': auc, 'accuracy': acc, 'precision': prec, 'recall': rec, 'f1': f1}


def run_cv_rf(X, y, target_name, params, n_splits=5, random_state=42):
    """Run cross-validation for RF model."""
    cv = get_cv_splitter(target_name, y)
    cv_scores = []

    is_classification = target_name in CLASSIFICATION_TARGETS

    # Convert to numpy arrays to avoid pandas indexing issues with integer indices
    X_array = X.values if hasattr(X, 'values') else X
    y_array = y.values if hasattr(y, 'values') else y

    for fold, (train_idx, val_idx) in enumerate(cv.split(X_array, y_array)):
        X_train, X_val = X_array[train_idx], X_array[val_idx]
        y_train, y_val = y_array[train_idx], y_array[val_idx]

        if target_name in CLASSIFICATION_TARGETS:
            model = RandomForestClassifier(**params)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
            y_proba = model.predict_proba(X_val)[:, 1]
            auc = roc_auc_score(y_val, y_proba)
            print(f"  Fold {fold+1}: AUC={auc:.4f}")
            cv_scores.append(auc)
        else:
            model = RandomForestRegressor(**params)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
            r2 = r2_score(y_val, y_pred)
            print(f"  Fold {fold+1}: R²={r2:.4f}")
            cv_scores.append(r2)

    mean_score = np.mean(cv_scores)
    std_score = np.std(cv_scores)
    print(f"  CV {target_name}: Mean={mean_score:.4f} ± Std={std_score:.4f}")

    return mean_score, std_score, cv_scores


# ── Optuna Objective Functions ────────────────────────────────────────────────
def objective_reg(trial, X, y, target_name):
    """Optuna objective for regression."""
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 200, 1000),
        'max_depth': trial.suggest_int('max_depth', 10, 30),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 10),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 5),
        'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', 0.3, 0.5]),
        'min_impurity_decrease': trial.suggest_float('min_impurity_decrease', 0.0, 0.01),
        'bootstrap': True,
        'random_state': 42,
        'n_jobs': -1,
    }

    mean_score, _, _ = run_cv_rf(X, y, target_name, params)
    return mean_score


def objective_clf(trial, X, y, target_name):
    """Optuna objective for classification."""
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 200, 1000),
        'max_depth': trial.suggest_int('max_depth', 10, 30),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 10),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 5),
        'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', 0.3, 0.5]),
        'class_weight': trial.suggest_categorical('class_weight', ['balanced', 'balanced_subsample', None]),
        'min_impurity_decrease': trial.suggest_float('min_impurity_decrease', 0.0, 0.01),
        'bootstrap': True,
        'random_state': 42,
        'n_jobs': -1,
    }

    mean_score, _, _ = run_cv_rf(X, y, target_name, params)
    return mean_score


def tune_hyperparameters(X, y, target_name, n_trials=50, timeout=3600):
    """Run Optuna hyperparameter optimization."""

    if target_name in CLASSIFICATION_TARGETS:
        study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
        study.optimize(lambda t: objective_clf(t, X, y, target_name),
                       n_trials=n_trials, timeout=timeout)
    else:
        study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
        study.optimize(lambda t: objective_reg(t, X, y, target_name),
                       n_trials=n_trials, timeout=timeout)

    print(f"  Best params: {study.best_params}")
    print(f"  Best score: {study.best_value:.4f}")

    return study.best_params


def train_final_model(X, y, target_name, params):
    """Train final model on full data."""
    is_classification = target_name in CLASSIFICATION_TARGETS

    if target_name in CLASSIFICATION_TARGETS:
        model = RandomForestClassifier(**params)
    else:
        model = RandomForestRegressor(**params)

    model.fit(X, y)
    return model


def evaluate_final_model(model, X_test, y_test, target_name):
    """Evaluate on hold-out test set."""
    is_classification = target_name in CLASSIFICATION_TARGETS

    if target_name in CLASSIFICATION_TARGETS:
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        return evaluate_classification(y_test, y_pred, y_proba, target_name)
    else:
        y_pred = model.predict(X_test)
        return evaluate_regression(y_test, y_pred, target_name)


def compute_permutation_importance(model, X, y, target_name, n_repeats=10):
    """Compute permutation importance."""
    result = permutation_importance(
        model, X, y, n_repeats=n_repeats, random_state=42, n_jobs=-1
    )
    importance_df = pd.DataFrame({
        'feature': X.columns,
        'importance_mean': result.importances_mean,
        'importance_std': result.importances_std
    }).sort_values('importance_mean', ascending=False)
    return importance_df


def save_model(model, target_name, model_type='rf'):
    """Save trained model."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / f"{target_name}_{model_type}.pkl"
    joblib.dump(model, model_path)
    print(f"  Saved model to {model_path}")


def save_results(results, target_name):
    """Save results to JSON."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    results_path = LOG_DIR / f"rf_{target_name}_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Results saved to {results_path}")


# ── Main Training Functions ───────────────────────────────────────────────────
def train_target(target_name, tune=False, n_trials=50, compare=False):
    """Train RF model for a single target."""
    print(f"\n{'='*70}")
    print(f"TRAINING: {target_name.upper()}")
    print(f"{'='*70}")

    # Load data
    df, X_df = load_data()
    y, target_col = prepare_targets(df, target_name)
    X = X_df[ALL_FEATURES].copy()

    # Handle categorical features
    X = pd.get_dummies(X, columns=CATEGORICAL_FEATURES, drop_first=True)
    print(f"Feature matrix: {X.shape}")

    # Hold-out test set (10%)
    from sklearn.model_selection import train_test_split
    stratify = None
    if target_name in CLASSIFICATION_TARGETS:
        stratify = y
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.1, random_state=42, stratify=stratify
    )
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # Hyperparameter tuning
    if tune:
        print(f"\n  🔧 Hyperparameter tuning (Optuna)...")
        best_params = tune_hyperparameters(
            X_train, y_train, target_name,
            n_trials=50, timeout=1800
        )
        if target_name not in CLASSIFICATION_TARGETS:
            base_params = RF_REG_DEFAULTS
        else:
            base_params = RF_CLF_DEFAULTS
        params = {**base_params, **best_params}
    else:
        params = RF_REG_DEFAULTS if target_name not in CLASSIFICATION_TARGETS else RF_CLF_DEFAULTS

    print(f"\n  📊 Cross-validation (5-fold)...")
    cv_mean, cv_std, cv_scores = run_cv_rf(X, y, target_name, params)

    # Train final model on full train data
    print(f"\n  🏋️ Training final model...")
    model = train_final_model(X_train, y_train, target_name, params)

    # Evaluate on test set
    print(f"\n  📊 Test set evaluation:")
    test_metrics = evaluate_final_model(model, X_test, y_test, target_name)

    # Permutation importance
    print(f"\n  🔍 Permutation importance...")
    imp_df = compute_permutation_importance(model, X_test, y_test, target_name)
    print(imp_df.head(15).to_string(index=False))

    # Save model
    save_model(model, target_name)

    # Prepare results
    results = {
        'target': target_name,
        'params': params,
        'cv_mean': float(np.mean(cv_scores)) if 'cv_scores' in locals() else None,
        'cv_std': float(np.std(cv_scores)) if 'cv_scores' in locals() else None,
        'cv_scores': [float(s) for s in cv_scores] if 'cv_scores' in locals() else [],
        'test_metrics': test_metrics,
        'feature_importance': imp_df.to_dict('records'),
    }

    save_results(results, target_name)

    return results


def train_all_targets(tune=False):
    """Train RF for all targets."""
    all_results = {}

    # Regression targets
    for target in REGRESSION_TARGETS:
        try:
            result = train_target(target, tune=tune)
            all_results[target] = result
        except Exception as e:
            print(f"Error training {target}: {e}")

    # Classification targets
    for target in CLASSIFICATION_TARGETS:
        try:
            result = train_target(target, tune=tune)
            all_results[target] = result
        except Exception as e:
            print(f"Error training {target}: {e}")

    # Summary
    print(f"\n{'='*70}")
    print("TRAINING COMPLETE - SUMMARY")
    print(f"{'='*70}")
    for target, result in all_results.items():
        if target in REGRESSION_TARGETS:
            print(f"  {target:10s}: CV R²={result.get('cv_mean', 0):.4f}±{result.get('cv_std', 0):.4f}, "
                  f"Test R²={result['test_metrics'].get('r2', 0):.4f}")
        else:
            print(f"  {target:10s}: CV AUC={result.get('cv_mean', 0):.4f}±{result.get('cv_std', 0):.4f}, "
                  f"Test AUC={result['test_metrics'].get('auc', 0):.4f}")

    return all_results


def compare_models():
    """Compare RF with existing LightGBM/MLP results."""
    print(f"\n{'='*70}")
    print("MODEL COMPARISON: RF vs LightGBM vs MLP vs Ensemble")
    print(f"{'='*70}")

    # Load existing results
    log_dir = LOG_DIR
    results_files = list(log_dir.glob("*_results.json"))

    comparison = {}
    for f in results_files:
        with open(f) as f:
            data = json.load(f)
            target = data.get('target', f.stem)
            comparison[target] = data

    print(f"{'Target':<15} {'RF':<10} {'LGB':<10} {'MLP':<10} {'Ensemble':<10}")
    print("-" * 55)
    for target in ['wns', 'tns', 'area', 'power', 'timing_closure', 'drc_clean']:
        # Would need actual comparison data
        pass


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Train Random Forest models for PPA prediction & timing closure"
    )
    parser.add_argument('--target', type=str, default='all',
                        choices=['all'] + list(ALL_TARGETS.keys()),
                        help='Target to train')
    parser.add_argument('--tune', action='store_true', help='Run hyperparameter tuning')
    parser.add_argument('--compare', action='store_true', help='Compare with existing models')
    parser.add_argument('--n-trials', type=int, default=50, help='Optuna trials')
    args = parser.parse_args()

    print("=" * 70)
    print("RANDOM FOREST TRAINING - OpenROAD Flow GUI")
    print("=" * 70)
    print(f"Target: {args.target}")
    print(f"Tuning: {args.tune}")
    print(f"Data: {DATA_PATH}")

    if args.compare:
        compare_models()
        return

    if args.target == 'all':
        train_all_targets(tune=args.tune)
    else:
        if args.target not in ALL_TARGETS:
            print(f"Unknown target: {args.target}")
            print(f"Available: {list(ALL_TARGETS.keys())}")
            sys.exit(1)
        train_target(args.target, tune=args.tune)

    print(f"\n✅ Training complete! Models saved to {MODEL_DIR}")


if __name__ == '__main__':
    main()