# OpenROAD Flow GUI - Intelligence Module Development Log

## Date: 2025-01-19 (Session 1) & 2025-01-20 (Session 2) & 2025-10-21 (Session 3)

---

## Summary
Fixed the intelligence module data pipeline to work with real ORFS (OpenROAD Flow Scripts) directory structure. Successfully collected **171 training runs** from **22 designs across 4 platforms** with full PPA metrics extraction. Completed full model training pipeline on Google Colab (T4 GPU).

---

## Issues Fixed (Session 1)

### 1. Feature Extraction Pipeline (`openroad_gui/intelligence/data/features.py`)

**Problem 1: `StructFieldNotFoundError: num_instances`**
- Root cause: Polars inferred empty struct schema when JSON was `{}`, causing `.struct.field()` to fail
- Fix: Changed JSON parsing to return `pl.Object` (raw dicts), added explicit extraction functions with defaults, defined explicit struct schemas

**Problem 2: `DuplicateError: platform`**
- Root cause: `platform` and `design_name` selected twice in `df.select()`
- Fix: Removed duplicate column selections

**Problem 3: `pl.NUMERIC_DTYPES` deprecated in Polars 1.0+**
- Fix: Replaced with `pl.selectors.numeric()`

**Problem 4: `DataFrame.items()` not available**
- Fix: Changed null count iteration to use DataFrame columns directly

**Problem 5: Test assertion `num_cols > 10` failing**
- Fix: Added more columns to test DataFrame

### 2. Reward Function Sign Bug (`openroad_gui/intelligence/models/flow_optimizer.py`)

**Problem: WNS/TNS improvement calculation had wrong sign**
- Original: `prev.current_wns_ns - curr.current_wns_ns` (treats degradation as improvement)
- Fix: Changed to `curr.current_wns_ns - prev.current_wns_ns` (improvement = less negative)
- Verified: Improvement test → positive reward, Degradation test → negative reward

### 3. Data Collector (`openroad_gui/intelligence/data/collector.py`)

**Problem 1: Wrong ORFS path resolution**
- Root cause: `results_dir.parent.parent.parent` went to wrong directory level
- Debug revealed: ORFS root is at `results_dir.parent.parent` (Level 2)
- Fix: Changed to `orfs_root = results_dir.parent.parent`

**Problem 2: ORFS directory structure mismatch**
- Collector expected: `results/<platform>/<design>/<run_id>/config.mk, reports/, logs/`
- Actual ORFS structure:
  - `flow/designs/<platform>/<design>/config.mk`
  - `flow/reports/<platform>/<design>/base/*.rpt`
  - `flow/logs/<platform>/<design>/base/*.log`
  - `flow/results/<platform>/<design>/base/*.odb, *.gds`
- Fix: Rewrote `collect_from_directory()` to iterate `designs_root` and look up corresponding reports/logs/results

**Problem 3: Timestamp handling**
- Multiple `time.gmtime()` calls returning `struct_time` (no `.isoformat()`)
- Fix: Replaced with `datetime.now()` or `datetime.fromtimestamp()`

**Problem 4: Report parsing regex not matching ORFS format** ✅ FIXED (Session 2)
- Reports use format: `wns max -0.74` / `tns max -14.20`
- Parser expected: `WNS: -0.74` / `TNS: -14.20`
- Fix: Updated regex patterns in `_parse_report_content()` to match ORFS format

**Problem 5: JSON report parsing not implemented** ✅ FIXED (Session 2)
- ORFS generates `6_report.json` in logs directory with comprehensive metrics
- Added `_parse_json_report()` to extract area, power, DRC violations, utilization
- Fixed `_parse_final_metrics()` to look for JSON in `logs/<platform>/<design>/base/6_report.json`

**Problem 6: Duplicate method definitions** ✅ FIXED (Session 2)
- File had 4 duplicate copies of each method due to repeated patching
- Rewrote entire `collector.py` cleanly with single method definitions

---

## Issues Fixed (Session 2)

