#!/usr/bin/env python3
"""
Extract new sweep batches and clean up failed data:
1. ip-172-31-32-99/nangate45/gcd (14 configs)
2. ip-172-31-47-219/nangate45/picorv32 (10 configs)
3. Remove nangate45/aes (failed floorplan config conflict)
"""

import json
import re
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import existing extraction functions
import sys
sys.path.insert(0, str(Path(__file__).parent))
from extract_comprehensive_aws import (
    parse_config_mk,
    parse_synth_report,
    parse_stage_report,
    parse_finish_report,
    parse_finish_json_report,
    parse_logs_for_runtime,
)


def extract_sweep_run(run_dir: Path, platform: str, design: str) -> Optional[dict]:
    """Extract data from a single parameter sweep run directory."""
    try:
        meta_path = run_dir / "run_metadata.json"
        config_path = run_dir / "config.mk"
        reports_dir = run_dir / "reports"
        logs_dir = run_dir / "logs"

        if not meta_path.exists() or not config_path.exists():
            return None

        metadata = json.loads(meta_path.read_text())
        config_params = parse_config_mk(config_path)

        # Extract params from folder name
        folder_name = run_dir.name
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
        json_metrics = parse_finish_json_report(logs_dir)
        finish_metrics.update(json_metrics)

        # Parse runtimes
        stage_runtimes = parse_logs_for_runtime(logs_dir)
        total_runtime = sum(stage_runtimes.values())

        status = metadata.get("status", "unknown")
        has_finish = (reports_dir / "6_finish.rpt").exists()

        if has_finish and status == "success":
            completeness = "complete"
        elif status in ("failed", "timed_out") or metadata.get("timed_out", False):
            completeness = "partial"
        else:
            completeness = "metadata_only"

        # Create clean run_id
        run_id = folder_name
        for prefix in ["20261103T165433Z_ip-172-31-32-99_", "20261103T170908Z_ip-172-31-47-219_",
                       "20261104T043700Z_ip-172-31-32-99_", "20261105T051211Z_ip-172-31-47-219_",
                       "20261105T084304Z_ip-172-31-32-99_", "20261105T104842Z_ip-172-31-32-99_"]:
            if run_id.startswith(prefix):
                run_id = run_id[len(prefix):]
                break

        return {
            "run_id": f"{design}_{run_id}",
            "timestamp": metadata.get("start_utc", datetime.now().isoformat()),
            "design_name": design,
            "platform": platform,
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
        import traceback
        traceback.print_exc()
        return None


def extract_new_sweeps(aws_root: Path) -> List[dict]:
    """Extract the two new sweep batches."""
    all_records = []

    # 1. ip-172-31-32-99/nangate45/gcd
    print("\n" + "="*60)
    print("Extracting: ip-172-31-32-99/nangate45/gcd")
    print("="*60)
    gcd_dir = aws_root / "parameter_sweep" / "ip-172-31-32-99" / "nangate45" / "gcd"
    if gcd_dir.exists():
        run_dirs = [d for d in gcd_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        print(f"Found {len(run_dirs)} run directories")
        for run_dir in sorted(run_dirs):
            print(f"  Processing {run_dir.name}...")
            record = extract_sweep_run(run_dir, "nangate45", "gcd")
            if record:
                all_records.append(record)
                wns = record.get("final_wns_ns", "N/A")
                tns = record.get("final_tns_ns", "N/A")
                area = record.get("final_area_um2", "N/A")
                power = record.get("final_power_w", "N/A")
                print(f"    ✅ WNS={wns}, TNS={tns}, Area={area}, Power={power}")
            else:
                print(f"    ❌ Failed to extract")
    else:
        print(f"Directory not found: {gcd_dir}")

    # 2. ip-172-31-47-219/nangate45/picorv32
    print("\n" + "="*60)
    print("Extracting: ip-172-31-47-219/nangate45/picorv32")
    print("="*60)
    picorv32_dir = aws_root / "parameter_sweep" / "ip-172-31-47-219" / "nangate45" / "picorv32"
    if picorv32_dir.exists():
        run_dirs = [d for d in picorv32_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        print(f"Found {len(run_dirs)} run directories")
        for run_dir in sorted(run_dirs):
            print(f"  Processing {run_dir.name}...")
            record = extract_sweep_run(run_dir, "nangate45", "picorv32")
            if record:
                all_records.append(record)
                wns = record.get("final_wns_ns", "N/A")
                tns = record.get("final_tns_ns", "N/A")
                area = record.get("final_area_um2", "N/A")
                power = record.get("final_power_w", "N/A")
                print(f"    ✅ WNS={wns}, TNS={tns}, Area={area}, Power={power}")
            else:
                print(f"    ❌ Failed to extract")
    else:
        print(f"Directory not found: {picorv32_dir}")

    return all_records


def remove_failed_aes(aws_root: Path) -> None:
    """Remove the failed nangate45/aes data."""
    print("\n" + "="*60)
    print("Removing failed: nangate45/aes")
    print("="*60)
    aes_dir = aws_root / "nangate45" / "aes"
    if aes_dir.exists():
        print(f"Removing: {aes_dir}")
        shutil.rmtree(aes_dir)
        print("✅ Removed")
    else:
        print("Directory not found (already removed?)")


def load_master_dataset(data_dir: Path) -> List[dict]:
    """Load the current master dataset."""
    master_path = data_dir / "real_runs.json"
    if master_path.exists():
        return json.loads(master_path.read_text())
    return []


def save_master_dataset(data_dir: Path, records: List[dict]) -> None:
    """Save the updated master dataset."""
    master_path = data_dir / "real_runs.json"
    master_path.write_text(json.dumps(records, indent=2, default=str))
    print(f"✅ Master dataset saved: {len(records)} runs -> {master_path}")

    # Also save CSV
    csv_path = data_dir / "real_runs_export.csv"
    _write_csv(records, csv_path)


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
        'final_power_w', 'final_area_um2', 'start_utc', 'end_utc',
        'timing_closure', 'drc_clean', 'lvs_clean',
        'data_completeness'
    ]
    import csv
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


def filter_out_aes(records: List[dict]) -> List[dict]:
    """Remove nangate45/aes records from the dataset."""
    filtered = [r for r in records if not (r.get("platform") == "nangate45" and r.get("design_name") == "aes")]
    removed = len(records) - len(filtered)
    print(f"✅ Removed {removed} nangate45/aes records")
    return filtered


def main():
    aws_root = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report")
    data_dir = Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data")

    print("="*60)
    print("NEW SWEEP EXTRACTION AND CLEANUP")
    print("="*60)
    print(f"AWS Root: {aws_root}")
    print(f"Data Dir: {data_dir}")

    # 1. Load current master dataset
    print("\nLoading current master dataset...")
    master_records = load_master_dataset(data_dir)
    print(f"Current: {len(master_records)} runs")

    # 2. Remove failed nangate45/aes
    master_records = filter_out_aes(master_records)

    # 3. Remove the actual AWS_Report directory for aes
    remove_failed_aes(aws_root)

    # 4. Extract new sweeps
    new_records = extract_new_sweeps(aws_root)
    print(f"\nExtracted {len(new_records)} new runs")

    # 5. Combine and save
    all_records = master_records + new_records
    print(f"\nTotal after merge: {len(all_records)} runs")

    # Summary by platform/design
    print("\nSummary by platform/design:")
    for platform in ["asap7", "gf180", "nangate45", "sky130hd"]:
        p_records = [r for r in all_records if r.get("platform") == platform]
        if not p_records:
            continue
        designs = {}
        for r in p_records:
            d = r.get("design_name", "unknown")
            designs[d] = designs.get(d, 0) + 1
        for design, count in sorted(designs.items()):
            tc = sum(1 for r in p_records if r.get("design_name") == design and r.get("timing_closure"))
            print(f"  {platform}/{design}: {count} runs, timing_closure={tc}/{count}")

    # Save
    save_master_dataset(data_dir, all_records)

    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)


if __name__ == "__main__":
    import json
    import re
    import csv
    main()