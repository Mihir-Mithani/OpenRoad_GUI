"""Log and report parsing utilities for OpenROAD flow."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ParsedMetrics:
    """Parsed metrics from reports/logs."""
    wns_ns: float = 0.0
    tns_ns: float = 0.0
    area_um2: float = 0.0
    power_mw: float = 0.0
    drc_violations: int = 0
    congestion_pct: float = 0.0
    max_congestion: float = 0.0
    wirelength: float = 0.0
    via_count: int = 0


def parse_openroad_logs(log_dir: str) -> Dict[str, Any]:
    """
    Parse OpenROAD log directory for metrics.

    Args:
        log_dir: Path to logs directory

    Returns:
        Dictionary with parsed metrics
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return {}

    metrics = {}

    for log_file in log_path.rglob("*.log"):
        try:
            content = log_file.read_text()
            metrics.update(_parse_log_content(content))
        except Exception:
            pass

    return metrics


def _parse_log_content(content: str) -> Dict[str, Any]:
    """Parse a single log file for metrics."""
    metrics = {}

    patterns = {
        "wns_ns": [r"WNS\s*:\s*([-\d.]+)", r"Worst Negative Slack\s*:\s*([-\d.]+)"],
        "tns_ns": [r"TNS\s*:\s*([-\d.]+)", r"Total Negative Slack\s*:\s*([-\d.]+)"],
        "area_um2": [r"Area\s*:\s*([\d.]+)", r"Total area\s*:\s*([\d.]+)"],
        "power_mw": [r"Power\s*:\s*([\d.]+)", r"Total power\s*:\s*([\d.]+)"],
        "drc_violations": [r"DRC.*?(\d+)\s*violations?", r"(\d+)\s*DRC violations?"],
        "congestion_pct": [r"Congestion.*?(\d+(?:\.\d+)?)\s*%", r"Congestion:\s*([\d.]+)%"],
        "max_congestion": [r"Max congestion.*?(\d+(?:\.\d+)?)\s*%"],
    }

    for key, pattern_list in {
        "wns_ns": [r"WNS\s*:\s*([-\d.]+)", r"Worst Negative Slack\s*:\s*([-\d.]+)"],
        "tns_ns": [r"TNS\s*:\s*([-\d.]+)", r"Total Negative Slack\s*:\s*([-\d.]+)"],
        "area_um2": [r"Area\s*:\s*([\d.]+)", r"Total area\s*:\s*([\d.]+)"],
        "power_mw": [r"Power\s*:\s*([\d.]+)", r"Total power\s*:\s*([\d.]+)"],
        "drc_violations": [r"DRC.*?(\d+)\s*violations?", r"(\d+)\s*DRC violations?"],
        "congestion_pct": [r"Congestion.*?(\d+(?:\.\d+)?)\s*%", r"Congestion:\s*([\d.]+)%"],
        "max_congestion": [r"Max congestion.*?(\d+(?:\.\d+)?)\s*%"],
    }.items():
        for pattern in pattern_list:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    val = match.group(1)
                    metrics[key] = float(val) if "." in val else int(val)
                    break
                except (ValueError, IndexError):
                    pass

    return metrics


def parse_yosys_log(log_path: Path) -> Dict[str, Any]:
    """Parse Yosys synthesis log."""
    if not log_path.exists():
        return {}

    content = log_path.read_text()
    metrics = {}

    for key, pattern in [
        ("num_cells", r"Number of cells:\s+(\d+)"),
        ("num_wires", r"Number of wires:\s+(\d+)"),
        ("num_wire_bits", r"Number of wire bits:\s+(\d+)"),
    ]:
        match = re.search(pattern, content)
        if match:
            metrics[key] = int(match.group(1))

    return metrics


def parse_nextpnr_log(log_path: Path) -> Dict[str, Any]:
    """Parse nextpnr log for PnR metrics."""
    if not log_path.exists():
        return {}

    content = log_path.read_text()
    metrics = {}

    for key, pattern in [
        ("max_freq_mhz", r"Max frequency:\s*([\d.]+)\s*MHz"),
        ("wirelength", r"Wirelength:\s*([\d.]+)"),
        ("placed_cells", r"Placed cells:\s*(\d+)"),
        ("routed_wires", r"Routed wires:\s*(\d+)"),
    ]:
        match = re.search(pattern, content)
        if match:
            try:
                val = match.group(1)
                metrics[key] = float(val) if "." in val else int(val)
            except ValueError:
                pass

    return metrics


def parse_reports_directory(reports_dir: str) -> Dict[str, Any]:
    """
    Parse reports directory for final PPA metrics.

    Args:
        reports_dir: Path to reports directory

    Returns:
        Dictionary with final PPA metrics
    """
    reports_path = Path(reports_dir)
    if not reports_path.exists():
        return {}

    metrics = {}

    # Look for common report files
    report_files = list(reports_path.rglob("*.rpt")) + list(reports_path.rglob("*.rpt.gz"))

    for report_file in report_files:
        try:
            content = report_file.read_text()
            metrics.update(_parse_report_content(content))
        except Exception:
            pass

    return metrics


