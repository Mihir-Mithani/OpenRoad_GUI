# Synthetic Dataset Generation Specification
## OpenROAD Flow GUI - Intelligence Module Training Data

---

## 📊 Current Dataset Profile (Reference)

| Property | Value |
|----------|-------|
| **Rows** | 171 |
| **Columns** | 35 |
| **Designs** | 22 unique |
| **Platforms** | 4 (asap7, gf180, nangate45, sky130hd) |
| **Runs with JSON metrics** | 18/22 designs |
| **Quality Score** | 100/100 |

**Key Statistics:**
| Metric | Range |
|--------|-------|
| final_wns_ns | -220.91 to 0.0 ns |
| final_tns_ns | -1271 to 0 ns |
| final_area_um2 | 2.3 to 129,825 μm² |
| final_power_mw | 0.007 to 582.8 mW |
| final_drc_violations | 0 (all clean) |
| timing_closure | 0% (all negative WNS) |
| drc_clean | 100% |

---

## 🎯 Synthetic Dataset Specification

### **Target Size: 3,000 rows** (minimum 2,000, ideal 5,000)

| Split | Rows | Percentage | Purpose |
|-------|------|------------|---------|
| Training | 2,100 | 70% | Model training |
| Validation | 600 | 20% | Hyperparameter tuning |
| Test | 300 | 10% | Final evaluation |

---

## 📋 Column Specification (35 columns)

### **Identifier Columns (4)**

| Column | Type | Description | Synthetic Strategy |
|--------|------|-------------|-------------------|
| `run_id` | string | Unique run identifier | `"{design}_{platform}_{uuid4()[:8]}"` |
| `design_name` | string | Design name | Sample from 22 real + 50 synthetic names |
| `platform` | categorical | PDK name | Stratified: asap7(30%), sky130hd(30%), nangate45(20%), gf180(20%) |
| `timestamp` | datetime | Run timestamp | Uniform over last 12 months |

### **Design Configuration (7)**

| Column | Type | Range/Distribution | Constraints |
|--------|------|-------------------|-------------|
| `core_utilization` | float | Uniform(10, 70) | Integer % |
| `core_aspect_ratio` | float | Choice[0.5, 1.0, 1.5, 2.0] | |
| `core_margin` | float | Uniform(1, 10) | Integer |
| `num_instances` | int | LogNormal(μ=8, σ=1.5) | 100 - 1M |
| `num_nets` | int | ~1.2 × num_instances | Correlation 0.95 |
| `num_sequential` | int | Binomial(num_instances, p=0.2) | Correlated |
| `num_macros` | int | Poisson(λ=2) | 0-50 |

### **Derived Design Features (6)**

| Column | Type | Formula/Strategy |
|--------|------|-----------------|
| `log_instances` | float | log1p(num_instances) / 20 |
| `log_nets` | float | log1p(num_nets) / 20 |
| `seq_ratio` | float | num_sequential / max(num_instances, 1) |
| `macro_ratio` | float | num_macros / max(num_instances, 1) |
| `platform_cat` | categorical | Same as platform |
| `design_name` | string | Same as design_name |

### **Target Metrics (PPA) - PRIMARY TARGETS (7)**

| Column | Type | Distribution | Correlation Notes |
|--------|------|--------------|-------------------|
| `final_wns_ns` | float | Mixture: 70% Neg(μ=-50,σ=30), 30% Pos(μ=20,σ=15) | **Key target** |
| `final_tns_ns` | float | ~10× WNS + Noise | Corr(WNS) ≈ 0.85 |
| `final_area_um2` | float | LogNormal(μ=10, σ=1.2) | Corr(instances) ≈ 0.9 |
| `final_power_mw` | float | LogNormal(μ=5, σ=1.0) | Corr(area) ≈ 0.6 |
| `final_drc_violations` | int | Zero-inflated Poisson: 85% zeros, Pois(λ=5) | Anti-corr(timing_closure) |
| `timing_closure_bin` | binary | P=0.3 (synthetic) | 1 if WNS ≥ 0 |
| `drc_clean_bin` | binary | P=0.85 | 1 if DRC=0 |

### **Binary Labels (2)**

| Column | Type | Derivation |
|--------|------|------------|
| `lvs_clean_bin` | binary | Copy of `drc_clean_bin` (LVS typically clean if DRC clean) |

### **Normalized/Engineered Features (5)**

