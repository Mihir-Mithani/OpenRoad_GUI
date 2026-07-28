# OpenRoad_GUI — Visual Redesign Spec (UI-only migration)

## Purpose
Migrate the current light-themed Tkinter UI to the new dark-themed layout shown in the target mockup. **This is a pure visual/layout change.** Every existing function, callback, button action, file path, thread, subprocess call, log-parsing logic, and state variable must keep working exactly as it does today. Do not rename functions, do not change data flow, do not remove or alter any operation — only restyle and rearrange how things are presented.

Two references are attached to this task:
- **`target_ui.png`** (dark theme) — the design to move *towards*.
- **`current_ui.png`** (light theme) — the existing app, i.e. what you're editing.

If those filenames don't match what's in the repo, ask before assuming which screenshot is "before" vs "after."

---

## Hard constraints
1. **No logic changes.** Every widget that currently triggers an action (Run Full Pipeline, Stop, View GDS in KLayout, Open Reports Folder, Open in Editor, Use as Active config.mk, Preview Layout, OpenROAD GUI per-stage buttons, Export Log, Clear, Restart, New Design, Open Folder, file tree selection, Text/Layout preview toggle) must call the exact same handler it calls today. Only its visual styling, icon, size, or position may change.
2. **No new dependencies unless necessary.** Prefer Tkinter/ttk styling (`ttk.Style`, custom `tk.Canvas` drawing) over pulling in new GUI frameworks. If a resource-usage line graph is needed and `matplotlib` isn't already a dependency, use a lightweight `tk.Canvas` sparkline instead of adding a new library — flag it if you think a new dependency is truly required, don't add it silently.
3. **Don't touch the file tree contents or naming.** The left-hand Project/file-tree panel's data source and click behavior stay identical; only the panel's theming (colors, font, spacing) changes.
4. **Preserve all existing state.** Status text ("Ready", running, error states), progress percentages, pass/fail indicators per stage, and log contents must map 1:1 onto the new visuals — don't drop any state the old UI displayed.

---

## What changes, section by section

### 1. Global theme
- Switch the whole app from the current light/default `ttk` theme to a dark theme: near-black background (`#0d1117`–`#1a1d24` range), light gray/white text, blue accent (`#3b82f6`-ish) for active/primary elements, green for success/checkmarks, amber/orange for warnings.
- Apply this via a single `ttk.Style` configuration (custom theme or `clam` base + overridden colors) so it's centralized, not scattered `bg=`/`fg=` calls per widget.
- Keep the same base font family; only adjust color/weight, not typography logic.

### 2. Flow Execution — pipeline stage row
**Current:** a plain single row of six equal-width rectangular buttons (Synthesis (Yosys), Floorplan/Macro Placement, Core Placement, Clock Tree Synthesis, Routing & DRC, GDSII Generation), plus a second identical-looking row of six buttons for the OpenROAD GUI viewer (Synthesis, Floorplan, Placement, CTS, Routing, Final).

