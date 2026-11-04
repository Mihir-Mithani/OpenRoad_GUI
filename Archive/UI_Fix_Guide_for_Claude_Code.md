# AI-Assisted EDA GUI — UI Fix Guide (for Claude Code)

**Scope: presentation only.** Every change below is layout, styling, sizing, text labels, icons, spacing, or theming of existing widgets. Nothing here asks you to add, remove, or alter behavior.

Stack: Python, Tkinter/`ttk`. Reference mockup size: ~1536 × 1024. Minimum supported window: 900 × 600.

---

## 0. Ground rules (read first)

1. **Presentation only.** Edit how widgets look and where they sit. Re-use every existing callback, variable, and handler exactly as is. When you move or restyle a widget, pass the same `command=` it already has.
2. **Files you may edit:** `openroad_gui/theme.py`, `openroad_gui/app.py` (layout/composition only), and the files under `openroad_gui/widgets/` (`sidebar.py`, `pipeline_row.py`, `flow_panel.py`, `preview_panel.py`, `project_tree.py`, `log_viewer.py`, plus any card/panel widgets for the right rail).
3. **Files you must not edit:** `flow_runner.py`, `config.py`, `viewers.py`, `settings_dialog.py` logic, and everything under `intelligence/`.
4. **No new handlers, parsers, threads, timers, polling, or state.** If a visual needs data or a handler that does not exist, draw it as a static, muted placeholder (`—`, never `0`, never sample numbers) or leave it out. Do not invent behavior to fill a visual.
5. **Do not rename widget attributes, variables, or public methods.** Other code and tests reference them. Changing visible label text is fine if no test asserts the old text (grep `tests/` first).
6. **Keep existing tab names and order** (Text / Layout, Flow Log / Terminal / Errors / Warnings, etc.).
7. **Work in small commits**, one work package (WP) per commit. After each WP: run the existing test suite, launch the app, and take a screenshot at 1536 × 1024 and at 900 × 600.
8. **Layout must be responsive.** Use `grid` with `weight`/`minsize`, `sticky`, and `columnconfigure`/`rowconfigure`. No absolute `place(x=..., y=...)` for panels (small overlays such as hint text are the only exception).

### Before changing anything
- Run the test suite and note the baseline result.
- Grep the repo for hard-coded colors (`#[0-9a-fA-F]{6}`, `"black"`, `"white"`, `bg=`, `background=`) and list every place a color is set outside `theme.py`.
- List the current callback names wired to each button (sidebar, header nav, pipeline, reports, AI quick actions). You will need them in WP4 and WP10.
- Save a "before" screenshot.

---

## WP1 — Window fit and responsive grid  *(issues H1, N1, H5)*

**Symptoms:** content runs past the right and bottom of the screen; the Dark/Light toggle, Run button, Clear button, viewer right edge, and bottom cards are cut off; the center column slides under the right rail.

**Fix:**
1. **Initial size:** compute from the screen, e.g. `w = min(1536, screen_w - 40)`, `h = min(1024, screen_h - 100)`, center the window. Keep `minsize(900, 600)`.
2. **Top-level grid** inside the content area (below the header):
   - col 0: left rail, fixed width ~212, `minsize=200`, `weight=0`
   - col 1: center workspace, `weight=1`, `minsize=0`
   - col 2: right rail, fixed width ~395, `weight=0`, `minsize=320`
   - one row, `weight=1`, all children `sticky="nsew"`
3. **Why the center gets clipped:** a child requests more width than the column has (long path labels, wide buttons, un-wrapped text) and the right rail overlaps. Fix each of these:
   - Long text (config path, project paths, log lines) gets `width=`/`wraplength=` or is middle-ellipsized (see WP11). It must never force its parent wider.
   - Call `grid_propagate(False)` / `pack_propagate(False)` on the three main columns so a child cannot widen them.
   - If any container uses `pack`, pack the right rail (`side="right"`) **before** the center so it is guaranteed its space.
4. **Center workspace rows** (weights): pipeline panel fixed height (~150–190 px, `weight=0`), inputs + viewer band (`weight=3`), terminal (`weight=2`, `minsize=160`), bottom cards row (`weight=0`, ~113 px).
5. **Bands:** Design Inputs column `weight=0` (~307 px), Layout Viewer `weight=1`.
6. **Right rail:** one column of stacked cards, ~10–12 px gutters. If the window height is too small for all four cards, wrap the rail in a scrollable container (canvas + scrollbar) instead of letting cards clip.
7. **Narrow windows (< ~1150 px wide):** turn the right rail into a `ttk.Notebook` (tabs: AI Assistant, PPA, Suggestions, Reports), or move its cards beneath the center workspace in a scrollable area. Do not force 395 px of right rail into a 900 px window.
8. **Whole-window safety net:** if the content minimum exceeds the window, make the content area scrollable rather than clipped.

