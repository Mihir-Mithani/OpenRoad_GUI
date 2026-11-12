#!/usr/bin/env python3
"""
Specification-Compliant Visualization Suite for OpenROAD Flow GUI Intelligence Module
Implements the exact plots specified in the design document.

Usage:
    python3 visualize_spec_compliant.py [--data-path PATH] [--output-dir PATH]
"""

import argparse
import json
import os
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.ticker as ticker
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
import seaborn as sns

# ── Style Configuration ─────────────────────────────────────────────────────
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.1)

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

# Outcome colors
OUTCOME_COLORS = {
    'Closed': '#39D785',           # green
    'Timing violated': '#FFC857',  # amber
    'Flow failed': '#FF667A',      # red
    'Partial': '#C084FC',          # purple
    'Metadata only': '#A7B7CD',    # gray
}

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

    # Create design|platform identifier
    df['design_platform'] = df['design_name'] + ' | ' + df['platform'].astype(str)

    # Define outcome based on status and timing_closure
    def determine_outcome(row):
        if row['status'] == 'success':
            if row.get('timing_closure', False):
                return 'Closed'
            else:
                return 'Timing violated'
        elif row['status'] == 'failed':
            return 'Flow failed'
        elif row['status'] == 'timed_out':
            return 'Flow failed'
        elif row['status'] == 'partial':
            return 'Partial'
        else:
            return 'Metadata only'

    df['outcome'] = df.apply(determine_outcome, axis=1)

    return df

