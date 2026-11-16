#!/usr/bin/env python3
"""
Unified Training Pipeline for OpenROAD Intelligence Models
Runs data collection + model training in sequence.
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
    parser = argparse.ArgumentParser(description="Unified training pipeline for OpenROAD intelligence (real data only)")
    parser.add_argument("--orfs-root", type=str, required=True, help="ORFS root directory")
    parser.add_argument("--platforms", nargs="+", default=["asap7", "sky130hd", "nangate45", "gf180"],
                        help="Platforms to collect data from")
    parser.add_argument("--epochs", type=int, default=200, help="MLP training epochs")
    parser.add_argument("--device", type=str, default="cpu", choices=["cpu", "mps", "cuda"])
    parser.add_argument("--skip-collect", action="store_true", help="Skip data collection, only train")
    parser.add_argument("--skip-train", action="store_true", help="Skip training, only collect data")
    args = parser.parse_args()

    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
    REAL_DATA_PATH = PROJECT_ROOT / "openroad_gui" / "intelligence" / "data" / "real_runs.json"

    print("🚀 OpenROAD Intelligence Unified Training Pipeline (Real Data Only)")
    print(f"   ORFS Root: {args.orfs_root}")
    print(f"   Platforms: {args.platforms}")
    print(f"   Device: {args.device}")

    # Step 1: Collect real data from ORFS
    if not args.skip_collect:
        for platform in args.platforms:
            print(f"\n📊 Collecting data for platform: {platform}")
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "openroad_gui" / "intelligence" / "data" / "collect_real_data.py"),
                "--orfs-root", args.orfs_root,
                "--platform", platform,
                "--output", str(REAL_DATA_PATH.with_suffix(f".{platform}.json"))
            ]
            if not run_command(cmd, f"Collect real data for {platform}"):
                print(f"Warning: Collection failed for {platform}, continuing...")

        # Merge all platform data
        import json
        all_records = []
        for platform in args.platforms:
            platform_file = REAL_DATA_PATH.with_suffix(f".{platform}.json")
            if platform_file.exists():
                with open(platform_file) as f:
                    records = json.load(f)
                    all_records.extend(records)
                print(f"  Loaded {len(records)} records from {platform}")

        if all_records:
            with open(REAL_DATA_PATH, 'w') as f:
                json.dump(all_records, f, indent=2)
            print(f"\n✅ Merged {len(all_records)} total real runs to {REAL_DATA_PATH}")
        else:
            print("\n⚠️ No real data collected!")
    else:
        print("\n⏭️ Skipping data collection (--skip-collect)")

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
            "--cv-folds", "5"
        ]
        run_command(cmd, "Train surrogate models v2")

    # Step 3: Train failure predictor
    if not args.skip_train:
        print(f"\n🎯 Training failure predictor...")
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "openroad_gui" / "intelligence" / "training" / "train_failure_predictor.py")
        ]
        run_command(cmd, "Train failure predictor")

    # Step 4: Train flow optimizer (PPO) - run on Google Colab
    if not args.skip_train:
        print(f"\n🤖 Training flow optimizer (PPO) - run on Google Colab")
        print("   Use: python train_flow_optimizer.py --timesteps 500000 --n-envs 8 --device cuda")
        print("   Models will save to: openroad_gui/intelligence/models/saved/")

    print("\n🎉 Pipeline complete!")
    print(f"   Real data: {REAL_DATA_PATH}")
    print(f"   Models: {PROJECT_ROOT / 'openroad_gui' / 'intelligence' / 'models' / 'saved'}")


if __name__ == "__main__":
    main()