#!/usr/bin/env python3
"""
Master Training Script
Runs all three model training pipelines sequentially
"""

import os
import sys
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path("/Users/mihirmithani/Downloads/OpenRoad GUI")

def run_training(script_name, description):
    """Run a training script and return success status"""
    script_path = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/training") / script_name

    print(f"\n{'='*60}")
    print(f"STARTING: {description}")
    print(f"Script: {script_name}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout per model
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            print(f"\n✅ {description} COMPLETED in {elapsed:.1f}s")
            print(f"Output: {result.stdout[-1000:]}")  # Last 1000 chars
            return True
        else:
            print(f"\n❌ {description} FAILED after {elapsed:.1f}s")
            print(f"Error: {result.stderr[-2000:]}")  # Last 2000 chars
            return False

    except subprocess.TimeoutExpired:
        print(f"\n⏱️ {description} TIMED OUT after 1 hour")
        return False
    except Exception as e:
        print(f"\n💥 {description} CRASHED: {e}")
        return False

def main():
    print("=" * 60)
    print("MASTER TRAINING PIPELINE")
    print("=" * 60)
    print("This will train all three models sequentially:")
    print("  1. Failure Predictor (Classification)")
    print("  2. Surrogate Models (Regression)")
    print("  3. Flow Optimizer (RL - PPO)")
    print("=" * 60)

    # Check data exists
    data_path = "/Users/mihirmithani/Downloads/OpenRoad GUI/dataset_genration/output/training_data.parquet"
    if not os.path.exists(data_path):
        print(f"❌ Training data not found at {data_path}")
        print("Run dataset generation first!")
        return

    print(f"✅ Training data found: {data_path}")

    # Training pipeline
    pipeline = [
        ("train_failure_predictor.py", "Failure Predictor (XGBoost + LightGBM)"),
        ("train_surrogate.py", "Surrogate Models (XGBoost Regression)"),
        ("train_flow_optimizer.py", "Flow Optimizer (PPO RL)"),
    ]

    results = {}
    total_start = time.time()

    for script, desc in pipeline:
        success = run_training(script, desc)
        results[script] = success

        if not success:
            print(f"\n⚠️  {script} failed. Continuing with next model...")

    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("TRAINING PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print()

    for script, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {script}: {status}")

    # Summary
    print("\n📁 Model artifacts saved to:")
    print(f"  {Path('/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/models/saved')}")
    print(f"  {Path('/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/training/checkpoints')}")
    print(f"  {Path('/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/training/logs')}")

if __name__ == '__main__':
    main()