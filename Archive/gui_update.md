# OpenRoad_GUI — GUI Update Specification

**Purpose:** Implementation-ready specification for updating the existing OpenRoad_GUI desktop application to match the approved **AI-Assisted EDA** mockup while preserving the current ORFS execution flow, file-tree behavior, viewer features, and project configuration options.

**Reference mockup:** the dark widescreen desktop UI supplied in this conversation. It is a visual target, not proof that every displayed capability or metric is currently implemented.

## 1. Design goals and implementation rules

1. Present the application as a modern EDA workstation for RTL-to-GDSII implementation.
2. Keep the existing Tkinter/`ttk` application, project data model, OpenROAD Flow Scripts (ORFS) command execution, file handlers, report paths, and viewer integrations. Prefer refactoring/repositioning existing widgets over replacing working backend logic.
3. Preserve every existing supported action. A control must call its existing handler or a newly implemented, tested handler; do not add controls that appear functional but are inert.
4. Keep the existing Layout Viewer configuration and behavior exactly as implemented in the project. Do **not** invent new layer controls, file formats, view settings, configuration fields, or replacement options merely to match a screenshot. Existing viewer selectors, toolbar actions, tabs, menus, and their defaults take precedence over this visual spec.
5. Do not add a new ORFS stage or `make` target just to match the seven visible pipeline nodes. The currently implemented flow has six stages: Synthesis, Floorplan, Placement, CTS, Routing, and GDSII. The mockup's separate **Signoff (DRC/LVS)** node may display real verification/report status when available, but must not be represented as a new runnable stage unless the configured ORFS flow genuinely supports it.
6. AI values shown in the mockup are examples only. Display values only from actual model output or parsed reports. Label predictions as estimates, distinguish them from measured PPA, and handle missing models/data gracefully.
7. Work in small, testable steps. Keep the app usable if ML dependencies or model files are missing.

## 2. Reference viewport and global geometry

The supplied mockup is approximately **1536 × 1024 px**. Coordinates below are reference estimates from that image to guide the initial layout. They are not hard-coded absolute positions: use a responsive Tkinter geometry manager (`grid`, `pack`, frames, weights, and minimum sizes) so the interface resizes sensibly.

### 2.1 Main regions at the reference size

| Region | Approx. bounds (x, y, width, height) | Approx. placement / behavior |
|---|---:|---|
| Native window title bar | `(0, 0, 1536, 30)` | OS-managed title bar; title `OpenROAD_GUI - AI-Assisted EDA` where supported |
| Application header | `(0, 30, 1536, 62)` | Full width; brand at left, navigation in center, theme/help actions at right |
| Left navigation rail | `(0, 92, 212, 932)` | Fixed/limited width; spans remaining window height; sections scroll if required |
| Main workspace | `(212, 92, 918, 932)` | Flexible central workspace; four vertical bands: pipeline, inputs/viewer, log, metrics/progress |
| Right analysis rail | `(1130, 92, 406, 932)` | Fixed/limited width; stacked AI Assistant, PPA, suggestions, and reports panels |
| Main content left inset | `~11 px` | Separation between navigation rail and main workspace |
| Main workspace/right rail gap | `~12 px` | Maintain consistent gutter |

### 2.2 Central workspace layout

| Panel | Approx. bounds | Layout rule |
|---|---:|---|
| Design Flow pipeline | `(223, 103, 896, 150)` | Full width of central workspace; fixed-height region with scalable node positions |
| Design Inputs | `(223, 264, 307, 366)` | Narrow left column in the second band |
| Layout Viewer | `(541, 264, 578, 366)` | Occupies remaining width in the second band |
| Terminal / Flow Log | `(223, 641, 896, 237)` | Full central width; vertically resizable if practical |
| Flow Progress | `(223, 889, 300, 113)` | Bottom-left card |
| Quick Metrics | `(534, 889, 589, 113)` | Bottom-center card; flexible width |

### 2.3 Right rail layout

