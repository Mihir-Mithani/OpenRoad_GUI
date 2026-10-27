#!/usr/bin/env python3
"""
PPO Flow Optimizer Training for Google Colab
Self-contained script - no repo clone needed.
Just upload this folder to Google Drive and mount in Colab.

Usage in Colab:
    from google.colab import drive
    drive.mount('/content/drive')
    %cd /content/drive/MyDrive/colab_rl_package/training
    !pip install stable-baselines3[extra] gymnasium torch polars scikit-learn joblib
    python train_ppo_colab.py --timesteps 200000 --device cuda
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecMonitor

# ─── Paths ────────────────────────────────────────────────────────────────
PACKAGE_ROOT = Path(__file__).parent.parent
MODELS_DIR = PACKAGE_ROOT / "models"
DESIGNS_DIR = PACKAGE_ROOT / "designs"

# ─── Constants ────────────────────────────────────────────────────────────
ACTION_DIM = 16
STATE_DIM = 128

ACTION_LOW = np.array([
    0, 0, 0, 0,          # synth: strategy, effort, retime, resynth
    0.4, 0, 0,           # floorplan: density, effort, macro_placement
    0.01, 0, 0,          # cts: skew_target, buffer_type, clustering
    4, 0, 0.5,           # routing: layers, effort, detour_scale
    0,                   # signoff: effort
], dtype=np.float32)

ACTION_HIGH = np.array([
    3, 3, 1, 1,          # synth
    0.8, 3, 2,           # floorplan
    0.1, 3, 2,           # cts
    8, 3, 2.0,           # routing
    2,                   # signoff
], dtype=np.float32)


# ─── MLP Surrogate Model ─────────────────────────────────────────────────
class MLPRegressor(nn.Module):
    """MLP matching train_surrogate.py architecture."""

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


# ─── Surrogate Inference ─────────────────────────────────────────────────
class SurrogateInference:
    """Load and run surrogate models (MLP only for Colab)."""

    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self.preprocessor = joblib.load(model_dir / "surrogate_preprocessor.pkl")
        self.models = {}
        self.input_dim = None
        self._load_models()

    def _load_models(self):
        """Load all MLP models."""
        targets = ['wns', 'tns', 'area', 'power']
        for target in targets:
            model_path = self.model_dir / f"surrogate_{target}_mlp.pt"
            if model_path.exists():
                checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
                self.input_dim = checkpoint.get('input_dim', 26)
                model = MLPRegressor(self.input_dim)
                model.load_state_dict(checkpoint['model_state'])
                model.eval()
                self.models[target] = model
                print(f"Loaded {target} MLP model")
            else:
                print(f"Warning: {model_path} not found")

    def predict(self, features: Dict[str, float], target: str) -> float:
        """Predict single target for given features."""
        if target not in self.models:
            return 0.0

        # Preprocess features
        df = pd.DataFrame([features])
        X = self.preprocessor.transform(df)

        # Predict
        model = self.models[target]
        with torch.no_grad():
            pred = model(torch.FloatTensor(X))
        return float(pred.item())

    def predict_ensemble(self, features: Dict[str, float]) -> Dict[str, float]:
        """Predict all targets."""
        return {target: self.predict(features, target) for target in self.models}


# ─── RL Environment ──────────────────────────────────────────────────────
ACTION_DIM = 16
STATE_DIM = 128

ACTION_LOW = np.array([0,0,0,0, 0.4,0,0, 0.01,0,0, 4,0,0.5, 0], dtype=np.float32)
ACTION_HIGH = np.array([3,3,1,1, 0.8,3,2, 0.1,3,2, 8,3,2.0, 2], dtype=np.float32)


class FlowOptEnv(gym.Env):
    """OpenROAD Flow Optimization Environment using surrogate models."""

    def __init__(self, surrogate: SurrogateInference, designs: List[Dict], max_stages: int = 6):
        super().__init__()
        self.surrogate = surrogate
        self.designs = designs
        self.max_stages = max_stages

        self.action_space = spaces.Box(low=ACTION_LOW, high=ACTION_HIGH, dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(STATE_DIM,), dtype=np.float32)

        self.designs = designs
        self.max_stages = max_stages
        self.current_design_idx = 0
        self.current_stage = 0
        self.prev_ppa = None

        # Reward weights (matching FlowReward)
        self.reward_weights = {
            "wns": 0.30, "tns": 0.15, "area": 0.15,
            "power": 0.10, "drc": 0.15, "congestion": 0.10, "runtime": 0.05
        }

    def _predict_ppa(self, design: Dict, action: np.ndarray) -> Dict[str, float]:
        """Predict PPA using surrogate ensemble."""
        features = self._build_features(design)
        predictions = self.surrogate.predict_ensemble(features)
        return {
            "wns": predictions.get("wns", 0.0),
            "tns": predictions.get("tns", 0.0),
            "area": predictions.get("area", 0.0),
            "power": predictions.get("power", 0.0),
            "drc": 0,
            "congestion": 0.0,
        }

    def _build_features(self, design: Dict) -> Dict[str, float]:
        """Build feature dict matching preprocessor schema."""
        return {
            "platform": design.get("platform", "sky130hd"),
            "core_aspect_ratio": str(design.get("core_aspect_ratio", 1.0)),
            "core_utilization": float(design.get("core_utilization", 30.0)),
            "core_margin": float(design.get("core_margin", 5.0)),
            "num_instances": design.get("num_instances", 5000),
            "num_nets": design.get("num_nets", 6000),
            "num_sequential": design.get("num_sequential", 1000),
            "num_macros": design.get("num_macros", 0),
            "macro_area_ratio": design.get("macro_area_ratio", 0.0),
            "log_instances": np.log1p(design.get("num_instances", 5000)) / 20.0,
            "log_nets": np.log1p(design.get("num_nets", 6000)) / 20.0,
            "seq_ratio": design.get("num_sequential", 1000) / max(1, design.get("num_instances", 5000)),
            "macro_ratio": design.get("num_macros", 0) / max(1, design.get("num_instances", 5000)),
        }

    def _compute_reward(self, prev: Dict, curr: Dict) -> float:
        """Multi-objective reward."""
        reward = 0.0
        w = self.reward_weights

        # Timing
        reward += w["wns"] * np.tanh((curr["wns"] - prev["wns"]) / 0.5)
        reward += w["tns"] * np.tanh((curr["tns"] - prev["tns"]) / 10.0)

        # Area/Power
        if prev["area"] > 0:
            reward += w["area"] * np.tanh((prev["area"] - curr["area"]) / prev["area"] * 10)
        if prev["power"] > 0:
            reward += w["power"] * np.tanh((prev["power"] - curr["power"]) / prev["power"] * 10)

        # DRC/cong (not predicted yet)
        if prev.get("drc", 0) > curr.get("drc", 0):
            reward += w["drc"] * min((prev["drc"] - curr["drc"]) / 100.0, 1.0)

        # Runtime penalty
        reward -= w["runtime"] * 0.01

        # Terminal bonuses
        if curr["wns"] >= 0:
            reward += 10.0

        return float(np.clip(reward, -50.0, 50.0))

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_design_idx = self.np_random.integers(0, len(self.designs))
        self.current_stage = 0

        design = self.designs[self.current_design_idx]
        self.prev_ppa = self._predict_ppa(design, np.zeros(16))

        # Simple state encoding (128-dim random for now)
        obs = self.np_random.normal(0, 1, STATE_DIM).astype(np.float32)
        return obs, {}

    def step(self, action: np.ndarray):
        action = np.clip(action, ACTION_LOW, ACTION_HIGH)
        design = self.designs[self.current_design_idx]

        curr_ppa = self._predict_ppa(design, action)
        reward = self._compute_reward(self.prev_ppa, curr_ppa)

        self.prev_ppa = curr_ppa
        self.current_stage += 1

        obs = np.random.normal(0, 1, STATE_DIM).astype(np.float32)  # Simplified

        terminated = self.current_stage >= 6 or curr_ppa["wns"] >= 0
        truncated = False

        info = {"ppa": curr_ppa, "stage": self.current_stage}
        return obs, reward, terminated, False, info


# ─── Helper Functions ────────────────────────────────────────────────────
ACTION_DIM = 16
STATE_DIM = 128
ACTION_LOW = np.array([0,0,0,0, 0.4,0,0, 0.01,0,0, 4,0,0.5, 0], dtype=np.float32)
ACTION_HIGH = np.array([3,3,1,1, 0.8,3,2, 0.1,3,2, 8,3,2.0, 2], dtype=np.float32)


def load_designs(designs_path: Path) -> List[Dict]:
    """Load designs from CSV."""
    df = pd.read_csv(designs_path)
    return df.to_dict('records')


def make_env(surrogate, designs, rank=0):
    def _init():
        env = FlowOptEnv(surrogate, designs)
        return Monitor(env)
    return _init


def train_ppo(timesteps=200_000, n_envs=4, device="auto", log_dir="./logs", model_dir="./models"):
    """Main training function."""

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    Path(model_dir).mkdir(parents=True, exist_ok=True)

    device = "cuda" if (device == "auto" and torch.cuda.is_available()) else device
    print(f"Device: {device}")

    # Load surrogate
    surrogate = SurrogateInference(MODELS_DIR)

    # Load designs
    designs = load_designs(DESIGNS_DIR / "designs.csv")
    print(f"Loaded {len(designs)} designs")

    # Create envs
    env = SubprocVecEnv([make_env(surrogate, designs, i) for i in range(n_envs)])
    env = VecMonitor(env, log_dir)

    eval_env = DummyVecEnv([make_env(surrogate, designs, 0)])
    eval_env = VecMonitor(eval_env)

    # PPO
    model = PPO(
        "MlpPolicy", env,
        learning_rate=3e-4, n_steps=2048, batch_size=64, n_epochs=10,
        gamma=0.99, gae_lambda=0.95, clip_range=0.2,
        ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5,
        policy_kwargs=dict(net_arch=[256, 256], activation_fn=torch.nn.ReLU),
        tensorboard_log=log_dir, device=device, verbose=1,
    )

    callbacks = [
        CheckpointCallback(save_freq=50000, save_path=model_dir, name_prefix="ppo_flow"),
        EvalCallback(eval_env, best_model_save_path=f"{model_dir}/best", eval_freq=25000, n_eval_episodes=5),
    ]

    print(f"Training for {timesteps:,} timesteps...")
    model.learn(total_timesteps=timesteps, callback=callbacks, progress_bar=True)

    # Save
    final_path = Path(model_dir) / "ppo_flow_optimizer_final"
    model.save(final_path)
    print(f"Model saved to {final_path}")

    # Export ONNX
    try:
        dummy_input = torch.randn(1, 128)
        torch.onnx.export(model.policy, torch.randn(1, 128),
                         str(Path(model_dir) / "ppo_flow_optimizer.onnx"),
                         opset_version=17, input_names=["obs"], output_names=["action"])
        print("ONNX exported")
    except Exception as e:
        print(f"ONNX export failed: {e}")

    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=200000)
    parser.add_argument("--n-envs", type=int, default=4)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    args = parser.parse_args()

    device = "cuda" if (args.device == "auto" and torch.cuda.is_available()) else args.device

    print(f"Training PPO Flow Optimizer on {device}")
    print(f"Models dir: {MODELS_DIR}")
    print(f"Designs dir: {DESIGNS_DIR}")

    train_ppo(timesteps=args.timesteps, n_envs=args.n_envs, device=device)


if __name__ == "__main__":
    import argparse
    main()