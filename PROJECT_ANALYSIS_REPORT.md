# OpenRoad-GUI Project Analysis Report

## Executive Summary

**OpenRoad-GUI** is an AI-assisted EDA workstation for RTL-to-GDSII flow automation, built as a Python tkinter GUI that wraps **OpenROAD Flow Scripts (ORFS)**. The project integrates machine learning intelligence for PPA (Power, Performance, Area) prediction, failure prediction, and flow parameter optimization using reinforcement learning (PPO).

---

## 1. Project Architecture Overview

### 1.1 High-Level Structure

```
/OpenRoad GUI/
├── openroad_gui/                    # Main GUI package
│   ├── app.py                      # Main Tkinter application (2000+ lines)
│   ├── config.py                   # Persistent configuration management
│   ├── flow_runner.py              # Subprocess execution of ORFS flow stages
│   ├── theme.py                    # Dark/Light theme management
│   ├── viewers.py                  # GDS/KLayout/OpenROAD GUI integration
│   ├── signoff.py                  # DRC/LVS sign-off result parsing
│   ├── widgets/                    # Custom UI components
│   │   ├── sidebar.py
│   │   ├── preview_panel.py
│   │   ├── log_viewer.py
│   │   ├── flow_panel.py
│   │   ├── pipeline_row.py
│   │   ├── project_tree.py
│   │   ├── settings_dialog.py
│   ├── intelligence/               # ML/AI modules
│   │   ├── models/
│   │   │   ├── flow_optimizer.py   # RL state/action/reward for PPO
│   │   │   ├── failure_predictor.py # LightGBM failure classifier
│   │   │   ├── random_forest.py    # RF PPA + failure prediction
│   │   │   └── __init__.py
│   │   ├── training/               # Model training pipelines
│   │   │   ├── train_all_v2.py     # Unified pipeline (real data only)
│   │   │   ├── train_surrogate_v2.py # Regression ensemble (LGB + MLP)
│   │   │   ├── train_failure_predictor.py # LightGBM classifier
│   │   │   ├── train_rf.py         # Random Forest training
│   │   │   ├── train_flow_optimizer.py # PPO for Colab/GPU
│   │   │   ├── train_all.py        # Legacy pipeline
│   │   │   ├── pipeline.py         # Shared pipeline utilities
│   │   │   └── data_loader.py
│   │   ├── data/                   # Data collection & feature engineering
│   │   │   ├── collector.py        # Historical data from ORFS
│   │   │   ├── collect_real_data.py # Real ORFS data collector v2
│   │   │   ├── features.py         # Polars feature extraction
│   │   │   ├── parser.py           # Log/report parsing
│   │   │   └── __init__.py
│   │   ├── utils/
│   │   │   ├── onnx_export.py      # ONNX export + inference engine
│   │   │   └── metrics.py
│   │   └── __init__.py
├── dataset_genration/              # Synthetic dataset generation
├── intelligence/                   # Legacy/external intelligence
├── notebooks/                      # Jupyter analysis notebooks
├── plots/                          # Visualization outputs
├── config/                         # Configuration files
├── models/                         # Trained model artifacts
├── scripts/                        # Utility scripts
└── tests/                          # Unit tests
```

### 1.2 Core Components

| Component | Purpose | Key Technologies |
|-----------|---------|------------------|
| **GUI (app.py)** | Industrial EDA workstation | Tkinter, ttk, matplotlib, threading |
| **Flow Runner** | Execute ORFS make targets | subprocess, threading |
| **Data Collector** | Extract training data from ORFS runs | SQLite, JSON, regex parsing |
| **Surrogate Models** | PPA prediction (WNS, TNS, Area, Power) | LightGBM, PyTorch MLP, ONNX |
| **Failure Predictor** | Binary classification (timing, DRC) | LightGBM, calibrated thresholds |
| **Random Forest** | Alternative PPA + failure models | scikit-learn RF, Optuna tuning |
| **Flow Optimizer (PPO)** | RL-based flow parameter optimization | Stable-Baselines3, Gymnasium |
| **Feature Engineering** | Design → ML feature conversion | Polars, OneHotEncoder, StandardScaler |

