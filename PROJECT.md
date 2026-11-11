# OpenROAD Flow GUI - Project Documentation

## Project Overview
OpenROAD Flow GUI is a Python-based desktop application (tkinter, stdlib only) that wraps OpenROAD Flow Scripts (ORFS) to automate the RTL-to-GDSII flow. It provides a professional EDA workstation interface with AI-assisted intelligence for failure prediction, parameter optimization, and surrogate PPA modeling.

## Dataset Summary (as of Session 15 - 2025-11-07)

### Master Dataset Statistics
| Metric | Value |
|--------|-------|
| **Total Runs** | 150 |
| **Platforms** | 4 (asap7, gf180, nangate45, sky130hd) |
| **Unique Designs** | 10 |
| **Area Coverage** | 92% (138/150) |
| **Power Coverage** | 92% (138/150) |
| **WNS/TNS Coverage** | 84.7% (127/150) |
| **Timing Closure Rate** | 28.3% (36/127 runs with WNS) |
| **Overall Timing Closure** | 18% (27/150 runs) |

### Platform Distribution
| Platform | Runs | Designs | Timing Closure | Key Designs |
|----------|------|---------|----------------|-------------|
| asap7 | 38 | 3 | 36.8% (14/38) | aes, gcd, riscv32i-mock-sram |
| gf180 | 44 | 4 | 29.5% (13/44) | gcd, jpeg, riscv32i, uart-blocks |
| nangate45 | 38 | 3 | 23.7% (9/38) | aes, dynamic_node, ibex |
| sky130hd | 30 | 2 | 0% (0/30) | aes, gcd |

### Design Distribution
| Platform | Design | Runs | Status |
|----------|--------|------|--------|
| asap7 | aes | 5 | Mixed |
| asap7 | gcd | 10 | Mixed |
| asap7 | riscv32i-mock-sram | 23 | Sweep (13 new) |
| gf180 | gcd | 11 | Mixed |
| gf180 | jpeg | 9 | Mixed (sweep + main) |
| gf180 | riscv32i | 11 | Sweep |
| gf180 | uart-blocks | 13 | 100% closure |
| nangate45 | aes | 14 | 13 failed (sweep), 1 success |
| nangate45 | dynamic_node | 10 | Sweep (success) |
| nangate45 | ibex | 14 | Sweep (mixed) |
| sky130hd | aes | 10 | Success (sweep) |
| sky130hd | gcd | 20 | Sweep (mixed) |

## File Structure & Locations

### Core Application Files
```
/Users/mihirmithani/Downloads/OpenRoad GUI/
├── main.py                          # Entry point
├── PROJECT.md                       # This file
├── LOG.md                           # Development log (15 sessions)
├── CLAUDE.md                        # Project instructions
├── requirements.txt                 # Dependencies (stdlib only)
├── setup.py                         # Package setup
├── pyproject.toml                   # Build config
├── openroad_gui/                    # Main package
│   ├── __init__.py                  # Package init, version
│   ├── app.py                       # Main window (OpenRoadGUI class)
│   ├── config.py                    # AppConfig, paths, validation
│   ├── flow_runner.py               # FlowRunner, FlowStage, FULL_PIPELINE
│   ├── viewers.py                   # ViewerService, KLayout, OpenROAD GUI
│   ├── templates.py                 # Design templates (verilog, sdc, config.mk)
│   ├── gds_info.py                  # GDSII parser (stdlib only)
│   ├── signoff.py                   # DRC/LVS result parsing
│   ├── theme.py                     # ThemeManager (Light/Dark mode)
│   ├── signoff.py                   # DRC/LVS result parsing
│   ├── intelligence/                # AI/ML modules
│   │   ├── __init__.py              # Exports
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── failure_predictor.py # FailurePredictor (LightGBM)
│   │   │   ├── flow_optimizer.py    # RL optimizer (FlowState, FlowAction)
│   │   │   └── saved/               # Trained models
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── collector.py         # Data collection from ORFS
│   │   │   ├── features.py          # Feature engineering
│   │   │   └── parser.py            # Report parsing
│   │   ├── training/                # Training pipelines
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py          # Training pipeline
│   │   │   ├── train_surrogate.py   # Surrogate models
│   │   │   ├── train_failure_predictor.py
│   │   │   ├── train_flow_optimizer.py
│   │   │   └── train_all.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── metrics.py
│   │   │   └── onnx_export.py       # ONNX export
│   │   └── tests/
│   └── widgets/                     # UI components
│       ├── __init__.py
       │   ├── flow_panel.py         # Legacy flow panel
      │   ├── pipeline_row.py        # Pipeline visualization
      │   ├── preview_panel.py       # File preview (text/GDS)
      │   ├── project_tree.py        # Project tree view
      │   ├── log_viewer.py          # Log viewer with PTY terminal
      │   ├── settings_dialog.py     # Settings dialog
      │   └── sidebar.py             # Sidebar (legacy)
```

