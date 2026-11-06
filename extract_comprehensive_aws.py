#!/usr/bin/env python3
"""
Comprehensive AWS ORFS Data Extractor
Extracts ALL available data from AWS_Report including:
- Successful runs (with 6_finish.rpt)
- Failed/timed-out runs (with partial reports)
- Parameter sweep runs
"""

import json
import re
import os
import csv
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class AWSRunRecord:
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
    data_completeness: str = "complete"  # "complete", "partial", "metadata_only"

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


def parse_finish_json_report(logs_dir: Path) -> Dict[str, Any]:
    """Parse area and other metrics from the JSON report (6_report.json)."""
    metrics = {}
    json_path = logs_dir / "6_report.json"
    if not json_path.exists():
        return metrics
    try:
        import json
        data = json.loads(json_path.read_text())
        # Extract area
        if "finish__design__instance__area" in data:
            metrics["area_um2"] = float(data["finish__design__instance__area"])
        # Extract power from JSON as fallback
        if "power_w" not in globals() and "finish__power__total" in data:
            metrics["power_w"] = float(data["finish__power__total"])
    except Exception:
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

def extract_run_from_dir(run_dir: Path, platform: str) -> Optional[dict]:
    """Extract data from a single run directory (any status)."""
    try:
        meta_path = run_dir / "run_metadata.json"
        config_path = run_dir / "config.mk"
        reports_dir = run_dir / "reports"
        logs_dir = run_dir / "logs"

        if not meta_path.exists():
            return None

        metadata = json.loads(meta_path.read_text())
        config_params = parse_config_mk(config_path)

        # Extract params from folder name as backup
        folder_name = run_dir.name
        util_match = re.search(r'_u(\d+)_', folder_name)
        ar_match = re.search(r'_ar([\d.]+)_', folder_name)
        margin_match = re.search(r'_m(\d+)_', folder_name)
        density_match = re.search(r'_d([\d.]+)$', folder_name)

        core_util = float(util_match.group(1)) if util_match else config_params.get("CORE_UTILIZATION", 30.0)
        core_ar = float(ar_match.group(1)) if ar_match else config_params.get("CORE_ASPECT_RATIO", 1.0)
        core_margin = float(margin_match.group(1)) if margin_match else config_params.get("CORE_MARGIN", 5.0)
        place_density = float(density_match.group(1)) if density_match else config_params.get("PLACE_DENSITY", 0.6)

        status = metadata.get("status", "unknown")
        timed_out = metadata.get("timed_out", False)
        exit_code = metadata.get("make_exit_code", 0)

        # Determine completeness
        finish_report = run_dir / "reports" / "6_finish.rpt"
        has_finish = finish_report.exists()

        if has_finish and status == "success":
            completeness = "complete"
        elif status in ("failed", "timed_out") or timed_out:
            completeness = "partial"
        else:
            completeness = "metadata_only"

        # Parse reports (even for failed runs - some stages may have completed)
        synth_metrics = parse_synth_report(run_dir / "reports" / "1_synth.rpt")
        floorplan_metrics = parse_stage_report(run_dir / "reports" / "2_floorplan_final.rpt", "floorplan")
        place_metrics = parse_stage_report(run_dir / "reports" / "3_detailed_place.rpt", "place")
        cts_metrics = parse_stage_report(run_dir / "reports" / "4_cts_final.rpt", "cts")
        route_metrics = parse_stage_report(run_dir / "reports" / "5_global_route.rpt", "route")
        finish_metrics = parse_finish_report(run_dir / "reports" / "6_finish.rpt") if has_finish else {}

        # Parse runtimes
        stage_runtimes, total_runtime = parse_logs_for_runtime(run_dir / "logs"), 0
        for v in stage_runtimes.values():
            total_runtime += v

        # Build run_id from folder name
        run_id = folder_name.replace("20261103T165433Z_ip-172-31-32-99_", "") if "ip-172-31-32-99" in folder_name else folder_name

        # Determine design name from folder
        design_match = re.search(r'nangate45_([^_]+(?:_[^_]+)?)_u', folder_name)
        if not design_match:
            design_match = re.search(r'(?:asap7|gf180|nangate45)_([^_]+(?:_[^_]+)?)_u', folder_name)
        design_name = design_match.group(1) if design_match else "unknown"

        return {
            "run_id": run_id,
            "timestamp": metadata.get("start_utc", datetime.now().isoformat()),
            "design_name": design_name,
            "platform": "nangate45",
            "status": status,
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
            "start_utc": metadata.get("start_utc"),
            "end_utc": metadata.get("end_utc"),
            "timing_closure": (finish_metrics.get("wns_ns", 1.0) >= 0) if finish_metrics.get("wns_ns") is not None else False,
            "drc_clean": (finish_metrics.get("setup_violations", 1) == 0),
            "lvs_clean": True,
            "data_completeness": completeness,
        }
    except Exception as e:
        print(f"  Error extracting {run_dir.name}: {e}")
        return None

