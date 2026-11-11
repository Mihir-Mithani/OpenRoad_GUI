# OpenROAD Flow GUI

A lightweight desktop wrapper for [OpenROAD Flow Scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts) (ORFS) that automates the RTL-to-GDSII flow with an AI-assisted EDA workstation interface.

**Pure Python 3.10+ stdlib (tkinter) — no external GUI dependencies.**

---

## Features

### Flow Execution
- **6-stage pipeline**: Synthesis → Floorplan → Placement → CTS → Routing → GDSII
- **Full pipeline** run with automatic stage sequencing
- **Per-stage execution** with live log streaming
- **OpenROAD GUI viewers** at each stage (Synthesis, Floorplan, Placement, CTS, Routing, Final)
- **Make Clean** targets for individual stages

### Project Management
- **Project Tree**: Browse `flow/designs/` and `flow/results/<pdk>/<design>/`
- **New Design Wizard**: Create starter files (Verilog, SDC, config.mk, testbench, config.json) for any supported PDK
- **Context menus**: Add template files to any design directory
- **Active Design**: Click any `config.mk` to set as active design

### Visualization
- **KLayout Integration**: View GDS files with one click
- **GDS Preview**: In-app PNG layout preview via KLayout batch mode
- **GDS Metadata Parser**: Stdlib-only parser showing library, structures, units
- **Terminal/Log Panel**: Color-coded streaming output (stdout/stderr/info/error) + **interactive PTY terminal**

### AI-Assisted Intelligence
- **Failure Predictor**: LightGBM model (AUC 0.755) for timing/DRC/congestion/power violation prediction
- **PPA Prediction**: Surrogate models (LightGBM + MLP ensemble) for WNS/TNS/Area/Power estimation
- **PPA Analysis Panel**: Predicted vs Actual metrics with Diff% comparison
- **Optimization Suggestions**: AI-driven parameter recommendations
- **ONNX Export**: Deploy trained models via ONNX Runtime

### Modern UI
- **Light/Dark theme** with professional color schemes
- **Responsive 4-zone layout**: Navigation rail → Workspace → Right rail
- **Pipeline Row**: Visual 7-node pipeline (6 stages + Signoff) with animated running state
- **Quick Metrics Cards**: WNS, TNS, Power, Area, DRC, LVS at a glance
- **Task Assistant**: Auto-captured warnings/errors from flow logs
- **Resource Monitor**: Live CPU/Memory/Disk sparklines (requires `psutil`)

---

## Requirements

- **Python 3.10+** with tkinter (included with most Python installs)
- **ORFS** (OpenROAD Flow Scripts) installation with `use-openroad.sh`
- **make**, **bash**, **Yosys**, **OpenROAD** on PATH (via ORFS env script)
- **KLayout** (for GDS viewing/preview) — auto-detected or set in Settings
- **psutil** (optional, for Resource Monitor): `pip install psutil`
- **lightgbm**, **torch**, **onnx**, **onnxruntime** (optional, for AI models)

---

## Quick Start

```bash
# Clone and run
git clone https://github.com/Mihir-Mithani/OpenRoad_GUI.git
cd OpenRoad_GUI

python3 -m venv .venv
source .venv/bin/activate

# Optional: install AI dependencies
pip install psutil lightgbm torch onnx onnxruntime scikit-learn pandas joblib

python3 main.py
```

Or directly if environment is ready:
```bash
python3 main.py
```

---

## First-Time Setup

1. **Settings → Paths**
   - **OpenROAD Root**: Select your ORFS checkout (must contain `flow/` and `use-openroad.sh`)
   - **KLayout binary**: Auto-detected from PATH, or browse to executable

2. **Settings → Active Design**
   - Select Platform (PDK), Design Name, and `config.mk` path
   - Or click a `config.mk` in the Project Tree to activate

3. **Create a New Design** (optional)
   - Click **New Design** in the sidebar
   - Choose PDK and design name → generates complete starter file set

---

## Running the Flow

| Button / Menu | Equivalent Command |
|---------------|-------------------|
| Synthesis | `make DESIGN_CONFIG=... synth` |
| Floorplan | `make DESIGN_CONFIG=... floorplan` |
| Core Placement | `make DESIGN_CONFIG=... place` |
| CTS | `make DESIGN_CONFIG=... cts` |
| Routing & DRC | `make DESIGN_CONFIG=... route` |
| GDSII Generation | `make DESIGN_CONFIG=... <gds_target>` |
| **Run Full Pipeline** | All 6 stages in sequence |

The app automatically runs `source use-openroad.sh` before each `make` invocation. Logs stream live into the Terminal/Log panel.

---

## Project Structure

```
OpenRoad_GUI/
├── main.py                      # Entry point
├── openroad_gui/
│   ├── app.py                   # Main window + 4-zone layout
│   ├── config.py                # Persistent config (~/.config/openroad-gui/config.json)
│   ├── flow_runner.py           # Threaded subprocess flow execution
│   ├── templates.py             # RTL/SDC/config template generators
│   ├── viewers.py               # KLayout, OpenROAD GUI, GDS preview
│   ├── gds_info.py              # Stdlib-only GDSII parser
│   ├── theme.py                 # Light/Dark theme manager
│   ├── intelligence/            # AI/ML modules
│   │   ├── models/
│   │   │   ├── flow_optimizer.py    # RL state/action/reward design
│   │   │   └── failure_predictor.py # LightGBM failure prediction
│   │   ├── utils/
│   │   │   └── onnx_export.py       # ONNX export + inference
│   │   └── data/
│   │       ├── parser.py            # Log/report parsing
│   │       ├── collector.py         # Historical data collection
│   │       └── collect_real_data.py # Real ORFS metrics collector
│   └── widgets/
│       ├── project_tree.py      # Workspace tree + context menus
│       ├── flow_panel.py        # Legacy stage buttons (hidden, for compat)
│       ├── pipeline_row.py      # Visual pipeline with 7 nodes
│       ├── log_viewer.py        # Streaming log + interactive PTY terminal
│       ├── preview_panel.py     # Text + Layout (PNG) preview tabs
│       ├── settings_dialog.py   # 3-tab settings (Paths/Design/Environment)
│       └── sidebar.py           # Task Assistant + Resource Monitor
├── tests/                       # Unit tests (pytest)
│   ├── test_config.py
│   ├── test_flow_runner.py
│   ├── test_templates.py
│   └── test_gds_info.py
└── README.md
```

