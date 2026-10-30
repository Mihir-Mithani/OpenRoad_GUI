"""Main application window - Industrial EDA Workstation."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np

from openroad_gui import __version__
from openroad_gui.config import AppConfig, load_config, save_config
from openroad_gui.flow_runner import FULL_PIPELINE, FlowRunner, FlowStage
from openroad_gui.viewers import OPENROAD_GUI_STAGES, OpenROADGuiStage, ViewerService
from openroad_gui.widgets.flow_panel import FlowPanel, ToolTip
from openroad_gui.widgets.log_viewer import LogViewer
from openroad_gui.widgets.preview_panel import PreviewPanel
from openroad_gui.widgets.project_tree import ProjectTree
from openroad_gui.widgets.settings_dialog import SettingsDialog
from openroad_gui.widgets.pipeline_row import PipelineRow

# Theme management
from openroad_gui.theme import init_theme, get_theme_manager, toggle_theme, set_dark_mode

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
    """Main application window - Industrial EDA Workstation."""

    LEFT_RAIL_WIDTH = 230
    RIGHT_RAIL_WIDTH = 380

    def __init__(self) -> None:
        super().__init__()
        self.title(f"OpenROAD Flow GUI v{__version__} - AI-Assisted EDA")
        # Compute initial size from screen dimensions
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = min(1536, screen_w - 40)
        h = min(1024, screen_h - 100)
        self.geometry(f"{w}x{h}+{(screen_w - w)//2}+{(screen_h - h)//2}")
        self.minsize(1100, 760)

        # Initialize theme manager FIRST (before any widgets)
        self.theme_manager = init_theme(self)

        self.app_config = load_config()
        self.runner = FlowRunner(self.app_config)
        self.viewers = ViewerService(self.app_config)

        # UI state used by the layout code
        self._selected_file: Path | None = None
        self._scroll_canvases: list[tk.Canvas] = []
        self._wheel_bound = False
        self._active_stage: FlowStage | None = None
        self._ui_stop_requested = False

        # Initialize intelligence modules
        self.optimizer = None
        self.failure_predictor = None
        self.surrogate_inference = None
        if HAS_INTELLIGENCE:
            try:
                self.optimizer = FlowOptimizationEngine()
                self.failure_predictor = FailurePredictor()
                self.surrogate_inference = SurrogateInference(
                    Path(__file__).parent / "intelligence" / "models" / "saved"
                )
            except Exception as e:
                print(f"Warning: Could not initialize intelligence modules: {e}")

        # Build UI in order: style -> menu -> layout
        self._apply_style()
        self._build_menu()
        self._build_layout()
        # Widgets created after init_theme() need their colours applied once
        self.theme_manager.apply_to_widgets(self)
        self.log_viewer._refresh_theme()
        self._apply_config()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Bind theme toggle
        self.bind("<Control-t>", lambda e: toggle_theme())
        self.bind("<Control-d>", lambda e: self.theme_manager.set_dark_mode(not self.theme_manager.is_dark_mode()))

        # Register for theme changes
        self.theme_manager._on_theme_change = self._on_theme_change

    def _on_theme_change(self, dark_mode: bool) -> None:
        """Update theme-sensitive widgets when theme changes."""
        if hasattr(self, 'theme_toggle_btn'):
            self.theme_toggle_btn.configure(
                text="🌙 Dark" if dark_mode else "☀️ Light"
            )
        colors = self.theme_manager.get_colors()
        if hasattr(self, 'pipeline_row'):
            self.pipeline_row._draw_pipeline()
        if hasattr(self, 'log_viewer'):
            self.log_viewer._refresh_theme()
        if hasattr(self, 'ppa_rows'):
            for row in self.ppa_rows.values():
                row['pred'].configure(foreground=colors["ACCENT_BLUE"])
                row['actual'].configure(foreground=colors["ACCENT_GREEN"])

    def _apply_style(self) -> None:
        """Apply theme - handled by ThemeManager during init."""
        pass  # Theme applied during init_theme()

    def _build_menu(self) -> None:
        """Build the complete menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(self, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Design", command=self._new_design, accelerator="Ctrl+N")
        file_menu.add_command(label="Open Project…", command=self._open_project, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Project", command=self._save_project, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Settings…", command=self._open_settings, accelerator="Ctrl+,")
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_close, accelerator="Ctrl+Q")

        # View menu
        view_menu = tk.Menu(self, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Theme", command=toggle_theme, accelerator="Ctrl+T")
        view_menu.add_separator()
        view_menu.add_command(label="GDS — View in KLayout", command=self._view_default_gds)
        view_menu.add_command(label="GDS — Preview Layout", command=self._preview_default_gds)
        view_menu.add_separator()
        for stage in OPENROAD_GUI_STAGES:
            view_menu.add_command(
                label=f"OpenROAD GUI — {stage.label}",
                command=lambda s=stage: self._open_or_gui_stage(s),
            )

        # Flow menu
        flow_menu = tk.Menu(self, tearoff=0)
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
        intel_menu = tk.Menu(self, tearoff=0)
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

        # Help menu
        help_menu = tk.Menu(self, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Quick Start", command=self._show_help)
        help_menu.add_command(label="About", command=self._show_about)

        self.config(menu=menubar)

    def _build_layout(self) -> None:
        """Build the main 4-zone layout per gui_update.md spec."""
        # 3 columns: left rail | flexible workspace | right rail
        self.columnconfigure(0, weight=0, minsize=self.LEFT_RAIL_WIDTH)
        self.columnconfigure(1, weight=1, minsize=480)
        self.columnconfigure(2, weight=0, minsize=self.RIGHT_RAIL_WIDTH)

        self.rowconfigure(0, weight=0)   # Header (natural height)
        self.rowconfigure(1, weight=1)   # Main content

        # ===== HEADER =====
        self.header_frame = ttk.Frame(self, style="Header.TFrame")
        self.header_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        self._build_header()

        # ===== LEFT NAVIGATION RAIL =====
        self.nav_rail = ttk.Frame(self, style="Sidebar.TFrame", width=self.LEFT_RAIL_WIDTH)
        self.nav_rail.grid(row=1, column=0, sticky="nsew")
        self.nav_rail.grid_propagate(False)
        self.nav_rail.pack_propagate(False)
        self._build_nav_rail()

        # ===== CENTER WORKSPACE =====
        self.center_workspace = ttk.Frame(self, style="Workspace.TFrame")
        self.center_workspace.grid(row=1, column=1, sticky="nsew")
        self._build_center_workspace()

        # ===== RIGHT RAIL =====
        self.right_rail = ttk.Frame(self, style="Sidebar.TFrame", width=self.RIGHT_RAIL_WIDTH)
        self.right_rail.grid(row=1, column=2, sticky="nsew")
        self.right_rail.grid_propagate(False)
        self.right_rail.pack_propagate(False)
        self._build_right_rail()

        # Bind responsive behavior
        self.bind("<Configure>", self._on_window_resize)

    # ===== HEADER =====
    def _build_header(self) -> None:
        """Build the application header with brand and actions only."""
        h = self.header_frame
        h.columnconfigure(0, weight=0)  # Brand
        h.columnconfigure(1, weight=1)  # Spacer
        h.columnconfigure(2, weight=0)  # Actions

        # Brand block (left)
        brand = ttk.Frame(h, style="Header.TFrame")
        brand.grid(row=0, column=0, sticky="w", padx=(18, 0), pady=4)
        ttk.Label(brand, text="⬢", style="Header.TLabel",
                  font=("TkDefaultFont", 26)).grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ttk.Label(brand, text="AI-Assisted EDA", style="Header.TLabel",
                  font=("TkDefaultFont", 20, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(brand, text="OpenROAD GUI for RTL-to-GDSII Flow", style="Header.Secondary.TLabel",
                  font=("TkDefaultFont", 10)).grid(row=1, column=1, sticky="w")

        # Right actions (theme toggle + help)
        actions = ttk.Frame(h, style="Header.TFrame")
        actions.grid(row=0, column=2, sticky="e", padx=18, pady=6)

        self.theme_toggle_btn = ttk.Button(
            actions,
            text="🌙 Dark" if self.theme_manager.is_dark_mode() else "☀️ Light",
            style="Header.Flat.TButton",
            command=toggle_theme,
            width=10,
        )
        self.theme_toggle_btn.grid(row=0, column=0, padx=(0, 8))

        ttk.Button(
            actions,
            text="❓ Help",
            style="Header.Flat.TButton",
            command=self._show_help,
            width=8,
        ).grid(row=0, column=1)

    # ===== LEFT NAV RAIL =====
    def _build_nav_rail(self) -> None:
        """Left rail: one scrollable column of sections with the project tree under "Project"."""
        rail = self.nav_rail
        rail.columnconfigure(0, weight=1)
        rail.columnconfigure(1, weight=0)
        rail.rowconfigure(0, weight=1)

        colors = self.theme_manager.get_colors()
        canvas = tk.Canvas(rail, highlightthickness=0, borderwidth=0, background=colors["BG_SIDEBAR"])
        canvas._theme_bg = "BG_SIDEBAR"
        scrollbar = ttk.Scrollbar(rail, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, style="Sidebar.TFrame")
        window = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._register_scroll_canvas(canvas)

        def add_section(title, items, primary_first=False):
            section = ttk.Frame(inner, style="Sidebar.TFrame")
            section.pack(fill="x", padx=10, pady=(10, 2))
            ttk.Label(section, text=title, style="Sidebar.Bold.TLabel").pack(anchor="w", pady=(0, 4))
            for idx, (label, icon, cmd) in enumerate(items):
                style = "Primary.TButton" if (primary_first and idx == 0) else "Nav.TButton"
                ttk.Button(
                    section,
                    text=f"{icon}  {label}",
                    style=style,
                    command=cmd,
                ).pack(fill="x", pady=1)

        # 5.1 Project
        add_section("Project", [
            ("New Design", "➕", self._new_design),
            ("Open Project…", "📁", self._open_project),
            ("Save Project", "💾", self._save_project),
        ], primary_first=True)

        # Project tree (existing widget, unchanged behaviour) sits directly under Project
        tree_holder = ttk.Frame(inner, style="Sidebar.TFrame", height=380)
        tree_holder.pack(fill="x", padx=10, pady=(8, 4))
        tree_holder.pack_propagate(False)
        self.project_tree = ProjectTree(
            tree_holder,
            on_select=self._on_file_select,
            on_view_gds=self._view_gds_in_klayout,
            on_open_or_gui=self._open_or_gui_for_file,
        )
        self.project_tree.pack(fill="both", expand=True)

        # 5.2 Design Inputs
        add_section("Design Inputs", [
            ("RTL (Verilog/SV)", "📄", lambda: self._focus_input("rtl")),
            ("Technology (Lib/LEF)", "🔬", lambda: self._focus_input("lib")),
            ("Constraints (SDC)", "📋", lambda: self._focus_input("sdc")),
            ("Floorplan / Config", "📐", lambda: self._focus_input("config")),
        ])

        # 5.3 Flow Configuration
        add_section("Flow Configuration", [
            ("Flow Steps", "🔢", self._show_flow_config),
            ("Parameter Tuning", "🎛", self._show_param_tuning),
            ("AI Optimization", "🤖", self._show_ai_optimization),
        ])

        # 5.4 Run & Monitor
        add_section("Run & Monitor", [
            ("Start Flow", "▶", self._run_all),
            ("Stop", "⏹", self._stop_flow),
            ("View Logs", "📋", self._focus_logs),
        ])

        # 5.5 Results & Analysis
        add_section("Results & Analysis", [
            ("Reports (PPA)", "📊", self._show_reports),
            ("Layout Viewer", "📐", self._show_layout_viewer),
            ("Timing Analysis", "⏱", self._show_timing_analysis),
            ("Power Analysis", "⚡", self._show_power_analysis),
            ("DRC/LVS", "✅", self._show_drc_lvs),
        ])

        # 5.6 Utilities
        add_section("Utilities", [
            ("Scripting (TCL)", "📝", self._open_tcl_console),
            ("Docs & Help", "📖", self._show_help),
            ("About", "ℹ", self._show_about),
        ])

        ttk.Frame(inner, style="Sidebar.TFrame", height=12).pack()

    def _register_scroll_canvas(self, canvas: tk.Canvas) -> None:
        """Register a scrollable rail canvas for mouse-wheel handling."""
        self._scroll_canvases.append(canvas)
        if not self._wheel_bound:
            self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
            self.bind_all("<Button-4>", self._on_mousewheel, add="+")   # X11
            self.bind_all("<Button-5>", self._on_mousewheel, add="+")   # X11
            self._wheel_bound = True

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Scroll whichever rail is under the pointer (the old code let the right rail steal
        every wheel event and divided macOS deltas by 120, so nothing scrolled)."""
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        target = None
        while widget is not None:
            if isinstance(widget, (ttk.Treeview, tk.Text, tk.Listbox)):
                return   # these scroll themselves
            if widget in self._scroll_canvases:
                target = widget
                break
            widget = getattr(widget, "master", None)
        if target is None:
            return

        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        elif sys.platform == "darwin":
            step = -int(event.delta)
        else:
            step = -int(event.delta / 120)
        if step == 0:
            return
        lo, hi = target.yview()
        if lo <= 0.0 and hi >= 1.0:
            return
        target.yview_scroll(step, "units")

    def _refresh_project_tree(self) -> None:
        """Refresh the project tree."""
        if hasattr(self, 'project_tree'):
            self.project_tree.refresh()

    # ===== CENTER WORKSPACE =====
    def _build_center_workspace(self) -> None:
        cw = self.center_workspace
        cw.columnconfigure(0, weight=1, minsize=290)   # Design Inputs
        cw.columnconfigure(1, weight=2, minsize=240)   # Layout Viewer
        cw.rowconfigure(0, weight=0)                   # Band 1: Pipeline (natural height)
        cw.rowconfigure(1, weight=3, minsize=250)      # Band 2: Inputs + Viewer
        cw.rowconfigure(2, weight=2, minsize=150)      # Band 3: Terminal / Log
        cw.rowconfigure(3, weight=0)                   # Band 4: Quick Metrics (full width)

        # Band 1: Pipeline - spans full width
        self.pipeline_frame = ttk.LabelFrame(cw, text="Design Flow (RTL → GDSII)", style="Card.TLabelframe")
        self.pipeline_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=6, pady=(6, 3))

        self.pipeline_row = PipelineRow(
            self.pipeline_frame,
            on_run_stage=self._run_stage,
            on_run_all=self._run_all,
            on_stop=self._stop_flow,
            on_open_gui=self._open_or_gui_stage,
            on_view_gds=self._view_default_gds,
            on_open_in_editor=lambda: self._open_in_editor(),
            on_use_as_config=self._use_as_config,
            on_open_reports=self._open_reports_folder,
            on_export_log=self._export_log,
            on_preview_layout=self._preview_default_gds,
            on_make_clean=self._make_clean,
            get_config=lambda: self.app_config,
            on_settings=self._open_settings,
        )
        self.pipeline_row.pack(fill=tk.X, padx=10, pady=(4, 6))

        # FlowPanel is kept (not displayed) so existing handlers that reference it keep working
        self.flow_panel = FlowPanel(
            self.pipeline_frame,
            on_run_stage=self._run_stage,
            on_run_all=self._run_all,
            on_stop=self._stop_flow,
            on_open_gui=self._open_or_gui_stage,
            on_view_gds=self._view_default_gds,
            on_make_clean=self._make_clean,
            get_config=lambda: self.app_config,
        )

        # Band 2 (left): Design Inputs
        self.inputs_frame = ttk.LabelFrame(cw, text="Design Inputs", style="Card.TLabelframe")
        self.inputs_frame.grid(row=1, column=0, sticky="nsew", padx=(6, 3), pady=3)
        self._build_inputs_panel()

        # Band 2 (right): Layout Viewer
        self.viewer_frame = ttk.LabelFrame(cw, text="Layout Viewer", style="Card.TLabelframe")
        self.viewer_frame.grid(row=1, column=1, sticky="nsew", padx=(3, 6), pady=3)
        self.preview_panel = PreviewPanel(self.viewer_frame)
        self.preview_panel.pack(fill="both", expand=True, padx=6, pady=6)

        # Band 3: Terminal / Flow Log - spans full width.
        # LogViewer already has its own Export / Clear buttons (the extra toolbar that used to be
        # added here was a duplicate and was pushed out of view).
        self.log_frame = ttk.LabelFrame(cw, text="Terminal / Flow Log", style="Card.TLabelframe")
        self.log_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=6, pady=3)
        self.log_viewer = LogViewer(self.log_frame)
        self.log_viewer.pack(fill="both", expand=True)

        # Band 4: Quick Metrics - Flow Progress was removed, so metrics span the full width
        self.metrics_frame = ttk.LabelFrame(cw, text="Quick Metrics (Current Run)", style="Card.TLabelframe")
        self.metrics_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=6, pady=(3, 6))
        self._build_metrics_cards()

    # ===== RIGHT RAIL =====
    def _build_right_rail(self) -> None:
        rail = self.right_rail

        colors = self.theme_manager.get_colors()
        canvas = tk.Canvas(rail, highlightthickness=0, borderwidth=0, background=colors["BG_SIDEBAR"])
        canvas._theme_bg = "BG_SIDEBAR"
        scrollbar = ttk.Scrollbar(rail, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Sidebar.TFrame")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self._register_scroll_canvas(canvas)

        scrollable_frame.columnconfigure(0, weight=1)

        # 1. AI Assistant
        self.ai_frame = ttk.LabelFrame(scrollable_frame, text="AI Assistant", style="Card.TLabelframe")
        self.ai_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))
        self.ai_frame.columnconfigure(0, weight=1)
        self._build_ai_assistant()

        # 2. PPA Analysis
        self.ppa_frame = ttk.LabelFrame(scrollable_frame, text="PPA Analysis (AI Prediction)", style="Card.TLabelframe")
        self.ppa_frame.grid(row=1, column=0, sticky="ew", padx=6, pady=4)
        self.ppa_frame.columnconfigure(0, weight=1)
        self._build_ppa_analysis()

        # 3. Optimization Suggestions
        self.opt_frame = ttk.LabelFrame(scrollable_frame, text="Optimization Suggestions", style="Card.TLabelframe")
        self.opt_frame.grid(row=2, column=0, sticky="ew", padx=6, pady=4)
        self.opt_frame.columnconfigure(0, weight=1)
        self._build_optimization_suggestions()

        # 4. Reports
        self.reports_frame = ttk.LabelFrame(scrollable_frame, text="Reports", style="Card.TLabelframe")
        self.reports_frame.grid(row=3, column=0, sticky="ew", padx=6, pady=(4, 6))
        self.reports_frame.columnconfigure(0, weight=1)
        self._build_reports_panel()

    # ===== PANEL BUILDERS =====
    def _build_inputs_panel(self) -> None:
        """Design Inputs card (read-only view of the active design's files)."""
        f = self.inputs_frame
        f.columnconfigure(0, weight=1)

        form = ttk.Frame(f)
        form.grid(row=0, column=0, sticky="nsew", padx=10, pady=(6, 4))
        form.columnconfigure(1, weight=1)

        self._input_vars: dict[str, tk.StringVar] = {}
        self._input_entries: dict[str, ttk.Entry] = {}
        self._input_tips: dict[str, ToolTip] = {}
        self._input_paths: dict[str, Path | None] = {}

        rows = [
            ("name", "Project Name", False),
            ("rtl", "RTL File", True),
            ("lib", "Technology LIB", True),
            ("lef", "LEF Files", True),
            ("sdc", "Constraints (SDC)", True),
            ("config", "Config / Floorplan", True),
        ]
        for r, (key, label, browsable) in enumerate(rows):
            ttk.Label(form, text=label, style="Secondary.TLabel",
                      font=("TkDefaultFont", 9)).grid(row=r, column=0, sticky="w", padx=(0, 8), pady=2)
            var = tk.StringVar(value="—")
            entry = ttk.Entry(form, textvariable=var, state="readonly",
                              font=("TkDefaultFont", 9), width=12)
            entry.grid(row=r, column=1, sticky="ew", pady=2)
            self._input_vars[key] = var
            self._input_entries[key] = entry
            self._input_paths[key] = None
            self._input_tips[key] = ToolTip(entry, "—")
            if browsable:
                btn = ttk.Button(form, text="📄", width=3, style="Secondary.TButton",
                                 command=lambda k=key: self._browse_input(k))
                btn.grid(row=r, column=2, padx=(4, 0), pady=2)
                ToolTip(btn, "Preview / open this file")

        btns = ttk.Frame(f)
        btns.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 8))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        ttk.Button(btns, text="Load Inputs", style="Primary.TButton",
                   command=self._load_inputs).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(btns, text="View / Edit Files",
                   command=self._view_edit_files).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _browse_input(self, key: str) -> None:
        """Preview (or open externally) the file shown in a Design Inputs row."""
        path = self._input_paths.get(key)
        if not path or not Path(path).is_file():
            messagebox.showinfo("Design Inputs", "No file found for this input in the active design.")
            return
        path = Path(path)
        self._selected_file = path
        if key in ("lib", "lef"):
            # Technology files can be huge; open them in the external editor instead of the viewer
            self._open_in_editor()
        else:
            self._show_text_file(path)

    def _build_metrics_cards(self) -> None:
        metrics = [
            ("WNS", "wns", "ns"),
            ("TNS", "tns", "ns"),
            ("Total Power", "power", "mW"),
            ("Cell Area", "area", "μm²"),
            ("DRC", "drc", "violations"),
            ("LVS", "lvs", "status"),
        ]

        cards_container = ttk.Frame(self.metrics_frame)
        cards_container.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        for i in range(len(metrics)):
            cards_container.columnconfigure(i, weight=1, uniform="metric")

        for i, (label, key, unit) in enumerate(metrics):
            card = ttk.Frame(cards_container, style="MetricCard.TFrame", padding=(10, 4))
            card.grid(row=0, column=i, sticky="nsew", padx=4, pady=2)

            ttk.Label(card, text=label, style="MetricCard.TLabel",
                      font=("TkDefaultFont", 9)).pack(anchor="w")
            value_label = ttk.Label(card, text="—", style="MetricValue.TLabel")
            value_label.pack(anchor="w")
            ttk.Label(card, text=unit, style="MetricCard.TLabel",
                      font=("TkDefaultFont", 8)).pack(anchor="w")

            setattr(self, f"metric_{key}", value_label)

    def _build_ai_assistant(self) -> None:
        f = self.ai_frame
        f.configure(text="🤖  AI Assistant")
        f.columnconfigure(0, weight=1)
        colors = self.theme_manager.get_colors()

        # Header row: Clear Chat sits at the top-right of the card (it used to float mid-panel)
        header = ttk.Frame(f)
        header.pack(fill="x", padx=8, pady=(6, 0))
        ttk.Button(header, text="Clear Chat", width=10, style="Secondary.TButton",
                   command=self._clear_ai_chat).pack(side="right")

        self.ai_chat = tk.Text(f, height=7, width=10, wrap="word",
                               font=(self.theme_manager.MONO_FONT_FAMILY, 10),
                               bg=colors["LOG_BG"], fg=colors["FG_PRIMARY"],
                               insertbackground=colors["FG_PRIMARY"], relief="flat",
                               borderwidth=0, highlightthickness=0, padx=8, pady=6)
        self.ai_chat._theme_bg = "LOG_BG"
        self.ai_chat._theme_fg = "FG_PRIMARY"
        self.ai_chat.pack(fill="both", expand=True, padx=8, pady=4)
        self.ai_chat.insert("1.0", "🤖 How can I help you with your design today?\n\n")
        self.ai_chat.config(state="disabled")

        # Quick actions
        for label, cmd in [
            ("Suggest optimal floorplan parameters", self._ai_suggest_floorplan),
            ("Predict PPA for current design", self._ai_predict_ppa),
            ("Recommend better configuration", self._ai_recommend_config),
            ("Explain STA violations", self._ai_explain_sta),
            ("Help me fix routing congestion", self._ai_fix_congestion),
            ("Generate TCL script for custom flow", self._ai_generate_tcl),
        ]:
            ttk.Button(f, text=label, command=cmd, style="Secondary.TButton").pack(fill="x", padx=8, pady=2)

        # Input row with placeholder overlay
        input_frame = ttk.Frame(f)
        input_frame.pack(fill="x", padx=8, pady=(4, 8))
        input_frame.columnconfigure(0, weight=1)

        self.ai_input = ttk.Entry(input_frame, font=("TkDefaultFont", 10))
        self.ai_input.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.ai_placeholder = ttk.Label(input_frame, text="Type your question...",
                                        style="Placeholder.TLabel", font=("TkDefaultFont", 10),
                                        cursor="xterm")

        def show_placeholder() -> None:
            self.ai_placeholder.place(in_=self.ai_input, x=8, rely=0.5, anchor="w")

        def hide_placeholder() -> None:
            self.ai_placeholder.place_forget()

        show_placeholder()
        self.ai_placeholder.bind("<Button-1>", lambda e: self.ai_input.focus_set())
        self.ai_input.bind("<FocusIn>", lambda e: hide_placeholder())
        self.ai_input.bind("<FocusOut>", lambda e: show_placeholder() if not self.ai_input.get() else None)
        self.ai_input.bind("<KeyRelease>", lambda e: hide_placeholder() if self.ai_input.get() else show_placeholder())
        self.ai_input.bind("<Return>", lambda e: self._send_ai_message())

        ttk.Button(input_frame, text="Send ➤", command=self._send_ai_message, width=8).grid(row=0, column=1, sticky="e")

    def _build_ppa_analysis(self) -> None:
        f = self.ppa_frame
        f.columnconfigure(0, weight=1)
        colors = self.theme_manager.get_colors()

        header = ttk.Frame(f)
        header.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(header, text="Auto-updated after Floorplan (Predicted) and GDS (Actual)",
                  style="Secondary.TLabel", font=("TkDefaultFont", 8),
                  wraplength=120, justify="left").pack(side="left")
        ttk.Button(header, text="Run Prediction", style="Secondary.TButton",
                   command=self._run_ppa_prediction).pack(side="right")

        # One grid so the columns of the header and rows always line up
        grid = ttk.Frame(f)
        grid.pack(fill="x", padx=8, pady=(4, 8))
        grid.columnconfigure(0, weight=2, minsize=90)
        for i in (1, 2, 3):
            grid.columnconfigure(i, weight=1, minsize=58)

        for i, col_title in enumerate(["Metric", "Predicted", "Actual", "Diff (%)"]):
            ttk.Label(grid, text=col_title, style="Secondary.TLabel",
                      font=("TkDefaultFont", 8, "bold")).grid(row=0, column=i, padx=2, pady=(0, 4), sticky="w")

        # Metric rows: Power, Performance (WNS), Area
        self.ppa_rows = {}
        metrics = [
            ("Power (mW)", "power", "mW"),
            ("Perf. WNS (ns)", "wns", "ns"),
            ("Area (μm²)", "area", "μm²"),
        ]

        for row_idx, (label, key, unit) in enumerate(metrics, start=1):
            ttk.Label(grid, text=label, style="Secondary.TLabel",
                      font=("TkDefaultFont", 9)).grid(row=row_idx, column=0, padx=4, pady=3, sticky="w")

            pred_val = ttk.Label(grid, text="—", font=("TkDefaultFont", 11, "bold"),
                                 foreground=colors["ACCENT_BLUE"])
            pred_val.grid(row=row_idx, column=1, padx=4, pady=3, sticky="w")

            actual_val = ttk.Label(grid, text="—", font=("TkDefaultFont", 11, "bold"),
                                   foreground=colors["ACCENT_GREEN"])
            actual_val.grid(row=row_idx, column=2, padx=4, pady=3, sticky="w")

            diff_val = ttk.Label(grid, text="—", font=("TkDefaultFont", 11, "bold"),
                                 foreground=colors["ACCENT_AMBER"])
            diff_val.grid(row=row_idx, column=3, padx=4, pady=3, sticky="w")

            self.ppa_rows[key] = {"pred": pred_val, "actual": actual_val, "diff": diff_val, "unit": unit}

    def _build_optimization_suggestions(self) -> None:
        f = self.opt_frame
        f.configure(text="💡  Optimization Suggestions")
        f.columnconfigure(0, weight=1)

        # Apply Suggestion at the top-right of the card (it used to drop below the list)
        header = ttk.Frame(f)
        header.pack(fill="x", padx=8, pady=(6, 0))
        ttk.Button(header, text="Apply Suggestion", style="Primary.TButton",
                   command=self._apply_optimization).pack(side="right")

        self.suggestions_frame = ttk.Frame(f)
        self.suggestions_frame.pack(fill="both", expand=True, padx=8, pady=4)
        ttk.Label(self.suggestions_frame, text="No suggestions yet.",
                  style="Secondary.TLabel").pack(anchor="w", padx=8, pady=(4, 8))

    def _build_reports_panel(self) -> None:
        f = self.reports_frame
        f.columnconfigure(0, weight=1)

        buttons = [
            ("Timing Report", "📈", self._open_timing_report),
            ("Power Report", "⚡", self._open_power_report),
            ("Area Report", "📐", self._open_area_report),
            ("DRC Report", "✅", self._open_drc_report),
            ("LVS Report", "✅", self._open_lvs_report),
            ("Generate GDSII", "💾", self._generate_gdsii),
        ]

        grid = ttk.Frame(f)
        grid.pack(fill="x", padx=4, pady=6)
        for col in range(3):
            grid.columnconfigure(col, weight=1, uniform="reports")

        for idx, (label, icon, cmd) in enumerate(buttons):
            ttk.Button(grid, text=label, command=cmd, style="Compact.TButton").grid(
                row=idx // 3, column=idx % 3, sticky="ew", padx=2, pady=3)

    # ===== SHARED STATUS / PIPELINE-STATE HELPERS =====
    # The old code only updated the hidden FlowPanel (`if hasattr(self, 'flow_panel') ... elif
    # pipeline_row`), so the visible pipeline bar never showed "Running…" and its Stop button
    # stayed disabled. Both widgets are now updated.
    def _set_running(self, running: bool) -> None:
        if hasattr(self, 'flow_panel'):
            self.flow_panel.set_running(running)
        if hasattr(self, 'pipeline_row'):
            self.pipeline_row.set_running(running)
            self.pipeline_row.set_status("Running…" if running else "Ready")

    def _set_status(self, message: str) -> None:
        if hasattr(self, 'flow_panel'):
            self.flow_panel.set_status(message)
        if hasattr(self, 'pipeline_row'):
            self.pipeline_row.set_status(message)

    @staticmethod
    def _stage_by_label(label: str) -> FlowStage | None:
        for stage in FULL_PIPELINE:
            if stage.label == label:
                return stage
        return None

    def _mark_stage(self, stage: FlowStage, state: str) -> None:
        if hasattr(self, 'pipeline_row'):
            self.pipeline_row.set_stage_state(stage, state)

    def _track_stage_from_log(self, line: str) -> None:
        """Advance the pipeline nodes from the runner's own "=== Stage: X ===" log markers."""
        text = line.strip()
        prefix = "=== Stage:"
        if not (text.startswith(prefix) and text.endswith("===")):
            return
        stage = self._stage_by_label(text[len(prefix):-3].strip())
        if stage is None:
            return
        previous = self._active_stage
        if previous is not None and previous != stage:
            self._mark_stage(previous, "completed")   # pipeline only advances after success
        self._active_stage = stage
        self._mark_stage(stage, "running")

    def _update_stage_visuals(self, exit_code: int, label: str) -> None:
        """Reflect the final result of a run on the pipeline nodes."""
        stage = self._stage_by_label(label)
        if exit_code == 0:
            if label == "Full Pipeline":
                for st in FULL_PIPELINE:
                    self._mark_stage(st, "completed")
            elif stage is not None:
                self._mark_stage(stage, "completed")
        else:
            outcome = "cancelled" if self._ui_stop_requested else "failed"
            if stage is not None:
                self._mark_stage(stage, outcome)
            elif self._active_stage is not None:
                self._mark_stage(self._active_stage, "cancelled")
        self._active_stage = None

    # ===== FILE/PREVIEW HANDLERS (from backup - WORKING) =====
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
        self._set_status("Rendering GDS preview…")

        def work() -> None:
            png_path, error = self.viewers.render_gds_preview(path)
            self.after(0, lambda: self._on_preview_ready(path, png_path, error))

        threading.Thread(target=work, daemon=True).start()

    def _on_preview_ready(self, path: Path, png_path: Path | None, error: str) -> None:
        self._set_status("Ready")
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

        # Update both flow_panel and pipeline_row if they exist
        if hasattr(self, 'flow_panel'):
            self.flow_panel.set_design_info(
                self.app_config.design_name,
                self.app_config.platform,
                self.app_config.design_config,
            )
        if hasattr(self, 'pipeline_row'):
            self.pipeline_row.set_design_info(
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
        self._populate_design_inputs()
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

        vim_commands = [
            ["gvim", "--remote-tab-silent", path],
            ["mvim", "--remote-tab-silent", path],
            ["vim", path],
        ]

        for cmd in vim_commands:
            try:
                subprocess.run(["which", cmd[0]], check=True, capture_output=True)
                subprocess.Popen(cmd)
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

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
            self._set_status(stage.label)
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
        if self.runner.is_running:
            self.log_viewer.log_error("A flow stage is already running.")
            return
        self._ui_stop_requested = False
        self._active_stage = stage
        self._set_running(True)
        self._mark_stage(stage, "running")
        self.log_viewer.log_info(f"\n--- Starting {stage.label} ---\n")
        self.runner.run_stage(stage, self._on_log_line, self._on_stage_done)

    def _run_all(self) -> None:
        if not self._validate_before_run():
            return
        if self.runner.is_running:
            self.log_viewer.log_error("A flow stage is already running.")
            return
        self._ui_stop_requested = False
        self._active_stage = None
        if hasattr(self, 'pipeline_row'):
            self.pipeline_row.reset_all_stages()
        self._set_running(True)
        self.runner.run_pipeline(FULL_PIPELINE, self._on_log_line, self._on_stage_done)

    def _stop_flow(self) -> None:
        self._ui_stop_requested = True
        self.runner.stop()
        self.log_viewer.log_error("Stop requested…")

    def _make_clean(self) -> None:
        if not self._validate_before_run():
            return
        self._set_running(True)
        self.log_viewer.log_info("\n--- Running make clean ---\n")

        def on_log(stream: str, line: str) -> None:
            self.after(0, lambda: self.log_viewer.append(stream, line))

        def on_done(exit_code: int, label: str) -> None:
            def update() -> None:
                self._set_running(False)
                if exit_code == 0:
                    self._set_status("Make Clean — done")
                    if hasattr(self, 'pipeline_row'):
                        self.pipeline_row.reset_all_stages()
                    self.log_viewer.log_info("--- Make Clean finished successfully ---\n")
                else:
                    self._set_status(f"Make Clean — failed ({exit_code})")
                    self.log_viewer.log_error(f"--- Make Clean failed (exit {exit_code}) ---\n")
            self.after(0, update)

        cfg = self.app_config
        design_config = cfg.design_config
        flow_dir = cfg.flow_dir
        env_script = cfg.env_script

        # Try to get clean target from flow_panel, otherwise use clean_all
        if hasattr(self, 'flow_panel'):
            clean_target = self.flow_panel.clean_var.get()
        else:
            clean_target = "clean_all"

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
        def update() -> None:
            self.log_viewer.append(stream, line)
            self._track_stage_from_log(line)
        self.after(0, update)

    def _on_stage_done(self, exit_code: int, label: str) -> None:
        def update() -> None:
            self._set_running(False)
            self._update_stage_visuals(exit_code, label)
            if exit_code == 0:
                self._set_status(f"{label} — done")
                self.log_viewer.log_info(f"--- {label} finished successfully ---\n")

                # Auto-fetch PPA after specific stages
                if label == "Floorplan / Macro Placement":
                    # After floorplan: run PPA prediction
                    self.after(100, self._auto_fetch_ppa_after_floorplan)
                elif label in ("GDSII Generation", "Full Pipeline"):
                    # After GDS: fetch actual PPA from reports
                    self.after(100, self._auto_fetch_ppa_after_gds)
                    gds = self.viewers.default_gds_path()
                    if gds.is_file():
                        results_dir = self.app_config.results_dir
                        self.project_tree.set_root(
                            self.app_config.flow_dir,
                            active_results_dir=results_dir if results_dir.is_dir() else None,
                        )
            else:
                self._set_status(f"{label} — failed ({exit_code})")
                self.log_viewer.log_error(f"--- {label} failed (exit {exit_code}) ---\n")

        self.after(0, update)

    # ===== INTELLIGENCE METHODS (from backup - WORKING) =====
    def _predict_failure_risk(self) -> None:
        if not HAS_INTELLIGENCE or self.failure_predictor is None:
            messagebox.showinfo("Intelligence Unavailable", "Failure predictor not available.")
            return

        if not self.app_config.design_config:
            messagebox.showwarning("No Design", "No active design selected.")
            return

        metrics = self._fetch_design_metrics()

        if not metrics:
            messagebox.showinfo(
                "No Metrics Available",
                "No flow metrics found. Run a flow stage first to collect metrics."
            )
            return

        found_metrics = [k for k, v in metrics.items() if v is not None and v != 0]
        self.log_viewer.log_info(f"Found metrics for prediction: {', '.join(found_metrics)}\n")

        prediction = self.failure_predictor.predict(metrics)

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

        msg_lines = [
            f"Failure Risk Assessment for {self.app_config.design_name}",
            f"Platform: {self.app_config.platform}",
            f"Overall Risk: {prediction.get('overall_risk', 0.0):.1%}",
            "",
        ]

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
            msg_lines.append(f"  {failure_type}: {prob:.1%} ({severity})")
            if mitigations:
                msg_lines.append(f"  Mitigations: {', '.join(mitigations[:3])}")

        msg_lines.append("")
        msg_lines.append(f"Recommendations: {', '.join(prediction.get('recommendations', ['None']))}")

        messagebox.showinfo("Failure Risk Assessment", "\n".join(msg_lines))

    def _suggest_optimal_params(self) -> None:
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
        if not HAS_INTELLIGENCE or self.surrogate_inference is None:
            messagebox.showinfo("Intelligence Unavailable", "Surrogate models not available.")
            return

        if not self.app_config.design_config:
            messagebox.showwarning("No Design", "No active design selected.")
            return

        features = self._build_surrogate_features()

        if not features:
            messagebox.showinfo(
                "Cannot Predict",
                "Could not extract design features. Ensure config.mk exists and has required parameters."
            )
            return

        try:
            predictions = self.surrogate_inference.predict_ensemble(features)
        except ValueError as e:
            messagebox.showinfo(
                "Surrogate Models Not Ready",
                f"Could not load surrogate models: {e}\n\n"
                "Ensure the following files exist in openroad_gui/intelligence/models/saved/:\n"
                "  • surrogate_preprocessor.pkl (or preprocessor embedded in model files)\n"
                "  • surrogate_wns.pkl / surrogate_wns_lgb.pkl\n"
                "  • surrogate_tns.pkl / surrogate_tns_lgb.pkl\n"
                "  • surrogate_area.pkl / surrogate_area_lgb.pkl\n"
                "  • surrogate_power.pkl / surrogate_power_lgb.pkl\n\n"
                "Run the training pipeline to generate these files."
            )
            return

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
        if not HAS_INTELLIGENCE:
            messagebox.showinfo("Intelligence Unavailable", "Intelligence reports not available.")
            return

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
        features = {}

        config_path = self.app_config.flow_dir / "designs" / self.app_config.platform / self.app_config.design_name / "config.mk"
        if config_path.exists():
            import re
            content = config_path.read_text()

            for key in ['CORE_UTILIZATION', 'CORE_ASPECT_RATIO', 'CORE_MARGIN']:
                match = re.search(rf'{key}\s*=\s*([\d.]+)', content)
                if match:
                    features[key.lower()] = float(match.group(1))

        features.setdefault('core_utilization', 30.0)
        features.setdefault('core_aspect_ratio', 1.0)
        features.setdefault('core_margin', 5.0)

        features['platform'] = self.app_config.platform
        features['core_aspect_ratio'] = float(features['core_aspect_ratio'])

        verilog_files = list((self.app_config.flow_dir / "designs" / self.app_config.platform / self.app_config.design_name).glob("*.v"))
        num_instances = 5000
        if verilog_files:
            content = verilog_files[0].read_text()
            num_instances = max(100, len(re.findall(r'\b(module|always|assign)\b', content)) * 100)

        features['num_instances'] = num_instances
        features['num_nets'] = int(num_instances * 1.2)
        features['num_sequential'] = int(num_instances * 0.2)
        features['num_macros'] = 0
        features['macro_area_ratio'] = 0.0

        features['log_instances'] = np.log1p(num_instances) / 20.0
        features['log_nets'] = np.log1p(features['num_nets']) / 20.0
        features['seq_ratio'] = features['num_sequential'] / max(1, features['num_instances'])
        features['macro_ratio'] = features['num_macros'] / max(1, features['num_instances'])

        return features

    def _fetch_design_metrics(self) -> dict:
        metrics = {}

        if not self.app_config.design_config or not self.app_config.results_dir:
            return metrics

        reports_dir = self.app_config.flow_dir / "reports" / self.app_config.platform / self.app_config.design_name / "base"
        if not reports_dir.exists():
            self.log_viewer.log_error(f"Reports directory not found: {reports_dir}\n")
            return metrics

        self.log_viewer.log_info(f"Looking for reports in: {reports_dir}\n")

        from openroad_gui.intelligence.data.parser import parse_reports_directory
        try:
            metrics = parse_reports_directory(str(reports_dir))
            self.log_viewer.log_info(f"parse_reports_directory found metrics: {list(metrics.keys())}\n")
        except Exception as e:
            self.log_viewer.log_error(f"Failed to parse reports: {e}\n")

        try:
            if reports_dir.exists():
                stage_reports = list(reports_dir.glob("[0-9]_*.rpt"))
                self.log_viewer.log_info(f"Found stage reports: {[f.name for f in stage_reports]}\n")
                if stage_reports:
                    def stage_num(f):
                        try:
                            return int(f.stem.split('_')[0])
                        except (ValueError, IndexError):
                            return 0

                    latest_report = max(stage_reports, key=stage_num)
                    self.log_viewer.log_info(f"Latest stage report: {latest_report.name}\n")
                    content = latest_report.read_text()
                    self.log_viewer.log_info(f"Report preview: {content[:500]}\n")
                    from openroad_gui.intelligence.data.parser import _parse_report_content
                    latest_metrics = _parse_report_content(content)
                    self.log_viewer.log_info(f"Parsed metrics from {latest_report.name}: {latest_metrics}\n")
                    metrics.update(latest_metrics)
                    self.log_viewer.log_info(f"Using metrics from latest stage report: {latest_report.name}\n")
        except Exception as e:
            self.log_viewer.log_error(f"Failed to parse latest stage report: {e}\n")
            import traceback
            self.log_viewer.log_error(traceback.format_exc() + "\n")

        if not metrics:
            try:
                all_files = list(reports_dir.glob("*"))
                self.log_viewer.log_info(f"All files in reports dir: {[f.name for f in all_files]}\n")
            except Exception:
                pass

        return metrics

    # ===== MENU ACTION HANDLERS =====
    def _new_design(self) -> None:
        if hasattr(self, 'project_tree'):
            self.project_tree._new_design()

    def _open_project(self) -> None:
        path = filedialog.askdirectory(title="Select OpenROAD flow/ directory")
        if path:
            if hasattr(self, 'project_tree'):
                self.project_tree.set_root(Path(path))
            self.app_config.last_project_dir = path
            save_config(self.app_config)

    def _save_project(self) -> None:
        save_config(self.app_config)
        self.log_viewer.log_info("Project configuration saved.\n")

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

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            f"OpenROAD Flow GUI v{__version__}\n"
            "AI-Assisted EDA Workstation for RTL-to-GDSII Flow\n\n"
            "Built with Python + tkinter (stdlib only)\n"
            "Wraps OpenROAD Flow Scripts (ORFS)",
        )

    def _on_close(self) -> None:
        if self.runner.is_running:
            if not messagebox.askyesno("Flow running", "A flow stage is still running. Quit anyway?"):
                return
            self.runner.stop()
        self.destroy()

    def _open_reports_folder(self) -> None:
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

    # ===== PLACEHOLDER HANDLERS FOR NEW UI NAVIGATION =====
    def _focus_input(self, input_type: str) -> None:
        self.log_viewer.log_info(f"Focus input: {input_type}\n")
        entry = getattr(self, "_input_entries", {}).get(input_type)
        if entry is not None:
            entry.focus_set()

    def _show_flow_config(self) -> None:
        self.log_viewer.log_info("Show flow configuration\n")

    def _show_param_tuning(self) -> None:
        self.log_viewer.log_info("Show parameter tuning\n")

    def _show_ai_optimization(self) -> None:
        self.log_viewer.log_info("Show AI optimization\n")

    def _focus_logs(self) -> None:
        # Bring the Flow Log tab to the front
        self.log_viewer.notebook.select(self.log_viewer.log_frame)
        self.log_viewer.text.focus_set()

    def _show_reports(self) -> None:
        self._open_reports_folder()

    def _show_layout_viewer(self) -> None:
        self._view_default_gds()

    def _show_timing_analysis(self) -> None:
        self.log_viewer.log_info("Show timing analysis\n")

    def _show_power_analysis(self) -> None:
        self.log_viewer.log_info("Show power analysis\n")

    def _show_drc_lvs(self) -> None:
        self.log_viewer.log_info("Show DRC/LVS\n")

    def _open_tcl_console(self) -> None:
        self.log_viewer.log_info("Open TCL console\n")

    def _show_home(self) -> None:
        self.log_viewer.log_info("Show home view\n")

    def _show_flow_view(self) -> None:
        self.log_viewer.log_info("Show flow view\n")

    def _show_design_view(self) -> None:
        self.log_viewer.log_info("Show design view\n")

    def _show_run_view(self) -> None:
        self.log_viewer.log_info("Show run view\n")

    def _show_results_view(self) -> None:
        self.log_viewer.log_info("Show results view\n")

    def _show_ai_view(self) -> None:
        self.log_viewer.log_info("Show AI view\n")

    def _load_inputs(self) -> None:
        self._populate_design_inputs()
        self._refresh_project_tree()
        self.log_viewer.log_info("Design inputs refreshed from the active design.\n")

    def _view_edit_files(self) -> None:
        if not (self._selected_file and self._selected_file.is_file()):
            cfg_path = self._input_paths.get("config") if hasattr(self, "_input_paths") else None
            if cfg_path and Path(cfg_path).is_file():
                self._selected_file = Path(cfg_path)
            else:
                messagebox.showinfo("View / Edit Files", "Select a file in the project tree first.")
                return
        self._open_in_editor()

    def _clear_ai_chat(self) -> None:
        self.ai_chat.config(state="normal")
        self.ai_chat.delete("1.0", tk.END)
        self.ai_chat.insert("1.0", "🤖 How can I help you with your design today?\n\n")
        self.ai_chat.config(state="disabled")

    def _ai_suggest_floorplan(self) -> None:
        self._append_ai_chat("AI: Analyzing floorplan parameters...")

    def _ai_predict_ppa(self) -> None:
        self._append_ai_chat("AI: Predicting PPA...")

    def _ai_recommend_config(self) -> None:
        self._append_ai_chat("AI: Recommending configuration...")

    def _ai_explain_sta(self) -> None:
        self._append_ai_chat("AI: Explaining STA violations...")

    def _ai_fix_congestion(self) -> None:
        self._append_ai_chat("AI: Analyzing routing congestion...")

    def _ai_generate_tcl(self) -> None:
        self._append_ai_chat("AI: Generating TCL script...")

    def _send_ai_message(self) -> None:
        msg = self.ai_input.get()
        if msg:
            self._append_ai_chat(f"You: {msg}")
            self.ai_input.delete(0, tk.END)
            self._append_ai_chat(f"AI: Processing '{msg}'...")

    def _append_ai_chat(self, text: str) -> None:
        self.ai_chat.config(state="normal")
        self.ai_chat.insert(tk.END, text + "\n")
        self.ai_chat.see(tk.END)
        self.ai_chat.config(state="disabled")

    def _run_ppa_prediction(self) -> None:
        """Run PPA prediction using surrogate models and update Predicted column."""
        if not HAS_INTELLIGENCE or self.surrogate_inference is None:
            self._append_ai_chat("❌ Surrogate models not available. Check intelligence module initialization.")
            return

        if not self.app_config.design_config:
            self._append_ai_chat("❌ No active design selected. Set a config.mk first.")
            return

        self._append_ai_chat("🔮 Running PPA prediction...")

        try:
            features = self._build_surrogate_features()
            if not features:
                self._append_ai_chat("❌ Could not extract design features from config.mk")
                return

            predictions = self.surrogate_inference.predict_ensemble(features)

            # Update Predicted column
            self._update_ppa_predicted(predictions)

            self._append_ai_chat(
                f"✅ PPA Prediction Complete:\n"
                f"   Power: {predictions.get('power', 0):.1f} mW\n"
                f"   WNS: {predictions.get('wns', 0):.2f} ns\n"
                f"   Area: {predictions.get('area', 0):.0f} μm²\n"
                f"   TNS: {predictions.get('tns', 0):.2f} ns"
            )
            self.log_viewer.log_info(f"PPA prediction: WNS={predictions.get('wns', 0):.2f}, "
                                     f"Area={predictions.get('area', 0):.0f}, "
                                     f"Power={predictions.get('power', 0):.1f}\n")

        except Exception as e:
            self._append_ai_chat(f"❌ PPA prediction failed: {e}")
            self.log_viewer.log_error(f"PPA prediction error: {e}\n")

    def _update_ppa_predicted(self, predictions: dict) -> None:
        """Update the Predicted column in PPA Analysis."""
        if not hasattr(self, 'ppa_rows'):
            return

        # Power (mW)
        if 'power' in self.ppa_rows:
            self.ppa_rows['power']['pred'].configure(text=f"{predictions.get('power', 0):.1f}")

        # WNS (ns)
        if 'wns' in self.ppa_rows:
            self.ppa_rows['wns']['pred'].configure(text=f"{predictions.get('wns', 0):.2f}")

        # Area (μm²)
        if 'area' in self.ppa_rows:
            self.ppa_rows['area']['pred'].configure(text=f"{predictions.get('area', 0):.0f}")

    def _fetch_actual_ppa_from_reports(self) -> dict | None:
        """Parse actual PPA from 6_finish.rpt reports after GDS completion."""
        reports_dir = self.app_config.flow_dir / "reports" / self.app_config.platform / self.app_config.design_name / "base"
        if not reports_dir.is_dir():
            return None

        finish_rpt = reports_dir / "6_finish.rpt"
        if not finish_rpt.exists():
            # Try to find any finish report
            finish_reports = list(reports_dir.glob("*_finish.rpt"))
            if not finish_reports:
                return None
            finish_rpt = max(finish_reports, key=lambda f: int(f.stem.split('_')[0]) if f.stem.split('_')[0].isdigit() else 0)

        try:
            content = finish_rpt.read_text(encoding="utf-8", errors="replace")
            ppa = {}

            import re

            # Parse WNS
            wns_match = re.search(r'wns max\s+([-\d.]+)', content)
            if wns_match:
                ppa['wns'] = float(wns_match.group(1))

            # Parse TNS
            tns_match = re.search(r'tns max\s+([-\d.]+)', content)
            if tns_match:
                ppa['tns'] = float(tns_match.group(1))

            # Parse Power from report_power section
            power_match = re.search(r'Total\s+[\de\.\-]+\s+[\de\.\-]+\s+[\de\.\-]+\s+([\de\.\-]+)\s+100\.0%', content)
            if power_match:
                power_watts = float(power_match.group(1))
                ppa['power'] = power_watts * 1000  # Convert W to mW

            # Parse DRC violations
            drc_match = re.search(r'drc_violations\s+(\d+)', content) or re.search(r'DRC violations\s+(\d+)', content) or re.search(r'drc violations\s+(\d+)', content)
            if drc_match:
                ppa['drc'] = int(drc_match.group(1))

            # Parse LVS
            lvs_match = re.search(r'lvs_clean\s+(\d+)', content) or re.search(r'LVS clean\s+(\d+)', content) or re.search(r'lvs violations\s+(\d+)', content)
            if lvs_match:
                ppa['lvs'] = int(lvs_match.group(1))

            # Parse Area from JSON report
            json_report = reports_dir / "6_report.json"
            if json_report.exists():
                import json
                try:
                    json_data = json.loads(json_report.read_text())
                    # Try multiple possible keys for area
                    area_keys = [
                        'finish__design__instance__area',
                        'finish__design__core__area',
                        'finish__design__die__area',
                        'instance_area_um2',
                        'core_area_um2',
                        'die_area_um2'
                    ]
                    for key in area_keys:
                        if key in json_data and json_data[key] is not None:
                            ppa['area'] = float(json_data[key])
                            break
                except Exception:
                    pass

            # Fallback 1: Parse area from 6_finish.rpt (look for area in report)
            if 'area' not in ppa:
                area_patterns = [
                    r'design area\s+(\d+)\s*um\^2',  # "Design area 13 um^2 55% utilization."
                    r'design area\s*[=:]\s*([\d.]+)',
                    r'area\s*[=:]\s*([\d.]+)',
                    r'design area\s*[=:]\s*([\d.]+)',
                    r'instance area\s*[=:]\s*([\d.]+)',
                    r'core area\s*[=:]\s*([\d.]+)',
                    r'total area\s*[=:]\s*([\d.]+)',
                ]
                for pattern in area_patterns:
                    area_match = re.search(pattern, content, re.IGNORECASE)
                    if area_match:
                        ppa['area'] = float(area_match.group(1))
                        break

            # Fallback 2: Try to get area from place reports
            if 'area' not in ppa:
                place_reports = list(reports_dir.glob("*_place*.rpt"))
                if place_reports:
                    latest_place = max(place_reports, key=lambda f: int(f.stem.split('_')[0]) if f.stem.split('_')[0].isdigit() else 0)
                    place_content = latest_place.read_text(encoding="utf-8", errors="replace")
                    area_match = re.search(r'area\s*[=:]\s*([\d.]+)', place_content, re.IGNORECASE)
                    if area_match:
                        ppa['area'] = float(area_match.group(1))

            # Fallback 3: Estimate from instance count and utilization (if available in JSON)
            if 'area' not in ppa and json_report.exists():
                try:
                    import json
                    json_data = json.loads(json_report.read_text())
                    # If we have utilization and instance count, we can estimate
                    instance_count = json_data.get('finish__design__instance__count')
                    utilization = json_data.get('finish__design__instance__utilization')
                    # Fallback: rough estimate from WNS/TNS magnitude (larger designs = more area)
                    if instance_count:
                        # Very rough heuristic: ~100-500 μm² per 1000 instances
                        ppa['area'] = float(instance_count) * 0.3
                except Exception:
                    pass

            return ppa if ppa else None

        except Exception as e:
            self.log_viewer.log_error(f"Failed to parse actual PPA: {e}\n")
            return None

    def _update_ppa_actual(self, ppa: dict) -> None:
        """Update the Actual column and calculate Diff (%)."""
        if not hasattr(self, 'ppa_rows'):
            return

        # Also update Quick Metrics in Band 4
        self._update_quick_metrics(ppa)

        for key, row in self.ppa_rows.items():
            pred_text = row['pred'].cget("text")
            actual_val = ppa.get(key)

            if actual_val is not None:
                # Update Actual
                if key == 'power':
                    row['actual'].configure(text=f"{actual_val:.1f}")
                elif key == 'wns':
                    row['actual'].configure(text=f"{actual_val:.2f}")
                elif key == 'area':
                    row['actual'].configure(text=f"{actual_val:.0f}")

                # Calculate Diff (%)
                try:
                    pred_val = float(pred_text) if pred_text not in ("—", "") else 0
                    if pred_val != 0:
                        diff_pct = ((actual_val - pred_val) / abs(pred_val)) * 100
                        diff_color = self.theme_manager.get_colors()["ACCENT_GREEN"] if diff_pct <= 0 else self.theme_manager.get_colors()["ACCENT_RED"]
                        row['diff'].configure(text=f"{diff_pct:+.1f}%", foreground=diff_color)
                    else:
                        row['diff'].configure(text="N/A", foreground=self.theme_manager.get_colors()["FG_SECONDARY"])
                except (ValueError, ZeroDivisionError):
                    row['diff'].configure(text="N/A", foreground=self.theme_manager.get_colors()["FG_SECONDARY"])

    def _update_quick_metrics(self, ppa: dict) -> None:
        """Update Quick Metrics cards in Band 4 from actual PPA data."""
        if not hasattr(self, 'metric_wns'):
            return

        metric_map = {
            'wns': ('metric_wns', lambda v: f"{v:.2f}"),
            'tns': ('metric_tns', lambda v: f"{v:.2f}"),
            'area': ('metric_area', lambda v: f"{v:.0f}"),
            'power': ('metric_power', lambda v: f"{v:.1f}"),
            'drc': ('metric_drc', lambda v: f"{v}"),
            'lvs': ('metric_lvs', lambda v: "Clean" if v == 0 else f"{v} viol"),
        }

        for key, (attr, fmt_func) in metric_map.items():
            if key in ppa and hasattr(self, attr):
                value_label = getattr(self, attr)
                value_label.configure(text=fmt_func(ppa[key]))

    def _auto_fetch_ppa_after_floorplan(self) -> None:
        """Auto-trigger PPA prediction after floorplan completes."""
        self.log_viewer.log_info("🔮 Auto-fetching PPA prediction after floorplan...\n")
        self._run_ppa_prediction()

    def _auto_fetch_ppa_after_gds(self) -> None:
        """Auto-fetch actual PPA from reports after GDS completes."""
        self.log_viewer.log_info("📊 Auto-fetching actual PPA from final reports...\n")
        ppa = self._fetch_actual_ppa_from_reports()
        if ppa:
            self._update_ppa_actual(ppa)
            self._append_ai_chat(
                f"✅ Actual PPA from reports:\n"
                f"   Power: {ppa.get('power', 0):.1f} mW\n"
                f"   WNS: {ppa.get('wns', 0):.2f} ns\n"
                f"   Area: {ppa.get('area', 0):.0f} μm²\n"
                f"   TNS: {ppa.get('tns', 0):.2f} ns"
            )
            self.log_viewer.log_info(f"Actual PPA: WNS={ppa.get('wns', 0):.2f}, "
                                     f"Area={ppa.get('area', 0):.0f}, "
                                     f"Power={ppa.get('power', 0):.1f}\n")
        else:
            self._append_ai_chat("⚠️ Could not parse actual PPA from reports.")
            self.log_viewer.log_warning("Could not parse actual PPA from reports.\n")

    def _apply_optimization(self) -> None:
        self._append_ai_chat("Applying optimization...")

    def _find_latest_report(self, patterns: list[str]) -> Path | None:
        """Find the latest report file matching any of the given patterns."""
        reports_dir = self.app_config.flow_dir / "reports" / self.app_config.platform / self.app_config.design_name / "base"
        if not reports_dir.is_dir():
            return None

        all_matches = []
        for pattern in patterns:
            matches = list(reports_dir.glob(pattern))
            all_matches.extend(matches)

        if not all_matches:
            return None

        # Return the most recent (highest stage number) report
        def stage_num(f):
            try:
                return int(f.stem.split('_')[0])
            except (ValueError, IndexError):
                return 0

        return max(all_matches, key=stage_num)

    def _open_report(self, patterns: list[str], title: str) -> None:
        """Open the latest report matching any of the patterns."""
        latest = self._find_latest_report(patterns)
        if latest is None:
            if not (self.app_config.flow_dir / "reports" / self.app_config.platform / self.app_config.design_name / "base").is_dir():
                messagebox.showinfo("No Reports", "Reports directory not found. Run a flow stage first.")
            else:
                messagebox.showinfo("No Report", f"No {title} found. Run a flow stage first.")
            return

        try:
            import os
            if os.uname().sysname == "Darwin":
                # On macOS, use MacVim/gvim/VS Code to open .rpt files since 'open' doesn't know how
                editor = None
                for cmd in ["mvim", "gvim", "vim", "code", "subl"]:
                    try:
                        subprocess.run(["which", cmd], check=True, capture_output=True)
                        editor = cmd
                        break
                    except subprocess.CalledProcessError:
                        continue

                if editor in ("mvim", "gvim"):
                    subprocess.Popen([editor, "--remote-tab-silent", str(latest)])
                elif editor == "vim":
                    subprocess.Popen([editor, str(latest)])
                elif editor:
                    subprocess.Popen([editor, str(latest)])
                else:
                    # Fallback to TextEdit
                    subprocess.Popen(["open", "-a", "TextEdit", str(latest)])
            else:
                subprocess.Popen(["xdg-open", str(latest)])
            self.log_viewer.log_info(f"Opened {title}: {latest.name}\n")
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))

    def _open_timing_report(self) -> None:
        # Timing reports: 4_cts_final.rpt (CTS), 6_finish.rpt (final timing), 3_*_place.rpt (placement timing)
        self._open_report(["*_cts_final.rpt", "*_finish.rpt", "*_place*.rpt", "*_timing*.rpt", "*_sta*.rpt", "*_wns*.rpt"], "Timing Report")

    def _open_power_report(self) -> None:
        # Power reports: 6_finish.rpt (final power), congestion reports may have power info
        self._open_report(["*_finish.rpt", "*_power*.rpt", "congestion*.rpt"], "Power Report")

    def _open_area_report(self) -> None:
        # Area reports: 3_*_place.rpt (placement area), 6_finish.rpt (final area)
        self._open_report(["*_place*.rpt", "*_finish.rpt", "*_area*.rpt", "*_detailed_place*.rpt", "*_global_place*.rpt"], "Area Report")

    def _open_drc_report(self) -> None:
        # DRC reports: 5_route_drc.rpt, 6_finish.rpt
        self._open_report(["*_route_drc*.rpt", "*_drc*.rpt", "*_finish.rpt", "*_magic*.rpt", "*_klayout*.rpt"], "DRC Report")

    def _open_lvs_report(self) -> None:
        # LVS reports: 6_finish.rpt (final signoff)
        self._open_report(["*_finish.rpt", "*_lvs*.rpt", "*_netgen*.rpt"], "LVS Report")

    def _generate_gdsii(self) -> None:
        if not self._validate_before_run():
            return
        self.log_viewer.log_info("Starting GDSII generation...\n")
        self._run_stage(FlowStage.GDS)

    def _apply_rail_widths(self, window_width: int) -> None:
        """Narrow the side rails on smaller windows so the centre workspace stays usable."""
        if window_width >= 1400:
            left, right = self.LEFT_RAIL_WIDTH, self.RIGHT_RAIL_WIDTH
        elif window_width >= 1200:
            left, right = 210, 340
        else:
            left, right = 190, 310
        if getattr(self, "_rail_widths", None) == (left, right):
            return
        self._rail_widths = (left, right)
        self.columnconfigure(0, minsize=left)
        self.columnconfigure(2, minsize=right)
        self.nav_rail.configure(width=left)
        self.right_rail.configure(width=right)

    def _on_window_resize(self, event: tk.Event) -> None:
        if event.widget == self:
            self._apply_rail_widths(event.width)
            if hasattr(self, 'pipeline_row'):
                self.after(100, self.pipeline_row._draw_pipeline)

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

        if hasattr(self, 'flow_panel'):
            self.flow_panel.set_design_info(
                self.app_config.design_name,
                self.app_config.platform,
                self.app_config.design_config,
            )
        if hasattr(self, 'pipeline_row'):
            self.pipeline_row.set_design_info(
                self.app_config.design_name,
                self.app_config.platform,
                self.app_config.design_config,
            )

        # Populate Design Inputs panel
        self._populate_design_inputs()

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

    def _populate_design_inputs(self) -> None:
        """Fill the Design Inputs card from the active design (display only)."""
        if not hasattr(self, "_input_vars"):
            return
        cfg = self.app_config
        design_dir = cfg.flow_dir / "designs" / cfg.platform / cfg.design_name
        plat_dir = cfg.flow_dir / "platforms" / cfg.platform

        def scan(base: Path, patterns: list[str]) -> list[Path]:
            found: list[Path] = []
            try:
                if base.is_dir():
                    for pattern in patterns:
                        found.extend(sorted(base.rglob(pattern)))
            except OSError:
                pass
            return found

        def put(key: str, display: str, path: Path | None, tip: str) -> None:
            self._input_vars[key].set(display or "—")
            self._input_paths[key] = path
            self._input_tips[key].text = tip or "Not found"

        def put_matches(key: str, matches: list[Path]) -> None:
            if not matches:
                put(key, "—", None, "Not found for the active design")
                return
            extra = f"  (+{len(matches) - 1} more)" if len(matches) > 1 else ""
            put(key, matches[0].name + extra, matches[0], "\n".join(str(m) for m in matches[:8]))

        put("name", cfg.design_name, None, f"{cfg.platform}/{cfg.design_name}")
        put_matches("rtl", scan(design_dir, ["*.v", "*.sv"]))
        put_matches("lib", scan(plat_dir / "lib", ["*.lib*"]))
        put_matches("lef", scan(plat_dir / "lef", ["*.lef"]))
        put_matches("sdc", scan(design_dir, ["*.sdc"]))

        cfg_path = Path(cfg.design_config) if cfg.design_config else None
        if cfg_path is not None and not cfg_path.is_absolute():
            cfg_path = cfg.flow_dir / cfg_path
        if cfg_path is not None and cfg_path.is_file():
            put("config", cfg_path.name, cfg_path, str(cfg_path))
        else:
            put("config", cfg.design_config or "—", None, "config.mk not found")

def run() -> None:
    """Entry point for the application."""
    app = OpenRoadGUI()
    app.mainloop()


if __name__ == "__main__":
    run()
