#!/usr/bin/env python3
"""
Config Sweep Runner for ORFS
Systematically varies parameters to generate diverse training data.
"""

import argparse
import itertools
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

# ─── Configuration ──────────────────────────────────────────────────────────
ORFS_ROOT = Path("/Users/mihirmithani/Documents/Codex/2026-06-02/i-want-you-to-setup-openroad/OpenROAD-flow-scripts")

# Designs to sweep (prioritized by timing closure potential)
# Only include designs that have config.mk files
DESIGNS = {
    "gf180": [
        "uart-blocks",      # Achieved closure at default
        "jpeg",             # Achieved closure at default
        "riscv32i",         # Near closure (WNS=-0.02)
        "aes",              # Near closure (WNS=-0.67)
        "aes-hybrid",       # Medium
    ],
    "sky130hd": [
        "counter4",         # Simple, likely to close
        "comparator2bit",   # Simple
        "clap_led",         # From Session 5, achieved closure
        "gcd",              # Classic test case
        "aes",              # Medium complexity
        "picorv32_pd",      # RISC-V variant
    ],
    "asap7": [
        "riscv32i-mock-sram",  # Achieved closure!
        "aes",               # Near closure (WNS=-2.46)
        "gcd",               # Simple
        "test_counter4",     # Small design
        "mock-cpu",          # Medium
    ],
    "nangate45": [
        "ibex",              # Near closure (WNS=-0.01)
        "aes",               # Near closure (WNS=-0.02)
        "gcd",               # Simple (WNS=-0.16)
        "picorv32",          # Medium (WNS=-0.30)
        "dynamic_node",      # Larger (WNS=-0.99)
    ],
}

# Parameter sweep ranges
SWEEP_PARAMS = {
    "CORE_UTILIZATION": [20, 30, 40, 50, 60, 70],
    "CORE_ASPECT_RATIO": [0.5, 1.0, 2.0],
    "CORE_MARGIN": [2, 4, 6, 8],
    "PLACEMENT_DENSITY": [0.4, 0.55, 0.7],  # Only for some platforms
}

# Stages to run (can limit for speed)
STAGE_SETS = {
    "quick": ["synth", "floorplan"],
    "place": ["synth", "floorplan", "place"],
    "cts": ["synth", "floorplan", "place", "cts"],
    "route": ["synth", "floorplan", "place", "cts", "route"],
    "full": ["synth", "floorplan", "place", "cts", "route", "gds"],
}

@dataclass
class SweepJob:
    platform: str
    design: str
    params: Dict[str, any]
    stages: List[str]
    run_id: str

def get_design_config_path(platform: str, design: str) -> Path:
    return ORFS_ROOT / "flow" / "designs" / platform / design / "config.mk"

def get_results_dir(platform: str, design: str) -> Path:
    return ORFS_ROOT / "flow" / "results" / platform / design

def get_reports_dir(platform: str, design: str) -> Path:
    return ORFS_ROOT / "flow" / "reports" / platform / design

def build_make_command(platform: str, design: str, params: Dict, target: str) -> str:
    """Build make command with parameters."""
    config_path = get_design_config_path(platform, design)
    rel_config = config_path.relative_to(ORFS_ROOT / "flow")

    param_exports = " ".join([f'{k}="{v}"' for k, v in params.items()])

    if target == "gds":
        # Special GDS target
        results_dir = get_results_dir(platform, design)
        target = f"{results_dir.relative_to(ORFS_ROOT / 'flow')}/base/6_final.gds"

    return (
        f'set -e\n'
        f'source "{ORFS_ROOT}/use-openroad.sh"\n'
        f'cd "{ORFS_ROOT}/flow"\n'
        f'echo ">>> Running: make DESIGN_CONFIG={rel_config} {param_exports} {target}"\n'
        f'make DESIGN_CONFIG={rel_config} {param_exports} {target}\n'
    )

