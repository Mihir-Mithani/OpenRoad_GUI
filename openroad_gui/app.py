"""Main application window."""

from __future__ import annotations

import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from openroad_gui import __version__
from openroad_gui.config import AppConfig, load_config, save_config
from openroad_gui.flow_runner import FULL_PIPELINE, FlowRunner, FlowStage
from openroad_gui.viewers import OPENROAD_GUI_STAGES, OpenROADGuiStage, ViewerService
from openroad_gui.widgets.flow_panel import FlowPanel
from openroad_gui.widgets.log_viewer import LogViewer
from openroad_gui.widgets.preview_panel import PreviewPanel
from openroad_gui.widgets.project_tree import ProjectTree
from openroad_gui.widgets.settings_dialog import SettingsDialog


class OpenRoadGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"OpenROAD Flow GUI v{__version__}")
        self.geometry("1200x800")
        self.minsize(900, 600)

        self.app_config = load_config()
        self.runner = FlowRunner(self.app_config)
        self.viewers = ViewerService(self.app_config)

        self._apply_style()
        self._build_menu()
        self._build_layout()
        self._apply_config()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_style(self) -> None:
        style = ttk.Style(self)
        if "aqua" in style.theme_names():
            style.theme_use("aqua")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings…", command=self._open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_close)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(
            label="GDS — View in KLayout",
            command=self._view_default_gds,
        )
        view_menu.add_command(
            label="GDS — Preview Layout",
            command=self._preview_default_gds,
        )
        view_menu.add_separator()
        for stage in OPENROAD_GUI_STAGES:
            view_menu.add_command(
                label=f"OpenROAD GUI — {stage.label}",
                command=lambda s=stage: self._open_or_gui_stage(s),
            )

        flow_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Flow", menu=flow_menu)
        for stage in FULL_PIPELINE:
            flow_menu.add_command(
                label=stage.label,
                command=lambda s=stage: self._run_stage(s),
            )
        flow_menu.add_separator()
        flow_menu.add_command(label="Run Full Pipeline", command=self._run_all)
        flow_menu.add_command(label="Stop", command=self._stop_flow)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Quick Start", command=self._show_help)

    def _build_layout(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        left = ttk.Frame(paned, width=280)
        paned.add(left, weight=1)

        right = ttk.Frame(paned)
        paned.add(right, weight=3)

        self.project_tree = ProjectTree(
            left,
            on_select=self._on_file_select,
            on_view_gds=self._view_gds_in_klayout,
            on_open_or_gui=self._open_or_gui_for_file,
        )
        self.project_tree.pack(fill=tk.BOTH, expand=True)

        self.flow_panel = FlowPanel(
            right,
            on_run_stage=self._run_stage,
            on_run_all=self._run_all,
            on_stop=self._stop_flow,
            on_open_gui=self._open_or_gui_stage,
            on_view_gds=self._view_default_gds,
        )
        self.flow_panel.pack(fill=tk.X, padx=4, pady=4)

        self.preview_panel = PreviewPanel(right)
        self.preview_panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.preview_panel.add_action("Open in Editor", self._open_in_editor)
        self.preview_panel.add_action("Use as Active config.mk", self._use_as_config)
        self.preview_panel.add_action("View GDS in KLayout", self._view_selected_gds)
        self.preview_panel.add_action("Preview Layout", self._preview_selected_gds)
        self.preview_panel.add_action("OpenROAD GUI", self._open_or_gui_for_selected)

        self.log_viewer = LogViewer(self)
        self.log_viewer.pack(fill=tk.BOTH, expand=False, padx=6, pady=(0, 6))

        self._selected_file: Path | None = None

    def _apply_config(self) -> None:
        self.app_config.update_from_design_config(self.app_config.design_config)
        self.runner = FlowRunner(self.app_config)
        self.viewers = ViewerService(self.app_config)

        flow_dir = self.app_config.flow_dir
        results_dir = self.app_config.results_dir
        if flow_dir.is_dir():
            self.project_tree.set_root(
                flow_dir,
                active_results_dir=results_dir if results_dir.is_dir() else None,
            )
        else:
            self.log_viewer.log_error(
                f"Flow directory not found: {flow_dir}\n"
                "Open Settings to set the correct OpenROAD root path."
            )

        self.flow_panel.set_design_info(
            self.app_config.design_name,
            self.app_config.platform,
            self.app_config.design_config,
        )

        errors = self.app_config.validate()
        if errors:
            self.log_viewer.log_info("Environment check:\n" + "\n".join(f"  • {e}" for e in errors))
        else:
            gds = self.viewers.default_gds_path()
            gds_note = f"GDS: {gds.name} ({'found' if gds.is_file() else 'not yet built'})"
            self.log_viewer.log_info(
                f"Ready — ORFS: {self.app_config.orfs_root}\n"
                f"Active design: {self.app_config.platform}/{self.app_config.design_name}\n"
                f"{gds_note}\n"
            )

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
                        self.project_tree.set_root(
                            self.app_config.flow_dir,
                            active_results_dir=results_dir if results_dir.is_dir() else None,
                        )
            else:
                self.flow_panel.set_status(f"{label} — failed ({exit_code})")
                self.log_viewer.log_error(f"--- {label} failed (exit {exit_code}) ---\n")

        self.after(0, update)

    def _show_help(self) -> None:
        messagebox.showinfo(
            "Quick Start",
            "1. Open Settings and set your OpenROAD root (ORFS) path.\n"
            "2. Select or create a design under flow/designs/<pdk>/<name>/.\n"
            "3. Click a config.mk in the tree to make it the active design.\n"
            "4. Run individual stages or the full RTL-to-GDSII pipeline.\n"
            "5. View results under 'results (<design>)' in the project tree.\n"
            "6. Double-click a .gds file to open in KLayout.\n"
            "7. Use View menu or Flow panel to launch OpenROAD GUI at any stage.\n\n"
            "The app sources use-openroad.sh automatically before each make.",
        )

    def _on_close(self) -> None:
        if self.runner.is_running:
            if not messagebox.askyesno(
                "Flow running",
                "A flow stage is still running. Quit anyway?",
            ):
                return
            self.runner.stop()
        self.destroy()


def run() -> None:
    app = OpenRoadGUI()
    app.mainloop()
