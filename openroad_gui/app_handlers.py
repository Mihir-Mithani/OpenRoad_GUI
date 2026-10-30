# openroad_gui/app_handlers.py
"""Handler methods for OpenRoadGUI - extracted from app.py for modularity."""

from __future__ import annotations

import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np

from openroad_gui import __version__
from openroad_gui.config import AppConfig, load_config, save_config
from openroad_gui.flow_runner import FULL_PIPELINE, FlowRunner, FlowStage
from openroad_gui.viewers import OPENROAD_GUI_STAGES, OpenROADGuiStage, ViewerService
from openroad_gui.widgets.flow_panel import FlowPanel
from openroad_gui.widgets.log_viewer import LogViewer
from openroad_gui.widgets.preview_panel import PreviewPanel
from openroad_gui.widgets.project_tree import ProjectTree
from openroad_gui.widgets.settings_dialog import SettingsDialog

# Intelligence modules
try:
    from openroad_gui.intelligence import FlowOptimizationEngine, FailurePredictor, SurrogateInference
    HAS_INTELLIGENCE = True
except ImportError:
    HAS_INTELLIGENCE = False
    FlowOptimizationEngine = None
    FailurePredictor = None
    SurrogateInference = None


# ─── File/Preview Handlers ───

def _on_file_select(self, path: Path) -> None:
    self._selected_file = path
    if path.is_file():
        suffix = path.suffix.lower()
        if suffix == ".gds":
            self._show_gds_file(path)
        else:
            self._show_text_file(path)
        if path.name == "config.mk":
            self._set_active_config(path)
    else:
        self.preview_panel.show_text(path, f"Directory: {path}")

def _show_text_file(self, path: Path) -> None:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        self.preview_panel.show_text(path, f"Cannot read file: {exc}")
        return
    self.preview_panel.show_text(path, content)

def _show_gds_file(self, path: Path) -> None:
    info = self.viewers.gds_info(path)
    self.preview_panel.show_text(path, info.summary)
    self._generate_gds_preview(path)

def _generate_gds_preview(self, path: Path) -> None:
    self.preview_panel.show_image_error(path, "Generating layout preview…")
    self.flow_panel.set_status("Rendering GDS preview…")

    def work() -> None:
        png_path, error = self.viewers.render_gds_preview(path)
        self.after(0, lambda: self._on_preview_ready(path, png_path, error))

    threading.Thread(target=work, daemon=True).start()

def _on_preview_ready(
    self, path: Path, png_path: Path | None, error: str
) -> None:
    self.flow_panel.set_status("Ready")
    if png_path:
        self.preview_panel.show_image(path, png_path, path.name)
        self.log_viewer.log_info(f"Layout preview generated for {path.name}\n")
    else:
        self.preview_panel.show_image_error(
            path,
            f"Preview unavailable.\n\n{error}\n\nUse 'View GDS in KLayout' for full viewing.",
        )

def _set_active_config(self, path: Path) -> None:
    flow_dir = self.app_config.flow_dir
    try:
        rel = path.relative_to(flow_dir)
        self.app_config.design_config = f"./{rel.as_posix()}"
    except ValueError:
        self.app_config.design_config = str(path)

    self.app_config.update_from_design_config(path)
    save_config(self.app_config)
    self.runner = FlowRunner(self.app_config)
    self.viewers = ViewerService(self.app_config)
    self.flow_panel.set_design_info(
        self.app_config.design_name,
        self.app_config.platform,
        self.app_config.design_config,
    )
    results_dir = self.app_config.results_dir
    if self.app_config.flow_dir.is_dir():
        self.project_tree.set_root(
            self.app_config.flow_dir,
            active_results_dir=results_dir if results_dir.is_dir() else None,
        )
    self.log_viewer.log_info(f"Active design set to: {self.app_config.design_config}\n")

def _use_as_config(self) -> None:
    if self._selected_file and self._selected_file.name == "config.mk":
        self._set_active_config(self._selected_file)
    else:
        messagebox.showinfo(
            "Select config.mk",
            "Select a config.mk file in the project tree first.",
        )

