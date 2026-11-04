cat > patch_app.py <<'PYEOF'
import re
from pathlib import Path

p = Path("openroad_gui/app.py")
s = p.read_text()

def sub1(src, old, new):
    assert old in src, f"anchor not found: {old[:70]!r}"
    return src.replace(old, new, 1)

_END = re.compile(r'^(    def |    # =====|def |class |if __name__)', re.M)

def replace_method(src, name, new):
    m = re.search(rf'^    def {name}\(', src, re.M)
    assert m, f"method not found: {name}"
    n = _END.search(src, m.end())
    end = n.start() if n else len(src)
    return src[:m.start()] + new.strip('\n') + '\n\n' + src[end:]

# ----------------------------------------------------------------- imports / init
s = sub1(s, "import subprocess\nimport threading\n", "import subprocess\nimport sys\nimport threading\n")
s = sub1(s, "from openroad_gui.widgets.flow_panel import FlowPanel\n",
            "from openroad_gui.widgets.flow_panel import FlowPanel, ToolTip\n")

s = sub1(s, 'class OpenRoadGUI(tk.Tk):\n    """Main application window - Industrial EDA Workstation."""\n',
            'class OpenRoadGUI(tk.Tk):\n    """Main application window - Industrial EDA Workstation."""\n\n'
            '    LEFT_RAIL_WIDTH = 230\n    RIGHT_RAIL_WIDTH = 380\n')

s = sub1(s, "        self.minsize(900, 600)\n", "        self.minsize(1100, 720)\n")

s = sub1(s, "        # Initialize intelligence modules\n        self.optimizer = None\n",
            "        # UI state used by the layout code\n"
            "        self._selected_file: Path | None = None\n"
            "        self._scroll_canvases: list[tk.Canvas] = []\n"
            "        self._wheel_bound = False\n"
            "        self._active_stage: FlowStage | None = None\n"
            "        self._ui_stop_requested = False\n\n"
            "        # Initialize intelligence modules\n        self.optimizer = None\n")

s = sub1(s, "        self._build_layout()\n        self._apply_config()\n",
            "        self._build_layout()\n"
            "        # Widgets created after init_theme() need their colours applied once\n"
            "        self.theme_manager.apply_to_widgets(self)\n"
            "        self.log_viewer._refresh_theme()\n"
            "        self._apply_config()\n")

# ----------------------------------------------------------------- theme change
s = replace_method(s, "_on_theme_change", '''
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
''')

# ----------------------------------------------------------------- layout
s = replace_method(s, "_build_layout", '''
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
''')

s = replace_method(s, "_build_header", '''
    def _build_header(self) -> None:
        """Build the application header with brand and actions only."""
        h = self.header_frame
        h.columnconfigure(0, weight=0)  # Brand
        h.columnconfigure(1, weight=1)  # Spacer
        h.columnconfigure(2, weight=0)  # Actions

        # Brand block (left)
        brand = ttk.Frame(h, style="Header.TFrame")
        brand.grid(row=0, column=0, sticky="w", padx=(18, 0), pady=8)
        ttk.Label(brand, text="⬢", style="Header.TLabel",
                  font=("TkDefaultFont", 26)).grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ttk.Label(brand, text="AI-Assisted EDA", style="Header.TLabel",
                  font=("TkDefaultFont", 20, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(brand, text="OpenROAD GUI for RTL-to-GDSII Flow", style="Header.Secondary.TLabel",
                  font=("TkDefaultFont", 10)).grid(row=1, column=1, sticky="w")

        # Right actions (theme toggle + help)
        actions = ttk.Frame(h, style="Header.TFrame")
        actions.grid(row=0, column=2, sticky="e", padx=18, pady=10)

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
''')

# ----------------------------------------------------------------- left rail + scrolling
s = replace_method(s, "_build_nav_rail", '''
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
            ("RTL (Verilog/SystemVerilog)", "📄", lambda: self._focus_input("rtl")),
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
''')

