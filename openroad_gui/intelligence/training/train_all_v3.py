#!/usr/bin/env python3
"""
Unified Training Pipeline for OpenROAD Intelligence Models v3
Uses pre-extracted AWS real run data instead of collecting from ORFS.
Real data only - no synthetic data.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"\n❌ FAILED: {description}")
        return False
    print(f"\n✅ SUCCESS: {description}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Unified training pipeline for OpenROAD intelligence (AWS real data only)")
    parser.add_argument("--aws-data", type=Path, default=None,
                        help="Path to AWS comprehensive data (default: auto-detect)")
    parser.add_argument("--epochs", type=int, default=200, help="MLP training epochs")
    parser.add_argument("--device", type=str, default="cpu", choices=["cpu", "mps", "cuda"])
    parser.add_argument("--skip-prepare", action="store_true", help="Skip data preparation, only train")
    parser.add_argument("--skip-train", action="store_true", help="Skip training, only prepare data")
    parser.add_argument("--cv-folds", type=int, default=5, help="CV folds for evaluation")
    args = parser.parse_args()

    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
    AWS_COMPREHENSIVE_PATH = PROJECT_ROOT / "openroad_gui" / "intelligence" / "data" / "aws_real_runs_comprehensive.json"
    REAL_DATA_PATH = PROJECT_ROOT / "openroad_gui" / "intelligence" / "data" / "real_runs_training.json"

    # Use provided AWS data path or auto-detect
    if args.aws_data:
        aws_path = args.aws_data
    elif AWS_COMPREHENSIVE_PATH.exists():
        aws_path = AWS_COMPREHENSIVE_PATH
    else:
        print(f"❌ AWS comprehensive data not found at {AWS_COMPREHENSIVE_PATH}")
        print("   Please run the extraction script first or provide --aws-data path")
        return 1

    print("🚀 OpenROAD Intelligence Unified Training Pipeline v3 (AWS Real Data Only)")
    print(f"   AWS Data: {aws_path}")
    print(f"   Device: {args.device}")
    print(f"   CV Folds: {args.cv_folds}")

    # Step 1: Prepare training data from AWS comprehensive data
    if not args.skip_prepare:
        print(f"\n📊 Preparing training data from AWS reports...")
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "openroad_gui" / "intelligence" / "data" / "prepare_real_training_data.py")
        ]
        if not run_command(cmd, "Prepare real training data"):
            return 1
    else:
        print("\n⏭️ Skipping data preparation (--skip-prepare)")

    # Verify training data exists
    if not REAL_DATA_PATH.exists():
        print(f"❌ Training data not found at {REAL_DATA_PATH}")
        return 1

    # Step 2: Train surrogate models (real data only)
    if not args.skip_train:
        print(f"\n🧠 Training surrogate models...")
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "openroad_gui" / "intelligence" / "training" / "train_surrogate_v2.py"),
            "--real-data", str(REAL_DATA_PATH),
            "--epochs", str(args.epochs),
            "--device", args.device,
            "--ensemble",
            "--cv-folds", str(args.cv_folds)
        ]
        if not run_command(cmd, "Train surrogate models v2"):
            return 1

    # Step 3: Train failure predictor
    if not args.skip_train:
        print(f"\n🎯 Training failure predictor...")
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "openroad_gui" / "intelligence" / "training" / "train_failure_predictor.py"),
            "--real-data", str(REAL_DATA_PATH)
        ]
        if not run_command(cmd, "Train failure predictor"):
            return 1

    # Step 4: Train Random Forest models
    if not args.skip_train:
        print(f"\n🌲 Training Random Forest models...")
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "openroad_gui" / "intelligence" / "training" / "train_rf.py"),
            "--target", "all"
        ]
        run_command(cmd, "Train Random Forest models")

    # Step 5: Train flow optimizer (PPO) - run on Google Colab
    if not args.skip_train:
        print(f"\n🤖 Training flow optimizer (PPO) - run on Google Colab")
        print("   Use: python -m openroad_gui.intelligence.training.train_flow_optimizer --timesteps 500000 --n-envs 8 --device cuda")
        print("   Models will save to: openroad_gui/intelligence/models/saved/")

    print("\n🎉 Pipeline complete!")
    print(f"   Training data: {REAL_DATA_PATH}")
    print(f"   Models: {PROJECT_ROOT / 'openroad_gui' / 'intelligence' / 'models' / 'saved'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())