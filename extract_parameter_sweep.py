#!/usr/bin/env python3
"""
Extract data from parameter_sweep directory structure.
Structure: parameter_sweep/ip-172-31-32-99/nangate45/ibex/<config_folder>/
Each config folder has: config.mk, run_metadata.json, reports/, logs/
"""

import json
import re
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

def parse_run_metadata(meta_path: Path) -> Dict[str, Any]:
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text())

def parse_synth_report(report_path: Path) -> Dict[str, Any]:
    metrics = {}
    if not report_path.exists():
        return metrics
    content = report_path.read_text()
    patterns = {"wns_ns": r"wns max\s+([-\d.]+)", "tns_ns": r"tns max\s+([-\d.]+)"}
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
    patterns = {"wns_ns": r"wns max\s+([-\d.]+)", "tns_ns": r"tns max\s+([-\d.]+)"}
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

def extract_parameter_sweep_run(run_dir: Path) -> Optional[AWSRunRecord]:
    """Extract data from a single parameter sweep run directory."""
    try:
        meta_path = run_dir / "run_metadata.json"
        config_path = run_dir / "config.mk"
        reports_dir = run_dir / "reports"
        logs_dir = run_dir / "logs"

        if not meta_path.exists() or not config_path.exists():
            return None

        metadata = parse_run_metadata(meta_path)
        config_params = parse_config_mk(config_path)

        # Extract params from folder name as backup
        folder_name = run_dir.name
        # Format: 20261103T165433Z_ip-172-31-32-99_nangate45_ibex_u20_ar1.0_m6_d0.7
        util_match = re.search(r'_u(\d+)_', folder_name)
        ar_match = re.search(r'_ar([\d.]+)_', folder_name)
        margin_match = re.search(r'_m(\d+)_', folder_name)
        density_match = re.search(r'_d([\d.]+)$', folder_name)

        core_util = float(util_match.group(1)) if util_match else config_params.get("CORE_UTILIZATION", 30.0)
        core_ar = float(ar_match.group(1)) if ar_match else config_params.get("CORE_ASPECT_RATIO", 1.0)
        core_margin = float(margin_match.group(1)) if margin_match else config_params.get("CORE_MARGIN", 5.0)
        place_density = float(density_match.group(1)) if density_match else config_params.get("PLACE_DENSITY", 0.6)

        # Parse reports
        synth_metrics = parse_synth_report(reports_dir / "1_synth.rpt")
        floorplan_metrics = parse_stage_report(reports_dir / "2_floorplan_final.rpt", "floorplan")
        place_metrics = parse_stage_report(reports_dir / "3_detailed_place.rpt", "place")
        cts_metrics = parse_stage_report(reports_dir / "4_cts_final.rpt", "cts")
        route_metrics = parse_stage_report(reports_dir / "5_global_route.rpt", "route")
        finish_metrics = parse_finish_report(reports_dir / "6_finish.rpt")

        # Parse runtimes
        stage_runtimes, total_runtime = parse_logs_for_runtime(logs_dir), 0
        for v in stage_runtimes.values():
            total_runtime += v

        # Get status from metadata
        status = metadata.get("status", "unknown")

        # Build run_id from folder name
        run_id = folder_name.replace("20261103T165433Z_ip-172-31-32-99_", "")

        return AWSRunRecord(
            run_id=run_id,
            timestamp=metadata.get("start_utc", datetime.now().isoformat()),
            design_name="ibex",
            platform="nangate45",
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
            final_setup_violations=int(finish_metrics.get("setup_violations", 0)),
            final_hold_violations=int(finish_metrics.get("hold_violations", 0)),
            final_power_w=finish_metrics.get("power_w"),
            start_utc=metadata.get("start_utc"),
            end_utc=metadata.get("end_utc"),
            timing_closure=(finish_metrics.get("wns_ns", 1.0) >= 0) if finish_metrics.get("wns_ns") is not None else False,
            drc_clean=(finish_metrics.get("setup_violations", 1) == 0),
            lvs_clean=True,
        )
    except Exception as e:
        print(f"  Error extracting {run_dir.name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract parameter sweep data")
    parser.add_argument("--sweep-root", type=Path, default=Path("/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report/parameter_sweep/ip-172-31-32-99/nangate45/ibex"),
                        help="Parameter sweep root directory")
    parser.add_argument("--platform", type=str, default="nangate45", help="Platform")
    parser.add_argument("--output", type=Path, default=Path("openroad_gui/intelligence/data/aws_real_runs_ibex_sweep.json"), help="Output JSON file")
    args = parser.parse_args()

    sweep_root = args.sweep_root
    if not sweep_root.exists():
        print(f"Sweep root not found: {sweep_root}")
        return

    all_records = []
    for run_dir in sorted(sweep_root.iterdir()):
        if not run_dir.is_dir():
            continue
        if run_dir.name.startswith("."):
            continue

        finish_report = run_dir / "reports" / "6_finish.rpt"
        if not finish_report.exists():
            print(f"  ⏭️  Skipping {run_dir.name} - no 6_finish.rpt")
            continue

        print(f"  Processing {run_dir.name}...")
        record = extract_parameter_sweep_run(run_dir)
        if record:
            all_records.append(record)
            wns = record.final_wns_ns if record.final_wns_ns is not None else "N/A"
            tns = record.final_tns_ns if record.final_tns_ns is not None else "N/A"
            power = record.final_power_w if record.final_power_w is not None else "N/A"
            print(f"    ✅ WNS={wns}, TNS={tns}, Setup={record.final_setup_violations}, Power={power}")

    # Save to JSON
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = [asdict(r) for r in all_records]
    output_path.write_text(json.dumps(output_data, indent=2, default=str))

    print(f"\n✅ Extracted {len(all_records)} runs")
    print(f"   Saved to: {output_path}")

    # Summary
    if all_records:
        print("\nSummary:")
        for r in all_records:
            wns = r.final_wns_ns if r.final_wns_ns is not None else "N/A"
            tns = r.final_tns_ns if r.final_tns_ns is not None else "N/A"
            power = r.final_power_w if r.final_power_w is not None else "N/A"
            print(f"  {r.run_id}: WNS={wns}, TNS={tns}, SetupViol={r.final_setup_violations}, Power={power}")

if __name__ == "__main__":
    main()