| Panel | Approx. bounds | Approx. height |
|---|---:|---:|
| AI Assistant | `(1131, 104, 395, 412)` | 412 px |
| PPA Analysis (AI Prediction) | `(1131, 527, 395, 171)` | 171 px |
| Optimization Suggestions | `(1131, 709, 395, 168)` | 168 px |
| Reports | `(1131, 888, 395, 114)` | 114 px |

The right rail uses a single vertical column, with approximately 10–12 px between cards. At smaller window sizes, the right rail may become a collapsible tabbed pane instead of compressing every card until its contents become unreadable.

## 3. Visual design system

Use a centralized theme in `openroad_gui/theme.py` and `ttk.Style`; do not scatter unrelated color values throughout widget files. Extend the existing theme constants and styles if they already provide the same roles.

### 3.1 Suggested color tokens

| Token | Suggested value | Usage |
|---|---|---|
| `BG_APP` | `#0A1320` | Application background |
| `BG_HEADER` | `#0B1524` | Header and top navigation |
| `BG_SIDEBAR` | `#0D1928` | Left navigation rail |
| `BG_PANEL` | `#101C2B` | Main cards and panel interiors |
| `BG_ELEVATED` | `#142337` | Inputs, buttons, nested cards |
| `BG_INPUT` | `#0C1726` | Text inputs, log search, chat input |
| `BORDER` | `#26384F` | Card outlines and separators |
| `FG_PRIMARY` | `#F0F5FF` | Main labels, headings, numbers |
| `FG_SECONDARY` | `#A7B7CD` | Secondary labels and helper text |
| `ACCENT_BLUE` | `#2D7DFF` | Primary buttons, active stage, focus/selection |
| `ACCENT_GREEN` | `#39D785` | Completed stages and success |
| `ACCENT_AMBER` | `#FFC857` | Warnings and intermediate status |
| `ACCENT_RED` | `#FF667A` | Failures and Stop action |
| `ACCENT_PURPLE` | `#C084FC` | AI-related highlights (sparingly) |
| `LOG_BG` | `#050B13` | Terminal/log text area |

These values are starting points and can be adjusted to the actual existing theme. Keep contrast strong, especially for small labels and log text. Color must not be the only indication of stage status; include labels/checkmarks/icons as well.

### 3.2 Typography, spacing, and shapes

- Use the operating system's available sans-serif UI font (for example, Segoe UI on Windows or the system UI font on macOS/Linux). Do not bundle a font just for this redesign.
- Main application title: approximately 22–25 px equivalent, semibold/bold.
- Panel headings: approximately 14–16 px equivalent, semibold.
- Normal controls/labels: approximately 12–13 px equivalent.
- Secondary text: approximately 10–11 px equivalent; do not make dense labels smaller than legibility allows.
- Use a consistent 8 px spacing unit with 4 px compact gaps and 12–16 px card padding.
- Card corners should be subtly rounded only where the current Tk implementation supports it cleanly; otherwise use restrained square-corner frames with thin borders. Do not add heavy shadows that Tk cannot render consistently.
- Primary buttons: blue background, clear text, visible keyboard focus.
- Secondary buttons: elevated/dark background with border.
- Stop: red or red-accented, visually distinct from Run.
- Disabled actions must visibly look disabled.

## 4. Application header

**Position:** full width, immediately below the native title bar; approximately 62 px tall in the reference.

### 4.1 Left brand block

- Chip/IC outline icon at the far left, approximately 42 × 42 px, with 12–18 px left inset.
- Main title: `AI-Assisted EDA`.
- Subtitle below/alongside: `OpenROAD GUI for RTL-to-GDSII Flow`.
- Preserve application identity; avoid claiming it is an official OpenROAD Project application.

### 4.2 Top navigation

Place horizontally after the brand. Items in order:

1. Home
2. Flow
3. Design
4. Run
5. Results
6. AI Assistant
7. Settings

- Active item uses a blue-tinted filled background and brighter text/icon.
- Inactive items use light gray text and simple line icons.
- Navigation is a visual entry point only for sections that actually exist. Connect each item to an existing view/handler or implement the page before enabling it. Do not add decorative buttons with no effect.
- Existing menu commands must remain accessible, even if reorganized under this navigation.

