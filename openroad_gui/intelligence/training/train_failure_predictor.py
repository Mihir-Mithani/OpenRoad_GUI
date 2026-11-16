#!/usr/bin/env python3
"""
Failure Predictor Training Script
Binary classification for timing_closure and drc_clean
Uses LightGBM (M1 compatible)
"""

import argparse
import os
import json
import joblib
import numpy as np
import pandas as pd
import polars as pl
from pathlib import Path
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, roc_curve
from sklearn.inspection import permutation_importance
import lightgbm as lgb
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# M1/M2 LightGBM compatibility: disable OpenMP to avoid segfault
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['LIGHTGBM_NUM_THREADS'] = '1'
os.environ['OMP_WAIT_POLICY'] = 'PASSIVE'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['KMP_AFFINITY'] = 'disabled'

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "openroad_gui" / "intelligence" / "data"
MODEL_DIR = PROJECT_ROOT / "openroad_gui" / "intelligence" / "models" / "saved"
CHECKPOINT_DIR = PROJECT_ROOT / "openroad_gui" / "intelligence" / "training" / "checkpoints"
LOG_DIR = PROJECT_ROOT / "openroad_gui" / "intelligence" / "training" / "logs"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Feature columns (from dataset_specification.md)
CATEGORICAL_FEATURES = ['platform', 'core_aspect_ratio']
NUMERIC_FEATURES = [
    'core_utilization', 'core_margin', 'num_instances', 'num_nets',
    'num_sequential', 'num_macros', 'macro_area_ratio',
    'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
]
TARGETS = ['timing_closure_bin', 'drc_clean_bin']

# Columns to drop
DROP_COLS = [
    'run_id', 'design_name', 'timestamp', 'design_name_config', 'platform_config',
    'final_wns_ns', 'final_tns_ns', 'final_area_um2', 'final_power_mw',
    'final_drc_violations', 'total_runtime_sec', 'timing_closure', 'drc_clean', 'lvs_clean',
    'wns_normalized', 'tns_normalized', 'log_area', 'log_power',
    'timing_closure_bin', 'drc_clean_bin', 'lvs_clean_bin', 'platform_cat'
]

# CV settings
N_SPLITS = 5
RANDOM_STATE = 42
TEST_SIZE = 0.1

# Class weights for imbalanced targets
CLASS_WEIGHTS = {
    'timing_closure_bin': {0: 1.0, 1: 2.33},  # 30% positive -> weight = 0.7/0.3 ≈ 2.33
    'drc_clean_bin': {0: 5.67, 1: 1.0},  # 85% positive -> weight = 0.85/0.15 ≈ 5.67
}

