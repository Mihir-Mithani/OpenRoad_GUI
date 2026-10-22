#!/usr/bin/env python3
"""
OpenROAD Flow GUI - Multi-Design Sequential Runner
Runs multiple designs through the OpenROAD flow sequentially to collect training data.

Usage:
    python3 run_multiple_designs.py --designs gcd multiplier_4bit mux4x1 counter4
    python3 run_multiple_designs.py --all-asap7
    python3 run_multiple_designs.py --config runs_config.json
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import threading
import signal
import psutil

# ─── Configuration ────────────────────────────────────────────────

# Default designs to run (borderline/priority first)
DEFAULT_DESIGNS = [
    "gcd",
    "multiplier_4bit",
    "mux4x1",
    "counter4",
    "comparator2bit",
    "uart_tx",
    "spi_master",
    "i2c_controller",
    "pwm_gen",
    "crc32",
]

# ORFS root (auto-detected or override)
ORFS_ROOT = os.environ.get("ORFS_ROOT") or os.environ.get("OPENROAD_FLOW_SCRIPTS") or \
    str(Path.home() / "OpenROAD-flow-scripts")

PLATFORM = "asap7"

# ─── Runner Class ────────────────────────────────────────────────

class DesignRunner:
    def __init__(self, orfs_root: str, platform: str, designs: List[str],
                 stages: Optional[List[str]] = None,
                 timeout_hours: int = 6,
                 collect_metrics: bool = True):
        self.orfs_root = Path(orfs_root).expanduser()
        self.platform = platform
        self.designs = designs
        self.stages = stages or ["synth", "floorplan", "place", "cts", "route", "finish"]
        self.timeout_seconds = timeout_hours * 3600
        self.collect_metrics = collect_metrics

        self.flow_dir = self.orfs_root / "flow"
        self.results = []
        self.current_process = None
        self.should_stop = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print(f"\n🛑 Received signal {signum}, stopping gracefully...")
        self.should_stop = True
        if self.current_process:
            self.current_process.terminate()

    def run_design(self, design: str) -> Dict:
        """Run full flow for a single design."""
        print(f"\n{'='*60}")
        print(f"🚀 Starting design: {design} ({self.platform})")
        print(f"{'='*60}")

        design_start = time.time()
        result = {
            "design": design,
            "platform": self.platform,
            "start_time": datetime.now().isoformat(),
            "stages": {},
            "success": False,
            "error": None,
            "metrics": {}
        }

        flow_dir = self.flow_dir
        design_config = f"./designs/{self.platform}/{design}/config.mk"

        # Verify design exists
        if not (flow_dir / "designs" / self.platform / design).exists():
            result["error"] = f"Design not found: {design}"
            return result

        env = os.environ.copy()
        env["ORFS_ROOT"] = str(self.orfs_root)

        for stage in self.stages:
            if self.should_stop:
                result["error"] = "Stopped by user"
                break

            print(f"\n📍 Stage: {stage}")
            stage_start = time.time()

            try:
                # Run make stage
                cmd = [
                    "make", f"DESIGN_CONFIG={design_config}", stage
                ]

                self.current_process = subprocess.Popen(
                    cmd,
                    cwd=flow_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                # Stream output with timeout
                stage_output = []
                start_time = time.time()

                while True:
                    if self.should_stop:
                        self.current_process.terminate()
                        break

                    if time.time() - start_time > self.timeout_seconds:
                        self.current_process.terminate()
                        raise TimeoutError(f"Stage {stage} timed out after {self.timeout_seconds/3600:.1f}h")

                    line = self.current_process.stdout.readline()
                    if not line and self.current_process.poll() is not None:
                        break
                    if line:
                        stage_output.append(line)
                        # Print progress indicators
                        if any(kw in line for kw in ["WNS", "TNS", "DRC", "congestion", "utilization", "Iteration"]):
                            print(f"  📊 {line.strip()}")

                self.current_process.wait()
                stage_time = time.time() - stage_start

                if self.current_process.returncode != 0:
                    result["error"] = f"Stage {stage} failed (exit {self.current_process.returncode})"
                    result["stages"][stage] = {
                        "success": False,
                        "time_sec": stage_time,
                        "output_tail": "".join(stage_output[-50:])
                    }
                    return result

                result["stages"][stage] = {
                    "success": True,
                    "time_sec": stage_time
                }

                print(f"  ✅ {stage} completed in {stage_time:.1f}s")

                # Collect metrics after each stage if enabled
                if self.collect_metrics:
                    metrics = self._collect_stage_metrics(stage)
                    result["metrics"][stage] = metrics

            except TimeoutError as e:
                result["error"] = str(e)
                return result
            except Exception as e:
                result["error"] = f"Stage {stage} error: {e}"
                return result

        # All stages completed
        result["success"] = True
        result["end_time"] = datetime.now().isoformat()
        result["total_time_sec"] = time.time() - design_start

        # Collect final metrics
        if self.collect_metrics:
            result["metrics"]["final"] = self._collect_final_metrics()

        print(f"\n✅ Design {design} completed in {(time.time() - design_start)/60:.1f} min")
        return result

    def _collect_stage_metrics(self, stage: str) -> Dict:
        """Extract metrics from stage reports."""
        metrics = {}
        reports_dir = self.flow_dir / "reports" / self.platform / "base"

        if not reports_dir.exists():
            return metrics

        # Look for stage report
        report_files = list(reports_dir.glob(f"*{stage}*.rpt")) + \
                       list(reports_dir.glob(f"*{stage}*.rpt"))

        for report_file in report_files:
            try:
                content = report_file.read_text()
                # Extract key metrics
                import re
                for key, pattern in {
                    "wns_ns": r"wns\s+max\s+([-\d.]+)",
                    "tns_ns": r"tns\s+max\s+([-\d.]+)",
                    "area_um2": r"Area\s*:\s*([\d.]+)",
                    "power_mw": r"Power\s+([\d.]+)\s*Watts",
                    "drc_violations": r"violation\s+count\s+(\d+)",
                }.items():
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        val = match.group(1)
                        metrics[key] = float(val) if "." in val else int(val)
            except Exception:
                pass

        return metrics

    def _collect_final_metrics(self) -> Dict:
        """Collect final sign-off metrics."""
        metrics = {}
        reports_dir = self.flow_dir / "reports" / self.platform / "base"

        if not reports_dir.exists():
            return metrics

        # Look for finish report
        finish_reports = list(reports_dir.glob("*finish*.rpt")) + \
                        list(reports_dir.glob("6_finish.rpt")) + \
                        list(reports_dir.glob("*6_*.rpt"))

        for report_file in finish_reports:
            try:
                content = report_file.read_text()
                import re
                for key, pattern in {
                    "wns_ns": r"wns\s+max\s+([-\d.]+)",
                    "tns_ns": r"tns\s+max\s+([-\d.]+)",
                    "area_um2": r"Area\s*:\s*([\d.]+)",
                    "power_mw": r"Power\s+([\d.]+)\s*Watts",
                    "drc_violations": r"violation\s+count\s+(\d+)",
                    "congestion_pct": r"congestion\s*:\s*(\d+)",
                }.items():
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        val = match.group(1)
                        metrics[key] = float(val) if "." in val else int(val)
            except Exception:
                pass

        # Also check for JSON report
        json_files = list(reports_dir.glob("*report.json")) + \
                     list(reports_dir.glob("6_report.json"))
        for json_file in json_files:
            try:
                import json
                data = json.loads(json_file.read_text())
                mapping = {
                    "finish__timing__drv__setup_violation_count": "setup_violations",
                    "finish__timing__drv__hold_violation_count": "hold_violations",
                    "finish__power__total": "power_w",
                    "finish__design__instance__area": "area_um2",
                }
                for k, v in mapping.items():
                    if k in data:
                        metrics[v] = data[k]
            except Exception:
                pass

        return metrics

    def run_all(self) -> List[Dict]:
        """Run all designs sequentially."""
        print(f"\n🚀 Starting batch run for {len(self.designs)} designs")
        print(f"   Platform: {self.platform}")
        print(f"   Stages: {', '.join(self.stages)}")
        print(f"   Timeout per stage: {self.timeout_seconds/3600:.1f}h")
        print(f"   Metrics collection: {'Enabled' if self.collect_metrics else 'Disabled'}")

        for i, design in enumerate(self.designs, 1):
            if self.should_stop:
                break

            print(f"\n{'🎯'*30}")
            print(f"   Design {i}/{len(self.designs)}: {design}")
            print(f"{'🎯'*30}")

            result = self.run_design(design)
            self.results.append(result)

            # Save intermediate results
            self._save_results()

            if not result["success"]:
                print(f"❌ Design {design} failed: {result.get('error', 'Unknown error')}")
            else:
                print(f"✅ Design {design} succeeded")

        self._save_results()
        self._print_summary()
        return self.results

    def _save_results(self):
        """Save results to JSON file."""
        output_file = Path.cwd() / f"batch_run_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"💾 Results saved to {output_file}")

    def _print_summary(self):
        print(f"\n{'='*60}")
        print("📊 BATCH RUN SUMMARY")
        print(f"{'='*60}")

        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful

        print(f"Total designs: {total}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"Success rate: {successful/total*100:.1f}%")

        if failed > 0:
            print("\n❌ Failed designs:")
            for r in self.results:
                if not r["success"]:
                    print(f"  - {r['design']}: {r.get('error', 'Unknown')}")

        if self.collect_metrics:
            print("\n📈 Collected metrics for:")
            for r in self.results:
                if r["success"] and r.get("metrics", {}).get("final"):
                    m = r["metrics"]["final"]
                    wns = m.get("wns_ns", "N/A")
                    tns = m.get("tns_ns", "N/A")
                    drc = m.get("drc_violations", "N/A")
                    print(f"  {r['design']}: WNS={wns}, TNS={tns}, DRC={drc}")

# ─── Main Entry Point ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run multiple OpenROAD designs sequentially",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --designs gcd multiplier_4bit mux4x1
  %(prog)s --all-asap7
  %(prog)s --config runs_config.json
  %(prog)s --designs gcd multiplier_4bit --stages synth floorplan place --timeout 4
        """
    )

    parser.add_argument("--designs", nargs="+", help="List of design names to run")
    parser.add_argument("--all-asap7", action="store_true", help="Run all asap7 designs")
    parser.add_argument("--platform", default="asap7", help="Platform/PDK name")
    parser.add_argument("--orfs-root", help="ORFS root directory")
    parser.add_argument("--stages", nargs="+", default=["synth", "floorplan", "place", "cts", "route", "finish"])
    parser.add_argument("--timeout", type=int, default=6, help="Timeout per stage in hours")
    parser.add_argument("--no-metrics", action="store_true", help="Disable metrics collection")
    parser.add_argument("--config", help="JSON config file with run parameters")

    args = parser.parse_args()

    # Load config file if provided
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
        for k, v in config.items():
            if not getattr(args, k, None):
                setattr(args, k, v)

    # Determine designs to run
    if args.all_asap7:
        orfs_root = Path(args.orfs_root or os.environ.get("ORFS_ROOT") or
                         Path.home() / "OpenROAD-flow-scripts")
        designs_dir = orfs_root / "flow" / "designs" / args.platform
        designs = sorted([d.name for d in designs_dir.iterdir() if d.is_dir()])
        print(f"Found {len(designs)} designs in {designs_dir}")
    elif args.designs:
        designs = args.designs
    else:
        designs = DEFAULT_DESIGNS
        print(f"Using default designs: {designs}")

    if not designs:
        print("❌ No designs to run")
        return 1

    # Validate ORFS root
    orfs_root = args.orfs_root or os.environ.get("ORFS_ROOT") or \
                str(Path.home() / "OpenROAD-flow-scripts")
    if not Path(orfs_root).exists():
        print(f"❌ ORFS root not found: {orfs_root}")
        print("   Set --orfs-root or ORFS_ROOT environment variable")
        return 1

    # Run
    runner = DesignRunner(
        orfs_root=orfs_root,
        platform=args.platform,
        designs=designs,
        stages=args.stages,
        timeout_hours=args.timeout,
        collect_metrics=not args.no_metrics
    )

    try:
        runner.run_all()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())