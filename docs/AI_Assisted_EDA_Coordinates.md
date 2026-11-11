# AI-Assisted EDA: Panel and Element Coordinates

**Source:** `gui_update.md` (OpenRoad_GUI update specification).  
**Change applied:** the **Flow Progress** panel is removed. **Quick Metrics (Current Run)** now spans the full central workspace width.

## Conventions

- Reference viewport: **1536 × 1024 px**. Origin `(0, 0)` is the top-left of the window.
- Every rectangle is `(x, y, w, h)` in px. Right edge = `x + w`; bottom edge = `y + h`.
- **Panel bounds** come from the spec (§2). **Element bounds** are derived from the spec's layout rules (12 px card padding, 8 px spacing unit, 32–36 px rows, 36 px stage nodes) and are starting estimates, not measurements of the mockup.
- Treat all values as guidance for a responsive Tk layout (`grid` / `pack` with weights), not as hard-coded absolute positions.
- Elements marked *only if implemented / only if present* must reuse real existing handlers; do not add inert controls.

## 1. Region and panel map

| Panel / region | x | y | w | h | Right edge | Bottom edge | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| Native title bar | 0 | 0 | 1536 | 30 | 1536 | 30 | OS-managed |
| Application header | 0 | 30 | 1536 | 62 | 1536 | 92 | Full width; brand + theme/help only, no navigation |
| Left navigation rail | 0 | 92 | 212 | 932 | 212 | 1024 |  |
| Main workspace (container) | 212 | 92 | 918 | 932 | 1130 | 1024 | Panels inset ~11 px from rail edges |
| Right analysis rail (container) | 1130 | 92 | 406 | 932 | 1536 | 1024 | Panels inset ~1 px; ~11 px gap to workspace |
| Design Flow (RTL → GDSII) | 223 | 103 | 896 | 150 | 1119 | 253 | Workspace band 1 |
| Design Inputs | 223 | 264 | 307 | 366 | 530 | 630 | Workspace band 2, left |
| Layout Viewer | 541 | 264 | 578 | 366 | 1119 | 630 | Workspace band 2, right |
| Terminal / Flow Log | 223 | 641 | 896 | 237 | 1119 | 878 | Workspace band 3 |
| Quick Metrics (Current Run) | 223 | 889 | 896 | 113 | 1119 | 1002 | Workspace band 4, full width |
| AI Assistant | 1131 | 104 | 395 | 412 | 1526 | 516 | Right rail |
| PPA Analysis (AI Prediction) | 1131 | 527 | 395 | 171 | 1526 | 698 | Right rail |
| Optimization Suggestions | 1131 | 709 | 395 | 168 | 1526 | 877 | Right rail |
| Reports | 1131 | 888 | 395 | 114 | 1526 | 1002 | Right rail |

**Removed:** Flow Progress `(223, 889, 300, 113)`, including its heading, stage/status text, progress bar, percentage label and elapsed/remaining time. Quick Metrics grows from `(534, 889, 589, 113)` to `(223, 889, 896, 113)`.

**Vertical bands, central workspace:** pipeline `y 103–253` → inputs/viewer `y 264–630` → log `y 641–878` → metrics `y 889–1002` (≈11 px gaps).  
**Vertical stack, right rail:** AI `y 104–516` → PPA `y 527–698` → Optimization `y 709–877` → Reports `y 888–1002` (≈11 px gaps).

## 2. Application Header

**Panel bounds:** `(0, 30, 1536, 62)`  
Top navigation (Home, Flow, Design, Run, Results, AI Assistant, Settings) removed; header keeps the brand block and right-side actions.

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Chip / IC icon | 16 | 40 | 42 | 42 | Brand icon, 12–18 px left inset |
| Title: `AI-Assisted EDA` | 68 | 38 | 240 | 28 | 22–25 px, semibold/bold |
| Subtitle: `OpenROAD GUI for RTL-to-GDSII Flow` | 68 | 66 | 300 | 16 | Secondary text |
| Light/dark theme toggle (pill) | 1388 | 45 | 96 | 32 | Uses centralized theme mechanism |
| Help icon | 1496 | 45 | 32 | 32 | Opens existing docs/about or a real help panel |

## 3. Left Navigation Rail