---

## 2. Training Pipeline Analysis

### 2.1 Unified Pipeline (`train_all_v2.py`)

**Purpose**: End-to-end real-data-only training pipeline

```python
# Flow:
1. collect_real_data.py  →  ORFS designs/ → real_runs.{platform}.json  →  merged real_runs.json
2. train_surrogate_v2.py →  real_runs.json  →  LightGBM + MLP ensemble (5-fold GroupKFold CV)
3. train_failure_predictor.py → real_runs.json → LightGBM classifiers (5-fold Stratified CV)
4. train_flow_optimizer.py →  Run on Google Colab (GPU) → PPO agent
```

**Key Features**:
- Real data only (no synthetic)
- Multi-platform support: `asap7`, `sky130hd`, `nangate45`, `gf180`
- Configurable epochs, device (cpu/mps/cuda)
- Skip flags for collection/training phases
- Ensemble training with cross-validation
- Model checkpointing and logging

### 2.2 Surrogate Model Training (`train_surrogate_v2.py`)

**Targets**: Regression for 4 PPA metrics
- `wns` (Worst Negative Slack, ns) — clipped to [-500, 100]
- `tns` (Total Negative Slack, ns) — clipped to [-10000, 100]
- `area` (μm²) — log-transformed (`log1p`)
- `power` (mW) — log-transformed (`log1p`)

**Models**:
1. **LightGBM** (gradient boosting)
   - 500 rounds, early stopping (50)
   - Learning rate: 0.05, num_leaves: 63
   - Feature fraction: 0.8, bagging: 0.8
   - L1/L2 regularization

2. **PyTorch MLP** (neural network)
   - Architecture: Input → 256 → 128 → 64 → 1
   - BatchNorm + ReLU + Dropout(0.2)
   - AdamW optimizer, ReduceLROnPlateau scheduler
   - Early stopping (patience=20)

3. **Ensemble**: Simple average of LGB + MLP predictions

**Cross-Validation**: GroupKFold by `design_name` (5 folds)
- Prevents data leakage across same designs
- Retrains on full dataset after CV

**Features** (13 total):
- Categorical: `platform` (4), `core_aspect_ratio` (treated as categorical)
- Numeric: `core_utilization`, `core_margin`, `num_instances`, `num_nets`, `num_sequential`, `num_macros`, `macro_area_ratio`
- Engineered: `log_instances`, `log_nets`, `seq_ratio`, `macro_ratio`

### 2.3 Failure Predictor Training (`train_failure_predictor.py`)

**Targets**: Binary classification
- `timing_closure_bin` (WNS ≥ 0): ~30% positive rate
- `drc_clean_bin` (DRC violations = 0): ~85% positive rate

**Model**: LightGBM with class weights
- `timing_closure`: {0: 1.0, 1: 2.33}
- `drc_clean`: {0: 5.67, 1: 1.0}

**Training**:
- 5-fold StratifiedKFold (stratified by platform + target)
- Hold-out test set (last fold)
- Isotonic calibration for probability outputs
- Optimal threshold via Youden's J statistic
- Feature importance plots, ROC curves, confusion matrices

**Results** (from training logs):
- Timing Closure: CV AUC ~0.755, Test AUC ~0.716
- DRC Clean: CV AUC ~0.588, Test AUC ~0.613

### 2.4 Random Forest Training (`train_rf.py`)

**Targets**: Same 6 targets (4 regression + 2 classification)

**Hyperparameters** (with Optuna tuning):
- Regression: n_estimators 200-1000, max_depth 10-30
- Classification: class_weight balanced/balanced_subsample