### 4.3 Header right actions

- Light/dark theme toggle, visually grouped in a small pill.
- Help icon at far right.
- Keep these compact and vertically centered.
- Theme switching must use the centralized theme mechanism. Help should open existing documentation/about content or a real help panel.

## 5. Left navigation rail

**Position:** full height beneath the header, approximately 212 px wide at the reference size. Use a slightly distinct background from the workspace, thin right border, and about 12 px horizontal inset.

Keep all sections and controls listed below. Each section has a semibold small heading, then aligned icon + label rows. Use approximately 32–36 px row height, with section separators and 8–12 px before each new heading.

### 5.1 Project

1. **New Project** — primary blue button, full available rail width.
2. **Open Project**.
3. **Save Project**.

Preserve the existing project/file creation, open, and save handlers. If the current product's operation is called **New Design** rather than **New Project**, retain its real semantics; the label may be `New Design` where needed to avoid implying unsupported project packaging.

### 5.2 Design Inputs

1. RTL (Verilog / SystemVerilog)
2. Technology (Lib, LEF)
3. Constraints (SDC)
4. Floorplan / Config

These should focus/scroll to the matching input/editor action or open the existing file handler. Do not create a second source of truth for selected files.

### 5.3 Flow Configuration

1. Flow Steps
2. Parameter Tuning
3. AI Optimization

These may select the flow panel or navigate to a real configuration section. Parameter changes must be stored through the existing active configuration mechanism and must respect platform-supported ORFS variables.

### 5.4 Run & Monitor

1. Start Flow
2. Stop
3. View Logs

- Start invokes the existing full pipeline action or opens a clear choice if the product supports both individual stages and the full pipeline.
- Stop invokes the existing stop/cancellation handler and is disabled when nothing is running.
- View Logs focuses the Terminal / Flow Log panel.

### 5.5 Results & Analysis

1. Reports (PPA)
2. Layout Viewer
3. Timing Analysis
4. Power Analysis
5. DRC/LVS (Optional)

Navigate to existing reports, viewers, or analysis actions. If a report or metric does not exist for the selected design/run, show an explanatory empty state instead of fabricated numbers.

### 5.6 Utilities

1. Scripting (TCL)
2. Docs & Help
3. About

Retain existing script/editor and help/about handlers if available. Mark unavailable functionality clearly rather than binding it to an unrelated action.

## 6. Main center — Design Flow pipeline

**Position:** top of the central workspace, approximately 896 × 150 px.

### 6.1 Panel title and global action

- Title at the top-left: `Design Flow (RTL → GDSII)`.
- Top-right button: `Run Full Flow`, blue outline or blue filled primary style with a play icon.
- Keep about 12 px internal margins.

### 6.2 Stage visualization

The mockup shows seven circular milestones. The actual runnable ORFS flow in the current code defines six stages. To reconcile the visual and implementation:

| Visual order | Label | Required behavior |
|---:|---|---|
| 1 | Synthesis (Yosys) | Map to existing `FlowStage.SYNTH` / current synthesis handler |
| 2 | Floorplanning | Map to existing `FlowStage.FLOORPLAN` |
| 3 | Placement | Map to existing `FlowStage.PLACE` |
| 4 | Clock Tree Synthesis | Map to existing `FlowStage.CTS` |
| 5 | Routing | Map to existing `FlowStage.ROUTE` |
| 6 | Signoff (DRC/LVS) | Display verification/report status if backed by real artifacts; do not create a new runnable stage or claim LVS ran if it did not |
| 7 | GDSII Export | Map to the existing GDS target/final GDS action; verify the output exists before marking complete |

An alternative that more strictly mirrors the current six-stage enum is to show six runnable nodes and display signoff as a small status badge within the Results/Reports area. Choose whichever is least disruptive to the current `PipelineRow` state model; do not modify `FULL_PIPELINE` to include a nonexistent stage.

### 6.3 Node appearance and status

