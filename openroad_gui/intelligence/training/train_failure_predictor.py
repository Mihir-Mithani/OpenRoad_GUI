#!/usr/bin/env python3
"""
Failure Predictor Training Script
Binary classification for timing_closure and drc_clean
Uses LightGBM (M1 compatible)
"""

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

# Paths
DATA_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/dataset_genration/output")
MODEL_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved")
CHECKPOINT_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/training/checkpoints")
LOG_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/training/logs")

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

def load_data():
    """Load and prepare training data"""
    df = pl.read_parquet("/Users/mihirmithani/Downloads/OpenRoad GUI/dataset_genration/output/training_data.parquet")
    df_pd = df.to_pandas()

    # Split features and targets
    X = df_pd.drop(columns=[c for c in DROP_COLS if c in df_pd.columns], errors='ignore')
    y_timing = df_pd['timing_closure_bin']
    y_drc = df_pd['drc_clean_bin']

    return X, y_timing, y_drc

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
    parser.add_argument('--no-cv', action='store_true', help='Disable cross-validation (single split)')
    args = parser.parse_args()

    print("=" * 60)
    print("FAILURE PREDICTOR TRAINING (LightGBM)")
    print("=" * 60)
    print(f"Cross-validation: {not args.no_cv} ({N_SPLITS}-fold stratified)")
    print("=" * 60)

    # Load data
    df = pl.read_parquet("/Users/mihirmithani/Downloads/OpenRoad GUI/dataset_genration/output/training_data.parquet")
    df_pd = df.to_pandas()

    # Split features and targets
    X = df_pd.drop(columns=[c for c in DROP_COLS if c in df_pd.columns], errors='ignore')
    y_timing = df_pd['timing_closure_bin']
    y_drc = df_pd['drc_clean_bin']

    print(f"Data shape: {X.shape}")
    print(f"Timing closure rate: {y_timing.mean():.3f}")
    print(f"DRC clean rate: {y_drc.mean():.3f}")

    if args.no_cv:
        # Original single-split logic (for backward compatibility)
        preprocessor = create_preprocessor()
        X_processed = preprocessor.fit_transform(X)
        feature_names = (NUMERIC_FEATURES +
                         list(preprocessor.named_transformers_['cat'].get_feature_names_out(['platform', 'core_aspect_ratio'])))

        # Split data (stratified for timing)
        X_train, X_test, y_timing_train, y_timing_test = train_test_split(
            X_processed, y_timing, test_size=0.2, random_state=42, stratify=y_timing
        )
        _, _, y_drc_train, y_drc_test = train_test_split(
            X_processed, y_drc, test_size=0.2, random_state=42, stratify=y_drc
        )

        # Further split train into train/val
        X_train_final, X_val, y_timing_train_final, y_timing_val = train_test_split(
            X_train, y_timing_train, test_size=0.15, random_state=42, stratify=y_timing_train
        )
        _, _, y_drc_train_final, y_drc_val = train_test_split(
            X_train, y_drc_train, test_size=0.15, random_state=42, stratify=y_drc_train
        )

        print(f"\nTrain: {X_train_final.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")

        results = {}

        for target_name, y_train, y_val, y_test in [
            ('timing_closure', y_timing_train_final, y_timing_val, y_timing_test),
            ('drc_clean', y_drc_train_final, y_drc_val, y_drc_test)
        ]:
            print(f"\n{'='*60}")
            print(f"TRAINING: {target_name}")
            print(f"{'='*60}")

            print("\n--- LightGBM ---")
            lgb_train = lgb.Dataset(X_train_final, label=y_train)
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
                'is_unbalance': True,
            }

            lgb_model = lgb.train(
                params,
                lgb_train,
                num_boost_round=500,
                valid_sets=[lgb_train, lgb_val],
                valid_names=['train', 'val'],
                callbacks=[
                    lgb.early_stopping(50),
                    lgb.log_evaluation(50)
                ]
            )

            y_pred_proba = lgb_model.predict(X_test, num_iteration=lgb_model.best_iteration)
            y_pred = (y_pred_proba >= 0.5).astype(int)

            auc = roc_auc_score(y_test, y_pred_proba)
            print(f"\n{target_name} (lgb) - AUC: {auc:.4f}")
            print(classification_report(y_test, y_pred))

            # Save model
            model_path = MODEL_DIR / f'{target_name}_lgb.pkl'
            preprocessor_path = MODEL_DIR / f'{target_name}_preprocessor.pkl'
            joblib.dump({'model': lgb_model, 'model_type': 'lgb'}, model_path)
            joblib.dump(preprocessor, preprocessor_path)
            print(f"Saved {target_name} to {model_path}")

            results[target_name] = {
                'best_model': 'lgb',
                'best_auc': auc,
            }

    else:
        # New CV-based training
        results = {}
        for target_name, y in [('timing_closure', y_timing), ('drc_clean', y_drc)]:
            print(f"\n{'='*60}")
            print(f"TRAINING: {target_name}")
            print(f"{'='*60}")

            result = run_cv_for_target(X, y, target_name, MODEL_DIR, LOG_DIR)
            results[target_name] = result

    # Save results summary
    with open(LOG_DIR / 'training_results.json', 'w') as f:
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
        json.dump(convert(results), f, indent=2)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    for target, res in results.items():
        if 'cv_auc_mean' in res:
            print(f"{target}: CV AUC={res['cv_auc_mean']:.4f}±{res['cv_auc_std']:.4f}, Test AUC={res['test_auc']:.4f}, Threshold={res['optimal_threshold']:.4f}")
        else:
            print(f"{target}: Best=lgb, AUC={res['best_auc']:.4f}")


if __name__ == '__main__':
    import argparse
    main()