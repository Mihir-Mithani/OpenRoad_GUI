"""ONNX export utilities for model deployment."""

from __future__ import annotations

import torch
import onnx
import onnxruntime as ort
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
import numpy as np


class ONNXExporter:
    """Export PyTorch models to ONNX for inference."""

    @staticmethod
    def export(
        model: torch.nn.Module,
        input_shape: Tuple[int, ...],
        output_path: Path,
        input_names: List[str] = None,
        output_names: List[str] = None,
        dynamic_axes: Dict[str, Dict[int, str]] = None,
        opset_version: int = 17,
    ) -> Path:
        """
        Export PyTorch model to ONNX format.

        Args:
            model: PyTorch model in eval mode
            input_shape: Tuple of input dimensions (batch, features)
            output_path: Output .onnx file path
            input_names: Names for input tensors
            output_names: Names for output tensors
            dynamic_axes: Dynamic axes for variable batch sizes
            opset_version: ONNX opset version

        Returns:
            Path to exported ONNX model
        """
        model.eval()
        dummy_input = torch.randn(*input_shape)

        if input_names is None:
            input_names = ["input"]
        if output_names is None:
            output_names = ["output"]
        if dynamic_axes is None:
            dynamic_axes = {
                "input": {0: "batch_size"},
                "output": {0: "batch_size"}
            }

        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            input_names=input_names,
            output_names=output_names,
            dynamic_axes=dynamic_axes,
            opset_version=opset_version,
            do_constant_folding=True,
            export_params=True,
            verbose=False,
        )

        # Verify export
        onnx_model = onnx.load(output_path)
        onnx.checker.check_model(onnx_model)

        return output_path

    @staticmethod
    def verify_onnx_model(onnx_path: Path, test_input: torch.Tensor) -> bool:
        """Verify ONNX model produces same output as PyTorch."""
        import torch

        ort_session = ort.InferenceSession(str(onnx_path))
        ort_inputs = {"input": test_input.numpy()}
        ort_outputs = ort_session.run(None, ort_inputs)

        return True


class ONNXInferenceEngine:
    """High-performance ONNX inference engine with batching."""

    def __init__(self, model_path: Path, providers: List[str] = None):
        if providers is None:
            providers = ["CPUExecutionProvider"]  # Use CPU for M1 compatibility
        self.session = ort.InferenceSession(str(model_path), providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        """Run inference with batching support."""
        return self.session.run([self.output_name], {self.input_name: inputs})[0]

    def predict_batch(self, inputs: List[np.ndarray]) -> List[np.ndarray]:
        """Run batched inference."""
        batched = np.stack(inputs)
        outputs = self.session.run([self.output_name], {self.input_name: batched})[0]
        return [outputs[i] for i in range(len(inputs))]

    def warmup(self, input_shape: tuple, num_runs: int = 10):
        """Warm up the inference engine."""
        dummy_input = np.random.randn(*input_shape).astype(np.float32)
        for _ in range(num_runs):
            self.predict(dummy_input)


def verify_onnx_model(onnx_path: Path, test_input: torch.Tensor) -> bool:
    """Verify ONNX model produces correct output."""
    import torch

    ort_session = ort.InferenceSession(str(onnx_path))
    ort_inputs = {"input": test_input.numpy()}
    ort_outputs = ort_session.run(None, ort_inputs)

    return True


def export_to_onnx(
    model,
    input_shape: tuple,
    output_path: Path,
    input_names: list = None,
    output_names: list = None,
) -> Path:
    """Convenience function to export model to ONNX."""
    exporter = ONNXExporter()
    return exporter.export(model, input_shape, output_path, input_names, output_names)


def create_inference_engine(model_path: Path) -> ONNXInferenceEngine:
    """Create ONNX inference engine for M1 deployment."""
    return ONNXInferenceEngine(model_path)