**Done when:** at 1536 × 1024 and 900 × 600 nothing is cut off at the right or bottom, the header buttons are fully visible, and resizing never makes the center slide under the right rail.

---

## WP2 — Centralized theme and full repaint on toggle  *(issues H2, N8, M7)*

**Symptoms:** mixed light and dark widgets (white inputs and preview in a dark theme, a dark pipeline canvas and a dark block in a light theme); toggle label changes but the UI does not repaint; log text is pale green on white.

**Fix in `theme.py`:**
1. Define **two palettes** (dark and light) as dicts of tokens, and one `apply_theme(root, mode)` that:
   - configures every `ttk.Style` (TFrame, TLabel, TButton variants, TEntry, TNotebook/TNotebook.Tab, Treeview, Scrollbar, Progressbar, Separator), and
   - recolors every classic `tk` widget (Text, Canvas, Entry, Listbox, tk.Frame, tk.Label, tk.Button).
2. Keep a small **registry** in theme.py: `theme.register(widget, role)` where `role` is a token name such as `"panel"`, `"input"`, `"log"`, `"canvas"`. `apply_theme` walks the registry and sets `bg`, `fg`, `insertbackground`, `selectbackground`, `highlightbackground`, `highlightcolor`. Replace every hard-coded color found in the pre-work grep with a registered role or a token.
3. **Default to dark** at startup (per the design spec). The toggle switches palettes and calls `apply_theme`, which must repaint everything, including canvases drawn by code (redraw pipeline nodes on theme change using the same draw function).

**Dark tokens (spec):**

| Token | Dark | Light |
|---|---|---|
| `BG_APP` | `#0A1320` | `#F4F6FA` |
| `BG_HEADER` | `#0B1524` | `#FFFFFF` |
| `BG_SIDEBAR` | `#0D1928` | `#EEF2F8` |
| `BG_PANEL` | `#101C2B` | `#FFFFFF` |
| `BG_ELEVATED` | `#142337` | `#F1F4F9` |
| `BG_INPUT` | `#0C1726` | `#FFFFFF` |
| `BORDER` | `#26384F` | `#CBD5E3` |
| `FG_PRIMARY` | `#F0F5FF` | `#0F1B2D` |
| `FG_SECONDARY` | `#A7B7CD` | `#55657D` |
| `ACCENT_BLUE` | `#2D7DFF` | `#1F6FEB` |
| `ACCENT_GREEN` | `#39D785` | `#1E9E5A` |
| `ACCENT_AMBER` | `#FFC857` | `#B7791F` |
| `ACCENT_RED` | `#FF667A` | `#D64560` |
| `ACCENT_PURPLE` | `#C084FC` | `#8B5CF6` |
| `LOG_BG` | `#050B13` | `#F7F9FC` |
| `LOG_FG` | `#8EE6B4` | `#0F3D2E` |
| `CANVAS_DARK` (layout view) | `#050B13` | `#050B13` |

4. **Rules for every widget:** no white borders. Use `relief="flat"`, `bd=0`, `highlightthickness=1`, `highlightbackground=BORDER`, `highlightcolor=ACCENT_BLUE`. Entries and Text areas use `BG_INPUT`. Treeview (project tree) uses `BG_PANEL`/`FG_PRIMARY` with an accent-colored selection.
5. **Toggle button label** names the mode it will switch *to* (for example "☀ Light" while dark, "🌙 Dark" while light), and updates on every toggle. Style it as a compact pill (see WP3).
6. **The unlabeled dark rectangle at the bottom of the left rail (M7):** find the widget (grep sidebar.py/app.py for the hard-coded dark color, or inspect with `widget.winfo_children()`). If it is an empty spacer or filler, give it the sidebar background token. If it holds something, keep the widget, restyle it with tokens, and make it blend with the rail.

**Done when:** toggling theme in either direction repaints every widget with no leftover white or black blocks, and text meets contrast on both palettes.

---

## WP3 — Header  *(issue L1)*