def load_real_data(real_data_path: Path) -> pd.DataFrame:
    """Load and process real ORFS data from JSON (supports both formats)."""
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

        # Map comprehensive JSON columns to expected format
        column_mapping = {
            'final_power_w': 'final_power_mw',
            'final_drc_violations': 'final_drc_violations',
            'final_congestion_pct': 'final_congestion_pct',
            'final_setup_violations': 'final_setup_violations',
            'final_hold_violations': 'final_hold_violations',
            'final_drc_violations': 'final_drc_violations',
            'synth_wns_ns': 'synth_wns_ns',
            'synth_tns_ns': 'synth_tns_ns',
            'floorplan_wns_ns': 'floorplan_wns_ns',
            'floorplan_tns_ns': 'floorplan_tns_ns',
            'place_wns_ns': 'place_wns_ns',
            'place_tns_ns': 'place_tns_ns',
            'cts_wns_ns': 'cts_wns_ns',
            'cts_tns_ns': 'cts_tns_ns',
            'route_wns_ns': 'route_wns_ns',
            'route_tns_ns': 'route_tns_ns',
            'start_utc': 'start_utc',
            'end_utc': 'end_utc',
        }

        # Apply column mapping
        for old_col, new_col in column_mapping.items():
            if old_col in df_real.columns and new_col not in df_real.columns:
                df_real[new_col] = df_real[old_col]

        # Check for required columns (updated for comprehensive JSON)
        required_cols = ['design_name', 'platform', 'core_utilization', 'core_aspect_ratio',
                         'core_margin', 'num_instances', 'num_nets', 'num_sequential',
                         'num_macros', 'macro_area_ratio', 'final_wns_ns', 'final_tns_ns',
                         'final_area_um2', 'final_power_mw', 'final_drc_violations',
                         'final_congestion_pct', 'final_setup_violations', 'final_hold_violations',
                         'stage_runtimes', 'total_runtime_sec', 'timing_closure', 'drc_clean', 'lvs_clean']

        # Add missing columns with defaults where possible
        if 'num_instances' not in df_real.columns and 'num_instances' in df_real.columns:
            pass  # already exists
        elif 'num_instances' not in df_real.columns:
            # Try to estimate from final_area_um2
            if 'final_area_um2' in df_real.columns:
                df_real['num_instances'] = (df_real['final_area_um2'] / 100).astype(int)
            else:
                df_real['num_instances'] = 5000  # default

        if 'num_nets' not in df_real.columns:
            df_real['num_nets'] = df_real.get('num_instances', 5000) * 1.2

        if 'num_sequential' not in df_real.columns:
            df_real['num_sequential'] = df_real['num_instances'] * 0.2

        if 'num_macros' not in df_real.columns:
            df_real['num_macros'] = 0

        if 'macro_area_ratio' not in df_real.columns:
            df_real['macro_area_ratio'] = 0.0

        if 'final_power_mw' not in df_real.columns and 'final_power_w' in df_real.columns:
            df_real['final_power_mw'] = df_real['final_power_w'] * 1000

        if 'final_drc_violations' not in df_real.columns:
            df_real['final_drc_violations'] = 0

        if 'final_congestion_pct' not in df_real.columns:
            df_real['final_congestion_pct'] = 0

        if 'final_setup_violations' not in df_real.columns:
            df_real['final_setup_violations'] = 0

        if 'final_hold_violations' not in df_real.columns:
            df_real['final_hold_violations'] = 0

        if 'stage_runtimes' not in df_real.columns:
            df_real['stage_runtimes'] = '{}'

        if 'total_runtime_sec' not in df_real.columns:
            df_real['total_runtime_sec'] = 0

        if 'timing_closure' not in df_real.columns:
            df_real['timing_closure'] = df_real.get('final_wns_ns', 0) >= 0

        if 'drc_clean' not in df_real.columns:
            df_real['drc_clean'] = df_real.get('final_drc_violations', 1) == 0

        if 'lvs_clean' not in df_real.columns:
            df_real['lvs_clean'] = True

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


def create_preprocessor():
    """Create a fresh preprocessor (no fitting)."""
    return ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['platform', 'core_aspect_ratio']),
            ('num', StandardScaler(), [
                'core_utilization', 'core_margin', 'num_instances', 'num_nets',
                'num_sequential', 'num_macros', 'macro_area_ratio',
                'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
            ])
        ],
        remainder='drop'
    )