- Arrange nodes horizontally along a central line, evenly spaced with equal margins.
- Node circles approximately 36 px diameter in the reference image.
- Completed: green fill with check mark and a green connector behind it.
- Running/current: blue fill or blue outline, brighter ring, and optional progress indication if real stage progress can be measured.
- Pending: muted slate circle and connector.
- Failed: red state with clear failure indicator.
- Cancelled/skipped: separate muted state with text/tooltip; do not conflate it with successful completion.
- Stage labels below each circle; allow two-line labels for CTS and signoff.
- Use `Canvas` for connectors/nodes if needed, but preserve click handlers and keyboard accessibility of the current pipeline widget.
- The stage status must reflect the actual active run. It must not infer success from a stale output file from a previous run.

### 6.4 Interaction

- Clicking a stage control runs that existing stage handler if no flow is currently running.
- `Run Full Flow` uses the current `run_pipeline` flow and `FULL_PIPELINE` order.
- While running, prevent duplicate flow starts, enable Stop, disable conflicting actions if necessary, and update status only from real callbacks.
- Keep OpenROAD GUI viewer actions available through their existing controls/menu. If buttons are placed below stage nodes, map each to the existing `ViewerService` stage handler without changing the viewer target.

## 7. Second band — Design Inputs and Layout Viewer

The second band is immediately below the pipeline. It consists of a smaller input card on the left and a wider viewer card on the right, with a 10–12 px gap.

### 7.1 Design Inputs panel

**Position:** approximately 307 × 366 px.

Panel title: `Design Inputs`.

Present labels in a left column and compact entries/file selectors in a right column. All paths should truncate visually rather than stretch the panel; provide a tooltip or existing browse/edit action for the full path.

Input rows in order:

1. Project Name
2. RTL File
3. Technology LIB
4. LEF Files
5. Constraints (SDC)
6. Config / Floorplan

- Project Name: editable only if the existing application supports changing it; otherwise show the active design name read-only.
- File rows: path/name field and folder/browse icon connected to the existing file selection logic.
- Config/Floorplan must continue to reflect the selected design/config in `AppConfig`; do not introduce a separate disconnected state.
- Primary bottom button: `Load Inputs` (use only if a real validation/load handler exists; otherwise use the existing equivalent label and action).
- Secondary bottom button: `View / Edit Files`, bound to the existing editor/project-tree actions.
- Keep form labels aligned and spacing consistent. If all fields cannot fit at smaller window sizes, allow the card to scroll rather than dropping fields.

### 7.2 Layout Viewer panel

**Position:** approximately 578 × 366 px.

Panel heading: `Layout Viewer`.

**Critical preservation rule:** keep the Layout Viewer controls/configuration currently present in this repository. This spec does not authorize replacing the existing viewer, deleting any viewer options, adding new layer configuration semantics, changing defaults, or changing which design artifacts can be opened. Reuse the real `PreviewPanel`, `ViewerService`, and existing GDS/OpenROAD GUI handlers.

The approved mockup's visible structure includes:

- A top toolbar with the current preview tabs, shown as `Layout Visualizer` and `Text Editor` in the mockup. If the current implementation uses different names, preserve the implemented actions and content; label changes are permitted only when they do not break tests or user expectations.
- A view orientation selector shown as `Top View` in the mockup, but only if that selector exists in the current app. Keep all current selector values and defaults.
- Zoom/search/fit-style icons shown at the top-right; use only real existing controls and preserve their handlers.
- A large central preview canvas showing the actual rendered placement/routing/GDS view or other supported preview content.
- Background should be near-black so the layout image's colors remain legible. Do not alter the rendered image/GDS contents to match the mockup.

**Do not create a fake chip view.** If no preview can be generated, show an empty state with a message such as `No layout preview available yet. Run the relevant flow stage or select a supported result.`

The currently selected design/platform/config and active preview state must remain consistent with the project tree and flow runner.

## 8. Terminal / Flow Log panel

**Position:** central full width under the Design Inputs/Viewer band, approximately 896 × 237 px.

### 8.1 Header and tabs

