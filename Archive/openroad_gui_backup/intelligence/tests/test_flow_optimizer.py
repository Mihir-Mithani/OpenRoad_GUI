"""Tests for state encoder and flow optimizer."""
import pytest
import numpy as np
from openroad_gui.intelligence.models.flow_optimizer import (
    StateEncoder,
    FlowState,
    FlowAction,
    FlowReward,
    DesignFeatures,
    StageFeatures,
    FlowStage,
    ActionSpace,
)


class TestStateEncoder:
    def test_encode_state(self):
        from openroad_gui.intelligence.models.flow_optimizer import FlowState, DesignFeatures, StageFeatures, FlowStage

        state = FlowState(
            design=DesignFeatures(
                num_instances=10000,
                num_nets=5000,
                num_sequential=5000,
                num_macros=10,
                macro_area_ratio=0.2,
                avg_fanout=4.0,
                max_fanout=100,
                logic_depth=20,
                target_freq_mhz=500.0,
                utilization_target=0.7,
                aspect_ratio=1.0,
                core_margin=4.0,
            ),
            current_stage=StageFeatures(
                stage=FlowStage.SYNTHESIS,
                current_wns_ns=-0.5,
                current_tns_ns=-100.0,
                current_area_um2=1000000.0,
                current_power_mw=1000.0,
                current_drc_violations=10,
                current_congestion_pct=50.0,
                placement_density=0.6,
                routing_congestion=0.5,
                macro_placement_quality=0.8,
                stage_attempt=1,
            ),
            stage_history=[],
        )

        encoder = StateEncoder()
        encoded = StateEncoder.encode(state)

        assert encoded.shape == (StateEncoder.STATE_DIM,)
        assert encoded.dtype == np.float32
        assert np.all(np.isfinite(encoded))
        assert np.all(encoded >= -10.0) and np.all(encoded <= 10.0)

    def test_encode_with_history(self):
        from openroad_gui.intelligence.models.flow_optimizer import FlowState, DesignFeatures, StageFeatures, FlowStage

        state = FlowState(
            design=DesignFeatures(
                num_instances=1000,
                num_nets=500,
                num_sequential=500,
            ),
            current_stage=StageFeatures(
                stage=FlowStage.ROUTING,
                current_wns_ns=-0.1,
                current_tns_ns=-10.0,
                current_area_um2=500000.0,
                current_power_mw=500.0,
                current_drc_violations=0,
                current_congestion_pct=30.0,
                placement_density=0.7,
                routing_congestion=0.4,
            ),
            stage_history=[
                StageFeatures(stage=FlowStage.SYNTHESIS, current_wns_ns=-1.0, current_tns_ns=-50.0),
                StageFeatures(stage=FlowStage.PLACEMENT, current_wns_ns=-0.5, current_tns_ns=-20.0),
            ],
        )

        encoded = StateEncoder.encode(state)
        assert encoded.shape == (StateEncoder.STATE_DIM,)


class TestFlowReward:
    def test_compute_reward_improvement(self):
        from openroad_gui.intelligence.models.flow_optimizer import FlowState, DesignFeatures, StageFeatures, FlowStage

        prev_state = FlowState(
            design=DesignFeatures(),
            current_stage=StageFeatures(
                stage=FlowStage.ROUTING,
                current_wns_ns=-1.0,
                current_tns_ns=-100.0,
                current_area_um2=1000000.0,
                current_power_mw=1000.0,
                current_drc_violations=10,
                current_congestion_pct=60.0,
            ),
        )

        curr_state = FlowState(
            design=DesignFeatures(),
            current_stage=StageFeatures(
                stage=FlowStage.ROUTING,
                current_wns_ns=0.1,  # Improved to positive
                current_tns_ns=-10.0,  # Improved
                current_area_um2=900000.0,  # Reduced
                current_power_mw=900.0,  # Reduced
                current_drc_violations=0,  # Fixed
                current_congestion_pct=30.0,  # Improved
            ),
        )

        action = np.zeros(16, dtype=np.float32)
        reward = FlowReward.compute(prev_state, curr_state, action, 300.0)

        # Should be positive (improvement)
        assert reward > 0
        assert reward > 5.0  # Should include timing closure bonus

    def test_compute_reward_degradation(self):
        from openroad_gui.intelligence.models.flow_optimizer import FlowState, DesignFeatures, StageFeatures, FlowStage

        prev_state = FlowState(
            design=DesignFeatures(),
            current_stage=StageFeatures(
                stage=FlowStage.ROUTING,
                current_wns_ns=0.1,
                current_tns_ns=0.0,
                current_area_um2=500000.0,
                current_power_mw=500.0,
                current_drc_violations=0,
                current_congestion_pct=30.0,
            ),
        )

        curr_state = FlowState(
            design=DesignFeatures(),
            current_stage=StageFeatures(
                stage=FlowStage.ROUTING,
                current_wns_ns=-1.0,  # Degraded
                current_tns_ns=-100.0,
                current_area_um2=1000000.0,  # Increased
                current_power_mw=1000.0,  # Increased
                current_drc_violations=50,  # New violations
                current_congestion_pct=90.0,  # Worsened
            ),
        )

        action = np.zeros(16, dtype=np.float32)
        reward = FlowReward.compute(prev_state, curr_state, action, 300.0)

        # Should be negative (degradation)
        assert reward < 0