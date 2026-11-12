#!/usr/bin/env python3
"""
Random Forest Models for PPA Prediction & Timing Closure Classification
Production-ready inference module for OpenROAD Flow GUI integration.

Usage:
    from openroad_gui.intelligence.models.random_forest import RandomForestPPA, RandomForestFailurePredictor

    # Regression (PPA)
    ppa_model = RandomForestPPA()
    ppa_model.load_model("wns")
    prediction = ppa_model.predict(features_dict)

    # Classification (Failure Prediction)
    failure_model = RandomForestFailurePredictor()
    failure_model.load_model("timing_closure")
    risk = failure_model.predict_proba(features_dict)
"""

from __future__ import annotations

import joblib
import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


# ── Configuration ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MODEL_DIR = Path(__file__).parent / "saved"

# Feature configuration (must match training)
CATEGORICAL_FEATURES = ['platform', 'core_aspect_ratio']
NUMERIC_FEATURES = [
    'core_utilization', 'core_margin',
    'num_instances', 'num_nets', 'num_sequential', 'num_macros', 'macro_area_ratio',
    'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
]

ALL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

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

# Expected model files
MODEL_FILES = {
    'wns': 'wns_rf.pkl',
    'tns': 'tns_rf.pkl',
    'area': 'area_rf.pkl',
    'power': 'power_rf.pkl',
    'timing_closure': 'timing_closure_rf.pkl',
    'drc_clean': 'drc_clean_rf.pkl',
}


# ── Preprocessing ────────────────────────────────────────────────────────────

