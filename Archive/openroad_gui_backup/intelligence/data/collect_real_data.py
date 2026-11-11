#!/usr/bin/env python3
"""
Real ORFS Data Collector
Fetches actual PPA metrics from completed ORFS runs and exports for dataset generation.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class RealRunRecord:
    """Single real ORFS run record with all metrics."""
    # Identity
    run_id: str
    timestamp: str
    design_name: str
    platform: str

    # Design features (from config.mk + verilog)
    core_utilization: float
    core_aspect_ratio: float
    core_margin: float
    num_instances: int
    num_nets: int
    num_sequential: int
    num_macros: int
    macro_area_ratio: float

    # Per-stage metrics
    stage_metrics: Dict[str, Dict[str, Any]]

    # Final PPA
    final_wns_ns: float
    final_tns_ns: float
    final_area_um2: float
    final_power_mw: float
    final_drc_violations: int
    final_congestion_pct: float
    final_setup_violations: int
    final_hold_violations: int

    # Runtime
    stage_runtimes: Dict[str, float]
    total_runtime_sec: float

    # Success flags
    timing_closure: bool
    drc_clean: bool
    lvs_clean: bool


class RealDataCollector:
    """Collect real metrics from completed ORFS runs."""

    def __init__(self, orfs_root: str | Path):
        self.orfs_root = Path(orfs_root).expanduser()
        self.flow_dir = self.orfs_root / "flow"
        self.designs_dir = self.flow_dir / "designs"
        self.reports_dir = self.flow_dir / "reports"
        self.logs_dir = self.flow_dir / "logs"
        self.results_dir = self.flow_dir / "results"

    def collect_all(self, platform: str = "asap7") -> List[RealRunRecord]:
        """Collect all completed runs for a platform."""
        records = []

        platform_designs_dir = self.designs_dir / platform
        if not platform_designs_dir.exists():
            print(f"Designs dir not found: {platform_designs_dir}")
            return records

        for design_dir in platform_designs_dir.iterdir():
            if not design_dir.is_dir():
                continue

            design = design_dir.name
            record = self._collect_design(platform, design)
            if record:
                records.append(record)

        return records

    def _collect_design(self, platform: str, design: str) -> Optional[RealRunRecord]:
        """Collect metrics for a single completed design run."""
        try:
            design_dir = self.designs_dir / platform / design

            # Check if results exist (indicates completed run)
            result_dir = self.results_dir / platform / design / "base"
            if not result_dir.exists():
                return None

            # Check for final GDS (indicates full flow completion)
            gds_files = list(result_dir.glob("*.gds"))
            if not gds_files:
                return None

            print(f"  Collecting: {platform}/{design}")

            # Parse config.mk for design parameters
            config_path = design_dir / "config.mk"
            config_params = self._parse_config_mk(config_path)

            # Parse design features from verilog
            design_features = self._extract_design_features(design_dir)

            # Parse stage reports
            stage_metrics = self._parse_stage_reports(platform, design)

            # Parse final metrics
            final_metrics = self._parse_final_metrics(platform, design)

            # Parse runtimes from logs
            stage_runtimes, total_runtime = self._parse_runtimes(platform, design)

            # Build record
            run_id = f"{design}_{platform}_{int(time.time())}"

            return RealRunRecord(
                run_id=run_id,
                timestamp=datetime.now().isoformat(),
                design_name=design,
                platform=platform,
                core_utilization=config_params.get('CORE_UTILIZATION', 30.0),
                core_aspect_ratio=config_params.get('CORE_ASPECT_RATIO', 1.0),
                core_margin=config_params.get('CORE_MARGIN', 5.0),
                num_instances=design_features.get('num_instances', 1000),
                num_nets=design_features.get('num_nets', 1200),
                num_sequential=design_features.get('num_sequential', 200),
                num_macros=design_features.get('num_macros', 0),
                macro_area_ratio=design_features.get('macro_area_ratio', 0.0),
                stage_metrics=stage_metrics,
                final_wns_ns=final_metrics.get('wns_ns', 0.0),
                final_tns_ns=final_metrics.get('tns_ns', 0.0),
                final_area_um2=final_metrics.get('area_um2', 0.0),
                final_power_mw=final_metrics.get('power_mw', 0.0),
                final_drc_violations=final_metrics.get('drc_violations', 0),
                final_congestion_pct=final_metrics.get('congestion_pct', 0.0),
                final_setup_violations=final_metrics.get('setup_violations', 0),
                final_hold_violations=final_metrics.get('hold_violations', 0),
                stage_runtimes=stage_runtimes,
                total_runtime_sec=total_runtime,
                timing_closure=final_metrics.get('wns_ns', 1.0) >= 0,
                drc_clean=final_metrics.get('drc_violations', 1) == 0,
                lvs_clean=final_metrics.get('lvs_clean', 0) == 1,
            )
        except Exception as e:
            print(f"    Error collecting {platform}/{design}: {e}")
            return None

    def _parse_config_mk(self, config_path: Path) -> Dict[str, float]:
        """Parse config.mk for design parameters."""
        params = {}
        if not config_path.exists():
            return params

        content = config_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                _, rest = line.split("export ", 1)
                key, value = rest.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Try to convert to float
                try:
                    params[key] = float(value)
                except ValueError:
                    params[key] = value
        return params

    def _extract_design_features(self, design_dir: Path) -> Dict[str, Any]:
        """Extract features from verilog files."""
        features = {}
        verilog_files = list(design_dir.glob("*.v"))
        if not verilog_files:
            return features

        content = verilog_files[0].read_text()

        # Count modules, instances, etc.
        features['num_modules'] = len(re.findall(r"^\s*module\s+\w+", content, re.MULTILINE))
        features['num_ports'] = len(re.findall(r"\b(input|output|inout)\b", content))

        # Estimate instances from module complexity
        # Rough heuristic: more complex modules = more instances
        always_blocks = len(re.findall(r"\balways\b", content))
        assign_stmts = len(re.findall(r"\bassign\b", content))
        features['num_instances'] = max(100, (always_blocks * 50 + assign_stmts * 10))
        features['num_nets'] = int(features['num_instances'] * 1.2)

        # Sequential logic estimate
        features['num_sequential'] = int(features['num_instances'] * 0.15)
        features['num_macros'] = 0
        features['macro_area_ratio'] = 0.0

        return features

    def _parse_stage_reports(self, platform: str, design: str) -> Dict[str, Dict[str, Any]]:
        """Parse all stage reports for a design."""
        stage_metrics = {}
        reports_path = self.reports_dir / platform / design / "base"

        if not reports_path.exists():
            return stage_metrics

        for report_file in reports_path.glob("*.rpt"):
            stage_name = report_file.stem
            try:
                content = report_file.read_text()
                stage_metrics[stage_name] = self._parse_report_content(content)
            except Exception:
                pass

        return stage_metrics

    def _parse_final_metrics(self, platform: str, design: str) -> Dict[str, Any]:
        """Parse final PPA metrics from finish reports."""
        metrics = {}
        reports_path = self.reports_dir / platform / design / "base"

        if not reports_path.exists():
            return metrics

        # Priority: 6_report.json > 6_finish.rpt > *finish*.rpt > *6_*.rpt
        json_file = reports_path / "6_report.json"
        if json_file.exists():
            metrics.update(self._parse_json_report(json_file))

        finish_reports = list(reports_path.glob("*finish*.rpt"))
        if not finish_reports:
            finish_reports = list(reports_path.glob("6_finish.rpt"))
        if not finish_reports:
            finish_reports = list(reports_path.glob("*6_*.rpt"))

        for report_file in finish_reports:
            try:
                content = report_file.read_text()
                metrics.update(self._parse_report_content(content))
            except Exception:
                pass

        # Calculate total DRC from violation types
        total_violations = (
            metrics.get('setup_violations', 0) +
            metrics.get('hold_violations', 0) +
            metrics.get('slew_violations', 0) +
            metrics.get('cap_violations', 0) +
            metrics.get('fanout_violations', 0)
        )
        if total_violations > 0:
            metrics['drc_violations'] = total_violations

        return metrics

    def _parse_json_report(self, json_path: Path) -> Dict[str, Any]:
        """Parse ORFS 6_report.json."""
        metrics = {}
        try:
            data = json.loads(json_path.read_text())
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
                "finish__design__instance__count": "instance_count",
            }
            for json_key, metric_key in mapping.items():
                if json_key in data:
                    val = data[json_key]
                    if metric_key == "power_w":
                        metrics["power_mw"] = val * 1000
                    else:
                        metrics[metric_key] = float(val) if isinstance(val, float) else int(val)
        except Exception:
            pass
        return metrics

    def _parse_report_content(self, content: str) -> Dict[str, Any]:
        """Parse report text for key metrics."""
        metrics = {}
        patterns = {
            "wns_ns": r"wns\s+max\s+([-\d.]+)",
            "tns_ns": r"tns\s+max\s+([-\d.]+)",
            "area_um2": r"Area\s*:\s*([\d.]+)",
            "power_mw": r"Power\s+([\d.]+)\s+Watts",
            "drc_violations": r"violation\s+count\s+(\d+)",
            "setup_violations": r"setup\s+violation\s+count\s+(\d+)",
            "hold_violations": r"hold\s+violation\s+count\s+(\d+)",
            "slew_violations": r"slew\s+violation\s+count\s+(\d+)",
            "cap_violations": r"cap\s+violation\s+count\s+(\d+)",
            "fanout_violations": r"fanout\s+violation\s+count\s+(\d+)",
            "congestion_pct": r"congestion\s*:\s*(\d+)",
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

    def _parse_runtimes(self, platform: str, design: str) -> tuple:
        """Parse stage runtimes from logs."""
        stage_runtimes = {}
        total_runtime = 0.0

        logs_path = self.logs_dir / platform / design / "base"
        if not logs_path.exists():
            return stage_runtimes, total_runtime

        for log_file in logs_path.glob("*.log"):
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
                            total_runtime += seconds
                            break
                        except (ValueError, IndexError):
                            pass
            except Exception:
                pass

        return stage_runtimes, total_runtime


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Collect real ORFS run data")
    parser.add_argument("--orfs-root", type=str, required=True, help="ORFS root directory")
    parser.add_argument("--platform", type=str, default="asap7", help="Platform/PDK")
    parser.add_argument("--output", type=str, required=True, help="Output JSON file")
    parser.add_argument("--include-failed", action="store_true", help="Include failed runs")

    args = parser.parse_args()

    collector = RealDataCollector(args.orfs_root)
    records = collector.collect_all(args.platform)

    # Convert to dict for JSON
    output_data = [asdict(r) for r in records]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_data, indent=2))

    print(f"\n✅ Collected {len(records)} real runs")
    print(f"   Saved to: {output_path}")

    # Print summary
    if records:
        print("\nSummary:")
        for r in records[:10]:
            print(f"  {r.design_name}: WNS={r.final_wns_ns:.2f}, TNS={r.final_tns_ns:.2f}, "
                  f"Area={r.final_area_um2:.0f}, Power={r.final_power_mw:.1f}, DRC={r.final_drc_violations}")


if __name__ == "__main__":
    main()