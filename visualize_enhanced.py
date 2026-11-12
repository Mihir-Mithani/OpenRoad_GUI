#!/usr/bin/env python3
"""
Enhanced Visualization Suite for OpenROAD Flow GUI Intelligence Module
Generates publication-quality plots from the 161-run dataset.

Usage:
    python3 visualize_enhanced.py [--data-path PATH] [--output-dir PATH]
"""

import argparse
import json
import os
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

# ── Style Configuration ─────────────────────────────────────────────────────
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.2)

# Custom color palette for platforms
PLATFORM_COLORS = {
    'asap7': '#2D7DFF',
    'gf180': '#39D785',
    'nangate45': '#FFC857',
    'sky130hd': '#FF667A',
}
PLATFORM_ORDER = ['asap7', 'gf180', 'nangate45', 'sky130hd']
PLATFORM_LABELS = {
    'asap7': 'ASAP7 (7nm)',
    'gf180': 'GF180 (180nm)',
    'nangate45': 'Nangate45 (45nm)',
    'sky130hd': 'Sky130HD (130nm)',
}

# Custom colormap for WNS (negative = bad, positive = good)
wns_cmap = LinearSegmentedColormap.from_list('wns', ['#FF667A', '#FFC857', '#39D785'])

# ── Data Loading ────────────────────────────────────────────────────────────
def load_data(data_path: Path) -> pd.DataFrame:
    """Load and preprocess the runs data."""
    if data_path.suffix == '.json':
        df = pd.read_json(data_path)
    elif data_path.suffix == '.csv':
        df = pd.read_csv(data_path)
    else:
        raise ValueError(f"Unsupported format: {data_path.suffix}")

    # Ensure platform is categorical with correct order
    df['platform'] = pd.Categorical(df['platform'], categories=PLATFORM_ORDER, ordered=True)

    # Compute timing closure if not present
    if 'timing_closure' not in df.columns and 'final_wns_ns' in df.columns:
        df['timing_closure'] = df['final_wns_ns'] >= 0

    return df

