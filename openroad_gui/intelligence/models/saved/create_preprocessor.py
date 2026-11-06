#!/usr/bin/env python3
"""
Create surrogate preprocessor for Colab RL training.
This matches the exact schema used in train_surrogate.py
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from pathlib import Path

# Feature definitions matching train_surrogate.py
CATEGORICAL_FEATURES = ['platform', 'core_aspect_ratio']
NUMERIC_FEATURES = [
    'core_utilization', 'core_margin',
    'num_instances', 'num_nets', 'num_sequential', 'num_macros', 'macro_area_ratio',
    'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
]

# Explicit categories from actual training data
PLATFORM_CATEGORIES = ['asap7', 'gf180', 'nangate45', 'sky130hd']
ASPECT_RATIO_CATEGORIES = [1.0]  # Only 1.0 in training data


def create_preprocessor():
    """Create and fit the ColumnTransformer preprocessor for inference."""

    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(
                handle_unknown='ignore',
                sparse_output=False,
                categories=[PLATFORM_CATEGORIES, ASPECT_RATIO_CATEGORIES]
            ), CATEGORICAL_FEATURES),
            ('num', StandardScaler(), NUMERIC_FEATURES),
        ],
        remainder='drop'
    )

    # Fit on a single sample with correct dtypes to establish feature_names_in_
    fit_df = pd.DataFrame([{
        'platform': 'sky130hd',
        'core_aspect_ratio': 1.0,
        'core_utilization': 30.0,
        'core_margin': 5.0,
        'num_instances': 5000,
        'num_nets': 6000,
        'num_sequential': 1000,
        'num_macros': 2,
        'macro_area_ratio': 0.05,
        'log_instances': np.log1p(5000)/20,
        'log_nets': np.log1p(6000)/20,
        'seq_ratio': 0.2,
        'macro_ratio': 0.0004,
    }])
    preprocessor.fit(fit_df)

    return preprocessor


if __name__ == "__main__":
    print("Creating surrogate preprocessor...")
    preprocessor = create_preprocessor()

    # Save
    output_path = Path(__file__).parent / "surrogate_preprocessor.pkl"
    joblib.dump(preprocessor, output_path)
    print(f"Preprocessor saved to {output_path}")

    # Verify
    print(f"Feature names in: {preprocessor.feature_names_in_}")
    print(f"Transformers: {preprocessor.transformers_}")

    # Test transform
    test_df = pd.DataFrame([{
        'platform': 'sky130hd',
        'core_aspect_ratio': 1.0,
        'core_utilization': 30.0,
        'core_margin': 5.0,
        'num_instances': 5000,
        'num_nets': 6000,
        'num_sequential': 1000,
        'num_macros': 2,
        'macro_area_ratio': 0.05,
        'log_instances': np.log1p(5000)/20,
        'log_nets': np.log1p(6000)/20,
        'seq_ratio': 0.2,
        'macro_ratio': 0.0004,
    }])

    X = preprocessor.transform(test_df)
    print(f"Transformed shape: {X.shape}")
    print(f"Feature names out: {preprocessor.get_feature_names_out()}")