| Column | Type | Formula |
|--------|------|---------|
| `wns_normalized` | float | clip(final_wns_ns / 10, -1, 1) |
| `tns_normalized` | float | clip(final_tns_ns / 1000, -1, 1) |
| `log_area` | float | log1p(final_area_um2) / 20 |
| `log_power` | float | log1p(final_power_mw) / 20 |

---

## 🔗 Critical Correlation Structure (MUST PRESERVE)

| Pair | Target Correlation | Notes |
|------|-------------------|-------|
| WNS ↔ TNS | **0.85 - 0.95** | Strong positive |
| Instances ↔ Area | **0.85 - 0.95** | Log-linear |
| Area ↔ Power | **0.55 - 0.75** | Sub-linear |
| Utilization ↔ WNS | **-0.4 to -0.6** | Higher util → worse timing |
| WNS ↔ Timing Closure | **-0.9** | Threshold at 0 |
| DRC Violations ↔ Timing Closure | **-0.3** | More violations → harder closure |

---

## 🎯 Class Balance Requirements (CRITICAL)

| Target | Current | Target | Action |
|--------|---------|--------|--------|
| `timing_closure=1` | 0% | **30%** | Force 30% WNS ≥ 0 |
| `drc_clean=0` | 0% | **15%** | Inject DRC violations |
| `lvs_clean=0` | 0% | **10%** | Correlated with DRC |

---

## 📐 Platform-Specific Distributions

| Platform | Weight | Utilization Range | Typical Area | Typical Power | WNS Bias |
|----------|--------|-------------------|--------------|---------------|----------|
| sky130hd | 30% | 20-50% | 10K-500K | 10-500mW | Slightly negative |
| asap7 | 30% | 15-40% | 5K-200K | 5-200mW | More negative |
| nangate45 | 20% | 25-60% | 50K-2M | 50-2000mW | Near zero |
| gf180 | 20% | 20-50% | 20K-500K | 20-800mW | Slightly negative |

---

## 🚫 Constraints & Validation Rules

| Rule | Check |
|------|-------|
| `num_nets` ≥ `num_instances` | Typically 1.1-1.5× |
| `num_sequential` ≤ `num_instances` | Ratio 0.1-0.3 |
| `core_utilization` ∈ [10, 80] | Integer |
| `core_aspect_ratio` ∈ {0.5, 1.0, 1.5, 2.0} | Discrete |
| `final_drc_violations` ≥ 0 | Integer |
| `timing_closure_bin` = 1 iff `final_wns_ns` ≥ 0 | Logical |
| `drc_clean_bin` = 1 iff `final_drc_violations` = 0 | Logical |
| `lvs_clean_bin` ≤ `drc_clean_bin` | LVS clean requires DRC clean |

---

## 📦 Delivery Format

| Format | Purpose |
|--------|---------|
| **Parquet** (`training_data.parquet`) | Primary - preserves types, compressed |
| **CSV** (`training_data.csv`) | Human-readable, Nemotron compatible |
| **Excel** (`training_data.xlsx`) | Nemotron Data Designer import |
| **JSON Lines** (`training_data.jsonl`) | Streaming/NDJSON for pipelines |

---

## ✅ Validation Checklist (Run After Generation)

```python
# Must pass all:
assert len(df) == 3000
assert df['timing_closure_bin'].mean() == 0.30 ± 0.02
assert df['drc_clean_bin'].mean() == 0.85 ± 0.02
assert df['final_wns_ns'].corr(df['final_tns_ns']) > 0.8
assert df['num_instances'].corr(df['final_area_um2']) > 0.8
assert (df['timing_closure_bin'] == (df['final_wns_ns'] >= 0)).all()
assert (df['drc_clean_bin'] == (df['final_drc_violations'] == 0)).all()
assert df['platform'].value_counts(normalize=True).round(2).to_dict() == \
    {'sky130hd': 0.30, 'asap7': 0.30, 'nangate45': 0.20, 'gf180': 0.20}
```

---

## 🎯 Minimum Viable Synthetic Dataset

If constrained: **2,000 rows** with:
- 600 timing closure = 1
- 300 DRC violations > 0
- All 4 platforms represented
- All correlations within ±0.1 of targets above

---

## 📋 Column Reference (Complete List)

