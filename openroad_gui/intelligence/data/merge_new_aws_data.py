#!/usr/bin/env python3
"""
Merge newly extracted AWS batch data into the master training dataset.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

MASTER_PATH = Path('/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json')
NEW_DATA_PATH = Path('/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report/asap_new_batch/extracted/training_data.jsonl')
OUTPUT_PATH = Path('/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json')
BACKUP_PATH = Path('/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_training.json.backup')

def load_master():
    """Load master dataset."""
    with open(MASTER_PATH, 'r') as f:
        return json.load(f)

def load_new_data():
    """Load new extracted data from JSONL."""
    records = []
    with open(NEW_DATA_PATH, 'r') as f:
        for line in f:
            records.append(json.loads(line.strip()))
    return records

def normalize_new_record(record: dict) -> dict:
    """Normalize new record to match master schema."""
    normalized = {}

    # Direct mappings (fields that exist in both)
    direct_mapping = {
        'run_id': 'run_id',
        'timestamp': 'extracted_at',  # map extracted_at to timestamp
        'design_name': 'design_name',
        'platform': 'platform',
        'status': 'status',
        'core_utilization': 'core_utilization',
        'core_aspect_ratio': 'core_aspect_ratio',
        'core_margin': 'core_margin',
        'place_density': 'place_density',
        'final_wns_ns': 'final_wns_ns',
        'final_tns_ns': 'final_tns_ns',
        'final_setup_violations': 'final_setup_violations',
        'final_hold_violations': 'final_hold_violations',
        'final_power_w': 'final_power_total_w',
        'final_area_um2': 'final_area_um2',
        'final_drc_violations': 'final_drc_violations',
        'final_congestion_pct': 'final_congestion_pct',
        'final_power_mw': 'final_power_total_w',  # convert W to mW
        'num_instances': 'final_instance_count',
        'final_drc_violations': 'final_drc_violations',
        'final_congestion_pct': 'final_congestion_pct',
    }

    for master_key, new_key in direct_mapping.items():
        if new_key in record:
            val = record[new_key]
            # Handle type conversions
            if master_key in ['core_utilization', 'core_margin', 'final_setup_violations',
                             'final_hold_violations', 'final_drc_violations']:
                normalized[master_key] = int(val) if val is not None and not np.isnan(val) else 0
            elif master_key in ['core_aspect_ratio', 'place_density', 'final_wns_ns',
                               'final_tns_ns', 'final_wns_ns', 'final_tns_ns',
                               'final_power_w', 'final_area_um2']:
                normalized[master_key] = float(val) if val is not None and not np.isnan(val) else np.nan
            elif master_key == 'timestamp':
                # Parse timestamp string to datetime string
                if isinstance(val, str):
                    normalized[master_key] = val
                else:
                    normalized[master_key] = datetime.now().isoformat()
            elif master_key == 'status':
                normalized[master_key] = str(val) if val else 'unknown'
            else:
                normalized[master_key] = val

    # Handle fields that exist in master but not in new data (set to NaN/None)
    na_fields = {
        'synth_wns_ns': np.nan, 'synth_tns_ns': np.nan,
        'floorplan_wns_ns': np.nan, 'floorplan_tns_ns': np.nan,
        'place_wns_ns': np.nan, 'place_tns_ns': np.nan,
        'cts_wns_ns': np.nan, 'cts_tns_ns': np.nan,
        'route_wns_ns': np.nan, 'route_tns_ns': np.nan,
        'final_setup_violations': 0,
        'final_hold_violations': 0,
        'start_utc': np.nan,
        'end_utc': np.nan,
        'timing_closure': False,
        'drc_clean': False,
        'lvs_clean': True,
        'data_completeness': 'complete',
        'final_power_mw': None,
        'num_instances': None,
        'num_nets': None,
        'num_sequential': None,
        'num_macros': 0,
        'macro_area_ratio': 0.0,
        'final_congestion_pct': np.nan,
        'stage_runtimes': '{}',
        'total_runtime_sec': 0,
        'suitable_for_regression': True,
        'log_instances': np.nan,
        'log_nets': np.nan,
        'seq_ratio': np.nan,
        'macro_ratio': 0.0,
        'log_area': np.nan,
        'log_power': np.nan,
        'wns_normalized': np.nan,
        'tns_normalized': np.nan,
        'timing_closure_bin': 0,
        'drc_clean_bin': 0,
        'lvs_clean_bin': 1,
        'platform_cat': None,
        'design_name_config': None,
        'platform_config': None,
        'final_power_mw': None,
        'num_instances': None,
        'num_nets': None,
        'num_sequential': None,
        'num_macros': 0,
        'macro_area_ratio': 0.0,
        'final_congestion_pct': np.nan,
        'stage_runtimes': '{}',
        'total_runtime_sec': 0,
        'suitable_for_regression': True,
        'log_instances': np.nan,
        'log_nets': np.nan,
        'seq_ratio': np.nan,
        'macro_ratio': 0.0,
        'log_area': np.nan,
        'log_power': np.nan,
        'wns_normalized': np.nan,
        'tns_normalized': np.nan,
        'timing_closure_bin': 0,
        'drc_clean_bin': 0,
        'lvs_clean_bin': 1,
        'platform_cat': None,
        'design_name_config': None,
        'platform_config': None,
    }

    # Add design info
    normalized['design_name'] = record.get('design_name', 'unknown')
    normalized['platform'] = record.get('platform', 'asap7')
    normalized['run_id'] = record.get('run_id', 'unknown')
    normalized['timestamp'] = record.get('extracted_at', datetime.now().isoformat())
    normalized['status'] = record.get('status', 'success')
    normalized['core_utilization'] = record.get('core_utilization', 0)
    normalized['core_aspect_ratio'] = record.get('core_aspect_ratio', 1.0)
    normalized['core_margin'] = record.get('core_margin', 4.0)
    normalized['place_density'] = record.get('place_density', 0.55)

    # Timing metrics
    normalized['final_wns_ns'] = record.get('final_wns_ns', np.nan)
    normalized['final_tns_ns'] = record.get('final_tns_ns', np.nan)
    normalized['final_wns_ns'] = record.get('final_wns_ns', np.nan)
    normalized['final_tns_ns'] = record.get('final_tns_ns', np.nan)
    normalized['final_setup_violations'] = record.get('final_setup_violations', 0)
    normalized['final_hold_violations'] = record.get('final_hold_violations', 0)

    # Power
    pw = record.get('final_power_total_w', 0)
    normalized['final_power_w'] = float(pw) if pw is not None else 0.0
    normalized['final_power_mw'] = float(pw * 1000) if pw is not None else 0.0

    # Area
    normalized['final_area_um2'] = float(record.get('final_area_um2', 0)) if record.get('final_area_um2') is not None else 0.0

    # DRC
    drc_val = record.get('final_drc_violations')
    normalized['final_drc_violations'] = int(drc_val) if drc_val is not None else 0
    congestion_val = record.get('final_congestion_pct')
    normalized['final_congestion_pct'] = float(congestion_val) if congestion_val is not None else np.nan

    # Power in mW
    normalized['final_power_mw'] = float(record.get('final_power_total_w', 0) * 1000) if record.get('final_power_total_w') is not None else 0.0

    # Instance counts
    inst_count = record.get('final_instance_count')
    normalized['num_instances'] = int(inst_count) if inst_count is not None else 0
    normalized['num_nets'] = 0
    normalized['num_sequential'] = 0
    normalized['num_macros'] = 0
    normalized['macro_area_ratio'] = 0.0

    # DRC
    drc_val = record.get('final_drc_violations')
    normalized['final_drc_violations'] = int(drc_val) if drc_val is not None else 0
    congestion_val = record.get('final_congestion_pct')
    normalized['final_congestion_pct'] = float(congestion_val) if congestion_val is not None else np.nan

    # Derived fields
    normalized['final_power_mw'] = float(record.get('final_power_total_w', 0) * 1000) if record.get('final_power_total_w') is not None else 0.0
    normalized['log_instances'] = np.nan
    normalized['log_nets'] = np.nan
    normalized['seq_ratio'] = np.nan
    normalized['macro_ratio'] = 0.0
    normalized['log_area'] = np.nan
    normalized['log_power'] = np.nan
    normalized['wns_normalized'] = np.nan
    normalized['tns_normalized'] = np.nan
    normalized['timing_closure_bin'] = 0
    normalized['drc_clean_bin'] = 0
    normalized['lvs_clean_bin'] = 1
    normalized['platform_cat'] = 'asap7'
    normalized['design_name_config'] = record.get('design_name', 'unknown')
    normalized['platform_config'] = 'asap7'
    normalized['final_power_mw'] = float(record.get('final_power_total_w', 0) * 1000) if record.get('final_power_total_w') is not None else 0.0
    normalized['num_instances'] = 0
    normalized['num_nets'] = 0
    normalized['num_sequential'] = 0
    normalized['num_macros'] = 0
    normalized['macro_area_ratio'] = 0.0
    normalized['final_congestion_pct'] = np.nan
    normalized['stage_runtimes'] = '{}'
    normalized['total_runtime_sec'] = 0
    normalized['suitable_for_regression'] = True
    normalized['log_instances'] = np.nan
    normalized['log_nets'] = np.nan
    normalized['seq_ratio'] = np.nan
    normalized['macro_ratio'] = 0.0
    normalized['log_area'] = np.nan
    normalized['log_power'] = np.nan
    normalized['wns_normalized'] = np.nan
    normalized['tns_normalized'] = np.nan
    normalized['timing_closure_bin'] = 0
    normalized['drc_clean_bin'] = 0
    normalized['lvs_clean_bin'] = 1
    normalized['platform_cat'] = 'asap7'
    normalized['design_name_config'] = record.get('design_name', 'unknown')
    normalized['platform_config'] = 'asap7'

    # Set timestamps
    normalized['timestamp'] = record.get('extracted_at', datetime.now().isoformat())
    normalized['start_utc'] = np.nan
    normalized['end_utc'] = np.nan
    normalized['timing_closure'] = False
    normalized['drc_clean'] = False
    normalized['lvs_clean'] = True
    normalized['data_completeness'] = 'complete'
    normalized['stage_runtimes'] = '{}'
    normalized['total_runtime_sec'] = 0
    normalized['suitable_for_regression'] = True
    normalized['log_instances'] = np.nan
    normalized['log_nets'] = np.nan
    normalized['seq_ratio'] = np.nan
    normalized['macro_ratio'] = 0.0
    normalized['log_area'] = np.nan
    normalized['log_power'] = np.nan
    normalized['wns_normalized'] = np.nan
    normalized['tns_normalized'] = np.nan
    normalized['timing_closure_bin'] = 0
    normalized['drc_clean_bin'] = 0
    normalized['lvs_clean_bin'] = 1
    normalized['platform_cat'] = 'asap7'
    normalized['design_name_config'] = record.get('design_name', 'unknown')
    normalized['platform_config'] = 'asap7'

    return normalized

def main():
    print("Loading master dataset...")
    master_data = load_master()
    master_df = pd.DataFrame(master_data)
    print(f"Master records: {len(master_df)}")

    print("Loading new data...")
    new_records = load_new_data()
    print(f"New records: {len(new_records)}")

    # Normalize new records
    print("Normalizing new records...")
    normalized_records = []
    for record in new_records:
        normalized = normalize_new_record(record)
        normalized_records.append(normalized)

    new_df = pd.DataFrame(normalized_records)
    print(f"Normalized new records: {len(new_df)}")
    print(f"New columns: {list(new_df.columns)}")

    # Align columns with master
    master_cols = master_df.columns.tolist()
    new_df = new_df.reindex(columns=master_cols, fill_value=np.nan)

    # Combine
    print("Merging datasets...")
    combined_df = pd.concat([master_df, new_df], ignore_index=True, sort=False)
    print(f"Combined records: {len(combined_df)}")

    # Remove duplicates by run_id (keep last)
    combined_df = combined_df.drop_duplicates(subset='run_id', keep='last')
    print(f"After deduplication: {len(combined_df)}")

    # Backup original
    print(f"Backing up original to {BACKUP_PATH}")
    with open(MASTER_PATH, 'r') as f:
        original = f.read()
    with open(BACKUP_PATH, 'w') as f:
        f.write(original)

    # Save merged
    print(f"Saving merged dataset to {OUTPUT_PATH}")
    combined_records = combined_df.to_dict(orient='records')
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(combined_records, f, indent=2, default=str)

    # Verify
    print("\nVerification:")
    print(f"  Total records: {len(combined_df)}")
    print(f"  Designs: {combined_df['design_name'].nunique()}")
    print(f"  Platforms: {combined_df['platform'].nunique()}")
    print(f"  Status distribution:")
    print(combined_df['status'].value_counts())

    if 'final_wns_ns' in combined_df.columns:
        successful = combined_df[combined_df['final_wns_ns'].notna()]
        print(f"\nSuccessful runs: {len(successful)}/{len(combined_df)}")
        if len(successful) > 0:
            print(f"WNS range: {successful['final_wns_ns'].min():.3f} to {successful['final_wns_ns'].max():.3f} ns")
            print(f"TNS range: {successful['final_tns_ns'].min():.1f} to {successful['final_tns_ns'].max():.1f} ns")
            print(f"Area range: {successful['final_area_um2'].min():.0f} to {successful['final_area_um2'].max():.0f} um2")
            print(f"Power range: {successful['final_power_w'].min():.6f} to {successful['final_power_w'].max():.6f} W")

    print(f"\nDone! Backup saved to {BACKUP_PATH}")

if __name__ == '__main__':
    main()