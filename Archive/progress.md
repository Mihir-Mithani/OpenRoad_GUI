# OpenROAD Flow GUI - Progress Log

## Summary of Changes

This document tracks all modifications made to the OpenROAD Flow GUI project.

---

## Session 1: Layout Restructuring & Resizable Log Window

### Date: 2026-07-23

### Changes Made

#### 1. Vertical Paned Window for Preview & Log
**File:** `openroad_gui/app.py`

- Added a vertical `ttk.PanedWindow` on the right side containing:
  - Preview Panel (weight=3, 75% vertical space)
  - Log Viewer (weight=1, 25% vertical space)
- Users can now drag the divider between preview and log to resize them

**Before:** Fixed layout with `expand=False` on log viewer  
**After:** Resizable paned window with configurable weights

#### 2. Action Buttons Bar
**File:** `openroad_gui/app.py`

Added fixed action button bar above the paned window:
- Open in Editor
- Use as Active config.mk
- View GDS in KLayout
- Preview Layout
- OpenROAD GUI
- **Open Reports Folder** (NEW)
- **Export Log...** (NEW)

#### 3. Open Reports Folder Feature
**Files:** `openroad_gui/app.py`, `openroad_gui/widgets/flow_panel.py`

- **App-level:** `OpenRoadGUI._open_reports_folder()` - opens `results/<pdk>/<design>/reports/` in system file manager
- **FlowPanel-level:** `FlowPanel._open_reports_folder()` - uses `get_config` callback to access current design config
- Cross-platform support: macOS (`open`), Windows (`explorer`), Linux (`xdg-open`)

#### 4. Export Log Feature
**Files:** `openroad_gui/app.py`, `openroad_gui/widgets/log_viewer.py`

- **LogViewer:** Added "Export Log..." button in toolbar + `get_text()` method
- **App-level:** `OpenRoadGUI._export_log()` - saves log to timestamped text file via file dialog
- FlowPanel also has "Export Log..." button in action bar

#### 5. Tooltips for Flow Stage Buttons
**File:** `openroad_gui/widgets/flow_panel.py`

Added `ToolTip` class and tooltips to all 12 buttons:

**Flow Stage Buttons (6):**
| Stage | Tooltip |
|-------|---------|
| Synthesis (Yosys) | "Run logic synthesis with Yosys\nConverts RTL to gate-level netlist" |
| Floorplan / Macro Placement | "Floorplan and macro placement\nDefines die/core area, places macros and I/O pins" |
| Core Placement | "Standard cell placement\nPlaces and optimizes standard cells" |
| Clock Tree Synthesis | "Clock Tree Synthesis\nBuilds clock distribution network" |
| Routing & DRC | "Detailed routing & DRC\nRoutes signals and fixes design rule violations" |
| GDSII Generation | "GDSII stream-out\nGenerates final GDSII for fabrication" |

**OpenROAD GUI Buttons (6):**
| Stage | Tooltip |
|-------|---------|
| Synthesis | "Open OpenROAD GUI at synthesis stage\nView synthesized netlist and reports" |
| Floorplan | "Open OpenROAD GUI at floorplan stage\nInspect macro placement and power grid" |
| Placement | "Open OpenROAD GUI at placement stage\nView cell placement and congestion" |
| CTS | "Open OpenROAD GUI at CTS stage\nInspect clock tree and skew reports" |
| Routing | "Open OpenROAD GUI at routing stage\nView routing layers and DRC violations" |
| Final | "Open OpenROAD GUI at final stage\nFull design view with sign-off checks" |

#### 6. Flow Stage Layout: 2 Rows × 3 Columns
**File:** `openroad_gui/widgets/flow_panel.py`

Changed stage button grid from 3 rows × 2 columns to 2 rows × 3 columns:

```
Row 0: [Synthesis] [Floorplan] [Place]
Row 1: [CTS]      [Route]      [GDS]
```

---

## Testing

- All 90 existing unit tests pass
- Syntax validation successful for all modified files
- Import verification successful

---

## Files Modified

1. `openroad_gui/app.py` - Main window layout, action buttons, new methods
2. `openroad_gui/widgets/flow_panel.py` - Tooltip class, tooltips, layout change, new callback
3. `openroad_gui/widgets/log_viewer.py` - Export button, get_text() method

---

## Future Enhancements (Planned)

See [ENHANCEMENTS.md](ENHANCEMENTS.md) for detailed roadmap including:
- Real-time flow progress with deterministic progress bars
- Design validation on create/edit
- DRC/LVS report viewer
- Resume from failed stage
- Dark/Light theme toggle
- Run history with SQLite
- Metrics dashboard
- PyPI packaging
- Remote SSH execution
- AI-assisted flow tuning