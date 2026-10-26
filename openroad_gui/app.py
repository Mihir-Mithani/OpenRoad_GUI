"""Main application window."""

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


class OpenRoadGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"OpenROAD Flow GUI v{__version__}")
        self.geometry("1200x800")
        self.minsize(900, 600)

        self.app_config = load_config()
        self.runner = FlowRunner(self.app_config)
        self.viewers = ViewerService(self.app_config)

        # Initialize intelligence modules
        self.optimizer = None
        self.failure_predictor = None
        self.surrogate_inference = None
        if HAS_INTELLIGENCE:
            try:
                self.optimizer = FlowOptimizationEngine()
                self.failure_predictor = FailurePredictor()
                self.surrogate_inference = SurrogateInference(
                    Path(__file__).parent.parent / "intelligence" / "models" / "saved"
                )
            except Exception as e:
                print(f"Warning: Could not initialize intelligence modules: {e}")

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

        # Intelligence menu
        intel_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Intelligence", menu=intel_menu)
        if HAS_INTELLIGENCE:
            intel_menu.add_command(
                label="Predict Failure Risk",
                command=self._predict_failure_risk,
            )
            intel_menu.add_command(
                label="Suggest Optimal Parameters",
                command=self._suggest_optimal_params,
            )
            intel_menu.add_separator()
            intel_menu.add_command(
                label="Show Surrogate Predictions",
                command=self._show_surrogate_predictions,
            )
            intel_menu.add_separator()
            intel_menu.add_command(
                label="Open Intelligence Reports",
                command=self._open_intelligence_reports,
            )
        else:
            intel_menu.add_command(
                label="Intelligence Unavailable",
                state="disabled",
            )

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
            on_make_clean=self._make_clean,
            get_config=lambda: self.app_config,
        )
        self.flow_panel.pack(fill=tk.X, padx=4, pady=4)

        # Action buttons frame (fixed, not in paned window)
        action_frame = ttk.Frame(right)
        action_frame.pack(fill=tk.X, padx=4, pady=(0, 4))
        ttk.Button(action_frame, text="Open in Editor", command=self._open_in_editor).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_frame, text="Use as Active config.mk", command=self._use_as_config).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_frame, text="View GDS in KLayout", command=self._view_selected_gds).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_frame, text="Preview Layout", command=self._preview_selected_gds).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_frame, text="OpenROAD GUI", command=self._open_or_gui_for_selected).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_frame, text="Open Reports Folder", command=self._open_reports_folder).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_frame, text="Export Log...", command=self._export_log).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_frame, text="Open Terminal Here", command=self._open_terminal_here).pack(side=tk.LEFT)

        # Vertical paned window for preview and log viewer
        right_paned = ttk.PanedWindow(right, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.preview_panel = PreviewPanel(right_paned)
        right_paned.add(self.preview_panel, weight=3)

        self.log_viewer = LogViewer(right_paned)
        right_paned.add(self.log_viewer, weight=1)

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

        # Get selected clean target from dropdown
        clean_target = self.flow_panel.clean_var.get()

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
            f'echo ">>> Running: make DESIGN_CONFIG={design_config} {clean_target}"\n'
            f'make DESIGN_CONFIG={design_config} {clean_target}\n'
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

    def _open_reports_folder(self) -> None:
        """Open the reports directory for the active design."""
        # Reports are under flow/reports/<platform>/<design>/base/ (ORFS convention)
        reports_dir = self.app_config.flow_dir / "reports" / self.app_config.platform / self.app_config.design_name / "base"
        if not reports_dir.is_dir():
            messagebox.showinfo("No Reports", "Reports directory not found. Run a flow stage first.")
            return
        try:
            import os
            if os.uname().sysname == "Darwin":
                subprocess.Popen(["open", str(reports_dir)])
            else:
                subprocess.Popen(["xdg-open", str(reports_dir)])
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))

    def _export_log(self) -> None:
        """Export the current log to a file."""
        from tkinter import filedialog
        content = self.log_viewer.get_text()
        if not content.strip():
            messagebox.showinfo("Empty Log", "No log content to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Export Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"{self.app_config.design_name}_flow_log.txt",
        )
        if path:
            try:
                Path(path).write_text(content, encoding="utf-8")
                self.log_viewer.log_info(f"Log exported to {path}\n")
            except OSError as exc:
                messagebox.showerror("Export failed", str(exc))

    def _open_terminal_here(self) -> None:
        """Open system terminal at the active design's flow directory."""
        cwd = self.app_config.flow_dir
        if not cwd.is_dir():
            messagebox.showinfo("No Flow Dir", "Flow directory not found.")
            return
        try:
            import os
            if os.uname().sysname == "Darwin":
                script = f'tell application "Terminal" to do script "cd {cwd} && clear"'
                subprocess.Popen(["osascript", "-e", script])
            elif os.uname().sysname == "Windows":
                subprocess.Popen(["cmd", "/k", f"cd /d {cwd}"])
            else:
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm", "tilix", "alacritty", "kitty"]:
                    try:
                        subprocess.Popen([term, "--working-directory", str(cwd)])
                        break
                    except FileNotFoundError:
                        continue
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))

    # ============================================================
    # Intelligence Methods
    # ============================================================

    def _predict_failure_risk(self) -> None:
        """Predict failure risk for the current design using real flow metrics."""
        if not HAS_INTELLIGENCE or self.failure_predictor is None:
            messagebox.showinfo("Intelligence Unavailable", "Failure predictor not available.")
            return

        if not self.app_config.design_config:
            messagebox.showwarning("No Design", "No active design selected.")
            return

        # Fetch real metrics from flow reports
        metrics = self._fetch_design_metrics()

        if not metrics:
            messagebox.showinfo(
                "No Metrics Available",
                "No flow metrics found. Run a flow stage first to collect metrics."
            )
            return

        # Show which metrics were found
        found_metrics = [k for k, v in metrics.items() if v is not None and v != 0]
        self.log_viewer.log_info(f"Found metrics for prediction: {', '.join(found_metrics)}\n")

        # Use the failure predictor with real metrics
        prediction = self.failure_predictor.predict(metrics)

        # Format the prediction results
        if not prediction.get("predictions"):
            messagebox.showinfo(
                "Failure Risk Assessment",
                f"Design: {self.app_config.design_name}\n"
                f"Platform: {self.app_config.platform}\n\n"
                "No significant failure risks detected.\n\n"
                f"Overall Risk: {prediction.get('overall_risk', 0.0):.1%}\n"
                f"Recommendations: {', '.join(prediction.get('recommendations', ['No specific mitigations needed']))}"
            )
            return

        # Format detailed predictions
        msg_lines = [
            f"Failure Risk Assessment for {self.app_config.design_name}",
            f"Platform: {self.app_config.platform}",
            f"Overall Risk: {prediction.get('overall_risk', 0.0):.1%}",
            "",
        ]

        # Show key metrics being used
        key_metrics = ['wns_ns', 'tns_ns', 'drc_violations', 'congestion_pct', 'area_um2', 'power_mw']
        metric_lines = ["Key Metrics:"]
        for km in key_metrics:
            if km in metrics:
                metric_lines.append(f"  {km}: {metrics[km]}")
        msg_lines.extend(metric_lines)
        msg_lines.append("")

        for failure_type, pred in prediction.get("predictions", {}).items():
            prob = pred.get("probability", 0)
            severity = pred.get("severity", "unknown")
            mitigations = pred.get("mitigations", [])
            # failure_type is a string key from the predictor (e.g., "timing_violation")
            msg_lines.append(f"  {failure_type}: {prob:.1%} ({severity})")
            if mitigations:
                msg_lines.append(f"  Mitigations: {', '.join(mitigations[:3])}")

        msg_lines.append("")
        msg_lines.append(f"Recommendations: {', '.join(prediction.get('recommendations', ['None']))}")

        messagebox.showinfo("Failure Risk Assessment", "\n".join(msg_lines))
    def _suggest_optimal_params(self) -> None:
        """Suggest optimal flow parameters using the optimization engine."""
        if not HAS_INTELLIGENCE or self.optimizer is None:
            messagebox.showinfo("Intelligence Unavailable", "Optimization engine not available.")
            return

        if not self.app_config.design_config:
            messagebox.showwarning("No Design", "No active design selected.")
            return

        messagebox.showinfo(
            "Optimal Parameter Suggestion",
            f"Design: {self.app_config.design_name}\n"
            f"Platform: {self.app_config.platform}\n\n"
            "Optimal parameter suggestions would include:\n"
            "  • Synthesis strategy & effort\n"
            "  • Placement density & effort\n"
            "  • CTS skew target & buffer type\n"
            "  • Routing layers & effort\n\n"
            "Run a flow stage first to collect metrics for accurate suggestions."
        )

    def _show_surrogate_predictions(self) -> None:
        """Show surrogate model predictions for the current design."""
        if not HAS_INTELLIGENCE or self.surrogate_inference is None:
            messagebox.showinfo("Intelligence Unavailable", "Surrogate models not available.")
            return

        if not self.app_config.design_config:
            messagebox.showwarning("No Design", "No active design selected.")
            return

        # Build features from config.mk and design
        features = self._build_surrogate_features()

        if not features:
            messagebox.showinfo(
                "Cannot Predict",
                "Could not extract design features. Ensure config.mk exists and has required parameters."
            )
            return

        # Get predictions from surrogate models
        predictions = self.surrogate_inference.predict_ensemble(features)

        # Format results
        msg_lines = [
            f"Surrogate Model Predictions (Ensemble)",
            f"Design: {self.app_config.design_name}",
            f"Platform: {self.app_config.platform}",
            "",
            f"Predicted WNS: {predictions.get('wns', 0):.2f} ns",
            f"Predicted TNS: {predictions.get('tns', 0):.2f} ns",
            f"Predicted Area: {predictions.get('area', 0):.0f} um²",
            f"Predicted Power: {predictions.get('power', 0):.1f} mW",
            "",
            "Note: Predictions based on synthetic training data. "
            "Accuracy improves with real ORFS run data.",
        ]

        messagebox.showinfo("Surrogate Predictions", "\n".join(msg_lines))

    def _open_intelligence_reports(self) -> None:
        """Open the intelligence reports directory."""
        if not HAS_INTELLIGENCE:
            messagebox.showinfo("Intelligence Unavailable", "Intelligence reports not available.")
            return

        # Open the logs/training directory where surrogate results are stored
        try:
            import os
            reports_dir = Path(__file__).parent.parent / "intelligence" / "training" / "logs"
            if not reports_dir.exists():
                messagebox.showinfo("No Reports", "Intelligence reports not found. Run training first.")
                return

            if os.uname().sysname == "Darwin":
                subprocess.Popen(["open", str(reports_dir)])
            else:
                subprocess.Popen(["xdg-open", str(reports_dir)])
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))

    def _build_surrogate_features(self) -> dict:
        """Build feature dict for surrogate inference from active design config."""
        features = {}

        # Parse config.mk for design parameters
        config_path = self.app_config.flow_dir / "designs" / self.app_config.platform / self.app_config.design_name / "config.mk"
        if config_path.exists():
            import re
            content = config_path.read_text()

            # Extract key parameters
            for key in ['CORE_UTILIZATION', 'CORE_ASPECT_RATIO', 'CORE_MARGIN']:
                match = re.search(rf'{key}\s*=\s*([\d.]+)', content)
                if match:
                    features[key.lower()] = float(match.group(1))

        # Set defaults for missing
        features.setdefault('core_utilization', 30.0)
        features.setdefault('core_aspect_ratio', 1.0)
        features.setdefault('core_margin', 5.0)

        # Platform
        features['platform'] = self.app_config.platform
        features['core_aspect_ratio'] = float(features['core_aspect_ratio'])

        # Estimate design size from config.mk verilog files
        verilog_files = list((self.app_config.flow_dir / "designs" / self.app_config.platform / self.app_config.design_name).glob("*.v"))
        num_instances = 5000  # default
        if verilog_files:
            # Rough estimate from verilog
            content = verilog_files[0].read_text()
            num_instances = max(100, len(re.findall(r'\b(module|always|assign)\b', content)) * 100)

        features['num_instances'] = num_instances
        features['num_nets'] = int(num_instances * 1.2)
        features['num_sequential'] = int(num_instances * 0.2)
        features['num_macros'] = 0
        features['macro_area_ratio'] = 0.0

        # Derived features
        features['log_instances'] = np.log1p(num_instances) / 20.0
        features['log_nets'] = np.log1p(features['num_nets']) / 20.0
        features['seq_ratio'] = features['num_sequential'] / max(1, features['num_instances'])
        features['macro_ratio'] = features['num_macros'] / max(1, features['num_instances'])

        return features

    def _fetch_design_metrics(self) -> dict:
        """Fetch real metrics from flow reports for the active design."""
        metrics = {}

        if not self.app_config.design_config or not self.app_config.results_dir:
            return metrics

        reports_dir = self.app_config.flow_dir / "reports" / self.app_config.platform / self.app_config.design_name / "base"
        if not reports_dir.exists():
            self.log_viewer.log_error(f"Reports directory not found: {reports_dir}\n")
            return metrics

        self.log_viewer.log_info(f"Looking for reports in: {reports_dir}\n")

        # Use the parser to extract metrics from ALL reports in the directory
        from openroad_gui.intelligence.data.parser import parse_reports_directory
        try:
            metrics = parse_reports_directory(str(reports_dir))
            self.log_viewer.log_info(f"parse_reports_directory found metrics: {list(metrics.keys())}\n")
        except Exception as e:
            self.log_viewer.log_error(f"Failed to parse reports: {e}\n")

        # Also try to get metrics from the latest stage report (by stage number)
        # ORFS reports are named: 1_synth.rpt, 2_floorplan.rpt, 3_place.rpt, 4_cts.rpt, 5_route.rpt, 6_finish.rpt
        # Also handles variants like 4_cts_final.rpt
        try:
            if reports_dir.exists():
                # Look for all numbered stage reports (including _final suffix)
                stage_reports = list(reports_dir.glob("[0-9]_*.rpt"))
                self.log_viewer.log_info(f"Found stage reports: {[f.name for f in stage_reports]}\n")
                if stage_reports:
                    # Sort by stage number (extract number from filename)
                    def stage_num(f):
                        try:
                            return int(f.stem.split('_')[0])
                        except (ValueError, IndexError):
                            return 0

                    latest_report = max(stage_reports, key=stage_num)
                    self.log_viewer.log_info(f"Latest stage report: {latest_report.name}\n")
                    content = latest_report.read_text()
                    # Debug: show first 500 chars of report
                    self.log_viewer.log_info(f"Report preview: {content[:500]}\n")
                    from openroad_gui.intelligence.data.parser import _parse_report_content
                    latest_metrics = _parse_report_content(content)
                    self.log_viewer.log_info(f"Parsed metrics from {latest_report.name}: {latest_metrics}\n")
                    # Update metrics with latest stage data (higher priority)
                    metrics.update(latest_metrics)
                    self.log_viewer.log_info(f"Using metrics from latest stage report: {latest_report.name}\n")
        except Exception as e:
            self.log_viewer.log_error(f"Failed to parse latest stage report: {e}\n")
            import traceback
            self.log_viewer.log_error(traceback.format_exc() + "\n")

        # Final check - if still empty, list all files in reports dir
        if not metrics:
            try:
                all_files = list(reports_dir.glob("*"))
                self.log_viewer.log_info(f"All files in reports dir: {[f.name for f in all_files]}\n")
            except Exception:
                pass

        return metrics


def run() -> None:
    """Entry point for the application."""
    app = OpenRoadGUI()
    app.mainloop()