- Panel title: `Terminal / Flow Log`.
- Tabs in the mockup: `OpenROAD Log`, `TCL Console`, `Errors / Warnings`.
- Preserve the existing log viewer's actual tabs and supported capabilities. Do not add a TCL command-execution surface unless safe, implemented, and validated; displaying a tab alone is not sufficient.
- `OpenROAD Log` shows actual stdout/stderr from the current process.
- `Errors / Warnings`, if implemented, filters or mirrors messages from the same log event source; it should not invent a second contradictory parser.

### 8.2 Toolbar

Place compact actions on the right side of the log toolbar:

- Search logs input.
- Lock/auto-scroll toggle only if supported by the log viewer.
- Copy action only if implemented.
- Export/download log action mapped to existing `Export Log...` behavior.
- Clear log action mapped to the current Clear handler.

Do not remove existing restart/clear/log controls if present elsewhere in the current application. Avoid duplicate buttons that perform subtly different actions.

### 8.3 Log text area

- Dark near-black background, monospace font, approximately 11–12 px equivalent.
- Time/stream prefixes aligned consistently.
- Use color for severity but retain severity text (`INFO`, `WARN`, `ERROR`).
- Preserve the actual log stream. Do not silently filter output from the exported full log.
- Vertical scrollbar at right. Ensure both stdout and stderr pipes are drained safely while the process is running.
- All Tk widget updates from background threads must be scheduled onto the Tk main thread.

## 9. Bottom central row — progress and quick metrics

### 9.1 Flow Progress

**Position:** approximately 300 × 113 px at the bottom-left of the central workspace.

Contents in order:

- Heading: `Flow Progress`.
- Current stage/status text, for example `Placement in progress...`.
- Horizontal progress bar.
- Percentage label.
- Elapsed runtime and optional estimated remaining runtime.

Only show an exact percentage or estimated remaining time when it is computed from real tracked data. Because ORFS may not expose uniform progress information across every stage, use an indeterminate bar and stage status when a reliable percentage is unavailable. Mark estimated times as estimates; do not invent values to match the mockup.

### 9.2 Quick Metrics (Current Run)

**Position:** approximately 589 × 113 px at the bottom-center.

Show compact metric cards for:

1. WNS
2. TNS
3. Total Power
4. Cell Area
5. DRC Violations
6. LVS

Rules:

- Values must come from reports/results for the **selected run**, not hard-coded examples or another design's stale output.
- Show units and preserve sign conventions, especially for WNS/TNS.
- Distinguish measured, predicted, unavailable, and not-yet-run data.
- Power and LVS can be unavailable for designs/flows that do not generate those measurements/checks. Show `—` or `Not available`, not zero.
- Tooltips should identify the metric/source report when practical.
- For long values, use a shortened display and a tooltip with the full precision.

## 10. Right rail — AI Assistant

**Position:** right column top, approximately 395 × 412 px.

### 10.1 Header and conversation area

- Robot/AI icon and title: `AI Assistant`.
- `Clear Chat` action at upper-right; only show if conversation state actually exists.
- Introductory prompt: `How can I help you with your design today?`
- Place quick-action chips/buttons in a vertical stack.

### 10.2 Suggested actions shown in the mockup

1. Suggest optimal floorplan parameters
2. Predict PPA for current design
3. Recommend better configuration
4. Explain STA violations
5. Help me fix routing congestion
6. Generate TCL script for custom flow

Each action must call an implemented service/handler. If a service is not yet implemented, disable it or display a transparent message that the capability is not available. Do not simulate a model response or produce fabricated timing/area/routing claims. Any TCL generated for the user must be reviewable before execution.

### 10.3 Chat input

- Bottom of assistant card: one-line expandable input with placeholder `Type your question...` and a send arrow.
- Enter submits only when the relevant assistant backend is active; otherwise explain setup/availability.
- Keep chat execution off the UI thread if it can take time. Use status/error feedback and allow cancellation where appropriate.
- Keep recent conversation in a scrollable area if responses are longer than the card.

## 11. Right rail — PPA Analysis (AI Prediction)

**Position:** below AI Assistant, approximately 395 × 171 px.

