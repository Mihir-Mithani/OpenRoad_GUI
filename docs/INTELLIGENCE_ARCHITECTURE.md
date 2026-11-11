# OpenROAD Flow GUI - Intelligence Module Architecture

## Overview

The `intelligence/` module adds AI/ML capabilities to the OpenROAD Flow GUI for RTL-to-GDSII flow optimization. This module provides:

- **Data Pipeline**: Collection and feature engineering from historical OpenROAD runs
- **RL-Based Flow Optimization**: RL-based flow parameter optimization
- **Failure Prediction**: Predictive failure detection for flow stages
- **Design Space Exploration**: Automated design space exploration
- **ONNX Export/Inference**: Model deployment for M1 inference

## Architecture

```
intelligence/
├── models/                 # ML model definitions
│   ├── flow_optimizer.py   # RL-based flow optimization (state/action/reward)
│   └── failure_predictor.py # Failure prediction architecture
├── data/                   # Data pipeline
│   ├── collector.py        # Historical data collector
│   ├── features.py         # Feature engineering (Polars streaming)
│   └── parser.py           # Log/report parsing
├── training/               # Training pipeline (cloud-ready)
│   ├── pipeline.py         # Training orchestration
│   ├── trainer.py          # PyTorch trainer with M1 MPS support
│   └── data_loader.py      # Data loading utilities
├── utils/                  # Utilities
│   ├── onnx_export.py      # ONNX export/import
│   └── metrics.py          # Evaluation metrics
└── tests/                  # Unit tests
```

## Sprint 1: Data Foundation + Architecture (Complete)

### Completed Components

1. **Data Pipeline** (`intelligence/data/`)
   - `collector.py`: Historical data collector from OpenROAD runs
   - `features.py`: Feature engineering with Polars streaming
   - `parser.py`: Log/report parsing utilities

2. **Model Architecture** (Design Complete)
   - `flow_optimizer.py`: RL state/action/reward design
   - `failure_predictor.py`: Failure prediction architecture

3. **Utilities**
   - `onnx_export.py`: ONNX export/import utilities
   - `metrics.py`: Evaluation metrics

3. **Tests** (All passing)
   - `test_data_collector.py`
   - `test_features.py`
   - `test_flow_optimizer.py`

## Sprint 2: Model Training (Cloud Required)

### Planned Components

1. **RL Training Pipeline** (`training/`)
   - PPO-based actor-critic for flow optimization
   - M1 MPS-compatible trainer
   - ONNX export for M1 deployment

2. **Failure Predictor Training**
   - Binary classifier + anomaly detector
   - GNN-based failure prediction

3. **Design Space Exploration**
   - Surrogate modeling
   - Pareto optimization

## Usage

### Local Development (8GB M1 Air Compatible)

```bash
# 1. Collect historical data
python -m intelligence.data.collector --results-dir ~/openroad/results --output data/training_runs.db

# 2. Feature engineering
python -m intelligence.data.features --input data/training_runs.db --output data/features.parquet

# 3. Validate features
python -m intelligence.data.validate --input data/features.parquet

# 4. Run tests
pytest intelligence/tests/ -v
```

### Cloud Training (Deferred to Sprint 2)

```yaml
# training_plan.yaml
model: rl_actor_critic
cloud: true
providers:
  - colab_pro: 100hrs T4/month ($10)
  - kaggle: 30hrs/week free
  - lambda_labs: $0.50/hr A100
export_format: onnx
deployment_target: m1_mps
```

## Architecture Decisions

### State/Action Space Design

**State (128-dim):**
- Design features (12 dims): instances, nets, macros, utilization, frequency, etc.
- Current stage (24 dims): WNS, TNS, area, power, DRC, congestion, density
- Stage history (48 dims): Last 3 stages × 6 metrics

**Action Space (16-dim):**
- Synthesis: strategy, effort, retime, resynth
- Placement: density, effort, macro placement
- CTS: skew target, buffer type, clustering
- Routing: layers, effort, detour scale
- Sign-off: effort level

### Reward Function (Multi-objective)

| Objective | Weight | Metric |
|-----------|--------|--------|
| WNS | 0.30 | Timing closure |
| TNS | 0.15 | Total negative slack |
| Area | 0.15 | Area efficiency |
| Power | 0.10 | Power consumption |
| DRC Clean | 0.15 | DRC violations |
| Congestion | 0.10 | Routing congestion |
| Runtime | 0.05 | Runtime penalty |

### Reward Function
```python
reward = 0.30 * tanh(wns_improvement/0.5) +
         0.15 * tanh(tns_improvement/10.0) +
         0.15 * tanh(area_improvement*10) +
         0.10 * tanh(power_improvement*10) +
         0.15 * drc_fixed_bonus +
         0.10 * tanh(cong_improvement/10) -
         0.05 * min(runtime_hours, 1.0) +
         timing_closure_bonus + drc_clean_bonus
```

## Sprint 2 Roadmap (Cloud Required)

### Week 1-2: RL Training Pipeline
- [ ] PPO Actor-Critic implementation
- [ ] Experience replay buffer
- [ ] M1 MPS-compatible trainer
- [ ] ONNX export pipeline

### Week 3-4: Failure Predictor
- [ ] Binary classifier training
- [ ] Anomaly detection integration
- [ ] GNN-based failure prediction

### Week 5-6: Design Space Exploration
- [ ] Surrogate modeling
- [ ] Pareto optimization
- [ ] Multi-objective optimization

### Week 7-8: Integration & Deployment
- [ ] ONNX export pipeline
- [ ] M1 MPS inference optimization
- [ ] GUI integration

## Deployment

### Model Deployment to M1
```python
# Export to ONNX
exporter = ONNXExporter()
exporter.export(model, input_shape=(1, 128), output_path="model.onnx")

# Deploy to M1 GUI
engine = ONNXInferenceEngine("model.onnx")
predictions = engine.predict(input_data)
```

## Testing

```bash
# Run all tests
pytest intelligence/tests/ -v

# Specific test modules
pytest intelligence/tests/test_data_collector.py -v
pytest intelligence/tests/test_features.py -v
pytest intelligence/tests/test_flow_optimizer.py -v
```

## Dependencies

```toml
# Added to requirements.txt
torch>=2.0.0
onnx>=1.14.0
onnxruntime>=1.15.0
polars>=0.19.0
scikit-learn>=1.3.0
```

## Next Steps

1. **Sprint 2**: Cloud training implementation
2. **Sprint 3**: Advanced analytics & DSE
3. **Sprint 4**: GUI integration & deployment