def save_figure(fig, output_dir: Path, name: str, dpi: int = 300):
    """Save figure with consistent naming."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.png"
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  ✅ Saved: {path}")

# ════════════════════════════════════════════════════════════════════════════
# PLOT 1: Closure Outcome by Design|Platform (01_closure_outcomes.png)
# ════════════════════════════════════════════════════════════════════════════
def plot_closure_outcomes(df: pd.DataFrame, output_dir: Path):
    """100% stacked horizontal bar: closure outcome by design|platform."""
    # Filter to complete runs
    complete = df[df['data_completeness'] == 'complete'].copy()

    # Group by design_platform and outcome
    counts = complete.groupby(['design_platform', 'outcome']).size().unstack(fill_value=0)

    # Calculate percentages
    totals = counts.sum(axis=1)
    pcts = counts.div(totals, axis=0) * 100

    # Sort by Closed % ascending (best at top)
    if 'Closed' in pcts.columns:
        pcts = pcts.sort_values('Closed', ascending=True)
    else:
        pcts = pcts.sort_index()

    # Add n to labels
    labels = []
    for dp in pcts.index:
        n = totals[dp]
        labels.append(f"{dp} (n={n})")
    pcts.index = labels

    # Ensure outcome order
    outcome_order = ['Closed', 'Timing violated', 'Flow failed', 'Partial', 'Metadata only']
    available_outcomes = [o for o in outcome_order if o in pcts.columns]
    pcts = pcts[available_outcomes]

    fig, ax = plt.subplots(figsize=(10, max(6, len(pcts) * 0.35)))

    bottom = np.zeros(len(pcts))
    for outcome in available_outcomes:
        bars = ax.barh(range(len(pcts)), pcts[outcome], left=bottom,
                       height=0.7, color=OUTCOME_COLORS.get(outcome, '#888888'),
                       label=outcome, edgecolor='white', linewidth=0.3)
        bottom += pcts[outcome].values

    ax.set_yticks(range(len(pcts)))
    ax.set_yticklabels(pcts.index, fontsize=9)
    ax.set_xlabel('% of Runs', fontsize=11)
    ax.set_xlim(0, 100)
    ax.set_title('Only 3 of 13 combinations ever close timing', fontsize=13, fontweight='bold', pad=15)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.15), ncol=len(available_outcomes),
              framealpha=0.9, fontsize=9)
    ax.grid(False, axis='y')

    # Annotate segments with %
    for i, outcome in enumerate(available_outcomes):
        for j in range(len(pcts)):
            val = pcts.iloc[j][outcome]
            if val >= 5:  # Only label if big enough
                left = sum(pcts.iloc[j][o] for o in available_outcomes[:available_outcomes.index(outcome)])
                color = 'white' if val > 15 else 'black'
                ax.text(left + val/2, j, f'{val:.0f}%',
                       ha='center', va='center', color=color, fontsize=8, fontweight='bold')

    save_figure(fig, output_dir, '01_closure_outcomes')


# ════════════════════════════════════════════════════════════════════════════
# PLOT 2: Parameter Effects (03_parameter_effects.png) - Two panels
# ════════════════════════════════════════════════════════════════════════════
def plot_parameter_effects(df: pd.DataFrame, output_dir: Path):
    """Two panels: (left) Aspect ratio vs WNS for riscv32i-mock-sram|asap7;
       (right) Utilization vs outcome for gcd|sky130hd"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # ── Left Panel: Aspect ratio vs final WNS, riscv32i-mock-sram|asap7 ──
    ax = axes[0]
    filtered = df[
        (df['design_name'] == 'riscv32i-mock-sram') &
        (df['platform'] == 'asap7') &
        (df['status'] == 'success') &
        (df['data_completeness'] == 'complete')
    ].copy()

    if len(filtered) > 0:
        # Strip plot with jitter
        for outcome in ['Closed', 'Timing violated', 'Flow failed']:
            subset = filtered[filtered['outcome'] == outcome]
            if len(subset) == 0:
                continue
            x_vals = subset['core_aspect_ratio'].values
            y_vals = subset['final_wns_ns'].values
            # Add jitter
            x_jitter = x_vals + np.random.uniform(-0.12, 0.12, len(x_vals))
            ax.scatter(x_jitter, y_vals, c=OUTCOME_COLORS.get(outcome, '#888888'),
                      s=60, alpha=0.85, edgecolors='white', linewidth=0.5,
                      label=outcome, zorder=3)

        ax.set_xlabel('Core Aspect Ratio', fontsize=11)
        ax.set_ylabel('Final WNS (ns)', fontsize=11)
        ax.set_xticks([0.5, 1.0, 2.0])
        ax.set_ylim(-2.1, 0.25)
        ax.axhline(y=0, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        ax.set_title('Aspect ratio 1.0 closes 14/14; 0.5 and 2.0 close 0/9',
                    fontsize=11, fontweight='bold', pad=10)
        ax.legend(loc='upper right', framealpha=0.9, fontsize=9)
        ax.grid(True, alpha=0.3)

    # ── Right Panel: Utilization vs outcome, gcd|sky130hd ──
    ax = axes[1]
    filtered = df[
        (df['design_name'] == 'gcd') &
        (df['platform'] == 'sky130hd') &
        (df['data_completeness'] == 'complete')
    ].copy()

    if len(filtered) > 0:
        # Stacked bar: utilization bins vs outcome counts
        util_bins = sorted(filtered['core_utilization'].unique())
        util_labels = [f'{int(u)}%' for u in util_bins]

        outcome_order = ['Closed', 'Timing violated', 'Flow failed']
        bottom = np.zeros(len(util_bins))

        for outcome in outcome_order:
            counts = []
            for u in util_bins:
                cnt = len(filtered[(filtered['core_utilization'] == u) & (filtered['outcome'] == outcome)])
                counts.append(cnt)
            counts = np.array(counts)
            if counts.sum() > 0:
                ax.bar(range(len(util_bins)), counts, bottom=bottom,
                       label=outcome, color=OUTCOME_COLORS.get(outcome, '#888888'),
                       width=0.6, edgecolor='white', linewidth=0.3)
                bottom += counts

        ax.set_xticks(range(len(util_bins)))
        ax.set_xticklabels(util_labels, fontsize=10)
        ax.set_ylabel('Number of Runs', fontsize=11)
        ax.set_xlabel('Core Utilization', fontsize=11)
        ax.set_title('Every run at utilization ≥ 50% failed', fontsize=11, fontweight='bold', pad=10)
        ax.legend(loc='upper right', framealpha=0.9, fontsize=9)
        ax.grid(False, axis='x')

    fig.suptitle('Parameter Effects by Design|Platform', fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, output_dir, '03_parameter_effects')


# ════════════════════════════════════════════════════════════════════════════
# PLOT 3: WNS Through the Flow (02_stage_wns.png)
# ════════════════════════════════════════════════════════════════════════════
def plot_stage_wns(df: pd.DataFrame, output_dir: Path):
    """Line chart, small multiples: WNS through flow stages by design|platform."""
    complete = df[df['data_completeness'] == 'complete'].copy()

    stages = ['synth_wns_ns', 'floorplan_wns_ns', 'place_wns_ns',
              'cts_wns_ns', 'route_wns_ns', 'final_wns_ns']
    stage_labels = ['Synth', 'Floorplan', 'Place', 'CTS', 'Route', 'Final']

    # Get design|platform combos with their counts
    combos = complete.groupby(['design_name', 'platform']).size().reset_index(name='n')
    combos = combos.sort_values('n', ascending=False)

    n_combos = len(combos)
    n_cols = 4
    n_rows = (n_combos + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 11), sharex=True, sharey=True)
    axes = axes.flatten() if n_combos > 1 else [axes]

    for idx, (_, row) in enumerate(combos.iterrows()):
        ax = axes[idx]
        plat_data = complete[
            (complete['design_name'] == row['design_name']) &
            (complete['platform'] == row['platform'])
        ]

        if len(plat_data) == 0:
            ax.set_visible(False)
            continue

        # Plot individual runs (thin, alpha 0.25)
        platform = row['platform']
        color = PLATFORM_COLORS.get(platform, '#888888')

        for _, run in plat_data.iterrows():
            wns_vals = []
            for stage in stages:
                if pd.notna(run[stage]):
                    wns_vals.append(run[stage])
                else:
                    wns_vals.append(np.nan)

            if not all(np.isnan(v) for v in wns_vals):
                ax.plot(range(len(stages)), wns_vals, '-',
                       color=color, alpha=0.25, linewidth=0.8, zorder=1)

        # Median line (bold black)
        medians = []
        for stage in stages:
            vals = plat_data[stage].dropna()
            medians.append(vals.median() if len(vals) > 0 else np.nan)

        valid = ~np.isnan(np.array(medians))
        if valid.any():
            ax.plot(np.array(range(len(stages)))[valid], np.array(medians)[valid],
                   'o-', color='black', linewidth=2.5, markersize=6, zorder=5,
                   label='Median' if idx == 0 else "")

        ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7, zorder=2)
        ax.set_xticks(range(len(stages)))
        ax.set_xticklabels(stage_labels, rotation=30, ha='right', fontsize=8)
        ax.set_title(f"{row['design_name']} | {row['platform']} (n={row['n']})",
                    fontsize=9, fontweight='bold')
        ax.grid(True, alpha=0.3)

        # Symlog scale
        ax.set_yscale('symlog', linthresh=0.01)
        ax.set_ylim(-5000, 2)
        # Custom ticks
        ticks = [-1000, -100, -10, -1, -0.1, 0]
        ax.set_yticks(ticks)
        ax.set_yticklabels([str(t) for t in ticks], fontsize=7)

        if idx % n_cols == 0:
            ax.set_ylabel('WNS (ns)', fontsize=10)

    # Hide unused axes
    for idx in range(n_combos, len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle('Worst negative slack by flow stage', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, output_dir, '02_stage_wns')


# ════════════════════════════════════════════════════════════════════════════
# PLOT 4: Parameter × Outcome Correlation Heatmap (04_param_outcome_heatmap.png)
# ════════════════════════════════════════════════════════════════════════════
def plot_param_outcome_heatmap(df: pd.DataFrame, output_dir: Path):
    """Diverging heatmap: 3 panels (WNS, Power, Area) showing Spearman ρ."""
    complete = df[(df['data_completeness'] == 'complete') &
                  (df['status'] == 'success')].copy()

    # Design|platform combos with n >= 9
    combo_counts = complete.groupby(['design_name', 'platform']).size()
    valid_combos = combo_counts[combo_counts >= 9].index.tolist()

    if len(valid_combos) == 0:
        print("  ⚠️  No combos with n>=9, skipping heatmap")
        return

    # Filter to valid combos
    mask = complete.set_index(['design_name', 'platform']).index.isin(valid_combos)
    filtered = complete[mask].copy()

    # Parameters and targets
    params = ['core_utilization', 'core_aspect_ratio', 'core_margin', 'place_density']
    targets = {
        'WNS': 'final_wns_ns',
        'Power': 'final_power_w',
        'Area': 'final_area_um2',
    }

    available_params = [p for p in params if p in filtered.columns]
    available_targets = {k: v for k, v in targets.items() if v in filtered.columns}

    if len(available_params) == 0 or len(available_targets) == 0:
        return

    n_targets = len(available_targets)
    fig, axes = plt.subplots(1, n_targets, figsize=(5 * n_targets, 5.5), sharey=True)
    if n_targets == 1:
        axes = [axes]

    for idx, (target_name, target_col) in enumerate(available_targets.items()):
        ax = axes[idx]

        # Compute Spearman ρ within each design|platform
        rho_matrix = []
        combo_labels = []

        for (design, platform), group in filtered.groupby(['design_name', 'platform']):
            if len(group) < 2:
                continue
            row = []
            valid_params = []
            for param in available_params:
                if group[param].nunique() > 1 and group[target_col].nunique() > 1:
                    rho, _ = group[param].corr(group[target_col], method='spearman'), 0
                    if not np.isnan(rho):
                        row.append(rho)
                        valid_params.append(param)
                    else:
                        row.append(np.nan)
                else:
                    row.append(np.nan)
            if len(row) == len(available_params):
                rho_matrix.append(row)
                combo_labels.append(f"{design} | {platform}")

        if len(rho_matrix) == 0:
            ax.set_visible(False)
            continue

        rho_df = pd.DataFrame(rho_matrix, columns=available_params, index=combo_labels)

        # Plot heatmap
        im = ax.imshow(rho_df.values, aspect='auto', cmap='RdBu_r',
                       vmin=-1, vmax=1, origin='lower')

        ax.set_xticks(range(len(available_params)))
        ax.set_xticklabels([p.replace('_', ' ').title() for p in available_params],
                          rotation=30, ha='right', fontsize=10)
        ax.set_yticks(range(len(rho_df.index)))
        ax.set_yticklabels(rho_df.index, fontsize=9)

        # Annotate cells
        for i in range(len(rho_df.index)):
            for j in range(len(available_params)):
                val = rho_df.iloc[i, j]
                if not np.isnan(val):
                    color = 'white' if abs(val) > 0.5 else 'black'
                    ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                           color=color, fontsize=9, fontweight='bold')

        ax.set_title(target_name, fontsize=12, fontweight='bold', pad=10)

    # Single colorbar
    fig.subplots_adjust(right=0.88)
    cbar_ax = fig.add_axes([0.91, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(im, cax=cbar_ax)
    cbar.set_label('Spearman ρ', fontsize=11)

    fig.suptitle('Parameter effects are design-specific; treat as hypotheses (small n)',
                fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout(rect=[0, 0, 0.9, 0.98])
    save_figure(fig, output_dir, '04_param_outcome_heatmap')


# ════════════════════════════════════════════════════════════════════════════
# PLOT 5: Power vs Area (05_power_vs_area.png)
# ════════════════════════════════════════════════════════════════════════════
def plot_power_vs_area(df: pd.DataFrame, output_dir: Path):
    """Scatter log-log: Power vs Area, colored by platform, marker by outcome."""
    filtered = df[
        (df['data_completeness'] == 'complete') &
        (df['status'] == 'success') &
        (df['final_power_w'].notna()) &
        (df['final_area_um2'].notna())
    ].copy()

    if len(filtered) == 0:
        return

    fig, ax = plt.subplots(figsize=(8.5, 6))

    for platform in PLATFORM_ORDER:
        if platform not in filtered['platform'].values:
            continue
        plat_data = filtered[filtered['platform'] == platform]

        for outcome in ['Closed', 'Timing violated']:
            subset = plat_data[plat_data['outcome'] == outcome]
            if len(subset) == 0:
                continue

            marker = 'o' if outcome == 'Closed' else 'X'
            ax.scatter(subset['final_area_um2'], subset['final_power_w'] * 1000,
                      c=PLATFORM_COLORS[platform], marker=marker,
                      s=70, alpha=0.8, edgecolors='white', linewidth=0.5,
                      label=f'{PLATFORM_LABELS[platform]} - {outcome}' if subset.index[0] == plat_data[plat_data['outcome'] == outcome].index[0] else "")

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Final Area (μm²)', fontsize=12)
    ax.set_ylabel('Final Power (mW)', fontsize=12)
    ax.set_title('Power tracks area over 4 orders of magnitude; clusters are designs, not sweep settings',
                fontsize=12, fontweight='bold', pad=15)

    # Custom legend
    from matplotlib.lines import Line2D
    legend_elements = []
    for platform in PLATFORM_ORDER:
        if platform in filtered['platform'].values:
            legend_elements.append(Line2D([0], [0], marker='o', color='w',
                                          markerfacecolor=PLATFORM_COLORS[platform],
                                          markersize=10, label=PLATFORM_LABELS[platform]))
    legend_elements.append(Line2D([0], [0], marker='o', color='w',
                                  markerfacecolor='gray', markersize=10, label='Closed'))
    legend_elements.append(Line2D([0], [0], marker='X', color='w',
                                  markerfacecolor='gray', markersize=10, label='Timing violated'))

    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1),
              framealpha=0.9, fontsize=9)
    ax.grid(True, alpha=0.3)

    save_figure(fig, output_dir, '05_power_vs_area')


# ════════════════════════════════════════════════════════════════════════════
# PLOT 6: Parallel Coordinates Interactive (06_parallel_coords.html)
# ════════════════════════════════════════════════════════════════════════════
def plot_parallel_coords(df: pd.DataFrame, output_dir: Path):
    """Generate interactive Plotly parallel coordinates HTML."""
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError:
        print("  ⚠️  Plotly not installed, skipping interactive parallel coordinates")
        return

    # Filter: success runs from specific designs
    target_designs = [
        ('ibex', 'nangate45'),
        ('riscv32i-mock-sram', 'asap7'),
        ('uart-blocks', 'gf180'),
    ]

    filtered = df[
        (df['data_completeness'] == 'complete') &
        (df['status'] == 'success')
    ].copy()

    # Filter to target designs
    mask = False
    for design, platform in target_designs:
        mask |= ((df['design_name'] == design) & (df['platform'] == platform))
    filtered = df[mask].copy()

    if len(filtered) == 0:
        return

    # Create binary closed column
    filtered['closed'] = (filtered['outcome'] == 'Closed').astype(int)

    # Dimensions for parallel coordinates
    dimensions = [
        dict(label='Core Utilization (%)', values=filtered['core_utilization'],
             range=[filtered['core_utilization'].min(), filtered['core_utilization'].max()]),
        dict(label='Core Aspect Ratio', values=filtered['core_aspect_ratio'],
             range=[filtered['core_aspect_ratio'].min(), filtered['core_aspect_ratio'].max()]),
        dict(label='Core Margin (%)', values=filtered['core_margin'],
             range=[filtered['core_margin'].min(), filtered['core_margin'].max()]),
        dict(label='Placement Density', values=filtered['place_density'],
             range=[filtered['place_density'].min(), filtered['place_density'].max()]),
        dict(label='Final WNS (ns)', values=filtered['final_wns_ns'],
             range=[filtered['final_wns_ns'].min(), filtered['final_wns_ns'].max()]),
        dict(label='Setup Violations', values=filtered['final_setup_violations'],
             range=[filtered['final_setup_violations'].min(), filtered['final_setup_violations'].max()]),
    ]

    fig = go.Figure(data=go.Parcoords(
        line=dict(
            color=filtered['closed'],
            colorscale=[[0, '#FFC857'], [1, '#39D785']],  # amber → green
            showscale=True,
            colorbar=dict(title='Closed (1) / Not Closed (0)'),
        ),
        dimensions=dimensions
    ))

    fig.update_layout(
        title='Sweep parameters vs outcome (viable combos)',
        font=dict(size=11),
        margin=dict(l=80, r=80, t=60, b=40),
    )

    output_path = output_dir / '06_parallel_coords.html'
    output_dir.mkdir(parents=True, exist_ok=True)
    pio.write_html(fig, str(output_path))
    print(f"  ✅ Saved: {output_path}")


# ════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Specification-Compliant Visualization Suite")
    parser.add_argument('--data-path', type=Path,
                        default=Path("/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs.json"),
                        help="Path to runs data (JSON or CSV)")
    parser.add_argument('--output-dir', type=Path,
                        default=Path("/Users/mihirmithani/Downloads/OpenRoad GUI/plots_spec"),
                        help="Output directory for plots")
    args = parser.parse_args()

    print("=" * 70)
    print("SPECIFICATION-COMPLIANT VISUALIZATION SUITE")
    print("=" * 70)
    print(f"Data: {args.data_path}")
    print(f"Output: {args.output_dir}")
    print("=" * 70)

    # Load data
    df = load_data(args.data_path)
    print(f"Loaded {len(df)} runs across {df['platform'].nunique()} platforms")
    print(f"Platforms: {df['platform'].value_counts().to_dict()}")
    print(f"Completeness: {df['data_completeness'].value_counts().to_dict()}")
    print(f"Outcomes: {df['outcome'].value_counts().to_dict()}")

    # Generate all specification-compliant plots
    plots = [
        ("01 Closure Outcomes", plot_closure_outcomes),
        ("02 Stage WNS", plot_stage_wns),
        ("03 Parameter Effects", plot_parameter_effects),
        ("04 Param Outcome Heatmap", plot_param_outcome_heatmap),
        ("05 Power vs Area", plot_power_vs_area),
        ("06 Parallel Coords (HTML)", plot_parallel_coords),
    ]

    print("\nGenerating specification-compliant plots...")
    for name, func in plots:
        print(f"  📊 {name}...")
        try:
            func(df, args.output_dir)
        except Exception as e:
            print(f"    ❌ Failed: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ All specification-compliant plots saved to: {args.output_dir}")
    print("=" * 70)


if __name__ == '__main__':
    main()