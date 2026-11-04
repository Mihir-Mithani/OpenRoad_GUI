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
    'core_aspect_ratio'
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
    """Create preprocessing pipeline"""
    return ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['platform', 'core_aspect_ratio']),
            ('num', StandardScaler(), [
                'core_utilization', 'core_margin', 'num_instances', 'num_nets',
                'num_sequential', 'num_macros', 'macro_area_ratio',
                'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
                'core_aspect_ratio'
            ])
        ],
        remainder='drop'
    )

def train_lightgbm(X_train, y_train, X_val, y_val, target_name):
    """Train LightGBM model (M1 compatible)"""
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
        'num_threads': 1,  # Single thread for M1 compatibility
        'force_col_wise': True,  # Force column-wise parallelism (M1 compatible)
        'verbose': -1
    }

    model = lgb.train(
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

    return model

def evaluate_model(model, X_test, y_test, target_name, model_type):
    """Evaluate model performance"""
    if model is None:
        print(f"  {model_type} model is None, skipping evaluation")
        return 0, None

    y_pred_proba = model.predict(X_test, num_iteration=model.best_iteration)

    y_pred = (y_pred_proba >= 0.5).astype(int)

    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n{target_name} ({model_type}) - AUC: {auc:.4f}")
    print(classification_report(y_test, y_pred))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title(f'{target_name} - {model_type} Confusion Matrix')
    plt.ylabel('True')
    plt.xlabel('Predicted')
    plt.savefig(LOG_DIR / f'cm_{target_name}_{model_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

    # ROC curve
    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    plt.figure(figsize=(5, 4))
    plt.plot(fpr, tpr, label=f'AUC = {auc:.3f}')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'{target_name} - {model_type} ROC Curve')
    plt.legend()
    plt.savefig(LOG_DIR / f'roc_{target_name}_{model_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

    return auc, y_pred_proba

def get_feature_importance(model, feature_names, model_type, target_name):
    """Extract and plot feature importance"""
    if model is None:
        return pd.DataFrame()

    importance = model.feature_importance(importance_type='gain', iteration=model.best_iteration)
    imp_df = pd.DataFrame({'feature': feature_names, 'importance': importance})

    imp_df = imp_df.sort_values('importance', ascending=False).head(20)

    plt.figure(figsize=(8, 6))
    sns.barplot(data=imp_df, x='importance', y='feature')
    plt.title(f'{target_name} - {model_type} Feature Importance (Top 20)')
    plt.tight_layout()
    plt.savefig(LOG_DIR / f'fi_{target_name}_{model_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

    return imp_df

def save_model(model, preprocessor, target_name, model_type):
    """Save model and preprocessor"""
    model_path = MODEL_DIR / f'{target_name}_{model_type}.pkl'
    preprocessor_path = MODEL_DIR / f'{target_name}_preprocessor.pkl'

    joblib.dump({'model': model, 'model_type': model_type}, model_path)
    joblib.dump(preprocessor, preprocessor_path)
    print(f"Saved {target_name} ({model_type}) to {model_path}")

def main():
    print("=" * 60)
    print("FAILURE PREDICTOR TRAINING (LightGBM)")
    print("=" * 60)

    # Load data
    X, y_timing, y_drc = load_data()
    print(f"Data shape: {X.shape}")
    print(f"Timing closure rate: {y_timing.mean():.3f}")
    print(f"DRC clean rate: {y_drc.mean():.3f}")

    # Preprocess
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

    # Train for each target
    for target_name, y_train, y_val, y_test in [
        ('timing_closure', y_timing_train_final, y_timing_val, y_timing_test),
        ('drc_clean', y_drc_train_final, y_drc_val, y_drc_test)
    ]:
        print(f"\n{'='*60}")
        print(f"TRAINING: {target_name}")
        print(f"{'='*60}")

        # Train LightGBM (primary and only model)
        print("\n--- LightGBM ---")
        lgb_model = train_lightgbm(X_train_final, y_train, X_val, y_val, target_name)
        lgb_auc, _ = evaluate_model(lgb_model, X_test, y_test, target_name, 'lgb')
        lgb_fi = get_feature_importance(lgb_model, feature_names, 'lgb', target_name)

        # Save model
        save_model(lgb_model, preprocessor, target_name, 'lgb')

        results[target_name] = {
            'best_model': 'lgb',
            'best_auc': lgb_auc,
        }

    # Save results summary
    with open(LOG_DIR / 'training_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    for target, res in results.items():
        print(f"{target}: Best=lgb, AUC={res['best_auc']:.4f}")

if __name__ == '__main__':
    main()