**Panel bounds:** `(0, 92, 212, 932)`  
Rail content inset 12 px; thin right border; scrolls if content exceeds height.

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Section heading: Project | 12 | 104 | 188 | 22 | Semibold small heading |
| 1.1 New Project (primary button) | 12 | 128 | 188 | 34 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 1.2 Open Project | 12 | 164 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 1.3 Save Project | 12 | 198 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| Section heading: Design Inputs | 12 | 240 | 188 | 22 | Semibold small heading |
| 2.1 RTL (Verilog / SystemVerilog) | 12 | 264 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 2.2 Technology (Lib, LEF) | 12 | 298 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 2.3 Constraints (SDC) | 12 | 332 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 2.4 Floorplan / Config | 12 | 366 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| Section heading: Flow Configuration | 12 | 408 | 188 | 22 | Semibold small heading |
| 3.1 Flow Steps | 12 | 432 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 3.2 Parameter Tuning | 12 | 466 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 3.3 AI Optimization | 12 | 500 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| Section heading: Run & Monitor | 12 | 542 | 188 | 22 | Semibold small heading |
| 4.1 Start Flow | 12 | 566 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 4.2 Stop | 12 | 600 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 4.3 View Logs | 12 | 634 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| Section heading: Results & Analysis | 12 | 676 | 188 | 22 | Semibold small heading |
| 5.1 Reports (PPA) | 12 | 700 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 5.2 Layout Viewer | 12 | 734 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 5.3 Timing Analysis | 12 | 768 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 5.4 Power Analysis | 12 | 802 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 5.5 DRC/LVS (Optional) | 12 | 836 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| Section heading: Utilities | 12 | 878 | 188 | 22 | Semibold small heading |
| 6.1 Scripting (TCL) | 12 | 902 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 6.2 Docs & Help | 12 | 936 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |
| 6.3 About | 12 | 970 | 188 | 32 | Row: icon at (x+8, y+8, 16×16), label at x+32 |

## 4. Design Flow (RTL → GDSII)

**Panel bounds:** `(223, 103, 896, 150)`  
Nodes evenly spaced: center x = 287 + 128·(n−1); circle Ø 36 px.

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Title: `Design Flow (RTL → GDSII)` | 235 | 113 | 320 | 22 | Top-left |
| Run Full Flow button (play icon) | 957 | 111 | 150 | 34 | Top-right, primary blue |
| Stage connector line (behind nodes) | 287 | 177 | 768 | 2 | Green = done, slate = pending |
| Node 1 circle: Synthesis (Yosys) | 269 | 160 | 36 | 36 | Center x=287, y=178 |
| Node 1 label | 227 | 200 | 120 | 34 | Maps to existing stage handler |
| Node 2 circle: Floorplanning | 397 | 160 | 36 | 36 | Center x=415, y=178 |
| Node 2 label | 355 | 200 | 120 | 34 | Maps to existing stage handler |
| Node 3 circle: Placement | 525 | 160 | 36 | 36 | Center x=543, y=178 |
| Node 3 label | 483 | 200 | 120 | 34 | Maps to existing stage handler |
| Node 4 circle: Clock Tree Synthesis | 653 | 160 | 36 | 36 | Center x=671, y=178 |
| Node 4 label | 611 | 200 | 120 | 34 | Maps to existing stage handler |
| Node 5 circle: Routing | 781 | 160 | 36 | 36 | Center x=799, y=178 |
| Node 5 label | 739 | 200 | 120 | 34 | Maps to existing stage handler |
| Node 6 circle: Signoff (DRC/LVS) | 909 | 160 | 36 | 36 | Center x=927, y=178 |
| Node 6 label | 867 | 200 | 120 | 34 | Status badge only (not a runnable stage) |
| Node 7 circle: GDSII Export | 1037 | 160 | 36 | 36 | Center x=1055, y=178 |
| Node 7 label | 995 | 200 | 120 | 34 | Maps to existing stage handler |

## 5. Design Inputs

**Panel bounds:** `(223, 264, 307, 366)`

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Title: `Design Inputs` | 235 | 274 | 283 | 22 |  |
| Row 1 label: Project Name | 235 | 304 | 100 | 32 | Left column |
| Row 1 field | 339 | 304 | 179 | 32 | Read-only unless rename is supported |
| Row 2 label: RTL File | 235 | 342 | 100 | 32 | Left column |
| Row 2 field | 339 | 342 | 144 | 32 | Truncate path; tooltip shows full path |
| Row 2 browse (folder) icon | 487 | 342 | 31 | 32 | Existing file-selection logic |
| Row 3 label: Technology LIB | 235 | 380 | 100 | 32 | Left column |
| Row 3 field | 339 | 380 | 144 | 32 | Truncate path; tooltip shows full path |
| Row 3 browse (folder) icon | 487 | 380 | 31 | 32 | Existing file-selection logic |
| Row 4 label: LEF Files | 235 | 418 | 100 | 32 | Left column |
| Row 4 field | 339 | 418 | 144 | 32 | Truncate path; tooltip shows full path |
| Row 4 browse (folder) icon | 487 | 418 | 31 | 32 | Existing file-selection logic |
| Row 5 label: Constraints (SDC) | 235 | 456 | 100 | 32 | Left column |
| Row 5 field | 339 | 456 | 144 | 32 | Truncate path; tooltip shows full path |
| Row 5 browse (folder) icon | 487 | 456 | 31 | 32 | Existing file-selection logic |
| Row 6 label: Config / Floorplan | 235 | 494 | 100 | 32 | Left column |
| Row 6 field | 339 | 494 | 144 | 32 | Truncate path; tooltip shows full path |
| Row 6 browse (folder) icon | 487 | 494 | 31 | 32 | Existing file-selection logic |
| Button: `Load Inputs` (primary) | 235 | 548 | 283 | 32 | Only if a real load/validate handler exists |
| Button: `View / Edit Files` | 235 | 584 | 283 | 32 | Existing editor / project-tree actions |

