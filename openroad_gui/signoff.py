"""Read DRC / LVS results produced by the ORFS ``make drc`` and ``make lvs`` targets.

Files (see the ORFS Makefile):

* DRC  ``reports/<platform>/<design>/base/6_drc.lyrdb``       KLayout marker database
       ``reports/<platform>/<design>/base/6_drc_count.rpt``   violation count (``grep -c "<value>"``)
* LVS  ``results/<platform>/<design>/base/6_lvs.lvsdb``       KLayout LVS database
       ``logs/<platform>/<design>/base/6_lvs.log``            KLayout log with the match verdict

When a platform has no deck, the Makefile writes "DRC/LVS not supported on this platform"
into the output file instead; that is reported as ``unsupported`` (never as zero).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from openroad_gui.config import AppConfig

DRC_LABEL = "DRC Check (KLayout)"
LVS_LABEL = "LVS Check (KLayout)"

# status values
NOT_RUN = "not_run"
UNSUPPORTED = "unsupported"
CLEAN = "clean"
VIOLATIONS = "violations"
ERROR = "error"


@dataclass
class SignoffResult:
    kind: str                       # "drc" | "lvs"
    status: str                     # one of the constants above
    count: int | None = None        # violation / mismatch count when known
    detail: str = ""                # human readable source / explanation
    stale: bool = False             # result file is older than the current 6_final.gds

    def display(self) -> tuple[str, str, str]:
        """Return (value text, unit text, level) for a metric card.

        level is one of "ok", "bad", "warn", "none".
        """
        unit_none = {NOT_RUN: "not run", UNSUPPORTED: "not supported", ERROR: "error"}
        if self.status in unit_none:
            value = "N/A" if self.status == UNSUPPORTED else "—"
            level = "warn" if self.status == ERROR else "none"
            return value, unit_none[self.status], level

        if self.kind == "drc":
            n = self.count or 0
            value, unit = str(n), "violations"
        else:
            if self.status == CLEAN:
                value, unit = "Clean", "netlists match"
            elif self.count:
                value, unit = str(self.count), "mismatches"
            else:
                value, unit = "Fail", "netlists differ"
        if self.stale:
            unit += " (stale)"
        return value, unit, "ok" if self.status == CLEAN else "bad"

    def summary(self) -> str:
        value, unit, _ = self.display()
        return f"{value} {unit}".strip() + (f" — {self.detail}" if self.detail else "")


# --------------------------------------------------------------------------- paths
def reports_dir(cfg: AppConfig) -> Path:
    return cfg.flow_dir / "reports" / cfg.platform / cfg.design_name / "base"


def logs_dir(cfg: AppConfig) -> Path:
    return cfg.flow_dir / "logs" / cfg.platform / cfg.design_name / "base"


def results_dir(cfg: AppConfig) -> Path:
    return cfg.results_dir / "base"


def drc_report_path(cfg: AppConfig) -> Path:
    return reports_dir(cfg) / "6_drc.lyrdb"


def lvs_db_path(cfg: AppConfig) -> Path:
    return results_dir(cfg) / "6_lvs.lvsdb"


def lvs_log_path(cfg: AppConfig) -> Path:
    return logs_dir(cfg) / "6_lvs.log"


# --------------------------------------------------------------------------- helpers
def _is_stale(path: Path, cfg: AppConfig) -> bool:
    gds = results_dir(cfg) / "6_final.gds"
    try:
        return gds.is_file() and path.stat().st_mtime < gds.stat().st_mtime
    except OSError:
        return False


def _head(path: Path, size: int = 512) -> str:
    try:
        with path.open("rb") as fh:
            return fh.read(size).decode("utf-8", errors="replace")
    except OSError:
        return ""


def _count_token(path: Path, token: bytes) -> int:
    """Count occurrences of ``token`` in a (possibly large) file without loading it whole."""
    total = 0
    keep = len(token) - 1
    tail = b""
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            data = tail + chunk
            total += data.count(token)
            tail = data[-keep:] if keep else b""   # shorter than token: cannot double count
    return total


# --------------------------------------------------------------------------- DRC
def read_drc(cfg: AppConfig) -> SignoffResult:
    lyrdb = drc_report_path(cfg)
    if not lyrdb.is_file():
        return SignoffResult("drc", NOT_RUN, detail="run DRC to generate 6_drc.lyrdb")
    if "not supported" in _head(lyrdb).lower():
        return SignoffResult("drc", UNSUPPORTED, detail=f"no DRC deck for platform {cfg.platform}")

    count: int | None = None
    source = "6_drc_count.rpt"
    count_rpt = reports_dir(cfg) / "6_drc_count.rpt"
    if count_rpt.is_file():
        try:
            count = int(count_rpt.read_text(encoding="utf-8", errors="replace").split()[0])
        except (OSError, ValueError, IndexError):
            count = None
    if count is None:
        try:
            count = _count_token(lyrdb, b"<value>")
            source = "6_drc.lyrdb"
        except OSError as exc:
            return SignoffResult("drc", ERROR, detail=str(exc))

    return SignoffResult(
        "drc",
        CLEAN if count == 0 else VIOLATIONS,
        count=count,
        detail=f"from {source}",
        stale=_is_stale(lyrdb, cfg),
    )


# --------------------------------------------------------------------------- LVS
_XREF_ISSUE = re.compile(r"(?m)^\s*(net|pin|device|circuit)\(.*?\b(nomatch|mismatch)\b")
_LOG_FAIL = re.compile(r"(don'?t|do not|doesn'?t)\s+match|mismatch", re.I)
_LOG_OK = re.compile(r"netlists match", re.I)


def read_lvs(cfg: AppConfig) -> SignoffResult:
    lvsdb = lvs_db_path(cfg)
    if not lvsdb.is_file():
        return SignoffResult("lvs", NOT_RUN, detail="run LVS to generate 6_lvs.lvsdb")
    if "not supported" in _head(lvsdb).lower():
        return SignoffResult("lvs", UNSUPPORTED, detail=f"no LVS deck for platform {cfg.platform}")

    try:
        text = lvsdb.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return SignoffResult("lvs", ERROR, detail=str(exc))

    matches = _XREF_ISSUE.findall(text)
    element_issues = sum(1 for kind, _ in matches if kind != "circuit")
    circuit_issues = sum(1 for kind, _ in matches if kind == "circuit")
    count = element_issues or circuit_issues

    log_text = ""
    log_path = lvs_log_path(cfg)
    if log_path.is_file():
        try:
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            log_text = ""
    log_fail = bool(_LOG_FAIL.search(log_text))
    log_ok = bool(_LOG_OK.search(log_text)) and not log_fail

    stale = _is_stale(lvsdb, cfg)
    if count or log_fail:
        return SignoffResult(
            "lvs", VIOLATIONS, count=count,
            detail="mismatching nets/devices/pins in 6_lvs.lvsdb" if count else "netlists don't match (6_lvs.log)",
            stale=stale,
        )
    return SignoffResult(
        "lvs", CLEAN, count=0,
        detail="netlists match (6_lvs.log)" if log_ok else "no mismatches in 6_lvs.lvsdb",
        stale=stale,
    )