def extract_asap7_gf180(run_dir: Path, platform: str) -> Optional[dict]:
    """Extract data for asap7/gf180 platforms (different folder structure)."""
    # Similar logic but with different folder naming
    # These use timestamp_design format in platform subdirectories
    pass

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Comprehensive AWS ORFS data extractor")
    parser.add_argument("--aws-root", type=Path, default=Path("/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report"),
                        help="AWS_Report root directory")
    parser.add_argument("--platform", type=str, default=None,
                        help="Platform to filter (asap7, gf180, nangate45). If not specified, processes all.")
    parser.add_argument("--output", type=Path, default=Path("openroad_gui/intelligence/data/aws_real_runs_comprehensive.json"),
                        help="Output JSON file")
    parser.add_argument("--include-failed", action="store_true", default=True,
                        help="Include failed/timed_out runs")
    args = parser.parse_args()

    aws_report_root = args.aws_root
    if not aws_report_root.exists():
        print(f"AWS_Report not found at {aws_report_root}")
        return

    all_records = []

    # Determine platforms to process
    if args.platform:
        platform_dirs = [aws_report_root / args.platform]
    else:
        platform_dirs = [p for p in aws_report_root.iterdir()
                         if p.is_dir() and not p.name.startswith(".")]

    for platform_dir in platform_dirs:
        platform = platform_dir.name
        print(f"\nProcessing platform: {platform}...")

        if platform == "parameter_sweep":
            # Handle parameter sweep directory structure
            for sweep_ip_dir in platform_dir.iterdir():
                if not sweep_ip_dir.is_dir() or sweep_ip_dir.name.startswith("."):
                    continue
                for sweep_platform_dir in sweep_ip_dir.iterdir():
                    if not sweep_platform_dir.is_dir() or sweep_platform_dir.name.startswith("."):
                        continue
                    sweep_platform = sweep_platform_dir.name
                    print(f"\nProcessing sweep platform: {sweep_platform}...")

                    for design_dir in sweep_platform_dir.iterdir():
                        if not design_dir.is_dir():
                            continue
                        design = design_dir.name
                        if design == ".DS_Store":
                            continue

                        run_dirs = [d for d in design_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

                        for run_dir in run_dirs:
                            if not (run_dir / "run_metadata.json").exists():
                                continue

                            finish_report = run_dir / "reports" / "6_finish.rpt"
                            if finish_report.exists() or args.include_failed:
                                print(f"  Processing {design}/{run_dir.name}...")
                                record = extract_parameter_sweep_run(run_dir, sweep_platform)
                                if record:
                                    all_records.append(record)
                                    wns = record.get("final_wns_ns", "N/A")
                                    tns = record.get("final_tns_ns", "N/A")
                                    power = record.get("final_power_w", "N/A")
                                    status = record.get("status", "unknown")
                                    completeness = record.get("data_completeness", "unknown")
                                    print(f"    ✅ {record['run_id']}: status={status}, completeness={completeness}, WNS={wns}, TNS={tns}")
            continue
            design = design_dir.name
            if design == "parameter_sweep":
                continue

            # Find run directories (timestamped subdirectories)
            run_dirs = [d for d in design_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

            for run_dir in run_dirs:
                finish_report = run_dir / "reports" / "6_finish.rpt"
                meta_path = run_dir / "run_metadata.json"

                if not meta_path.exists():
                    continue

                # Extract data (including failed/timed_out if requested)
                if args.include_failed or (finish_report.exists()):
                    print(f"  Processing {platform}/{design_dir.name}/{run_dir.name}...")

                    # Use appropriate extractor based on platform
                    if platform == "nangate45" and "ip-172-31-32-99" in run_dir.name:
                        record = extract_parameter_sweep_run(run_dir, platform)
                    else:
                        # For asap7/gf180 and parameter sweep nangate45
                        record = extract_standard_run(run_dir, platform)

                    if record:
                        all_records.append(record)
                        wns = record.get("final_wns_ns", "N/A")
                        tns = record.get("final_tns_ns", "N/A")
                        power = record.get("final_power_w", "N/A")
                        status = record.get("status", "unknown")
                        completeness = record.get("data_completeness", "unknown")
                        print(f"    ✅ {record['run_id']}: status={status}, completeness={completeness}, WNS={wns}, TNS={tns}")

    # Save to JSON
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_records, indent=2, default=str))

    # Also save CSV
    csv_path = output_path.with_suffix('.csv')
    _write_csv(all_records, csv_path)

    print(f"\n✅ Extracted {len(all_records)} total runs")
    print(f"   Saved to: {output_path}")
    print(f"   CSV saved to: {csv_path}")

    # Summary
    if all_records:
        print("\nSummary by platform:")
        for platform in ["asap7", "gf180", "nangate45"]:
            p_records = [r for r in all_records if r.get("platform") == platform]
            if not p_records:
                continue
            complete = sum(1 for r in p_records if r.get("data_completeness") == "complete")
            partial = sum(1 for r in p_records if r.get("data_completeness") == "partial")
            meta_only = sum(1 for r in p_records if r.get("data_completeness") == "metadata_only")
            print(f"  {platform}: {len(p_records)} total (complete={complete}, partial={partial}, metadata_only={meta_only})")

            # Timing closure stats
            tc = sum(1 for r in p_records if r.get("timing_closure"))
            print(f"    Timing closure: {tc}/{len(p_records)}")