1. Layout: full width, ~62 px tall, `BG_HEADER`, thin bottom border. Brand at left, nav centered after it, theme pill and Help at right, all vertically centered. Use grid with the nav column `weight=1` so the right actions never clip.
2. **Brand:** chip/IC icon ~42 px (draw with a Canvas polygon or use the existing glyph at a larger font), title "AI-Assisted EDA" (22–25 px equivalent, bold), subtitle "OpenROAD GUI for RTL-to-GDSII Flow" in `FG_SECONDARY`.
3. **Nav buttons:** Home, Flow, Design, Run, Results, AI Assistant, Settings (existing order and commands). Define `Nav.TButton` and `Nav.Active.TButton` styles. Active style = blue-tinted fill + brighter text. Highlight the entry whose existing command shows the current view. If no existing code tracks the current view, keep **Home** highlighted statically.
4. **Right actions:** theme toggle as a compact pill, Help as an icon + label button (existing commands), grouped with ~8 px gap, fully visible at every window size. At narrow widths, drop nav labels to icon-only before allowing overlap.

---

## WP4 — Left navigation rail  *(issues H6, M6, M7)*

1. Rail: ~212 px wide (`minsize=200`), `BG_SIDEBAR`, thin right border, 12 px horizontal padding. Wrap content in a scrollable frame so nothing is dropped at small heights.
2. Sections in this order, each with a small semibold heading, then icon + label rows (32–36 px high, hover highlight, 8–12 px gap before each new heading):
   - **Project:** New Design (primary blue, full width), Open Folder, Save Project
   - **Design Inputs:** RTL (Verilog / SystemVerilog), Technology (Lib, LEF), Constraints (SDC), Floorplan / Config
   - **Flow Configuration:** Flow Steps, Parameter Tuning, AI Optimization
   - **Run & Monitor:** Start Flow, Stop, View Logs
   - **Results & Analysis:** Reports (PPA), Layout Viewer, Timing Analysis, Power Analysis, DRC/LVS
   - **Utilities:** Scripting (TCL), Docs & Help, About
3. **Binding rule:** each row calls the existing handler that already does that job (use the callback list you made in pre-work: for example Start Flow ↔ the Run Full Flow handler, Stop ↔ the existing stop handler, View Logs ↔ whatever focuses/reveals the log panel, Timing/Power/DRC/LVS ↔ the same handlers the Reports buttons use). Where no existing handler matches, render the row in the muted **disabled** style with a tooltip "Not available" and do not bind it to anything else.
4. **Keep the project tree widget exactly as is** (data, click, double-click, context menu). Place it in the Project section (or in its own collapsible area directly below the Project buttons), with its own scrollbar and a sensible max height so it does not push the other sections off-screen. Keep the refresh button next to the "Project" heading.
5. New Design uses `Primary.TButton`; Open Folder and Save Project use `Secondary.TButton`. Keep the label "New Design" (do not rename to "New Project").

---

## WP5 — Pipeline panel  *(issues H3, H4, H5, M10, N5)*

1. **One title only.** Remove the duplicate heading (the outer section label *or* the inner label; keep a single "Design Flow (RTL → GDSII)" at the top-left of the card).
2. **Header row of the card:** title left, **Run Full Flow** button right (`▶ Run Full Flow`, primary blue, same command as now). Give it a fixed minimum width (`width=` in characters) and put it in a `weight=0` grid column with `sticky="e"` so it can never truncate or slide under another panel. It sits top-right, not mid-height.
3. **Info row** (Design / Platform / Config / Configure ▼): single compact line below the title. Truncate the config path with a middle ellipsis and show the full path in a tooltip. Keep the Configure ▼ button and its command.
4. **Node canvas:**
   - Canvas background = `BG_PANEL` (never a different dark island). Redraw on `<Configure>` so the six nodes are evenly spaced for the current width.
   - ~36 px circles, connectors behind them, labels below. Labels: Synthesis, Floorplanning, Placement, Clock Tree Synthesis (two lines), Routing, GDSII Export. If there is not room, wrap labels to two lines; never overlap.
   - Draw state styles from the *existing* stage state: pending (muted slate), running (blue ring), passed (green + ✓), failed (red + ✕), cancelled/skipped (muted + label). Do not change how state is produced; only how it is drawn. Color is never the only indicator (glyph or text too).
5. **Stage button row** under the nodes: same six existing buttons, restyled as `Secondary.TButton`, laid out in an equal-weight grid so each button sits under its node, with labels matching the node labels (same wording).
6. Keep keyboard focus order and click handlers on nodes and buttons as they are.

---

## WP6 — Design Inputs card  *(issues L2, N10)*