**CV Results** (from saved logs):
| Target | CV R²/AUC | Test R²/AUC |
|--------|-----------|-------------|
| WNS    | 0.212 ± 0.012 | Ensemble: 0.230 |
| TNS    | 0.203 ± 0.012 | Ensemble: 0.212 |
| Area   | 0.824 ± 0.074 | LGB: 0.627 |
| Power  | 0.551 ± 0.161 | Ensemble: 0.655 |
| Timing | 0.709 ± 0.009 | 0.716 (thresh=0.208) |
| DRC    | 0.588 ± 0.029 | 0.613 (thresh=0.930) |

### 2.5 PPO Flow Optimizer (`train_flow_optimizer.py`)

**Environment**: `ORFSFlowEnv` (Gymnasium)
- **State**: 128-dim encoded `FlowState` (design + stage + history)
- **Action**: 16-dim continuous flow parameters
- **Reward**: Multi-objective (WNS 30%, TNS 15%, Area 15%, Power 10%, DRC 15%, Congestion 10%, Runtime 5%)
- **Surrogate**: Uses trained surrogate models for PPA prediction

**Training** (Colab/GPU):
- 500K timesteps, 8 parallel envs
- PPO: lr=3e-4, n_steps=2048, batch=64, epochs=10
- Checkpoint every 50K, eval every 25K
- ONNX export for deployment

---

## 3. Data Pipeline Analysis

### 3.1 Real Data Collection (`collect_real_data.py`)

**Source**: ORFS flow directories (`flow/designs`, `flow/reports`, `flow/logs`, `flow/results`)

**Per-Design Extraction**:
1. **Config** (`config.mk`): CORE_UTILIZATION, CORE_ASPECT_RATIO, CORE_MARGIN
2. **Verilog parsing**: Instance/net/sequential/macro counts
3. **Reports**: Per-stage metrics (WNS, TNS, area, power, DRC, congestion)
4. **Logs**: Stage runtimes
5. **JSON reports** (`6_report.json`): Comprehensive metrics from ORFS

**Output**: `real_runs_training.json` (7000+ records, ~30 designs × platforms × configs)

### 3.2 Training Data (`real_runs_training.json`)

**Schema** (per record):
```json
{
  "run_id": "design_platform_config",
  "timestamp": "ISO8601",
  "design_name": "riscv32i",
  "platform": "gf180|asap7|nangate45|sky130hd",
  "status": "success|failed",
  "core_utilization": 20.0,
  "core_aspect_ratio": 1.0,
  "core_margin": 4.0,
  "place_density": 0.55,
  "synth_wns_ns": null,
  "floorplan_wns_ns": -3.44,
  "place_wns_ns": -1.44,
  "cts_wns_ns": 0.0,
  "route_wns_ns": 0.0,
  "final_wns_ns": -0.03,
  "final_tns_ns": -0.07,
  "final_power_w": 0.28,
  "final_area_um2": 364790.0,
  "final_drc_violations": 2,
  "final_setup_violations": 2,
  "final_hold_violations": 0,
  "timing_closure": 0,
  "drc_clean": 0,
  "lvs_clean": true,
  "data_completeness": "complete|partial"
}
```

**Data Quality Issues**:
- Many `null` values for failed runs (partial data)
- Only 2 designs with significant variation: `riscv32i`, `jpeg`, `picorv32`, `aes`, `riscv32i-mock-sram`
- Most records from `gf180` and `asap7` platforms
- Timing closure rate: ~15% (mostly failing)
- DRC clean rate: ~20%

### 3.3 Feature Engineering (`features.py`)

**Pipeline**: SQLite → Polars → Parquet
- JSON column parsing (`config_params`, `design_features`, `stage_results`)
- Derived features: log transforms, ratios, normalized targets
- Binary flags: `timing_closure_bin`, `drc_clean_bin`, `lvs_clean_bin`
- Categorical encoding: `platform_cat`

---

## 4. ML Model Architecture Details

### 4.1 Surrogate Models (PPA Regression)

