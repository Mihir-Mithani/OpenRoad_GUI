"""Evaluation metrics for ML models."""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


@dataclass
class RegressionMetrics:
    """Regression evaluation metrics."""
    mse: float
    rmse: float
    mae: float
    r2: float
    mape: float

    @classmethod
    def compute(cls, y_true: np.ndarray, y_pred: np.ndarray) -> 'RegressionMetrics':
        """Compute all regression metrics."""
        mse = mean_squared_error(y_true, y_pred)
        return cls(
            mse=mse,
            rmse=np.sqrt(mse),
            mae=mean_absolute_error(y_true, y_pred),
            r2=r2_score(y_true, y_pred),
            mape=np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1e-8))) * 100,
        )


@dataclass
class ClassificationMetrics:
    """Classification evaluation metrics."""
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    confusion_matrix: np.ndarray

    @classmethod
    def compute(cls, y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray = None) -> 'ClassificationMetrics':
        """Compute all classification metrics."""
        return cls(
            accuracy=accuracy_score(y_true, y_pred),
            precision=precision_score(y_true, y_pred, average='weighted', zero_division=0),
            recall=recall_score(y_true, y_pred, average='weighted', zero_division=0),
            f1=f1_score(y_true, y_pred, average='weighted', zero_division=0),
            roc_auc=roc_auc_score(y_true, y_prob) if y_prob is not None else 0.0,
            confusion_matrix=confusion_matrix(y_true, y_pred),
        )


@dataclass
class FlowMetrics:
    """Flow-specific evaluation metrics."""
    wns_mae_ns: float
    tns_mae_ns: float
    area_mape: float
    power_mape: float
    drc_accuracy: float
    timing_closure_rate: float
    drc_clean_rate: float

    @classmethod
    def compute(cls, y_true: Dict, y_pred: Dict) -> 'FlowMetrics':
        """Compute flow-specific metrics."""
        return cls(
            wns_mae_ns=np.mean(np.abs(y_true.get("wns", []) - y_pred.get("wns", []))),
            tns_mae_ns=np.mean(np.abs(y_true.get("tns", []) - y_pred.get("tns", []))),
            area_mape=np.mean(np.abs(np.array(y_true.get("area", [])) - np.array(y_pred.get("area", []))) / np.maximum(np.abs(y_true.get("area", [])), 1e-8)) * 100,
            power_mape=np.mean(np.abs(np.array(y_true.get("power", [])) - np.array(y_pred.get("power", []))) / np.maximum(np.abs(y_true.get("power", [])), 1e-8)) * 100,
            drc_accuracy=np.mean(np.array(y_true.get("drc", [])) == np.array(y_pred.get("drc", []))),
            timing_closure_rate=np.mean(np.array(y_true.get("timing", [])) == np.array(y_pred.get("timing", []))),
            drc_clean_rate=np.mean(np.array(y_true.get("drc", [])) == np.array(y_pred.get("drc", []))),
        )


def compute_metrics(y_true: Any, y_pred: Any, task_type: str = "regression") -> Dict[str, float]:
    """
    Compute appropriate metrics based on task type.

    Args:
        y_true: Ground truth values
        y_pred: Predicted values
        task_type: "regression", "classification", or "flow"

    Returns:
        Dictionary of computed metrics
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    if task_type == "regression":
        metrics = RegressionMetrics.compute(y_true, y_pred)
        return {
            "mse": metrics.mse,
            "rmse": metrics.rmse,
            "mae": metrics.mae,
            "r2": metrics.r2,
            "mape": metrics.mape,
        }
    elif task_type == "classification":
        metrics = ClassificationMetrics.compute(y_true, y_pred)
        return {
            "accuracy": metrics.accuracy,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "roc_auc": metrics.roc_auc,
        }
    elif task_type == "flow":
        metrics = FlowMetrics.compute(y_true, y_pred)
        return {
            "wns_mae_ns": metrics.wns_mae_ns,
            "tns_mae_ns": metrics.tns_mae_ns,
            "area_mape": metrics.area_mape,
            "power_mape": metrics.power_mape,
            "drc_accuracy": metrics.drc_accuracy,
            "timing_closure_rate": metrics.timing_closure_rate,
            "drc_clean_rate": metrics.drc_clean_rate,
        }
    else:
        raise ValueError(f"Unknown task_type: {task_type}")