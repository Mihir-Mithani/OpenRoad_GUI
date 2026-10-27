#!/usr/bin/env python3
"""
Colab RL Training - One-Click Setup & Train Script
Run this single cell in Colab after uploading colab_rl_package.zip to Google Drive.
"""

import os
import sys
import subprocess
import zipfile
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────
ZIP_PATH = "/content/drive/MyDrive/colab_rl_package.zip"  # Update if different location
EXTRACT_DIR = "/content/colab_rl_package"
TRAINING_DIR = "/content/colab_rl_package/training"
MODELS_DIR = "/content/colab_rl_package/models"
DESIGNS_DIR = "/content/colab_rl_package/designs"

# ─── Helper Functions ───────────────────────────────────────────────────
def run(cmd, check=True, capture=False):
    """Run shell command with nice output."""
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr and "WARNING" not in result.stderr and "UserWarning" not in result.stderr:
        print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return result

def setup_gpu():
    """Verify and configure GPU."""
    import torch
    if torch.cuda.is_available():
        print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA: {torch.version.cuda}")
        return "cuda"
    else:
        print("⚠️  No GPU detected - using CPU")
        return "cpu"

# ─── Main Setup ─────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🚀 Colab RL Training - One-Click Setup")
    print("=" * 60)

    # 1. Mount Google Drive
    print("\n📁 Mounting Google Drive...")
    from google.colab import drive
    drive.mount('/content/drive')

    # 2. Unzip package
    print(f"\n📦 Extracting {ZIP_PATH}...")
    if not Path(ZIP_PATH).exists():
        raise FileNotFoundError(f"Zip not found at {ZIP_PATH}. Upload colab_rl_package.zip to Google Drive first.")

    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        zf.extractall(EXTRACT_DIR)
    print(f"✅ Extracted to {EXTRACT_DIR}")

    # 3. Verify structure
    for d in [MODELS_DIR, DESIGNS_DIR]:
        if not Path(d).exists():
            raise FileNotFoundError(f"Missing directory: {d}")
    print(f"✅ Models: {len(list(Path(MODELS_DIR).glob('*.pkl')))} LightGBM + {len(list(Path(MODELS_DIR).glob('*.pt')))} PyTorch")
    print(f"✅ Designs: {len(list(Path(DESIGNS_DIR).glob('*.csv')))} CSV files")

    # 4. Install dependencies (with correct sklearn version)
    print("\n📦 Installing dependencies...")
    run("pip install -q scikit-learn==1.9.1 stable-baselines3[extra] gymnasium torch pandas polars joblib")

    # 5. Verify GPU
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if torch.cuda.is_available():
        print(f"🚀 GPU: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA: {torch.version.cuda}")
    else:
        print("⚠️  No GPU - using CPU")

    # 6. Train
    print("\n🚀 Starting PPO Training...")
    os.chdir("/content/colab_rl_package/training")

    cmd = [
        sys.executable, "train_ppo_colab.py",
        "--timesteps", "200000",
        "--device", "cuda" if torch.cuda.is_available() else "cpu",
        "--n-envs", "4",
    ]

    print(f"\n🚀 Running: {' '.join(cmd)}")
    print("=" * 60)

    # Run training with live output
    result = subprocess.run(
        [sys.executable, "train_ppo_colab.py",
         "--timesteps", "200000",
         "--device", "cuda" if torch.cuda.is_available() else "cpu",
         "--n-envs", "4"],
        cwd=TRAINING_DIR
    )

    if result.returncode == 0:
        print("\n✅ Training completed successfully!")
        print(f"📁 Models saved to: /content/colab_rl_package/training/../models/")
    else:
        print(f"\n❌ Training failed with exit code {result.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()