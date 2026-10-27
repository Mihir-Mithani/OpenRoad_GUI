# Colab RL Training Package

Self-contained package for training PPO Flow Optimizer in Google Colab.
No repo clone needed — just upload this folder to Google Drive.

## 📁 Package Structure

```
colab_rl_package/
├── models/                    # Surrogate models (reward function)
│   ├── surrogate_wns_mlp.pt      # WNS predictor (PyTorch)
│   ├── surrogate_tns_mlp.pt      # TNS predictor (PyTorch)
│   ├── surrogate_area_mlp.pt     # Area predictor (PyTorch)
│   ├── surrogate_power_mlp.pt    # Power predictor (PyTorch)
│   ├── surrogate_preprocessor.pkl # Feature preprocessor (sklearn)
│   └── create_preprocessor.py    # Script to recreate preprocessor
├── designs/
│   └── designs.csv               # 100+ design configurations
├── training/
│   └── train_ppo_colab.py        # Self-contained Colab training script
└── config/
    └── (reserved for future config)
```

## 🚀 Quick Start in Google Colab

### 1. Upload to Google Drive
- Zip this `colab_rl_package` folder
- Upload to Google Drive (e.g., `MyDrive/colab_rl_package`)

### 2. Open Colab Notebook
```python
# Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Navigate to package
%cd /content/drive/MyDrive/colab_rl_package/training

# Install dependencies
!pip install stable-baselines3[extra] gymnasium torch pandas scikit-learn joblib polars -q

# Train
!python train_ppo_colab.py --timesteps 200000 --device cuda
```

### 3. Monitor Training
```python
# TensorBoard
%load_ext tensorboard
%tensorboard --logdir ./logs
```

## 📦 Model Files Included

| File | Description |
|------|-------------|
| `surrogate_wns_mlp.pt` | WNS predictor (MLP) |
| `surrogate_tns_mlp.pt` | TNS predictor (MLP) |
| `surrogate_area_mlp.pt` | Area predictor (MLP) |
| `surrogate_power_mlp.pt` | Power predictor (MLP) |
| `surrogate_preprocessor.pkl` | sklearn ColumnTransformer |

**Note**: Only MLP models included (LightGBM not included to avoid `onnxmltools` dependency in Colab).

## 📊 Design Configurations

`designs/designs.csv` contains 100+ synthetic designs covering:
- **Platforms**: sky130hd, asap7, nangate45, gf180
- **Tiers**: tiny (5K), medium (50K), large (200K) instances
- **Utilization**: 15-60% per platform spec
- **Aspect ratios**: 0.5, 1.0, 1.5, 2.0

## 🎯 Training Command

```bash
# In Colab, after mounting drive and installing deps:
cd /content/drive/MyDrive/colab_rl_package/training
python train_ppo_colab.py --timesteps 200000 --device cuda --n-envs 4
```

### Arguments
| Arg | Default | Description |
|-----|---------|-------------|
| `--timesteps` | 200000 | Total training steps |
| `--n-envs` | 4 | Parallel environments |
| `--device` | auto | `auto`, `cpu`, or `cuda` |

## 📊 Output

```
models/
├── ppo_flow_optimizer_final.zip      # Final PPO model
├── best/                             # Best eval model
├── ppo_flow_optimizer_*.zip          # Checkpoints
└── ppo_flow_optimizer.onnx           # ONNX export
```

## 🔧 Customization

### Add Real Designs
Replace `designs/designs.csv` with your real ORFS designs:
```csv
design_name,platform,core_utilization,core_aspect_ratio,core_margin,num_instances,num_nets,num_sequential,num_macros,macro_area_ratio
my_aes,sky130hd,40,1.0,5,45000,54000,9000,4,0.12
```

### Adjust Reward Weights
Edit `reward_weights` in `FlowOptEnv.__init__`:
```python
self.reward_weights = {
    "wns": 0.30, "tns": 0.15, "area": 0.15,
    "power": 0.10, "drc": 0.15, "congestion": 0.10, "runtime": 0.05
}
```

### Use Real Surrogate Models
Replace `.pt` files in `models/` with your retrained models (run `train_surrogate.py` locally first).

## 📝 Requirements

```bash
pip install stable-baselines3[extra] gymnasium torch pandas scikit-learn joblib polars
```

- Python 3.10+
- CUDA 11.8+ (for GPU training)
- 8GB+ RAM recommended

## 📝 License

Part of OpenROAD Flow GUI project.