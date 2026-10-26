"""Historical OpenROAD run data collector for training data."""

from __future__ import annotations

import json
import sqlite3
import re
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class RunRecord:
    """Single OpenROAD flow execution record."""
    run_id: str
    timestamp: datetime
    design_name: str
    platform: str

    # Input configuration
    config_params: Dict[str, Any] = field(default_factory=dict)
    design_features: Dict[str, Any] = field(default_factory=dict)

    # Per-stage results
    stage_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Final PPA
    final_wns_ns: float = 0.0
    final_tns_ns: float = 0.0
    final_area_um2: float = 0.0
    final_power_mw: float = 0.0
    final_drc_violations: int = 0

    # Runtime
    total_runtime_sec: float = 0.0
    stage_runtimes: Dict[str, float] = field(default_factory=dict)

    # Success flags
    timing_closure: bool = False
    drc_clean: bool = False
    lvs_clean: bool = False


class HistoricalDataCollector:
    """Collect and store historical OpenROAD runs for training data."""

    def __init__(self, db_path: str = "data/training_runs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
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
            # Create indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_design ON runs(design_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON runs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_platform ON runs(platform)")

    def insert_run(self, record: RunRecord) -> None:
        """Insert a run record into database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.run_id,
                record.timestamp.isoformat(),
                record.design_name,
                record.platform,
                json.dumps(record.config_params),
                json.dumps(record.design_features),
                json.dumps(record.stage_results),
                record.final_wns_ns,
                record.final_tns_ns,
                record.final_area_um2,
                record.final_power_mw,
                record.final_drc_violations,
                record.total_runtime_sec,
                json.dumps(record.stage_runtimes),
                int(record.timing_closure),
                int(record.drc_clean),
                int(record.lvs_clean)
            ))

    def collect_from_directory(self, results_dir: Path) -> List[RunRecord]:
        """
        Scan OpenROAD results directory and extract training records.

        ORFS standard structure:
        flow/
          designs/<platform>/<design>/config.mk
          reports/<platform>/<design>/base/*.rpt
          logs/<platform>/<design>/base/*.log
          results/<platform>/<design>/base/*.odb, *.gds
        """
        records = []

        if not results_dir.exists():
            print(f"Results directory not found: {results_dir}")
            return records

        # Find ORFS root by looking for flow/designs, flow/reports, flow/logs
        # results_dir = <orfs_root>/flow/results
        orfs_root = results_dir.parent.parent.parent
        designs_root = orfs_root / "flow" / "designs"

        # If not found, try going up one more level (for nested OpenROAD-flow-scripts)
        if not designs_root.exists():
            orfs_root = results_dir.parent.parent.parent.parent
            designs_root = orfs_root / "flow" / "designs"

        reports_root = orfs_root / "flow" / "reports"
        logs_root = orfs_root / "flow" / "logs"

        if not designs_root.exists():
            print(f"Designs directory not found: {designs_root}")
            return records

        for platform_dir in designs_root.iterdir():
            if not platform_dir.is_dir():
                continue
            platform = platform_dir.name
            for design_dir in platform_dir.iterdir():
                if not design_dir.is_dir():
                    continue
                design = design_dir.name

                # Check if results exist for this design
                result_dir = results_dir / platform / design / "base"
                if not result_dir.exists():
                    continue

                # Check if reports exist
                report_dir = reports_root / platform / design / "base"
                if not report_dir.exists():
                    print(f"Reports not found for {platform}/{design}, skipping")
                    continue

                # Check if logs exist
                log_dir = logs_root / platform / design / "base"
                if not log_dir.exists():
                    print(f"Logs not found for {platform}/{design}, skipping")
                    continue

                # Create a single run record for this design
                record = self._parse_orfs_design(
                    design_dir, platform, design, report_dir, log_dir, result_dir
                )
                if record:
                    records.append(record)

        return records

    def _parse_orfs_design(self, design_dir: Path, platform: str, design: str,
                           report_dir: Path, log_dir: Path, result_dir: Path) -> Optional[RunRecord]:
        """Parse a single ORFS design (one run per design)."""
        try:
            import time
            from datetime import datetime

            # Parse config.mk from design directory
            config_path = design_dir / "config.mk"
            config_params = self._parse_config_mk(config_path)

            # Parse design features from netlist (if available)
            design_features = self._extract_design_features(design_dir)

            # Parse stage results from reports
            stage_results = self._parse_stage_reports(report_dir)

            # Parse final PPA from final reports
            final_metrics = self._parse_final_metrics(report_dir)

            # Parse runtimes from logs
            stage_runtimes, total_runtime = self._parse_runtimes(log_dir)

            # Generate run_id from design + timestamp
            run_id = f"{design}_{int(time.time())}"

            return RunRecord(
                run_id=run_id,
                timestamp=datetime.now(),
                design_name=design,
                platform=platform,
                config_params=config_params,
                design_features=design_features,
                stage_results=stage_results,
                **final_metrics,
                total_runtime_sec=total_runtime,
                stage_runtimes=stage_runtimes,
                timing_closure=final_metrics.get("final_wns_ns", 1) >= 0,
                drc_clean=final_metrics.get("final_drc_violations", 1) == 0,
                lvs_clean=final_metrics.get("lvs_clean", 0) == 1
            )
        except Exception as e:
            print(f"Failed to parse {platform}/{design}: {e}")
            return None

    def _parse_stage_reports(self, reports_dir: Path) -> Dict[str, Dict[str, Any]]:
        """Parse stage-specific reports from ORFS reports directory."""
        results = {}
        if not reports_dir.exists():
            return results

        for report_file in reports_dir.glob("*.rpt"):
            stage_name = report_file.stem
            try:
                content = report_file.read_text()
                results[stage_name] = self._parse_report_content(content)
            except Exception:
                pass
        return results

    def _parse_final_metrics(self, reports_dir: Path) -> Dict[str, Any]:
        """Parse final PPA metrics from ORFS finish reports."""
        metrics = {}
        if not reports_dir.exists():
            return metrics

        # Look for finish report (6_finish.rpt or *finish*.rpt)
        finish_reports = list(reports_dir.glob("*finish*.rpt"))
        if not finish_reports:
            finish_reports = list(reports_dir.glob("6_finish.rpt"))
        if not finish_reports:
            finish_reports = list(reports_dir.glob("*6_*.rpt"))

        for report_file in finish_reports:
            try:
                content = report_file.read_text()
                metrics.update(self._parse_report_content(content))
            except Exception:
                pass

        return {
            "final_wns_ns": metrics.get("wns_ns", 0.0),
            "final_tns_ns": metrics.get("tns_ns", 0.0),
            "final_area_um2": metrics.get("area_um2", 0.0),
            "final_power_mw": metrics.get("power_mw", 0.0),
            "final_drc_violations": int(metrics.get("drc_violations", 0)),
        }

    def _parse_runtimes(self, logs_dir: Path) -> tuple:
        """Parse stage runtimes from ORFS logs directory."""
        stage_runtimes = {}
        total_runtime = 0.0

        if not logs_dir.exists():
            return stage_runtimes, total_runtime

        for log_file in logs_dir.glob("*.log"):
            try:
                content = log_file.read_text()
                stage_name = log_file.stem
                import re
                time_patterns = [
                    r"Elapsed.*?(\d+(?:\.\d+)?)\s*s",
                    r"Time:\s*([\d.]+)\s*s",
                    r"Elapsed.*?(\d+):(\d+):(\d+)",
                ]
                for pattern in time_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        try:
                            if ":" in match.group(1):
                                parts = match.group(1).split(":")
                                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                            else:
                                seconds = float(match.group(1))
                            stage_runtimes[stage_name] = seconds
                            total_runtime += seconds
                            break
                        except (ValueError, IndexError):
                            pass
            except Exception:
                pass

        return stage_runtimes, total_runtime

    def _parse_orfs_design(self, design_dir: Path, platform: str, design: str,
                           report_dir: Path, log_dir: Path, result_dir: Path) -> Optional[RunRecord]:
        """Parse a single ORFS design (one run per design)."""
        try:
            import time
            from datetime import datetime

            # Parse config.mk from design directory
            config_path = design_dir / "config.mk"
            config_params = self._parse_config_mk(config_path)

            # Parse design features from netlist (if available)
            design_features = self._extract_design_features(design_dir)

            # Parse stage results from reports
            stage_results = self._parse_stage_reports(report_dir)

            # Parse final PPA from final reports (pass log_dir for JSON report)
            final_metrics = self._parse_final_metrics(report_dir, log_dir)

            # Parse runtimes from logs
            stage_runtimes, total_runtime = self._parse_runtimes(log_dir)

            # Generate run_id from design + timestamp
            run_id = f"{design}_{int(time.time())}"
            timestamp = datetime.now()

            return RunRecord(
                run_id=run_id,
                timestamp=timestamp,
                design_name=design,
                platform=platform,
                config_params=config_params,
                design_features=design_features,
                stage_results=stage_results,
                **final_metrics,
                total_runtime_sec=total_runtime,
                stage_runtimes=stage_runtimes,
                timing_closure=final_metrics.get("final_wns_ns", 1) >= 0,
                drc_clean=final_metrics.get("final_drc_violations", 1) == 0,
                lvs_clean=final_metrics.get("lvs_clean", 0) == 1
            )
        except Exception as e:
            print(f"Failed to parse {platform}/{design}: {e}")
            return None

    def _parse_stage_reports(self, reports_dir: Path) -> Dict[str, Dict[str, Any]]:
        """Parse stage-specific reports from ORFS reports directory."""
        results = {}
        if not reports_dir.exists():
            return results

        for report_file in reports_dir.glob("*.rpt"):
            stage_name = report_file.stem
            try:
                content = report_file.read_text()
                results[stage_name] = self._parse_report_content(content)
            except Exception:
                pass
        return results

    def _parse_final_metrics(self, reports_dir: Path, logs_dir: Path = None) -> Dict[str, Any]:
        """Parse final PPA metrics from ORFS finish reports."""
        metrics = {}
        if not reports_dir.exists():
            return metrics

        # Look for finish report (6_finish.rpt or *finish*.rpt)
        finish_reports = list(reports_dir.glob("*finish*.rpt"))
        if not finish_reports:
            finish_reports = list(reports_dir.glob("6_finish.rpt"))
        if not finish_reports:
            finish_reports = list(reports_dir.glob("*6_*.rpt"))

        for report_file in finish_reports:
            try:
                content = report_file.read_text()
                metrics.update(self._parse_report_content(content))
            except Exception:
                pass

        # Also parse JSON report for comprehensive metrics
        json_path = None
        if logs_dir and (logs_dir / "6_report.json").exists():
            json_path = logs_dir / "6_report.json"
        elif (reports_dir / "6_report.json").exists():
            json_path = reports_dir / "6_report.json"

        if json_path and json_path.exists():
            metrics.update(self._parse_json_report(json_path))

        # Calculate total DRC violations from various violation types
        total_violations = (
            metrics.get("setup_violations", 0) +
            metrics.get("hold_violations", 0) +
            metrics.get("slew_violations", 0) +
            metrics.get("cap_violations", 0) +
            metrics.get("fanout_violations", 0)
        )

        return {
            "final_wns_ns": metrics.get("wns_ns", 0.0),
            "final_tns_ns": metrics.get("tns_ns", 0.0),
            "final_area_um2": metrics.get("area_um2", metrics.get("instance_area_um2", 0.0)),
            "final_power_mw": metrics.get("power_mw", 0.0),
            "final_drc_violations": int(metrics.get("drc_violations", total_violations)),
        }

    def _parse_runtimes(self, logs_dir: Path) -> tuple:
        """Parse stage runtimes from ORFS logs directory."""
        stage_runtimes = {}
        total_runtime = 0.0

        if not logs_dir.exists():
            return stage_runtimes, total_runtime

        for log_file in logs_dir.glob("*.log"):
            try:
                content = log_file.read_text()
                stage_name = log_file.stem
                import re
                time_patterns = [
                    r"Elapsed.*?(\d+(?:\.\d+)?)\s*s",
                    r"Time:\s*([\d.]+)\s*s",
                    r"Elapsed.*?(\d+):(\d+):(\d+)",
                ]
                for pattern in time_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        try:
                            if ":" in match.group(1):
                                parts = match.group(1).split(":")
                                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                            else:
                                seconds = float(match.group(1))
                            stage_runtimes[stage_name] = seconds
                            total_runtime += seconds
                            break
                        except (ValueError, IndexError):
                            pass
            except Exception:
                pass

        return stage_runtimes, total_runtime

    def _parse_config_mk(self, config_path: Path) -> Dict[str, str]:
        """Parse config.mk for input parameters."""
        params = {}
        if not config_path.exists():
            return params

        try:
            content = config_path.read_text()
            # Parse export VAR = value lines
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    _, rest = line.split("export ", 1)
                    key, value = rest.split("=", 1)
                    params[key.strip()] = value.strip()
        except Exception:
            pass
        return params

    def _extract_design_features(self, design_dir: Path) -> Dict[str, Any]:
        """Extract design features from netlist files."""
        features = {}
        # Look for synthesized netlist
        netlist_files = list(design_dir.rglob("*.v")) + list(design_dir.rglob("*.vhd"))
        if netlist_files:
            # Basic stats from first netlist
            netlist = netlist_files[0].read_text()
            features["num_modules"] = len(re.findall(r"^\s*module\s+\w+", netlist, re.MULTILINE))
            features["num_ports"] = len(re.findall(r"\b(input|output|inout)\b", netlist))
        return features

    def _parse_report_content(self, content: str) -> Dict[str, Any]:
        """Parse report content for key metrics."""
        metrics = {}
        import re
        # Extract common metrics from report text (ORFS format)
        patterns = {
            "wns_ns": r"wns\s+max\s+([-\d.]+)",
            "tns_ns": r"tns\s+max\s+([-\d.]+)",
            "area_um2": r"Area\s*:\s*([\d.]+)",
            "power_mw": r"Power\s+([\d.]+)\s+Watts",
            "drc_violations": r"violation\s+count\s+(\d+)",
            "setup_violations": r"setup\s+violation\s+count\s+(\d+)",
            "hold_violations": r"hold\s+violation\s+count\s+(\d+)",
            "slew_violations": r"slew\s+violation\s+count\s+(\d+)",
            "fanout_violations": r"fanout\s+violation\s+count\s+(\d+)",
            "cap_violations": r"cap\s+violation\s+count\s+(\d+)",
            "congestion": r"congestion\s*:\s*(\d+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    val = match.group(1)
                    metrics[key] = float(val) if "." in val else int(val)
                except ValueError:
                    pass
        return metrics

    def _parse_json_report(self, json_path: Path) -> Dict[str, Any]:
        """Parse ORFS 6_report.json for final metrics."""
        import json
        metrics = {}
        if not json_path.exists():
            return metrics
        try:
            data = json.loads(json_path.read_text())
            # Map JSON keys to our metric names
            mapping = {
                "finish__design__instance__area": "area_um2",
                "finish__power__total": "power_w",
                "finish__timing__drv__setup_violation_count": "setup_violations",
                "finish__timing__drv__hold_violation_count": "hold_violations",
                "finish__timing__drv__max_slew": "slew_violations",
                "finish__timing__drv__max_cap": "cap_violations",
                "finish__timing__drv__max_fanout": "fanout_violations",
                "finish__design__die__area": "die_area_um2",
                "finish__design__core__area": "core_area_um2",
                "finish__design__instance__area": "instance_area_um2",
                "finish__design__instance__utilization": "utilization",
                "finish__design__instance__count": "instance_count",
            }
            for json_key, metric_key in mapping.items():
                if json_key in data:
                    val = data[json_key]
                    if metric_key == "power_w":
                        metrics["power_mw"] = val * 1000  # Convert W to mW
                    elif metric_key in ("area_um2", "die_area_um2", "core_area_um2",
                       "instance_area_um2"):
                        metrics[metric_key] = float(val)
                    elif metric_key == "utilization":
                        metrics[metric_key] = float(val)
                    else:
                        metrics[metric_key] = int(val) if isinstance(val, (int, float)) and val == int(val) else float(val)
        except Exception:
            pass
        return metrics


def main():
    """CLI entry point for data collector."""
    import argparse
    parser = argparse.ArgumentParser(description="Collect historical OpenROAD run data")
    parser.add_argument("--results-dir", type=str, required=True, help="Path to ORFS results directory")
    parser.add_argument("--output", type=str, required=True, help="Output SQLite database path")
    args = parser.parse_args()

    collector = HistoricalDataCollector(args.output)
    records = collector.collect_from_directory(Path(args.results_dir))

    for record in records:
        collector.insert_run(record)

    print(f"Collected {len(records)} runs into {args.output}")


if __name__ == "__main__":
    main()

# Type imports
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import sqlite3
import re
from pathlib import Path