def extract_standard_run(run_dir: Path, platform: str) -> Optional[dict]:
    """Extract data from standard asap7/gf180 run directory."""
    try:
        meta_path = run_dir / "run_metadata.json"
        config_path = run_dir / "config.mk"
        reports_dir = run_dir / "reports"
        logs_dir = run_dir / "logs"

        if not meta_path.exists():
            return None

        metadata = json.loads(meta_path.read_text())
        config_params = parse_config_mk(config_path)

        # Extract params from config.mk
        core_util = float(config_params.get("CORE_UTILIZATION", 30.0))
        core_ar = float(config_params.get("CORE_ASPECT_RATIO", 1.0))
        core_margin = float(config_params.get("CORE_MARGIN", 5.0))
        place_density = float(config_params.get("PLACE_DENSITY", 0.6))

        # Override with metadata if available
        metadata_platform = metadata.get("platform", platform)
        design_name = metadata.get("design", run_dir.name)
        status = metadata.get("status", "unknown")
        timed_out = metadata.get("timed_out", False)

        finish_report = run_dir / "reports" / "6_finish.rpt"
        has_finish = finish_report.exists()

        if has_finish and status == "success":
            completeness = "complete"
        elif status in ("failed", "timed_out") or timed_out:
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
        # Parse JSON report for area and additional metrics
        json_metrics = parse_finish_json_report(logs_dir)
        finish_metrics.update(json_metrics)

        # Parse runtimes
        stage_runtimes = parse_logs_for_runtime(logs_dir)
        total_runtime = sum(stage_runtimes.values())

        run_id = metadata.get("run_id", run_dir.name)

        return {
            "run_id": run_id,
            "timestamp": metadata.get("start_utc", datetime.now().isoformat()),
            "design_name": design_name,
            "platform": platform,
            "status": status,
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
            "final_area_um2": finish_metrics.get("area_um2"),
            "start_utc": metadata.get("start_utc"),
            "end_utc": metadata.get("end_utc"),
            "timing_closure": (finish_metrics.get("wns_ns", 1.0) >= 0) if finish_metrics.get("wns_ns") is not None else False,
            "drc_clean": (finish_metrics.get("setup_violations", 1) == 0),
            "lvs_clean": True,
            "data_completeness": "complete" if finish_report.exists() else "partial",
        }
    except Exception as e:
        print(f"  Error extracting {run_dir.name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_parameter_sweep_run(run_dir: Path, platform: str) -> Optional[dict]:
    """Extract data from parameter sweep run directory (supports all platforms)."""
    try:
        meta_path = run_dir / "run_metadata.json"
        config_path = run_dir / "config.mk"
        reports_dir = run_dir / "reports"
        logs_dir = run_dir / "logs"

        if not meta_path.exists():
            return None

        metadata = json.loads(meta_path.read_text())
        config_params = parse_config_mk(config_path)

        # Extract params from folder name (supports multiple sweep formats)
        folder_name = run_dir.name

        # Format 1: ip-172-31-47-219 (new sweep)
        # e.g., 20261103T105908Z_ip-172-31-47-219_asap7_riscv32i-mock-sram_u20_ar0.5_m4_d0.4
        # Format 2: ip-172-31-32-99 (old sweep)
        # e.g., 20261103T165433Z_ip-172-31-32-99_nangate45_ibex_u20_ar0.5_m4_d0.4

        util_match = re.search(r'_u(\d+)_', folder_name)
        ar_match = re.search(r'_ar([\d.]+)_', folder_name)
        margin_match = re.search(r'_m(\d+)_', folder_name)
        density_match = re.search(r'_d([\d.]+)$', folder_name)

        # Extract design name from folder name
        # Pattern: <timestamp>_ip-<ip>_<platform>_<design>_u<util>_ar<ar>_m<margin>_d<density>
        design = "unknown"
        sweep_platform = platform

        # Try to extract platform and design from folder name
        # Match patterns like: _asap7_riscv32i-mock-sram_ or _nangate45_ibex_
        platform_design_match = re.search(r'_ip-[\d-]+_([a-z0-9-]+)_([a-z0-9-]+)_u\d+', folder_name)
        if platform_design_match:
            sweep_platform = platform_design_match.group(1)
            design = platform_design_match.group(2)
        else:
            # Fallback: try to get from metadata
            sweep_platform = metadata.get("platform", platform)
            design = metadata.get("design", run_dir.name)

        util_match = re.search(r'_u(\d+)_', folder_name)
        ar_match = re.search(r'_ar([\d.]+)_', folder_name)
        margin_match = re.search(r'_m(\d+)_', folder_name)
        density_match = re.search(r'_d([\d.]+)$', folder_name)

        core_util = float(util_match.group(1)) if util_match else config_params.get("CORE_UTILIZATION", 30.0)
        core_ar = float(ar_match.group(1)) if ar_match else config_params.get("CORE_ASPECT_RATIO", 1.0)
        core_margin = float(margin_match.group(1)) if margin_match else config_params.get("CORE_MARGIN", 5.0)
        place_density = float(density_match.group(1)) if density_match else config_params.get("PLACE_DENSITY", 0.6)

        metadata = json.loads((run_dir / "run_metadata.json").read_text())
        status = metadata.get("status", "unknown")

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
        finish_metrics = parse_finish_report(run_dir / "reports" / "6_finish.rpt")
        # Parse JSON report for area and additional metrics
        json_metrics = parse_finish_json_report(run_dir / "logs")
        finish_metrics.update(json_metrics)

        stage_runtimes = parse_logs_for_runtime(run_dir / "logs")
        total_runtime = sum(stage_runtimes.values())

        folder_name = run_dir.name
        # Create a clean run_id by removing timestamp and IP prefix
        run_id = folder_name
        for prefix in ["20261103T165433Z_ip-172-31-32-99_", "20261103T170908Z_ip-172-31-47-219_", "20261104T043700Z_ip-172-31-32-99_", "20261105T051211Z_ip-172-31-47-219_", "20261105T084304Z_ip-172-31-32-99_", "20261105T104842Z_ip-172-31-32-99_"]:
            if run_id.startswith(prefix):
                run_id = run_id[len(prefix):]
                break

        return {
            "run_id": f"{design}_{run_id}",
            "timestamp": metadata.get("start_utc", datetime.now().isoformat()),
            "design_name": design,
            "platform": sweep_platform,
            "status": "success" if has_finish else "failed",
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
            "final_area_um2": finish_metrics.get("area_um2"),
            "start_utc": metadata.get("start_utc"),
            "end_utc": metadata.get("end_utc"),
            "timing_closure": (finish_metrics.get("wns_ns", 1.0) >= 0) if finish_metrics.get("wns_ns") is not None else False,
            "drc_clean": (finish_metrics.get("setup_violations", 1) == 0),
            "lvs_clean": True,
            "data_completeness": "complete" if has_finish else "partial",
        }
    except Exception as e:
        print(f"  Error extracting {run_dir.name}: {e}")
        return None


def _write_csv(records: List[dict], csv_path: Path) -> None:
    """Write records to CSV format."""
    if not records:
        return

    fieldnames = [
        'run_id', 'timestamp', 'design_name', 'platform', 'status',
        'core_utilization', 'core_aspect_ratio', 'core_margin', 'place_density',
        'synth_wns_ns', 'synth_tns_ns',
        'floorplan_wns_ns', 'floorplan_tns_ns',
        'place_wns_ns', 'place_tns_ns',
        'cts_wns_ns', 'cts_tns_ns',
        'route_wns_ns', 'route_tns_ns',
        'final_wns_ns', 'final_tns_ns',
        'final_setup_violations', 'final_hold_violations',
        'final_power_w', 'start_utc', 'end_utc',
        'timing_closure', 'drc_clean', 'lvs_clean',
        'data_completeness', 'source'
    ]

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for record in records:
            flat = {}
            for k, v in record.items():
                if isinstance(v, (dict, list)):
                    flat[k] = json.dumps(v, default=str)
                else:
                    flat[k] = v
            writer.writerow(flat)


if __name__ == "__main__":
    main()