def run_make_command(cmd: str, timeout: int = 7200) -> tuple[bool, str, int]:
    """Run make command via bash."""
    try:
        result = subprocess.run(
            ["/bin/bash", "-lc", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", -1
    except Exception as e:
        return False, str(e), -1

def run_sweep_job(job: SweepJob) -> Dict:
    """Run a single sweep job."""
    platform = job.platform
    design = job.design
    params = job.params
    stages = job.stages
    run_id = job.run_id

    print(f"[{run_id}] Starting {platform}/{design} with {params}")
    start_time = time.time()

    results = {
        "run_id": run_id,
        "platform": platform,
        "design": design,
        "params": params,
        "stages": stages,
        "success": False,
        "stages_completed": [],
        "final_wns_ns": None,
        "final_tns_ns": None,
        "final_area_um2": None,
        "final_power_mw": None,
        "final_setup_violations": 0,
        "final_hold_violations": 0,
        "runtime_sec": 0,
        "error": None,
    }

    # Run each stage sequentially
    for stage in stages:
        cmd = build_make_command(platform, design, params, stage)
        success, output, exit_code = run_make_command(cmd, timeout=3600)

        stage_result = {
            "stage": stage,
            "success": success,
            "exit_code": exit_code,
            "output": output[-2000:] if output else "",  # Last 2000 chars
        }
        results["stages_completed"].append(stage_result)

        if not success:
            results["error"] = f"Stage {stage} failed (exit {exit_code})"
            print(f"[{run_id}] ❌ Stage {stage} failed")
            break
        else:
            print(f"[{run_id}] ✅ Stage {stage} completed")

    # If all stages succeeded, extract final metrics
    if len(results["stages_completed"]) == len(stages):
        results["success"] = True
        results = extract_final_metrics(results, platform, design)

    results["runtime_sec"] = time.time() - start_time
    print(f"[{run_id}] {'✅' if results['success'] else '❌'} Completed in {results['runtime_sec']:.1f}s")
    return results

def extract_final_metrics(results: Dict, platform: str, design: str) -> Dict:
    """Extract final PPA metrics from reports."""
    reports_dir = get_reports_dir(platform, design) / "base"

    if not reports_dir.exists():
        results["error"] = "Reports directory not found"
        return results

    # Look for finish report
    finish_reports = list(reports_dir.glob("*finish*.rpt"))
    if not finish_reports:
        finish_reports = list(reports_dir.glob("6_finish.rpt"))
    if not finish_reports:
        finish_reports = list(reports_dir.glob("*6_*.rpt"))

    import re
    for report_file in finish_reports:
        try:
            content = report_file.read_text()

            # Parse metrics
            wns_match = re.search(r"wns\s+max\s+([-\d.]+)", content, re.IGNORECASE)
            if wns_match:
                results["final_wns_ns"] = float(wns_match.group(1))

            tns_match = re.search(r"tns\s+max\s+([-\d.]+)", content, re.IGNORECASE)
            if tns_match:
                results["final_tns_ns"] = float(tns_match.group(1))

            setup_match = re.search(r"setup\s+violation\s+count\s+(\d+)", content, re.IGNORECASE)
            if setup_match:
                results["final_setup_violations"] = int(setup_match.group(1))

            hold_match = re.search(r"hold\s+violation\s+count\s+(\d+)", content, re.IGNORECASE)
            if hold_match:
                results["final_hold_violations"] = int(hold_match.group(1))

            # Try JSON report for area/power
            json_report = reports_dir / "6_report.json"
            if json_report.exists():
                import json
                data = json.loads(json_report.read_text())
                if "finish__design__instance__area" in data:
                    results["final_area_um2"] = float(data["finish__design__instance__area"])
                if "finish__power__total" in data:
                    results["final_power_mw"] = float(data["finish__power__total"]) * 1000

            break
        except Exception as e:
            results["error"] = f"Failed to parse report: {e}"

    return results

def generate_sweep_jobs(
    platforms: List[str],
    stage_set: str,
    max_jobs_per_design: int = 8
) -> List[SweepJob]:
    """Generate sweep jobs for given platforms."""
    jobs = []
    stage_list = STAGE_SETS[stage_set]

    for platform in platforms:
        if platform not in DESIGNS:
            print(f"Warning: Platform {platform} not in DESIGNS config")
            continue

        for design in DESIGNS[platform]:
            config_path = get_design_config_path(platform, design)
            if not config_path.exists():
                print(f"Warning: Config not found for {platform}/{design}")
                continue

            # Generate parameter combinations
            param_combos = []

            # Base combinations
            for util in SWEEP_PARAMS["CORE_UTILIZATION"]:
                for aspect in SWEEP_PARAMS["CORE_ASPECT_RATIO"]:
                    for margin in SWEEP_PARAMS["CORE_MARGIN"]:
                        params = {
                            "CORE_UTILIZATION": util,
                            "CORE_ASPECT_RATIO": aspect,
                            "CORE_MARGIN": margin,
                        }
                        # Add placement density for supported platforms
                        if platform in ["gf180", "asap7", "sky130hd"]:
                            for density in SWEEP_PARAMS["PLACEMENT_DENSITY"]:
                                params["PLACEMENT_DENSITY"] = density
                                param_combos.append(params.copy())
                        else:
                            param_combos.append(params)

            # Filter out problematic combinations (known issues)
            # High utilization + low margin often causes floorplan conflicts
            filtered_combos = []
            for p in param_combos:
                util = p.get("CORE_UTILIZATION", 30)
                margin = p.get("CORE_MARGIN", 4)
                # Skip high util + low margin combos that cause floorplan conflicts
                if util >= 60 and margin <= 4:
                    continue
                # Skip very low margin with high aspect ratio
                aspect = p.get("CORE_ASPECT_RATIO", 1.0)
                if margin <= 2 and aspect >= 2.0:
                    continue
                filtered_combos.append(p)

            param_combos = filtered_combos

            # Limit combinations per design
            if len(param_combos) > max_jobs_per_design:
                # Sample diverse combinations
                import random
                random.seed(42)
                param_combos = random.sample(param_combos, max_jobs_per_design)

            for i, params in enumerate(param_combos):
                run_id = f"{platform}_{design}_util{params['CORE_UTILIZATION']}_ar{params['CORE_ASPECT_RATIO']}_margin{params['CORE_MARGIN']}_{i}"
                jobs.append(SweepJob(
                    platform=platform,
                    design=design,
                    params=params,
                    stages=stage_list,
                    run_id=run_id,
                ))

    return jobs

def save_results(results: List[Dict], output_path: Path):
    """Save results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"Results saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Run ORFS config sweeps for training data")
    parser.add_argument("--platforms", nargs="+", default=["gf180", "sky130hd", "asap7", "nangate45"],
                        help="Platforms to sweep")
    parser.add_argument("--stages", default="route", choices=list(STAGE_SETS.keys()),
                        help="Stage set to run")
    parser.add_argument("--max-jobs", type=int, default=8,
                        help="Max jobs per design")
    parser.add_argument("--parallel", type=int, default=1,
                        help="Number of parallel jobs (1 = sequential)")
    parser.add_argument("--output", type=Path, default=Path("sweep_results.json"),
                        help="Output file for results")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show jobs without running")

    args = parser.parse_args()

    print("=" * 70)
    print("ORFS CONFIG SWEEP RUNNER")
    print("=" * 70)
    print(f"ORFS Root: {ORFS_ROOT}")
    print(f"Platforms: {args.platforms}")
    print(f"Stages: {STAGE_SETS[args.stages]}")
    print(f"Max jobs/design: {args.max_jobs}")
    print(f"Parallel: {args.parallel}")
    print("=" * 70)

    # Verify ORFS root
    if not (ORFS_ROOT / "use-openroad.sh").exists():
        print(f"ERROR: ORFS not found at {ORFS_ROOT}")
        sys.exit(1)

    # Generate jobs
    jobs = generate_sweep_jobs(args.platforms, args.stages, args.max_jobs)
    print(f"\nGenerated {len(jobs)} sweep jobs")

    # Group by platform for summary
    by_platform = {}
    for job in jobs:
        by_platform.setdefault(job.platform, []).append(job)

    for platform, pjobs in by_platform.items():
        designs = set(j.design for j in pjobs)
        print(f"  {platform}: {len(pjobs)} jobs across {len(designs)} designs")

    if args.dry_run:
        print("\nDry run complete. Exiting.")
        return

    # Run jobs
    results = []
    total_start = time.time()

    if args.parallel > 1:
        print(f"\nRunning {args.parallel} jobs in parallel...")
        with ProcessPoolExecutor(max_workers=args.parallel) as executor:
            future_to_job = {executor.submit(run_sweep_job, job): job for job in jobs}
            for future in as_completed(future_to_job):
                result = future.result()
                results.append(result)
    else:
        print(f"\nRunning {len(jobs)} jobs sequentially...")
        for job in jobs:
            result = run_sweep_job(job)
            results.append(result)

            # Save intermediate results
            save_results(results, args.output)

    # Final save
    save_results(results, args.output)

    # Summary
    total_time = time.time() - total_start
    successful = sum(1 for r in results if r["success"])
    print(f"\n{'='*70}")
    print(f"SWEEP COMPLETE")
    print(f"{'='*70}")
    print(f"Total jobs: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"Total time: {total_time/60:.1f} minutes")
    print(f"Results: {args.output}")

    # Per-platform summary
    for platform in args.platforms:
        p_results = [r for r in results if r["platform"] == platform]
        p_success = sum(1 for r in p_results if r["success"])
        if p_results:
            print(f"  {platform}: {p_success}/{len(p_results)} successful")

if __name__ == "__main__":
    main()