### 11.1 Heading and action

- Heading: `PPA Analysis (AI Prediction)`.
- Upper-right action: `Run Prediction`.
- Button runs the current supported surrogate/failure-prediction inference for the active design.

### 11.2 Metric cards

Three equal-width cards:

1. **Power** — display power and unit (for example mW).
2. **Performance (WNS)** — display predicted or measured WNS in ns.
3. **Area** — display area and correct unit (for example µm²).

- Add a small icon and optional trend/relative comparison only when there is a valid comparable baseline.
- Predictions must say `estimate` or `predicted`; measurements must say `measured` or identify the source report.
- Do not show example numbers from the mockup as defaults.
- If model artifacts are absent, inputs are outside the supported feature schema, or inference fails, show the reason and do not substitute fake numbers.

## 12. Right rail — Optimization Suggestions

**Position:** below PPA Analysis, approximately 395 × 168 px.

- Heading: `Optimization Suggestions`, with a restrained bulb/light icon.
- `Apply Suggestion` button aligned top-right.
- Up to four compact numbered recommendations, with short explanations and the predicted metric impact on the right.

Each recommendation should ideally include:

- Suggested parameter/value or actionable diagnostic.
- Why it is being suggested and which measured/predicted metrics informed it.
- Expected impact and uncertainty when the model supports these values.
- A way to inspect the current configuration versus proposed changes.

**Apply behavior and safety:**

- Applying a suggestion must not silently overwrite `config.mk`, constraints, RTL, or other project files.
- Present a proposed diff/config preview and require user confirmation before writing changes.
- Validate the parameter and value against the active platform, current design and supported ORFS options.
- Make a backup or use the project's existing safe-save behavior.
- Never claim a predicted improvement is a guaranteed outcome.
- If the optimizer is still a placeholder/default heuristic, do not show fabricated recommendations as model-generated. Display `Parameter recommendations are not available yet` or expose only explicitly labeled rule-based guidance.

## 13. Right rail — Reports

**Position:** bottom of right rail, approximately 395 × 114 px.

Arrange six compact buttons in two rows of three, matching the mockup:

| Row | Left | Middle | Right |
|---|---|---|---|
| 1 | Timing Report | Power Report | Area Report |
| 2 | DRC Report | LVS Report | Generate GDSII |

Map these to existing report-opening/viewing actions and the existing GDS generation target. A report button should open the actual report for the active design and run. If a report is not present, explain whether the relevant stage has not run or the flow does not generate that report.

`Generate GDSII` must invoke the existing GDS target/action and then validate output existence before reporting success. Keep the action disabled while an incompatible flow is already running, unless the existing runner explicitly supports this safely.

## 14. State and data contracts

All panels must reflect one shared active design and current run.

- **Active design:** resolve from the existing `AppConfig`/selected `config.mk`; do not introduce a second active-design variable that can disagree.
- **Active platform:** comes from the selected design/config.
- **Current run:** distinguish current-run artifacts from previous results; use existing ORFS results/reports/log paths and record run timing/status where possible.
- **Stage state:** pending, running, passed, failed, cancelled, or skipped. Persist only if there is already a reliable run-state mechanism; otherwise do not imply historical persistence.
- **Metrics:** each metric should carry a value, unit, source (report/model), timestamp/run ID, and validity/availability state where practical.
- **Predictions:** record model version and input feature data/schema; do not present a prediction as a measured value.
- **Missing metrics:** represent as unavailable, not zero.
- **Error handling:** failed stage, parser error, missing file, unavailable dependency, and unavailable model should each produce clear user feedback and a useful log entry.

## 15. Responsive behavior

Although the reference is 1536 × 1024, the window must remain usable at the existing minimum size (the current app sets 900 × 600 unless deliberately revised after tests).

Suggested rules:

- Header: keep brand visible; collapse or compact navigation labels before allowing overlap.
- Left rail: preferred width 200–220 px. At small widths, allow a collapsed icon-only mode or a scrollable rail with tooltips.
- Central workspace and right rail: use a weighted grid. At wide widths use the pictured three-zone composition (left rail / center workspace / right rail). At narrower widths convert the right rail into tabs or place its cards under the central workspace; do not force 395 px of right rail into a 900 px window.
- Design Inputs/Viewer: maintain the left-to-right relationship; if too narrow, stack the cards vertically and allow the window/content area to scroll.
- Pipeline: space nodes dynamically based on canvas width. Keep labels readable and do not overlap nodes.
- Terminal: allow vertical resize and preserve a meaningful minimum height.
- Bottom cards: resize horizontally; wrap metric cards or use a compact scrollable row if required.
- Do not rely on fixed absolute pixel coordinates for final Tk widget placement.

## 16. Implementation mapping to current project files

Prefer modifying the current classes instead of building a parallel GUI.

| Existing module | Expected responsibility during update |
|---|---|
| `openroad_gui/app.py` | Compose the application layout, own top-level navigation, wire callbacks and marshal UI updates onto Tk's main thread |
| `openroad_gui/theme.py` | Centralize colors, ttk styles, font sizing and active/disabled/status styles |
| `openroad_gui/widgets/sidebar.py` | Left rail navigation and existing project/utility actions |
| `openroad_gui/widgets/pipeline_row.py` | Pipeline nodes, stage labels/status, top control bar and current stage actions |
| `openroad_gui/widgets/flow_panel.py` | Existing stage actions, state/progress indicators and reports access |
| `openroad_gui/widgets/preview_panel.py` | Preserve existing Text/Layout preview functionality and current viewer settings |
| `openroad_gui/widgets/project_tree.py` | Preserve tree data source, node types, click/double-click/context-menu behavior, New Design/Open Folder actions |
| `openroad_gui/widgets/log_viewer.py` | Actual logs, tabs supported by the app, search/export/clear and severity display |
| `openroad_gui/widgets/settings_dialog.py` | Preserve ORFS root, KLayout path, environment values and current configuration settings |
| `openroad_gui/flow_runner.py` | Keep ORFS command construction and current six-stage flow semantics; harden safely in isolated changes |
| `openroad_gui/config.py` | Remain the source of truth for active design, platform and ORFS paths |
| `openroad_gui/viewers.py` | Preserve OpenROAD GUI/KLayout viewer selection and launch behavior |
| `openroad_gui/intelligence/` | Existing models/data/inference; surface only capabilities backed by tested implementations and available artifacts |

This is a mapping recommendation. Before changing a module, inspect the current branch and existing handler names so callbacks are re-used rather than guessed.

## 17. Suggested implementation order

1. **Baseline and safety:** run existing tests; remove/rotate any exposed credentials in the repo; capture a before screenshot; record current viewer controls and config defaults.
2. **Theme:** centralize dark colors/styles and apply them to the current layout without changing behavior.
3. **Top-level geometry:** organize header, left rail, central workspace and right rail using weighted frames/grid; verify at 1536 × 1024 and the minimum supported window size.
4. **Pipeline:** apply the visual stage layout while keeping actual stage enum, flow order and viewer callbacks intact. Make signoff a status/report element unless backed by an actual runnable stage.
5. **Inputs and viewer:** place the Design Inputs and existing Layout Viewer side by side. Preserve all current viewer options/configurations and file handling.
6. **Terminal and bottom row:** organize the log, flow-progress display and metrics; ensure missing values and unavailable progress are represented honestly.
7. **AI rail:** connect existing inference only. Label forecasts clearly and disable unsupported menu actions. Implement a safe recommendation diff/confirmation workflow before enabling Apply Suggestion.
8. **Regression testing:** run pytest, inspect startup without optional ML dependencies, test active design switching, run each supported stage, cancel a flow, open reports/GDS, and verify no callbacks or viewer actions were lost.
9. **Visual QA:** compare screenshots at wide and narrow viewport sizes; verify clipping, contrast, keyboard focus, long paths, logs, and window resizing.

## 18. Acceptance checklist

