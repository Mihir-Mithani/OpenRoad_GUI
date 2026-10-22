"""Failure prediction architecture for OpenROAD flow stages."""

from __future__ import annotations

import os
import joblib
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from pathlib import Path


class FailureType(Enum):
    """Types of flow failures that can be predicted."""
    TIMING_VIOLATION = "timing_violation"      # WNS < 0
    DRC_VIOLATION = "drc_violation"            # DRC violations
    CONGESTION = "congestion"                  # Routing congestion
    POWER_VIOLATION = "power_violation"        # Power budget exceeded
    AREA_OVERFLOW = "area_overflow"            # Area exceeds limit
    RUNTIME_TIMEOUT = "runtime_timeout"        # Stage timeout
    LVS_FAILURE = "lvs_failure"                # LVS mismatch


@dataclass
class FailurePrediction:
    """Prediction result for a flow stage."""
    failure_type: FailureType
    probability: float          # 0.0 - 1.0
    confidence: float           # Model confidence
    severity: str               # "low", "medium", "high", "critical"
    affected_stage: str
    estimated_impact: str       # Description of impact if failure occurs
    suggested_mitigations: List[str] = field(default_factory=list)


@dataclass
class StageMetrics:
    """Metrics collected during a flow stage for failure prediction."""
    stage_name: str

    # Timing metrics
    wns_ns: float = 0.0
    tns_ns: float = 0.0
    num_critical_paths: int = 0

    # Area/Power
    area_um2: float = 0.0
    power_mw: float = 0.0

    # Quality metrics
    drc_violations: int = 0
    congestion_pct: float = 0.0
    max_congestion: float = 0.0

    # Placement/Route quality
    placement_density: float = 0.0
    wirelength: float = 0.0
    via_count: int = 0

    # Timing details
    wns_trend: float = 0.0      # WNS change rate (ns per iteration)
    tns_trend: float = 0.0
    critical_path_depth: int = 0

    # Runtime context
    iteration: int = 0
    runtime_sec: float = 0.0
    memory_usage_mb: float = 0.0