1. Card title "Design Inputs" (single title). Two-column grid: labels (fixed width, `FG_SECONDARY`, 12–13 px equivalent — not oversized) and entries (`weight=1`, `sticky="ew"`).
2. Rows in order: Project Name, RTL File, Technology LIB, LEF Files, Constraints (SDC), Config / Floorplan. Keep existing values and variables untouched.
3. Entries show a truncated view (set `width` small, let the column stretch; for long paths scroll the entry to show the filename end, or ellipsize visually) and a tooltip with the full value. Do not change the text of any value.
4. If a per-row browse/choose handler already exists, add a small folder icon button bound to it. If not, omit the icon.
5. Bottom row: **Load Inputs** (primary) and **View / Edit Files** (secondary), equal height, minimum widths so no label truncates, aligned to the card's left padding. Pin them to the bottom of the card (give the spacer row `weight=1`) so there is no awkward dead gap above them.
6. If the card is shorter than its content at small window heights, make it scroll rather than hide rows.

---

## WP7 — Layout Viewer card  *(issues M1, M2)*

1. Card title "Layout Viewer" (single title). Keep the existing Text / Layout tabs and their content widgets. Remove any *extra* wrapper title that duplicates the card title (for example a second "File Preview" heading), but only if it is a plain label.
2. **Toolbar:** restyle whichever viewer controls already exist (view selector, zoom/fit buttons, etc.) into one compact row at the top-right of the card. Do not add new controls.
3. **Canvas:** the Layout tab canvas background is `CANVAS_DARK` (near-black) in both themes. The Text tab uses `BG_INPUT` / `FG_PRIMARY` with a monospace font.
4. **Empty hint:** place a muted one-line hint under the tabs (static label, no polling): "No layout preview available yet. Run the relevant flow stage or select a supported result." If the preview widget already exposes an "empty" state or hook, show/hide the hint there; otherwise leave it as a static muted line outside the canvas.
5. Make sure the card's right edge is fully visible (WP1).

---

## WP8 — Terminal / Flow Log  *(issues M3, M5, N1)*

1. Panel spans the **full center width** under the inputs/viewer band, with its own row weight and `minsize=160`. Single title "Terminal / Flow Log".
2. **Toolbar row:** title/label left; **Export Log...** and **Clear** right-aligned in a `weight=0` column with minimum widths, so neither can clip. Keep their commands.
3. **Tabs:** keep Flow Log / Terminal / Errors / Warnings. Add horizontal tab padding (`ttk.Style().configure("TNotebook.Tab", padding=(14, 6))`) so no label is truncated. Remove any *nested* duplicate tab strip or duplicate "Flow Log" heading that sits inside the first tab if it is only a label/wrapper.
4. **Log text area:** monospace 11–12 px equivalent, `LOG_BG`/`LOG_FG` from the theme (readable in both palettes), 8 px inner padding, themed vertical scrollbar. Use `wrap="none"` plus a horizontal scrollbar so long paths do not wrap into misaligned fragments (or `wrap="char"` if the existing code already depends on it).
5. Keep the log area as tall as the row allows, no fixed pixel height.

---

## WP9 — Bottom row: Flow Progress and Quick Metrics  *(issue H7)*

Place a bottom row under the log: **Flow Progress** (left, ~300 px) and **Quick Metrics** (right, `weight=1`), ~113 px tall.

1. If the application already has widgets, variables, or values for progress or metrics, move/restyle and show them here using the same variables.
2. Otherwise render **display-only cards** with static placeholders:
   - Flow Progress: heading, status line "Idle", a `ttk.Progressbar` in indeterminate/zero state, and a "—" for elapsed time.
   - Quick Metrics: six compact tiles — WNS, TNS, Total Power, Cell Area, DRC Violations, LVS — each with a caption, a `—` value, and a unit where applicable (WNS/TNS: ns, Power: mW, Area: µm²).
3. Tiles wrap into two rows (or become a horizontally scrollable row) when the card is narrow.
4. No fabricated numbers anywhere: placeholders stay `—`.

---

## WP10 — Right rail cards  *(issues M8, M9, M10, N9, L3, L4)*

Card order, top to bottom: AI Assistant, PPA Analysis (AI Prediction), Optimization Suggestions, Reports. Each card has **one** title (remove the duplicate outer label above each card), ~12–16 px padding, `BG_PANEL`, `BORDER` outline.