def run_cv_for_target(X, y, target_name, model_dir, log_dir):
    """Run stratified K-fold CV for a single classification target."""
    from sklearn.model_selection import StratifiedKFold

    # Stratify by platform + target
    platform = X['platform'].values if 'platform' in X.columns else np.zeros(len(X))
    stratify_key = platform.astype(str) + '_' + y.astype(str)

    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    cv_indices = list(cv.split(X, stratify_key))

    # Use last fold as hold-out test
    train_val_idx, test_idx = cv_indices[-1]
    cv_indices = cv_indices[:-1]

    print(f"  CV folds: {len(cv_indices)}, Hold-out test: {len(test_idx)} samples")

    cv_results = []
    class_weight = CLASS_WEIGHTS.get(target_name, {0: 1.0, 1: 1.0})

    for fold, (train_idx, val_idx) in enumerate(cv_indices):
        print(f"\n  --- Fold {fold + 1}/{len(cv_indices)} ---")

        X_train_df = X.iloc[train_idx]
        X_val_df = X.iloc[val_idx]
        y_train = y.iloc[train_idx]
        y_val = y.iloc[val_idx]

        # Fit preprocessor ONLY on training data
        preprocessor = create_preprocessor()
        X_train = preprocessor.fit_transform(X_train_df)
        X_val = preprocessor.transform(X_val_df)

        # ── LightGBM ────────────────────────────────────────────────────
        print("    LightGBM...")
        lgb_train = lgb.Dataset(X_train, label=y_train)
        lgb_val = lgb.Dataset(X_val, label=y_val, reference=lgb_train)

        params = {
            'objective': 'binary',
            'metric': 'auc',
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
            'is_unbalance': True,  # Handle class imbalance
        }

        lgb_model = lgb.train(
            params,
            lgb_train,
            num_boost_round=500,
            valid_sets=[lgb_train, lgb_val],
            valid_names=['train', 'val'],
            callbacks=[
                lgb.early_stopping(30),
                lgb.log_evaluation(0),
            ]
        )

        y_pred_proba = lgb_model.predict(X_val, num_iteration=lgb_model.best_iteration)
        auc = roc_auc_score(y_val, y_pred_proba)
        y_pred = (y_pred_proba >= 0.5).astype(int)

        print(f"      AUC: {auc:.4f}")
        print(classification_report(y_val, y_pred))

        cv_results.append({
            'auc': auc,
            'y_val': y_val,
            'y_pred_proba': y_pred_proba,
        })

    # ── Train final model on full train+val ────────────────────────────
    print(f"\n  --- Training final model on {len(train_val_idx)} samples ---")
    X_trainval_df = X.iloc[train_val_idx]
    y_trainval = y.iloc[train_val_idx]
    X_test_df = X.iloc[test_idx]
    y_test = y.iloc[test_idx]

    final_preprocessor = create_preprocessor()
    X_trainval = final_preprocessor.fit_transform(X_trainval_df)
    X_test = final_preprocessor.transform(X_test_df)

    lgb_train_full = lgb.Dataset(X_trainval, label=y_trainval)
    lgb_val_full = lgb.Dataset(X_test, label=y_test, reference=lgb_train_full)

    lgb_model_final = lgb.train(
        params,
        lgb_train_full,
        num_boost_round=500,
        valid_sets=[lgb_train_full, lgb_val_full],
        valid_names=['train', 'val'],
        callbacks=[
            lgb.early_stopping(50),
            lgb.log_evaluation(50),
        ]
    )

    # ── Calibrate probabilities ────────────────────────────────────────
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.isotonic import IsotonicRegression

    # Simple isotonic calibration on validation predictions
    y_val_pred = lgb_model_final.predict(X_val, num_iteration=lgb_model_final.best_iteration)
    iso_reg = IsotonicRegression(out_of_bounds='clip')
    iso_reg.fit(y_val_pred, y_val)

    # Apply calibration to test predictions
    y_test_pred = lgb_model_final.predict(X_test, num_iteration=lgb_model_final.best_iteration)
    y_pred_proba_cal = iso_reg.predict(y_test_pred)
    auc_cal = roc_auc_score(y_test, y_pred_proba_cal)

    # Find optimal threshold via Youden's J
    fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba_cal)
    youden_j = tpr - fpr
    optimal_idx = np.argmax(youden_j)
    optimal_threshold = thresholds[optimal_idx]
    print(f"  Optimal threshold (Youden's J): {optimal_threshold:.4f}")

    y_pred_cal = (y_pred_proba_cal >= optimal_threshold).astype(int)
    print(f"\n  Final Test AUC (calibrated): {auc_cal:.4f}")
    print(classification_report(y_test, y_pred_cal))

    # Save calibration model
    calibration_path = model_dir / f'{target_name}_calibration.pkl'
    joblib.dump({
        'method': 'isotonic',
        'iso_reg': iso_reg,
        'threshold': float(optimal_threshold),
    }, calibration_path)

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred_cal)
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title(f'{target_name} - Final Calibrated Confusion Matrix')
    plt.ylabel('True')
    plt.xlabel('Predicted')
    plt.savefig(log_dir / f'cm_{target_name}_final.png', dpi=150, bbox_inches='tight')
    plt.close()

    # ROC curve
    plt.figure(figsize=(5, 4))
    plt.plot(fpr, tpr, label=f'AUC = {auc_cal:.3f}')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'{target_name} - Final ROC Curve')
    plt.legend()
    plt.savefig(log_dir / f'roc_{target_name}_final.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Feature importance
    feature_names = (['core_utilization', 'core_margin', 'num_instances', 'num_nets',
                      'num_sequential', 'num_macros', 'macro_area_ratio',
                      'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio'] +
                     list(final_preprocessor.named_transformers_['cat'].get_feature_names_out(['platform', 'core_aspect_ratio'])))
    importance = lgb_model_final.feature_importance(importance_type='gain', iteration=lgb_model_final.best_iteration)
    imp_df = pd.DataFrame({'feature': feature_names, 'importance': importance})
    imp_df = imp_df.sort_values('importance', ascending=False).head(20)

    plt.figure(figsize=(8, 6))
    sns.barplot(data=imp_df, x='importance', y='feature')
    plt.title(f'{target_name} - Feature Importance (Top 20)')
    plt.tight_layout()
    plt.savefig(log_dir / f'fi_{target_name}_final.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Save final model + preprocessor + calibration info
    model_path = model_dir / f'{target_name}_lgb.pkl'
    preprocessor_path = model_dir / f'{target_name}_preprocessor.pkl'
    calibration_path = model_dir / f'{target_name}_calibration.pkl'

    joblib.dump({
        'model': lgb_model_final,
        'model_type': 'lgb',
        'optimal_threshold': float(optimal_threshold),
        'calibrated': True,
    }, model_path)
    joblib.dump(final_preprocessor, preprocessor_path)
    joblib.dump({
        'method': 'isotonic',
        'threshold': float(optimal_threshold),
    }, calibration_path)
    print(f"Saved {target_name} to {model_path}")

    # Aggregate CV results
    mean_auc = np.mean([r['auc'] for r in cv_results])
    std_auc = np.std([r['auc'] for r in cv_results])
    print(f"\n  {'='*50}")
    print(f"  CV RESULTS SUMMARY ({target_name})")
    print(f"  {'='*50}")
    print(f"    CV AUC: {mean_auc:.4f} ± {std_auc:.4f}")
    print(f"    Final Test AUC (calibrated): {auc_cal:.4f}")

    return {
        'cv_auc_mean': mean_auc,
        'cv_auc_std': std_auc,
        'test_auc': auc_cal,
        'optimal_threshold': optimal_threshold,
    }


def main():
    parser = argparse.ArgumentParser(description="Train failure predictor (LightGBM)")
    parser.add_argument('--real-data', type=Path, default=None,
                        help='Path to real ORFS runs JSON')
    parser.add_argument('--no-cv', action='store_true', help='Disable cross-validation (single split)')
    args = parser.parse_args()

    # Default to real data path
    if args.real_data is None:
        args.real_data = PROJECT_ROOT / "openroad_gui" / "intelligence" / "data" / "real_runs.json"

    print("=" * 60)
    print("FAILURE PREDICTOR TRAINING (LightGBM)")
    print("=" * 60)
    print(f"Cross-validation: True (5-fold stratified)")
    print("=" * 60)

    # Load real data
    df_real = load_real_data(args.real_data)

    if len(df_real) == 0:
        raise FileNotFoundError("No real training data available!")

    df = df_real.copy()
    print(f"Loaded {len(df_real)} real ORFS runs")

    # Ensure required features exist
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna('unknown')
    for col in NUMERIC_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    # Ensure binary targets exist
    if 'timing_closure_bin' not in df.columns:
        df['timing_closure_bin'] = (df.get('final_wns_ns', 0) >= 0).astype(int)
    if 'drc_clean_bin' not in df.columns:
        df['drc_clean_bin'] = (df.get('final_drc_violations', 1) == 0).astype(int)

    # Split features and targets
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns], errors='ignore')
    y_timing = df['timing_closure_bin']
    y_drc = df['drc_clean_bin']

    print(f"Data shape: {X.shape}")
    print(f"Timing closure rate: {y_timing.mean():.3f}")
    print(f"DRC clean rate: {y_drc.mean():.3f}")

    model_dir = MODEL_DIR
    log_dir = LOG_DIR

    # Train for each target
    for target_name, y in [('timing_closure', y_timing), ('drc_clean', y_drc)]:
        print(f"\n{'='*60}")
        print(f"TRAINING: {target_name}")
        print(f"{'='*60}")

        result = run_cv_for_target(X, y, target_name, MODEL_DIR, LOG_DIR)
        print(f"  Result: CV AUC={result['cv_auc_mean']:.4f}±{result['cv_auc_std']:.4f}, Test AUC={result['test_auc']:.4f}")


