"""Pipeline stage row visualization using Canvas."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from openroad_gui.config import AppConfig
from openroad_gui.flow_runner import FULL_PIPELINE, FlowStage
from openroad_gui.theme import (ACCENT_AMBER, ACCENT_BLUE, ACCENT_GREEN,
                                ACCENT_RED, BG_DARK, BG_ELEVATED, BG_HOVER,
                                BG_PANEL, BORDER, FG_PRIMARY, FG_SECONDARY)
from openroad_gui.viewers import OPENROAD_GUI_STAGES, OpenROADGuiStage


# Stage icons (Unicode symbols)
STAGE_ICONS = {
    FlowStage.SYNTH: "⟳",       # Waveform/synthesis
    FlowStage.FLOORPLAN: "⬜",    # Grid/floorplan
    FlowStage.PLACE: "⬛",       # Placement
    FlowStage.CTS: "✂",         # Scissors/CTS
    FlowStage.ROUTE: "⎋",       # Routing
    FlowStage.GDS: "◆",         # Diamond/GDS
}

STAGE_SHORT_NAMES = {
    FlowStage.SYNTH: "Synth",
    FlowStage.FLOORPLAN: "Floorplan",
    FlowStage.PLACE: "Place",
    FlowStage.CTS: "CTS",
    FlowStage.ROUTE: "Route",
    FlowStage.GDS: "GDS",
}

class PipelineRow(ttk.Frame):
    """Horizontal pipeline visualization with circular nodes connected by line."""

    def __init__(
        self,
        master: tk.Misc,
        on_run_stage: Callable[[FlowStage], None],
        on_run_all: Callable[[], None],
        on_stop: Callable[[], None],
        on_open_gui: Callable[[OpenROADGuiStage], None],
        on_view_gds: Callable[[], None],
        on_open_in_editor: Callable[[], None],
        on_use_as_config: Callable[[], None],
        on_open_reports: Callable[[], None],
        on_export_log: Callable[[], None],
        on_preview_layout: Callable[[], None],
        get_config: Callable[[], Optional[AppConfig]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.on_run_stage = on_run_stage
        self.on_run_all = on_run_all
        self.on_stop = on_stop
        self.on_open_gui = on_open_gui
        self.on_view_gds = on_view_gds
        self.on_open_in_editor = on_open_in_editor
        self.on_use_as_config = on_use_as_config
        self.on_open_reports = on_open_reports
        self.on_export_log = on_export_log
        self.on_preview_layout = on_preview_layout
        self.get_config = get_config

        self._node_radius = 18
        self._node_margin = 60
        self._canvas_height = 100
        self._line_y = 50
        self._node_y = 50

        self._stage_states: dict[FlowStage, str] = {stage: "pending" for stage in FULL_PIPELINE}
        self._node_items: dict[FlowStage, dict] = {}  # Stores canvas item IDs
        self._gui_buttons: dict[OpenROADGuiStage, ttk.Button] = {}

        self._running = False
        self._build_ui()

    def _build_ui(self) -> None:
        # Top bar with design info and controls
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        # Design info section
        info_frame = ttk.Frame(top_bar)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        ttk.Label(info_frame, text="Design:", style="Bold.TLabel").pack(side=tk.LEFT)
        self.design_var = tk.StringVar(value="—")
        ttk.Label(info_frame, textvariable=self.design_var, style="Title.TLabel").pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(info_frame, text="Platform:", style="Bold.TLabel").pack(side=tk.LEFT)
        self.platform_var = tk.StringVar(value="—")
        ttk.Label(info_frame, textvariable=self.platform_var).pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(info_frame, text="Config:", style="Bold.TLabel").pack(side=tk.LEFT)
        self.config_var = tk.StringVar(value="—")
        config_label = ttk.Label(info_frame, textvariable=self.config_var, wraplength=300)
        config_label.pack(side=tk.LEFT, padx=(4, 0))
        # Make config path clickable to open in editor
        config_label.bind("<Button-1>", lambda e: self.on_open_in_editor())
        config_label.configure(cursor="hand2")

        # Configure button (dropdown)
        self.configure_btn = ttk.Menubutton(top_bar, text="Configure ▼", style="Flat.TButton")
        self.configure_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Create dropdown menu
        configure_menu = tk.Menu(self.configure_btn, tearoff=0)
        self.configure_btn["menu"] = configure_menu
        configure_menu.add_command(label="Settings…", command=self._on_settings)
        configure_menu.add_separator()
        configure_menu.add_command(label="Open in Editor", command=self.on_open_in_editor)
        configure_menu.add_command(label="Use as Active config.mk", command=self.on_use_as_config)
        configure_menu.add_command(label="View GDS in KLayout", command=self.on_view_gds)
        configure_menu.add_command(label="Open Reports Folder", command=self.on_open_reports)
        configure_menu.add_separator()
        configure_menu.add_command(label="Export Log…", command=self.on_export_log)

        # Run Full Pipeline button
        self.run_all_btn = ttk.Button(
            top_bar,
            text="▶ Run Full Pipeline",
            command=self.on_run_all,
            style="Primary.TButton",
        )
        self.run_all_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Stop button
        self.stop_btn = ttk.Button(
            top_bar,
            text="■ Stop",
            command=self.on_stop,
            style="Danger.TButton",
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Preview Layout button
        ttk.Button(
            top_bar,
            text="Preview Layout",
            command=self.on_preview_layout,
            style="Flat.TButton",
        ).pack(side=tk.LEFT)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(top_bar, textvariable=self.status_var, style="Status.Ready.TLabel")
        status_label.pack(side=tk.RIGHT, padx=(16, 0))

        # Canvas for pipeline visualization
        self.canvas = tk.Canvas(
            self,
            height=self._canvas_height,
            background=BG_DARK,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack(fill=tk.X, pady=(0, 8))

        # Frame for OpenROAD GUI buttons below nodes
        self.gui_button_frame = ttk.Frame(self)
        self.gui_button_frame.pack(fill=tk.X)

        # Bind resize to redraw
        self.canvas.bind("<Configure>", self._on_resize)

        # Draw initial pipeline
        self.after(100, self._draw_pipeline)
        self.after(200, self.create_gui_buttons)

    def _on_settings(self) -> None:
        if self.get_config:
            config = self.get_config()
            if config:
                # This will be handled by the app
                pass

    def _on_resize(self, event: tk.Event) -> None:
        self._draw_pipeline()

    def _draw_pipeline(self) -> None:
        """Draw the pipeline nodes and connecting line."""
        self.canvas.delete("all")
        self._node_items.clear()

        width = self.canvas.winfo_width()
        if width < 200:
            return

        # Calculate node positions
        num_stages = len(FULL_PIPELINE)
        available_width = width - 2 * self._node_margin
        spacing = available_width / (num_stages - 1) if num_stages > 1 else 0

        node_positions = []
        for i, stage in enumerate(FULL_PIPELINE):
            x = self._node_margin + i * spacing
            node_positions.append((stage, x))

        # Draw connecting line
        if len(node_positions) >= 2:
            first_x = node_positions[0][1]
            last_x = node_positions[-1][1]
            self.canvas.create_line(
                first_x, self._line_y,
                last_x, self._line_y,
                fill=BORDER,
                width=2,
                capstyle=tk.ROUND,
                tags="pipeline_line"
            )

        # Draw nodes
        for stage, x in node_positions:
            self._draw_node(stage, x)

    def _draw_node(self, stage: FlowStage, x: float) -> None:
        """Draw a single pipeline node."""
        r = self._node_radius
        state = self._stage_states.get(stage, "pending")
        icon = STAGE_ICONS.get(stage, "●")
        short_name = STAGE_SHORT_NAMES.get(stage, stage.label[:8])

        # Determine colors based on state
        if state == "completed":
            fill = ACCENT_GREEN
            outline = ACCENT_GREEN
            text_color = "#ffffff"
            show_checkmark = True
        elif state == "running":
            fill = ACCENT_BLUE
            outline = ACCENT_BLUE
            text_color = "#ffffff"
            show_checkmark = False
        elif state == "failed":
            fill = ACCENT_RED
            outline = ACCENT_RED
            text_color = "#ffffff"
            show_checkmark = False
        else:  # pending
            fill = BG_ELEVATED
            outline = BORDER
            text_color = FG_SECONDARY
            show_checkmark = False

        # Draw node circle
        circle = self.canvas.create_oval(
            x - r, self._node_y - r,
            x + r, self._node_y + r,
            fill=fill,
            outline=outline,
            width=3 if state == "running" else 2,
            tags=f"node_{stage.name}"
        )

        # Draw icon/text in center
        if state == "completed":
            # Checkmark for completed
            text_id = self.canvas.create_text(
                x, self._node_y,
                text="✓",
                fill=text_color,
                font=("TkDefaultFont", 14, "bold"),
                tags=f"node_{stage.name}"
            )
        else:
            # Stage icon
            text_id = self.canvas.create_text(
                x, self._node_y,
                text=icon,
                fill=text_color,
                font=("TkDefaultFont", 14),
                tags=f"node_{stage.name}"
            )

        # Draw stage label below node
        label_id = self.canvas.create_text(
            x, self._node_y + r + 14,
            text=short_name,
            fill=FG_PRIMARY if state != "pending" else FG_SECONDARY,
            font=("TkDefaultFont", 8),
            tags=f"node_{stage.name}"
        )

        # Store item IDs
        self._node_items[stage] = {
            "circle": circle,
            "icon": text_id,
            "label": label_id,
            "x": x,
        }

        # Bind click events
        for item_id in (circle, text_id, label_id):
            self.canvas.tag_bind(item_id, "<Button-1>", lambda e, s=stage: self._on_node_click(s))
            self.canvas.tag_bind(item_id, "<Enter>", lambda e, s=stage: self._on_node_enter(s))
            self.canvas.tag_bind(item_id, "<Leave>", lambda e: self._on_node_leave())

        # Draw progress arc for running stage
        if state == "running":
            self._draw_progress_arc(stage, x)

    def _draw_progress_arc(self, stage: FlowStage, x: float) -> None:
        """Draw animated progress arc under running node."""
        r = self._node_radius + 6
        # Draw arc (will be animated via after callback)
        arc = self.canvas.create_arc(
            x - r, self._node_y - r,
            x + r, self._node_y + r,
            start=90,
            extent=0,
            outline=ACCENT_BLUE,
            width=3,
            style=tk.ARC,
            tags=f"progress_{stage.name}"
        )
        self._node_items[stage]["progress_arc"] = arc
        self._animate_progress(stage, 0)

    def _animate_progress(self, stage: FlowStage, extent: int) -> None:
        """Animate progress arc."""
        if self._stage_states.get(stage) != "running":
            return
        arc_id = self._node_items.get(stage, {}).get("progress_arc")
        if arc_id:
            try:
                self.canvas.itemconfig(arc_id, extent=extent)
                next_extent = (extent + 10) % 360
                self.after(50, lambda: self._animate_progress(stage, next_extent))
            except tk.TclError:
                pass  # Canvas destroyed

    def _on_node_click(self, stage: FlowStage) -> None:
        """Handle node click - run the stage."""
        if self._stage_states.get(stage) != "running":
            self.on_run_stage(stage)

    def _on_node_enter(self, stage: FlowStage) -> None:
        """Handle mouse enter on node."""
        state = self._stage_states.get(stage, "pending")
        if state == "pending":
            items = self._node_items.get(stage, {})
            circle = items.get("circle")
            if circle:
                self.canvas.itemconfig(circle, outline=ACCENT_BLUE, width=2)

    def _on_node_leave(self) -> None:
        """Handle mouse leave on node."""
        # Redraw to restore original state
        self._draw_pipeline()

    def set_stage_state(self, stage: FlowStage, state: str) -> None:
        """Update the visual state of a stage.

        Args:
            stage: The FlowStage to update
            state: One of "pending", "running", "completed", "failed"
        """
        self._stage_states[stage] = state
        self._draw_pipeline()

        # Also update the GUI button below
        gui_stage = self._flow_to_gui_stage(stage)
        if gui_stage and gui_stage in self._gui_buttons:
            btn = self._gui_buttons[gui_stage]
            if state == "completed":
                btn.configure(state=tk.NORMAL)
            elif state == "running":
                btn.configure(state=tk.NORMAL)
            else:
                btn.configure(state=tk.NORMAL)

    def _flow_to_gui_stage(self, stage: FlowStage) -> Optional[OpenROADGuiStage]:
        """Map FlowStage to OpenROADGuiStage."""
        mapping = {
            FlowStage.SYNTH: OpenROADGuiStage.SYNTH,
            FlowStage.FLOORPLAN: OpenROADGuiStage.FLOORPLAN,
            FlowStage.PLACE: OpenROADGuiStage.PLACE,
            FlowStage.CTS: OpenROADGuiStage.CTS,
            FlowStage.ROUTE: OpenROADGuiStage.ROUTE,
            FlowStage.GDS: OpenROADGuiStage.FINAL,
        }
        return mapping.get(stage)

    def create_gui_buttons(self) -> None:
        """Create OpenROAD GUI buttons below each node."""
        # Clear existing buttons
        for widget in self.gui_button_frame.winfo_children():
            widget.destroy()
        self._gui_buttons.clear()

        # Create buttons for each OpenROAD GUI stage - LARGER SIZE
        for i, gui_stage in enumerate(OPENROAD_GUI_STAGES):
            btn = ttk.Button(
                self.gui_button_frame,
                text=gui_stage.label,
                command=lambda s=gui_stage: self.on_open_gui(s),
                style="Secondary.TButton",
                width=14,  # Increased from 10
            )
            btn.grid(row=0, column=i, padx=6, pady=6, sticky=tk.EW)
            self._gui_buttons[gui_stage] = btn

            # Add tooltip
            from openroad_gui.widgets.flow_panel import ToolTip
            gui_tooltips = {
                OpenROADGuiStage.SYNTH: "Open OpenROAD GUI at synthesis stage\nView synthesized netlist and reports",
                OpenROADGuiStage.FLOORPLAN: "Open OpenROAD GUI at floorplan stage\nInspect macro placement and power grid",
                OpenROADGuiStage.PLACE: "Open OpenROAD GUI at placement stage\nView cell placement and congestion",
                OpenROADGuiStage.CTS: "Open OpenROAD GUI at CTS stage\nInspect clock tree and skew reports",
                OpenROADGuiStage.ROUTE: "Open OpenROAD GUI at routing stage\nView routing layers and DRC violations",
                OpenROADGuiStage.FINAL: "Open OpenROAD GUI at final stage\nFull design view with sign-off checks",
            }
            ToolTip(btn, gui_tooltips.get(gui_stage, gui_stage.label))

        # Configure equal column weights
        for i in range(len(OPENROAD_GUI_STAGES)):
            self.gui_button_frame.columnconfigure(i, weight=1)

    def reset_all(self) -> None:
        """Reset all stages to pending state."""
        for stage in FULL_PIPELINE:
            self._stage_states[stage] = "pending"
        self._draw_pipeline()

    def get_stage_state(self, stage: FlowStage) -> str:
        return self._stage_states.get(stage, "pending")

    def set_design_info(self, design_name: str, platform: str, design_config: str) -> None:
        """Update design info display at the top."""
        self.design_var.set(design_name or "—")
        self.platform_var.set(platform or "—")
        self.config_var.set(design_config or "—")

    def set_status(self, message: str) -> None:
        """Update status label."""
        self.status_var.set(message)

    def set_running(self, running: bool) -> None:
        """Update running state of control buttons."""
        self._running = running
        state = tk.DISABLED if running else tk.NORMAL
        self.run_all_btn.configure(state=state)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)

    def reset_all_stages(self) -> None:
        """Reset all stages to pending state."""
        self.reset_all()