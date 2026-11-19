#!/usr/bin/env python3
"""
Extract training data from AWS ORFS batch reports.
Processes 6_report.json and intermediate stage JSONs to extract PPA metrics and design features.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Target fields to extract from 6_report.json (final sign-off)
TARGET_FIELDS = {
    # Timing
    'final_wns_ns': 'finish__timing__setup__ws',  # WNS is 'ws' (worst slack) in ORFS
    'final_tns_ns': 'finish__timing__setup__tns',
    'final_setup_ws': 'finish__timing__setup__ws',
    'final_hold_tns': 'finish__timing__hold__tns',
    'final_hold_ws': 'finish__timing__hold__ws',
    'final_fmax_mhz': 'finish__timing__fmax',  # Hz -> MHz
    'final_skew_setup': 'finish__clock__skew__setup',
    'final_skew_hold': 'finish__clock__skew__hold',
    'final_setup_violations': 'finish__timing__drv__setup_violation_count',
    'final_hold_violations': 'finish__timing__drv__hold_violation_count',
    'final_max_slew_limit': 'finish__timing__drv__max_slew_limit',
    'final_max_cap_limit': 'finish__timing__drv__max_cap_limit',
    'final_max_fanout_limit': 'finish__timing__drv__max_fanout_limit',

    # Power
    'final_power_total_w': 'finish__power__total',
    'final_power_internal': 'finish__power__internal__total',
    'final_power_switching': 'finish__power__switching__total',
    'final_power_leakage': 'finish__power__leakage__total',

    # Area
    'final_area_um2': 'finish__design__core__area',
    'final_die_area_um2': 'finish__design__die__area',
    'final_instance_area_um2': 'finish__design__instance__area',
    'final_instance_count': 'finish__design__instance__count',
    'final_drc_violations': 'finish__flow__warnings__count',  # approximate

    # DRC/Violations
    'final_drc_violations_detailed': 'finish__flow__warnings__count',
    'final_setup_violations': 'finish__timing__drv__setup_violation_count',
    'final_hold_violations': 'finish__timing__drv__hold_violation_count',

    # DRC/Violations detailed
    'final_drc_errors': 'detailedroute__route__drc_errors',

    # Power breakdown
    'final_power_internal': 'finish__power__internal__total',
    'final_power_switching': 'finish__power__switching__total',
    'final_power_leakage': 'finish__power__leakage__total',
    'final_power_total': 'finish__power__total',

    # Area breakdown
    'final_core_area': 'finish__design__core__area',
    'final_die_area': 'finish__design__die__area',
    'final_instance_area': 'finish__design__instance__area',
    'final_instance_count': 'finish__design__instance__count',
    'final_instance_count_stdcell': 'finish__design__instance__count__stdcell',
    'final_instance_area_stdcell': 'finish__design__instance__area__stdcell',
    'final_instance_count_macros': 'finish__design__instance__count__macros',
    'final_instance_area_macros': 'finish__design__instance__area__macros',

    # Utilization
    'final_utilization': 'finish__design__instance__utilization',
    'final_utilization_stdcell': 'finish__design__instance__utilization__stdcell',

    # Rows/Sites
    'final_rows': 'finish__design__rows',
    'final_sites': 'finish__design__sites',

    # Power grid
    'pg_voltage_worst_vdd': 'finish__design_powergrid__voltage__worst__net:VDD__corner:default',
    'pg_drop_avg_vdd': 'finish__design_powergrid__drop__average__net:VDD__corner:default',
    'pg_drop_worst_vdd': 'finish__design_powergrid__drop__worst__net:VDD__corner:default',

    # Clock
    'final_clock_skew_setup': 'finish__clock__skew__setup',
    'final_clock_skew_hold': 'finish__clock__skew__hold',
    'final_fmax_mhz': 'finish__timing__fmax',

    # DRC
    'final_drc_violations': 'detailedroute__route__drc_errors',

    # Congestion
    # 'final_congestion_pct': None,  # Need to compute from reports - disabled for now
}

# Stage-specific field mappings
STAGE_FIELDS = {
    'synth': {
        'prefix': 'synth__',
        'fields': {
            'synth_wns_ns': 'synth__timing__setup__wns',
            'synth_tns_ns': 'synth__timing__setup__tns',
        }
    },
    'floorplan': {
        'prefix': 'floorplan_final__',
        'fields': {
            'floorplan_wns_ns': 'floorplan_final__report_wns',
            'floorplan_tns_ns': 'floorplan_final__report_tns',
        }
    },
    'place': {
        'prefix': 'globalplace__',
        'fields': {
            'place_wns_ns': 'globalplace__timing__setup__wns',
            'place_tns_ns': 'globalplace__timing__setup__tns',
            'place_area_um2': 'globalplace__design__core__area',
            'place_power_mw': 'globalplace__power__total',
        }
    },
    'cts': {
        'prefix': 'cts_final__',
        'fields': {
            'cts_wns_ns': 'cts_final__report_wns',
            'cts_tns_ns': 'cts_final__report_tns',
        }
    },
    'route': {
        'prefix': 'globalroute__',
        'fields': {
            'route_wns_ns': 'globalroute__timing__setup__tns',
            'route_tns_ns': 'globalroute__timing__setup__tns',
            'route_wirelength': 'globalroute__global_route__wirelength',
            'route_vias': 'globalroute__global_route__vias',
        }
    },
    'finish': {
        'prefix': 'finish__',
        'fields': TARGET_FIELDS
    }
}

# Design name mapping from directory names
DESIGN_NAME_MAP = {
    'aes-mbff': 'aes',
    'aes-block': 'aes-block',
    'gcd': 'gcd',
}

PLATFORM_MAP = {
    'asap7': 'asap7',
}

def extract_design_platform_from_dir(dir_name: str) -> tuple:
    """Extract design name and platform from directory name."""
    # Pattern: asap7_aes-mbff_PLACE_DENSITY=0.55
    # Pattern: aes-block/asap7_aes-block_PLACE_DENSITY=0.55
    # Pattern: gcd/asap7_gcd_PLACE_DENSITY=0.55

    logger.debug(f"extract_design_platform_from_dir called with: {dir_name} (type: {type(dir_name)})")

    if not dir_name or not isinstance(dir_name, str):
        logger.warning(f"Invalid dir_name: {dir_name} (type: {type(dir_name)})")
        return None, None

    # Extract platform (first part before first _)
    parts = dir_name.split('_')
    if len(parts) >= 2:
        platform = parts[0]
        # Design is everything after platform_ up to the parameter
        rest = '_'.join(parts[1:])
        # Remove parameter suffixes like _PLACE_DENSITY=0.55
        design = re.sub(r'_(PLACE_DENSITY|CORE_UTILIZATION|CORE_ASPECT_RATIO|CORE_MARGIN)=[\d.]+', '', rest)
        logger.debug(f"Extracted: design={design}, platform={platform}")
        return design, platform
    logger.warning(f"Could not parse design/platform from: {dir_name}")
    return None, None

def parse_config_mk(config_path: Path) -> Dict:
    """Parse config.mk for design parameters."""
    config = {}
    if not config_path.exists():
        return config

    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip()
                if key in ['DESIGN_NAME', 'PLATFORM', 'CORE_UTILIZATION', 'CORE_ASPECT_RATIO',
                           'CORE_MARGIN', 'PLACE_DENSITY', 'TARGET_FREQ_MHZ']:
                    try:
                        config[key] = float(val) if '.' in val else int(val)
                    except:
                        config[key] = val
    return config

def extract_from_json(json_path: Path, field_map: Dict[str, str], prefix: str = '') -> Dict:
    """Extract target fields from a JSON file using field mapping.

    The JSON has flat keys with '__' as separators (e.g., 'finish__timing__setup__ws'),
    not nested objects. So we use the source_key directly as the dictionary key.
    """
    if not json_path.exists():
        return {}

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to parse {json_path}: {e}")
        return {}

    result = {}
    for target_key, source_key in field_map.items():
        # The JSON has flat keys with '__' separators, use source_key directly
        try:
            result[target_key] = data[source_key]
        except (KeyError, TypeError):
            result[target_key] = None

    return result

def extract_design_features(config_mk: Dict, design_name: str) -> Dict:
    """Extract design-level features from config and design name."""
    features = {}

    # From config.mk
    features['core_utilization'] = config_mk.get('CORE_UTILIZATION', 0)
    features['core_aspect_ratio'] = config_mk.get('CORE_ASPECT_RATIO', 1.0)
    features['core_margin'] = config_mk.get('CORE_MARGIN', 4.0)
    features['place_density'] = config_mk.get('PLACE_DENSITY', 0.55)
    features['target_freq_mhz'] = config_mk.get('TARGET_FREQ_MHZ', 500)

    # Parse design name for type info
    features['design_name'] = design_name
    features['is_block'] = 'block' in design_name.lower()
    features['is_aes'] = 'aes' in design_name.lower()
    features['is_gcd'] = 'gcd' in design_name.lower()

    return features

def extract_stage_metrics(run_dir: Path) -> Dict[str, Any]:
    """Extract metrics from all stage JSON files in a run directory."""
    metrics = {}

    # Stage JSON files to check
    stage_files = {
        'synth': ['1_synth.json', 'synth.json'],
        'floorplan': ['2_floorplan_final.rpt', '2_1_floorplan.json', '2_2_floorplan_macro.json'],
        'place': ['3_1_place_gp_skip_io.json', '3_2_place_iop.json', '3_3_place_gp.json',
                  '3_4_place_resized.json', '3_5_place_dp.json'],
        'cts': ['4_1_cts.json', '4_cts_final.rpt'],
        'route': ['5_1_grt.json', '5_2_route.json', '5_3_fillcell.json'],
        'finish': ['6_report.json', '6_finish.rpt'],
        'detailedroute': ['5_2_route.json', '5_route_drc.rpt'],
        'globalroute': ['5_1_grt.json'],
        'detailedplace': ['3_5_place_dp.json'],
    }

    for stage, files in stage_files.items():
        for f in files:
            fpath = run_dir / f
            if fpath.exists():
                if f.endswith('.json'):
                    try:
                        with open(fpath, 'r') as f:
                            data = json.load(f)
                        # Add all keys with stage prefix
                        for k, v in data.items():
                            if isinstance(v, (int, float, str, bool)) or v is None:
                                metrics[f'{stage}__{k}'] = v
                    except Exception as e:
                        logger.debug(f"Failed to parse {fpath}: {e}")
                elif f.endswith('.rpt'):
                    # Could parse .rpt files for timing data if needed
                    pass

    return metrics

def extract_training_record(run_dir: Path) -> Optional[Dict]:
    """Extract a complete training record from a run directory."""
    dir_name = str(run_dir.name)
    logger.debug(f"extract_training_record called with run_dir={run_dir}, dir_name={dir_name}")

    design, platform = extract_design_platform_from_dir(dir_name)

    if not design or not platform:
        logger.warning(f"Could not parse design/platform from {dir_name}")
        return None

    # Find config.mk
    config_mk_path = run_dir / 'config.mk'
    config_mk = parse_config_mk(config_mk_path)

    # Parse design name from directory
    # Extract actual design name from config.mk if available
    design_name = config_mk.get('DESIGN_NAME', design)

    # Extract design features
    features = extract_design_features(config_mk, design_name)
    features['platform'] = platform

    # Find 6_report.json (final sign-off)
    report_6_path = run_dir / '6_report.json'
    if not report_6_path.exists():
        # Try alternative locations
        for f in run_dir.glob('**/6_report.json'):
            report_6_path = f
            break

    if not report_6_path.exists():
        logger.warning(f"No 6_report.json found in {run_dir}")
        return None

    # Extract final metrics from 6_report.json
    final_metrics = extract_from_json(report_6_path, TARGET_FIELDS, 'finish__')

    # Add design info
    final_metrics['design_name'] = design_name
    final_metrics['platform'] = platform

    # Add design features
    final_metrics.update(features)

    # Add config parameters
    for k, v in config_mk.items():
        final_metrics[f'config_{k.lower()}'] = v

    # Parse run_id from directory name
    final_metrics['run_id'] = dir_name

    # Add timestamp
    final_metrics['extracted_at'] = datetime.now().isoformat()

    # Determine status
    final_metrics['status'] = 'success' if final_metrics.get('final_wns_ns') is not None else 'failed'

    return final_metrics

def process_batch_directory(batch_root: Path) -> List[Dict]:
    """Process all run directories in a batch directory."""
    records = []

    # Find all directories containing 6_report.json
    for report_path in batch_root.rglob('6_report.json'):
        run_dir = report_path.parent

        # Skip if this is a subdirectory of another run (avoid duplicates)
        # Check if any parent directory (up to batch_root) also has 6_report.json
        is_duplicate = False
        for p in run_dir.parents:
            if p == batch_root:
                break
            if (p / '6_report.json').exists():
                is_duplicate = True
                break

        if is_duplicate:
            continue

        logger.info(f"Processing: {run_dir.relative_to(batch_root)}")
        logger.debug(f"run_dir={run_dir}, run_dir.name={run_dir.name}, type(run_dir.name)={type(run_dir.name)}")

        try:
            record = extract_training_record(run_dir)
            if record:
                records.append(record)
        except Exception as e:
            logger.error(f"Failed to process {run_dir}: {e}")

    return records

def main():
    batch_root = Path('/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report/asap_new_batch')

    print(f"Processing batch: {batch_root}")
    records = process_batch_directory(batch_root)

    print(f"\nExtracted {len(records)} training records")

    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Save to multiple formats
    output_dir = Path('/Users/mihirmithani/Downloads/OpenRoad GUI/AWS_Report/asap_new_batch/extracted')
    output_dir.mkdir(exist_ok=True)

    # Save as JSONL (one record per line)
    jsonl_path = output_dir / 'training_data.jsonl'
    df.to_json(jsonl_path, orient='records', lines=True)
    print(f"Saved JSONL: {jsonl_path}")

    # Save as CSV
    csv_path = output_dir / 'training_data.csv'
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path}")

    # Save as Parquet (efficient for ML)
    parquet_path = output_dir / 'training_data.parquet'
    df.to_parquet(parquet_path, index=False)
    print(f"Saved Parquet: {parquet_path}")

    # Save as Excel for inspection
    excel_path = output_dir / 'training_data.xlsx'
    df.to_excel(excel_path, index=False)
    print(f"Saved Excel: {excel_path}")

    # Print summary
    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total records: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"\nDesigns: {df['design_name'].nunique() if 'design_name' in df.columns else 'N/A'}")
    print(f"Platforms: {df['platform'].nunique() if 'platform' in df.columns else 'N/A'}")

    if 'status' in df.columns:
        print(f"\nStatus distribution:")
        print(df['status'].value_counts())

    if 'final_wns_ns' in df.columns:
        successful = df[df['final_wns_ns'].notna()]
        print(f"\nSuccessful runs: {len(successful)}/{len(df)}")
        if len(successful) > 0:
            print(f"WNS range: {successful['final_wns_ns'].min():.3f} to {successful['final_wns_ns'].max():.3f} ns")
            print(f"TNS range: {successful['final_tns_ns'].min():.3f} to {successful['final_tns_ns'].max():.3f} ns")
            print(f"Area range: {successful['final_area_um2'].min():.0f} to {successful['final_area_um2'].max():.0f} um2")
            print(f"Power range: {successful['final_power_total_w'].min():.6f} to {successful['final_power_total_w'].max():.6f} W")

    # Show column names
    print(f"\nAll columns ({len(df.columns)}):")
    for col in sorted(df.columns):
        print(f"  {col}")

if __name__ == '__main__':
    main()