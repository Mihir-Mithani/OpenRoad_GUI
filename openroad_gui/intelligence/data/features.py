"""Feature engineering for OpenROAD flow data using Polars with sqlite3 (no connectorx dependency)."""

from __future__ import annotations

import polars as pl
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional


def extract_features_streaming(db_path: str, output_path: str, batch_size: int = 1000) -> None:
    """
    Extract features from training runs database using Polars with sqlite3.

    Uses sqlite3 directly to avoid connectorx dependency.

    Args:
        db_path: Path to SQLite database with training runs
        output_path: Output Parquet file path
        batch_size: Number of rows to process at once (unused, kept for API compatibility)
    """
    # Connect to SQLite and read data directly using sqlite3 + Polars
    conn = sqlite3.connect(db_path)

    # Read all data from runs table
    df = pl.read_database("SELECT * FROM runs", connection=conn)
    conn.close()

    # Extract features from JSON columns
    df = _extract_features(df)

    # Write to Parquet (columnar, compressed)
    df.write_parquet(output_path)
    print(f"Features written to {output_path}: {df.height} rows, {df.width} columns")


def _extract_features(df: pl.DataFrame) -> pl.DataFrame:
    """Extract numerical features from raw run data."""

    # Parse JSON columns using map_elements with dict return type
    df = df.with_columns([
        # Parse config_params JSON
        pl.col("config_params").map_elements(_parse_json, return_dtype=pl.Object).alias("config"),
        pl.col("design_features").map_elements(_parse_json, return_dtype=pl.Object).alias("design"),
        pl.col("stage_results").map_elements(_parse_json, return_dtype=pl.Object).alias("stages"),
    ])

    # Extract design features using map_elements to safely access dict fields with defaults
    def _extract_design_fields(design_dict):
        if not isinstance(design_dict, dict):
            return {}
        return {
            "num_instances": design_dict.get("num_instances", 0),
            "num_nets": design_dict.get("num_nets", 0),
            "num_sequential": design_dict.get("num_sequential", 0),
            "num_macros": design_dict.get("num_macros", 0),
            "macro_area_ratio": design_dict.get("macro_area_ratio", 0.0),
        }

    def _extract_config_fields(config_dict):
        if not isinstance(config_dict, dict):
            return {}
        return {
            "DESIGN_NAME": config_dict.get("DESIGN_NAME", ""),
            "PLATFORM": config_dict.get("PLATFORM", ""),
            "CORE_UTILIZATION": float(config_dict.get("CORE_UTILIZATION", 0)),
            "CORE_ASPECT_RATIO": float(config_dict.get("CORE_ASPECT_RATIO", 1.0)),
            "CORE_MARGIN": float(config_dict.get("CORE_MARGIN", 0)),
        }

    df = df.with_columns([
        pl.col("design").map_elements(_extract_design_fields, return_dtype=pl.Struct({
            "num_instances": pl.Int64,
            "num_nets": pl.Int64,
            "num_sequential": pl.Int64,
            "num_macros": pl.Int64,
            "macro_area_ratio": pl.Float64,
        })).alias("design_extracted"),
        pl.col("config").map_elements(_extract_config_fields, return_dtype=pl.Struct({
            "DESIGN_NAME": pl.String,
            "PLATFORM": pl.String,
            "CORE_UTILIZATION": pl.Float64,
            "CORE_ASPECT_RATIO": pl.Float64,
            "CORE_MARGIN": pl.Float64,
        })).alias("config_extracted"),
    ])

    # Extract design features
    features = df.select([
        pl.col("run_id"),
        pl.col("design_name"),
        pl.col("platform"),
        pl.col("timestamp"),

        # Design features from JSON (now guaranteed to exist)
        pl.col("design_extracted").struct.field("num_instances").alias("num_instances"),
        pl.col("design_extracted").struct.field("num_nets").alias("num_nets"),
        pl.col("design_extracted").struct.field("num_sequential").alias("num_sequential"),
        pl.col("design_extracted").struct.field("num_macros").alias("num_macros"),
        pl.col("design_extracted").struct.field("macro_area_ratio").alias("macro_area_ratio"),

        # Config parameters
        pl.col("config_extracted").struct.field("DESIGN_NAME").alias("design_name_config"),
        pl.col("config_extracted").struct.field("PLATFORM").alias("platform_config"),
        pl.col("config_extracted").struct.field("CORE_UTILIZATION").alias("core_utilization"),
        pl.col("config_extracted").struct.field("CORE_ASPECT_RATIO").alias("core_aspect_ratio"),
        pl.col("config_extracted").struct.field("CORE_MARGIN").alias("core_margin"),

        # Final PPA metrics
        pl.col("final_wns_ns").fill_null(0.0).cast(pl.Float64).alias("final_wns_ns"),
        pl.col("final_tns_ns").fill_null(0.0).cast(pl.Float64).alias("final_tns_ns"),
        pl.col("final_area_um2").fill_null(0.0).cast(pl.Float64).alias("final_area_um2"),
        pl.col("final_power_mw").fill_null(0.0).cast(pl.Float64).alias("final_power_mw"),
        pl.col("final_drc_violations").fill_null(0).cast(pl.Int64).alias("final_drc_violations"),

        # Runtime
        pl.col("total_runtime_sec").fill_null(0.0).cast(pl.Float64).alias("total_runtime_sec"),

        # Success flags
        pl.col("timing_closure").fill_null(False).alias("timing_closure"),
        pl.col("drc_clean").fill_null(False).alias("drc_clean"),
        pl.col("lvs_clean").fill_null(False).alias("lvs_clean"),
    ])

    # Derived features
    features = features.with_columns([
        # Log-transformed features (better for ML)
        (pl.col("num_instances").log1p() / 20.0).clip(0, 1).alias("log_instances"),
        (pl.col("num_nets").log1p() / 20.0).alias("log_nets"),

        # Ratios
        (pl.col("num_sequential") / pl.max_horizontal(pl.col("num_instances"), pl.lit(1))).alias("seq_ratio"),
        (pl.col("num_macros") / pl.max_horizontal(pl.col("num_instances"), pl.lit(1))).alias("macro_ratio"),

        # Normalized PPA targets
        (pl.col("final_wns_ns") / 10.0).clip(-1, 1).alias("wns_normalized"),
        (pl.col("final_tns_ns") / 1000.0).clip(-1, 1).alias("tns_normalized"),
        (pl.col("final_area_um2").log1p() / 20.0).alias("log_area"),
        (pl.col("final_power_mw").log1p() / 20.0).alias("log_power"),

        # Binary success flags
        pl.col("timing_closure").cast(pl.Int8).alias("timing_closure_bin"),
        pl.col("drc_clean").cast(pl.Int8).alias("drc_clean_bin"),
        pl.col("lvs_clean").cast(pl.Int8).alias("lvs_clean_bin"),

        # Platform encoding
        pl.col("platform").cast(pl.Categorical).alias("platform_cat"),
    ])

    return features


