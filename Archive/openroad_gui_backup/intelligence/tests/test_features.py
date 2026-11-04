"""Tests for feature engineering."""
import pytest
import polars as pl
import tempfile
from pathlib import Path
from openroad_gui.intelligence.data.features import (
    extract_features_streaming,
    validate_features,
    _parse_json,
)


class TestFeatureEngineering:
    def test_parse_json(self):
        assert _parse_json('{"a": 1}') == {"a": 1}
        assert _parse_json('invalid') == {}
        assert _parse_json('') == {}
        assert _parse_json(None) == {}

    def test_extract_features_streaming(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create test database
            import sqlite3
            import json
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE runs (
                        run_id TEXT PRIMARY KEY,
                        timestamp TEXT,
                        design_name TEXT,
                        platform TEXT,
                        config_params TEXT,
                        design_features TEXT,
                        stage_results TEXT,
                        final_wns_ns REAL,
                        final_tns_ns REAL,
                        final_area_um2 REAL,
                        final_power_mw REAL,
                        final_drc_violations INTEGER,
                        total_runtime_sec REAL,
                        stage_runtimes TEXT,
                        timing_closure INTEGER,
                        drc_clean INTEGER,
                        lvs_clean INTEGER
                    )
                """)

                # Insert test record
                conn.execute("""
                    INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "run_001",
                    "2024-01-01T00:00:00",
                    "test_design",
                    "asap7",
                    json.dumps({"CORE_UTILIZATION": "30", "PLATFORM": "asap7"}),
                    json.dumps({"num_instances": 1000, "num_nets": 5000, "num_sequential": 500}),
                    json.dumps({}),
                    -0.5, -100.0, 100000.0, 50.0, 0,
                    300.0, json.dumps({}), 0, 1, 1
                ))

            output_path = Path(tmpdir) / "features.parquet"
            extract_features_streaming(str(db_path), str(output_path))

            # Verify output
            assert Path(output_path).exists()
            df = pl.read_parquet(output_path)
            assert df.height == 1
            assert "log_instances" in df.columns
            assert "wns_normalized" in df.columns
            assert "timing_closure_bin" in df.columns

    def test_validate_features(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test parquet with more columns to test validation logic
            df = pl.DataFrame({
                "run_id": ["run_001", "run_002"],
                "final_wns_ns": [-0.5, 0.2],
                "final_area_um2": [100000.0, 200000.0],
                "final_power_mw": [50.0, 60.0],
                "final_tns_ns": [-10.0, -5.0],
                "num_instances": [1000, 2000],
                "num_nets": [5000, 10000],
                "timing_closure_bin": [0, 1],
                "drc_clean_bin": [1, 1],
                "lvs_clean_bin": [1, 1],
                "platform": ["asap7", "sky130hd"],
                "design_name": ["design1", "design2"],
            })
            parquet_path = Path(tmpdir) / "features.parquet"
            df.write_parquet(parquet_path)

            report = validate_features(str(parquet_path))
            assert report["num_rows"] == 2
            assert report["num_cols"] > 10
            assert "quality_score" in report