| # | Column | Type | Category |
|---|--------|------|----------|
| 1 | `run_id` | string | Identifier |
| 2 | `design_name` | string | Identifier |
| 3 | `platform` | categorical | Identifier |
| 4 | `timestamp` | datetime | Identifier |
| 5 | `core_utilization` | float | Config |
| 6 | `core_aspect_ratio` | float | Config |
| 6 | `core_margin` | float | Config |
| 7 | `num_instances` | int | Design |
| 8 | `num_nets` | int | Design |
| 9 | `num_sequential` | int | Design |
| 10 | `num_macros` | int | Design |
| 11 | `log_instances` | float | Derived |
| 12 | `log_nets` | float | Derived |
| 13 | `seq_ratio` | float | Derived |
| 14 | `macro_ratio` | float | Derived |
| 15 | `platform_cat` | categorical | Derived |
| 16 | `design_name` | string | Derived |
| 17 | `final_wns_ns` | float | Target |
| 18 | `final_tns_ns` | float | Target |
| 19 | `final_area_um2` | float | Target |
| 20 | `final_power_mw` | float | Target |
| 21 | `final_drc_violations` | int | Target |
| 22 | `timing_closure_bin` | binary | Target |
| 23 | `drc_clean_bin` | binary | Target |
| 24 | `lvs_clean_bin` | binary | Target |
| 25 | `wns_normalized` | float | Normalized |
| 26 | `tns_normalized` | float | Normalized |
| 27 | `log_area` | float | Normalized |
| 28 | `log_power` | float | Normalized |
| 29 | `timing_closure_bin` | binary | Target |
| 30 | `drc_clean_bin` | binary | Target |
| 31 | `lvs_clean_bin` | binary | Target |
| 32 | `platform_cat` | categorical | Platform |
| 33 | `design_name` | string | Design |
| 34 | `core_utilization` | float | Config |
| 35 | `core_aspect_ratio` | float | Config |

---

## 📦 Delivery Formats

| Format | Filename | Purpose |
|--------|----------|---------|
| **Parquet** | `training_data.parquet` | Primary - preserves types, compressed |
| **CSV** | `training_data.csv` | Human-readable, Nemotron compatible |
| **Excel** | `training_data.xlsx` | Nemotron Data Designer import |
| **JSON Lines** | `training_data.jsonl` | Streaming/NDJSON for pipelines |

---

## 📋 Column Reference (Complete List in Order)

| # | Column | Type | Category |
|---|--------|------|----------|
| 1 | `run_id` | string | Identifier |
| 2 | `design_name` | string | Identifier |
| 3 | `platform` | categorical | Identifier |
| 4 | `timestamp` | datetime | Identifier |
| 5 | `core_utilization` | float | Config |
| 6 | `core_aspect_ratio` | float | Config |
| 7 | `core_margin` | float | Config |
| 8 | `num_instances` | int | Design |
| 9 | `num_nets` | int | Design |
| 10 | `num_sequential` | int | Design |
| 11 | `num_macros` | int | Design |
| 11 | `log_instances` | float | Derived |
| 12 | `log_nets` | float | Derived |
| 13 | `seq_ratio` | float | Derived |
| 14 | `macro_ratio` | float | Derived |
| 15 | `platform_cat` | categorical | Derived |
| 16 | `design_name` | string | Derived |
| 17 | `final_wns_ns` | float | Target |
| 18 | `final_tns_ns` | float | Target |
| 19 | `final_area_um2` | float | Target |
| 20 | `final_power_mw` | float | Target |
| 21 | `final_drc_violations` | int | Target |
| 22 | `timing_closure_bin` | binary | Target |
| 23 | `drc_clean_bin` | binary | Target |
| 24 | `lvs_clean_bin` | binary | Target |
| 25 | `wns_normalized` | float | Normalized |
| 26 | `tns_normalized` | float | Normalized |
| 27 | `log_area` | float | Normalized |
| 28 | `log_power` | float | Normalized |
| 29 | `timing_closure_bin` | binary | Target |
| 30 | `drc_clean_bin` | binary | Target |
| 31 | `lvs_clean_bin` | binary | Target |
| 32 | `platform_cat` | categorical | Platform |
| 33 | `design_name` | string | Design |
| 34 | `core_utilization` | float | Config |
| 35 | `core_aspect_ratio` | float | Config |

---

## 📦 Delivery Formats Checklist

- [ ] `training_data.parquet` (Primary)
- [ ] `training_data.csv`
- [ ] `training_data.xlsx` (Nemotron Data Designer)
- [ ] `training_data.jsonl` (Streaming)

---

## ✅ Validation Checklist (Run After Generation)

