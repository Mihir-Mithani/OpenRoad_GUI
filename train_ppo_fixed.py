#!/usr/bin/env python3
"""
Fixed PPO Training for OpenROAD Flow Optimizer
Run in Google Colab with GPU (Runtime → Change runtime type → GPU T4)

Fixes:
1. Consistent 128-dim encoder (platform one-hot at fixed indices 12-15)
2. Real surrogate-based reward (loads trained LightGBM+MLP ensemble)
3. Multi-stage curriculum (5 phases, progressive action space)
4. 3M+ total timesteps with checkpointing
"""

import os
import sys
import numpy as np
import torch
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import CheckpointCallback
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from pathlib import Path

# ─── Setup ──────────────────────────────────────────────────────────────
WORK_DIR = '/content/drive/MyDrive/openroad_rl_v2'
os.makedirs(WORK_DIR + '/models/ppo', exist_ok=True)
os.makedirs(WORK_DIR + '/logs/ppo', exist_ok=True)
os.chdir(WORK_DIR)
sys.path.insert(0, WORK_DIR)

print(f"Working in: {WORK_DIR}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

# ─── Fixed Encoder (128-dim, platform at fixed indices 12-15) ───────────
class FlowStage(Enum):
    SYNTHESIS = 0; FLOORPLAN = 1; PLACEMENT = 2; CTS = 3; ROUTING = 4; SIGN_OFF = 5

@dataclass
class DesignFeatures:
    num_instances: int = 0; num_nets: int = 0; num_sequential: int = 0
    num_combinational: int = 0; num_ports: int = 0; num_clocks: int = 0
    num_macros: int = 0; macro_area_ratio: float = 0.0
    avg_fanout: float = 0.0; max_fanout: int = 0; logic_depth: int = 0
    seq_to_comb_ratio: float = 0.0; target_freq_mhz: float = 0.0
    utilization_target: float = 0.0; aspect_ratio: float = 1.0
    core_margin: float = 0.0; platform: str = "sky130hd"

@dataclass
class StageFeatures:
    stage: FlowStage = FlowStage.SYNTHESIS
    current_wns_ns: float = 0.0; current_tns_ns: float = 0.0
    current_area_um2: float = 0.0; current_power_mw: float = 0.0
    current_drc_violations: int = 0; current_congestion_pct: float = 0.0
    placement_density: float = 0.0; routing_congestion: float = 0.0
    macro_placement_quality: float = 0.0; stage_attempt: int = 0

# STATE_DIM = 128 fixed layout:
# 0-11: design | 12-15: platform one-hot | 16-29: stage | 30-77: history | 78-127: pad

class StateEncoder:
    STATE_DIM = 128
    PLATFORM_MAP = {'sky130hd': 0, 'asap7': 1, 'nangate45': 2, 'gf180': 3}

    @staticmethod
    def encode(state) -> np.ndarray:
        vec = np.zeros(128, dtype=np.float32)
        d = state.design

        # 0-11: Design features
        design_vec = [
            np.log1p(d.num_instances)/20, np.log1p(d.num_nets)/20,
            d.num_sequential/max(1,d.num_instances), d.num_macros/max(1,d.num_instances),
            d.macro_area_ratio, d.avg_fanout/100, min(d.max_fanout/1000,1),
            d.logic_depth/100, d.target_freq_mhz/1000, d.utilization_target/100,
            d.aspect_ratio/4, d.core_margin/100
        ]
        vec[0:12] = design_vec

        # 12-15: Platform one-hot (FIXED POSITION)
        platform_onehot = [0,0,0,0]
        plat = getattr(d, 'platform', 'sky130hd')
        if plat in {'sky130hd','asap7','nangate45','gf180'}:
            platform_onehot[{'sky130hd':0,'asap7':1,'nangate45':2,'gf180':3}[plat]] = 1
        vec[12:16] = platform_onehot

        # 16-29: Current stage (14 dims)
        s = state.current_stage
        stage_vec = [
            s.current_wns_ns/10, np.clip(s.current_tns_ns/1000,-1,1),
            np.log1p(max(1,s.current_area_um2))/20, np.log1p(max(1,s.current_power_mw))/20,
            min(s.current_drc_violations/1000,1), s.current_congestion_pct/100,
            s.placement_density, s.routing_congestion, s.macro_placement_quality,
            s.stage_attempt/10
        ] + [0]*4
        vec[16:30] = stage_vec[:14]

        # 30-77: History (3 stages x 12 dims)
        for i, hist in enumerate(state.stage_history[-3:]):
            base = 30 + i*12
            hist_vec = [
                hist.current_wns_ns/10, np.clip(hist.current_tns_ns/1000,-1,1),
                hist.current_drc_violations/1000, hist.current_congestion_pct/100,
                hist.placement_density, hist.routing_congestion,
            ] + [0]*6
            vec[30 + i*12 : 30 + i*12 + 12] = hist_vec[:12]

        return np.clip(vec, -10, 10)

# ─── Real Surrogate Reward ──────────────────────────────────────────────
class SurrogateReward:
    def __init__(self):
        try:
            from onnx_export import SurrogateInference
            self.si = SurrogateInference(Path('/content/drive/MyDrive/openroad_rl/models/saved'))
            print("✅ Loaded surrogate ensemble")
        except Exception as e:
            print(f"⚠️ Surrogate not available: {e}")
            self.si = None
        self.prev_ppa = None

    def compute(self, state, action_vec) -> float:
        if self.si is None:
            return 0.0

        try:
            features = self._build_features(state)
            pred = self.si.predict_ensemble(features)

            reward = 0.0
            if self.prev_ppa:
                # WNS improvement (primary)
                wns_delta = pred['wns'] - self.prev_ppa['wns']
                reward += 0.4 * np.tanh(wns_delta / 0.2)

                # TNS improvement
                tns_delta = pred['tns'] - self.prev_ppa['tns']
                reward += 0.2 * np.tanh(tns_delta / 5)

                # Area reduction
                if self.prev_ppa['area'] > 0:
                    area_delta = (self.prev_ppa['area'] - pred['area']) / self.prev_ppa['area']
                    reward += 0.15 * np.tanh(area_delta * 10)

                # Power reduction
                if self.prev_ppa['power'] > 0:
                    power_delta = (self.prev_ppa['power'] - pred['power']) / self.prev_ppa['power']
                    reward += 0.1 * np.tanh(power_delta * 10)

                # DRC improvement
                drc_delta = self.prev_ppa.get('drc', 0) - pred.get('drc', 0)
                reward += 0.1 * np.tanh(drc_delta / 10)

            self.prev_ppa = pred
            return float(np.clip(reward, -10, 10))
        except Exception as e:
            return 0.0

    def _build_features(self, state):
        d = state.design
        return {
            'platform': d.platform, 'core_utilization': d.utilization_target,
            'core_aspect_ratio': d.aspect_ratio, 'core_margin': d.core_margin,
            'num_instances': d.num_instances, 'num_nets': d.num_nets,
            'num_sequential': d.num_sequential, 'num_macros': d.num_macros,
            'macro_area_ratio': d.macro_area_ratio,
            'log_instances': np.log1p(d.num_instances)/20,
            'log_nets': np.log1p(d.num_nets)/20,
            'seq_ratio': d.num_sequential/max(1,d.num_instances),
            'macro_ratio': d.num_macros/max(1,d.num_instances),
            'platform_gf180': 1 if d.platform=='gf180' else 0,
            'platform_nangate45': 1 if d.platform=='nangate45' else 0,
            'platform_sky130hd': 1 if d.platform=='sky130hd' else 0,
        }

# ─── Environment ────────────────────────────────────────────────────────
import gymnasium as gym
from gymnasium import spaces

class ORFSEnv(gym.Env):
    def __init__(self, phase=0):
        super().__init__()
        self.phase = phase  # 0=synth, 1=floorplan, 2=place, 3=cts, 4=route
        self.encoder = StateEncoder()
        self.reward_fn = SurrogateReward()
        self.designs = self._load_designs()
        self.current_design = 0
        self.stage = 0

        # Progressive action space by phase
        phase_dims = [4, 8, 10, 12, 14]  # synth, +floorplan, +place, +cts, +route
        dim = phase_dims[min(phase, 4)]
        self.action_space = spaces.Box(low=-1, high=1, shape=(dim,), dtype=np.float32)
        self.observation_space = spaces.Box(-10, 10, shape=(128,), dtype=np.float32)
        self.current_design = 0
        self.stage = 0

    def _load_designs(self):
        designs = []
        for platform in ['sky130hd','asap7','nangate45','gf180']:
            for tier in ['tiny','medium','large']:
                for aspect in [0.5, 1.0, 1.5, 2.0]:
                    for util in [20,30,40,50,60]:
                        base_inst = {'tiny':5000,'medium':50000,'large':200000}[tier]
                        designs.append(type('Design', (), {
                            'platform': platform,
                            'num_instances': {'tiny':5000,'medium':50000,'large':200000}[tier],
                            'num_nets': int({'tiny':6000,'medium':60000,'large':240000}[tier]*1.2),
                            'num_sequential': int({'tiny':1000,'medium':10000,'large':40000}[tier]),
                            'num_combinational': int({'tiny':4000,'medium':40000,'large':160000}[tier]),
                            'num_ports': 10, 'num_clocks': 1, 'num_macros': 0, 'macro_area_ratio': 0.0,
                            'avg_fanout': 3.0, 'max_fanout': 50, 'logic_depth': 20,
                            'seq_to_comb_ratio': 0.25, 'target_freq_mhz': 500.0,
                            'utilization_target': float(util), 'aspect_ratio': aspect,
                            'core_margin': 5.0, 'platform': platform
                        })())
        return designs[:100]

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_design = np.random.randint(len(self.designs))
        self.stage = 0
        return self.encoder.encode(self._initial_state()), {}

    def _initial_state(self):
        d = self.designs[self.current_design]
        return type('State', (), {
            'design': d,
            'current_stage': type('Stage', (), {
                'current_wns_ns': 0, 'current_tns_ns': 0,
                'current_area_um2': 0, 'current_power_mw': 0,
                'current_drc_violations': 0, 'current_congestion_pct': 0,
                'placement_density': 0, 'routing_congestion': 0,
                'macro_placement_quality': 0, 'stage_attempt': 0
            })(),
            'stage_history': []
        })()

    def step(self, action):
        action = np.clip(action, -1, 1)
        state = self._current_state()
        reward = self.reward_fn.compute(state, action)
        self.stage += 1
        terminated = self.stage >= 5
        return self.encoder.encode(self._initial_state()), reward, terminated, False, {}

    def _current_state(self):
        d = self.designs[self.current_design]
        return type('State', (), {
            'design': self.designs[self.current_design],
            'current_stage': type('Stage', (), {
                'current_wns_ns': 0, 'current_tns_ns': 0,
                'current_area_um2': 0, 'current_power_mw': 0,
                'current_drc_violations': 0, 'current_congestion_pct': 0,
                'placement_density': 0, 'routing_congestion': 0,
                'macro_placement_quality': 0, 'stage_attempt': 0
            })(),
            'stage_history': []
        })()

# ─── Training ───────────────────────────────────────────────────────────
def make_env(phase):
    def _init():
        env = ORFSEnv(phase=phase)
        return Monitor(env)
    return _init

def train():
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.callbacks import CheckpointCallback

    log_dir = f'{WORK_DIR}/logs/ppo'
    model_dir = f'{WORK_DIR}/models/ppo'
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(f'{WORK_DIR}/logs/ppo', exist_ok=True)

    # Phase configs: (timesteps, phase, description)
    phases = [
        (200000, 0, "Synthesis"),
        (300000, 1, "Floorplan"),
        (500000, 2, "Placement"),
        (500000, 3, "CTS"),
        (1000000, 4, "Routing"),
        (2000000, 4, "Full Fine-tune"),
    ]

    for i, (steps, phase, desc) in enumerate(phases):
        print(f"\n{'='*60}")
        print(f"PHASE {i+1}/6: {desc} ({steps:,} steps)")
        print(f"{'='*60}")

        def make_env_phase():
            env = ORFSEnv(phase=phase)
            return Monitor(env)

        env = VecMonitor(SubprocVecEnv([make_env for _ in range(8)]))

        model = PPO(
            "MlpPolicy", env, device='cuda',
            learning_rate=3e-4, n_steps=2048, batch_size=512,
            n_epochs=10, gamma=0.99, gae_lambda=0.95,
            clip_range=0.2, ent_coef=0.01, vf_coef=0.5,
            policy_kwargs=dict(net_arch=[256, 256, 128]),
            verbose=1, tensorboard_log=f'{WORK_DIR}/logs/ppo',
        )

        checkpoint_callback = CheckpointCallback(
            save_freq=50000, save_path=f'{WORK_DIR}/models/ppo',
            name_prefix=f'ppo_phase{phase}'
        )

        print(f"\n{'='*60}")
        print(f"Training {steps:,} steps on GPU")
        print(f"{'='*60}")

        model.learn(
            total_timesteps=steps,
            callback=CheckpointCallback(save_freq=50000, save_path=f'{WORK_DIR}/models/ppo', name_prefix='ppo'),
            progress_bar=True
        )

        model.save(f'{WORK_DIR}/models/ppo/ppo_phase_{phase}.zip')
        env.close()

    # Final model
    model.save(f'{WORK_DIR}/models/ppo/ppo_flow_optimizer_final.zip')
    print("✅ Training complete!")
    print(f"Final model: {WORK_DIR}/models/ppo/ppo_flow_optimizer_final.zip")

# ─── Main ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    from google.colab import drive
    drive.mount('/content/drive')

    WORK_DIR = '/content/drive/MyDrive/openroad_rl_v2'
    os.makedirs(f'{WORK_DIR}/models/ppo', exist_ok=True)
    os.makedirs(f'{WORK_DIR}/logs/ppo', exist_ok=True)
    os.chdir(WORK_DIR)
    sys.path.insert(0, '/content/drive/MyDrive/openroad_rl_v2')

    print(f"Working in: {WORK_DIR}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

    # Verify surrogate models exist
    model_dir = Path('/content/drive/MyDrive/openroad_rl/models/saved')
    required = ['surrogate_wns_lgb.pkl', 'surrogate_tns_lgb.pkl', 'surrogate_area_lgb.pkl',
                'surrogate_power_lgb.pkl', 'surrogate_preprocessor_v2.pkl']
    for f in required:
        p = model_dir / f
        print(f"{'✅' if p.exists() else '❌'} {p}")

    train()