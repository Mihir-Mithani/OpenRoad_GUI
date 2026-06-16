"""Flow stage control panel."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from openroad_gui.flow_runner import FULL_PIPELINE, FlowStage
from openroad_gui.viewers import OPENROAD_GUI_STAGES, OpenROADGuiStage


class FlowPanel(ttk.LabelFrame):
    def __init__(
        self,
        master: tk.Misc,
        on_run_stage: Callable[[FlowStage], None],
        on_run_all: Callable[[], None],
        on_stop: Callable[[], None],
        on_open_gui: Callable[[OpenROADGuiStage], None],
        on_view_gds: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, text="Flow Execution", padding=8, **kwargs)
        self.on_run_stage = on_run_stage
        self.on_run_all = on_run_all
        self.on_stop = on_stop
        self.on_open_gui = on_open_gui
        self.on_view_gds = on_view_gds
        self._stage_buttons: dict[FlowStage, ttk.Button] = {}
        self._gui_buttons: dict[OpenROADGuiStage, ttk.Button] = {}
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

        for idx, stage in enumerate(stage_order):
            btn = ttk.Button(
                stages_frame,
                text=stage.label,
                command=lambda s=stage: self.on_run_stage(s),
                width=22,
            )
            btn.grid(row=idx // 3, column=idx % 3, padx=4, pady=4, sticky=tk.EW)
            self._stage_buttons[stage] = btn

        for col in range(3):
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

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(actions, textvariable=self.status_var).pack(side=tk.RIGHT)

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
        for btn in self._gui_buttons.values():
            btn.configure(state=state)
        self.status_var.set("Running…" if running else "Ready")

    def set_status(self, message: str) -> None:
        self.status_var.set(message)