### Data Files
```
/Users/mihirmithani/Downloads/OpenRoad GUI/
├── openroad_gui/intelligence/data/
│   ├── real_runs.json              # Master dataset (150 runs)
│   ├── real_runs_export.csv        # CSV export (150 rows)
│   ├── aws_real_runs.json          # Latest AWS extraction
│   ├── aws_real_runs_all.json      # All extractions combined
│   ├── aws_real_runs_comprehensive.json
│   ├── aws_real_runs_gf180.json
│   ├── aws_real_runs_gf180_riscv32i.json
│   ├── aws_real_runs_ibex_sweep.json
│   ├── aws_real_runs_ip172_31_47_219.json
│   ├── aws_real_runs_new_sweep.json
│   ├── aws_real_runs_nangate45.json
│   ├── aws_real_runs_new_sweep.json
│   ├── collect_real_data.py        # Data collection script
│   ├── collector.py                # Data collector
│   ├── features.py                 # Feature engineering
│   ├── parser.py                   # Report parser
│   ├── real_runs.json              # Alternative master
│   ├── real_runs_export.csv        # CSV export
│   ├── real_runs_asap7.json
│   ├── real_runs_gf180.json
│   ├── real_runs_nangate45.json
│   └── real_runs_sky130hd.json
```

### Extraction Scripts
```
/Users/mihirmithani/Downloads/OpenRoad GUI/
├── extract_comprehensive_aws.py    # Main extractor (all platforms + sweeps)
├── extract_aws_data.py             # Basic AWS extractor
├── extract_parameter_sweep.py      # ip-172-31-32-99 sweep extractor
├── extract_ip172_31_47_219_sweep.py # ip-172-31-47-219 sweep extractor
├── extract_new_sweep.py            # New sweep extractor
├── extract_comprehensive_aws.py    # Comprehensive extractor
├── extract_parameter_sweep.py      # Parameter sweep extractor
├── cleanup_aws_report.py           # Cleanup large files (.odb, .gds, .def, .spef)
├── run_full_pipeline.py            # Full pipeline orchestrator
├── run_config_sweeps.py            # Config sweep runner
├── visualize_final.py              # Visualization suite (14 plots)
├── visualize_all.py                # Visualization suite (13 plots)
├── visualize_nangate45.py
└── visualize_final.py
```

### Training & Intelligence
```
/Users/mihirmithani/Downloads/OpenRoad GUI/
├── openroad_gui/intelligence/training/
│   ├── train_surrogate.py          # Surrogate model training
│   ├── train_failure_predictor.py  # Failure predictor training
│   ├── train_flow_optimizer.py     # Flow optimizer training
│   ├── train_all.py                # Unified training
│   ├── pipeline.py                 # Training pipeline
│   └── train_all_v2.py
├── openroad_gui/intelligence/models/saved/
│   ├── surrogate_wns_lgb.pkl
│   ├── surrogate_tns_lgb.pkl
│   ├── surrogate_area_lgb.pkl
│   ├── surrogate_power_lgb.pkl
│   ├── surrogate_*_mlp.pt
│   ├── surrogate_preprocessor_v2.pkl
│   ├── timing_closure_lgb.pkl
│   ├── drc_clean_lgb.pkl
│   ├── flow_optimizer_ppo.pt
│   └── ppo_flow_*.zip
```

