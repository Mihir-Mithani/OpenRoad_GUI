# ORFS Data Collection - Complete Deliverables

## 📦 Delivered Files

### 1. Master Collection Script
**`orfs_data_collection_master.py`** - Main orchestration script
- Multi-platform, multi-design data collection
- Parallel execution with configurable workers (default: 4)
- Resume capability with checkpointing
- Progress tracking with ETA
- Remote execution via SSH
- Retry logic with exponential backoff
- Automatic result aggregation
- Resume capability with checkpointing

### 2. Quick Start Script
**`collect_data_quickstart.sh`** - One-command setup and execution
- Auto-detects ORFS installation
- Installs missing Python dependencies
- Configurable platforms, workers, output
- Remote execution support via SSH
- Resume capability

### 3. Requirements
**`requirements_data_collection.txt`** - Python dependencies
```
numpy>=1.21.0
pandas>=1.3.0
polars>=0.18.0
scikit-learn>=1.0.0
lightgbm>=3.3.0
torch>=1.12.0
scipy>=1.7.0
matplotlib>=3.5.0
seaborn>=0.11.0
pyyaml>=6.0
paramiko>=2.11.0
tqdm>=4.64.0
```

---

## 🚀 Quick Start

### Local Collection (Single Machine)
```bash
# Make script executable
chmod +x collect_data_quickstart.sh

# Run with defaults (all platforms, 4 workers)
./collect_data_quickstart.sh

# Custom platforms and workers
./collect_data_quickstart.sh --platforms asap7,sky130hd,gf180 --workers 8

# Resume interrupted collection
./collect_data_quickstart.sh --resume

# Custom output directory
./collect_data_quickstart.sh --output ./my_collected_data
```

### Remote Collection (SSH)
```bash
# Collect on remote machine via SSH
./collect_data_quickstart.sh \
    --remote-host user@remote-server \
    --remote-user ubuntu \
    --remote-orfs-root ~/OpenROAD-flow-scripts \
    --ssh-key ~/.ssh/id_rsa \
    --platforms sky130hd,gf180
```

### Direct Python Usage
```bash
python3 orfs_data_collection_master.py \
    --orfs-root ~/OpenROAD-flow-scripts \
    --platforms asap7 sky130hd gf180 \
    --workers 8 \
    --output ./my_collected_data \
    --resume
```

---

## 📊 Output Structure

```
collected_data/
├── all_collected_records.json      # All collected records (JSON)
├── training_data.json              # Prepared for training (JSON)
├── collection_summary.json         # Collection summary
├── collection_state.pkl            # Resume checkpoint
├── results/                        # Individual design results
│   ├── asap7_alu4.json
│   ├── sky130hd_gcd.json
│   └── ...
└── collection_summary.json         # Final summary
```

---

## 📋 Generated Data Format

Each collected record contains:

```json
{
  "run_id": "riscv32i_gf180_20241116_123456",
  "timestamp": "2024-11-16T12:34:56.789",
  "design_name": "riscv32i",
  "platform": "gf180",
  "status": "success",
  "core_utilization": 20.0,
  "core_aspect_ratio": 1.0,
  "core_margin": 4.0,
  "place_density": 0.4,
  "final_wns_ns": -0.03,
  "final_tns_ns": -0.07,
  "final_area_um2": 364790.0,
  "final_power_mw": 280.894,
  "final_drc_violations": 2,
  "final_setup_violations": 2,
  "final_hold_violations": 0,
  "stage_runtimes": {"synth": 45.2, "place": 120.5, ...},
  "total_runtime_sec": 1250.3,
  "timing_closure": false,
  "drc_clean": false,
  "lvs_clean": true,
  "data_completeness": "complete"
}
```

---

## 🔧 Configuration

### Platforms Supported
| Platform | Example Designs |
|----------|----------------|
| asap7 | alu4, adder, multiplier, riscv32i |
| sky130hd | gcd, uart, spi, i2c, pwm, riscv32i |
| nangate45 | picorv32, aes, des, sha256, riscv32i |
| gf180 | riscv32i, jpeg, aes, gcd, uart-blocks, ibex |
| ihp-sg13g2 | adc, dac, pll, ldo |

### Custom Designs per Platform
```bash
# JSON format
--designs '{"asap7": ["alu4", "adder"], "gf180": ["riscv32i", "jpeg"]}'
```

---

## 📊 Resume Capability

