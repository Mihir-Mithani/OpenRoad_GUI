"""Launch external viewers and generate layout previews."""

from __future__ import annotations

import subprocess
import tempfile
from enum import Enum
from pathlib import Path

from openroad_gui.config import AppConfig
from openroad_gui.gds_info import GdsInfo, parse_gds

_KLAYOUT_EXPORT_SCRIPT = """\
gds = $gds
png = $png
width = ($width || 640).to_i
height = ($height || 480).to_i
layout = RBA::Layout::new
layout.read(gds)
lv = RBA::LayoutView::new
lv.show_layout(layout, true)
lv.max_hier
lv.save_image(png, width, height)
"""


class OpenROADGuiStage(Enum):
    SYNTH = ("gui_synth", "Synthesis")
    FLOORPLAN = ("gui_floorplan", "Floorplan")
    PLACE = ("gui_place", "Placement")
    CTS = ("gui_cts", "CTS")
    ROUTE = ("gui_route", "Routing")
    FINAL = ("gui_final", "Final")

    def __init__(self, make_target: str, label: str) -> None:
        self.make_target = make_target
        self.label = label


OPENROAD_GUI_STAGES = list(OpenROADGuiStage)


class ViewerService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def gds_info(self, path: Path) -> GdsInfo:
        return parse_gds(path)

    def open_gds_in_klayout(self, path: Path) -> tuple[bool, str]:
        klayout = Path(self.config.klayout_cmd)
        if not klayout.is_file():
            return False, f"KLayout not found: {klayout}"
        if not path.is_file():
            return False, f"GDS file not found: {path}"

        try:
            subprocess.Popen([str(klayout), str(path)])
        except OSError as exc:
            return False, str(exc)
        return True, f"Opened {path.name} in KLayout"

    def render_gds_preview(
        self, path: Path, width: int = 640, height: int = 480
    ) -> tuple[Path | None, str]:
        klayout = Path(self.config.klayout_cmd)
        if not klayout.is_file():
            return None, f"KLayout not found: {klayout}"
        if not path.is_file():
            return None, f"GDS file not found: {path}"

        script_path = Path(tempfile.gettempdir()) / "openroad_gui_klayout_export.rb"
        script_path.write_text(_KLAYOUT_EXPORT_SCRIPT, encoding="utf-8")
        png_path = Path(tempfile.gettempdir()) / f"openroad_gui_{path.stem}_preview.png"

        try:
            result = subprocess.run(
                [
                    str(klayout),
                    "-b",
                    "-r",
                    str(script_path),
                    "-rd",
                    f"gds={path}",
                    "-rd",
                    f"png={png_path}",
                    "-rd",
                    f"width={width}",
                    "-rd",
                    f"height={height}",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, str(exc)

        if result.returncode != 0 or not png_path.is_file():
            err = (result.stderr or result.stdout or "Preview generation failed").strip()
            return None, err
        return png_path, ""

    def odb_gui_target(self, odb_path: Path) -> str | None:
        """Derive a make gui_* target from an .odb filename."""
        stem = odb_path.stem
        shortcuts = {
            "1_synth": "gui_synth",
            "2_floorplan": "gui_floorplan",
            "3_place": "gui_place",
            "4_cts": "gui_cts",
            "5_route": "gui_route",
            "5_1_grt": "gui_grt",
            "6_final": "gui_final",
        }
        if stem in shortcuts:
            return shortcuts[stem]
        return f"gui_{stem}"

    def build_openroad_gui_command(self, make_target: str) -> str:
        cfg = self.config
        extra_exports = "\n".join(
            f'export {key}="{value}"' for key, value in cfg.extra_env.items()
        )
        klayout_export = f'export KLAYOUT_CMD="{cfg.klayout_cmd}"'
        return (
            f'source "{cfg.env_script}"\n'
            f"{klayout_export}\n"
            f"{extra_exports}\n"
            f'cd "{cfg.flow_dir}"\n'
            f'echo ">>> Launching: make DESIGN_CONFIG={cfg.design_config} {make_target}"\n'
            f"make DESIGN_CONFIG={cfg.design_config} {make_target}\n"
        )

    def launch_openroad_gui(self, make_target: str) -> tuple[bool, str]:
        errors = self.config.validate()
        if errors:
            return False, "\n".join(errors)
        if not self.config.design_config:
            return False, "No active design config.mk set"

        command = self.build_openroad_gui_command(make_target)
        try:
            subprocess.Popen(
                ["/bin/bash", "-lc", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            return False, str(exc)
        return True, f"Launched OpenROAD GUI ({make_target})"

    def default_gds_path(self) -> Path:
        return self.config.results_dir / "base" / "6_final.gds"
