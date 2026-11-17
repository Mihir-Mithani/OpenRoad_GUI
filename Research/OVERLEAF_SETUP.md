# Overleaf Setup Instructions for OpenRoad-GUI Paper

## Project Structure for Overleaf

```
overleaf-project/
├── openroad_gui_paper.tex          # Main LaTeX file
├── openroad_gui_paper.bib          # Bibliography (optional - references in tex)
├── figures/
│   └── architecture_layers.pdf     # Architecture diagram (create this)
├── plots/
│   ├── 1a_outcomes_by_platform.png
│   ├── 1b_closure_rate_util_density.png
│   ├── 2a_wns_evolution_by_platform.png
│   ├── 2b_wns_improvement_waterfall.png
│   ├── 3a_knob_effects_box.png
│   ├── 3b_parallel_coordinates.png
│   ├── 3c_spearman_correlation.png
│   ├── 4a_power_vs_violations_loglog.png
│   ├── 4b_runtime_ecdf.png
│   ├── 4c_runs_per_design.png
│   ├── 5_timeline_gantt.png
│   ├── 6_design_facet_wns_evolution.png
│   └── 7_normalized_within_design.png
├── plots_enhanced/
│   ├── 1_platform_outcomes.png
│   ├── 2_closure_rate_util_density.png
│   ├── 3a_knob_effects_box.png
│   ├── 3a_wns_evolution_by_platform.png
│   ├── 3b_parallel_coordinates.png
│   ├── 3b_wns_improvement_waterfall.png
│   ├── 3c_spearman_correlation.png
│   ├── 4a_power_vs_violations_loglog.png
│   ├── 4c_runs_per_design.png
│   ├── 6_design_facet_wns_evolution.png
│   ├── 7_normalized_within_design.png
│   └── 8_model_performance_comparison.png
├── plots_spec/
│   ├── 01_closure_outcomes.png
│   ├── 02_stage_wns.png
│   ├── 03_parameter_effects.png
│   ├── 04_param_outcome_heatmap.png
│   ├── 05_power_vs_area.png
│   └── 06_parallel_coords.html     # Not used in LaTeX (interactive)
└── README.md
```

## Upload Instructions

### 1. Create New Overleaf Project
1. Go to [overleaf.com](https://overleaf.com)
2. Click "New Project" → "Blank Project"
3. Name it: "OpenRoad-GUI Paper"

### 2. Upload Files
**Option A: Drag and Drop (Recommended)**
- Select all files in the folder structure above
- Drag into Overleaf file panel
- Overleaf will preserve directory structure

**Option B: Upload ZIP**
- Zip the entire folder structure
- In Overleaf: Menu → Upload → Upload ZIP

### 3. Required Directories
Make sure these directories exist in Overleaf:
- `figures/` - for architecture diagram
- `plots/` - original plots
- `plots_enhanced/` - enhanced plots (preferred for paper)
- `plots_spec/` - specification plots

### 4. Compile Settings
- **Compiler**: `pdfLaTeX` (default)
- **Main file**: `openroad_gui_paper.tex`
- **Timeout**: 60 seconds (default is fine)

### 5. Figure References in Paper

The paper references figures using these paths:
- `figures/architecture_layers.pdf` - Architecture diagram (needs creation)
- `plots_enhanced/8_model_performance_comparison.png` - Model comparison
- `plots_enhanced/1_platform_outcomes.png` - Platform outcomes
- `plots_enhanced/2_closure_rate_util_density.png` - Closure rates
- `plots_enhanced/3a_wns_evolution_by_platform.png` - WNS evolution
- `plots_enhanced/3b_wns_improvement_waterfall.png` - WNS waterfall
- `plots_enhanced/3a_knob_effects_box.png` - Knob effects
- `plots_enhanced/3c_spearman_correlation.png` - Spearman correlation
- `plots_spec/01_closure_outcomes.png` - Closure outcomes
- `plots_enhanced/2a_wns_evolution_by_platform.png` - PPA panel
- `plots_enhanced/2b_wns_improvement_waterfall.png` - WNS improvement
- `plots_enhanced/3a_knob_effects_box.png` - Knob effects (reused)
- `plots_enhanced/3c_spearman_correlation.png` - Spearman (reused)

### 6. Missing Files to Create

**`figures/architecture_layers.pdf`** - Architecture diagram
Create this using:
- draw.io (diagrams.net) - export as PDF
- Lucidchart - export as PDF
- PowerPoint/Keynote - export as PDF
- TikZ (if you prefer LaTeX native)

The diagram should show 4 layers:
1. GUI Layer (Tkinter)
2. Flow Execution Layer (FlowRunner → ORFS)
3. Intelligence Layer (Surrogate | Failure Predictor | Flow Optimizer)
4. Data Layer (Real ORFS Runs → Feature Engineering → Training Pipeline)

### 7. Bibliography

The paper includes references directly in the `.tex` file using `\bibitem` commands. No separate `.bib` file needed.

### 8. Compilation Checklist

After upload, verify:
- [ ] Main file compiles without errors
- [ ] All figures appear correctly
- [ ] Cross-references work (Fig.~\ref{fig:...})
- [ ] Tables render correctly
- [ ] Appendix sections appear
- [ ] References section appears

### 9. Troubleshooting

**Figure not found errors:**
- Check file paths match exactly (case-sensitive)
- Ensure directories exist in Overleaf project
- Verify file extensions (.png vs .PNG)

**Compilation timeout:**
- Reduce figure resolution if needed
- Remove unused packages

**Missing fonts:**
- Paper uses standard IEEE fonts (no special fonts needed)

### 10. Final PDF Output

Expected output: ~12-15 page IEEE conference paper with:
- Title, authors, abstract
- 12 sections + appendices
- ~15 figures
- 12+ tables
- 25+ references
- 3 appendices

---

## Quick Upload Commands (if using CLI)

```bash
# From the OpenRoad GUI directory
cd "/Users/mihirmithani/Downloads/OpenRoad GUI"

# Create zip for upload
zip -r overleaf_upload.zip \
    openroad_gui_paper.tex \
    figures/ \
    plots/ \
    plots_enhanced/ \
    plots_spec/

# Or upload individual directories via Overleaf UI
```

---

## Contact

For questions about the paper or Overleaf setup, refer to the paper content or the OpenRoad-GUI project documentation.