## 6. Layout Viewer

**Panel bounds:** `(541, 264, 578, 366)`  
Viewer options/config must be preserved exactly as implemented.

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Title: `Layout Viewer` | 553 | 274 | 200 | 22 |  |
| Tab: `Layout Visualizer` | 553 | 302 | 150 | 32 | Keep existing preview tab names/actions |
| Tab: `Text Editor` | 707 | 302 | 110 | 32 | Keep existing preview tab names/actions |
| View selector: `Top View` | 831 | 302 | 100 | 32 | Only if present in current app; keep all values/defaults |
| Toolbar icon 1 (zoom / search / fit) | 1003 | 302 | 32 | 32 | Real existing controls only |
| Toolbar icon 2 (zoom / search / fit) | 1039 | 302 | 32 | 32 | Real existing controls only |
| Toolbar icon 3 (zoom / search / fit) | 1075 | 302 | 32 | 32 | Real existing controls only |
| Preview canvas (near-black) | 553 | 342 | 554 | 276 | Real render or empty-state message; no fake chip |

## 7. Terminal / Flow Log

**Panel bounds:** `(223, 641, 896, 237)`

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Title: `Terminal / Flow Log` | 235 | 651 | 200 | 22 |  |
| Tab: `OpenROAD Log` | 235 | 679 | 130 | 30 | Actual stdout/stderr |
| Tab: `TCL Console` | 369 | 679 | 120 | 30 | Only if implemented and validated |
| Tab: `Errors / Warnings` | 493 | 679 | 150 | 30 | Mirrors the same log event source |
| Search logs input | 787 | 679 | 184 | 30 |  |
| Lock / auto-scroll toggle | 975 | 679 | 30 | 30 | Only if supported |
| Copy button | 1009 | 679 | 30 | 30 | Only if implemented |
| Export log button | 1043 | 679 | 30 | 30 | Maps to existing `Export Log...` |
| Clear log button | 1077 | 679 | 30 | 30 | Maps to existing Clear handler |
| Log text area (monospace, `LOG_BG`) | 235 | 717 | 858 | 149 | Prefixes INFO / WARN / ERROR |
| Vertical scrollbar | 1093 | 717 | 14 | 149 |  |

## 8. Quick Metrics (Current Run)

**Panel bounds:** `(223, 889, 896, 113)`  
Now spans the full central width (was 589 px wide beside Flow Progress).

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Title: `Quick Metrics (Current Run)` | 235 | 897 | 300 | 20 |  |
| Card 1: WNS (ns) | 235 | 921 | 138 | 72 | Label (x+10,y+6), value (x+10,y+26), unit/source (x+10,y+54) |
| Card 2: TNS (ns) | 381 | 921 | 138 | 72 | Label (x+10,y+6), value (x+10,y+26), unit/source (x+10,y+54) |
| Card 3: Total Power (mW) | 527 | 921 | 138 | 72 | Label (x+10,y+6), value (x+10,y+26), unit/source (x+10,y+54) |
| Card 4: Cell Area (µm²) | 673 | 921 | 138 | 72 | Label (x+10,y+6), value (x+10,y+26), unit/source (x+10,y+54) |
| Card 5: DRC Violations | 819 | 921 | 138 | 72 | Label (x+10,y+6), value (x+10,y+26), unit/source (x+10,y+54) |
| Card 6: LVS | 965 | 921 | 138 | 72 | Label (x+10,y+6), value (x+10,y+26), unit/source (x+10,y+54) |

## 9. AI Assistant

