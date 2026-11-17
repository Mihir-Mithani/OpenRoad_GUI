#!/usr/bin/env python3
"""
Fix all PNG images for python-docx compatibility.
Converts RGBA to RGB with white background.
"""

from PIL import Image
import os

def fix_png_for_docx(input_path, output_path=None):
    """Convert RGBA PNG to RGB with white background for docx compatibility."""
    if output_path is None:
        output_path = input_path.replace('.png', '_docx.png')

    try:
        with Image.open(input_path) as img:
            if img.mode == 'RGBA':
                # Create white background
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])  # Use alpha as mask
                rgb_img.save(output_path, 'PNG', optimize=True)
                print(f"Fixed: {input_path} -> {output_path}")
                return True
            elif img.mode == 'P':
                # Palette mode - convert to RGB
                rgb_img = img.convert('RGB')
                rgb_img.save(output_path, 'PNG', optimize=True)
                print(f"Fixed (palette): {input_path} -> {output_path}")
                return True
            elif img.mode == 'RGB':
                # Already RGB, just re-save to ensure compatibility
                img.save(output_path, 'PNG', optimize=True)
                print(f"Re-saved (RGB): {input_path} -> {output_path}")
                return True
            else:
                # Convert to RGB
                rgb_img = img.convert('RGB')
                rgb_img.save(output_path, 'PNG', optimize=True)
                print(f"Converted ({img.mode}->RGB): {input_path} -> {output_path}")
                return True
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        return False

def main():
    base_dir = "/Users/mihirmithani/Downloads/OpenRoad GUI"

    # All figure paths that need fixing
    figure_paths = [
        # Architecture
        "figures/architecture_layers.png",

        # Enhanced plots
        "plots_enhanced/8_model_performance_comparison.png",
        "plots_enhanced/1_platform_outcomes.png",
        "plots_enhanced/2_closure_rate_util_density.png",
        "plots_enhanced/3a_wns_evolution_by_platform.png",
        "plots_enhanced/3b_wns_improvement_waterfall.png",
        "plots_enhanced/3a_knob_effects_box.png",
        "plots_enhanced/3c_spearman_correlation.png",
        "plots_enhanced/3b_wns_improvement_waterfall.png",
        "plots_enhanced/3a_knob_effects_box.png",  # duplicate key
        "plots_enhanced/3c_spearman_correlation.png",  # duplicate key
        "plots_enhanced/2a_wns_evolution_by_platform.png",
        "plots_enhanced/3a_knob_effects_box.png",
        "plots_enhanced/3c_spearman_correlation.png",
        "plots_enhanced/3b_wns_improvement_waterfall.png",

        # Spec plots
        "plots_spec/01_closure_outcomes.png",
        "plots_spec/02_stage_wns.png",
        "plots_spec/03_parameter_effects.png",
        "plots_spec/04_param_outcome_heatmap.png",
        "plots_spec/05_power_vs_area.png",

        # Original plots
        "plots/6_design_facet_wns_evolution.png",
        "plots/7_normalized_within_design.png",
        "plots/3b_parallel_coordinates.png",
        "plots/4a_power_vs_violations_loglog.png",
        "plots/4b_runtime_ecdf.png",
        "plots/4c_runs_per_design.png",
        "plots/5_timeline_gantt.png",

        # Architecture
        "figures/architecture_layers.png",
    ]

    # Remove duplicates
    figure_paths = list(set(figure_paths))

    fixed_dir = "/Users/mihirmithani/Downloads/OpenRoad GUI/figures_docx_ready"
    os.makedirs(fixed_dir, exist_ok=True)

    print("Fixing PNG images for python-docx compatibility...")
    for rel_path in figure_paths:
        input_path = os.path.join("/Users/mihirmithani/Downloads/OpenRoad GUI", rel_path)
        if os.path.exists(input_path):
            output_path = os.path.join(fixed_dir, os.path.basename(rel_path))
            fix_png_for_docx(input_path, output_path)
        else:
            print(f"NOT FOUND: {input_path}")

    print(f"\nFixed images saved to: {fixed_dir}")
    print("Use these fixed images in your DOCX generation script.")

if __name__ == "__main__":
    main()