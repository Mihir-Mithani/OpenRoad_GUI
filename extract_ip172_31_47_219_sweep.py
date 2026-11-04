#!/usr/bin/env python3
"""
Extract parameter sweep data from AWS_Report/parameter_sweep/ip-172-31-47-219/
Handles both asap7 and gf180 platforms with the new IP format.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import os

@dataclass
class SweepRunRecord:
    run_id: str
    timestamp: str
    design_name: str
    platform: str
    status: str
    core_utilization: float
    core_aspect_ratio: float
    core_margin: float
    place_density: float
    synth_wns_ns: Optional[float] = None
    synth_tns_ns: Optional[float] = None
    floorplan_wns_ns: Optional[float] = None
    floorplan_tns_ns: Optional[float] = None
    place_wns_ns: Optional[float] = None
    place_tns_ns: Optional[float] = None
    cts_wns_ns: Optional[float] = None
    cts_tns_ns: Optional[float] = None
    route_wns_ns: Optional[float] = None
    route_tns_ns: Optional[float] = None
    final_wns_ns: Optional[float] = None
    final_tns_ns: Optional[float] = None
    final_setup_violations: int = 0
    final_hold_violations: int = 0
    final_power_w: Optional[float] = None
    start_utc: Optional[str] = None
    end_utc: Optional[str] = None
    timing_closure: bool = False
    drc_clean: bool = True
    lvs_clean: bool = True
    data_completeness: str = "complete"

def parse_config_mk(config_path: Path) -> Dict[str, Any]:
    params = {}
    if not config_path.exists():
        return params
    content = config_path.read_text()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            _, rest = line.split("export ", 1)
            key, value = rest.split("=", 1)
            params[key.strip()] = value.strip()
    return params

def parse_synth_report(report_path: Path) -> Dict[str, Any]:
    metrics = {}
    if not report_path.exists():
        return metrics
    content = report_path.read_text()
    patterns = {
        "wns_ns": r"wns max\s+([-\d.]+)",
        "tns_ns": r"tns max\s+([-\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                metrics[key] = float(match.group(1))
            except ValueError:
                pass
    return metrics

def parse_stage_report(report_path: Path, stage: str) -> Dict[str, Any]:
    metrics = {}
    if not report_path.exists():
        return metrics
    content = report_path.read_text()
    patterns = {
        "wns_ns": r"wns max\s+([-\d.]+)",
        "tns_ns": r"tns max\s+([-\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                metrics[f"{stage}_{key}"] = float(match.group(1))
            except ValueError:
                pass
    return metrics

def parse_finish_report(report_path: Path) -> Dict[str, Any]:
    metrics = {}
    if not report_path.exists():
        return metrics
    content = report_path.read_text()
    patterns = {
        "wns_ns": r"wns max\s+([-\d.]+)",
        "tns_ns": r"tns max\s+([-\d.]+)",
        "setup_violations": r"setup violation count\s+(\d+)",
        "hold_violations": r"hold violation count\s+(\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                metrics[key] = float(match.group(1)) if "violations" not in key else int(match.group(1))
            except ValueError:
                pass
    # Power from report_power section
    power_sections = re.findall(r"finish report_power\s*-+\s*\n(.*?)(?:\n\s*\n|$)", content, re.DOTALL)
    if power_sections:
        last_power = power_sections[-1]
        total_match = re.search(r"Total\s+[\de\.\-]+\s+[\de\.\-]+\s+[\de\.\-]+\s+([\de\.\-]+)\s+100\.0%", last_power)
        if total_match:
            try:
                metrics["power_w"] = float(total_match.group(1))
            except ValueError:
                pass
    return metrics

def parse_logs_for_runtime(logs_dir: Path) -> Dict[str, float]:
    stage_runtimes = {}
    if not logs_dir.exists():
        return stage_runtimes
    for log_file in logs_dir.glob("*.log"):
        try:
            content = log_file.read_text()
            stage_name = log_file.stem
            patterns = [
                r"Elapsed.*?(\d+(?:\.\d+)?)\s*s",
                r"Time:\s*([\d.]+)\s*s",
                r"Elapsed.*?(\d+):(\d+):(\d+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    try:
                        if ":" in match.group(1):
                            parts = match.group(1).split(":")
                            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                        else:
                            seconds = float(match.group(1))
                        stage_runtimes[stage_name] = seconds
                        break
                    except (ValueError, IndexError):
                        pass
        except Exception:
            pass
    return stage_runtimes

def extract_sweep_run(run_dir: Path, platform: str, design: str) -> Optional[dict]:
    """Extract data from a sweep run directory (ip-172-31-47-219 format)."""
    try:
        meta_path = run_dir / "run_metadata.json"
        config_path = run_dir / "config.mk"
        reports_dir = run_dir / "reports"
        logs_dir = run_dir / "logs"

        if not meta_path.exists():
            return None

        metadata = json.loads(meta_path.read_text())
        config_params = parse_config_mk(config_path)

        # Extract params from metadata (primary) or config.mk
        params = metadata.get("parameters", {})
        core_util = float(params.get("CORE_UTILIZATION", 30.0))
        core_ar = float(params.get("CORE_ASPECT_RATIO", 1.0))
        core_margin = float(params.get("CORE_MARGIN", 5.0))
        place_density = float(params.get("PLACE_DENSITY", 0.6))

        # Fallback to config.mk
        if core_util == 30.0 and "CORE_UTILIZATION" in metadata.get("parameters", {}):
            pass  # Already got from metadata

        # Override with config.mk if metadata missing
        config_params = parse_config_mk(config_path)
        core_util = float(params.get("CORE_UTILIZATION", config_params.get("CORE_UTILIZATION", 30.0)))
        core_ar = float(params.get("CORE_ASPECT_RATIO", config_params.get("CORE_ASPECT_RATIO", 1.0)))
        core_margin = float(params.get("CORE_MARGIN", config_params.get("CORE_MARGIN", 5.0)))
        place_density = float(params.get("PLACE_DENSITY", config_params.get("PLACE_DENSITY", 0.6)))

        status = metadata.get("status", "unknown")
        design_name = metadata.get("design", "unknown")
        platform_from_meta = metadata.get("platform", "unknown")

        finish_report = run_dir / "reports" / "6_finish.rpt"
        has_finish = finish_report.exists()

        if has_finish:
            completeness = "complete"
        elif metadata.get("status") in ("failed", "timed_out") or metadata.get("timed_out", False):
            completeness = "partial"
        else:
            completeness = "metadata_only"

        # Parse reports
        synth_metrics = parse_synth_report(run_dir / "reports" / "1_synth.rpt")
        floorplan_metrics = parse_stage_report(run_dir / "reports" / "2_floorplan_final.rpt", "floorplan")
        place_metrics = parse_stage_report(run_dir / "reports" / "3_detailed_place.rpt", "place")
        cts_metrics = parse_stage_report(run_dir / "reports" / "4_cts_final.rpt", "cts")
        route_metrics = parse_stage_report(run_dir / "reports" / "5_global_route.rpt", "route")
        finish_metrics = parse_finish_report(run_dir / "reports" / "6_finish.rpt") if has_finish else {}

        # Parse runtimes
        stage_runtimes = parse_logs_for_runtime(run_dir / "logs")
        total_runtime = sum(stage_runtimes.values())

        # Build run_id
        folder_name = run_dir.name
        # Extract design name from folder or metadata
        design_name = metadata.get("design", "unknown")

        run_id = f"{design}_{run_dir.name}"

        return {
            "run_id": run_id,
            "timestamp": metadata.get("started_utc", datetime.now().isoformat()),
            "design_name": design_name,
            "platform": platform_from_meta if platform_from_meta != "unknown" else platform,
            "status": "success" if has_finish else metadata.get("status", "failed"),
            "core_utilization": core_util,
            "core_aspect_ratio": core_ar,
            "core_margin": core_margin,
            "place_density": place_density,
            "synth_wns_ns": synth_metrics.get("wns_ns"),
            "synth_tns_ns": synth_metrics.get("tns_ns"),
            "floorplan_wns_ns": floorplan_metrics.get("floorplan_wns_ns"),
            "floorplan_tns_ns": floorplan_metrics.get("floorplan_tns_ns"),
            "place_wns_ns": place_metrics.get("place_wns_ns"),
            "place_tns_ns": place_metrics.get("place_tns_ns"),
            "cts_wns_ns": cts_metrics.get("cts_wns_ns"),
            "cts_tns_ns": cts_metrics.get("cts_tns_ns"),
            "route_wns_ns": route_metrics.get("route_wns_ns"),
            "route_tns_ns": route_metrics.get("route_tns_ns"),
            "final_wns_ns": finish_metrics.get("wns_ns"),
            "final_tns_ns": finish_metrics.get("tns_ns"),
            "final_setup_violations": int(finish_metrics.get("setup_violations", 0)),
            "final_hold_violations": int(finish_metrics.get("hold_violations", 0)),
            "final_power_w": finish_metrics.get("power_w"),
            "start_utc": metadata.get("started_utc"),
            "end_utc": metadata.get("ended_utc"),
            "timing_closure": (finish_metrics.get("wns_ns", 1.0) >= 0) if finish_metrics.get("wns_ns") is not None else False,
            "drc_clean": (finish_metrics.get("setup_violations", 1) == 0),
            "lvs_clean": True,
            "data_completeness": "complete" if has_finish else "partial",
        }
    except Exception as e:
        print(f"  Error extracting {run_dir.name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_config_mk(config_path: Path) -> Dict[str, Any]:
    params = {}
    if not config_path.exists():
        return params
    content = config_path.read_text()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            _, rest = line.split("export ", 1)
            key, value = rest.split("=", 1)
            params[key.strip()] = value.strip()
    return params

def parse_synth_report(report_path: Path) -> Dict[str, Any]:
    metrics = {}
    if not report_path.exists():
        return metrics
    content = report_path.read_text()
    patterns = {
        "wns_ns": r"wns max\s+([-\d.]+)",
        "tns_ns": r"tns max\s+([-\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                metrics[key] = float(match.group(1))
            except ValueError:
                pass
    return metrics

def parse_stage_report(report_path: Path, stage: str) -> Dict[str, Any]:
    metrics = {}
    if not report_path.exists():
        return metrics
    content = report_path.read_text()
    patterns = {
        "wns_ns": r"wns max\s+([-\d.]+)",
        "tns_ns": r"tns max\s+([-\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                metrics[f"{stage}_{key}"] = float(match.group(1))
            except ValueError:
                pass
    return metrics

def parse_finish_report(report_path: Path) -> Dict[str, Any]:
    metrics = {}
    if not report_path.exists():
        return metrics
    content = report_path.read_text()
    patterns = {
        "wns_ns": r"wns max\s+([-\d.]+)",
        "tns_ns": r"tns max\s+([-\d.]+)",
        "setup_violations": r"setup violation count\s+(\d+)",
        "hold_violations": r"hold violation count\s+(\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                metrics[key] = float(match.group(1)) if "violations" not in key else int(match.group(1))
            except ValueError:
                pass
    # Power from report_power section
    power_sections = re.findall(r"finish report_power\s*-+\s*\n(.*?)(?:\n\s*\n|$)", content, re.DOTALL)
    if power_sections:
        last_power = power_sections[-1]
        total_match = re.search(r"Total\s+[\de\.\-]+\s+[\de\.\-]+\s+[\de\.\-]+\s+([\de\.\-]+)\s+100\.0%", last_power)
        if total_match:
            try:
                metrics["power_w"] = float(total_match.group(1))
            except ValueError:
                pass
    return metrics

def parse_logs_for_runtime(logs_dir: Path) -> Dict[str, float]:
    stage_runtimes = {}
    if not logs_dir.exists():
        return stage_runtimes
    for log_file in logs_dir.glob("*.log"):
        try:
            content = log_file.read_text()
            stage_name = log_file.stem
            patterns = [
                r"Elapsed.*?(\d+(?:\.\d+)?)\s*s",
                r"Time:\s*([\d.]+)\s*s",
                r"Elapsed.*?(\d+):(\d+):(\d+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    try:
                        if ":" in match.group(1):
                            parts = match.group(1).split(":")
                            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                        else:
                            seconds = float(match.group(1))
                        stage_runtimes[stage_name] = seconds
                        break
                    except (ValueError, IndexError):
                        pass
        except Exception:
            pass
    return stage_runtimes

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract parameter sweep data from ip-172-31-47-219")
    parser.add_argument("--sweep-root", type=Path, default=Path("/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report/parameter_sweep/ip-172-31-47-219"),
                        help="Parameter sweep root directory")
    parser.add_argument("--output", type=Path, default=Path("openroad_gui/intelligence/data/aws_real_runs_ip172_31_47_219.json"),
                        help="Output JSON file")
    parser.add_argument("--platform", type=str, default=None,
                        help="Platform filter (asap7, gf180)")
    args = parser.parse_args()

    sweep_root = args.sweep_root
    if not sweep_root.exists():
        print(f"Sweep root not found: {sweep_root}")
        return

    all_records = []

    # Determine platforms to process
    if args.platform:
        platform_dirs = [sweep_root / args.platform]
    else:
        platform_dirs = [p for p in sweep_root.iterdir()
                         if p.is_dir() and not p.name.startswith(".")]

    for platform_dir in platform_dirs:
        platform = platform_dir.name
        if args.platform and platform != args.platform:
            continue
        print(f"\nProcessing platform: {platform}...")

        for design_dir in platform_dir.iterdir():
            if not design_dir.is_dir():
                continue
            design = design_dir.name
            if design == ".DS_Store":
                continue

            # Handle nested directories (e.g., "jpeg 2")
            run_dirs = []
            for item in design_dir.iterdir():
                if item.is_dir():
                    # Check if this is a run directory (has run_metadata.json)
                    if (item / "run_metadata.json").exists():
                        run_dirs.append(item)
                    else:
                        # Check subdirectories (e.g., "jpeg 2" has run dirs inside)
                        for sub in item.iterdir():
                            if sub.is_dir() and (sub / "run_metadata.json").exists():
                                run_dirs.append(sub)

            for run_dir in run_dirs:
                if not (run_dir / "run_metadata.json").exists():
                    continue

                finish_report = run_dir / "reports" / "6_finish.rpt"
                has_finish = finish_report.exists()

                print(f"  Processing {design}/{run_dir.name}...")
                record = extract_sweep_run(run_dir, platform, design_dir.name)
                if record:
                    record["design_name"] = record.get("design_name", "unknown")
                    record["platform"] = platform
                    record["run_id"] = f"{record.get('design_name', 'unknown')}_{run_dir.name}"

                    # Print summary
                    wns = record.get("final_wns_ns", "N/A")
                    tns = record.get("final_tns_ns", "N/A")
                    power = record.get("final_power_w", "N/A")
                    has_finish = (run_dir / "reports" / "6_finish.rpt").exists()
                    print(f"    ✅ WNS={record.get('final_wns_ns', 'N/A')}, TNS={record.get('final_tns_ns', 'N/A')}, Power={record.get('final_power_w', 'N/A')}")
                    all_records.append(record)

    # Save to JSON
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_records, indent=2, default=str))

    print(f"\n✅ Extracted {len(all_records)} total runs")
    print(f"   Saved to: {args.output}")

    # Summary
    if all_records:
        print("\nSummary by platform:")
        for platform in ["asap7", "gf180"]:
            p_records = [r for r in all_records if r.get("platform") == platform]
            if not p_records:
                continue
            complete = sum(1 for r in p_records if r.get("data_completeness") == "complete")
            partial = sum(1 for r in all_records if r.get("platform") == platform and r.get("data_completeness") == "partial")
            print(f"  {platform}: {len(p_records)} total (complete={complete}, partial={partial})")

            # Timing closure stats for complete runs
            tc = sum(1 for r in p_records if r.get("timing_closure"))
            print(f"    Timing closure: {tc}/{len(p_records)}")

if __name__ == "__main__":
    import re
    main()