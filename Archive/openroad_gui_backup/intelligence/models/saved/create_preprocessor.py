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

def create_preprocessor():
    """Create and fit the ColumnTransformer preprocessor."""

    # Create sample data to fit the preprocessor
    # This matches the training data distribution
    np.random.seed(42)
    n_samples = 1000

    platforms = np.random.choice(['sky130hd', 'asap7', 'nangate45', 'gf180'], n_samples, p=[0.3, 0.3, 0.2, 0.2])
    aspect_ratios = np.random.choice([0.5, 0.67, 0.8, 1.0, 1.2, 1.33, 1.5, 1.67, 2.0, 2.5, 3.0], n_samples)

    # Generate realistic feature values
    data = {
        'platform': platforms,
        'core_aspect_ratio': aspect_ratios.astype(str),  # categorical as string
        'core_utilization': np.random.uniform(10, 80, n_samples),
        'core_margin': np.random.uniform(1, 10, n_samples),
        'num_instances': np.random.lognormal(8, 1.5, n_samples).astype(int),
        'num_nets': np.random.lognormal(8.5, 1.3, n_samples).astype(int),
        'num_sequential': np.random.lognormal(7, 1.2, n_samples).astype(int),
        'num_macros': np.random.poisson(2, n_samples),
        'macro_area_ratio': np.random.uniform(0, 0.5, n_samples),
        'log_instances': np.log1p(np.random.lognormal(8, 1.5, n_samples)) / 20,
        'log_nets': np.log1p(np.random.lognormal(8.5, 1.3, n_samples)) / 20,
        'seq_ratio': np.random.beta(2, 8, n_samples),
        'macro_ratio': np.random.beta(1, 50, n_samples),
    }

    df = pd.DataFrame(data)

    # Create preprocessor matching train_surrogate.py
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL_FEATURES),
            ('num', StandardScaler(), NUMERIC_FEATURES),
        ],
        remainder='drop'
    )

    # Fit on sample data
    preprocessor.fit(df)

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
        'core_aspect_ratio': '1.0',
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