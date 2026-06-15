# OpenROAD Flow GUI

A lightweight desktop wrapper for [OpenROAD Flow Scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts) (ORFS). It automates project setup, file templating, environment sourcing, and one-click execution of the RTL-to-GDSII pipeline.

## Requirements

- Python 3.10+ with **tkinter** (included with most Python installs on macOS)
- A working ORFS installation with `use-openroad.sh`
- `make`, `bash`, Yosys, and OpenROAD on your PATH (via the ORFS env script)
- KLayout (for GDS export) — set `KLAYOUT_CMD` in Settings

## Quick Start

```bash
cd "/Users/mihirmithani/Downloads/OpenRoad GUI"

# Optional: use the project venv
python3 -m venv .venv
source .venv/bin/activate

# Launch the GUI
python main.py
```

## First-Time Setup

1. **Settings → Paths**
   - **OpenROAD Root**: path to your ORFS checkout, e.g.
     `/Users/mihirmithani/Documents/Codex/2026-06-02/i-want-you-to-setup-openroad/OpenROAD-flow-scripts`
   - **KLayout binary**: e.g.
     `/Applications/KLayout/klayout.app/Contents/MacOS/klayout`

2. **Settings → Active Design**
   - Set platform (`asap7`), design name (`alu4`), and `config.mk` path
   - Or click any `config.mk` in the project tree to activate it

3. **Create a new design** (optional)
   - Click **New Design** in the sidebar
   - Choose PDK and name — starter `*.v`, `*.sdc`, `config.mk`, and `*.tb` files are created

## Running the Flow

| Button | Equivalent command |
|--------|-------------------|
| Synthesis | `make DESIGN_CONFIG=... synth` |
| Floorplan | `make DESIGN_CONFIG=... floorplan` |
| Core Placement | `make DESIGN_CONFIG=... place` |
| CTS | `make DESIGN_CONFIG=... cts` |
| Routing & DRC | `make DESIGN_CONFIG=... route` |
| GDSII Generation | `make DESIGN_CONFIG=... results/<pdk>/<design>/base/6_final.gds` |
| Full Pipeline | All stages in sequence |

The app automatically runs `source use-openroad.sh` before each `make` invocation. Logs stream live into the bottom panel.

## Project Layout

```
OpenRoad GUI/
├── main.py                      # Entry point
├── openroad_gui/
│   ├── app.py                   # Main window
│   ├── config.py                # Saved settings (~/.config/openroad-gui/config.json)
│   ├── flow_runner.py           # Subprocess flow execution
│   ├── templates.py             # RTL/SDC/config templates
│   └── widgets/
│       ├── project_tree.py      # Workspace tree + new design
│       ├── flow_panel.py        # Stage buttons
│       ├── log_viewer.py        # Terminal output
│       └── settings_dialog.py   # Paths & environment
└── requirements.txt
```

## Context Menu (right-click a design folder)

- New Verilog (`.v`)
- New Testbench (`.tb`)
- New SDC (`.sdc`)
- New `config.mk` / `config.json`

## Viewing Results

### GDS files
- Active design results appear under **results (&lt;design&gt;)** in the project tree.
- **Double-click** a `.gds` file to open it in KLayout.
- **Right-click** a `.gds` file for *View in KLayout* or *Preview Layout*.
- The **Layout** tab shows an in-app PNG preview (rendered via KLayout batch mode).
- **View → GDS** menu or **View GDS in KLayout** button opens `6_final.gds`.

### OpenROAD GUI
- Use the **OpenROAD GUI Viewer** buttons (Synthesis, Floorplan, Placement, CTS, Routing, Final).
- Or **View → OpenROAD GUI** menu to open the interactive layout viewer at each stage.
- **Right-click** any `.odb` checkpoint → *View in OpenROAD GUI*.
- Equivalent to `make DESIGN_CONFIG=... gui_route`, `gui_final`, etc.

## Tips

- Right-click a design directory to add individual template files.
- Extra env vars (e.g. `KLAYOUT_CMD`) can be set in **Settings → Environment**.
- Config is stored at `~/.config/openroad-gui/config.json`.

## Example: 4-bit ALU (asap7)

With the default paths pointing at your ORFS install:

1. Open the GUI — the `alu4` design under `designs/asap7/alu4/` should appear.
2. Click `config.mk` to activate it.
3. Click **Run Full RTL-to-GDSII Pipeline** or run stages individually.
4. GDS output: `flow/results/asap7/alu4/base/6_final.gds`