# ----------------------------------------------------------------- center workspace
s = replace_method(s, "_build_center_workspace", '''
    def _build_center_workspace(self) -> None:
        cw = self.center_workspace
        cw.columnconfigure(0, weight=2, minsize=250)   # Design Inputs
        cw.columnconfigure(1, weight=3, minsize=240)   # Layout Viewer
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
''')

# ----------------------------------------------------------------- right rail
s = replace_method(s, "_build_right_rail", '''
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
''')

# ----------------------------------------------------------------- Design Inputs panel (was an empty stub)
s = replace_method(s, "_build_inputs_panel", '''
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
''')

s = replace_method(s, "_populate_design_inputs", '''
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
            put(key, matches[0].name + extra, matches[0], "\\n".join(str(m) for m in matches[:8]))

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
''')

s = replace_method(s, "_load_inputs", '''
    def _load_inputs(self) -> None:
        self._populate_design_inputs()
        self._refresh_project_tree()
        self.log_viewer.log_info("Design inputs refreshed from the active design.\\n")
''')

s = replace_method(s, "_view_edit_files", '''
    def _view_edit_files(self) -> None:
        if not (self._selected_file and self._selected_file.is_file()):
            cfg_path = self._input_paths.get("config") if hasattr(self, "_input_paths") else None
            if cfg_path and Path(cfg_path).is_file():
                self._selected_file = Path(cfg_path)
            else:
                messagebox.showinfo("View / Edit Files", "Select a file in the project tree first.")
                return
        self._open_in_editor()
''')

s = replace_method(s, "_focus_input", '''
    def _focus_input(self, input_type: str) -> None:
        self.log_viewer.log_info(f"Focus input: {input_type}\\n")
        entry = getattr(self, "_input_entries", {}).get(input_type)
        if entry is not None:
            entry.focus_set()
''')

s = replace_method(s, "_focus_logs", '''
    def _focus_logs(self) -> None:
        # Bring the Flow Log tab to the front
        self.log_viewer.notebook.select(self.log_viewer.log_frame)
        self.log_viewer.text.focus_set()
''')

# ----------------------------------------------------------------- Quick metrics (full width, spec order)
s = replace_method(s, "_build_metrics_cards", '''
    def _build_metrics_cards(self) -> None:
        metrics = [
            ("WNS", "wns", "ns"),
            ("TNS", "tns", "ns"),
            ("Total Power", "power", "mW"),
            ("Cell Area", "area", "μm²"),
            ("DRC Violations", "drc", "count"),
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
''')

# ----------------------------------------------------------------- AI assistant
s = replace_method(s, "_build_ai_assistant", '''
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
        self.ai_chat.insert("1.0", "🤖 How can I help you with your design today?\\n\\n")
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
''')

# ----------------------------------------------------------------- PPA
s = replace_method(s, "_build_ppa_analysis", '''
    def _build_ppa_analysis(self) -> None:
        f = self.ppa_frame
        f.columnconfigure(0, weight=1)
        colors = self.theme_manager.get_colors()

        header = ttk.Frame(f)
        header.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(header, text="Auto-updated after Floorplan (Predicted) and GDS (Actual)",
                  style="Secondary.TLabel", font=("TkDefaultFont", 8),
                  wraplength=230, justify="left").pack(side="left")
        ttk.Button(header, text="Run Prediction", style="Secondary.TButton",
                   command=self._run_ppa_prediction).pack(side="right")

        # One grid so the columns of the header and rows always line up
        grid = ttk.Frame(f)
        grid.pack(fill="x", padx=8, pady=(4, 8))
        grid.columnconfigure(0, weight=2, minsize=110)
        for i in (1, 2, 3):
            grid.columnconfigure(i, weight=1, minsize=60)

        for i, col_title in enumerate(["Metric", "Predicted", "Actual", "Diff (%)"]):
            ttk.Label(grid, text=col_title, style="Secondary.TLabel",
                      font=("TkDefaultFont", 8, "bold")).grid(row=0, column=i, padx=4, pady=(0, 4), sticky="w")

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
''')

# ----------------------------------------------------------------- Optimization suggestions
s = replace_method(s, "_build_optimization_suggestions", '''
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
''')