**Inference Interface** (`onnx_export.py` → `SurrogateInference`):
```python
surrogate = SurrogateInference("models/saved")
predictions = surrogate.predict_ensemble(features)
# Returns: {'wns': -0.5, 'tns': -10.2, 'area': 123456, 'power': 45.3}
```

**Preprocessing** (ColumnTransformer):
- Categorical: OneHotEncoder (platform: 4, core_aspect_ratio: 1)
- Numeric: StandardScaler (10 features)
- Output: ~16-17 dimensions after one-hot

**Model Files Expected**:
- `surrogate_{wns|tns|area|power}_lgb.pkl` (LightGBM)
- `surrogate_{wns|tns|area|power}_mlp.pt` (PyTorch)
- `surrogate_preprocessor_v2.pkl` (fitted preprocessor)
- ONNX exports: `.onnx` files

### 4.2 Failure Predictor (`failure_predictor.py`)

**Model**: LightGBM (AUC 0.755) + WNS calibration
```python
predictor = FailurePredictor()
result = predictor.predict(metrics)
# Returns: {'predictions': {...}, 'overall_risk': 0.85, 'model_used': 'LightGBM + WNS calibration'}
```

**Calibration**: Isotonic regression + Youden's J threshold
- Falls back to calibrated heuristic if model unavailable
- Heuristic: WNS < -5 → 95%, -5<WNS<0 → 30-70%, WNS≥0 → 5%

### 4.3 Random Forest Models (`random_forest.py`)

**Unified Interface** (`RandomForestIntelligence`):
```python
rf = RandomForestIntelligence()
rf.load_all()
ppa = rf.predict_ppa(features)           # {'wns': -0.5, 'tns': -10.2, ...}
risk = rf.predict_failure_risk(features) # {'timing_closure': {...}, 'drc_clean': {...}}
```

**Feature Format** (one-hot encoded):
- Numeric: 10 base features
- Platform one-hot: `platform_gf180`, `platform_nangate45`, `platform_sky130hd`, `platform_asap7`

**Model Files**:
- Regression: `wns_rf.pkl`, `tns_rf.pkl`, `area_rf.pkl`, `power_rf.pkl`
- Classification: `timing_closure_rf.pkl`, `drc_clean_rf.pkl`
- Calibrators: `{target}_calibration.pkl` (isotonic + threshold)

### 4.4 Flow Optimizer / RL (`flow_optimizer.py`)

**State Encoding** (128-dim):
- Design features: 12 dims (log instances, ratios, freq, util, etc.)
- Platform one-hot: 4 dims
- Current stage: 14 dims (WNS, TNS, area, power, DRC, congestion, density, etc.)
- Stage history (3 stages × 6 dims): 18 dims
- Padding to 128

**Action Space** (16 continuous):
```
[0-3]  synth_strategy, synth_effort, retime, resynth
[4-6]  placement_density, placement_effort, macro_placement
[7-9]  cts_skew_target, cts_buffer_type, cts_clustering
[10-12] routing_layers, routing_effort, detour_scale
[13]   signoff_effort
```

**Reward Function** (`FlowReward.compute`):
- Multi-objective with tanh scaling
- Terminal bonuses: +10 (timing closure), +5 (DRC clean)
- Runtime penalty

**Hybrid Inference**: Heuristic base + PPO residual adjustment

---

## 5. GUI Integration

### 5.1 Intelligence Menu (app.py)

```python
intel_menu.add_command("Predict Failure Risk", _predict_failure_risk)
intel_menu.add_command("Suggest Optimal Parameters", _suggest_optimal_params)
intel_menu.add_command("Show Surrogate Predictions", _show_surrogate_predictions)
intel_menu.add_command("Run RF PPA Prediction", _run_rf_ppa_prediction)
intel_menu.add_command("Run RF Failure Prediction", _run_rf_failure_prediction)
intel_menu.add_command("Show RF Model Performance", _show_rf_model_performance)
intel_menu.add_command("Open Intelligence Reports", _open_intelligence_reports)
```

### 5.2 Right Rail Panels

