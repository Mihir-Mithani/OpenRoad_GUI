"""Persistent application configuration."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_ORFS_ROOT = ""
DEFAULT_KLAYOUT_CMD = "/Applications/KLayout/klayout.app/Contents/MacOS/klayout"
CONFIG_DIR = Path.home() / ".config" / "openroad-gui"
CONFIG_FILE = CONFIG_DIR / "config.json"

PLATFORMS = [
    "asap7",
    "nangate45",
    "sky130hd",
    "sky130hs",
    "gf12",
    "gf180",
    "ihp-sg13g2",
]


@dataclass
class AppConfig:
    orfs_root: str = DEFAULT_ORFS_ROOT
    klayout_cmd: str = DEFAULT_KLAYOUT_CMD
    design_config: str = "./designs/asap7/alu4/config.mk"
    platform: str = "asap7"
    design_name: str = "alu4"
    extra_env: dict[str, str] = field(default_factory=dict)
    last_project_dir: str = ""

    @property
    def flow_dir(self) -> Path:
        return Path(self.orfs_root) / "flow"

    @property
    def designs_dir(self) -> Path:
        return self.flow_dir / "designs"

    @property
    def env_script(self) -> Path:
        return Path(self.orfs_root) / "use-openroad.sh"

    @property
    def results_dir(self) -> Path:
        return self.flow_dir / "results" / self.platform / self.design_name

    def gds_target(self) -> str:
        rel = self.results_dir.relative_to(self.flow_dir)
        return f"{rel.as_posix()}/base/6_final.gds"

    @property
    def logs_dir(self) -> Path:
        return CONFIG_DIR / "logs"


    def update_from_design_config(self, config_path: str | Path) -> None:
        """Parse config.mk to refresh platform and design name."""
        path = Path(config_path)
        if not path.is_absolute():
            path = self.flow_dir / path
        if not path.exists():
            return

        self.design_config = self._relative_design_config(path)
        parts = path.parts
        if "designs" in parts:
            idx = parts.index("designs")
            if idx + 2 < len(parts):
                self.platform = parts[idx + 1]
                self.design_name = parts[idx + 2]

    def _relative_design_config(self, path: Path) -> str:
        try:
            rel = path.relative_to(self.flow_dir)
            return f"./{rel.as_posix()}"
        except ValueError:
            return str(path)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.orfs_root:
            errors.append(
                "OpenROAD root path is not set. "
                "Go to Settings \u2192 Paths to configure it."
            )
            return errors
        if not Path(self.orfs_root).is_dir():
            errors.append(f"OpenROAD root not found: {self.orfs_root}")
        elif not self.flow_dir.is_dir():
            errors.append(f"flow/ directory missing under {self.orfs_root}")
        elif not self.env_script.is_file():
            errors.append(f"use-openroad.sh not found at {self.env_script}")
        return errors


def load_config() -> AppConfig:
    if not CONFIG_FILE.exists():
        return AppConfig()

    try:
        with CONFIG_FILE.open(encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return AppConfig()

    extra_env = data.pop("extra_env", {})
    config = AppConfig(**{k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__})
    config.extra_env = extra_env if isinstance(extra_env, dict) else {}
    return config


def save_config(config: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as fh:
        json.dump(asdict(config), fh, indent=2)
