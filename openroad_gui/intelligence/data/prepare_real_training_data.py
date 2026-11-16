#!/usr/bin/env python3
"""
Prepare real training data from AWS comprehensive extraction.
Converts aws_real_runs_comprehensive.json to the format expected by training scripts.
Adds engineered features and missing columns with reasonable defaults/estimates.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

INPUT_PATH = Path(__file__).parent / "aws_real_runs_comprehensive.json"
OUTPUT_PATH = Path(__file__).parent / "real_runs_training.json"

def prepare_training_data():
    """Load AWS comprehensive data and prepare for training."""
    print(f"Loading data from {INPUT_PATH}")

    with open(INPUT_PATH, 'r') as f:
        records = json.load(f)

    print(f"Loaded {len(records)} records")

    df = pd.DataFrame(records)
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")

    # Check data completeness
    print(f"\nData completeness distribution:")
    print(df['data_completeness'].value_counts())

    print(f"\nPlatform distribution:")
    print(df['platform'].value_counts())

    print(f"\nDesign distribution:")
    print(df['design_name'].value_counts())

    print(f"\nStatus distribution:")
    print(df['status'].value_counts())

    # Convert power from W to mW
    if 'final_power_w' in df.columns:
        df['final_power_mw'] = df['final_power_w'] * 1000

    # Add missing columns with estimates
    # Estimate num_instances from area (rough heuristic: ~1 instance per 100-200 um2 for standard cells)
    if 'num_instances' not in df.columns:
        if 'final_area_um2' in df.columns:
            df['num_instances'] = (df['final_area_um2'] / 150).fillna(5000).astype(int)
        else:
            df['num_instances'] = 5000

    if 'num_nets' not in df.columns:
        df['num_nets'] = (df['num_instances'] * 1.2).astype(int)

    if 'num_sequential' not in df.columns:
        df['num_sequential'] = (df['num_instances'] * 0.2).astype(int)

    if 'num_macros' not in df.columns:
        df['num_macros'] = 0

    if 'macro_area_ratio' not in df.columns:
        df['macro_area_ratio'] = 0.0

    # DRC violations - use setup_violations as proxy
    if 'final_drc_violations' not in df.columns:
        df['final_drc_violations'] = df.get('final_setup_violations', 0).fillna(0).astype(int)

    # Congestion - estimate from place_density
    if 'final_congestion_pct' not in df.columns:
        # Higher density -> higher congestion estimate
        place_density = pd.to_numeric(df.get('place_density', 0.6), errors='coerce').fillna(0.6)
        df['final_congestion_pct'] = (place_density * 100).clip(0, 100)

    # Hold violations
    if 'final_hold_violations' not in df.columns:
        df['final_hold_violations'] = 0

    # Stage runtimes - empty dict for now
    if 'stage_runtimes' not in df.columns:
        df['stage_runtimes'] = '{}'

    # Total runtime - estimate from start/end UTC
    if 'total_runtime_sec' not in df.columns:
        def estimate_runtime(row):
            try:
                if pd.notna(row.get('start_utc')) and pd.notna(row.get('end_utc')):
                    start = pd.to_datetime(row['start_utc'])
                    end = pd.to_datetime(row['end_utc'])
                    return (end - start).total_seconds()
            except:
                pass
            return 0.0

        df['total_runtime_sec'] = df.apply(estimate_runtime, axis=1)

    # Timing closure and DRC clean flags
    if 'timing_closure' not in df.columns:
        df['timing_closure'] = (df.get('final_wns_ns', -1) >= 0).astype(int)

    if 'drc_clean' not in df.columns:
        df['drc_clean'] = (df.get('final_drc_violations', 1) == 0).astype(int)

    if 'lvs_clean' not in df.columns:
        df['lvs_clean'] = True

    # Add flag for regression-suitable data (complete runs with valid targets)
    df['suitable_for_regression'] = (
        (df['data_completeness'] == 'complete') &
        df['final_wns_ns'].notna() &
        df['final_tns_ns'].notna() &
        df['final_area_um2'].notna() &
        df['final_power_mw'].notna()
    )

    # Add engineered features
    df['log_instances'] = np.log1p(df['num_instances']) / 20
    df['log_nets'] = np.log1p(df['num_nets']) / 20
    df['seq_ratio'] = df['num_sequential'] / np.maximum(df['num_instances'], 1)
    df['macro_ratio'] = df['num_macros'] / np.maximum(df['num_instances'], 1)
    df['log_area'] = np.log1p(df['final_area_um2'].clip(lower=0)) / 20
    df['log_power'] = np.log1p(df['final_power_mw'].clip(lower=0)) / 20
    df['wns_normalized'] = np.clip(df['final_wns_ns'] / 10, -1, 1)
    df['tns_normalized'] = np.clip(df['final_tns_ns'] / 1000, -1, 1)
    df['timing_closure_bin'] = (df['final_wns_ns'] >= 0).astype(int)
    df['drc_clean_bin'] = (df['final_drc_violations'] == 0).astype(int)
    df['lvs_clean_bin'] = df['lvs_clean'].astype(int)
    df['platform_cat'] = df['platform']
    df['design_name_config'] = df['design_name']
    df['platform_config'] = df['platform']

    # Generate run_id and timestamp if missing
    if 'run_id' not in df.columns:
        df['run_id'] = [f"{d}_{p}_real_{i:08x}" for i, (d, p) in enumerate(zip(df['design_name'], df['platform']))]
    if 'timestamp' not in df.columns:
        rng = np.random.default_rng(42)
        anchor = datetime.now()
        df['timestamp'] = [(anchor - timedelta(seconds=float(s))).isoformat()
                           for s in rng.uniform(0, 365 * 86400, len(df))]

    # Print summary
    print(f"\nPrepared training data shape: {df.shape}")
    print(f"Timing closure rate: {df['timing_closure_bin'].mean():.3f}")
    print(f"DRC clean rate: {df['drc_clean_bin'].mean():.3f}")
    print(f"Platforms: {df['platform'].unique()}")
    print(f"Designs: {df['design_name'].unique()}")
    print(f"Core utilization range: {df['core_utilization'].min()}-{df['core_utilization'].max()}")
    print(f"Final WNS range: {df['final_wns_ns'].min():.2f} to {df['final_wns_ns'].max():.2f}")
    print(f"Final TNS range: {df['final_tns_ns'].min():.2f} to {df['final_tns_ns'].max():.2f}")
    print(f"Final Area range: {df['final_area_um2'].min():.0f} to {df['final_area_um2'].max():.0f}")
    print(f"Final Power range: {df['final_power_mw'].min():.2f} to {df['final_power_mw'].max():.2f}")

    # Save
    output_records = df.to_dict('records')
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output_records, f, indent=2, default=str)

    print(f"\n✅ Saved {len(output_records)} records to {OUTPUT_PATH}")

    return df

if __name__ == "__main__":
    prepare_training_data()