def _parse_report_content(content: str) -> Dict[str, Any]:
    """Parse a single report file for metrics."""
    metrics = {}

    patterns = {
        "wns_ns": r"WNS\s*:\s*([-\d.]+)",
        "tns_ns": r"TNS\s*:\s*([-\d.]+)",
        "area_um2": r"Area\s*:\s*([\d.]+)",
        "power_mw": r"Power\s*:\s*([\d.]+)",
        "drc_violations": r"DRC.*?(\d+)\s*violations?",
        "congestion_pct": r"Congestion.*?(\d+(?:\.\d+)?)\s*%",
        "max_congestion": r"Max congestion.*?(\d+(?:\.\d+)?)\s*%",
        "wirelength": r"Wirelength\s*:\s*([\d.]+)",
        "via_count": r"Via count\s*:\s*(\d+)",
    }

    for key, pattern in {
        "wns_ns": r"WNS\s*:\s*([-\d.]+)",
        "tns_ns": r"TNS\s*:\s*([-\d.]+)",
        "area_um2": r"Area\s*:\s*([\d.]+)",
        "power_mw": r"Power\s*:\s*([\d.]+)",
        "drc_violations": r"DRC.*?(\d+)\s*violations?",
        "congestion_pct": r"Congestion.*?(\d+(?:\.\d+)?)\s*%",
        "max_congestion": r"Max congestion.*?(\d+(?:\.\d+)?)\s*%",
    }.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                val = match.group(1)
                metrics[key] = float(val) if "." in val else int(val)
            except (ValueError, IndexError):
                pass

    return metrics


def extract_runtime_from_logs(log_dir: str) -> Dict[str, float]:
    """Extract stage runtimes from logs."""
    log_path = Path(log_dir)
    if not log_path.exists():
        return {}

    runtimes = {}

    for log_file in log_path.rglob("*.log"):
        try:
            content = log_file.read_text()
            # Look for time patterns
            stage_name = log_file.stem

            # Try to extract elapsed time
            time_patterns = [
                r"Elapsed.*?(\d+(?:\.\d+)?)\s*s",
                r"Elapsed.*?(\d+(?:\.\d+)?)\s*s",
                r"Time:\s*([\d.]+)\s*s",
                r"Elapsed.*?(\d+):(\d+):(\d+)",
            ]

            for pattern in [
                r"Elapsed.*?(\d+(?:\.\d+)?)\s*s",
                r"Time:\s*([\d.]+)\s*s",
                r"Elapsed.*?(\d+):(\d+):(\d+)",
            ]:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    try:
                        if ":" in match.group(1):
                            # HH:MM:SS format
                            parts = match.group(1).split(":")
                            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                        else:
                            seconds = float(match.group(1))
                        return {log_file.stem: seconds}
                    except (ValueError, IndexError):
                        pass
        except Exception:
            pass

    return {}


def parse_config_mk(config_path: Path) -> Dict[str, str]:
    """Parse config.mk for build parameters."""
    params = {}
    if not config_path.exists():
        return {}

    try:
        content = config_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                _, rest = line.split("export ", 1)
                key, value = rest.split("=", 1)
                params[key.strip()] = value.strip()
    except Exception:
        pass
    return params


def extract_design_metrics(json_path: Path) -> Dict[str, Any]:
    """Extract design metrics from synthesis JSON."""
    if not json_path.exists():
        return {}

    import json
    try:
        data = json.loads(json_path.read_text())
        metrics = {}

        # Extract hierarchy info
        if "modules" in data:
            for module_name, module_data in data["modules"].items():
                if "ports" in module_data:
                    # Count ports
                    pass
                if "cells" in module_data:
                    # Count cells
                    pass

        return {
            "num_modules": len(data.get("modules", {})),
            "num_cells": sum(1 for m in data.get("modules", {}).values() if "cells" in m for c in m["cells"]),
        }
    except Exception:
        pass

    return {}


def main():
    """CLI entry point for log parsing."""
    import argparse
    parser = argparse.ArgumentParser(description="Parse OpenROAD logs and reports")
    parser.add_argument("--logs-dir", type=str, help="Path to logs directory")
    parser.add_argument("--reports-dir", type=str, help="Path to reports directory")
    parser.add_argument("--output", type=str, help="Output JSON file path")
    args = parser.parse_args()

    import json
    results = {}

    if args.logs_dir:
        results["logs"] = parse_openroad_logs(args.logs_dir)

    if args.reports_dir:
        results["reports"] = parse_reports_directory(args.reports_dir)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Parsed results written to {args.output}")
    else:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()