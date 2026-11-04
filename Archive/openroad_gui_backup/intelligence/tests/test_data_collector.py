"""Tests for data collector."""
import pytest
import tempfile
import sqlite3
from pathlib import Path
from openroad_gui.intelligence.data.collector import HistoricalDataCollector, RunRecord


class TestHistoricalDataCollector:
    def test_init_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            collector = HistoricalDataCollector(str(db_path))

            # Check tables exist
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                assert "runs" in tables

    def test_insert_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            collector = HistoricalDataCollector(str(db_path))

            from datetime import datetime
            record = RunRecord(
                run_id="test_001",
                timestamp=datetime.now(),
                design_name="test_design",
                platform="asap7",
                final_wns_ns=-0.5,
                final_tns_ns=-10.0,
                final_area_um2=100000.0,
                final_power_mw=50.0,
                final_drc_violations=0,
                total_runtime_sec=300.0,
                timing_closure=False,
                drc_clean=True,
                lvs_clean=True,
            )

            collector.insert_run(record)

            # Verify insert
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT * FROM runs WHERE run_id=?", ("test_001",))
                row = cursor.fetchone()
                assert row is not None
                assert row[2] == "test_design"  # design_name
                assert row[3] == "asap7"  # platform (default)

    def test_parse_config_mk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            collector = HistoricalDataCollector(str(db_path))

            config_path = Path(tmpdir) / "config.mk"
            config_path.write_text("""export DESIGN_NAME = test_design
export PLATFORM = asap7
export CORE_UTILIZATION = 30
export CORE_MARGIN = 5
""")

            params = collector._parse_config_mk(config_path)
            assert params["DESIGN_NAME"] == "test_design"
            assert params["PLATFORM"] == "asap7"
            assert params["CORE_UTILIZATION"] == "30"
            assert params["CORE_MARGIN"] == "5"