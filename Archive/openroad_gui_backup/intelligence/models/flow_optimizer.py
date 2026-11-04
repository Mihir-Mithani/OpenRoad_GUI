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

    STATE_DIM = 128

    @staticmethod
    def encode(state: FlowState) -> np.ndarray:
        """Encode FlowState into fixed-size vector."""
        vec = np.zeros(StateEncoder.STATE_DIM, dtype=np.float32)
        idx = 0

        # Design features (12 dims)
        design_vec = [
            np.log1p(state.design.num_instances) / 20.0,
            np.log1p(state.design.num_nets) / 20.0,
            state.design.num_sequential / max(1, state.design.num_instances),
            state.design.num_macros / max(1, state.design.num_instances),
            state.design.macro_area_ratio,
            state.design.avg_fanout / 100.0,
            min(state.design.max_fanout / 1000.0, 1.0),
            state.design.logic_depth / 100.0,
            state.design.target_freq_mhz / 1000.0,
            state.design.utilization_target,
            state.design.aspect_ratio / 4.0,
            state.design.core_margin / 100.0,
        ]
        vec[idx:idx+len(design_vec)] = design_vec
        idx += len(design_vec)

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
        """Decode action vector to FlowAction."""
        # Decode action vector to FlowAction
        return FlowAction()

    def compute_reward(self, prev_state: FlowState, curr_state: FlowState,
                       action: np.ndarray, runtime_sec: float) -> float:
        """Compute reward for state transition."""
        return FlowReward.compute(prev_state, self._current_state, action, 0.0)

    def predict_action(self, state: FlowState) -> FlowAction:
        """Predict optimal action for given state (uses trained model)."""
        if self._model is None:
            # Return default/heuristic action if no model loaded
            return self._default_action()
        # Would use self._model.predict() with encoded state
        return self._default_action()

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