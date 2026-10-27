"""ONNX Export and Inference Engine for surrogate models."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

# Optional imports
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import lightgbm as lgb
    LGB_AVAILABLE = True
except ImportError:
    LGB_AVAILABLE = False

try:
    import onnx
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


class MLPRegressor(nn.Module):
    """PyTorch MLP matching train_surrogate.py architecture."""

    def __init__(self, input_dim: int, hidden_dims=(256, 128, 64), dropout=0.2):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev_dim, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev_dim = h
        layers.append(nn.Linear(prev_dim, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x).squeeze(-1)


class ONNXExporter:
    """Export trained models to ONNX format for deployment."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir).resolve()

    def export_lightgbm_to_onnx(self, target: str, output_path: str | Path) -> bool:
        """Export LightGBM model to ONNX using onnxmltools."""
        if not ONNX_AVAILABLE:
            print("ONNX not available, skipping export")
            return False

        try:
            import onnxmltools
            from onnxmltools.convert.lightgbm.operator_converters.LightGbm import convert_lightgbm
            from onnxmltools.convert.common.data_types import FloatTensorType

            model_path = self.model_dir / f"surrogate_{target}_lgb.pkl"
            if not model_path.exists():
                print(f"Model not found: {model_path}")
                return False

            model_data = joblib.load(model_path)
            lgb_model = model_data['model']
            preprocessor = model_data.get('preprocessor')

            # Get input dimension from preprocessor
            if preprocessor:
                import pandas as pd
                dummy = pd.DataFrame([{
                    'platform': 'sky130hd',
                    'core_aspect_ratio': 1.0,
                    'core_utilization': 30,
                    'core_margin': 5,
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
                X_dummy = preprocessor.transform(dummy)
                input_dim = X_dummy.shape[1]
            else:
                input_dim = 17  # current feature dim after preprocessing

            initial_type = [('float_input', FloatTensorType([None, input_dim]))]

            # Use onnxmltools convert_lightgbm with correct API
            onnx_model = onnxmltools.convert_lightgbm(
                lgb_model,
                initial_types=initial_type,
                target_opset=12,
                zipmap=False
            )

            onnx.save_model(onnx_model, str(output_path))
            print(f"Exported LightGBM {target} to ONNX: {output_path}")
            return True

        except Exception as e:
            print(f"Failed to export LightGBM {target} to ONNX: {e}")
            import traceback
            traceback.print_exc()
            return False

    def export_mlp_to_onnx(self, target: str, output_path: str | Path) -> bool:
        """Export PyTorch MLP to ONNX."""
        if not (ONNX_AVAILABLE and TORCH_AVAILABLE):
            print("ONNX/PyTorch not available, skipping export")
            return False

        try:
            model_path = self.model_dir / f"surrogate_{target}_mlp.pt"
            if not model_path.exists():
                print(f"MLP model not found: {model_path}")
                return False

            # Fix: weights_only=False for PyTorch 2.6+ compatibility
            checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
            input_dim = checkpoint.get('input_dim', 17)

            model = MLPRegressor(input_dim)
            model.load_state_dict(checkpoint['model_state'])
            model.eval()

            # Export
            dummy_input = torch.randn(1, input_dim)
            torch.onnx.export(
                model,
                dummy_input,
                str(output_path),
                export_params=True,
                opset_version=12,
                do_constant_folding=True,
                input_names=['input'],
                output_names=['output'],
                dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}},
            )
            print(f"Exported MLP {target} to ONNX: {output_path}")
            return True

        except Exception as e:
            print(f"Failed to export MLP {target} to ONNX: {e}")
            import traceback
            traceback.print_exc()
            return False

    def export_all(self, targets: List[str] = None) -> Dict[str, bool]:
        """Export all models for given targets."""
        if targets is None:
            targets = ['wns', 'tns', 'area', 'power']

        results = {}
        for target in targets:
            lgb_path = self.model_dir / f"surrogate_{target}_lgb.onnx"
            mlp_path = self.model_dir / f"surrogate_{target}_mlp.onnx"

            results[f"{target}_lgb"] = self.export_lightgbm_to_onnx(target, lgb_path)
            results[f"{target}_mlp"] = self.export_mlp_to_onnx(target, mlp_path)

        return results


class ONNXInferenceEngine:
    """Fast ONNX Runtime inference for surrogate models."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir).resolve()
        self.sessions: Dict[str, ort.InferenceSession] = {}
        self.preprocessor = None
        self._load_preprocessor()

    def _load_preprocessor(self):
        """Load the shared preprocessor."""
        preprocessor_path = self.model_dir / "surrogate_preprocessor.pkl"
        if preprocessor_path.exists():
            self.preprocessor = joblib.load(preprocessor_path)

    def load_model(self, target: str, model_type: str = 'lgb') -> bool:
        """Load ONNX model for inference."""
        if not ONNX_AVAILABLE:
            return False

        model_path = self.model_dir / f"surrogate_{target}_{model_type}.onnx"
        if not model_path.exists():
            return False

        try:
            self.sessions[f"{target}_{model_type}"] = ort.InferenceSession(str(model_path))
            return True
        except Exception as e:
            print(f"Failed to load ONNX model {target}_{model_type}: {e}")
            return False

    def predict(self, features: Dict[str, Any], target: str, model_type: str = 'lgb') -> Optional[float]:
        """Run inference on preprocessed features."""
        if self.preprocessor is None:
            raise ValueError("Preprocessor not loaded")

        if f"{target}_{model_type}" not in self.sessions:
            if not self.load_model(target, model_type):
                return None

        # Preprocess
        import pandas as pd
        df = pd.DataFrame([features])
        X = self.preprocessor.transform(df)

        # Inference
        session = self.sessions[f"{target}_{model_type}"]
        input_name = session.get_inputs()[0].name
        output = session.run(None, {input_name: X.astype(np.float32)})

        return float(output[0][0])

    def predict_batch(self, features_list: List[Dict], target: str, model_type: str = 'lgb') -> List[float]:
        """Batch inference."""
        if self.preprocessor is None:
            raise ValueError("Preprocessor not loaded")

        if f"{target}_{model_type}" not in self.sessions:
            if not self.load_model(target, model_type):
                return []

        import pandas as pd
        df = pd.DataFrame(features_list)
        X = self.preprocessor.transform(df)

        session = self.sessions[f"{target}_{model_type}"]
        input_name = session.get_inputs()[0].name
        output = session.run(None, {input_name: X.astype(np.float32)})

        return output[0].flatten().tolist()


class SurrogateInference:
    """High-level inference using joblib models (no ONNX required)."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir).resolve()
        self.models: Dict[str, Dict] = {}
        self.preprocessor = None
        self._load_all()

    def _load_all(self):
        """Load preprocessor and all available models."""
        preprocessor_path = self.model_dir / "surrogate_preprocessor.pkl"
        if preprocessor_path.exists():
            self.preprocessor = joblib.load(preprocessor_path)

        targets = ['wns', 'tns', 'area', 'power']
        for target in targets:
            self.models[target] = {}
            # LightGBM
            lgb_path = self.model_dir / f"surrogate_{target}_lgb.pkl"
            if lgb_path.exists():
                self.models[target]['lgb'] = joblib.load(lgb_path)
            # MLP
            if TORCH_AVAILABLE:
                mlp_path = self.model_dir / f"surrogate_{target}_mlp.pt"
                if mlp_path.exists():
                    checkpoint = torch.load(mlp_path, map_location='cpu', weights_only=False)
                    model = MLPRegressor(checkpoint.get('input_dim', 17))
                    model.load_state_dict(checkpoint['model_state'])
                    model.eval()
                    self.models[target]['mlp'] = model

    def predict(self, features: Dict[str, Any], target: str, model_type: str = 'lgb') -> Optional[float]:
        """Predict single target using specified model type."""
        if self.preprocessor is None:
            raise ValueError("Preprocessor not loaded")

        if target not in self.models or model_type not in self.models[target]:
            return None

        import pandas as pd
        df = pd.DataFrame([features])
        X = self.preprocessor.transform(df)

        model_data = self.models[target][model_type]

        if model_type == 'lgb':
            model = model_data['model'] if isinstance(model_data, dict) else model_data
            pred = model.predict(X, num_iteration=model.best_iteration)
            return float(pred[0])
        elif model_type == 'mlp' and TORCH_AVAILABLE:
            model = model_data
            with torch.no_grad():
                pred = model(torch.FloatTensor(X))
            return float(pred.item())

        return None

    def predict_all(self, features: Dict[str, Any], model_type: str = 'lgb') -> Dict[str, float]:
        """Predict all PPA targets."""
        results = {}
        for target in ['wns', 'tns', 'area', 'power']:
            pred = self.predict(features, target, model_type)
            if pred is not None:
                results[target] = pred
        return results

    def predict_ensemble(self, features: Dict[str, Any]) -> Dict[str, float]:
        """Predict using ensemble average of LightGBM + MLP."""
        results = {}
        for target in ['wns', 'tns', 'area', 'power']:
            preds = []
            for model_type in ['lgb', 'mlp']:
                pred = self.predict(features, target, model_type)
                if pred is not None:
                    preds.append(pred)
            if preds:
                results[target] = float(np.mean(preds))
        return results


def main():
    """CLI for ONNX export."""
    import argparse
    parser = argparse.ArgumentParser(description="Export surrogate models to ONNX")
    parser.add_argument('--model-dir', type=Path, default=Path("openroad_gui/intelligence/models/saved"))
    parser.add_argument('--targets', nargs='+', default=['wns', 'tns', 'area', 'power'])
    args = parser.parse_args()

    exporter = ONNXExporter(args.model_dir)
    results = exporter.export_all(args.targets)

    print("\nExport Results:")
    for model, success in results.items():
        print(f"  {model}: {'✓' if success else '✗'}")


if __name__ == '__main__':
    main()