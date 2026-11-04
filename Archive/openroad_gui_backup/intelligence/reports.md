# Model Training Reports

## Failure Predictor (Classification) - LightGBM
**Training Date:** 2025-10-21  
**Dataset:** 3000 samples, 13 features, 2 targets  
**Platform:** macOS M1 (LightGBM, single thread)

| Target | Model | AUC | Precision (0/1) | Recall (0/1) | F1 (0/1) |
|--------|-------|-----|----------------|--------------|----------|
| timing_closure | LightGBM | 0.7551 | 0.71 / 0.60 | 0.99 / 0.03 | 0.82 / 0.06 |
| drc_clean | LightGBM | 0.5197 | 0.00 / 0.85 | 0.00 / 1.00 | 0.00 / 0.92 |

**Class Balance:**
- timing_closure: 30% positive (900/3000)
- drc_clean: 15% positive (450/3000) - Note: class imbalance, all runs DRC clean in current data

**Models Saved:**
- `openroad_gui/intelligence/models/saved/timing_closure_lgb.pkl`
- `openroad_gui/intelligence/models/saved/drc_clean_lgb.pkl`

---

## Surrogate Models (Regression) - XGBoost + LightGBM
**Training Date:** 2025-10-21  
**Dataset:** 3000 samples, 13 features, 4 targets  
**Split:** 2400 train / 600 test (80/20)  
**Platform:** macOS M1 (XGBoost single-thread, LightGBM single-thread)

| Target | XGBoost R² | LightGBM R² | Best Model | RMSE (Best) | MAE (Best) |
|--------|-----------|-------------|------------|-------------|------------|
| WNS (ns) | 0.2865 | 0.2818 | XGBoost | 34.99 | 29.04 |
| TNS (ns) | 0.2283 | 0.2249 | XGBoost | 321.90 | 253.31 |
| Area (μm²) | 0.9626 | 0.9556 | XGBoost | 100,171 | 34,501 |
| Power (mW) | 0.4313 | 0.4787 | LightGBM | 284.67 | 107.70 |

**Key Observations:**
- Area prediction is excellent (R² > 0.95) - strong correlation with design size
- WNS/TNS prediction moderate (R² ~0.23-0.29) - timing is harder to predict
- Power prediction moderate (R² ~0.43-0.48)
- Area is the most predictable metric

**Models Saved:**
- `surrogate_wns.pkl`, `surrogate_tns.pkl`, `surrogate_area.pkl`, `surrogate_power.pkl`

---

## Dataset Statistics
- **Total samples:** 3000
- **Features:** 13 (11 numeric + 2 categorical)
- **Designs:** 22 unique across 4 platforms
- **Platforms:** asap7 (30%), sky130hd (30%), nangate45 (20%), gf180 (20%)
- **Class balance:** timing_closure=30%, drc_clean=85%
- **Data quality score:** 100/100

---

## Files Generated
```
openroad_gui/intelligence/models/saved/
├── timing_closure_lgb.pkl
├── drc_clean_lgb.pkl
├── surrogate_wns.pkl
├── surrogate_tns.pkl
├── surrogate_area.pkl
├── surrogate_power.pkl

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
├── (PPO checkpoints - to be generated)

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