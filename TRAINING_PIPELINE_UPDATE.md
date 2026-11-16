# Training Pipeline Update: Real AWS Data Only

## Summary of Changes

The training pipeline has been updated to use **real AWS ORFS run data exclusively** (no synthetic data). The key changes are:

### 1. New Data Source: AWS_Report Directory
- **Location**: `/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report/`
- **Structure**: Platform → Design → Timestamped run directories with `config.mk`, `run_metadata.json`, `reports/`, `logs/`
- **Platforms**: `asap7`, `gf180`, `nangate45`, `sky130hd`
- **Designs**: 9 unique designs (gcd, aes, riscv32i-mock-sram, ibex, uart-blocks, riscv32i, picorv32, dynamic_node, jpeg)
- **Total Runs**: 175 unique design/config combinations (152 complete, 23 partial/failed)

### 2. Comprehensive Data Extraction
**Script**: `scripts/data_extraction/extract_comprehensive_aws.py`
- Extracts ALL available data including successful, failed, and timed-out runs
- Parses: `config.mk`, `run_metadata.json`, stage reports (1-6), `6_finish.rpt`, `6_report.json`, logs
- Outputs: `aws_real_runs_comprehensive.json` + CSV

### 3. Training Data Preparation
**Script**: `openroad_gui/intelligence/data/prepare_real_training_data.py`
- Converts comprehensive AWS data → format expected by training scripts
- Adds engineered features: log transforms, ratios, normalized targets, binary flags
- Estimates missing columns: `num_instances`, `num_nets`, `num_sequential`, etc.
- Adds `suitable_for_regression` flag (149 complete runs with valid targets)
- Outputs: `real_runs_training.json` (175 records, 56 columns)

### 4. Training Script Updates

#### `train_surrogate_v2.py`
- Filters data using `suitable_for_regression` flag before training
- Only uses 149 complete runs for regression targets (WNS, TNS, Area, Power)
- GroupKFold CV by design_name prevents data leakage

#### `train_failure_predictor.py`
- Fixed duplicate code bug in `run_cv_for_target()`
- Uses all 175 runs (including partial/failed) for classification
- StratifiedKFold by platform + target
- Isotonic calibration + Youden's J threshold optimization

#### `train_all_v3.py` (New Unified Pipeline)
- Uses pre-extracted AWS data instead of collecting from ORFS
- Steps: Prepare data → Train surrogate → Train failure predictor → Train RF → PPO (Colab)
- No ORFS root required for training

## Data Statistics

| Metric | Value |
|--------|-------|
| Total Records | 175 |
| Complete Runs | 152 |
| Partial/Failed Runs | 23 |
| Regression-Suitable | 149 |
| Platforms | 4 (asap7, gf180, nangate45, sky130hd) |
| Designs | 9 |
| Timing Closure Rate | 20.6% |
| DRC Clean Rate | 31.4% |
| Core Utilization Range | 20-70% |
| WNS Range | -40.49 to 0.00 ns |
| TNS Range | -784.16 to 0.00 ns |
| Area Range | 46 to 2,201,890 μm² |
| Power Range | 0.60 to 4,195.09 mW |

## Training Results (Preliminary)

### Surrogate Models (3-fold GroupKFold CV)
| Target | Final Retrain R² | Final Retrain RMSE |
|--------|------------------|-------------------|
| WNS | 0.971 (LGB) / 0.786 (Ensemble) | 1.58 ns / 4.28 ns |
| TNS | 0.954 (LGB) | 40.71 ns |
| Area | Training... | Training... |
| Power | Training... | Training... |

### Failure Predictor (4-fold Stratified CV)
| Target | CV AUC | Test AUC (Calibrated) | Threshold |
|--------|--------|----------------------|-----------|
| Timing Closure | 0.958 ± 0.014 | 0.995 | 0.333 |
| DRC Clean | Training... | Training... | Training... |

## Usage

### Run Full Pipeline
```bash
cd /Users/mihirmithani/Downloads/OpenRoad GUI
python -m openroad_gui.intelligence.training.train_all_v3 --epochs 200 --device cpu --cv-folds 5
```

### Run Individual Components
```bash
# Prepare training data only
python openroad_gui/intelligence/data/prepare_real_training_data.py

# Train surrogate models
python -m openroad_gui.intelligence.training.train_surrogate_v2 \
    --real-data openroad_gui/intelligence/data/real_runs_training.json \
    --epochs 200 --device cpu --cv-folds 5 --ensemble

# Train failure predictor
python -m openroad_gui.intelligence.training.train_failure_predictor \
    --real-data openroad_gui/intelligence/data/real_runs_training.json

# Train Random Forest
python -m openroad_gui.intelligence.training.train_rf --target all
```

## Key Improvements

1. **Real Data Only**: No synthetic data contamination
2. **Better Coverage**: 9 designs × 4 platforms × multiple config sweeps
3. **Failed Run Inclusion**: Partial/failed runs improve failure prediction
4. **Proper CV**: GroupKFold (surrogate) and StratifiedKFold (failure) prevent leakage
5. **Calibrated Probabilities**: Isotonic regression + Youden's J for reliable thresholds
6. **Reproducible**: Fixed random seeds, deterministic CV splits

## Next Steps

1. **Expand Data**: Run more ORFS designs/configs to increase sample size
2. **Feature Enhancement**: Add per-stage metrics as features for surrogate models
3. **Model Tuning**: Optuna hyperparameter optimization for all models
4. **PPO Training**: Run flow optimizer on Colab/GPU with updated surrogate
5. **Evaluation**: Test on held-out designs for true generalization assessment