def _parse_json(json_str: str) -> dict:
    """Safely parse JSON string."""
    if not json_str or json_str.strip() == "":
        return {}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def extract_stage_features(db_path: str, output_path: str) -> None:
    """
    Extract per-stage features from stage_results JSON.

    Creates a long-format DataFrame with one row per stage per run.
    """
    query = "SELECT run_id, design_name, platform, stage_results, timestamp FROM runs"
    conn = sqlite3.connect(db_path)
    df = pl.read_database(query, connection=conn)
    conn.close()

    # Parse stage results
    df = df.with_columns([
        pl.col("stage_results").map_elements(_parse_json, return_dtype=pl.Struct).alias("stages"),
    ])

    # Explode stages into rows
    stage_data = []
    for row in df.iter_rows(named=True):
        run_id = row["run_id"]
        stages = row["stages"] or {}
        for stage_name, stage_data in (stages or {}).items():
            if isinstance(stage_data, dict):
                stage_data["run_id"] = row["run_id"]
                stage_data["stage_name"] = stage_name
                stage_data["platform"] = row["platform"]
                stage_data["design_name"] = row["design_name"]
                stage_data["timestamp"] = row["timestamp"]
                stage_data.append(stage_data)

    # This would be expanded to collect all stages
    # For now, placeholder
    pass


def validate_features(parquet_path: str) -> Dict[str, any]:
    """Validate feature matrix quality."""
    df = pl.read_parquet(parquet_path)

    report = {
        "num_rows": df.height,
        "num_cols": df.width,
        "missing_values": df.null_count().to_dict(),
        "dtypes": {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)},
        "numeric_stats": {},
    }

    # Statistics for numeric columns
    for col in df.select(pl.selectors.numeric()).columns:
        stats = df.select([
            pl.col(col).mean().alias("mean"),
            pl.col(col).std().alias("std"),
            pl.col(col).min().alias("min"),
            pl.col(col).max().alias("max"),
            pl.col(col).null_count().alias("nulls"),
        ]).to_dict(as_series=False)
        report["numeric_stats"][col] = {k: v[0] for k, v in stats.items()}

    # Check for data quality issues
    issues = []
    if df.height == 0:
        issues.append("Empty dataset")

    null_counts = df.null_count()
    # null_counts is a DataFrame with one row, iterate over columns
    for col in null_counts.columns:
        count = null_counts[col][0]
        if count > df.height * 0.5:
            issues.append(f"Column {col} has >50% missing values")

    report["issues"] = issues
    report["quality_score"] = max(0, 100 - len(issues) * 10)

    return report


def main():
    """CLI entry point for feature extraction."""
    import argparse
    parser = argparse.ArgumentParser(description="Extract features from training runs database")
    parser.add_argument("--input", type=str, required=True, help="Input SQLite database path")
    parser.add_argument("--output", type=str, required=True, help="Output Parquet file path")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for streaming")
    args = parser.parse_args()

    extract_features_streaming(args.input, args.output, args.batch_size)
    print(f"Features extracted to {args.output}")


if __name__ == "__main__":
    main()