# ── Helper Functions ────────────────────────────────────────────────────────
def save_figure(fig, output_dir: Path, name: str, dpi: int = 300):
    """Save figure with consistent naming."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.png"
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  ✅ Saved: {path}")

def annotate_bars(ax, fmt='{:.1f}', offset=3):
    """Add value labels on top of bars."""
    for bar in ax.patches:
        height = bar.get_height()
        if height > 0:
            ax.annotate(fmt.format(height),
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, offset), textcoords="offset points",
                       ha='center', va='bottom', fontsize=9, fontweight='bold')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 1: Platform Outcomes Summary
# ════════════════════════════════════════════════════════════════════════════
def plot_platform_outcomes(df: pd.DataFrame, output_dir: Path):
    """Stacked bar: success/failure/timed_out per platform."""
    fig, ax = plt.subplots(figsize=(10, 6))

    status_order = ['success', 'failed', 'timed_out', 'partial', 'metadata_only']
    status_colors = {
        'success': '#39D785',
        'failed': '#FF667A',
        'timed_out': '#FFC857',
        'partial': '#C084FC',
        'metadata_only': '#A7B7CD',
    }
    status_labels = {
        'success': 'Success',
        'failed': 'Failed',
        'timed_out': 'Timed Out',
        'partial': 'Partial',
        'metadata_only': 'Metadata Only',
    }

    platforms_present = [p for p in PLATFORM_ORDER if p in df['platform'].values]

    bottom = np.zeros(len(platforms_present))
    for status in status_order:
        counts = []
        for platform in platforms_present:
            count = len(df[(df['platform'] == platform) & (df['status'] == status)])
            counts.append(count)
        bars = ax.bar([PLATFORM_LABELS[p] for p in platforms_present],
                      counts, bottom=bottom, label=status_labels[status],
                      color=status_colors.get(status, '#888888'), width=0.6)
        bottom += counts

    # Add total count labels
    for i, platform in enumerate(platforms_present):
        total = len(df[df['platform'] == platform])
        ax.text(i, bottom[i] + 0.5, f'n={total}', ha='center', va='bottom',
                fontsize=11, fontweight='bold')

    ax.set_ylabel('Number of Runs', fontsize=12)
    ax.set_title('Run Outcomes by Platform', fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='upper right', framealpha=0.9)
    ax.set_ylim(0, max(bottom) * 1.2)

    save_figure(fig, output_dir, '1_platform_outcomes')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 2: Timing Closure Rate by Platform & Utilization/Density
# ════════════════════════════════════════════════════════════════════════════
def plot_closure_rate(df: pd.DataFrame, output_dir: Path):
    """Heatmap: timing closure rate by platform, utilization, density."""
    fig, ax = plt.subplots(figsize=(12, 5))

    # Only complete runs
    complete = df[df['data_completeness'] == 'complete'].copy()
    if len(complete) == 0:
        return

    # Bin utilization and density
    complete['util_bin'] = pd.cut(complete['core_utilization'],
                                   bins=[0, 25, 35, 50, 70, 100],
                                   labels=['20-25', '25-35', '35-50', '50-70', '70+'])
    complete['density_bin'] = pd.cut(complete['place_density'],
                                      bins=[0, 0.45, 0.55, 0.65, 0.8, 1.0],
                                      labels=['<0.45', '0.45-0.55', '0.55-0.65', '0.65-0.8', '0.8+'])

    # Create pivot tables for each platform
    n_platforms = len([p for p in PLATFORM_ORDER if p in complete['platform'].values])
    fig, axes = plt.subplots(1, n_platforms, figsize=(4*n_platforms, 4), sharey=True)
    if n_platforms == 1:
        axes = [axes]

    for idx, platform in enumerate([p for p in PLATFORM_ORDER if p in complete['platform'].values]):
        plat_data = complete[complete['platform'] == platform]
        pivot = plat_data.pivot_table(
            values='timing_closure', index='util_bin', columns='density_bin',
            aggfunc='mean', observed=False
        )

        # Plot heatmap
        im = axes[idx].imshow(pivot.values, aspect='auto', cmap='RdYlGn',
                               vmin=0, vmax=1, origin='lower')
        axes[idx].set_xticks(range(len(pivot.columns)))
        axes[idx].set_xticklabels(pivot.columns, rotation=45, ha='right', fontsize=9)
        axes[idx].set_yticks(range(len(pivot.index)))
        axes[idx].set_yticklabels(pivot.index, fontsize=9)
        axes[idx].set_title(f'{PLATFORM_LABELS[platform]}', fontsize=12, fontweight='bold')
        axes[idx].set_xlabel('Placement Density', fontsize=10)
        if idx == 0:
            axes[idx].set_ylabel('Core Utilization (%)', fontsize=10)

        # Annotate cells
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                val = pivot.iloc[i, j]
                if not np.isnan(val):
                    color = 'white' if val < 0.5 else 'black'
                    axes[idx].text(j, i, f'{val:.0%}', ha='center', va='center',
                                   color=color, fontsize=10, fontweight='bold')

    # Colorbar
    cbar = fig.colorbar(im, ax=axes, shrink=0.8)
    cbar.set_label('Timing Closure Rate', fontsize=11)

    fig.suptitle('Timing Closure Rate by Utilization & Density', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, output_dir, '2_closure_rate_util_density')

# ═════════════════════════════════════════════════════════════════════════════
# PLOT 3: WNS Evolution Across Stages
# ════════════════════════════════════════════════════════════════════════════
def plot_wns_evolution(df: pd.DataFrame, output_dir: Path):
    """Line plot: WNS progression through flow stages by platform."""
    fig, ax = plt.subplots(figsize=(12, 6))

    stages = ['synth_wns_ns', 'floorplan_wns_ns', 'place_wns_ns',
              'cts_wns_ns', 'route_wns_ns', 'final_wns_ns']
    stage_labels = ['Synth', 'Floorplan', 'Place', 'CTS', 'Route', 'Final']

    platforms_present = [p for p in PLATFORM_ORDER if p in df['platform'].values]

    for platform in platforms_present:
        plat_data = df[(df['platform'] == platform) & (df['data_completeness'] == 'complete')]
        if len(plat_data) == 0:
            continue

        # Mean WNS per stage
        means = []
        stds = []
        for stage in stages:
            vals = plat_data[stage].dropna()
            if len(vals) > 0:
                means.append(vals.mean())
                stds.append(vals.std())
            else:
                means.append(np.nan)
                stds.append(np.nan)

        x = range(len(stages))
        color = PLATFORM_COLORS[platform]
        ax.plot(x, means, 'o-', label=PLATFORM_LABELS[platform],
                color=color, linewidth=2.5, markersize=8)
        ax.fill_between(x,
                        np.array(means) - np.array(stds),
                        np.array(means) + np.array(stds),
                        alpha=0.15, color=color)

    # Reference line at WNS=0
    ax.axhline(y=0, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='Timing Closure (WNS=0)')

    ax.set_xticks(range(len(stages)))
    ax.set_xticklabels(stage_labels, fontsize=11)
    ax.set_ylabel('WNS (ns)', fontsize=12)
    ax.set_xlabel('Flow Stage', fontsize=12)
    ax.set_title('WNS Evolution Across Flow Stages by Platform', fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='lower right', framealpha=0.9)
    ax.grid(True, alpha=0.3)

    save_figure(fig, output_dir, '3a_wns_evolution_by_platform')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 4: WNS Improvement Waterfall
# ════════════════════════════════════════════════════════════════════════════
def plot_wns_improvement(df: pd.DataFrame, output_dir: Path):
    """Waterfall: WNS improvement from synth to final per design."""
    fig, ax = plt.subplots(figsize=(14, 7))

    complete = df[(df['data_completeness'] == 'complete') &
                  (df['synth_wns_ns'].notna()) & (df['final_wns_ns'].notna())].copy()

    if len(complete) == 0:
        return

    complete['wns_improvement'] = complete['final_wns_ns'] - complete['synth_wns_ns']
    complete = complete.sort_values('wns_improvement')

    platforms_present = [p for p in PLATFORM_ORDER if p in complete['platform'].values]
    colors = [PLATFORM_COLORS[p] for p in complete['platform']]

    bars = ax.barh(range(len(complete)), complete['wns_improvement'],
                   color=colors, edgecolor='white', linewidth=0.5, height=0.7)

    # Design labels
    labels = [f"{row['platform']}/{row['design_name']}" for _, row in complete.iterrows()]
    ax.set_yticks(range(len(complete)))
    ax.set_yticklabels(labels, fontsize=9)

    ax.axvline(x=0, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.set_xlabel('WNS Improvement (ns) [Final - Synth]', fontsize=12)
    ax.set_title('WNS Improvement from Synthesis to Final by Design',
                 fontsize=14, fontweight='bold', pad=15)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=PLATFORM_COLORS[p], label=PLATFORM_LABELS[p])
                       for p in platforms_present]
    ax.legend(handles=legend_elements, loc='lower right', framealpha=0.9)

    save_figure(fig, output_dir, '3b_wns_improvement_waterfall')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 5: Knob Effects (Box plots)
# ════════════════════════════════════════════════════════════════════════════
def plot_knob_effects(df: pd.DataFrame, output_dir: Path):
    """Box plots: WNS by utilization, aspect ratio, margin, density."""
    complete = df[(df['data_completeness'] == 'complete') &
                  (df['final_wns_ns'].notna())].copy()

    if len(complete) == 0:
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    knobs = [
        ('core_utilization', 'Core Utilization (%)', 'Core Utilization'),
        ('core_aspect_ratio', 'Core Aspect Ratio', 'Aspect Ratio'),
        ('core_margin', 'Core Margin (%)', 'Core Margin'),
        ('place_density', 'Placement Density', 'Placement Density'),
    ]

    for idx, (col, ylabel, title) in enumerate(knobs):
        ax = axes[idx]

        # Create bins for continuous variables
        if col in ['core_utilization', 'place_density']:
            complete[f'{col}_bin'] = pd.qcut(complete[col], q=5, duplicates='drop')
            sns.boxplot(data=complete, x=f'{col}_bin', y='final_wns_ns',
                        hue='platform', palette=PLATFORM_COLORS, ax=ax)
        else:
            sns.boxplot(data=complete, x=col, y='final_wns_ns',
                        hue='platform', palette=PLATFORM_COLORS, ax=ax)

        ax.axhline(y=0, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        ax.set_xlabel('')
        ax.set_ylabel('Final WNS (ns)', fontsize=11)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.tick_params(axis='x', rotation=30)
        if idx > 0:
            ax.get_legend().remove()
        else:
            ax.legend(loc='lower right', fontsize=9)

    fig.suptitle('WNS Distribution by Flow Configuration Knobs', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, output_dir, '3a_knob_effects_box')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 6: Parallel Coordinates
# ════════════════════════════════════════════════════════════════════════════
def plot_parallel_coordinates(df: pd.DataFrame, output_dir: Path):
    """Parallel coordinates: design parameters colored by WNS."""
    complete = df[(df['data_completeness'] == 'complete') &
                  (df['final_wns_ns'].notna())].copy()

    if len(complete) == 0:
        return

    # Select features (use actual column names from data)
    features = ['core_utilization', 'core_aspect_ratio', 'core_margin',
                'place_density', 'final_wns_ns', 'final_area_um2', 'final_power_w']
    # Only use features that exist in the data
    available_features = [f for f in features if f in complete.columns]
    plot_data = complete[available_features + ['platform']].dropna()

    if len(plot_data) < 2:
        return

    fig, ax = plt.subplots(figsize=(14, 7))

    # Normalize for parallel coordinates
    for col in features:
        if col != 'platform':
            min_v, max_v = plot_data[col].min(), plot_data[col].max()
            if max_v > min_v:
                plot_data[col] = (plot_data[col] - min_v) / (max_v - min_v)

    # Color by WNS (original, not normalized)
    colors = plt.cm.RdYlGn((plot_data['final_wns_ns'] - plot_data['final_wns_ns'].min()) /
                            (plot_data['final_wns_ns'].max() - plot_data['final_wns_ns'].min() + 1e-9))

    # Plot
    from matplotlib.collections import LineCollection
    lines = []
    for _, row in plot_data.iterrows():
        lines.append(list(zip(range(len(features)), [row[c] for c in features])))

    lc = LineCollection(lines, colors=colors, alpha=0.3, linewidth=0.5)
    ax.add_collection(lc)

    # Axis formatting
    ax.set_xticks(range(len(features)))
    ax.set_xticklabels(['Util (%)', 'AR', 'Margin (%)', 'Density', 'WNS (ns)', 'Area (μm²)', 'Power (mW)'],
                       rotation=30, ha='right', fontsize=10)
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel('Normalized Value', fontsize=11)
    ax.set_title('Parallel Coordinates: Design Parameters & PPA (colored by WNS)',
                 fontsize=14, fontweight='bold', pad=15)

    # Colorbar
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    norm = Normalize(vmin=complete['final_wns_ns'].min(), vmax=complete['final_wns_ns'].max())
    sm = ScalarMappable(cmap='RdYlGn', norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.6)
    cbar.set_label('WNS (ns)', fontsize=11)

    save_figure(fig, output_dir, '3b_parallel_coordinates')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 7: Spearman Correlation Heatmap
# ════════════════════════════════════════════════════════════════════════════
def plot_correlation_heatmap(df: pd.DataFrame, output_dir: Path):
    """Spearman correlation between all PPA metrics and design parameters."""
    complete = df[(df['data_completeness'] == 'complete')].copy()

    # Use actual column names from data
    metrics = ['final_wns_ns', 'final_tns_ns', 'final_area_um2', 'final_power_w',
               'final_setup_violations', 'timing_closure']
    params = ['core_utilization', 'core_aspect_ratio', 'core_margin', 'place_density',
              'num_instances', 'num_nets', 'num_sequential', 'num_macros']
    # num_instances etc not in data - just use available params
    params = ['core_utilization', 'core_aspect_ratio', 'core_margin', 'place_density']

    available_metrics = [m for m in metrics if m in complete.columns]
    available_params = [p for p in params if p in complete.columns]

    if len(available_metrics) == 0 or len(available_params) == 0:
        return

    corr_data = complete[available_metrics + available_params]
    spearman_corr = corr_data.corr(method='spearman')

    # Extract cross-correlation
    cross_corr = spearman_corr.loc[available_metrics, available_params]

    fig, ax = plt.subplots(figsize=(12, 6))

    im = ax.imshow(cross_corr.values, aspect='auto', cmap='RdBu_r', vmin=-1, vmax=1)

    ax.set_xticks(range(len(available_params)))
    ax.set_xticklabels([p.replace('_', ' ').title() for p in available_params],
                       rotation=45, ha='right', fontsize=10)
    ax.set_yticks(range(len(available_metrics)))
    ax.set_yticklabels([m.replace('_', ' ').title() for m in available_metrics], fontsize=10)

    # Annotate
    for i in range(len(available_metrics)):
        for j in range(len(available_params)):
            val = cross_corr.iloc[i, j]
            color = 'white' if abs(val) > 0.5 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    color=color, fontsize=9, fontweight='bold')

    ax.set_title('Spearman Correlation: PPA Metrics vs Design Parameters',
                 fontsize=14, fontweight='bold', pad=15)

    cbar = plt.colorbar(im, ax=ax, shrink=0.6)
    cbar.set_label('Spearman ρ', fontsize=11)

    save_figure(fig, output_dir, '3c_spearman_correlation')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 8: Power vs Violations (Log-Log)
# ════════════════════════════════════════════════════════════════════════════
def plot_power_vs_violations(df: pd.DataFrame, output_dir: Path):
    """Scatter: Power vs DRC violations, colored by WNS."""
    # Use final_setup_violations as proxy for DRC violations, final_power_w in Watts
    complete = df[(df['data_completeness'] == 'complete') &
                  (df['final_power_w'].notna()) & (df['final_setup_violations'].notna())].copy()

    if len(complete) == 0:
        return

    fig, ax = plt.subplots(figsize=(10, 7))

    scatter = ax.scatter(complete['final_setup_violations'] + 1,
                         complete['final_power_w'] * 1000,  # Convert W to mW
                         c=complete['final_wns_ns'], cmap='RdYlGn',
                         s=80, alpha=0.7, edgecolors='white', linewidth=0.5)

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Setup Violations + 1', fontsize=12)
    ax.set_ylabel('Total Power (mW)', fontsize=12)
    ax.set_title('Power vs Setup Violations (Log-Log)', fontsize=14, fontweight='bold', pad=15)

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('WNS (ns)', fontsize=11)

    # Annotate designs
    for _, row in complete.iterrows():
        ax.annotate(f"{row['platform']}/{row['design_name']}",
                    (row['final_setup_violations'] + 1, row['final_power_w'] * 1000),
                    fontsize=7, alpha=0.7, xytext=(3, 3), textcoords='offset points')

    save_figure(fig, output_dir, '4a_power_vs_violations_loglog')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 9: Runtime ECDF
# ════════════════════════════════════════════════════════════════════════════
def plot_runtime_ecdf(df: pd.DataFrame, output_dir: Path):
    """ECDF of total runtime by platform. (Skipped - no runtime column in current data)"""
    # No total_runtime_sec column in current dataset
    print("  ⏭️  Skipped: total_runtime_sec not in dataset")
    return

    if len(complete) == 0:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    for platform in PLATFORM_ORDER:
        if platform not in complete['platform'].values:
            continue
        plat_data = complete[complete['platform'] == platform]
        runtimes = plat_data['total_runtime_sec'].values
        runtimes = np.sort(runtimes)
        y = np.arange(1, len(runtimes) + 1) / len(runtimes)
        ax.plot(runtimes / 60, y, 'o-', label=PLATFORM_LABELS[platform],
                color=PLATFORM_COLORS[platform], linewidth=2, markersize=5)

    ax.set_xlabel('Total Runtime (minutes)', fontsize=12)
    ax.set_ylabel('ECDF', fontsize=12)
    ax.set_title('Runtime Distribution by Platform (ECDF)', fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='lower right', framealpha=0.9)
    ax.grid(True, alpha=0.3)

    save_figure(fig, output_dir, '4b_runtime_ecdf')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 10: Runs per Design
# ════════════════════════════════════════════════════════════════════════════
def plot_runs_per_design(df: pd.DataFrame, output_dir: Path):
    """Bar: Number of runs per design, colored by platform."""
    design_counts = df.groupby(['platform', 'design_name']).size().reset_index(name='count')
    design_counts = design_counts.sort_values('count', ascending=True)

    fig, ax = plt.subplots(figsize=(12, max(8, len(design_counts) * 0.3)))

    colors = [PLATFORM_COLORS[p] for p in design_counts['platform']]
    bars = ax.barh(range(len(design_counts)), design_counts['count'],
                   color=colors, edgecolor='white', linewidth=0.5, height=0.7)

    labels = [f"{row['platform']}/{row['design_name']}" for _, row in design_counts.iterrows()]
    ax.set_yticks(range(len(design_counts)))
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel('Number of Runs', fontsize=12)
    ax.set_title('Number of Runs per Design', fontsize=14, fontweight='bold', pad=15)

    # Legend
    from matplotlib.patches import Patch
    platforms_present = design_counts['platform'].unique()
    legend_elements = [Patch(facecolor=PLATFORM_COLORS[p], label=PLATFORM_LABELS[p])
                       for p in platforms_present]
    ax.legend(handles=legend_elements, loc='lower right', framealpha=0.9)

    annotate_bars(ax, fmt='{:.0f}', offset=5)

    save_figure(fig, output_dir, '4c_runs_per_design')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 11: Timeline Gantt
# ════════════════════════════════════════════════════════════════════════════
def plot_timeline_gantt(df: pd.DataFrame, output_dir: Path):
    """Gantt chart of run timelines."""
    complete = df[(df['start_utc'].notna()) & (df['end_utc'].notna())].copy()

    if len(complete) == 0:
        return

    complete['start'] = pd.to_datetime(complete['start_utc'])
    complete['end'] = pd.to_datetime(complete['end_utc'])
    complete = complete.sort_values('start')

    fig, ax = plt.subplots(figsize=(14, max(8, len(complete) * 0.25)))

    for i, (_, row) in enumerate(complete.iterrows()):
        color = PLATFORM_COLORS.get(row['platform'], '#888888')
        duration = (row['end'] - row['start']).total_seconds() / 3600  # hours
        ax.barh(i, duration, left=0, height=0.6, color=color, alpha=0.8, edgecolor='white')
        ax.text(duration + 0.1, i, f"{row['platform']}/{row['design_name']} ({duration:.1f}h)",
                va='center', fontsize=8)

    ax.set_yticks(range(len(complete)))
    ax.set_yticklabels([f"{row['platform']}/{row['design_name']}" for _, row in complete.iterrows()], fontsize=9)
    ax.set_xlabel('Duration (hours)', fontsize=12)
    ax.set_title('Run Timeline (Gantt Chart)', fontsize=14, fontweight='bold', pad=15)
    ax.invert_yaxis()

    save_figure(fig, output_dir, '5_timeline_gantt')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 12: Design Facet WNS Evolution
# ════════════════════════════════════════════════════════════════════════════
def plot_design_facet_wns(df: pd.DataFrame, output_dir: Path):
    """Facet grid: WNS evolution per design."""
    complete = df[(df['data_completeness'] == 'complete')].copy()

    stages = ['synth_wns_ns', 'floorplan_wns_ns', 'place_wns_ns',
              'cts_wns_ns', 'route_wns_ns', 'final_wns_ns']
    stage_labels = ['Synth', 'Floorplan', 'Place', 'CTS', 'Route', 'Final']

    designs = complete[['platform', 'design_name']].drop_duplicates()
    if len(designs) == 0:
        return

    n_designs = len(designs)
    n_cols = 3
    n_rows = (n_designs + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6*n_cols, 4*n_rows), sharex=True, sharey=True)
    axes = axes.flatten() if n_designs > 1 else [axes]

    for idx, (_, design) in enumerate(designs.iterrows()):
        ax = axes[idx]
        plat_data = complete[(complete['platform'] == design['platform']) &
                            (complete['design_name'] == design['design_name'])]

        means = []
        for stage in stages:
            vals = plat_data[stage].dropna()
            means.append(vals.mean() if len(vals) > 0 else np.nan)

        color = PLATFORM_COLORS[design['platform']]
        ax.plot(range(len(stages)), means, 'o-', color=color, linewidth=2, markersize=6)
        ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7)
        ax.set_xticks(range(len(stages)))
        ax.set_xticklabels(stage_labels, rotation=30, ha='right', fontsize=8)
        ax.set_title(f"{design['platform']}/{design['design_name']}", fontsize=10, fontweight='bold')
        ax.grid(True, alpha=0.3)
        if idx % n_cols == 0:
            ax.set_ylabel('WNS (ns)', fontsize=10)

    # Hide unused axes
    for idx in range(n_designs, len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle('WNS Evolution by Design', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, output_dir, '6_design_facet_wns_evolution')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 13: Normalized Within-Design Comparison
# ════════════════════════════════════════════════════════════════════════════
def plot_normalized_within_design(df: pd.DataFrame, output_dir: Path):
    """Normalize metrics within each design for cross-design comparison."""
    complete = df[(df['data_completeness'] == 'complete')].copy()

    metrics = ['final_wns_ns', 'final_tns_ns', 'final_area_um2', 'final_power_w']
    available = [m for m in metrics if m in complete.columns]

    if len(available) == 0:
        return

    # Normalize within each design (z-score)
    for metric in available:
        complete[f'{metric}_norm'] = complete.groupby(['platform', 'design_name'])[metric].transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-9)
        )

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    for idx, metric in enumerate(available):
        ax = axes[idx]
        sns.boxplot(data=complete, x='platform', y=f'{metric}_norm',
                    order=PLATFORM_ORDER, palette=PLATFORM_COLORS, ax=ax)
        ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7)
        ax.set_xlabel('')
        ax.set_ylabel('Z-Score (Within Design)', fontsize=11)
        ax.set_title(metric.replace('_', ' ').title(), fontsize=12, fontweight='bold')

    fig.suptitle('Normalized PPA Metrics Within Each Design (Z-Score)',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, output_dir, '7_normalized_within_design')

# ════════════════════════════════════════════════════════════════════════════
# PLOT 14: Model Performance Comparison
# ════════════════════════════════════════════════════════════════════════════
def plot_model_performance(df: pd.DataFrame, output_dir: Path):
    """Bar chart comparing model performance metrics (hardcoded from training results)."""
    # Data from latest training (Session 16)
    models = ['LightGBM', 'MLP', 'Ensemble']
    targets = ['WNS', 'TNS', 'Area', 'Power']

    cv_r2 = {
        'WNS': [0.212, 0.229, 0.230],
        'TNS': [0.203, 0.196, 0.212],
        'Area': [0.824, -0.202, 0.547],
        'Power': [0.551, 0.584, 0.606],
    }

    test_r2 = {
        'WNS': [0.200, 0.216, 0.218],
        'TNS': [0.228, 0.248, 0.249],
        'Area': [0.627, -0.078, 0.417],
        'Power': [0.459, 0.752, 0.655],
    }

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, target in enumerate(targets):
        ax = axes[idx]
        x = np.arange(len(models))
        width = 0.35

        cv_vals = [cv_r2[target][i] if i < len(cv_r2[target]) else 0 for i in range(len(models))]
        test_vals = [test_r2[target][i] if i < len(test_r2[target]) else 0 for i in range(len(models))]

        bars1 = ax.bar(x - width/2, cv_vals, width, label='CV R²',
                       color='#2D7DFF', alpha=0.8, edgecolor='white')
        bars2 = ax.bar(x + width/2, test_vals, width, label='Test R²',
                       color='#39D785', alpha=0.8, edgecolor='white')

        ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(models, fontsize=11)
        ax.set_ylabel('R² Score', fontsize=11)
        ax.set_title(f'{target} - Model Performance Comparison', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.set_ylim(-0.3, 1.0)
        ax.grid(True, alpha=0.3, axis='y')

        # Annotate values
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.annotate(f'{height:.3f}',
                               xy=(bar.get_x() + bar.get_width() / 2, height),
                               xytext=(0, 3), textcoords="offset points",
                               ha='center', va='bottom', fontsize=9, fontweight='bold')

    fig.suptitle('Model Performance: CV vs Test R² by Target', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, output_dir, '8_model_performance_comparison')

# ════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Enhanced Visualization Suite for OpenROAD Intelligence")
    parser.add_argument('--data-path', type=Path,
                        default=Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs.json"),
                        help="Path to runs data (JSON or CSV)")
    parser.add_argument('--output-dir', type=Path,
                        default=Path("/Users/mihirmithani/Downloads/OpenRoad GUI/plots_enhanced"),
                        help="Output directory for plots")
    args = parser.parse_args()

    print("=" * 70)
    print("ENHANCED VISUALIZATION SUITE - OpenROAD Intelligence")
    print("=" * 70)
    print(f"Data: {args.data_path}")
    print(f"Output: {args.output_dir}")
    print("=" * 70)

    # Load data
    df = load_data(args.data_path)
    print(f"Loaded {len(df)} runs across {df['platform'].nunique()} platforms")
    print(f"Platforms: {df['platform'].value_counts().to_dict()}")
    print(f"Completeness: {df['data_completeness'].value_counts().to_dict()}")

    # Generate all plots
    plots = [
        ("Platform Outcomes", plot_platform_outcomes),
        ("Closure Rate by Util/Density", plot_closure_rate),
        ("WNS Evolution", plot_wns_evolution),
        ("WNS Improvement Waterfall", plot_wns_improvement),
        ("Knob Effects", plot_knob_effects),
        ("Parallel Coordinates", plot_parallel_coordinates),
        ("Spearman Correlation", plot_correlation_heatmap),
        ("Power vs Violations", plot_power_vs_violations),
        ("Runtime ECDF", plot_runtime_ecdf),
        ("Runs per Design", plot_runs_per_design),
        ("Timeline Gantt", plot_timeline_gantt),
        ("Design Facet WNS", plot_design_facet_wns),
        ("Normalized Within-Design", plot_normalized_within_design),
        ("Model Performance", plot_model_performance),
    ]

    print("\nGenerating plots...")
    for name, func in plots:
        print(f"  📊 {name}...")
        try:
            func(df, args.output_dir)
        except Exception as e:
            print(f"    ❌ Failed: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ All plots saved to: {args.output_dir}")
    print("=" * 70)


if __name__ == '__main__':
    main()