def main():
    parser = argparse.ArgumentParser(description="Train failure predictor (LightGBM)")
    parser.add_argument('--real-data', type=Path, default=None,
                        help='Path to real ORFS runs JSON')
    parser.add_argument('--no-cv', action='store_true', help='Disable cross-validation (single split)')
    args = parser.parse_args()

    # Default to real data path
    if args.real_data is None:
        args.real_data = PROJECT_ROOT / "openroad_gui" / "intelligence" / "data" / "real_runs.json"

    print("=" * 60)
    print("FAILURE PREDICTOR TRAINING (LightGBM)")
    print("=" * 60)
    print(f"Cross-validation: True (5-fold stratified)")
    print("=" * 60)

    # Load real data
    df_real = load_real_data(args.real_data)

    if len(df_real) == 0:
        raise FileNotFoundError("No real training data available!")

    df = df_real.copy()
    print(f"Loaded {len(df_real)} real ORFS runs")

    # Ensure required features exist
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna('unknown')
    for col in NUMERIC_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    # Ensure binary targets exist
    if 'timing_closure_bin' not in df.columns:
        df['timing_closure_bin'] = (df.get('final_wns_ns', 0) >= 0).astype(int)
    if 'drc_clean_bin' not in df.columns:
        df['drc_clean_bin'] = (df.get('final_drc_violations', 1) == 0).astype(int)

    # Split features and targets
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns], errors='ignore')
    y_timing = df['timing_closure_bin']
    y_drc = df['drc_clean_bin']

    print(f"Data shape: {X.shape}")
    print(f"Timing closure rate: {y_timing.mean():.3f}")
    print(f"DRC clean rate: {y_drc.mean():.3f}")

    model_dir = MODEL_DIR
    log_dir = LOG_DIR

    # Train for each target
    for target_name, y in [('timing_closure', y_timing), ('drc_clean', y_drc)]:
        print(f"\n{'='*60}")
        print(f"TRAINING: {target_name}")
        print(f"{'='*60}")

        result = run_cv_for_target(X, y, target_name, MODEL_DIR, LOG_DIR)
        print(f"  Result: CV AUC={result['cv_auc_mean']:.4f}±{result['cv_auc_std']:.4f}, Test AUC={result['test_auc']:.4f}")


if __name__ == '__main__':
    main()