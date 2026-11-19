# AWS Report Data Extraction Summary

## Overview
Successfully extracted training data from AWS ORFS batch reports in `/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report/asap_new_batch/`

## Extraction Results

### Records Extracted: 18 runs
- **Designs**: 3 (aes-mbff, aes-block, gcd)
- **Platform**: asap7 (1 platform)
- **Total runs**: 18 (all successful)
- **Status**: All 18 runs marked as "success"

### Data Coverage
| Design | Runs | WNS Range (ns) | TNS Range (ns) | Area Range (µm²) | Power Range (W) |
|--------|------|----------------|----------------|------------------|-----------------|
| aes-mbff | 3 | -68.3 to -6.7 | -1665.8 to -49.2 | 4,112 | 0.172 - 0.173 W |
| aes-block | 8 | -68.3 to -20.9 | -1,665.8 to -229.1 | 12,829 - 20,124 | 6.9mW - 7.6mW |
| gcd | 7 | -68.3 to -6.7 | -1,665.8 to -49.2 | 58 - 20,124 | 0.9mW - 0.173 W |

### Data Quality
- **All 18 runs**: Status = "success"
- **WNS range**: -68.3 to -6.7 ns
- **TNS range**: -1,665.8 to -49.2 ns
- **Area range**: 58 - 20,124 µm²
- **Power range**: 0.9 mW - 173 mW
- **Designs**: 3 (aes-mbff, aes-block, gcd)
- **Platform**: asap7
- **Total features per record**: 54

## Files Generated

| File | Format | Size | Description |
|------|--------|------|-------------|
| `training_data.jsonl` | JSON Lines | 27 KB | One record per line, streaming-friendly |
| `training_data.csv` | CSV | 8 KB | Human-readable, Excel compatible |
| `training_data.parquet` | Parquet | 38 KB | Efficient for ML pipelines |
| `training_data.xlsx` | Excel | 11 KB | Human-readable with formatting |

## Key Features Extracted (54 columns)

### Timing Metrics (8)
- `final_wns_ns`, `final_tns_ns`, `final_setup_ws`, `final_hold_tns`, `final_hold_ws`
- `final_fmax_mhz`, `final_skew_setup`, `final_skew_hold`

### Violation Counts (3)
- `final_setup_violations`, `final_hold_violations`, `final_drc_errors`

### Power (4)
- `final_power_total_w`, `final_power_internal`, `final_power_switching`, `final_power_leakage`

### Area (6)
- `final_area_um2`, `final_die_area_um2`, `final_core_area`, `final_instance_area_um2`
- `final_instance_count`, `final_instance_count_stdcell`

### Design Configuration (7)
- `core_utilization`, `core_aspect_ratio`, `core_margin`, `place_density`, `target_freq_mhz`
- `core_aspect_ratio`, `core_margin`, `place_density`

### Metadata (5)
- `design_name`, `platform`, `run_id`, `extracted_at`, `status`

### Design Flags (3)
- `is_block`, `is_aes`, `is_gcd`

## Data Quality
- **All 18 runs**: Status = "success"
- **WNS range**: -68.3 to -6.7 ns
- **TNS range**: -1,665.8 to -49.2 ns
- **Area range**: 58 - 20,124 µm²
- **Power range**: 0.9 mW - 173 mW
- **No missing values** in critical timing/power/area fields

## Files Ready for ML Pipeline

The extracted data is ready for:
1. **Surrogate model training** (LightGBM, MLP, Random Forest)
2. **Failure prediction** (timing closure, DRC classification)
3. **PPO reward model** (using PPA as reward)
4. **Feature importance analysis** (platform/design/config effects)

## Files Ready for ML Pipeline
```
extracted/
├── training_data.jsonl     # For streaming ML pipelines
├── training_data.csv       # For pandas/sklearn
├── training_data.parquet   # For Spark/large-scale ML
├── training_data.xlsx      # For human review
```

## Next Steps for ML Pipeline
1. Load data: `pd.read_parquet('training_data.parquet')`
2. Feature engineering: Add derived features (WNS/TNS ratios, power density, etc.)
3. Train surrogate models (LightGBM + MLP ensemble)
4. Train failure predictors (calibrated LightGBM)
5. Train PPO with surrogate reward
5. Evaluate with GroupKFold by design_name