**AI Assistant**
1. Header row: robot icon + "AI Assistant" at left, **Clear Chat** at the right (same command as the current "Clear" button, label text changed only).
2. Chat area: full card width, themed `Text` (not a stark white box), scrollbar, same content as now.
3. Quick actions: the six existing buttons stacked vertically, full width, uniform `Chip.TButton` style, same order and commands.
4. Input row: `Entry` stretches (`weight=1`) + Send button with a "➤" glyph (same command). Placeholder "Type your question..." is drawn as an **overlay Label** (muted text) that hides on focus or when the entry has text. Do **not** insert the placeholder into the Entry's value, so anything that reads the Entry's content still gets exactly what the user typed.

**PPA Analysis (AI Prediction)**
1. Title left, **Run Prediction** right (existing command), fully visible.
2. Three equal-width tiles: Power (mW), Performance (WNS, ns), Area (µm²), each with a small icon, caption, `—`/value, and unit. Add a muted caption under the title: "Values shown are model estimates." Keep the existing value variables.

**Optimization Suggestions**
1. Title left (small bulb icon), **Apply Suggestion** right (existing command; do not alter its enabled/disabled logic — only style it, including a distinct disabled look).
2. The list area keeps its current behavior. Change the empty-state text from "Run optimization to see suggestions" to "No suggestions yet." (text only), muted color.

**Reports**
1. Two rows × three equal-width buttons: Timing Report, Power Report, Area Report / DRC Report, LVS Report, Generate GDSII. Existing commands and icons; uniform `Secondary.TButton`, minimum width so no label truncates, equal column weights. The card's bottom edge must be fully visible (WP1).
2. Keep the existing enabled/disabled behavior; only provide a clearly distinct disabled style.

---

## WP11 — Polish and consistency  *(issues L1–L4 remainder)*

1. **Spacing:** constants `SPACE_XS=4`, `SPACE_S=8`, `SPACE_M=12`, `SPACE_L=16` in `theme.py`; use them for all padding/gutters.
2. **Fonts:** OS UI sans-serif via `tkinter.font.nametofont("TkDefaultFont")`; title ~22–25 px, headings 14–16, body 12–13, secondary 10–11 (never smaller). Monospace only for log, chat, and text preview.
3. **Tooltips:** one small `Tooltip` helper in `widgets/` for truncated paths and for disabled controls.
4. **Middle-ellipsis helper** for long paths (`/Users/…/OpenROAD-flow-scripts`), used wherever a path appears in a label.
5. **Buttons:** `Primary.TButton` (blue fill), `Secondary.TButton` (elevated + border), `Danger.TButton` (red, for Stop), all with a visible focus ring and a distinct disabled look.
6. **Headings:** audit every card for duplicate titles (outer label plus inner label) and keep one.

---

## Final verification checklist

- [ ] Existing test suite result is the same as the baseline from before you started.
- [ ] `git diff --stat` touches only theme/layout/widget presentation files; none of the files listed in rule 3 appear.
- [ ] Every button's `command` is unchanged (spot-check with a diff on callback names).
- [ ] App starts with dark theme; toggling to light and back repaints **all** widgets (no leftover white or black blocks); toggle label names the target mode.
- [ ] At 1536 × 1024 and 900 × 600: nothing clipped at right or bottom; center never slides under the right rail; right rail collapses to tabs or scrolls when narrow.
- [ ] Header: brand, nav with active highlight, theme pill, Help — all visible.
- [ ] Left rail shows all six sections in order; rows without an existing handler are visibly disabled.
- [ ] Pipeline: single title; "Run Full Flow" fully visible top-right; six evenly spaced nodes; labels match stage buttons.
- [ ] Design Inputs: aligned labels, truncated values with tooltips, buttons not truncated.
- [ ] Layout Viewer: near-black canvas, hint line present, toolbar restyled, right edge visible.
- [ ] Terminal: full width, tabs not truncated, Export Log... and Clear fully visible, log readable in both themes.
- [ ] Bottom row cards visible and show `—` placeholders (no sample numbers).
- [ ] Right rail order correct, one title per card, Clear Chat in the header, placeholder overlay works, Reports shows 2 × 3 buttons fully.
- [ ] Before/after screenshots saved for both themes at both sizes.

---

## Issue → work package map

| Issue IDs | Work package |
|---|---|
| H1, H5, N1 | WP1 |
| H2, N8, M7 | WP2 |
| L1 | WP3 |
| H6, M6 | WP4 |
| H3, H4, M10, N5 | WP5 |
| L2, N10 | WP6 |
| M1, M2 | WP7 |
| M3, M5 | WP8 |
| H7 | WP9 |
| M8, M9, M10, N9, L3, L4 | WP10 |
| Remaining spacing, fonts, tooltips, focus states | WP11 |