**Panel bounds:** `(1131, 104, 395, 412)`

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Robot / AI icon | 1143 | 114 | 24 | 24 |  |
| Title: `AI Assistant` | 1173 | 115 | 150 | 22 |  |
| `Clear Chat` button | 1429 | 113 | 85 | 26 | Only when conversation state exists |
| Intro / conversation area | 1143 | 146 | 371 | 64 | `How can I help you with your design today?`; scrolls |
| Action chip 1: Suggest optimal floorplan parameters | 1143 | 216 | 371 | 32 | Disable if backend not implemented |
| Action chip 2: Predict PPA for current design | 1143 | 254 | 371 | 32 | Disable if backend not implemented |
| Action chip 3: Recommend better configuration | 1143 | 292 | 371 | 32 | Disable if backend not implemented |
| Action chip 4: Explain STA violations | 1143 | 330 | 371 | 32 | Disable if backend not implemented |
| Action chip 5: Help me fix routing congestion | 1143 | 368 | 371 | 32 | Disable if backend not implemented |
| Action chip 6: Generate TCL script for custom flow | 1143 | 406 | 371 | 32 | Disable if backend not implemented |
| Chat input (`Type your question...`) | 1143 | 466 | 331 | 34 | Placeholder text |
| Send arrow button | 1478 | 466 | 36 | 34 |  |

## 10. PPA Analysis (AI Prediction)

**Panel bounds:** `(1131, 527, 395, 171)`

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Title: `PPA Analysis (AI Prediction)` | 1143 | 537 | 260 | 22 |  |
| `Run Prediction` button | 1409 | 533 | 105 | 28 | Runs existing inference only |
| Card 1: Power | 1143 | 571 | 118 | 104 | Icon (x+8,y+8,20×20), label (x+32,y+10), value (x+8,y+40), unit/status (x+8,y+76) |
| Card 2: Performance (WNS) | 1269 | 571 | 118 | 104 | Icon (x+8,y+8,20×20), label (x+32,y+10), value (x+8,y+40), unit/status (x+8,y+76) |
| Card 3: Area | 1395 | 571 | 118 | 104 | Icon (x+8,y+8,20×20), label (x+32,y+10), value (x+8,y+40), unit/status (x+8,y+76) |

## 11. Optimization Suggestions

**Panel bounds:** `(1131, 709, 395, 168)`  
Up to four recommendations.

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Bulb icon | 1143 | 719 | 20 | 20 |  |
| Title: `Optimization Suggestions` | 1169 | 719 | 220 | 22 |  |
| `Apply Suggestion` button | 1389 | 715 | 125 | 28 | Requires diff preview + confirmation |
| Suggestion 1 number | 1143 | 751 | 20 | 26 |  |
| Suggestion 1 text | 1167 | 751 | 250 | 26 | Parameter/value + short reason |
| Suggestion 1 predicted impact | 1421 | 751 | 93 | 26 | Right-aligned |
| Suggestion 2 number | 1143 | 779 | 20 | 26 |  |
| Suggestion 2 text | 1167 | 779 | 250 | 26 | Parameter/value + short reason |
| Suggestion 2 predicted impact | 1421 | 779 | 93 | 26 | Right-aligned |
| Suggestion 3 number | 1143 | 807 | 20 | 26 |  |
| Suggestion 3 text | 1167 | 807 | 250 | 26 | Parameter/value + short reason |
| Suggestion 3 predicted impact | 1421 | 807 | 93 | 26 | Right-aligned |
| Suggestion 4 number | 1143 | 835 | 20 | 26 |  |
| Suggestion 4 text | 1167 | 835 | 250 | 26 | Parameter/value + short reason |
| Suggestion 4 predicted impact | 1421 | 835 | 93 | 26 | Right-aligned |

## 12. Reports

**Panel bounds:** `(1131, 888, 395, 114)`

| Element | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Title: `Reports` | 1143 | 894 | 120 | 20 |  |
| Button r1c1: Timing Report | 1143 | 918 | 118 | 30 |  |
| Button r1c2: Power Report | 1269 | 918 | 118 | 30 |  |
| Button r1c3: Area Report | 1395 | 918 | 118 | 30 |  |
| Button r2c1: DRC Report | 1143 | 954 | 118 | 30 |  |
| Button r2c2: LVS Report | 1269 | 954 | 118 | 30 |  |
| Button r2c3: Generate GDSII | 1395 | 954 | 118 | 30 |  |

## Notes on conditional elements

- **Signoff (DRC/LVS)** node: shown for visual match; it displays real report status only and is not a runnable stage. A strict six-node alternative is allowed by the spec: use six centers at `x = 223 + 74.67 + 149.33·(n−1)` and move signoff to a status badge in Reports.
- **Layout Viewer** toolbar names, selector values and icons must follow what the repository already implements.
- **TCL Console**, lock, copy and the **AI Assistant** actions appear only when backed by working implementations.
- Metric cards show `—` or `Not available` when data is missing, never zero or mockup example values.