def _open_in_editor(self) -> None:
    if not self._selected_file or not self._selected_file.is_file():
        return
    path = str(self._selected_file)

    # Try Vim variants in order of preference
    vim_commands = [
        ["gvim", "--remote-tab-silent", path],  # GVim (GUI)
        ["mvim", "--remote-tab-silent", path],  # MacVim (GUI)
        ["vim", path],                           # Terminal vim
    ]

    for cmd in vim_commands:
        try:
            # Check if command exists
            subprocess.run(["which", cmd[0]], check=True, capture_output=True)
            # Found it — launch and return
            subprocess.Popen(cmd)
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue  # Try next editor

    # Fallback: system default editor
    try:
        if os.uname().sysname == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError as exc:
        messagebox.showerror("Open failed", str(exc))

def _resolve_gds_path(self, path: Path | None = None) -> Path | None:
    if path and path.is_file():
        return path
    default = self.viewers.default_gds_path()
    if default.is_file():
        return default
    chosen = filedialog.askopenfilename(
        title="Select GDS file",
        initialdir=str(self.app_config.results_dir),
        filetypes=[("GDSII", "*.gds"), ("All files", "*.*")],
    )
    return Path(chosen) if chosen else None

def _view_gds_in_klayout(self, path: Path | None = None) -> None:
    gds = self._resolve_gds_path(path)
    if not gds:
        messagebox.showinfo("No GDS", "No GDS file selected or found for the active design.")
        return
    ok, message = self.viewers.open_gds_in_klayout(gds)
    if ok:
        self.log_viewer.log_info(message + "\n")
    else:
        messagebox.showerror("KLayout", message)

def _view_default_gds(self) -> None:
    self._view_gds_in_klayout(self.viewers.default_gds_path())

def _view_selected_gds(self) -> None:
    if self._selected_file and self._selected_file.suffix.lower() == ".gds":
        self._view_gds_in_klayout(self._selected_file)
    else:
        self._view_default_gds()

def _preview_default_gds(self) -> None:
    gds = self._resolve_gds_path()
    if gds:
        self._selected_file = gds
        self._show_gds_file(gds)
    else:
        messagebox.showinfo("No GDS", "No GDS file found for the active design.")

def _preview_selected_gds(self) -> None:
    if self._selected_file and self._selected_file.suffix.lower() == ".gds":
        self._show_gds_file(self._selected_file)
    else:
        self._preview_default_gds()

def _open_or_gui_stage(self, stage: OpenROADGuiStage) -> None:
    if not self._validate_before_run():
        return
    ok, message = self.viewers.launch_openroad_gui(stage.make_target)
    if ok:
        self.log_viewer.log_info(message + "\n")
        self.flow_panel.set_status(stage.label)
    else:
        messagebox.showerror("OpenROAD GUI", message)

def _open_or_gui_for_file(self, path: Path) -> None:
    if path.suffix.lower() != ".odb":
        messagebox.showinfo("OpenROAD GUI", "Select an .odb checkpoint file.")
        return
    target = self.viewers.odb_gui_target(path)
    if not target:
        return
    if not self._validate_before_run():
        return
    ok, message = self.viewers.launch_openroad_gui(target)
    if ok:
        self.log_viewer.log_info(f"{message} — {path.name}\n")
    else:
        messagebox.showerror("OpenROAD GUI", message)

def _open_or_gui_for_selected(self) -> None:
    if self._selected_file and self._selected_file.suffix.lower() == ".odb":
        self._open_or_gui_for_file(self._selected_file)
    else:
        self._open_or_gui_stage(OpenROADGuiStage.FINAL)

def _open_settings(self) -> None:
    SettingsDialog(self, self.app_config, on_save=self._on_settings_saved)

def _on_settings_saved(self, config: AppConfig) -> None:
    self.app_config = config
    self._apply_config()

def _validate_before_run(self) -> bool:
    errors = self.app_config.validate()
    if errors:
        messagebox.showerror("Cannot run flow", "\n".join(errors))
        return False
    if not self.app_config.design_config:
        messagebox.showerror("No design", "Set an active design config.mk in Settings.")
        return False
    return True

