# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenROAD Flow GUI — A lightweight desktop wrapper for [OpenROAD Flow Scripts (ORFS)](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts) that automates the RTL-to-GDSII flow. Built with Python 3.10+ and tkinter (stdlib only, no external GUI deps).

## Commands

### Run the Application
```bash
cd "/Users/mihirmithani/Downloads/OpenRoad GUI"
python main.py
# or
python -m openroad_gui
```

### Run Tests
```bash
# All tests
python -m pytest tests/ -v

# Single test module
python -m pytest tests/test_config.py -v
python -m pytest tests/test_flow_runner.py -v
python -m pytest tests/test_templates.py -v
python -m pytest tests/test_gds_info.py -v

# Single test function
python -m pytest tests/test_config.py::TestAppConfig::test_validate_valid -v
```

### Lint/Type Check (if configured)
```bash
# No formal lint config present; uses standard Python conventions
python -m py_compile openroad_gui/**/*.py
```

### Virtual Environment (Optional)
```bash
python3 -m venv .venv
source .venv/bin/activate
# No requirements.txt dependencies (stdlib only)
```

## Architecture

### Entry Point
- `main.py` → `openroad_gui.app.run()` — Creates `OpenRoadGUI` (subclasses `tk.Tk`) and starts mainloop.

### Core Modules (`openroad_gui/`)

| Module | Responsibility |
|--------|----------------|
| `config.py` | Persistent config (`~/.config/openroad-gui/config.json`), `AppConfig` dataclass, validation, path properties (`flow_dir`, `designs_dir`, `results_dir`, `gds_target()`) |
| `flow_runner.py` | `FlowRunner` — Threaded subprocess execution of `make` targets via `source use-openroad.sh`. `FlowStage` enum (SYNTH, FLOORPLAN, PLACE, CTS, ROUTE, GDS), `FULL_PIPELINE` list. Streaming stdout/stderr to Tk callbacks. |
| `viewers.py` | `ViewerService` — External tool launching: KLayout (GDS view), KLayout batch (GDS→PNG preview), OpenROAD GUI (`make gui_*`). `OpenROADGuiStage` enum. |
| `templates.py` | `create_design(dir, pdk, name)` — Generates starter files: `.v`, `.sdc`, `config.mk`, `config.json`, `.tb`. Individual `write_template_file()` for ad-hoc additions. |
| `gds_info.py` | Stdlib-only GDSII parser (`parse_gds()` → `GdsInfo` dataclass with `library_name`, `structures`, `units`). |
| `app.py` | Main window (`OpenRoadGUI`): menu bar, paned layout (ProjectTree left, FlowPanel+PreviewPanel+LogViewer right), event wiring, config apply/refresh. |

### Widgets (`openroad_gui/widgets/`)

| Widget | Purpose |
|--------|---------|
| `project_tree.py` | Treeview of `flow/designs/` + `results/<pdk>/<design>/`. Context menus: New Design, New File (verilog/tb/sdc/config), Open Folder. Double-click actions per file type. |
| `flow_panel.py` | Stage buttons (6 stages), OpenROAD GUI buttons (6 stages), "Run Full Pipeline", "Stop", "View GDS", status label. |
| `log_viewer.py` | `ScrolledText` with color tags: stdout (white), stderr (red), info (cyan), error (red bold). |
| `preview_panel.py` | Notebook: Text tab (file content / GDS metadata), Layout tab (GDS→PNG via KLayout batch). Actions: Open in Editor, Use as config.mk, View GDS, Preview, OpenROAD GUI. |
| `settings_dialog.py` | 3-tab dialog: Paths (ORFS root, KLayout), Active Design (platform, name, config.mk), Environment (extra env vars). |

### Data Flow

```
SettingsDialog → AppConfig → save_config() → ~/.config/openroad-gui/config.json
                                    ↓
                    OpenRoadGUI._apply_config() → FlowRunner(config) + ViewerService(config)
                                    ↓
                    ProjectTree.set_root(flow_dir, results_dir)
                                    ↓
                    User clicks stage button → FlowRunner.run_stage(stage, log_cb, done_cb)
                                    ↓
                    Thread: subprocess.Popen(bash -lc "source use-openroad.sh && make ...")
                                    ↓
                    stdout/stderr lines → log_cb("stdout"/"stderr", line) → LogViewer.append()
                                    ↓
                    done_cb(exit_code, stage_label) → FlowPanel.set_status() + tree refresh
```