class FailurePredictor:
    """
    Failure prediction for OpenROAD flow stages using trained LightGBM model.

    Loads trained LightGBM model (AUC 0.755) for timing closure prediction.
    Falls back to calibrated heuristic if model unavailable.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or self._default_model_path()
        self._model = None
        self._preprocessor = None
        self._feature_columns = self._define_feature_columns()
        self._load_model()

    def _default_model_path(self) -> str:
        """Get default model path relative to this file."""
        base = Path(__file__).parent.parent.parent.parent
        return str(base / "models" / "saved" / "timing_closure_lgb.pkl")

    def _define_feature_columns(self) -> List[str]:
        """Define feature columns expected by the model (must match training)."""
        return [
            # Design features (from training data)
            "log_instances", "log_nets", "seq_ratio", "macro_ratio",
            "core_utilization", "core_aspect_ratio", "core_margin",
            "platform_cat",

            # Stage metrics (runtime)
            "wns_ns", "tns_ns", "num_critical_paths",
            "drc_violations", "congestion_pct", "max_congestion",
            "placement_density", "wirelength", "via_count",

            # Runtime context
            "iteration", "runtime_sec", "memory_usage_mb",
        ]

    def _load_model(self) -> None:
        """Load trained LightGBM model and preprocessor."""
        model_path = Path(self.model_path)
        preprocessor_path = Path(str(model_path).replace("_lgb.pkl", "_preprocessor.pkl"))

        try:
            import joblib
            model_data = joblib.load(self.model_path)
            self._model = model_data.get("model")

            if preprocessor_path.exists():
                self._preprocessor = joblib.load(str(preprocessor_path))
            else:
                # Build default preprocessor matching training
                from sklearn.preprocessing import StandardScaler, OneHotEncoder
                from sklearn.compose import ColumnTransformer

                numeric_features = [
                    "log_instances", "log_nets", "seq_ratio", "macro_ratio",
                    "core_utilization", "core_aspect_ratio", "core_margin",
                    "wns_ns", "tns_ns", "num_critical_paths",
                    "drc_violations", "congestion_pct", "max_congestion",
                    "placement_density", "wirelength", "via_count",
                    "iteration", "runtime_sec", "memory_usage_mb",
                ]
                categorical_features = ["platform_cat"]

                self._preprocessor = ColumnTransformer(
                    transformers=[
                        ("num", StandardScaler(), numeric_features),
                        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
                    ],
                    remainder="drop"
                )

            print(f"✅ Loaded timing closure model from {self.model_path}")
        except Exception as e:
            print(f"⚠️  Failed to load model: {e}. Falling back to calibrated heuristic.")
            self._model = None
            self._preprocessor = None

    def predict(self, metrics: dict) -> dict:
        """
        Predict failure probability for current stage using trained model or calibrated heuristic.

        Args:
            metrics: Current stage metrics dict with keys matching _feature_columns

        Returns:
            Dict with failure predictions per failure type
        """
        # Try trained model first
        if self._model is not None and self._preprocessor is not None:
            return self._predict_with_model(metrics)

        # Fallback to calibrated heuristic
        return self._predict_heuristic(metrics)

    def _predict_with_model(self, metrics: dict) -> dict:
        """Use trained LightGBM model for prediction."""
        try:
            import pandas as pd

            # Prepare feature vector matching training columns
            feature_dict = {}
            for col in self._feature_columns:
                feature_dict[col] = metrics.get(col, 0)

            # Add defaults for missing design features
            defaults = {
                "log_instances": 0, "log_nets": 0, "seq_ratio": 0, "macro_ratio": 0,
                "core_utilization": 50, "core_aspect_ratio": 1.0, "core_margin": 5,
                "platform_cat": "asap7",
            }
            for k, v in defaults.items():
                if k not in feature_dict or feature_dict[k] is None:
                    feature_dict[k] = v

            # Create DataFrame and preprocess
            df = pd.DataFrame([feature_dict])
            X = self._preprocessor.transform(df)

            # Predict probability
            prob = self._model.predict(X, num_iteration=self._model.best_iteration)[0]
            prob = float(np.clip(prob, 0.0, 1.0))

            # Determine severity based on probability
            if prob >= 0.7:
                severity = "high"
            elif prob >= 0.4:
                severity = "medium"
            else:
                severity = "low"

            predictions = {}
            if prob > 0.5:
                predictions["timing_violation"] = {
                    "probability": prob,
                    "severity": severity,
                    "confidence": 0.755,  # Model AUC
                    "mitigations": ["Increase placement effort", "Reduce density", "Add pipeline stages", "Review clock constraints"]
                }

            overall_risk = prob if prob > 0.5 else 0.0

            return {
                "predictions": predictions,
                "overall_risk": overall_risk,
                "model_used": "LightGBM (AUC 0.755)",
                "recommendations": self._aggregate_recommendations({"timing_violation": {"mitigations": ["Increase placement effort", "Reduce density", "Add pipeline stages"]}} if prob > 0.5 else {})
            }

        except Exception as e:
            print(f"⚠️  Model prediction failed: {e}. Falling back to heuristic.")
            return self._predict_heuristic(metrics)

    def _predict_heuristic(self, metrics: dict) -> dict:
        """
        Calibrated heuristic fallback with improved thresholds.

        Thresholds calibrated from observed data:
        - WNS < -5ns → High risk (90%+)
        - -5 < WNS < 0 → Medium risk (30-70%)
        - WNS >= 0 → Low risk (<10%)
        """
        predictions = {}
        wns = metrics.get("wns_ns", 0)

        # Calibrated timing violation probability
        if wns < -5.0:
            prob = 0.95
            severity = "high"
        elif wns < 0:
            # Linear interpolation between 0.3 (at 0) and 0.95 (at -5)
            prob = 0.3 + 0.65 * (abs(wns) / 5.0)
            severity = "high" if wns < -2.0 else "medium"
        else:
            prob = 0.05
            severity = "low"

        predictions = {}
        if prob > 0.5:
            predictions["timing_violation"] = {
                "probability": prob,
                "severity": severity,
                "confidence": 0.7,  # Heuristic confidence
                "mitigations": ["Increase placement effort", "Reduce density", "Add pipeline stages", "Review clock constraints"]
            }

        # DRC violation prediction (if data available)
        drc = metrics.get("drc_violations", 0)
        if drc > 0:
            prob = min(drc / 100.0, 1.0)
            severity = "critical" if drc > 100 else "high"
            predictions["drc_violation"] = {
                "probability": prob,
                "severity": severity,
                "mitigations": ["Increase routing layers", "Reduce density", "Manual fix"]
            }

        # Congestion prediction
        cong = metrics.get("congestion_pct", 0)
        if cong > 80:
            prob = cong / 100.0
            severity = "critical" if cong > 95 else "high"
            predictions["congestion"] = {
                "probability": prob,
                "severity": severity,
                "mitigations": ["Increase routing layers", "Reduce density", "Spread macros"]
            }

        overall_risk = max([p.get("probability", 0) for p in predictions.values()], default=0.0)

        return {
            "predictions": predictions,
            "overall_risk": overall_risk,
            "model_used": "Calibrated Heuristic",
            "recommendations": self._aggregate_recommendations(predictions)
        }

    def _aggregate_recommendations(self, predictions: dict) -> List[str]:
        """Aggregate mitigation strategies from all predictions."""
        all_mitigations = []
        for pred in predictions.values():
            all_mitigations.extend(pred.get("mitigations", []))
        # Deduplicate and prioritize
        seen = set()
        unique = []
        for m in all_mitigations:
            if m not in seen:
                seen.add(m)
                unique.append(m)
        return unique[:5]  # Top 5 recommendations


# Type imports at module level
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np