def _prepare_features(features: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert input feature dict to DataFrame matching training format.

    Args:
        features: Dict with keys matching ALL_FEATURES

    Returns:
        DataFrame with one row, columns matching training features
    """
    # Start with all features as NaN
    row = {feat: np.nan for feat in ['platform', 'core_aspect_ratio'] + NUMERIC_FEATURES}

    # Fill provided features
    for key, value in features.items():
        if key in row:
            row[key] = value

    df = pd.DataFrame([row])

    # Handle categorical features
    if 'platform' in df.columns:
        df['platform'] = df['platform'].astype('category')
    if 'core_aspect_ratio' in df.columns:
        df['core_aspect_ratio'] = df['core_aspect_ratio'].astype('category')

    # One-hot encode categorical (matches training)
    df = pd.get_dummies(df, columns=['platform', 'core_aspect_ratio'], drop_first=True)

    return df


def _validate_features(features: Dict[str, Any]) -> List[str]:
    """Validate input features, return list of missing required features."""
    required = set(NUMERIC_FEATURES) | {'platform', 'core_aspect_ratio'}
    provided = set(features.keys())
    missing = required - set(features.keys())
    return list(missing)


# ── Base Model Class ─────────────────────────────────────────────────────────

class _RandomForestBase:
    """Base class for RF models with common loading/prediction logic."""

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = Path(model_dir) if model_dir else Path(__file__).parent / "saved"
        self.model = None
        self.feature_names: Optional[List[str]] = None
        self.is_loaded = False
        self.target_name: Optional[str] = None
        self.is_classifier = False

    def load_model(self, target_name: str) -> bool:
        """
        Load pre-trained model from disk.

        Args:
            target_name: One of ['wns', 'tns', 'area', 'power', 'timing_closure', 'drc_clean']

        Returns:
            True if loaded successfully, False otherwise
        """
        if target_name not in ['wns', 'tns', 'area', 'power', 'timing_closure', 'drc_clean']:
            raise ValueError(f"Unknown target: {target_name}")

        model_filename = {
            'wns': 'wns_rf.pkl',
            'tns': 'tns_rf.pkl',
            'area': 'area_rf.pkl',
            'power': 'power_rf.pkl',
            'timing_closure': 'timing_closure_rf.pkl',
            'drc_clean': 'drc_clean_rf.pkl',
        }[target_name]

        model_path = self.model_dir / model_filename
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        try:
            model_data = joblib.load(model_path)

            # Handle both direct model and dict-wrapped model
            if isinstance(model_data, dict):
                self.model = model_data.get('model', model_data)
            else:
                self.model = model_data

            self.target_name = target_name
            self.is_classifier = target_name in ['timing_closure', 'drc_clean']
            self.is_loaded = True

            # Try to extract feature names from model
            if hasattr(self.model, 'feature_names_in_'):
                self.feature_names = list(self.model.feature_names_in_)
            elif hasattr(self.model, 'feature_importances_'):
                # Feature names not stored, will be inferred at prediction time
                pass

            print(f"✅ Loaded {target_name} model from {model_path}")
            return True

        except Exception as e:
            print(f"❌ Failed to load model {target_name}: {e}")
            self.is_loaded = False
            return False

    def is_model_loaded(self) -> bool:
        return self.is_loaded and self.model is not None

    def _validate_loaded(self):
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

    def _prepare_input(self, features: Dict[str, Any]) -> np.ndarray:
        """Convert feature dict to model-ready array."""
        missing = _validate_features(features)
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        df = _prepare_features(features)

        # Ensure columns match model expectation
        if self.feature_names is not None:
            # Add missing columns as 0
            for col in self.feature_names:
                if col not in df.columns:
                    df[col] = 0
            # Reorder columns
            df = df[self.feature_names]

        return df.values


# ── Regression (PPA Prediction) ──────────────────────────────────────────────

class RandomForestPPA:
    """
    Random Forest surrogate models for PPA prediction (WNS, TNS, Area, Power).

    Usage:
        ppa = RandomForestPPA()
        ppa.load_model("wns")  # or "tns", "area", "power"
        prediction = ppa.predict({
            'platform': 'asap7',
            'core_utilization': 30.0,
            'core_aspect_ratio': 1.0,
            'core_margin': 5.0,
            'num_instances': 5000,
            'num_nets': 6000,
            'num_sequential': 1000,
            'num_macros': 2,
            'macro_area_ratio': 0.05,
            'log_instances': 8.5,
            'log_nets': 8.7,
            'seq_ratio': 0.2,
            'macro_ratio': 0.0004,
        })
        # Returns: {'wns': -0.5} (in ns)
    """

    def __init__(self, model_dir: Optional[Path] = None):
        self.models: Dict[str, Any] = {}
        self.model_dir = Path(model_dir) if model_dir else Path(__file__).parent / "saved"
        self.loaded_targets: set = set()
        # Feature names expected by the models (from training)
        self.feature_names = [
            'core_utilization', 'core_margin', 'num_instances', 'num_nets',
            'num_sequential', 'num_macros', 'macro_area_ratio',
            'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
            'platform_gf180', 'platform_nangate45', 'platform_sky130hd'
        ]

    def _prepare_features(self, features: Dict[str, Any]) -> np.ndarray:
        """Convert feature dict to model-ready array."""
        # Validate required features
        required = {'core_utilization', 'core_margin', 'num_instances', 'num_nets',
                      'num_sequential', 'num_macros', 'macro_area_ratio',
                      'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
                      'platform_gf180', 'platform_nangate45', 'platform_sky130hd'}
        missing = [f for f in self.feature_names if f not in features]
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        # Create DataFrame with correct column order
        df = pd.DataFrame([features])
        df = df[self.feature_names]
        return df.values

    def load_model(self, target: str) -> bool:
        """
        Load model for a specific PPA target.

        Args:
            target: One of 'wns', 'tns', 'area', 'power'
        """
        if target not in ['wns', 'tns', 'area', 'power']:
            raise ValueError(f"Unknown PPA target: {target}. Must be one of: wns, tns, area, power")

        if target in self.models:
            return True  # Already loaded

        model_filename = {
            'wns': 'wns_rf.pkl',
            'tns': 'tns_rf.pkl',
            'area': 'area_rf.pkl',
            'power': 'power_rf.pkl',
        }[target]

        model_path = Path(__file__).parent / "saved" / model_filename
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        try:
            model_data = joblib.load(model_path)
            # Handle both dict-wrapped and direct model
            if isinstance(model_data, dict):
                model = model_data.get('model', model_data)
            else:
                model = model_data

            self.models[target] = model
            print(f"✅ Loaded {target} model")
            return True
        except Exception as e:
            print(f"❌ Failed to load {target}: {e}")
            return False

    def load_all(self) -> Dict[str, bool]:
        """Load all four PPA models."""
        results = {}
        for target in ['wns', 'tns', 'area', 'power']:
            try:
                self.load_model(target)
                results[target] = True
            except Exception as e:
                print(f"❌ Failed to load {target}: {e}")
                results[target] = False
        return results

    def predict(self, features: Dict[str, Any], targets: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Predict PPA metrics for given features.

        Args:
            features: Dict with keys matching feature names
            targets: List of targets to predict (default: all loaded)

        Returns:
            Dict mapping target names to predicted values
        """
        if not self.models:
            raise RuntimeError("No models loaded. Call load_model() or load_all() first.")

        targets = targets or list(self.models.keys())
        results = {}

        for target in targets:
            if target not in self.models:
                raise ValueError(f"Model for {target} not loaded. Call load_model('{target}') first.")

            model = self.models[target]

            # Prepare features for the model (use _prepare_features, not _prepare_input)
            X = self._prepare_features(features)
            prediction = model.predict(X)
            results[target] = float(prediction[0])

        return results

    def predict_all(self, features: Dict[str, Any]) -> Dict[str, float]:
        """Predict all four PPA metrics at once."""
        return self.predict(features, targets=['wns', 'tns', 'area', 'power'])

    def get_feature_importance(self, target: str) -> Optional[pd.DataFrame]:
        """Get feature importance for a loaded model."""
        if target not in self.models:
            return None

        model = self.models[target]
        if not hasattr(model, 'feature_importances_'):
            return None

        # Would need feature names from training
        importances = model.feature_importances_
        # Return DataFrame with feature names and importance values
        return pd.DataFrame({
            'importance': importances
        }).sort_values('importance', ascending=False)


# ── Classification (Failure Prediction) ──────────────────────────────────────

class RandomForestFailurePredictor:
    """
    Random Forest classifiers for failure prediction (Timing Closure, DRC Clean).

    Usage:
        fp = RandomForestFailurePredictor()
        fp.load_model("timing_closure")  # or "drc_clean"
        risk = fp.predict_proba({
            'platform': 'asap7',
            'core_utilization': 30.0,
            ...
        })
        # Returns: {'probability': 0.85, 'risk_level': 'high', 'threshold': 0.208}
    """

    def __init__(self, model_dir: Optional[Path] = None):
        self.models: Dict[str, Any] = {}
        self.calibrators: Dict[str, Any] = {}  # Isotonic calibrators
        self.thresholds: Dict[str, float] = {}  # Optimal thresholds
        self.model_dir = Path(model_dir) if model_dir else Path(__file__).parent / "saved"

    def load_model(self, target: str) -> bool:
        """
        Load classifier and calibrator for target.

        Args:
            target: 'timing_closure' or 'drc_clean'
        """
        if target not in ['timing_closure', 'drc_clean']:
            raise ValueError(f"Unknown target: {target}. Must be 'timing_closure' or 'drc_clean'")

        if target in self.models:
            return True

        model_filename = f"{target}_rf.pkl"
        model_path = Path(__file__).parent / "saved" / model_filename
        calibrator_filename = f"{target}_calibration.pkl"
        calibrator_path = Path(__file__).parent / "saved" / calibrator_filename

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        try:
            # Load model
            model_data = joblib.load(model_path)
            if isinstance(model_data, dict):
                model = model_data.get('model', model_data)
            else:
                model = model_data

            self.models[target] = model

            # Load calibrator if exists
            if Path(calibrator_path).exists():
                calibrator_data = joblib.load(calibrator_path)
                self.calibrators[target] = calibrator_data

            # Default thresholds (from training)
            self.thresholds = {
                'timing_closure': 0.208,
                'drc_clean': 0.930,
            }

            print(f"✅ Loaded {target} failure predictor")
            return True

        except Exception as e:
            print(f"❌ Failed to load {target}: {e}")
            return False

    def _prepare_features(self, features: Dict[str, Any]) -> np.ndarray:
        """Convert feature dict to model-ready array (same as PPA models)."""
        # Feature names expected by the failure prediction models
        feature_names = [
            'core_utilization', 'core_margin', 'num_instances', 'num_nets',
            'num_sequential', 'num_macros', 'macro_area_ratio',
            'log_instances', 'log_nets', 'seq_ratio', 'macro_ratio',
            'platform_gf180', 'platform_nangate45', 'platform_sky130hd'
        ]

        missing = [f for f in feature_names if f not in features]
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        import pandas as pd
        df = pd.DataFrame([features])
        df = df[feature_names]
        return df.values

    def predict_proba(self, features: Dict[str, Any], target: str = "timing_closure") -> Dict[str, Any]:
        """
        Predict failure probability with calibration.

        Returns:
            Dict with keys: probability, risk_level, threshold, calibrated
        """
        if target not in self.models:
            raise ValueError(f"Model for {target} not loaded. Call load_model('{target}') first.")

        model = self.models[target]
        calibrator = self.calibrators.get(target)
        threshold = self.thresholds.get(target, 0.5)

        # Prepare features for the model
        X = self._prepare_features(features)
        raw_prob = float(model.predict_proba(X)[0, 1])

        # Apply calibration if available
        calibrated_prob = raw_prob
        if target in self.calibrators:
            calibrator = self.calibrators[target]
            # Apply isotonic calibration
            calibrated_prob = calibrator.predict([raw_prob])[0] if hasattr(calibrator, 'predict') else raw_prob

        risk_level = "high" if calibrated_prob > threshold else "low"

        return {
            'probability': float(calibrated_prob),
            'raw_probability': float(raw_prob),
            'risk_level': risk_level,
            'threshold': float(threshold),
            'calibrated': target in self.calibrators,
            'target': target
        }

    def predict(self, features: Dict[str, Any], target: str = "timing_closure") -> int:
        """Binary prediction (0 or 1)."""
        proba = self.predict_proba(features, target)
        return 1 if proba['probability'] > proba['threshold'] else 0


# ── Unified Interface ────────────────────────────────────────────────────────

class RandomForestIntelligence:
    """
    Unified interface for all RF models (PPA + Failure Prediction).

    Usage:
        rf = RandomForestIntelligence()
        rf.load_all()

        # PPA prediction
        ppa = rf.predict_ppa(features)
        # {'wns': -0.5, 'tns': -10.2, 'area': 123456, 'power': 45.3}

        # Failure prediction
        risk = rf.predict_failure_risk(features)
        # {'timing_closure': {...}, 'drc_clean': {...}}
    """

    def __init__(self, model_dir: Optional[Path] = None):
        self.ppa = RandomForestPPA(model_dir)
        self.failure = RandomForestFailurePredictor(model_dir)
        self.model_dir = Path(model_dir) if model_dir else Path(__file__).parent / "saved"

    def load_all(self) -> Dict[str, bool]:
        """Load all models (PPA + Failure)."""
        ppa_results = self.ppa.load_all()
        failure_results = {}
        for target in ['timing_closure', 'drc_clean']:
            try:
                self.failure.load_model(target)
                failure_results[target] = True
            except Exception as e:
                print(f"❌ Failed to load {target}: {e}")
                failure_results[target] = False

        return {**ppa_results, **failure_results}

    def predict_ppa(self, features: Dict[str, Any]) -> Dict[str, float]:
        """Predict all four PPA metrics."""
        return self.ppa.predict_all(features)

    def predict_failure_risk(self, features: Dict[str, Any]) -> Dict[str, Dict]:
        """Predict failure risk for timing closure and DRC."""
        return {
            'timing_closure': self.failure.predict_proba(features, 'timing_closure'),
            'drc_clean': self.failure.predict_proba(features, 'drc_clean'),
        }

    def is_ready(self) -> bool:
        """Check if all models are loaded."""
        ppa_loaded = len(self.ppa.models) == 4
        failure_loaded = len(self.failure.models) == 2
        return ppa_loaded and failure_loaded


# ── Factory Function ────────────────────────────────────────────────────────

def create_intelligence(model_dir: Optional[Path] = None) -> RandomForestIntelligence:
    """
    Factory function to create and load all RF intelligence models.

    Usage:
        intelligence = create_intelligence()
        intelligence.load_all()

        ppa = intelligence.predict_ppa(features)
        risk = intelligence.predict_failure_risk(features)
    """
    intelligence = RandomForestIntelligence(model_dir)
    return intelligence


# ── Example Usage ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Example usage
    print("Random Forest Models for OpenROAD Flow GUI")
    print("=" * 50)

    # Check available models
    model_dir = Path(__file__).parent / "saved"
    for target in ['wns', 'tns', 'area', 'power', 'timing_closure', 'drc_clean']:
        model_file = {
            'wns': 'wns_rf.pkl',
            'tns': 'tns_rf.pkl',
            'area': 'area_rf.pkl',
            'power': 'power_rf.pkl',
            'timing_closure': 'timing_closure_rf.pkl',
            'drc_clean': 'drc_clean_rf.pkl',
        }[target]
        path = Path(__file__).parent / "saved" / model_file
        exists = "✅" if Path(path).exists() else "❌"
        print(f"  {target:20s}: {exists}")

    print("\nTo use in your application:")
    print("  from openroad_gui.intelligence.models.random_forest import RandomForestIntelligence")
    print("  rf = RandomForestIntelligence()")
    print("  rf.load_all()")
    print("  ppa = rf.predict_ppa(features)")
    print("  risk = rf.predict_failure_risk(features)")
