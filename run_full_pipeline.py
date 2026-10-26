#!/usr/bin/env python3
"""
Complete Data Pipeline for OpenROAD Flow GUI Intelligence

This orchestrates the full pipeline:
1. Fetch real ORFS data from completed runs
2. Update synthetic generator with learned priors
3. Generate new training dataset
4. Train surrogate models
5. (Optional) Train failure predictor

Usage:
    python run_full_pipeline.py --orfs-root /path/to/OpenROAD-flow-scripts
    python run_full_pipeline.py --orfs-root /path --skip-training  # Just data
    python run_full_pipeline.py --orfs-root /path --real-only      # Only real data, no synthetic
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


# ─── Paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
ORFS_ROOT_DEFAULT = Path("/Users/mihirmithani/Documents/Codex/2026-06-02/i-want-you-to-setup-openroad/OpenROAD-flow-scripts")

# Derived paths
REAL_DATA_DIR = PROJECT_ROOT / "intelligence" / "data" / "real"
REAL_DATA_PATH = REAL_DATA_DIR / "real_runs.json"
DATASET_DIR = PROJECT_ROOT / "dataset_genration" / "output"
MODEL_DIR = PROJECT_ROOT / "intelligence" / "models" / "saved"


def run_cmd(cmd: list[str], cwd: Path = None, description: str = "") -> tuple[bool, str]:
    """Run command and return (success, output)."""
    print(f"\n{'='*70}")
    print(f"▶ {description or ' '.join(cmd)}")
    print(f"{'='*70}")

    start = time.time()
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=7200
        )
        elapsed = time.time() - start

        if result.returncode == 0:
            print(f"✅ Completed in {elapsed:.1f}s")
            if result.stdout:
                print(result.stdout[-2000:])  # Last 2000 chars
            return True, result.stdout
        else:
            print(f"❌ Failed after {elapsed:.1f}s (exit {result.returncode})")
            if result.stderr:
                print(result.stderr[-3000:])
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"⏱️ Timed out after 2 hours")
        return False, "Timeout"
    except Exception as e:
        print(f"💥 Error: {e}")
        return False, str(e)


def step1_collect_real_data(orfs_root: Path, platform: str = "asap7") -> bool:
    """Step 1: Collect real metrics from completed ORFS runs."""
    print("\n" + "🔵" * 35)
    print("STEP 1: Collect Real ORFS Data")
    print("🔵" * 35)

    REAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m", "openroad_gui.intelligence.data.collect_real_data",
        "--orfs-root", str(orfs_root),
        "--platform", platform,
        "--output", str(REAL_DATA_PATH),
    ]

    success, output = run_cmd(cmd, cwd=PROJECT_ROOT, description="Collect real ORFS data")

    if success and REAL_DATA_PATH.exists():
        with open(REAL_DATA_PATH) as f:
            data = json.load(f)
        print(f"\n📊 Collected {len(data)} real runs")
        return True

    return False


def step2_generate_dataset(real_data_path: Path, rows: int = 3000, seed: int = 42) -> bool:
    """Step 2: Generate synthetic dataset grounded in real data."""
    print("\n" + "🟢" * 35)
    print("STEP 2: Generate Synthetic Dataset")
    print("🟢" * 35)

    cmd = [
        sys.executable,
        "dataset_genration/generate_dataset_v2.py",
        "--rows", str(rows),
        "--seed", str(seed),
        "--outdir", str(DATASET_DIR),
        "--real-data", str(real_data_path),
        "--max-attempts", "25",
    ]

    success, _ = run_cmd(cmd, cwd=PROJECT_ROOT, description="Generate dataset")
    return success


def step3_train_surrogate(epochs: int = 200, ensemble: bool = True) -> bool:
    """Step 3: Train surrogate models."""
    print("\n" + "🟡" * 35)
    print("STEP 3: Train Surrogate Models")
    print("🟡" * 35)

    cmd = [
        sys.executable,
        "-m", "openroad_gui.intelligence.training.train_surrogate",
        "--epochs", str(epochs),
    ]
    if ensemble:
        cmd.append("--ensemble")

    success, _ = run_cmd(cmd, cwd=PROJECT_ROOT, description="Train surrogate models")
    return success


def step4_train_failure_predictor() -> bool:
    """Step 4: Train failure predictor."""
    print("\n" + "🟣" * 35)
    print("STEP 4: Train Failure Predictor")
    print("🟣" * 35)

    cmd = [
        sys.executable,
        "-m", "openroad_gui.intelligence.training.train_failure_predictor",
    ]

    success, _ = run_cmd(cmd, cwd=PROJECT_ROOT, description="Train failure predictor")
    return success


def step5_export_onnx() -> bool:
    """Step 5: Export models to ONNX."""
    print("\n" + "🟠" * 35)
    print("STEP 5: Export to ONNX")
    print("🟠" * 35)

    cmd = [
        sys.executable,
        "-m", "openroad_gui.intelligence.utils.onnx_export",
        "--targets", "wns", "tns", "area", "power",
    ]

    success, _ = run_cmd(cmd, cwd=PROJECT_ROOT, description="Export ONNX models")
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Complete OpenROAD Intelligence Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_full_pipeline.py
  python run_full_pipeline.py --orfs-root /custom/path --platform sky130hd
  python run_full_pipeline.py --skip-training
  python run_full_pipeline.py --steps 1 2 3
        """
    )

    parser.add_argument("--orfs-root", type=Path, default=ORFS_ROOT_DEFAULT,
                        help="ORFS root directory (contains flow/, use-openroad.sh)")
    parser.add_argument("--platform", type=str, default="asap7",
                        help="Platform/PDK to collect data for")
    parser.add_argument("--rows", type=int, default=3000,
                        help="Number of synthetic rows to generate")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for dataset generation")
    parser.add_argument("--epochs", type=int, default=200,
                        help="MLP training epochs")
    parser.add_argument("--steps", nargs="+", type=int, default=[1, 2, 3, 4, 5],
                        choices=[1, 2, 3, 4, 5],
                        help="Pipeline steps to run (1=collect, 2=generate, 3=surrogate, 4=failure, 5=onnx)")
    parser.add_argument("--skip-training", action="store_true",
                        help="Only run data collection and generation (steps 1-2)")

    args = parser.parse_args()

    # Validate ORFS root
    orfs_root = args.orfs_root
    if not (orfs_root / "flow").exists() or not (orfs_root / "use-openroad.sh").exists():
        print(f"❌ Invalid ORFS root: {orfs_root}")
        print("   Must contain 'flow/' directory and 'use-openroad.sh'")
        return 1

    if args.skip_training:
        args.steps = [1, 2]

    print("=" * 70)
    print("🚀 OPENROAD INTELLIGENCE PIPELINE")
    print("=" * 70)
    print(f"ORFS Root: {orfs_root}")
    print(f"Platform:  {args.platform}")
    print(f"Rows:      {args.rows}")
    print(f"Steps:     {args.steps}")
    print("=" * 70)

    total_start = time.time()
    results = {}

    # Step 1: Collect real data
    if 1 in args.steps:
        results["collect_real"] = step1_collect_real_data(orfs_root, args.platform)
        if not results["collect_real"]:
            print("\n⚠️  Real data collection failed, continuing with synthetic-only...")
            # Create empty real data file for synthetic generator
            REAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
            REAL_DATA_PATH.write_text("[]")

    # Step 2: Generate dataset
    if 2 in args.steps:
        results["generate"] = step2_generate_dataset(REAL_DATA_PATH, args.rows, args.seed)

    # Step 3: Train surrogate
    if 3 in args.steps:
        results["surrogate"] = step3_train_surrogate(args.epochs, ensemble=True)

    # Step 4: Train failure predictor
    if 4 in args.steps:
        results["failure"] = step4_train_failure_predictor()

    # Step 5: Export ONNX
    if 5 in args.steps:
        results["onnx"] = step5_export_onnx()

    # Summary
    total_time = time.time() - total_start
    print("\n" + "=" * 70)
    print("📊 PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Total time: {total_time/60:.1f} min")
    for step, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {step:<20} {status}")

    # Check key outputs
    print("\n📁 Key Outputs:")
    for path, desc in [
        (REAL_DATA_PATH, "Real ORFS runs"),
        (DATASET_DIR / "training_data.parquet", "Training dataset"),
        (MODEL_DIR / "surrogate_area_lgb.pkl", "Surrogate Area model"),
        (MODEL_DIR / "surrogate_preprocessor.pkl", "Feature preprocessor"),
    ]:
        if path.exists():
            print(f"  ✅ {desc}: {path}")
        else:
            print(f"  ❌ {desc}: {path} (MISSING)")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())