1. **AI Assistant**: Chat interface with quick actions
2. **PPA Analysis**: Predicted vs Actual vs Diff (%) grid
3. **Optimization Suggestions**: Apply button + suggestion list
4. **Reports**: Buttons for timing/power/area/DRC/LVS reports + GDS generation

### 5.3 Auto-PPA Fetching

- After **Floorplan**: Runs surrogate prediction → updates "Predicted" column
- After **GDS**: Parses actual PPA from `6_finish.rpt` / `6_report.json` → updates "Actual" column

---

## 6. Configuration & Deployment

### 6.1 Configuration (`config.py`)

**AppConfig** (persisted to `~/.config/openroad-gui/config.json`):
- `orfs_root`: ORFS installation path
- `klayout_cmd`: KLayout binary path
- `design_config`: Active design config.mk
- `platform`, `design_name`: Current design
- `extra_env`: Environment variables

**Auto-discovery**: `DEFAULT_ORFS_ROOT` from `$ORFS_ROOT` or `~/OpenROAD-flow-scripts`

### 6.2 Model Deployment

**Model Directory**: `openroad_gui/intelligence/models/saved/`

**Required Files**:
```
surrogate_preprocessor_v2.pkl
surrogate_wns_lgb.pkl, surrogate_wns_mlp.pt
surrogate_tns_lgb.pkl, surrogate_tns_mlp.pt
surrogate_area_lgb.pkl, surrogate_area_mlp.pt
surrogate_power_lgb.pkl, surrogate_power_mlp.pt
timing_closure_lgb.pkl, timing_closure_preprocessor.pkl, timing_closure_calibration.pkl
drc_clean_lgb.pkl, drc_clean_preprocessor.pkl, drc_clean_calibration.pkl
wns_rf.pkl, tns_rf.pkl, area_rf.pkl, power_rf.pkl
timing_closure_rf.pkl, drc_clean_rf.pkl
timing_closure_calibration.pkl, drc_clean_calibration.pkl
```

**ONNX Export** (for deployment):
```
surrogate_{target}_lgb.onnx, surrogate_{target}_mlp.onnx
ppo_flow_optimizer.onnx
```

---

## 7. Strengths & Areas for Improvement

### 7.1 Strengths

| Area | Details |
|------|---------|
| **Comprehensive ML Pipeline** | End-to-end: data collection → feature engineering → training → inference → GUI integration |
| **Multiple Model Types** | LightGBM, PyTorch MLP, Random Forest, PPO — ensemble diversity |
| **Real Data Focus** | `train_all_v2.py` explicitly uses real ORFS runs only |
| **Cross-Validation Rigor** | GroupKFold (design), StratifiedKFold (classification), hold-out test sets |
| **Probability Calibration** | Isotonic regression + Youden's J thresholds for classifiers |
| **GUI Integration** | Intelligence accessible via menu, right-rail panels, auto-updates |
| **ONNX Export** | Deployment-ready model serialization |
| **Multi-Platform Support** | asap7, sky130hd, nangate45, gf180 |
| **Feature Engineering** | Systematic log transforms, ratios, normalized targets |
| **PPO Flow Optimization** | RL-based parameter tuning with surrogate reward |

### 7.2 Areas for Improvement

| Issue | Impact | Recommendation |
|-------|--------|----------------|
| **Limited Training Data** | ~7K records, only 5 designs, imbalanced targets | Expand design portfolio, synthetic augmentation |
| **Surrogate Model Performance** | R² ~0.2-0.6 (WNS/TNS weak), Power ~0.55 | Add flow parameters as features, more data |
| **Failure Predictor DRC AUC** | 0.59-0.61 (near random) | Better features for DRC, more positive samples |
| **Data Quality** | Many nulls in failed runs, partial records | Improve collector to handle partial data |
| **Feature-Model Mismatch** | Surrogate uses design-only features, PPO needs flow params | Extend surrogate to accept flow parameters |
| **Code Duplication** | `train_rf.py` and `train_surrogate_v2.py` share logic | Refactor shared preprocessing into library |
| **Error Handling** | Many bare `except: pass` in parsing | Specific exception handling, logging |
| **Testing** | Only basic test files, no CI/CD | Add pytest suite, GitHub Actions |
| **Documentation** | Scattered docstrings, no architecture doc | Create ARCHITECTURE.md, API docs |