### Layout and appearance
- [ ] Dark navy/charcoal theme is centralized and applied consistently.
- [ ] Header contains brand, functional navigation and right-side theme/help actions.
- [ ] Left rail contains all six named sections and their controls in the specified order.
- [ ] Pipeline card spans the top of the central workspace; stage positions are even and state-coded.
- [ ] Design Inputs card is left of the Layout Viewer in wide mode.
- [ ] Terminal / Flow Log spans the center workspace beneath the second band.
- [ ] Flow Progress and Quick Metrics appear beneath the log.
- [ ] AI Assistant, PPA Analysis, Optimization Suggestions, and Reports appear in the right rail in the specified order.
- [ ] Content resizes cleanly without overlapping or clipping at the minimum supported window size.

### Functional preservation
- [ ] New/open/save and new-design flows retain their existing semantics.
- [ ] Project tree contents and click/expand/double-click/context-menu behavior remain unchanged.
- [ ] Every existing ORFS stage command and Full Pipeline still uses the current `FlowRunner` handlers.
- [ ] Stop and error states are reflected accurately.
- [ ] All current Layout Viewer tabs, controls, selector options, defaults, file handling and viewer callbacks are preserved.
- [ ] KLayout and OpenROAD GUI actions still open the correct selected artifacts/checkpoints.
- [ ] Settings retain ORFS root, KLayout executable and extra environment configuration.
- [ ] Log export includes full output and still works after UI rearrangement.
- [ ] Existing reports-folder and GDS actions still use the active design's artifacts.

### Data correctness and AI transparency
- [ ] No illustrative mockup metrics are shipped as hard-coded live results.
- [ ] Measured PPA, predicted PPA, missing metrics and stale metrics are distinguishable.
- [ ] Model-unavailable and prediction-error paths are handled cleanly.
- [ ] Unsupported AI actions are disabled or clearly identified as unavailable.
- [ ] Suggestions cannot modify design/config files without a preview and explicit confirmation.
- [ ] The GUI remains usable when optional ML packages/model artifacts are not installed.

### Validation
- [ ] Existing unit tests pass.
- [ ] New/updated tests cover changed widgets and callback mapping.
- [ ] Application tested on the primary supported OS and Python/Tkinter environment.
- [ ] One real small-design ORFS run reaches the expected output/checkpoint and displays its correct reports/metrics.
- [ ] Before/after screenshots are reviewed at desktop and minimum sizes.

## 19. Non-goals

- Do not rewrite the ORFS flow or replace OpenROAD/Yosys/KLayout.
- Do not change the project tree's data source, file ordering, file types, or click behavior as part of a visual-only redesign.
- Do not invent unsupported platform controls, layer settings, report metrics, signoff targets, or live AI capabilities.
- Do not turn the GUI into a new backend service or require a cloud connection for normal local ORFS use.
- Do not make a model prediction automatically modify constraints, RTL, floorplan, or platform files.

## 20. Reference links

- Repository: <https://github.com/Mihir-Mithani/OpenRoad_GUI>
- README: <https://github.com/Mihir-Mithani/OpenRoad_GUI/blob/main/README.md>
- Main application: <https://github.com/Mihir-Mithani/OpenRoad_GUI/blob/main/openroad_gui/app.py>
- Theme: <https://github.com/Mihir-Mithani/OpenRoad_GUI/blob/main/openroad_gui/theme.py>
- Pipeline row: <https://github.com/Mihir-Mithani/OpenRoad_GUI/blob/main/openroad_gui/widgets/pipeline_row.py>
- Preview panel: <https://github.com/Mihir-Mithani/OpenRoad_GUI/blob/main/openroad_gui/widgets/preview_panel.py>
- Flow runner: <https://github.com/Mihir-Mithani/OpenRoad_GUI/blob/main/openroad_gui/flow_runner.py>
- Intelligence architecture: <https://github.com/Mihir-Mithani/OpenRoad_GUI/blob/main/INTELLIGENCE_ARCHITECTURE.md>

---

**Implementation principle:** match the approved visual hierarchy and positions while preserving the real project behavior. Where the mockup and current code disagree, current working functionality and truthful data take precedence over appearance.