---

## Context Menu (Right-click a Design Folder)

- New Verilog (`.v`)
- New Testbench (`.tb`)
- New SDC (`.sdc`)
- New `config.mk`
- New `config.json`

---

## Viewing Results

### GDS Files
- Active design results appear under **results (<design>)** in the Project Tree
- **Double-click** a `.gds` file → opens in KLayout
- **Right-click** → *View in KLayout* or *Preview Layout*
- **Layout tab** shows in-app PNG preview (via KLayout batch)
- **View → GDS** menu or **View GDS in KLayout** button opens `6_final.gds`

### OpenROAD GUI
- **OpenROAD GUI Viewer** buttons (Synthesis, Floorplan, Placement, CTS, Routing, Final)
- **View → OpenROAD GUI** menu for any stage
- **Right-click** any `.odb` checkpoint → *View in OpenROAD GUI*
- Equivalent to `make DESIGN_CONFIG=... gui_synth`, `gui_floorplan`, etc.

### Reports
- **Open Reports Folder** button opens `flow/reports/<pdk>/<design>/base/`
- Individual report buttons: Timing, Power, Area, DRC, LVS
- **Generate GDSII** button runs the GDS stage directly

---

## AI Intelligence Usage

### Failure Prediction
1. Run at least one flow stage to generate reports
2. **Intelligence → Predict Failure Risk** or click "Predict Failure Risk" in AI panel
3. View probability, severity, and mitigation suggestions

### PPA Prediction
1. Ensure surrogate models are trained (see `intelligence/training/`)
2. **Intelligence → Show Surrogate Predictions** or click "Run Prediction" in PPA panel
3. Predicted values populate the **Predicted** column
4. After GDS completion, **Actual** column auto-populates from reports
5. **Diff%** shows prediction accuracy

### Model Training
```bash
# Generate training data from completed ORFS runs
python -m openroad_gui.intelligence.data.collect_real_data \
    --orfs-root ~/OpenROAD-flow-scripts \
    --platform asap7 \
    --output data/real_runs.json

# Train surrogate models
python -m openroad_gui.intelligence.training.train_surrogate \
    --data data/real_runs.json \
    --output openroad_gui/intelligence/models/saved/

# Export to ONNX for deployment
python -m openroad_gui.intelligence.utils.onnx_export \
    --model-dir openroad_gui/intelligence/models/saved/
```

---

## Configuration

Stored at `~/.config/openroad-gui/config.json`:

```json
{
  "orfs_root": "/path/to/OpenROAD-flow-scripts",
  "klayout_cmd": "/Applications/KLayout/klayout.app/Contents/MacOS/klayout",
  "design_config": "./designs/asap7/alu4/config.mk",
  "platform": "asap7",
  "design_name": "alu4",
  "extra_env": {},
  "last_project_dir": ""
}
```

### Supported Platforms (PDKs)
- `asap7`, `nangate45`, `sky130hd`, `sky130hs`
- `gf12`, `gf180`, `ihp-sg13g2`

Add new PDKs by adding to `PLATFORMS` in `config.py` — no other code changes needed.

---

## Testing

```bash
# All tests
python -m pytest tests/ -v

# Single test module
python -m pytest tests/test_config.py -v
python -m pytest tests/test_flow_runner.py -v
python -m pytest tests/test_templates.py -v
python -m pytest tests/test_gds_info.py -v
```

**91 unit tests** covering config, flow runner, templates, and GDS parser. All tests mock external dependencies (no ORFS/KLayout required).

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | Toggle Dark/Light theme |
| `Ctrl+D` | Toggle dark mode |
| `Ctrl+N` | New Design |
| `Ctrl+O` | Open Project |
| `Ctrl+S` | Save Project |
| `Ctrl+,` | Settings |
| `Ctrl+Q` | Quit |

---

## Example: 4-bit ALU (asap7)

With default paths pointing at your ORFS install:

1. Open the GUI — `alu4` design under `designs/asap7/alu4/` appears
2. Click `config.mk` to activate it
3. Click **Run Full RTL-to-GDSII Pipeline** or run stages individually
4. GDS output: `flow/results/asap7/alu4/base/6_final.gds`

---

## License

BSD 3-Clause License. See [LICENSE](LICENSE) for details.

OpenROAD Flow GUI uses OpenROAD Flow Scripts (ORFS) and other external tools as dependencies. Those projects remain subject to their respective licenses.

---

## Version History

- **v3.0.0** (current) — AI-assisted EDA workstation: pipeline visualization, PPA prediction, failure prediction, surrogate models, ONNX export, interactive terminal, task assistant, resource monitor, modern theming
- **v2.0.0** — Resizable panes, fixed toolbar, tooltips, progress bars, log export, 2×3 grid
- **v1.0.0** — Initial release: flow execution, GDS preview, OpenROAD GUI launch, design templating

---

Built for EDA engineers who want a clean, scriptable, AI-enhanced workflow. Issues, suggestions, and PRs welcome.