### Configuration (`AppConfig`)

Stored at `~/.config/openroad-gui/config.json`. Key fields:
- `orfs_root` — Path to ORFS checkout (must contain `flow/`, `use-openroad.sh`)
- `klayout_cmd` — Path to KLayout binary
- `design_config` — Relative path to active `config.mk` (e.g., `./designs/asap7/alu4/config.mk`)
- `platform` — PDK name (`asap7`, `sky130hd`, `sky130hs`, `nangate45`, `gf12`, `gf180`, `ihp-sg13g2`)
- `design_name` — Design directory name
- `extra_env` — Dict of extra env vars passed to `make`

Derived paths:
- `flow_dir = orfs_root / "flow"`
- `designs_dir = flow_dir / "designs"`
- `results_dir = flow_dir / "results" / platform / design_name`
- `env_script = orfs_root / "use-openroad.sh"`
- `gds_target() = "results/<pdk>/<design>/base/6_final.gds"`

### Flow Stages

| Enum | Make Target | Label |
|------|-------------|-------|
| `FlowStage.SYNTH` | `synth` | Synthesis (Yosys) |
| `FlowStage.FLOORPLAN` | `floorplan` | Floorplan / Macro Placement |
| `FlowStage.PLACE` | `place` | Core Placement |
| `FlowStage.CTS` | `cts` | Clock Tree Synthesis |
| `FlowStage.ROUTE` | `route` | Routing & DRC |
| `FlowStage.GDS` | `gds_target()` | GDSII Generation |

OpenROAD GUI stages: `gui_synth`, `gui_floorplan`, `gui_place`, `gui_cts`, `gui_route`, `gui_final`

### Adding a New PDK/Platform

1. Add to `PLATFORMS` list in `config.py`
2. Ensure ORFS has `flow/designs/<pdk>/` with a reference design
3. No code changes needed elsewhere (platform is a free-form string validated against ORFS directory structure)

### Testing Strategy

- **Unit tests only** (no integration tests requiring ORFS/KLayout)
- Mock `subprocess.Popen` in `flow_runner` tests
- Use `tempfile.TemporaryDirectory` for config/file I/O tests
- Synthetic GDSII byte streams for `gds_info` parser tests
- Run with `python -m pytest tests/ -v`

### Key Conventions

- **Threading**: Flow execution runs in daemon threads; Tk callbacks via `self.after(0, callback)`
- **Config persistence**: `save_config()` called on every settings change; `_apply_config()` rebuilds runner/viewers
- **File preview**: Text files → direct read; GDS → `parse_gds()` summary + background PNG render
- **External tools**: Launched via `subprocess.Popen` with `DEVNULL` stdout/stderr (fire-and-forget)
- **No external deps**: Only Python stdlib (`tkinter`, `subprocess`, `threading`, `json`, `pathlib`, `dataclasses`, `struct`, `tempfile`)

### Common Development Tasks

| Task | Where to Look |
|------|---------------|
| Add a new flow stage | `flow_runner.py` (`FlowStage` enum, `FULL_PIPELINE`), `flow_panel.py` (button grid), `app.py` (menu) |
| Add a template file type | `templates.py` (new template function + entry in `writers` dict), `project_tree.py` (context menu) |
| Change config schema | `config.py` (`AppConfig` dataclass, `load_config`/`save_config` field filtering) |
| Modify GDS preview | `viewers.py` (`render_gds_preview` KLayout script), `preview_panel.py` (image display) |
| Add log filtering/search | `log_viewer.py` (`LogViewer` class) |
| Change project tree structure | `project_tree.py` (`_populate_tree`, `_insert_dir`, ignored dirs/extensions) |

### Git Conventions

- Branch: `main` (default)
- Commit messages: Concise, present tense ("Add X", "Fix Y")
- No formal PR process; push to main after local testing