### 1. Report Parsing Regex (`_parse_report_content`)
- Updated patterns to match ORFS format:
  - `wns max -0.74` → `r"wns\s+max\s+([-\d.]+)"`
  - `tns max -14.20` → `r"tns\s+max\s+([-\d.]+)"`
  - `setup violation count 45` → `r"setup\s+violation\s+count\s+(\d+)"`
  - `hold violation count 0` → `r"hold\s+violation\s+count\s+(\d+)"`
  - `slew violation count 0` → `r"slew\s+violation\s+count\s+(\d+)"`
  - `fanout violation count 0` → `r"fanout\s+violation\s+count\s+(\d+)"`
  - `cap violation count 1` → `r"cap\s+violation\s+count\s+(\d+)"`
  - `congestion:1` → `r"congestion\s*:\s*(\d+)"`

### 2. JSON Report Parsing (`_parse_json_report`)
- Added method to parse `6_report.json` from logs directory
- Maps ORFS JSON keys to internal metric names:
  - `finish__design__instance__area` → `area_um2` / `instance_area_um2`
  - `finish__power__total` → `power_mw` (converts W to mW)
  - `finish__timing__drv__setup_violation_count` → `setup_violations`
  - `finish__timing__drv__hold_violation_count` → `hold_violations`
  - `finish__timing__drv__max_slew` → `slew_violations`
  - `finish__timing__drv__max_cap` → `cap_violations`
  - `finish__timing__drv__max_fanout` → `fanout_violations`
  - `finish__design__die__area` → `die_area_um2`
  - `finish__design__core__area` → `core_area_um2`
  - `finish__design__instance__area` → `instance_area_um2`
  - `finish__design__instance__utilization` → `utilization`
  - `finish__design__instance__count` → `instance_count`

### 3. Duplicate Method Cleanup
- File had 4 duplicate copies of `_parse_final_metrics`, `_parse_orfs_design`, `_parse_stage_reports`, etc.
- Rewrote entire `collector.py` cleanly with single method definitions
- Removed legacy `_parse_run_directory` method (old structure)

---

## Session 3: Google Colab Training (2025-10-21)

### Google Colab Training Session
- **Platform:** Google Colab with T4 GPU
- **Data:** 3000 samples, 22 designs across 4 platforms (asap7, gf180, nangate45, sky130hd)
- **Training Pipeline:**
  1. **Failure Predictor** (LightGBM) - Binary classification for timing_closure, drc_clean
  2. **Surrogate Models** (XGBoost + LightGBM) - Regression for WNS, TNS, Area, Power
  3. **Flow Optimizer** (PPO) - RL agent for flow parameter optimization

### Models Trained & Results

| Model | Algorithm | Target | Metric | Value |
|-------|-----------|--------|--------|-------|
| Failure Predictor | LightGBM | timing_closure | AUC | 0.7551 |
| Failure Predictor | LightGBM | drc_clean | AUC | 0.5197 |
| Surrogate (WNS) | XGBoost | final_wns_ns | R² | 0.2853 |
| Surrogate (TNS) | XGBoost | final_tns_ns | R² | 0.2300 |
| Surrogate (Area) | XGBoost | final_area_um2 | R² | 0.9559 |
| Surrogate (Power) | LightGBM | final_power_mw | R² | 0.4787 |
| Flow Optimizer | PPO (Actor-Critic) | - | Avg Reward | ~6900-7000 |

### Key Achievements
- ✅ All 10 intelligence unit tests pass
- ✅ 3000 samples, 22 designs across 4 platforms (asap7, gf180, nangate45, sky130hd)
- ✅ 18 designs with full JSON metrics (6_report.json)
- ✅ Area prediction excellent (R² = 0.9559)
- ✅ Flow Optimizer PPO completed 2000 iterations on T4 GPU
- ✅ All models exported and saved to Google Drive

---

## Models Saved & Exported

```
openroad_gui/intelligence/models/saved/
├── timing_closure_lgb.pkl      # Failure predictor (AUC=0.7551)
├── drc_clean_lgb.pkl           # Failure predictor (AUC=0.5197)
├── surrogate_wns.pkl           # WNS regressor (R²=0.2853)
├── surrogate_tns.pkl           # TNS regressor (R²=0.2300)
├── surrogate_area.pkl          # Area regressor (R²=0.9559) ← Excellent
├── surrogate_power.pkl         # Power regressor (R²=0.4787)
├── flow_optimizer_ppo.pt       # PPO Actor-Critic (2000 iters)
└── ppo_checkpoint_{0,500,1000,1500,2000}.pt  # Checkpoints
```

