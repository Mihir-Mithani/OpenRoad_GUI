#!/usr/bin/env python3
"""
Surrogate Models Training Script
Regression models for WNS, TNS, Area, Power prediction
Uses XGBoost (M1 compatible with single thread)
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import polars as pl
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.inspection import permutation_importance
import lightgbm as lgb
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# M1/M2 XGBoost compatibility: use single thread
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['XGB_NUM_THREADS'] = '1'

# Try to import XGBoost, but make it optional for M1 compatibility
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except (ImportError, SegmentationError):
    XGB_AVAILABLE = False
    xgb = None
    print("XGBoost not available, using LightGBM only")

# Paths
DATA_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/dataset_genration/output")
MODEL_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved")
CHECKPOINT_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/training/checkpoints")
LOG_DIR = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/training/logs")

MODEL_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Feature columns
CATEGORICAL_FEATURES = ['platform', 'core_aspect_ratio']
NUMERIC_FEATURES = [
    'core_utilization', 'core_margin', 'num_instances', 'num_nets',
    'num_sequential', 'num_macros', 'macro_area_ratio',
    'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
]

# Regression targets
REGRESSION_TARGETS = [
    'final_wns_ns', 'final_tns_ns', 'final_area_um2', 'final_power_mw'
]

DROP_COLS = [
    'run_id', 'design_name', 'timestamp', 'design_name_config', 'platform_config',
    'final_wns_ns', 'final_tns_ns', 'final_area_um2', 'final_power_mw',
    'final_drc_violations', 'total_runtime_sec', 'timing_closure', 'drc_clean', 'lvs_clean',
    'wns_normalized', 'tns_normalized', 'log_area', 'log_power',
    'timing_closure_bin', 'drc_clean_bin', 'lvs_clean_bin', 'platform_cat',
    'total_runtime_sec', 'stage_runtimes', 'timing_closure', 'drc_clean', 'lvs_clean',
    'design_name_config', 'platform_config'
]

def load_data():
    df = pl.read_parquet("/Users/mihirmithani/Downloads/OpenRoad GUI/dataset_genration/output/training_data.parquet")
    df_pd = df.to_pandas()

    # Select features (exclude target and metadata columns)
    drop_cols = [c for c in [
        'run_id', 'design_name', 'timestamp', 'design_name_config', 'platform_config',
        'final_wns_ns', 'final_tns_ns', 'final_area_um2', 'final_power_mw',
        'final_drc_violations', 'total_runtime_sec', 'timing_closure', 'drc_clean', 'lvs_clean',
        'wns_normalized', 'tns_normalized', 'log_area', 'log_power',
        'timing_closure_bin', 'drc_clean_bin', 'lvs_clean_bin', 'platform_cat',
        'total_runtime_sec', 'stage_runtimes', 'timing_closure', 'drc_clean', 'lvs_clean',
        'design_name_config', 'platform_config'
    ] if c in df.columns]

    X = df_pd.drop(columns=[c for c in DROP_COLS if c in df_pd.columns], errors='ignore')

    y_targets = {
        'wns': df_pd['final_wns_ns'],
        'tns': df_pd['final_tns_ns'],
        'area': df_pd['final_area_um2'],
        'power': df_pd['final_power_mw']
    }

    return X, y_targets

def create_preprocessor():
    return ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['platform', 'core_aspect_ratio']),
            ('num', StandardScaler(), [
                'core_utilization', 'core_margin', 'num_instances', 'num_nets',
                'num_sequential', 'num_macros', 'macro_area_ratio',
                'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio'
            ])
        ],
        remainder='drop'
    )

def train_xgboost(X_train, y_train, X_val, y_val):
    if not XGB_AVAILABLE:
        return None

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)

    params = {
        'objective': 'reg:squarederror',
        'eval_metric': 'rmse',
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 3,
        'gamma': 0.1,
        'reg_alpha': 0.1,
        'reg_lambda': 1.0,
        'seed': 42,
        'nthread': 1
    }

    evals = [(dtrain, 'train'), (dval, 'val')]
    model = xgb.train(
        params, dtrain,
        num_boost_round=500,
        evals=evals,
        early_stopping_rounds=50,
        verbose_eval=50
    )
    return model

def train_lightgbm(X_train, y_train, X_val, y_val):
    lgb_train = lgb.Dataset(X_train, label=y_train)
    lgb_val = lgb.Dataset(X_val, label=y_val, reference=lgb_train)

    params = {
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
        'force_col_wise': True
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

def evaluate_regression(model, X_test, y_test, target_name, model_type):
    if model is None:
        return None

    if isinstance(model, xgb.Booster) if XGB_AVAILABLE else False:
        y_pred = model.predict(xgb.DMatrix(X_test))
    else:
        y_pred = model.predict(X_test, num_iteration=model.best_iteration)

    mse = np.mean((y_test - y_pred) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(y_test - y_pred))
    r2 = 1 - np.sum((y_test - y_pred) ** 2) / np.sum((y_test - np.mean(y_test)) ** 2)
    mape = np.mean(np.abs((y_test - y_pred) / np.maximum(np.abs(y_test), 1e-8))) * 100

    print(f"  RMSE: {rmse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}, MAPE: {mape:.2f}%")

    # Residual plot
    plt.figure(figsize=(5, 4))
    plt.scatter(y_test, y_test - y_pred, alpha=0.5, s=10)
    plt.axhline(y=0, color='r', linestyle='--')
    plt.xlabel('Actual')
    plt.ylabel('Residual')
    plt.title(f'{target_name} - Residuals')
    plt.tight_layout()
    plt.savefig(LOG_DIR / f'residuals_{target_name}_{model_type}.png', dpi=150, bbox_inches='tight')
    plt.close()

    return {'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape}

def main():
    print("=" * 60)
    print("SURROGATE MODELS TRAINING (Regression)")
    print("=" * 60)

    # Load data
    df = pl.read_parquet("/Users/mihirmithani/Downloads/OpenRoad GUI/dataset_genration/output/training_data.parquet")
    df_pd = df.to_pandas()

    # Drop target and metadata columns
    drop_cols = [c for c in DROP_COLS if c in df_pd.columns]
    X = df_pd.drop(columns=drop_cols, errors='ignore')

    y_targets = {
        'wns': df_pd['final_wns_ns'],
        'tns': df_pd['final_tns_ns'],
        'area': df_pd['final_area_um2'],
        'power': df_pd['final_power_mw']
    }

    print(f"Data shape: {df_pd.shape}")
    print(f"Features: {X.shape[1]}")

    # Preprocess
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['platform', 'core_aspect_ratio']),
            ('num', StandardScaler(), [
                'core_utilization', 'core_margin', 'num_instances', 'num_nets',
                'num_sequential', 'num_macros', 'macro_area_ratio',
                'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio'
            ])
        ],
        remainder='drop'
    )

    # Fit preprocessor on all data
    X_processed = preprocessor.fit_transform(df_pd)

    # Train/test split (same split for all targets)
    indices = np.arange(len(df_pd))
    train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42)

    X_train = X_processed[train_idx]
    X_test = X_processed[test_idx]

    print(f"Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")

    results = {}

    target_names = ['final_wns_ns', 'final_tns_ns', 'final_area_um2', 'final_power_mw']
    short_names = ['wns', 'tns', 'area', 'power']

    for target_name, short_name in zip(target_names, short_names):
        print(f"\n{'='*60}")
        print(f"TRAINING: {target_name}")
        print(f"{'='*60}")

        y_train = df_pd[target_name].iloc[train_idx].values
        y_test = df_pd[target_name].iloc[test_idx].values

        results[short_name] = {}

        # Train XGBoost
        if XGB_AVAILABLE:
            print("\n--- XGBoost ---")
            dtrain = xgb.DMatrix(X_train, label=y_train)
            dval = xgb.DMatrix(X_test, label=y_test)

            params = {
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse',
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'min_child_weight': 3,
                'gamma': 0.1,
                'reg_alpha': 0.1,
                'reg_lambda': 1.0,
                'seed': 42,
                'nthread': 1
            }

            model = xgb.train(
                params, dtrain,
                num_boost_round=500,
                evals=[(dtrain, 'train'), (dval, 'val')],
                early_stopping_rounds=50,
                verbose_eval=50
            )

            # Evaluate
            dtest = xgb.DMatrix(X_test)
            y_pred = model.predict(dtest)
            mse = np.mean((y_test - y_pred) ** 2)
            rmse = np.sqrt(mse)
            mae = np.mean(np.abs(y_test - y_pred))
            r2 = 1 - np.sum((y_test - y_pred) ** 2) / np.sum((y_test - np.mean(y_test)) ** 2)

            print(f"  RMSE: {rmse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")

            # Save model
            joblib.dump({'model': model, 'target': target_name},
                       f'/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_{short_name}.pkl')
            results[short_name]['xgb'] = {'rmse': rmse, 'mae': mae, 'r2': r2}

        # LightGBM
        print("\n--- LightGBM ---")
        lgb_train = lgb.Dataset(X_train, label=y_train)
        lgb_val = lgb.Dataset(X_test, label=y_test, reference=lgb_train)

        params = {
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
            'force_col_wise': True
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

        # Evaluate
        y_pred = model.predict(X_test, num_iteration=model.best_iteration)
        mse = np.mean((y_test - y_pred) ** 2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(y_test - y_pred))
        r2 = 1 - np.sum((y_test - y_pred) ** 2) / np.sum((y_test - np.mean(y_test)) ** 2)

        print(f"  RMSE: {rmse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")

        # Save model
        joblib.dump({'model': model, 'target': target_name},
                   f'/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved/surrogate_{short_name}.pkl')
        results[short_name]['lgb'] = {'rmse': rmse, 'mae': mae, 'r2': r2}

    # Save results
    with open(f'/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/training/logs/surrogate_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print("SURROGATE TRAINING COMPLETE")
    print("=" * 60)
    for target, res in results.items():
        if 'xgb' in res:
            print(f"  {target}: XGB R²={res['xgb']['r2']:.4f}, LGB R²={res['lgb']['r2']:.4f}")
        else:
            print(f"  {target}: LGB R²={res['lgb']['r2']:.4f}")

if __name__ == '__main__':
    main()