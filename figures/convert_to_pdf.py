#!/usr/bin/env python3
"""
Convert all PNG figures to optimized PDFs for faster Overleaf compilation.
Also creates properly sized versions for IEEEtran columns.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
import os
import shutil

# IEEEtran column widths
IEEE_COLUMN_WIDTH = 3.5  # inches
IEEE_FULL_WIDTH = 7.16   # inches (two-column)

# Target DPI for PDF (vector, so DPI matters for embedded rasters only)
TARGET_DPI = 300

# Maximum pixel dimensions for PNGs (if we must keep PNG)
MAX_SINGLE_COL_PX = 1100
MAX_FULL_COL_PX = 2100

def resize_image_if_needed(input_path, output_path, max_width=None, max_height=None):
    """Resize image if it exceeds max dimensions."""
    with Image.open(input_path) as img:
        if max_width and img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        if max_height and img.height > max_height:
            ratio = max_height / img.height
            new_size = (int(img.width * ratio), max_height)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        img.save(output_path, optimize=True, quality=85)
    print(f"  Resized: {input_path} -> {output_path} ({img.width}x{img.height})")

def convert_png_to_pdf(png_path, pdf_path, figsize=None, dpi=300):
    """Convert PNG to PDF via matplotlib for proper embedding."""
    try:
        with Image.open(png_path) as img:
            # Calculate figure size in inches for proper aspect ratio
            if figsize is None:
                aspect = img.width / img.height
                fig_w = min(IEEE_COLUMN_WIDTH, IEEE_FULL_WIDTH)
                fig_h = fig_w / aspect
                figsize = (fig_w, fig_h)

            fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
            ax.imshow(img)
            ax.axis('off')
            plt.tight_layout(pad=0)
            plt.savefig(pdf_path, format='pdf', bbox_inches='tight', pad_inches=0, dpi=dpi)
            plt.close()
            print(f"  Converted: {png_path} -> {pdf_path}")
            return True
    except Exception as e:
        print(f"  Error converting {png_path}: {e}")
        return False

def main():
    base_dir = "/Users/mihirmithani/Downloads/OpenRoad GUI"

    # Define figure mappings: (source_png, target_pdf, is_full_width)
    figures = [
        # Architecture diagram (already PDF, just copy)
        ("figures/architecture_layers.pdf", "figures/architecture_layers.pdf", False),

        # Model comparison (FULL WIDTH - key figure)
        ("plots_enhanced/8_model_performance_comparison.png", "figures/fig_model_comparison.pdf", True),

        # Platform outcomes (SINGLE COLUMN)
        ("plots_enhanced/1_platform_outcomes.png", "figures/fig_platform_outcomes.pdf", False),

        # Closure rates (SINGLE COLUMN)
        ("plots_enhanced/2_closure_rate_util_density.png", "figures/fig_closure_rates.pdf", False),

        # WNS evolution (SINGLE COLUMN)
        ("plots_enhanced/3a_wns_evolution_by_platform.png", "figures/fig_wns_evolution.pdf", False),

        # WNS waterfall (FULL WIDTH)
        ("plots_enhanced/3b_wns_improvement_waterfall.png", "figures/fig_wns_waterfall.pdf", True),

        # Closure outcomes (SINGLE COLUMN)
        ("plots_spec/01_closure_outcomes.png", "figures/fig_closure_outcomes.pdf", False),

        # PPA panel (SINGLE COLUMN - uses same as 3a_wns_evolution but different caption)
        ("plots_enhanced/3a_wns_evolution_by_platform.png", "figures/fig_ppa_panel.pdf", False),

        # Knob effects (SINGLE COLUMN)
        ("plots_enhanced/3a_knob_effects_box.png", "figures/fig_knob_effects.pdf", False),

        # Spearman correlation (SINGLE COLUMN)
        ("plots_enhanced/3c_spearman_correlation.png", "figures/fig_spearman.pdf", False),

        # Additional figures from plots/ directory (duplicates or alternatives)
        ("plots/2a_wns_evolution_by_platform.png", "figures/fig_wns_evolution_alt.pdf", False),
        ("plots/2b_wns_improvement_waterfall.png", "figures/fig_wns_waterfall_alt.pdf", True),
        ("plots/3a_knob_effects_box.png", "figures/fig_knob_effects_alt.pdf", False),
        ("plots/3c_spearman_correlation.png", "figures/fig_spearman_alt.pdf", False),
        ("plots/6_design_facet_wns_evolution.png", "figures/fig_design_facet.pdf", True),
        ("plots/7_normalized_within_design.png", "figures/fig_normalized.pdf", False),
    ]

    output_dir = "/Users/mihirmithani/Downloads/OpenRoad GUI/figures_optimized"
    os.makedirs(output_dir, exist_ok=True)

    print("Converting figures to optimized PDFs...")
    for src, dst, full_width in figures:
        src_path = os.path.join(base_dir, src)
        dst_path = os.path.join(output_dir, os.path.basename(dst))

        if not os.path.exists(src_path):
            print(f"  SKIP (not found): {src}")
            continue

        if src.endswith('.pdf'):
            # Just copy PDF files
            shutil.copy2(src_path, dst_path)
            print(f"  Copied PDF: {src} -> {dst}")
        else:
            # Convert PNG to PDF
            # For single column: 3.5" wide; full width: 7.16" wide
            if full_width:
                figsize = (IEEE_FULL_WIDTH, IEEE_FULL_WIDTH * 0.6)  # ~4.3" tall for 7.16" wide
            else:
                figsize = (IEEE_COLUMN_WIDTH, IEEE_COLUMN_WIDTH * 0.75)  # ~2.6" tall for 3.5" wide

            convert_png_to_pdf(src_path, dst_path, figsize=figsize, dpi=300)

    print("\nDone! Created optimized PDF figures in figures/ directory")

    # List created files
    print("\nCreated PDF figures:")
    for f in sorted(os.listdir(output_dir)):
        if f.endswith('.pdf'):
            size = os.path.getsize(os.path.join(output_dir, f)) / 1024
            print(f"  {f} ({size:.1f} KB)")

if __name__ == "__main__":
    main()