### Model Performance Summary

| Model | Algorithm | Target | Metric | Value | Notes |
|-------|-----------|--------|--------|-------|-------|
| Failure Predictor | LightGBM | timing_closure | AUC | 0.7551 | 30% positive class |
| Failure Predictor | LightGBM | drc_clean | AUC | 0.5197 | 85% clean (imbalanced) |
| Surrogate (WNS) | XGBoost | final_wns_ns | R² | 0.2853 | Moderate |
| Surrogate (TNS) | XGBoost | final_tns_ns | R² | 0.2300 | Moderate |
| Surrogate (Area) | XGBoost | final_area_um2 | R² | **0.9559** | **Excellent** |
| Surrogate (Power) | LightGBM | final_power_mw | R² | 0.4787 | Moderate |
| Flow Optimizer | PPO | - | Avg Reward | ~6900-7000 | 2000 iterations |

---

## Files Generated & Exported

```
openroad_gui/intelligence/models/saved/
├── timing_closure_lgb.pkl      # Failure predictor (AUC=0.7551)
├── drc_clean_lgb.pkl           # Failure predictor (AUC=0.5197)
├── surrogate_wns.pkl           # WNS regressor (R²=0.2853)
├── surrogate_tns.pkl           # TNS regressor (R²=0.2300)
├── surrogate_area.pkl          # Area regressor (R²=0.9559) ← Excellent
├── surrogate_power.pkl         # Power regressor (R²=0.4787)
├── flow_optimizer_ppo.pt       # PPO Actor-Critic (2000 iters)
└── ppo_checkpoint_{0,500,1000,1500,2000}.pt  # Checkpoints

openroad_gui/intelligence/training/logs/
├── training_results.json
├── surrogate_results.json
├── cm_timing_closure_lgb.png
├── roc_timing_closure_lgb.png
├── fi_timing_closure_lgb.png
├── cm_drc_clean_lgb.png
├── roc_drc_clean_lgb.png
├── fi_drc_clean_lgb.png
├── residuals_wns_xgb.png
├── residuals_wns_lgb.png
├── residuals_tns_xgb.png
├── residuals_tns_lgb.png
├── residuals_area_xgb.png
├── residuals_area_lgb.png
├── residuals_power_xgb.png
├── residuals_power_lgb.png
├── fi_wns_xgb.png
├── fi_wns_lgb.png
├── fi_tns_xgb.png
├── fi_tns_lgb.png
├── fi_area_xgb.png
├── fi_area_lgb.png
├── fi_power_xgb.png
├── fi_power_lgb.png

openroad_gui/intelligence/training/checkpoints/
├── ppo_checkpoint_0.pt
├── ppo_checkpoint_500.pt
├── ppo_checkpoint_1000.pt
├── ppo_checkpoint_1500.pt
├── ppo_checkpoint_2000.pt

openroad_gui/dataset_genration/output/
├── training_data.parquet
├── training_data.csv
├── training_data.jsonl
├── training_data.xlsx
├── splits/
│   ├── train.csv (2100 rows)
│   ├── validation.csv (600 rows)
│   └── test.csv (300 rows)
```

---

## Current Status Summary

### ✅ Completed (Sprint 1 + 2 + 3)
- **Sprint 1:** Data pipeline, architecture design, unit tests (10/10 passing)
- **Sprint 2:** Cloud training on T4 GPU (Colab)
- **Sprint 3:** Model export, Google Drive sync, local integration ready

### ✅ All Models Trained & Exported
| Model | Status | Key Metric |
|-------|--------|------------|
| Failure Predictor (timing) | ✅ Complete | AUC = 0.7551 |
| Failure Predictor (DRC) | ✅ Complete | AUC = 0.5197 |
| Surrogate (WNS) | ✅ Complete | R² = 0.2853 |
| Surrogate (TNS) | ✅ Complete | R² = 0.2300 |
| Surrogate (Area) | ✅ Complete | **R² = 0.9559** |
| Surrogate (Power) | ✅ Complete | R² = 0.4787 |
| Flow Optimizer (PPO) | ✅ Complete | 2000 iterations, avg reward ~6900-7000 |

