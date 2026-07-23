"""Flow stage control panel."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from openroad_gui.config import AppConfig
from openroad_gui.flow_runner import FULL_PIPELINE, FlowStage
from openroad_gui.viewers import OPENROAD_GUI_STAGES, OpenROADGuiStage


class ToolTip:
    """Simple tooltip for tkinter widgets."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window: Optional[tk.Toplevel] = None
        self.after_id: Optional[str] = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    def _on_enter(self, _event: tk.Event) -> None:
        self.after_id = self.widget.after(self.delay, self._show_tip)

    def _on_leave(self, _event: tk.Event) -> None:
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self._hide_tip()

    def _show_tip(self) -> None:
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip_window,
            text=self.text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("TkDefaultFont", 9),
            padx=6,
            pady=3,
        )
        label.pack()

    def _hide_tip(self) -> None:
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class FlowPanel(ttk.LabelFrame):
    def __init__(
        self,
        master: tk.Misc,
        on_run_stage: Callable[[FlowStage], None],
        on_run_all: Callable[[], None],
        on_stop: Callable[[], None],
        on_open_gui: Callable[[OpenROADGuiStage], None],
        on_view_gds: Callable[[], None],
        get_config: Callable[[], Optional[AppConfig]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, text="Flow Execution", padding=8, **kwargs)
        self.on_run_stage = on_run_stage
        self.on_run_all = on_run_all
        self.on_stop = on_stop
        self.on_open_gui = on_open_gui
        self.on_view_gds = on_view_gds
        self.get_config = get_config
        self._stage_buttons: dict[FlowStage, ttk.Button] = {}
        self._gui_buttons: dict[OpenROADGuiStage, ttk.Button] = {}
        self._stage_progress: dict[FlowStage, ttk.Progressbar] = {}
        self._current_stage: FlowStage | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        info = ttk.Frame(self)
        info.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(info, text="Design:").grid(row=0, column=0, sticky=tk.W)
        self.design_label = ttk.Label(info, text="—", font=("", 10, "bold"))
        self.design_label.grid(row=0, column=1, sticky=tk.W, padx=(4, 16))

        ttk.Label(info, text="Platform:").grid(row=0, column=2, sticky=tk.W)
        self.platform_label = ttk.Label(info, text="—")
        self.platform_label.grid(row=0, column=3, sticky=tk.W, padx=(4, 0))

        ttk.Label(info, text="Config:").grid(row=1, column=0, sticky=tk.NW, pady=(4, 0))
        self.config_label = ttk.Label(info, text="—", wraplength=420)
        self.config_label.grid(
            row=1, column=1, columnspan=3, sticky=tk.W, padx=(4, 0), pady=(4, 0)
        )

        stages_frame = ttk.Frame(self)
        stages_frame.pack(fill=tk.X, pady=4)

        stage_order = [
            FlowStage.SYNTH,
            FlowStage.FLOORPLAN,
            FlowStage.PLACE,
            FlowStage.CTS,
            FlowStage.ROUTE,
            FlowStage.GDS,
        ]

        # Tooltip texts for flow stages
        stage_tooltips = {
            FlowStage.SYNTH: "Run logic synthesis with Yosys\nConverts RTL to gate-level netlist",
            FlowStage.FLOORPLAN: "Floorplan and macro placement\nDefines die/core area, places macros and I/O pins",
            FlowStage.PLACE: "Standard cell placement\nPlaces and optimizes standard cells",
            FlowStage.CTS: "Clock Tree Synthesis\nBuilds clock distribution network",
            FlowStage.ROUTE: "Detailed routing & DRC\nRoutes signals and fixes design rule violations",
            FlowStage.GDS: "GDSII stream-out\nGenerates final GDSII for fabrication",
        }

        gui_tooltips = {
            OpenROADGuiStage.SYNTH: "Open OpenROAD GUI at synthesis stage\nView synthesized netlist and reports",
            OpenROADGuiStage.FLOORPLAN: "Open OpenROAD GUI at floorplan stage\nInspect macro placement and power grid",
            OpenROADGuiStage.PLACE: "Open OpenROAD GUI at placement stage\nView cell placement and congestion",
            OpenROADGuiStage.CTS: "Open OpenROAD GUI at CTS stage\nInspect clock tree and skew reports",
            OpenROADGuiStage.ROUTE: "Open OpenROAD GUI at routing stage\nView routing layers and DRC violations",
            OpenROADGuiStage.FINAL: "Open OpenROAD GUI at final stage\nFull design view with sign-off checks",
        }

        # 2 rows, 3 columns
        for idx, stage in enumerate(stage_order):
            row = idx // 3
            col = idx % 3
            row_frame = ttk.Frame(stages_frame)
            row_frame.grid(row=row, column=col, padx=4, pady=4, sticky=tk.EW)

            btn = ttk.Button(
                row_frame,
                text=stage.label,
                command=lambda s=stage: self.on_run_stage(s),
                width=22,
            )
            btn.pack(side=tk.LEFT)
            self._stage_buttons[stage] = btn

            # Add tooltip
            ToolTip(btn, stage_tooltips.get(stage, stage.label))

            # Progress bar for this stage (hidden by default)
            progress = ttk.Progressbar(
                row_frame,
                mode="indeterminate",
                length=180,
            )
            self._stage_progress[stage] = progress

            stages_frame.columnconfigure(col, weight=1)

        gui_frame = ttk.LabelFrame(self, text="OpenROAD GUI Viewer", padding=4)
        gui_frame.pack(fill=tk.X, pady=(4, 0))

        for idx, stage in enumerate(OPENROAD_GUI_STAGES):
            btn = ttk.Button(
                gui_frame,
                text=stage.label,
                command=lambda s=stage: self.on_open_gui(s),
                width=14,
            )
            btn.grid(row=idx // 3, column=idx % 3, padx=4, pady=4, sticky=tk.EW)
            self._gui_buttons[stage] = btn

            # Add tooltip
            ToolTip(btn, gui_tooltips.get(stage, stage.label))

        for col in range(3):
            gui_frame.columnconfigure(col, weight=1)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, pady=(8, 0))

        self.run_all_btn = ttk.Button(
            actions,
            text="▶ Run Full RTL-to-GDSII Pipeline",
            command=self.on_run_all,
        )
        self.run_all_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_btn = ttk.Button(
            actions,
            text="■ Stop",
            command=self.on_stop,
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            actions,
            text="View GDS in KLayout",
            command=self.on_view_gds,
        ).pack(side=tk.LEFT)

        ttk.Button(
            actions,
            text="Open Reports Folder",
            command=self._open_reports_folder,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(actions, textvariable=self.status_var).pack(side=tk.RIGHT)

    def _open_reports_folder(self) -> None:
        """Open the reports directory for the active design."""
        config = self.get_config() if self.get_config else None
        if not config:
            messagebox.showinfo("No Configuration", "No active design configuration available.")
            return

        reports_dir = config.flow_dir / "reports" / config.platform / config.design_name
        if not reports_dir.is_dir():
            messagebox.showinfo("Reports Not Found", f"Reports directory does not exist yet:\n{reports_dir}\n\nRun a flow stage first to generate reports.")
            return

        import subprocess
        import sys
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(reports_dir)])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", str(reports_dir)])
            else:
                subprocess.Popen(["xdg-open", str(reports_dir)])
        except OSError as exc:
            messagebox.showerror("Open Failed", f"Could not open reports folder:\n{exc}")

    def set_design_info(
        self, design_name: str, platform: str, design_config: str
    ) -> None:
        self.design_label.configure(text=design_name or "—")
        self.platform_label.configure(text=platform or "—")
        self.config_label.configure(text=design_config or "—")

    def set_running(self, running: bool) -> None:
        state = tk.DISABLED if running else tk.NORMAL
        self.run_all_btn.configure(state=state)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)
        for btn in self._stage_buttons.values():
            btn.configure(state=state)
        self.status_var.set("Running…" if running else "Ready")

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def start_stage_progress(self, stage: FlowStage) -> None:
        """Show and start indeterminate progress bar for a stage."""
        self._current_stage = stage
        progress = self._stage_progress.get(stage)
        if progress:
            progress.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
            progress.start(10)  # ms per step

    def stop_stage_progress(self, stage: FlowStage, success: bool = True) -> None:
        """Stop and hide progress bar for a stage."""
        progress = self._stage_progress.get(stage)
        if progress:
            progress.stop()
            progress.pack_forget()
        # Optionally update button appearance
        btn = self._stage_buttons.get(stage)
        if btn:
            btn.configure(text=f"✓ {stage.label}" if success else f"✗ {stage.label}")

    def reset_stage_buttons(self) -> None:
        """Reset all stage buttons to original labels."""
        for stage, btn in self._stage_buttons.items():
            btn.configure(text=stage.label)