### Visualization Outputs
```
/Users/mihirmithani/Downloads/OpenRoad GUI/visualizations/
├── 1a_outcomes_by_platform.png
├── 1b_closure_rate_util_density.png
├── 2a_wns_evolution_by_platform.png
├── 2b_wns_improvement_waterfall.png
├── 3a_knob_effects_box.png
├── 3b_parallel_coordinates.png
├── 3c_spearman_correlation.png
├── 4a_power_vs_violations_loglog.png
├── 4b_runtime_ecdf.png
├── 4c_runs_per_design.png
├── 5_timeline_gantt.png
├── 6_design_facet_wns_evolution.png
├── 7_normalized_within_design.png
```

### AWS Report Structure
```
/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report/
├── asap7/                          # 16 designs, 38 runs
├── gf180/                          # 7 designs, 44 runs
├── nangate45/                      # 18 designs, 38 runs
├── sky130hd/                       # 1 design (gcd), 1 run
├── parameter_sweep/
│   ├── ip-172-31-32-99/            # Old sweep
│   │   ├── asap7/ (aes, ibex)
│   │   ├── gf180/ (gcd, jpeg, uart-blocks, riscv32i)
│   │   └── nangate45/ (ibex, dynamic_node, aes)
│   └── ip-172-31-47-219/           # New sweep
│       ├── asap7/ (riscv32i-mock-sram, gcd, aes)
│       ├── gf180/ (jpeg, riscv32i, gcd)
│       └── sky130hd/ (gcd, aes)
```

## Key Features

### Core Application
- **tkinter-based GUI** (stdlib only, no external deps)
- **Real-time flow execution** with subprocess streaming
- **Multi-platform support** (asap7, gf180, nangate45, sky130hd, ihp-sg13g2, gf12)
- **Live log streaming** with color-coded stdout/stderr
- **Interactive terminal** with PTY support
- **GDS preview** via KLayout batch rendering
- **Project tree** with context menus
- **Dark/Light theme** support

### Intelligence Module
- **Surrogate Models**: LightGBM + MLP ensemble for WNS, TNS, Area, Power prediction
- **Failure Predictor**: LightGBM classifier (AUC 0.755) for timing closure prediction
- **Flow Optimizer**: RL-based parameter optimization (PPO)
- **ONNX Export**: Model deployment ready
- **Feature Engineering**: 13 features from config + runtime metrics

### Data Pipeline
- **Real ORFS Data Collection**: Extracts from AWS_Report completed runs
- **Synthetic Data Generation**: Statistical blending with SPEC targets
- **Feature Engineering**: 13 features (platform, utilization, instance counts, etc.)
- **Target Normalization**: Log-transform for area/power, clip for WNS/TNS

## Key Sessions Timeline

| Session | Date | Key Achievement |
|---------|------|-----------------|
| 1 | 2026-07-23 | Layout restructuring, resizable log window |
| 2 | 2025-10-26 | Intelligence module fixes, data collector fixes |
| 3 | 2025-10-27 | Complete intelligence pipeline, ONNX export |
| 4 | 2025-11-03 | AWS_Report extraction, gf180/uart-blocks sweep |
| 5 | 2025-11-04 | Parameter sweep extraction (60 designs) |
| 6 | 2025-11-04 | New parameter sweep extraction (gf180/riscv32i) |
| 7 | 2025-11-04 | GUI integration, tkinter fix on macOS |
| 8 | 2025-11-05 | gf180/uart-blocks & sky130hd/gcd sweeps |
| 9 | 2025-11-05 | sky130hd/gcd sweep extraction |
| 10 | 2025-11-04 | gf180/riscv32i sweep extraction |
| 11 | 2025-11-05 | gf180/uart-blocks & sky130hd/gcd sweeps |
| 12 | 2025-11-05 | sky130hd/gcd + gf180/uart-blocks sweeps |
| 13 | 2025-11-05 | gf180/uart-blocks & sky130hd/gcd sweeps |
| 14 | 2025-11-06 | Area/power parsing fix, 14.2GB cleanup |
| 15 | 2025-11-07 | New sweep batches (nangate45/aes, sky130hd/aes) |

