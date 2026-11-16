"""RL State/Action space and reward design for OpenROAD flow optimization."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class FlowStage(Enum):
    """OpenROAD flow stages in order."""
    SYNTHESIS = "synthesis"
    FLOORPLAN = "floorplan"
    PLACEMENT = "placement"
    CTS = "cts"
    ROUTING = "routing"
    SIGN_OFF = "signoff"


@dataclass
class DesignFeatures:
    """Static design characteristics (extracted once per design)."""

    # Design complexity
    num_instances: int = 0
    num_nets: int = 0
    num_sequential: int = 0
    num_combinational: int = 0
    num_ports: int = 0
    num_clocks: int = 0
    num_macros: int = 0
    macro_area_ratio: float = 0.0

    # Netlist characteristics
    avg_fanout: float = 0.0
    max_fanout: int = 0
    logic_depth: int = 0
    seq_to_comb_ratio: float = 0.0

    # Constraints
    target_freq_mhz: float = 0.0
    utilization_target: float = 0.0
    aspect_ratio: float = 1.0
    core_margin: float = 0.0

    # Platform (for differentiation)
    platform: str = "sky130hd"


@dataclass
class StageFeatures:
    """Dynamic stage-specific features (updated per stage)."""
    stage: FlowStage = FlowStage.SYNTHESIS

    # Current PPA metrics (from previous runs or estimates)
    current_wns_ns: float = 0.0
    current_tns_ns: float = 0.0
    current_area_um2: float = 0.0
    current_power_mw: float = 0.0
    current_drc_violations: int = 0
    current_congestion_pct: float = 0.0

    # Resource utilization
    placement_density: float = 0.0
    routing_congestion: float = 0.0
    macro_placement_quality: float = 0.0

    # Historical context
    stage_attempt: int = 0
    previous_params: Dict = field(default_factory=dict)


@dataclass
class FlowState:
    """Complete RL state representation."""
    design: DesignFeatures
    current_stage: StageFeatures
    stage_history: List[StageFeatures] = field(default_factory=list)
    global_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class FlowAction:
    """Discrete action space for flow optimization."""

    # Synthesis parameters
    synth_strategy: int = 1          # 0=area, 1=balanced, 2=timing, 3=power
    synth_effort: int = 1            # 0=low, 1=medium, 2=high, 3=extreme
    retime: bool = False
    resynth: bool = False

    # Floorplan/Placement
    placement_density: float = 0.6   # 0.4 - 0.8
    placement_effort: int = 1        # 0=low, 1=medium, 2=high, 3=extreme
    macro_placement: int = 0         # 0=auto, 1=manual, 2=hierarchical

    # CTS
    cts_skew_target: float = 0.05    # 0.01 - 0.1 ns
    cts_buffer_type: int = 0         # Buffer cell selection
    cts_clustering: int = 0          # Clustering algorithm

    # Routing
    routing_layers: int = 6          # 4-8 layers
    routing_effort: int = 1          # 0=low, 1=medium, 2=high, 3=extreme
    detour_scale: float = 1.0        # Detour scale factor

    # Sign-off
    signoff_effort: int = 1          # 0=fast, 1=standard, 2=extreme


@dataclass
class FlowReward:
    """Multi-objective reward function for flow optimization."""

    # Weights for multi-objective reward (sum to 1.0)
    WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "wns": 0.30,
        "tns": 0.15,
        "area": 0.15,
        "power": 0.10,
        "drc_clean": 0.15,
        "congestion": 0.10,
        "runtime": 0.05,
    })

    @staticmethod
    def compute(prev_state: 'FlowState', curr_state: 'FlowState',
                action: np.ndarray, runtime_sec: float) -> float:
        """Compute multi-objective reward based on state transition."""

        reward = 0.0
        prev = prev_state.current_stage
        curr = curr_state.current_stage

        # Timing rewards: WNS/TNS higher (less negative) is better
        # So improvement = curr - prev (positive when improving)
        wns_improvement = curr.current_wns_ns - prev.current_wns_ns
        reward += 0.30 * np.tanh(wns_improvement / 0.5)

        tns_improvement = curr.current_tns_ns - prev.current_tns_ns
        reward += 0.15 * np.tanh(tns_improvement / 10.0)

        # Area efficiency: lower is better
        if prev.current_area_um2 > 0:
            area_change = (prev.current_area_um2 - curr.current_area_um2) / prev.current_area_um2
            reward += 0.15 * np.tanh(area_change * 10)

        # Power: lower is better
        if prev.current_power_mw > 0:
            power_change = (prev.current_power_mw - curr.current_power_mw) / prev.current_power_mw
            reward += 0.10 * np.tanh(power_change * 10)

        # DRC clean bonus: fewer violations is better
        drc_fixed = prev.current_drc_violations - curr.current_drc_violations
        if drc_fixed > 0:
            reward += 0.15 * min(drc_fixed / 100.0, 1.0)

        # Congestion: lower is better
        cong_improvement = prev.current_congestion_pct - curr.current_congestion_pct
        reward += 0.10 * np.tanh(cong_improvement / 10.0)

        # Runtime penalty
        reward -= 0.05 * min(runtime_sec / 3600.0, 1.0)

        # Episode termination bonuses
        if curr.current_wns_ns >= 0:
            reward += 10.0  # Timing closure bonus
        if curr.current_drc_violations == 0:
            reward += 5.0   # DRC clean bonus

        return float(np.clip(reward, -50.0, 50.0))


class StateEncoder:
    """Encode FlowState into fixed-size numpy array for RL."""

    STATE_DIM = 128  # Match trained model's observation space

    @staticmethod
    def encode(state: FlowState) -> np.ndarray:
        """Encode FlowState into fixed-size vector."""
        vec = np.zeros(StateEncoder.STATE_DIM, dtype=np.float32)
        idx = 0

        # Design features (12 dims)
        d = state.design
        design_vec = [
            np.log1p(d.num_instances) / 20.0,
            np.log1p(d.num_nets) / 20.0,
            d.num_sequential / max(1, d.num_instances),
            d.num_macros / max(1, d.num_instances),
            d.macro_area_ratio,
            d.avg_fanout / 100.0,
            min(d.max_fanout / 1000.0, 1.0),
            d.logic_depth / 100.0,
            d.target_freq_mhz / 1000.0,
            d.utilization_target / 100.0,
            d.aspect_ratio / 4.0,
            d.core_margin / 100.0,
        ]
        vec[idx:idx+len(design_vec)] = design_vec
        idx += len(design_vec)

        # Platform one-hot (4 dims)
        platform_map = {'sky130hd': 0, 'asap7': 1, 'nangate45': 2, 'gf180': 3}
        platform_onehot = [0.0, 0.0, 0.0, 0.0]
        plat = getattr(state.design, 'platform', 'sky130hd')
        if plat in platform_map:
            platform_onehot[platform_map[plat]] = 1.0
        vec[idx:idx+4] = platform_onehot
        idx += 4

        # Current stage features (24 dims)
        stage_vec = [
            state.current_stage.current_wns_ns / 10.0,
            np.clip(state.current_stage.current_tns_ns / 1000.0, -1, 1),
            np.log1p(state.current_stage.current_area_um2) / 20.0,
            np.log1p(state.current_stage.current_power_mw) / 20.0,
            min(state.current_stage.current_drc_violations / 1000.0, 1.0),
            state.current_stage.current_congestion_pct / 100.0,
            state.current_stage.placement_density,
            state.current_stage.routing_congestion,
            state.current_stage.macro_placement_quality,
            state.current_stage.stage_attempt / 10.0,
        ]
        # Pad stage_vec to 14 dims
        stage_vec = stage_vec + [0.0] * (14 - len(stage_vec))
        vec[idx:idx+len(stage_vec)] = stage_vec
        idx += len(stage_vec)

        # Stage history (last 3 stages x 6 dims = 18 dims)
        for hist in state.stage_history[-3:]:
            hist_vec = [
                hist.current_wns_ns / 10.0,
                np.clip(hist.current_tns_ns / 1000.0, -1, 1),
                hist.current_drc_violations / 1000.0,
                hist.current_congestion_pct / 100.0,
                hist.placement_density,
                hist.routing_congestion,
            ]
            vec[idx:idx+6] = hist_vec[:6]
            idx += 6

        # Remaining dims are zero-padded (already zeros from np.zeros)
        return np.clip(vec, -10.0, 10.0)


class ActionSpace:
    """Discrete action space for flow optimization."""

    PARAM_RANGES = {
        "synth_strategy": (0, 3),
        "synth_effort": (0, 3),
        "retime": (0, 1),
        "resynth": (0, 1),
        "placement_density": (0.4, 0.8),
        "placement_effort": (0, 3),
        "macro_placement": (0, 2),
        "cts_skew_target": (0.01, 0.1),
        "cts_buffer_type": (0, 3),
        "cts_clustering": (0, 2),
        "routing_layers": (4, 8),
        "routing_effort": (0, 3),
        "detour_scale": (0.5, 2.0),
        "signoff_effort": (0, 2),
    }

    @staticmethod
    def clip_action(action: np.ndarray) -> np.ndarray:
        """Clip action to valid ranges."""
        # Implementation would clip each dimension to valid range
        return np.clip(action, -1.0, 1.0)

    @staticmethod
    def random_action() -> np.ndarray:
        """Generate random valid action for exploration."""
        action = np.zeros(16, dtype=np.float32)
        # Sample from valid ranges
        return action


class FlowOptimizationEngine:
    """Main RL-based flow optimization engine (architecture only - no training)."""

    def __init__(self, model_path: Optional[str] = None):
        self.encoder = StateEncoder()
        self.action_space = ActionSpace()
        self.reward_fn = FlowReward()
        self.model_path = model_path
        self._model = None  # Placeholder for trained model

    def encode_state(self, state: FlowState) -> np.ndarray:
        """Encode state for model input."""
        return self.encoder.encode(state)

    def decode_action(self, action_vec: np.ndarray) -> FlowAction:
        """Decode action vector to FlowAction.

        Action vector (14 dims) matches FlowAction fields:
        0: synth_strategy (0-3), 1: synth_effort (0-3), 2: retime (0-1), 3: resynth (0-1)
        4: placement_density (0.4-0.8), 5: placement_effort (0-3), 6: macro_placement (0-2)
        7: cts_skew_target (0.01-0.1), 8: cts_buffer_type (0-3), 9: cts_clustering (0-2)
        10: routing_layers (4-8), 11: routing_effort (0-3), 12: detour_scale (0.5-2.0)
        13: signoff_effort (0-2)
        """
        # Clip to valid bounds
        action_vec = np.clip(action_vec,
            [0, 0, 0, 0, 0.4, 0, 0, 0.01, 0, 0, 4, 0, 0.5, 0],
            [3, 3, 1, 1, 0.8, 3, 2, 0.1, 3, 2, 8, 3, 2.0, 2]
        )

        return FlowAction(
            synth_strategy=int(np.round(action_vec[0])),
            synth_effort=int(np.round(action_vec[1])),
            retime=bool(action_vec[2] > 0.5),
            resynth=bool(action_vec[3] > 0.5),
            placement_density=float(action_vec[4]),
            placement_effort=int(np.round(action_vec[5])),
            macro_placement=int(np.round(action_vec[6])),
            cts_skew_target=float(action_vec[7]),
            cts_buffer_type=int(np.round(action_vec[8])),
            cts_clustering=int(np.round(action_vec[9])),
            routing_layers=int(np.round(action_vec[10])),
            routing_effort=int(np.round(action_vec[11])),
            detour_scale=float(action_vec[12]),
            signoff_effort=int(np.round(action_vec[13])),
        )

    def compute_reward(self, prev_state: FlowState, curr_state: FlowState,
                       action: np.ndarray, runtime_sec: float) -> float:
        """Compute reward for state transition."""
        return FlowReward.compute(prev_state, self._current_state, action, 0.0)

    def _load_model(self):
        """Lazy load PPO model from model_path."""
        if self._model is None and self.model_path:
            try:
                from stable_baselines3 import PPO
                self._model = PPO.load(self.model_path)
                print(f"✅ Loaded PPO model from {self.model_path}")
            except Exception as e:
                print(f"⚠️ Failed to load PPO model: {e}")
                self._model = None

    def _heuristic_action(self, state: FlowState) -> FlowAction:
        """Platform-specific heuristic defaults from successful ORFS runs."""
        plat = getattr(state.design, 'platform', 'sky130hd')
        inst = state.design.num_instances

        heuristics = {
            'sky130hd': dict(
                synth_strategy=2, synth_effort=2, placement_density=0.45,
                placement_effort=2, routing_layers=6, routing_effort=2,
                cts_skew_target=0.03, detour_scale=1.5, signoff_effort=1
            ),
            'asap7': dict(
                synth_strategy=1, synth_effort=2, placement_density=0.55,
                placement_effort=2, routing_layers=8, routing_effort=2,
                cts_skew_target=0.05, detour_scale=1.2, signoff_effort=1
            ),
            'nangate45': dict(
                synth_strategy=1, synth_effort=1, placement_density=0.6,
                placement_effort=1, routing_layers=6, routing_effort=1,
                cts_skew_target=0.05, detour_scale=1.0, signoff_effort=1
            ),
            'gf180': dict(
                synth_strategy=2, synth_effort=2, placement_density=0.5,
                placement_effort=2, routing_layers=8, routing_effort=2,
                cts_skew_target=0.04, detour_scale=1.3, signoff_effort=1
            ),
        }

        h = heuristics.get(plat, heuristics['sky130hd'])

        # Adjust for design size
        if inst > 20000:
            h['placement_effort'] = min(h['placement_effort'] + 1, 3)
            h['routing_effort'] = min(h['routing_effort'] + 1, 3)

        return FlowAction(
            synth_strategy=h['synth_strategy'],
            synth_effort=h['synth_effort'],
            retime=False, resynth=False,
            placement_density=h['placement_density'],
            placement_effort=h['placement_effort'],
            macro_placement=0,
            cts_skew_target=h['cts_skew_target'],
            cts_buffer_type=0, cts_clustering=0,
            routing_layers=h['routing_layers'],
            routing_effort=h['routing_effort'],
            detour_scale=h['detour_scale'],
            signoff_effort=h['signoff_effort'],
        )

    def predict_action(self, state: FlowState) -> FlowAction:
        """Hybrid: heuristic base + PPO residual adjustment."""
        # Get heuristic base action
        base = self._heuristic_action(state)

        if self._model is None:
            self._load_model()
        if self._model is None:
            return base

        # PPO predicts RESIDUAL adjustment to heuristic
        obs = self.encode_state(state)
        residual, _ = self._model.predict(obs, deterministic=True)

        # Decode residual
        residual_action = self.decode_action(residual)

        # Combine: heuristic + small PPO residual adjustment (clipped)
        return FlowAction(
            synth_strategy=base.synth_strategy,  # Keep heuristic discrete
            synth_effort=base.synth_effort,
            retime=base.retime or residual_action.retime,
            resynth=base.resynth or residual_action.resynth,
            placement_density=np.clip(base.placement_density + 0.1*(residual_action.placement_density-0.6), 0.4, 0.8),
            placement_effort=base.placement_effort,
            macro_placement=base.macro_placement,
            cts_skew_target=np.clip(base.cts_skew_target + 0.1*(residual_action.cts_skew_target-0.05), 0.01, 0.1),
            cts_buffer_type=base.cts_buffer_type,
            cts_clustering=base.cts_clustering,
            routing_layers=base.routing_layers,
            routing_effort=base.routing_effort,
            detour_scale=np.clip(base.detour_scale + 0.2*(residual_action.detour_scale-1.0), 0.5, 2.0),
            signoff_effort=base.signoff_effort,
        )

    def _default_action(self) -> FlowAction:
        """Return default/heuristic action when no model available."""
        return FlowAction(
            synth_strategy=1,  # balanced
            synth_effort=1,    # medium
            retime=False,
            resynth=False,
            placement_density=0.6,
            placement_effort=1,
            macro_placement=0,
            cts_skew_target=0.05,
            cts_buffer_type=0,
            cts_clustering=0,
            routing_layers=6,
            routing_effort=1,
            detour_scale=1.0,
            signoff_effort=1,
        )


# Import numpy at module level for FlowReward
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum