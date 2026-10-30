"""Pipeline stage row visualization using Canvas."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from openroad_gui.config import AppConfig
from openroad_gui.flow_runner import FULL_PIPELINE, FlowStage
from openroad_gui.viewers import OPENROAD_GUI_STAGES, OpenROADGuiStage


# Stage icons (Unicode symbols)
STAGE_ICONS = {
    FlowStage.SYNTH: "⟳",       # Waveform/synthesis
    FlowStage.FLOORPLAN: "📐",    # Ruler/triangle for floorplan
    FlowStage.PLACE: "📦",       # Box for placement
    FlowStage.CTS: "⏱",         # Clock for CTS
    FlowStage.ROUTE: "🔀",       # Route/switch for routing
    FlowStage.GDS: "💾",         # Disk for GDS
}

STAGE_SHORT_NAMES = {
    FlowStage.SYNTH: "Synthesis",
    FlowStage.FLOORPLAN: "Floorplan",
    FlowStage.PLACE: "Placement",
    FlowStage.CTS: "CTS",
    FlowStage.ROUTE: "Routing",
    FlowStage.GDS: "GDSII",
}

# 7th node for Signoff (not runnable, status only)
SIGNOFF_LABEL = "Signoff"


class PipelineRow(ttk.Frame):
    """Horizontal pipeline visualization with circular nodes connected by line.

    Matches AI_Assisted_EDA_Coordinates.md specification:
    - Panel: (223, 103, 896, 150)
    - 7 nodes, 36px circles, evenly spaced
    - OpenROAD GUI buttons drawn on canvas below each node
    """

    NODE_RADIUS = 18  # 36px diameter
    NODE_MARGIN = 40  # Left/right margin
    CANVAS_HEIGHT = 180  # Enough for nodes + labels + GUI buttons
    NODE_Y = 85  # Center Y for nodes (matches spec y=178 with header offset)
    LINE_Y = 85  # Line through center of nodes
    LABEL_Y_OFFSET = 42  # Distance from node center to label
    GUI_BUTTON_Y_OFFSET = 80  # Distance from node center to GUI button top
    GUI_BUTTON_HEIGHT = 28
    GUI_BUTTON_WIDTH = 100


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
        on_make_clean: Callable[[], None],
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
        self.on_make_clean = on_make_clean
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

    def _get_theme_colors(self) -> dict:
        """Get current theme colors from ThemeManager."""
        try:
            from openroad_gui.theme import get_theme_manager
            return get_theme_manager().get_colors()
        except RuntimeError:
            # Fallback to dark theme defaults
            return {
                "BG_DARK": "#0A1320",
                "BG_PANEL": "#101C2B",
                "BG_ELEVATED": "#142337",
                "BG_HOVER": "#1A2A3F",
                "BORDER": "#26384F",
                "FG_PRIMARY": "#F0F5FF",
                "FG_SECONDARY": "#A7B7CD",
                "ACCENT_BLUE": "#2D7DFF",
                "ACCENT_BLUE_HOVER": "#4DA3FF",
                "ACCENT_GREEN": "#39D785",
                "ACCENT_GREEN_HOVER": "#56E096",
                "ACCENT_AMBER": "#FFC857",
                "ACCENT_RED": "#FF667A",
                "ACCENT_RED_HOVER": "#FF8A8A",
                "ACCENT_PURPLE": "#C084FC",
                "SELECTION_BG": "#264F78",
                "SELECTION_FG": "#FFFFFF",
            }

    def _build_ui(self) -> None:
        # ===== HEADER / TOP BAR =====
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, pady=(0, 8))
        # Ensure top bar has minimum height
        top_bar.pack_propagate(False)
        top_bar.configure(height=44)

        # Design info section
        info_frame = ttk.Frame(top_bar)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16), pady=8)

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

        # Status label (rightmost)
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(top_bar, textvariable=self.status_var, style="Status.Ready.TLabel")
        status_label.pack(side=tk.RIGHT, padx=(16, 0), pady=8)

        # Stop button (right of Run Full Flow)
        self.stop_btn = ttk.Button(
            top_bar,
            text="■ Stop",
            command=self.on_stop,
            style="Danger.TButton",
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=4)

        # Run Full Pipeline button (top-right, primary)
        self.run_all_btn = ttk.Button(
            top_bar,
            text="▶ Run Full Flow",
            command=self.on_run_all,
            style="Primary.TButton",
        )
        self.run_all_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=4)

        # Preview Layout button
        ttk.Button(
            top_bar,
            text="Preview Layout",
            command=self.on_preview_layout,
            style="Flat.TButton",
        ).pack(side=tk.RIGHT, padx=(0, 8), pady=4)

        # Configure button (dropdown)
        self.configure_btn = tk.Menubutton(top_bar, text="Configure ▼", relief=tk.FLAT, bd=0)
        self.configure_btn.pack(side=tk.LEFT, padx=(0, 8), pady=4)

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
        configure_menu.add_command(label="Make Clean", command=self._on_make_clean)
        configure_menu.add_separator()
        configure_menu.add_command(label="Export Log…", command=self.on_export_log)

        # Canvas for pipeline visualization - transparent background
        self.canvas = tk.Canvas(
            self,
            height=self._canvas_height,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack(fill=tk.X, pady=(0, 8))

        # Bind resize to redraw
        self.canvas.bind("<Configure>", self._on_resize)

        # Draw initial pipeline
        self.after(100, self._draw_pipeline)

    def _on_settings(self) -> None:
        if self.get_config:
            config = self.get_config()
            if config:
                # This will be handled by the app
                pass

    def _on_resize(self, event: tk.Event) -> None:
        self._draw_pipeline()

    def _draw_pipeline(self) -> None:
        """Draw the 7-node pipeline per AI_Assisted_EDA_Coordinates.md spec."""
        self.canvas.delete("all")
        self._node_items.clear()

        width = self.canvas.winfo_width()
        if width < 800:
            return

        colors = self._get_theme_colors()

        # 7 nodes per spec: 6 runnable stages + 1 Signoff status node
        self._all_stages = list(FULL_PIPELINE) + ["SIGNOFF"]
        num_nodes = 7

        # Calculate positions proportional to canvas width
        # Spec margins: 64px from panel edges
        left_margin = 64
        right_margin = 64
        available = width - left_margin - right_margin
        spacing = available / 6  # 6 intervals between 7 nodes

        node_positions = []
        for i in range(num_nodes):
            x = left_margin + i * spacing
            if i < 6:
                stage = FULL_PIPELINE[i]
            else:
                stage = "SIGNOFF"
            node_positions.append((stage, x))

        # Draw connecting line (behind nodes)
        first_x = node_positions[0][1]
        last_x = node_positions[-1][1]
        self.canvas.create_line(
            first_x, self.LINE_Y,
            last_x, self.LINE_Y,
            fill=colors["BORDER"],
            width=2,
            capstyle=tk.ROUND,
            tags="pipeline_line"
        )

        # Draw nodes (circle, label, GUI button)
        for stage, x in node_positions:
            self._draw_node(stage, x, colors)

    def _draw_node(self, stage, x: float, colors: dict) -> None:
        """Draw a single pipeline node with label and GUI button below."""
        r = self.NODE_RADIUS

        if stage == "SIGNOFF":
            state = "signoff"
            short_name = "Signoff"
            gui_label = "Signoff"
        else:
            state = self._stage_states.get(stage, "pending")
            short_name = STAGE_SHORT_NAMES.get(stage, stage.label[:8])
            gui_stage_map = {
                FlowStage.SYNTH: "Synthesis",
                FlowStage.FLOORPLAN: "Floorplan",
                FlowStage.PLACE: "Placement",
                FlowStage.CTS: "CTS",
                FlowStage.ROUTE: "Routing",
                FlowStage.GDS: "GDSII",
            }
            gui_label = gui_stage_map.get(stage, short_name)

        # Determine colors based on state
        if state == "completed":
            fill = colors["ACCENT_GREEN"]
            outline = colors["ACCENT_GREEN"]
            text_color = "#ffffff"
            show_checkmark = True
        elif state == "running":
            fill = colors["ACCENT_BLUE"]
            outline = colors["ACCENT_BLUE"]
            text_color = "#ffffff"
            show_checkmark = False
        elif state == "failed":
            fill = colors["ACCENT_RED"]
            outline = colors["ACCENT_RED"]
            text_color = "#ffffff"
            show_checkmark = False
        elif state == "signoff":
            fill = colors["BG_ELEVATED"]
            outline = colors["ACCENT_AMBER"]
            text_color = colors["ACCENT_AMBER"]
            show_checkmark = False
        else:  # pending - transparent fill, only outline
            fill = ""
            outline = colors["BORDER"]
            text_color = colors["FG_SECONDARY"]
            show_checkmark = False

        # Draw node circle (36px diameter = 18px radius)
        circle = self.canvas.create_oval(
            x - self.NODE_RADIUS, self.NODE_Y - self.NODE_RADIUS,
            x + self.NODE_RADIUS, self.NODE_Y + self.NODE_RADIUS,
            fill=fill,
            outline=outline,
            width=3 if state == "running" else 2,
            tags=f"node_{stage}"
        )

        # Draw icon/text in center
        if state == "completed":
            text_id = self.canvas.create_text(
                x, self.NODE_Y,
                text="✓",
                fill=text_color,
                font=("TkDefaultFont", 14, "bold"),
                tags=f"node_{stage}"
            )
        elif state == "signoff":
            text_id = self.canvas.create_text(
                x, self.NODE_Y,
                text="🛡",
                fill=text_color,
                font=("TkDefaultFont", 14),
                tags=f"node_{stage}"
            )
        else:
            icon = STAGE_ICONS.get(stage, "●")
            text_id = self.canvas.create_text(
                x, self.NODE_Y,
                text=icon,
                fill=text_color,
                font=("TkDefaultFont", 14),
                tags=f"node_{stage}"
            )

        # Draw stage label below node
        label_y = self.NODE_Y + self.NODE_RADIUS + 14
        label_id = self.canvas.create_text(
            x, label_y,
            text=short_name,
            fill=colors["FG_PRIMARY"] if state not in ("pending", "signoff") else (colors["ACCENT_AMBER"] if state == "signoff" else colors["FG_SECONDARY"]),
            font=("TkDefaultFont", 9, "bold"),
            tags=f"node_{stage}"
        )

        # Draw OpenROAD GUI button below label
        gui_button_y = self.NODE_Y + 80
        gui_button_h = 28
        gui_button_w = 100

        btn_bg = self.canvas.create_rectangle(
            x - gui_button_w//2, gui_button_y,
            x + gui_button_w//2, gui_button_y + 28,
            fill=colors["BG_ELEVATED"],
            outline=colors["BORDER"],
            width=1,
            tags=f"gui_btn_{stage}"
        )

        btn_text = self.canvas.create_text(
            x, gui_button_y + 14,
            text=gui_label,
            fill=colors["FG_PRIMARY"],
            font=("TkDefaultFont", 8, "bold"),
            tags=f"gui_btn_{stage}"
        )

        # Store item IDs
        stage_key = stage if isinstance(stage, str) else stage.name
        self._node_items[stage_key] = {
            "circle": circle,
            "icon": text_id,
            "label": label_id,
            "gui_bg": btn_bg,
            "gui_text": btn_text,
            "x": x,
        }

        # Bind click events for node (runnable stages only)
        if stage != "SIGNOFF":
            for item_id in (circle, text_id, label_id):
                self.canvas.tag_bind(item_id, "<Button-1>", lambda e, s=stage: self._on_node_click(s))
                self.canvas.tag_bind(item_id, "<Enter>", lambda e, s=stage: self._on_node_enter(s))
                self.canvas.tag_bind(item_id, "<Leave>", lambda e: self._on_node_leave())

        # Bind click events for GUI button
        gui_tag = f"gui_btn_{stage_key if isinstance(stage, str) else stage.name}"
        if stage != "SIGNOFF":
            gui_stage_map = {
                FlowStage.SYNTH: "Synthesis",
                FlowStage.FLOORPLAN: "Floorplan",
                FlowStage.PLACE: "Placement",
                FlowStage.CTS: "CTS",
                FlowStage.ROUTE: "Routing",
                FlowStage.GDS: "GDSII",
            }
            gui_label_text = gui_stage_map.get(stage, short_name)
            self.canvas.tag_bind(gui_tag, "<Button-1>", lambda e, l=gui_label_text: self.on_open_gui(l))
            self.canvas.tag_bind(gui_tag, "<Enter>", lambda e: self._on_gui_button_enter(stage_key))
            self.canvas.tag_bind(gui_tag, "<Leave>", lambda e: self._on_gui_button_leave())

        # Draw progress arc for running stage
        if state == "running":
            self._draw_progress_arc(stage_key, x, colors)

    def _on_node_enter(self, stage) -> None:
        """Handle mouse enter on node."""
        stage_key = stage if isinstance(stage, str) else stage.name
        state = self._stage_states.get(stage, "pending")
        if state == "pending":
            items = self._node_items.get(stage_key, {})
            circle = items.get("circle")
            if circle:
                colors = self._get_theme_colors()
                self.canvas.itemconfig(circle, outline=colors["ACCENT_BLUE"], width=2)

    def _on_node_leave(self) -> None:
        """Handle mouse leave on node."""
        self._draw_pipeline()

    def _on_gui_button_enter(self, stage_key) -> None:
        """Handle mouse enter on GUI button."""
        items = self._node_items.get(stage_key, {})
        btn_bg = items.get("gui_bg")
        if btn_bg:
            colors = self._get_theme_colors()
            self.canvas.itemconfig(btn_bg, fill=colors["BG_HOVER"])

    def _on_gui_button_leave(self) -> None:
        """Handle mouse leave on GUI button."""
        self._draw_pipeline()

    def _draw_progress_arc(self, stage_key: str, x: float, colors: dict) -> None:
        """Draw animated progress arc under running node."""
        r = self.NODE_RADIUS + 6
        arc = self.canvas.create_arc(
            x - r, self.NODE_Y - r,
            x + r, self.NODE_Y + r,
            start=90,
            extent=0,
            outline=colors["ACCENT_BLUE"],
            width=3,
            style=tk.ARC,
            tags=f"progress_{stage_key}"
        )
        self._node_items[stage_key]["progress_arc"] = arc
        self._animate_progress(stage_key, 0)

    def _animate_progress(self, stage_key: str, extent: int) -> None:
        """Animate progress arc."""
        if self._stage_states.get(stage_key) != "running":
            return
        arc_id = self._node_items.get(stage_key, {}).get("progress_arc")
        if arc_id:
            try:
                self.canvas.itemconfig(arc_id, extent=extent)
                next_extent = (extent + 10) % 360
                self.after(50, lambda: self._animate_progress(stage_key, next_extent))
            except tk.TclError:
                pass  # Canvas destroyed

    def _on_node_click(self, stage: FlowStage) -> None:
        """Handle node click - run the stage."""
        if self._stage_states.get(stage) != "running":
            self.on_run_stage(stage)

    def _on_node_enter(self, stage) -> None:
        """Handle mouse enter on node."""
        stage_key = stage if isinstance(stage, str) else stage.name
        state = self._stage_states.get(stage, "pending")
        if state == "pending":
            items = self._node_items.get(stage_key, {})
            circle = items.get("circle")
            if circle:
                colors = self._get_theme_colors()
                self.canvas.itemconfig(circle, outline=colors["ACCENT_BLUE"], width=2)

    def _on_node_leave(self) -> None:
        """Handle mouse leave on node."""
        self._draw_pipeline()

    def _on_gui_button_enter(self, stage_key) -> None:
        """Handle mouse enter on GUI button."""
        items = self._node_items.get(stage_key, {})
        btn_bg = items.get("gui_bg")
        if btn_bg:
            colors = self._get_theme_colors()
            self.canvas.itemconfig(btn_bg, fill=colors["BG_HOVER"])

    def _on_gui_button_leave(self) -> None:
        """Handle mouse leave on GUI button."""
        self._draw_pipeline()

    def _draw_progress_arc(self, stage_key: str, x: float, colors: dict) -> None:
        """Draw animated progress arc under running node."""
        r = self.NODE_RADIUS + 6
        arc = self.canvas.create_arc(
            x - r, self.NODE_Y - r,
            x + r, self.NODE_Y + r,
            start=90,
            extent=0,
            outline=colors["ACCENT_BLUE"],
            width=3,
            style=tk.ARC,
            tags=f"progress_{stage_key}"
        )
        self._node_items[stage_key]["progress_arc"] = arc
        self._animate_progress(stage_key, 0)

    def _animate_progress(self, stage_key: str, extent: int) -> None:
        """Animate progress arc."""
        if self._stage_states.get(stage_key) != "running":
            return
        arc_id = self._node_items.get(stage_key, {}).get("progress_arc")
        if arc_id:
            try:
                self.canvas.itemconfig(arc_id, extent=extent)
                next_extent = (extent + 10) % 360
                self.after(50, lambda: self._animate_progress(stage_key, next_extent))
            except tk.TclError:
                pass  # Canvas destroyed

    def _on_node_click(self, stage) -> None:
        """Handle node click - run the stage."""
        if stage != "SIGNOFF" and self._stage_states.get(stage) != "running":
            self.on_run_stage(stage)

    def _on_node_enter(self, stage) -> None:
        """Handle mouse enter on node."""
        stage_key = stage if isinstance(stage, str) else stage.name
        state = self._stage_states.get(stage, "pending")
        if state == "pending":
            items = self._node_items.get(stage_key, {})
            circle = items.get("circle")
            if circle:
                colors = self._get_theme_colors()
                self.canvas.itemconfig(circle, outline=colors["ACCENT_BLUE"], width=2)

    def _on_node_leave(self) -> None:
        """Handle mouse leave on node."""
        self._draw_pipeline()

    def _on_gui_button_enter(self, stage_key) -> None:
        """Handle mouse enter on GUI button."""
        items = self._node_items.get(stage_key, {})
        btn_bg = items.get("gui_bg")
        if btn_bg:
            colors = self._get_theme_colors()
            self.canvas.itemconfig(btn_bg, fill=colors["BG_HOVER"])

    def _on_gui_button_leave(self) -> None:
        """Handle mouse leave on GUI button."""
        self._draw_pipeline()

    def set_stage_state(self, stage, state: str) -> None:
        """Update the visual state of a stage."""
        stage_key = stage if isinstance(stage, str) else stage.name
        self._stage_states[stage_key] = state
        self._draw_pipeline()

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

    def _on_make_clean(self) -> None:
        """Trigger make clean via app callback."""
        if self.on_make_clean:
            self.on_make_clean()

    def set_running(self, running: bool) -> None:
        """Update running state of control buttons."""
        self._running = running
        state = tk.DISABLED if running else tk.NORMAL
        self.run_all_btn.configure(state=state)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)

    def reset_all_stages(self) -> None:
        """Reset all stages to pending state."""
        self.reset_all()