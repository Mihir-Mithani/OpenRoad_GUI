#!/usr/bin/env python3
"""
Extract training data from AWS ORFS reports.
AWS reports have slightly different format than local ORFS runs.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class AWSRunRecord:
    """Single AWS ORFS run record."""
    # Identity
    run_id: str
    timestamp: str
    design_name: str
    platform: str
    status: str

    # Config parameters
    core_utilization: float
    core_aspect_ratio: float
    core_margin: float
    place_density: float

    # Per-stage metrics (all optional since some stages may not have reports)
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

    # Final PPA
    final_wns_ns: Optional[float] = None
    final_tns_ns: Optional[float] = None
    final_setup_violations: int = 0
    final_hold_violations: int = 0
    final_power_w: Optional[float] = None  # Watts from report_power

    # Runtime (from metadata)
    start_utc: Optional[str] = None
    end_utc: Optional[str] = None

    # Success flags
    timing_closure: bool = False
    drc_clean: bool = True
    lvs_clean: bool = True


def parse_config_mk(config_path: Path) -> Dict[str, Any]:
    """Parse config.mk for design parameters."""
    params = {}
    if not config_path.exists():
        return params

    content = config_path.read_text()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            _, rest = line.split("export ", 1)
            key, value = rest.split("=", 1)
            key = key.strip()
            value = value.strip()
            try:
                params[key] = float(value)
            except ValueError:
                params[key] = value
    return params


def parse_synth_report(report_path: Path) -> Dict[str, Any]:
    """Parse 1_synth.rpt for synthesis metrics."""
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

    # Power from report_power section
    power_match = re.search(r"Total\s+[\de\.\-]+\s+[\de\.\-]+\s+[\de\.\-]+\s+([\de\.\-]+)\s+100\.0%", content)
    if power_match:
        try:
            metrics["power_w"] = float(power_match.group(1))
        except ValueError:
            pass

    return metrics


def parse_place_report(report_path: Path, stage: str) -> Dict[str, Any]:
    """Parse place reports (global/detailed)."""
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


def parse_cts_report(report_path: Path) -> Dict[str, Any]:
    """Parse 4_cts_final.rpt."""
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
                metrics[f"cts_{key}"] = float(match.group(1))
            except ValueError:
                pass

    return metrics


def parse_route_report(report_path: Path) -> Dict[str, Any]:
    """Parse 5_global_route.rpt."""
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
                metrics[f"route_{key}"] = float(match.group(1))
            except ValueError:
                pass

    # Congestion
    cong_match = re.search(r"congestion\s*:\s*(\d+)", content, re.IGNORECASE)
    if cong_match:
        try:
            metrics["route_congestion_pct"] = int(cong_match.group(1))
        except ValueError:
            pass

    return metrics


def parse_finish_report(report_path: Path) -> Dict[str, Any]:
    """Parse 6_finish.rpt for final metrics."""
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

    # Power from report_power section (last one in finish report)
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
    """Parse log files for stage runtimes."""
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


def extract_aws_run(run_dir: Path) -> Optional[AWSRunRecord]:
    """Extract all metrics from a single AWS ORFS run directory."""
    try:
        # Parse metadata
        metadata_path = run_dir / "run_metadata.json"
        if not metadata_path.exists():
            return None

        metadata = json.loads(metadata_path.read_text())
        design_name = metadata.get("design", "")
        platform = metadata.get("platform", "")
        status = metadata.get("status", "")

        if status != "success":
            print(f"  Skipping {design_name} - status: {status}")
            return None

        # Parse config.mk
        config_path = run_dir / "config.mk"
        config_params = parse_config_mk(config_path)

        core_util = config_params.get("CORE_UTILIZATION", 30.0)
        core_ar = config_params.get("CORE_ASPECT_RATIO", 1.0)
        core_margin = config_params.get("CORE_MARGIN", 5.0)
        place_density = config_params.get("PLACE_DENSITY", 0.6)

        # Parse reports
        reports_dir = run_dir / "reports"
        logs_dir = run_dir / "logs"

        synth_metrics = parse_synth_report(reports_dir / "1_synth.rpt")
        floorplan_metrics = parse_place_report(reports_dir / "2_floorplan_final.rpt", "floorplan")
        place_metrics = parse_place_report(reports_dir / "3_detailed_place.rpt", "place")
        cts_metrics = parse_cts_report(reports_dir / "4_cts_final.rpt")
        route_metrics = parse_route_report(reports_dir / "5_global_route.rpt")
        finish_metrics = parse_finish_report(reports_dir / "6_finish.rpt")

        # Stage runtimes from logs
        stage_runtimes = parse_logs_for_runtime(logs_dir)

        # Build record
        run_id = metadata.get("run_id", f"{design_name}_{platform}")

        return AWSRunRecord(
            run_id=run_id,
            timestamp=metadata.get("start_utc", datetime.now().isoformat()),
            design_name=design_name,
            platform=platform,
            status=status,
            core_utilization=core_util,
            core_aspect_ratio=core_ar,
            core_margin=core_margin,
            place_density=place_density,
            synth_wns_ns=synth_metrics.get("wns_ns"),
            synth_tns_ns=synth_metrics.get("tns_ns"),
            floorplan_wns_ns=floorplan_metrics.get("floorplan_wns_ns"),
            floorplan_tns_ns=floorplan_metrics.get("floorplan_tns_ns"),
            place_wns_ns=place_metrics.get("place_wns_ns"),
            place_tns_ns=place_metrics.get("place_tns_ns"),
            cts_wns_ns=cts_metrics.get("cts_wns_ns"),
            cts_tns_ns=cts_metrics.get("cts_tns_ns"),
            route_wns_ns=route_metrics.get("route_wns_ns"),
            route_tns_ns=route_metrics.get("route_tns_ns"),
            final_wns_ns=finish_metrics.get("wns_ns"),
            final_tns_ns=finish_metrics.get("tns_ns"),
            final_setup_violations=finish_metrics.get("setup_violations", 0),
            final_hold_violations=finish_metrics.get("hold_violations", 0),
            final_power_w=finish_metrics.get("power_w"),
            start_utc=metadata.get("start_utc"),
            end_utc=metadata.get("end_utc"),
            timing_closure=(finish_metrics.get("wns_ns", 1.0) >= 0) if finish_metrics.get("wns_ns") is not None else False,
            drc_clean=finish_metrics.get("setup_violations", 1) == 0,
            lvs_clean=True,
        )
    except Exception as e:
        print(f"  Error extracting {run_dir.name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract AWS ORFS report data")
    parser.add_argument("--aws-root", type=Path, default=Path("/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report"),
                        help="AWS_Report root directory")
    parser.add_argument("--platform", type=str, default=None,
                        help="Platform to filter (e.g., asap7, gf180). If not specified, uses metadata from run.")
    parser.add_argument("--output", type=Path, default=Path("openroad_gui/intelligence/data/aws_real_runs.json"),
                        help="Output JSON file")
    args = parser.parse_args()

    aws_report_root = args.aws_root

    if not aws_report_root.exists():
        print(f"AWS_Report not found at {aws_report_root}")
        return

    all_records = []

    def find_run_dirs(root: Path) -> List[Path]:
        """Find all run directories (containing 6_finish.rpt) under a platform root."""
        run_dirs = []
        for item in root.iterdir():
            if not item.is_dir():
                continue
            # Check if this item itself is a run dir (has reports/6_finish.rpt)
            if (item / "reports" / "6_finish.rpt").exists():
                run_dirs.append(item)
            else:
                # Check if it's a design dir containing run dirs
                for sub_item in item.iterdir():
                    if sub_item.is_dir() and (sub_item / "reports" / "6_finish.rpt").exists():
                        run_dirs.append(sub_item)
        return run_dirs

    # Determine which platform directories to process
    if args.platform:
        platform_dirs = [aws_report_root / args.platform]
        if not platform_dirs[0].exists():
            print(f"Platform directory not found: {platform_dirs[0]}")
            return
    else:
        platform_dirs = [p for p in sorted(aws_report_root.iterdir())
                         if p.is_dir() and not p.name.startswith(".") and not p.name.startswith("drive-download")]

    for platform_dir in platform_dirs:
        print(f"\nProcessing platform: {platform_dir.name}...")

        # Find all run dirs (handles both flat and nested structures)
        run_dirs = find_run_dirs(platform_dir)

        for run_dir in run_dirs:
            finish_report = run_dir / "reports" / "6_finish.rpt"
            if not finish_report.exists():
                continue

            # Check platform filter (double-check from metadata)
            if args.platform:
                metadata_path = run_dir / "run_metadata.json"
                if metadata_path.exists():
                    metadata = json.loads(metadata_path.read_text())
                    if metadata.get("platform", "") != args.platform:
                        continue

            record = extract_aws_run(run_dir)
            if record:
                all_records.append(record)
                wns = record.final_wns_ns if record.final_wns_ns is not None else "N/A"
                tns = record.final_tns_ns if record.final_tns_ns is not None else "N/A"
                power = record.final_power_w if record.final_power_w is not None else "N/A"
                print(f"  ✅ {record.run_id}: WNS={wns}, TNS={tns}, Setup={record.final_setup_violations}, Power={power}")

    # Save to JSON
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = [asdict(r) for r in all_records]
    output_path.write_text(json.dumps(output_data, indent=2, default=str))

    print(f"\n✅ Extracted {len(all_records)} successful runs")
    print(f"   Saved to: {output_path}")

    # Summary
    if all_records:
        print("\nSummary:")
        for r in all_records:
            wns = r.final_wns_ns if r.final_wns_ns is not None else "N/A"
            tns = r.final_tns_ns if r.final_tns_ns is not None else "N/A"
            power = r.final_power_w if r.final_power_w is not None else "N/A"
            print(f"  {r.design_name} ({r.platform}): WNS={wns}, TNS={tns}, SetupViol={r.final_setup_violations}, Power={power}")


if __name__ == "__main__":
    main()