The script automatically saves checkpoints every 10 designs. If interrupted:

```bash
# Resume from last checkpoint
./collect_data_quickstart.sh --resume

# Or with Python directly
python3 orfs_data_collection_master.py --resume --output ./collected_data
```

Checkpoint file: `collected_data/collection_state.pkl`

---

## 📊 Generated Training Data

After collection, training data is automatically prepared:

```bash
# training_data.json format
{
  "run_id": "...",
  "design_name": "riscv32i",
  "platform": "gf180",
  "core_utilization": 20.0,
  "core_aspect_ratio": 1.0,
  "core_margin": 4.0,
  "num_instances": 2431,
  "num_nets": 2917,
  "num_sequential": 486,
  "final_wns_ns": -0.03,
  "final_tns_ns": -0.07,
  "final_area_um2": 364790.0,
  "final_power_mw": 280.894,
  "final_drc_violations": 2,
  "timing_closure": false,
  "drc_clean": false,
  "suitable_for_regression": true,
  "log_instances": 0.34,
  "log_nets": 0.35,
  "seq_ratio": 0.2,
  "macro_ratio": 0.0,
  "timing_closure_bin": 0,
  "drc_clean_bin": 0
}
```

---

## 🎯 Next Steps After Collection

### 1. Train Models
```bash
# Train all models (surrogate, failure predictor, RF)
python -m openroad_gui.intelligence.training.train_all_v3 \
    --aws-data ./collected_data/aws_real_runs_comprehensive.json \
    --epochs 200 --device cuda
```

### 2. Train Individual Models
```bash
# Surrogate models (LightGBM + MLP)
python -m openroad_gui.intelligence.training.train_surrogate_v2 \
    --real-data ./collected_data/real_runs_training.json \
    --epochs 200 --device cuda --ensemble --cv-folds 5

# Failure predictor (LightGBM classifiers)
python -m openroad_gui.intelligence.training.train_failure_predictor \
    --real-data ./collected_data/real_runs_training.json

# Random Forest models
python -m openroad_gui.intelligence.training.train_rf --target all
```

### 3. Train PPO Flow Optimizer (on GPU)
```bash
# On Google Colab or GPU machine
python -m openroad_gui.intelligence.training.train_flow_optimizer \
    --timesteps 500000 --n-envs 8 --device cuda
```

### 4. Full Pipeline
```bash
# Complete pipeline from data to trained models
python -m openroad_gui.intelligence.training.train_all_v3 \
    --aws-data ./collected_data/aws_real_runs_comprehensive.json \
    --epochs 200 --device cuda
```

---

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| ORFS not found | Set `--orfs-root` to correct path |
| Python dependencies missing | Run `pip install -r requirements_data_collection.txt` |
| Design fails to collect | Check `--resume` flag, check logs in `./collected_data/` |
| Remote connection fails | Check SSH keys, `--ssh-key` path |
| Design fails repeatedly | Check `--max-retries`, increase `--timeout` |

### Debug Mode
```bash
./collect_data_quickstart.sh --log-level DEBUG --workers 1
```

---

## 📁 File Inventory

```
OpenRoad-GUI/
├── orfs_data_collection_master.py      # Main orchestrator
├── collect_data_quickstart.sh          # Quick start script
├── requirements_data_collection.txt    # Python dependencies
├── openroad_gui/
│   └── intelligence/
│       └── data/
│           ├── collect_real_data.py    # Core collector
│           ├── parser.py               # Log/report parser
│           ├── features.py             # Feature engineering
│           ├── prepare_real_training_data.py  # Training prep
│           ├── collector.py            # Historical collector
│           └── ...
└── requirements_data_collection.txt    # Python deps
```

---

## 🎯 Next Steps After Collection

1. **Review collected data**: `cat collected_data/collection_summary.json`
2. **Train models**: Run training scripts above
3. **Deploy models**: Models save to `openroad_gui/intelligence/models/saved/`
4. **Use in GUI**: Launch `python -m openroad_gui` to use trained models
5. **Iterate**: Collect more data → retrain → improve

---

## 📞 Support

For issues:
1. Check `./collected_data/` for logs
2. Enable debug: `--log-level DEBUG`
3. Reduce workers: `--workers 1`
4. Increase timeout: `--timeout 10800`

---

*Generated for OpenRoad-GUI v3.0+ | Compatible with OpenROAD Flow Scripts*