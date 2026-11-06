#!/usr/bin/env python3
"""Convert real_runs.json to CSV format."""
import json
import csv
from pathlib import Path

json_path = Path("openroad_gui/intelligence/data/real_runs.json")
csv_path = Path("openroad_gui/intelligence/data/real_runs_export.csv")

with open(json_path) as f:
    data = json.load(f)

if not data:
    print("No data to convert")
    exit(0)

# Flatten any nested structures
def flatten_record(r):
    flat = {}
    for k, v in r.items():
        if isinstance(v, (dict, list)):
            flat[k] = json.dumps(v, default=str)
        else:
            flat[k] = v
    return flat

flat_data = [flatten_record(r) for r in data]

# Ensure consistent column order
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
    for row in flat_data:
        writer.writerow(row)

print(f"✅ Converted {len(data)} runs to CSV: {csv_path}")