```python
import polars as pl
df = pl.read_parquet('training_data.parquet')

# Size
assert len(df) == 3000

# Class balance
assert abs(df['timing_closure_bin'].mean() - 0.30) < 0.02
assert df['drc_clean_bin'].mean() == 0.85 ± 0.02

# Correlations
assert df['final_wns_ns'].corr(df['final_tns_ns']) > 0.8
assert df['num_instances'].corr(df['final_area_um2']) > 0.8

# Logical consistency
assert (df['timing_closure_bin'] == (df['final_wns_ns'] >= 0)).all()
assert (df['drc_clean_bin'] == (df['final_drc_violations'] == 0)).all()

# Platform distribution
platform_dist = df['platform'].value_counts(normalize=True).round(2).to_dict()
assert platform_dist == {'sky130hd': 0.30, 'asap7': 0.30, 'nangate45': 0.20, 'gf180': 0.20}

print("✅ All validation checks passed!")
```

---

## 🎯 Minimum Viable Synthetic Dataset

If constrained: **2,000 rows** with:
- 600 timing closure = 1
- 300 DRC violations > 0
- All 4 platforms represented
- All correlations within ±0.1 of targets above

---

## 📋 Design Name Pool (Real + Synthetic)

**Real (22):**
`alu4`, `alu_4bit`, `gcd`, `mock-cpu`, `Multiplier`, `multiplier_4bit`, `mux4x1`, `my_design`, `my_design2`, `sonibhai`, `Sample2`, `aes`, `comparator2bit`, `counter4`, `gcd`, `ibex`, `picorv32_pd`, `uart-blocks`, `riscv32i`, `tinyRocket`, `mux_2x1_behaviroal`, `nangate45_aes`

**Synthetic (50+):**
`fifo_8x32`, `spi_master`, `i2c_controller`, `uart_tx`, `uart_rx`, `pwm_gen`, `crc32`, `sha256_core`, `aes_encrypt`, `aes_decrypt`, `dma_controller`, `interrupt_ctrl`, `timer_32bit`, `gpio_ctrl`, `spi_slave`, `jtag_tap`, `riscv_core`, `picorv32`, `vexriscv`, `ibex_core`, `fpu_sp`, `fpu_dp`, `div_sqrt`, `mul_acc`, `fft_256`, `fir_filter`, `iir_filter`, `cordic`, `matrix_mul_4x4`, `conv2d_3x3`, `pooling_max`, `relu_activation`, `batch_norm`, `lstm_cell`, `gru_cell`, `attention_head`, `transformer_block`, `embed_lookup`, `pos_encoding`, `layer_norm`, `dropout_layer`, `residual_add`, `skip_connection`

---

## 📦 Output Files Checklist

- [ ] `training_data.parquet` (Primary)
- [ ] `training_data.csv`
- [ ] `training_data.xlsx` (Nemotron Data Designer)
- [ ] `training_data.jsonl` (Streaming)

---

## 📝 Notes for Nemotron Data Designer

1. **Import Excel** (`training_data.xlsx`) as reference dataset
2. **Set target size**: 3,000 rows
3. **Preserve correlations**: Enable correlation preservation mode
4. **Set class balance**: timing_closure=30%, drc_violations>0=15%
5. **Stratify by platform**: 30/30/20/20 split
6. **Preserve correlations**: WNS↔TNS (0.9), Instances↔Area (0.9), Area↔Power (0.65)
7. **Logical constraints**: Enable logical constraint enforcement (timing_closure ↔ WNS≥0, drc_clean ↔ DRC=0)
8. **Platform stratification**: 30/30/20/20 split

---

## 📝 Notes for Model Training

**Target Variables:**
- **Regression**: `final_wns_ns`, `final_tns_ns`, `final_area_um2`, `final_power_mw`
- **Classification**: `timing_closure_bin`, `drc_clean_bin`
- **Count**: `final_drc_violations`

**Feature Groups:**
- **Design**: `num_instances`, `num_nets`, `num_sequential`, `num_macros`, `seq_ratio`, `macro_ratio`
- **Config**: `core_utilization`, `core_aspect_ratio`, `core_margin`
- **Platform**: One-hot encoded `platform`
- **Derived**: `log_instances`, `log_nets`, `seq_ratio`, `macro_ratio`

**Suggested Models:**
- **Flow Optimizer (RL)**: PPO with state = [design_features, current_stage_metrics, stage_history]
- **Failure Predictor**: XGBoost/LightGBM on [design_features, config, stage_metrics]
- **Surrogate Models**: Neural net / GP for WNS/TNS/Area/Power prediction

---

*Generated: 2025-01-20 | OpenROAD Flow GUI Intelligence Module | Version 1.0*