---

## 8. Recommendations

### 8.1 Immediate (High Impact)

1. **Fix DRC Failure Prediction**
   - Add congestion, routing layer, density features
   - Collect more DRC-positive samples (currently ~15%)
   - Consider multi-stage prediction (post-placement, post-route)

2. **Improve Surrogate Accuracy**
   - Include flow parameters in training (from `collect_real_data.py` stage metrics)
   - Add per-stage WNS/TNS as features for final prediction
   - Experiment with deeper MLP, XGBoost, CatBoost

3. **Data Expansion**
   - Run more ORFS designs across platforms
   - Add synthetic data generation with domain randomization
   - Include failed runs with imputed targets

### 8.2 Medium Term

4. **Unify Training Pipeline**
   - Create `training_pipeline.py` with shared base classes
   - Single entry point: `python -m openroad_gui.intelligence.training`
   - Config-driven (YAML) instead of CLI flags

5. **Enhance PPO Environment**
   - Make surrogate accept flow parameters (action → features)
   - Add curriculum learning (easy → hard designs)
   - Implement domain randomization for robustness

6. **Production Hardening**
   - Add model versioning, metadata, lineage
   - Implement A/B testing in GUI
   - Add monitoring/telemetry for predictions

### 8.3 Long Term

7. **Advanced ML**
   - Graph Neural Networks for netlist structure
   - Transfer learning across platforms
   - Active learning for data acquisition

8. **GUI Enhancements**
   - Real-time prediction during flow runs
   - What-if analysis sliders for parameters
   - Integration with OpenROAD GUI TCL scripting

---

## 9. File Inventory (Key Files)

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 2100+ | Main GUI application |
| `config.py` | 187 | Configuration management |
| `flow_runner.py` | 211 | ORFS subprocess execution |
| `train_all_v2.py` | 117 | Unified training pipeline |
| `train_surrogate_v2.py` | 579 | Surrogate model training |
| `train_failure_predictor.py` | 600 | Failure classifier training |
| `train_rf.py` | 514 | Random Forest training |
| `train_flow_optimizer.py` | 548 | PPO training |
| `collect_real_data.py` | 397 | Real ORFS data collection |
| `collector.py` | 573 | Historical data collector |
| `features.py` | 254 | Feature engineering |
| `parser.py` | 339 | Log/report parsing |
| `failure_predictor.py` | 420 | LightGBM failure inference |
| `random_forest.py` | 600 | RF inference engine |
| `flow_optimizer.py` | 455 | RL state/action/reward |
| `onnx_export.py` | 452 | ONNX export + inference |
| `real_runs_training.json` | 7001 | Training dataset (35 designs) |

---

## 10. Conclusion

OpenRoad-GUI is a **sophisticated, production-oriented EDA workstation** with deep ML integration. The project demonstrates:

- **Engineering maturity**: Modular architecture, proper separation of concerns, comprehensive training pipelines
- **ML best practices**: Cross-validation, calibration, ensemble methods, hyperparameter tuning
- **Domain expertise**: ORFS-specific parsing, multi-platform support, realistic feature engineering
- **Deployment readiness**: ONNX export, GUI integration, configuration management

**Primary bottleneck**: Training data quantity and quality. The models show promise but are limited by ~7K records from only 5 designs. Investing in data collection (more ORFS runs, synthetic augmentation, failed-run imputation) would yield the highest ROI for model performance.

The PPO flow optimizer is architecturally sound but needs the surrogate models to accept flow parameters as inputs to close the RL loop effectively.

---
*Report generated from comprehensive codebase analysis*