## Test Suite
```
tests/
├── test_config.py           # Config validation, serialization
├── test_flow_runner.py      # FlowRunner, FlowStage, FULL_PIPELINE
├── test_templates.py        # Template generation
└── test_gds_info.py         # GDSII parser

Total: 91 tests, all passing
```

## Running the Application
```bash
cd /Users/mihirmithani/Downloads/OpenRoad\ GUI
python3 main.py
# or
python3 -m openroad_gui
```

## Running Extractions
```bash
# Full pipeline
python3 run_full_pipeline.py --aws-root /path/to/ORFS --steps 1 2 3 4 5

# Individual steps
python3 extract_comprehensive_aws.py --aws-root /path/to/ORFS --include-failed
python3 cleanup_aws_report.py --aws-root /path/to/AWS_Report
```

## Running Visualizations
```bash
python3 visualize_final.py      # 14 plots (modern)
python3 visualize_all.py        # 13 plots (comprehensive)
```

## Training Models
```bash
# Surrogate models
python3 -m openroad_gui.intelligence.training.train_surrogate --ensemble --epochs 300

# Failure predictor
python3 -m openroad_gui.intelligence.training.train_failure_predictor

# Flow optimizer (PPO)
python3 -m openroad_gui.intelligence.training.train_flow_optimizer

# Full pipeline
python3 -m openroad_gui.intelligence.training.train_all_v2 --ensemble --epochs 300
```

## Key Environment Variables
- `ORFS_ROOT` - OpenROAD Flow Scripts root path
- `OPENROAD_FLOW_SCRIPTS` - Alternative ORFS path
- `KLAYOUT_CMD` - KLayout binary path (auto-detected if not set)

## Dataset Quality Metrics (150 runs)
| Metric | Value |
|--------|-------|
| Runs with WNS/TNS | 127/150 (84.7%) |
| Runs with Area | 125/150 (83.3%) |
| Runs with Power | 125/150 (83.3%) |
| Timing Closure | 27/150 (18%) |
| Timing Closure (of runs with WNS) | 36/127 (28.3%) |
| Field Completeness | 100% core fields |
| NaN Values | 0 |
| Timing Closure Consistency | 100% (no mismatches) |

## Recent Sweep Results
### nangate45/aes (ip-172-31-32-99) - 13 configs
- **Status**: ALL FAILED - Floorplan config conflict
- **Error**: `Floorplan initialization methods are mutually exclusive`
- **Root cause**: Config has both `FLOORPLAN_DEF` (fixed floorplan) AND utilization/aspect_ratio/margin params

### sky130hd/aes (ip-172-31-47-219)
- 9 sweep configs + 1 existing = 10 runs
- **All SUCCESS** with PPA data
- First successful sky130hd aes runs!

### sky130hd/gcd
- 20 runs total (10 original + 10 new sweep)
- 0% timing closure (all WNS < 0)

### gf180/uart-blocks (ip-172-31-32-99)
- 13 sweep configs
- **100% timing closure** across ALL configurations
- Only design with 100% closure rate

## Cleanup Status
- **14.2 GB freed** (1,192 files: .odb, .gds, .def, .spef)
- Failed nangate45/aes sweep removed (~80 MB)
- Duplicate sweep folders cleaned
- Main platform results preserved (intermediate files kept)

## Test Status
```
All 91 tests passing:
  test_config.py: 28 tests
  test_flow_runner.py: 14 tests
  test_templates.py: 36 tests
  test_gds_info.py: 13 tests
```

## Known Issues / Future Work
1. **sky130hd timing closure**: 0% across all designs - needs config tuning
2. **nangate45/aes**: Floorplan config conflict needs resolution
3. **Area/Power coverage**: 17 runs missing (failed/partial runs)
4. **sky130hd platform**: Only 2 designs, need more diversity
5. **Model training**: Need more real data for better surrogate accuracy