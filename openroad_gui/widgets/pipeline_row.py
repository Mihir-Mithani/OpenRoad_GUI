"""Pipeline stage row visualization using Canvas."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from openroad_gui.config import AppConfig
from openroad_gui.flow_runner import FULL_PIPELINE, FlowStage
from openroad_gui.viewers import OpenROADGuiStage


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

# FlowStage -> OpenROAD GUI viewer stage
_FLOW_TO_GUI = {
    FlowStage.SYNTH: OpenROADGuiStage.SYNTH,
    FlowStage.FLOORPLAN: OpenROADGuiStage.FLOORPLAN,
    FlowStage.PLACE: OpenROADGuiStage.PLACE,
    FlowStage.CTS: OpenROADGuiStage.CTS,
    FlowStage.ROUTE: OpenROADGuiStage.ROUTE,
    FlowStage.GDS: OpenROADGuiStage.FINAL,
}

# 7th node for Signoff (not runnable, status only)
SIGNOFF_KEY = "SIGNOFF"
SIGNOFF_LABEL = "Signoff"

VALID_STATES = ("pending", "running", "completed", "failed", "cancelled")


class PipelineRow(ttk.Frame):
    """Horizontal pipeline visualization with circular nodes connected by a line.

    Layout (see AI_Assisted_EDA_Coordinates.md): a control bar on top, then a canvas
    with 7 evenly spaced 36 px nodes (6 runnable stages + a status-only Signoff node).
    Each runnable node has an "Open GUI" button below it that launches the matching
    OpenROAD GUI viewer stage.
    """

    NODE_RADIUS = 18          # 36 px diameter
    SIDE_MARGIN = 48          # left/right margin to first/last node centre
    NODE_Y = 28               # node centre
    LABEL_OFFSET = 13         # below the circle
    GUI_BUTTON_TOP = 70       # y of the GUI button
    GUI_BUTTON_HEIGHT = 22
    CANVAS_HEIGHT = 98

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
        on_settings: Optional[Callable[[], None]] = None,
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
        self.on_settings = on_settings

        self._stage_states: dict[FlowStage, str] = {stage: "pending" for stage in FULL_PIPELINE}
        self._node_items: dict[str, dict] = {}   # canvas item ids, keyed by stage name
        self._anim_job: Optional[str] = None
        self._anim_extent = 0

        self._running = False
        self._build_ui()

    # ------------------------------------------------------------------ theme
    def _get_theme_colors(self) -> dict:
        """Get current theme colors from ThemeManager."""
        try:
            from openroad_gui.theme import get_theme_manager
            return get_theme_manager().get_colors()
        except RuntimeError:
            from openroad_gui.theme import ThemeManager
            return ThemeManager.DARK

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        # ===== CONTROL BAR =====
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, pady=(0, 2))

        # Row 1: design info (clipped, never the buttons, when the panel is narrow)
        info_frame = ttk.Frame(top_bar)
        info_frame.pack(fill=tk.X)

        ttk.Label(info_frame, text="Design:", style="Bold.TLabel").pack(side=tk.LEFT)
        self.design_var = tk.StringVar(value="—")
        ttk.Label(info_frame, textvariable=self.design_var, style="Title.TLabel").pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(info_frame, text="Platform:", style="Bold.TLabel").pack(side=tk.LEFT)
        self.platform_var = tk.StringVar(value="—")
        ttk.Label(info_frame, textvariable=self.platform_var).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(info_frame, text="Config:", style="Bold.TLabel").pack(side=tk.LEFT)
        self.config_var = tk.StringVar(value="—")
        config_label = ttk.Label(info_frame, textvariable=self.config_var)
        config_label.pack(side=tk.LEFT, padx=(4, 0))
        # Clicking the config path opens it in the editor
        config_label.bind("<Button-1>", lambda e: self.on_open_in_editor())
        config_label.configure(cursor="hand2")

        # Row 2: status on the left, actions on the right
        btn_row = ttk.Frame(top_bar)
        btn_row.pack(fill=tk.X, pady=(6, 0))

        self.run_all_btn = ttk.Button(
            btn_row,
            text="▶ Run Full Flow",
            command=self.on_run_all,
            style="Primary.TButton",
        )
        self.run_all_btn.pack(side=tk.RIGHT, padx=(6, 0))

        self.stop_btn = ttk.Button(
            btn_row,
            text="■ Stop",
            command=self.on_stop,
            style="Danger.TButton",
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=(6, 0))

        ttk.Button(
            btn_row,
            text="Preview Layout",
            command=self.on_preview_layout,
            style="Flat.TButton",
        ).pack(side=tk.RIGHT, padx=(6, 0))

        self.configure_btn = ttk.Menubutton(btn_row, text="Configure")
        self.configure_btn.pack(side=tk.RIGHT, padx=(6, 0))
        configure_menu = tk.Menu(self.configure_btn, tearoff=0)
        self.configure_btn.configure(menu=configure_menu)
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

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(btn_row, textvariable=self.status_var, style="Status.Ready.TLabel")
        self.status_label.pack(side=tk.LEFT)

        # ===== PIPELINE CANVAS =====
        self.canvas = tk.Canvas(
            self,
            height=self.CANVAS_HEIGHT,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas._theme_bg = "BG_APP"
        self.canvas.pack(fill=tk.X, pady=(0, 4))
        self.canvas.bind("<Configure>", self._on_resize)

        self.after(100, self._draw_pipeline)

    def _on_settings(self) -> None:
        if self.on_settings:
            self.on_settings()

    def _on_resize(self, event: tk.Event) -> None:
        self._draw_pipeline()

    # ---------------------------------------------------------------- drawing
    def _draw_pipeline(self) -> None:
        """Draw the 7-node pipeline per AI_Assisted_EDA_Coordinates.md."""
        c = self.canvas
        c.delete("all")
        self._node_items.clear()

        width = c.winfo_width()
        if width < 50:           # not laid out yet
            return

        colors = self._get_theme_colors()
        c.configure(background=colors["BG_APP"])

        nodes: list = list(FULL_PIPELINE) + [SIGNOFF_KEY]
        spacing = max(1.0, (width - 2 * self.SIDE_MARGIN) / (len(nodes) - 1))
        xs = [self.SIDE_MARGIN + i * spacing for i in range(len(nodes))]

        # Connectors behind the nodes: green once the stage on the left is completed
        for i in range(len(nodes) - 1):
            done = i < len(FULL_PIPELINE) and self._stage_states.get(nodes[i]) == "completed"
            c.create_line(
                xs[i], self.NODE_Y, xs[i + 1], self.NODE_Y,
                fill=colors["ACCENT_GREEN"] if done else colors["BORDER"],
                width=2,
                capstyle=tk.ROUND,
            )

        for node, x in zip(nodes, xs):
            self._draw_node(node, x, spacing, colors)

        self._ensure_animation()

    def _node_style(self, node, state: str, colors: dict):
        """Return (fill, outline, icon colour, icon, outline width) for a node state."""
        icon = STAGE_ICONS.get(node, "●")
        if state == "completed":
            return colors["ACCENT_GREEN"], colors["ACCENT_GREEN"], "#ffffff", "✓", 2
        if state == "running":
            return colors["ACCENT_BLUE"], colors["ACCENT_BLUE"], "#ffffff", icon, 3
        if state == "failed":
            return colors["ACCENT_RED"], colors["ACCENT_RED"], "#ffffff", "✗", 2
        if state == "cancelled":
            return colors["BG_ELEVATED"], colors["FG_SECONDARY"], colors["FG_SECONDARY"], "⊘", 2
        if state == "signoff":
            return colors["BG_ELEVATED"], colors["ACCENT_AMBER"], colors["ACCENT_AMBER"], "🛡", 2
        # pending: filled with the card colour so the connector does not show through
        return colors["BG_ELEVATED"], colors["BORDER"], colors["FG_SECONDARY"], icon, 2

    def _draw_node(self, node, x: float, spacing: float, colors: dict) -> None:
        """Draw a single pipeline node with its label and OpenROAD GUI button."""
        c = self.canvas
        is_signoff = node == SIGNOFF_KEY
        key = SIGNOFF_KEY if is_signoff else node.name
        state = "signoff" if is_signoff else self._stage_states.get(node, "pending")
        fill, outline, icon_fg, icon, width = self._node_style(node, state, colors)
        r = self.NODE_RADIUS

        circle = c.create_oval(
            x - r, self.NODE_Y - r, x + r, self.NODE_Y + r,
            fill=fill, outline=outline, width=width,
        )
        icon_id = c.create_text(
            x, self.NODE_Y, text=icon, fill=icon_fg,
            font=("TkDefaultFont", 13, "bold" if state in ("completed", "failed") else "normal"),
        )

        if is_signoff:
            label_color = colors["ACCENT_AMBER"]
        elif state in ("completed", "running", "failed"):
            label_color = colors["FG_PRIMARY"]
        else:
            label_color = colors["FG_SECONDARY"]
        name = SIGNOFF_LABEL if is_signoff else STAGE_SHORT_NAMES.get(node, node.label[:10])
        label_id = c.create_text(
            x, self.NODE_Y + r + self.LABEL_OFFSET, text=name, fill=label_color,
            font=("TkDefaultFont", 9, "bold"),
        )

        items = {
            "circle": circle, "icon": icon_id, "label": label_id, "x": x,
            "state": state, "outline": outline, "outline_width": width,
        }
        self._node_items[key] = items

        btn_w = max(48, min(100, spacing - 10))
        top = self.GUI_BUTTON_TOP
        h = self.GUI_BUTTON_HEIGHT

        if is_signoff:
            # Status-only node: not runnable, no viewer button
            c.create_text(
                x, top + h / 2, text="DRC / LVS", fill=colors["FG_SECONDARY"],
                font=("TkDefaultFont", 8),
            )
            return

        # Click on the node runs the existing stage handler
        for item in (circle, icon_id, label_id):
            c.tag_bind(item, "<Button-1>", lambda e, s=node: self._on_node_click(s))
            c.tag_bind(item, "<Enter>", lambda e, k=key: self._hover_node(k, True))
            c.tag_bind(item, "<Leave>", lambda e, k=key: self._hover_node(k, False))

        # OpenROAD GUI viewer button
        btn_bg = c.create_rectangle(
            x - btn_w / 2, top, x + btn_w / 2, top + h,
            fill=colors["BG_ELEVATED"], outline=colors["BORDER"], width=1,
        )
        btn_text = c.create_text(
            x, top + h / 2, text="Open GUI", fill=colors["FG_PRIMARY"],
            font=("TkDefaultFont", 8),
        )
        items["gui_bg"] = btn_bg
        items["gui_text"] = btn_text
        for item in (btn_bg, btn_text):
            c.tag_bind(item, "<Button-1>", lambda e, s=node: self._on_gui_click(s))
            c.tag_bind(item, "<Enter>", lambda e, k=key: self._hover_gui(k, True))
            c.tag_bind(item, "<Leave>", lambda e, k=key: self._hover_gui(k, False))

        # Animated ring for the running stage
        if state == "running":
            ar = r + 6
            items["arc"] = c.create_arc(
                x - ar, self.NODE_Y - ar, x + ar, self.NODE_Y + ar,
                start=90, extent=self._anim_extent or 90,
                outline=colors["ACCENT_BLUE"], width=3, style=tk.ARC,
            )

    # ---------------------------------------------------------------- hover
    def _hover_node(self, key: str, enter: bool) -> None:
        items = self._node_items.get(key)
        if not items:
            return
        self.canvas.configure(cursor="hand2" if enter else "")
        colors = self._get_theme_colors()
        if enter and items["state"] == "pending":
            self.canvas.itemconfig(items["circle"], outline=colors["ACCENT_BLUE"])
        else:
            self.canvas.itemconfig(items["circle"], outline=items["outline"])

    def _hover_gui(self, key: str, enter: bool) -> None:
        items = self._node_items.get(key)
        if not items or "gui_bg" not in items:
            return
        colors = self._get_theme_colors()
        self.canvas.configure(cursor="hand2" if enter else "")
        self.canvas.itemconfig(items["gui_bg"], fill=colors["BG_HOVER"] if enter else colors["BG_ELEVATED"])

    # ------------------------------------------------------------ animation
    def _ensure_animation(self) -> None:
        if self._anim_job is None and any(s == "running" for s in self._stage_states.values()):
            self._anim_job = self.after(60, self._tick)

    def _tick(self) -> None:
        self._anim_job = None
        if not any(s == "running" for s in self._stage_states.values()):
            return
        self._anim_extent = (self._anim_extent + 14) % 360 or 14
        for items in self._node_items.values():
            arc = items.get("arc")
            if arc:
                try:
                    self.canvas.itemconfig(arc, extent=self._anim_extent)
                except tk.TclError:
                    return
        self._anim_job = self.after(60, self._tick)

    def destroy(self) -> None:
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except tk.TclError:
                pass
            self._anim_job = None
        super().destroy()

    # --------------------------------------------------------------- clicks
    def _on_node_click(self, stage) -> None:
        """Handle node click - run the stage (ignored while a flow is running)."""
        if stage == SIGNOFF_KEY or self._running:
            return
        if self._stage_states.get(stage) != "running":
            self.on_run_stage(stage)

    def _on_gui_click(self, stage: FlowStage) -> None:
        """Open the OpenROAD GUI viewer for the stage (callback expects the enum)."""
        gui_stage = self._flow_to_gui_stage(stage)
        if gui_stage is not None:
            self.on_open_gui(gui_stage)

    def _flow_to_gui_stage(self, stage: FlowStage) -> Optional[OpenROADGuiStage]:
        """Map FlowStage to OpenROADGuiStage."""
        return _FLOW_TO_GUI.get(stage)

    # ------------------------------------------------------------ public API
    def set_stage_state(self, stage, state: str) -> None:
        """Update the visual state of a stage (FlowStage or its name)."""
        if isinstance(stage, str):
            try:
                stage = FlowStage[stage]
            except KeyError:
                return
        if stage not in self._stage_states:
            return
        self._stage_states[stage] = state
        self._draw_pipeline()

    def reset_all(self) -> None:
        """Reset all stages to pending state."""
        for stage in FULL_PIPELINE:
            self._stage_states[stage] = "pending"
        self._draw_pipeline()

    def reset_all_stages(self) -> None:
        """Reset all stages to pending state."""
        self.reset_all()

    def get_stage_state(self, stage: FlowStage) -> str:
        return self._stage_states.get(stage, "pending")

    def set_design_info(self, design_name: str, platform: str, design_config: str) -> None:
        """Update design info display at the top."""
        self.design_var.set(design_name or "—")
        self.platform_var.set(platform or "—")
        self.config_var.set(design_config or "—")

    def set_status(self, message: str) -> None:
        """Update status label (colour follows the message)."""
        self.status_var.set(message)
        lowered = message.lower()
        if "fail" in lowered or "error" in lowered:
            style = "Status.Error.TLabel"
        elif lowered.startswith(("running", "rendering")) or "in progress" in lowered:
            style = "Status.Running.TLabel"
        else:
            style = "Status.Ready.TLabel"
        self.status_label.configure(style=style)

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