**Target:** a single horizontal pipeline visualization:
- Six circular icon nodes (Synthesis, Floorplan, Place, CTS, Route, GDSII) connected by a horizontal line/arrow.
- Each node gets a small icon representing its stage (waveform/chip icon for Synthesis, grid icon for Floorplan/Place, scissors for CTS, etc. — reuse simple Unicode symbols or a small icon set, doesn't need to be pixel-perfect).
- Completed stages: green circle with a checkmark badge.
- The currently-active/in-progress stage: highlighted blue outline, with a thin progress bar segment underneath the connecting line for that stage showing % complete.
- Not-yet-run stages: gray/muted circle.
- Below each node, keep a small button labeled "OpenROAD GUI" that opens that stage's viewer — this replaces the old second row of six separate viewer buttons, but must call the exact same per-stage "open GUI" handler as before (just triggered from underneath the corresponding node instead of a separate row).
- Clicking a node itself (not just the GUI button) can optionally show stage details — only add this if it's trivial; not required.

### 3. Top control bar
- Keep: **Run Full Pipeline**, **Stop Flow**, **Preview Layout**, and a **Status: Ready/Running/Error** indicator (color-coded text, green/blue/red) — same handlers as current "Run Full RTL-to-GDSII Pipeline" / "Stop" / "Preview Layout" buttons.
- Replace the current flat row of extra buttons (Open in Editor, Use as Active config.mk, View GDS in KLayout, OpenROAD GUI, Open Reports Folder, Export Log) with a single **Configure** button that opens a small dropdown/menu containing **Settings** (and optionally group the rest — Open in Editor, Use as config, View GDS in KLayout, Open Reports Folder — as additional menu items so no action is lost). Every menu item must call its existing handler unchanged.
- Keep Export Log and Clear where they are for the Flow Log panel (bottom right), not in this dropdown.

### 4. Design/Platform/Config header
- Current: "Design: alu_4bit  Platform: asap7 / Config: ./designs/asap7/alu_4bit/config.mk" as plain text.
- Target: same three values, but "Config File Path" gets a small **Edit** icon/link next to it instead of showing the raw path inline — clicking Edit opens whatever the current config-editing action already is (e.g. same as "Open in Editor" / "Use as Active config.mk" flow, don't invent new behavior — check what the current "Open in Editor" button does and wire Edit to that same function).

### 5. File Preview panel
- Rename tab labels from "Text" / "Layout" to "Text Editor" / "Layout Visualizer" (label text only — same tab-switch handler, same content underneath).
- Restyle the preview canvas to dark background; when a layout image/GDS preview is shown, keep it rendered exactly as today, just on a dark canvas background instead of light gray.

### 6. New: right-hand sidebar (Task Assistant + Resource Monitor)
This is new panel real estate, not present in the current UI. Add a fixed right sidebar with two stacked sections:

- **Task Assistant**: a scrollable list of warnings/errors surfaced during the run (e.g. "Floorplan constraint violation detected"). Populate this from whatever warning/error stream the flow log or backend already produces — do not invent a new detection mechanism. If the current app already logs warnings/errors to the Flow Log panel, mirror those same entries here (filtered to warning/error severity) rather than duplicating log-parsing logic; ideally have both panels read from the same underlying log/event list.
- **Resource Monitor**: three small live graphs/gauges for CPU, Memory, and Disk usage. If the app doesn't currently track these, this is the one place where *new* functionality is genuinely required (reading system resource usage) — implement it with `psutil` if available, polling on a timer already used elsewhere in the app (reuse the existing periodic-update/polling pattern if one exists, e.g. whatever refreshes the Flow Log). Keep it lightweight (simple Canvas sparkline lines), and make clear in the PR/commit message that this is additive monitoring, not a change to existing behavior.
- If adding real resource monitoring is out of scope for now, stub the section with static/placeholder graphs and leave a `# TODO: wire to real system stats` comment, so the layout matches the target without inventing fake functionality that looks real.

### 7. Terminal panel
- Keep Flow Log / Terminal tab toggle, terminal output text, Restart and Clear buttons — identical behavior, just dark styling to match.
- The small sparkle/decorative icon in the corner of the target mockup's terminal is purely cosmetic — optional, skip if it adds complexity for no functional value.

### 8. Left file tree panel
- Restyle to dark theme (dark background, light text, blue highlight on selection) matching the target.
- No changes to what nodes exist, how they're populated, or click/expand behavior.
- Keep **New Design** and **Open Folder** buttons pinned at the bottom exactly as now.

---

## Suggested implementation order
1. Centralize a dark `ttk.Style` theme and apply it globally — verify nothing breaks functionally with just the theme swap.
2. Rebuild the pipeline stage row as a `Canvas`-based node-and-line visualization, wiring each node's existing per-stage button handler in.
3. Consolidate the extra action buttons into the Configure dropdown menu.
4. Rename preview tabs and restyle the preview canvas.
5. Add the right sidebar (Task Assistant list + Resource Monitor), starting with static/placeholder content if live wiring isn't ready, then wire it to real log/resource data.
6. Final pass: spacing, colors, font consistency against the target screenshot.

## Non-goals
- No new pipeline stages, no new file operations, no change to how ORFS is invoked, no change to the underlying `odb`/`.sdc`/`.v`/`.gds` file handling.
- No change to which files appear in the tree or how the flow log is generated.
- Don't redesign icons/branding beyond what's needed to match the mockup's general look.