def _run_stage(self, stage: FlowStage) -> None:
    if not self._validate_before_run():
        return

    self.flow_panel.set_running(True)
    self.log_viewer.log_info(f"\n--- Starting {stage.label} ---\n")
    self.runner.run_stage(stage, self._on_log_line, self._on_stage_done)

def _run_all(self) -> None:
    if not self._validate_before_run():
        return

    self.flow_panel.set_running(True)
    self.runner.run_pipeline(FULL_PIPELINE, self._on_log_line, self._on_stage_done)

def _stop_flow(self) -> None:
    self.runner.stop()
    self.log_viewer.log_error("Stop requested…")

def _make_clean(self) -> None:
    if not self._validate_before_run():
        return

    self.flow_panel.set_running(True)
    self.log_viewer.log_info("\n--- Running make clean ---\n")

    def on_log(stream: str, line: str) -> None:
        self.after(0, lambda: self.log_viewer.append(stream, line))

    def on_done(exit_code: int, label: str) -> None:
        def update() -> None:
            self.flow_panel.set_running(False)
            if exit_code == 0:
                self.flow_panel.set_status("Make Clean — done")
                self.log_viewer.log_info("--- Make Clean finished successfully ---\n")
            else:
                self.flow_panel.set_status(f"Make Clean — failed ({exit_code})")
                self.log_viewer.log_error(f"--- Make Clean failed (exit {exit_code}) ---\n")

        self.after(0, update)

    # Run make clean in the flow directory
    cfg = self.app_config
    design_config = cfg.design_config
    flow_dir = cfg.flow_dir
    env_script = cfg.env_script

    extra_exports = "\n".join(
        f'export {key}="{value}"' for key, value in cfg.extra_env.items()
    )
    klayout_export = f'export KLAYOUT_CMD="{cfg.klayout_cmd}"'

    command = (
        f'set -e\n'
        f'source "{env_script}"\n'
        f'{klayout_export}\n'
        f'{extra_exports}\n'
        f'cd "{flow_dir}"\n'
        f'echo ">>> Running: make DESIGN_CONFIG={design_config} clean_all"\n'
        f'make DESIGN_CONFIG={design_config} clean_all\n'
    )

    import threading
    thread = threading.Thread(
        target=self._run_clean_thread,
        args=(command, on_log, on_done),
        daemon=True,
    )
    thread.start()

def _run_clean_thread(self, command: str, on_log, on_done) -> None:
    import subprocess
    try:
        process = subprocess.Popen(
            ["/bin/bash", "-lc", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        on_log("stderr", f"Failed to start process: {exc}\n")
        on_done(1, "Make Clean")
        return

    assert process.stdout is not None
    assert process.stderr is not None

    def drain(stream_name: str, pipe) -> None:
        for line in iter(pipe.readline, ""):
            on_log(stream_name, line)

    stdout_thread = threading.Thread(
        target=drain, args=("stdout", process.stdout), daemon=True
    )
    stderr_thread = threading.Thread(
        target=drain, args=("stderr", process.stderr), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()
    stdout_thread.join()
    stderr_thread.join()

    exit_code = process.wait()
    on_done(exit_code, "Make Clean")

def _on_log_line(self, stream: str, line: str) -> None:
    self.after(0, lambda: self.log_viewer.append(stream, line))

def _on_stage_done(self, exit_code: int, label: str) -> None:
    def update() -> None:
        self.flow_panel.set_running(False)
        if exit_code == 0:
            self.flow_panel.set_status(f"{label} — done")
            self.log_viewer.log_info(f"--- {label} finished successfully ---\n")
            if label in ("GDSII Generation", "Full Pipeline"):
                gds = self.viewers.default_gds_path()
                if gds.is_file():
                    results_dir = self.app_config.results_dir
                    if self.app_config.flow_dir.is_dir():
                        self.project_tree.set_root(
                            self.app_config.flow_dir,
                            active_results_dir=results_dir if results_dir.is_dir() else None,
                        )
        else:
            self.flow_panel.set_status(f"{label} — failed ({exit_code})")
            self.log_viewer.log_error(f"--- {label} failed (exit {exit_code}) ---\n")

    self.after(0, update)