# ----------------------------------------------------------------- Reports
s = replace_method(s, "_build_reports_panel", '''
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
        grid.pack(fill="x", padx=8, pady=6)
        for col in range(3):
            grid.columnconfigure(col, weight=1, uniform="reports")

        for idx, (label, icon, cmd) in enumerate(buttons):
            ttk.Button(grid, text=f"{icon} {label}", command=cmd, style="Compact.TButton").grid(
                row=idx // 3, column=idx % 3, sticky="ew", padx=3, pady=3)
''')

# ----------------------------------------------------------------- shared running/status helpers
s = sub1(s, "    # ===== FILE/PREVIEW HANDLERS (from backup - WORKING) =====\n", '''    # ===== SHARED STATUS / PIPELINE-STATE HELPERS =====
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

''' + "    # ===== FILE/PREVIEW HANDLERS (from backup - WORKING) =====\n")

# collapse the `if hasattr(flow_panel) ... elif hasattr(pipeline_row)` pairs into the helpers
pat_fp_first = re.compile(
    r"(?m)^([ ]*)if hasattr\(self, 'flow_panel'\):\n[ ]+self\.flow_panel\.(set_running|set_status)\((.+)\)\n"
    r"[ ]+elif hasattr\(self, 'pipeline_row'\):\n[ ]+self\.pipeline_row\.\2\(\3\)\n")
s, n1 = pat_fp_first.subn(lambda m: f"{m.group(1)}self._{m.group(2)}({m.group(3)})\n", s)
pat_pr_first = re.compile(
    r"(?m)^([ ]*)if hasattr\(self, 'pipeline_row'\):\n[ ]+self\.pipeline_row\.(set_status)\((.+)\)\n"
    r"[ ]+elif hasattr\(self, 'flow_panel'\):\n[ ]+self\.flow_panel\.\2\(\3\)\n")
s, n2 = pat_pr_first.subn(lambda m: f"{m.group(1)}self._{m.group(2)}({m.group(3)})\n", s)
print("collapsed status/running blocks:", n1, n2)

# stale "success" markers must not survive a successful make clean
s = sub1(s, '                    self.log_viewer.log_info("--- Make Clean finished successfully ---\\n")',
            '                    if hasattr(self, \'pipeline_row\'):\n                        self.pipeline_row.reset_all_stages()\n'
            '                    self.log_viewer.log_info("--- Make Clean finished successfully ---\\n")')

# ----------------------------------------------------------------- run / stop / log / done
s = replace_method(s, "_run_stage", '''
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
        self.log_viewer.log_info(f"\\n--- Starting {stage.label} ---\\n")
        self.runner.run_stage(stage, self._on_log_line, self._on_stage_done)
''')

s = replace_method(s, "_run_all", '''
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
''')

s = replace_method(s, "_stop_flow", '''
    def _stop_flow(self) -> None:
        self._ui_stop_requested = True
        self.runner.stop()
        self.log_viewer.log_error("Stop requested…")
''')

s = replace_method(s, "_on_log_line", '''
    def _on_log_line(self, stream: str, line: str) -> None:
        def update() -> None:
            self.log_viewer.append(stream, line)
            self._track_stage_from_log(line)
        self.after(0, update)
''')

s = replace_method(s, "_on_stage_done", '''
    def _on_stage_done(self, exit_code: int, label: str) -> None:
        def update() -> None:
            self._set_running(False)
            self._update_stage_visuals(exit_code, label)
            if exit_code == 0:
                self._set_status(f"{label} — done")
                self.log_viewer.log_info(f"--- {label} finished successfully ---\\n")

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
                self.log_viewer.log_error(f"--- {label} failed (exit {exit_code}) ---\\n")

        self.after(0, update)
''')

# keep the Design Inputs card in sync when the active config.mk changes from the tree
s = sub1(s, '        self.log_viewer.log_info(f"Active design set to: {self.app_config.design_config}\\n")',
            '        self._populate_design_inputs()\n        self.log_viewer.log_info(f"Active design set to: {self.app_config.design_config}\\n")')

p.write_text(s)
print("app.py patched")
PYEOF
python3 patch_app.py && python3 -m py_compile openroad_gui/app.py && echo compiled