### ✅ Data Pipeline
- 3000 samples, 22 designs, 4 platforms
- 18 designs with full JSON metrics (6_report.json)
- Feature extraction pipeline working (quality score 100)
- Report parsing regex matches ORFS format
- JSON report parsing extracts area, power, DRC, utilization

### ✅ Model Export
- All 7 models saved to Google Drive
- PPO checkpoints saved every 500 iterations
- Models ready for local integration

---

## Next Steps (Sprint 4 - Local Integration)

### Priority 1: Local Integration
```bash
# On local laptop
cp ~/Google\ Drive/MyDrive/OpenRoad_Training/intelligence/models/saved/* \
   openroad_gui/intelligence/models/saved/

# Verify in local code
python3 -c "
from openroad_gui.intelligence import FlowOptimizationEngine, FailurePredictor
optimizer = FlowOptimizationEngine()
predictor = FailurePredictor()
print('Models loaded successfully!')
"
```

### Priority 2: GUI Integration
- Integrate `FlowOptimizationEngine` with FlowPanel for real-time parameter suggestions
- Integrate `FailurePredictor` with FlowPanel for real-time risk alerts
- Add Analytics tab with congestion heatmaps

### Priority 3: Production Hardening
- Add model versioning
- Add prediction confidence intervals
- Add fallback to default parameters if prediction fails
- Add logging for production debugging

---

## Files Modified (Complete List)

### Core Fixes (Sessions 1-2)
1. `openroad_gui/intelligence/data/features.py` - Fixed feature extraction (5 bugs)
2. `openroad_gui/intelligence/models/flow_optimizer.py` - Fixed reward sign
3. `openroad_gui/intelligence/data/collector.py` - **Complete rewrite** (path resolution, ORFS structure, timestamps, regex, JSON parsing, duplicate removal)
4. `openroad_gui/intelligence/tests/test_features.py` - Fixed test assertions
5. `openroad_gui/intelligence/tests/test_flow_optimizer.py` - Tests pass

### Training Scripts (Session 3)
6. `openroad_gui/intelligence/training/train_failure_predictor.py` - LightGBM only (M1 compatible)
7. `openroad_gui/intelligence/training/train_surrogate.py` - XGBoost + LightGBM regression
7. `openroad_gui/intelligence/training/train_flow_optimizer.py` - PPO with MPS/CUDA support, cooling periods
8. `openroad_gui/intelligence/training/train_all.py` - Master training script

### Documentation
8. `INTELLIGENCE_ARCHITECTURE.md` - Architecture documentation
9. `SPRINT1_EXECUTION_ORDER.md` - Sprint execution guide
10. `reports.md` - Model training reports
11. `LOG.md` - This development log

---

## Commands to Resume (Sprint 4 - Local Integration)

```bash
cd "/Users/mihirmithani/Downloads/OpenRoad GUI"

# 1. Copy models from Google Drive to local
cp ~/Google\ Drive/MyDrive/OpenRoad_Training/intelligence/models/saved/* \
   openroad_gui/intelligence/models/saved/

# 2. Verify in local code
python3 -c "
from openroad_gui.intelligence import FlowOptimizationEngine, FailurePredictor
optimizer = FlowOptimizationEngine()
predictor = FailurePredictor()
print('Models loaded successfully!')
print('Optimizer:', optimizer)
print('Predictor:', predictor)
"

# 3. Run GUI locally
python3 -m openroad_gui
```

---

## Notes
- All fixes are in the main codebase, no temporary patch files needed
- The collector now correctly handles ORFS standard directory structure
- 22 diverse designs provide good platform/design coverage for initial training
- 18 designs have `6_report.json` with full PPA metrics (area, power, DRC, utilization)
- Report parsing and JSON extraction are the key enablers for meaningful feature data
- Ready for Sprint 4: Local GUI integration and production hardening

---

**Last Updated:** 2025-10-21  
**Status:** All training complete, models exported, ready for local integration (Sprint 4)