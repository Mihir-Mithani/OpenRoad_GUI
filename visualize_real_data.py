#!/usr/bin/env python3
"""
Quick visualization of real ORFS run data (AWS + local).
Run: python3 visualize_real_data.py
Outputs: real_data_plots/
"""

import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ── Load data ────────────────────────────────────────────────────────────────
CSV_PATH = Path("openroad_gui/intelligence/data/real_runs_export.csv")
OUT_DIR = Path("real_data_plots")
OUT_DIR.mkdir(exist_ok=True)

df = pd.read_csv(CSV_PATH)

# Convert numeric columns
numeric_cols = [
    'core_utilization', 'core_aspect_ratio', 'core_margin', 'place_density',
    'synth_wns_ns', 'synth_tns_ns', 'floorplan_wns_ns', 'floorplan_tns_ns',
    'place_wns_ns', 'place_tns_ns', 'cts_wns_ns', 'cts_tns_ns',
    'route_wns_ns', 'route_tns_ns', 'final_wns_ns', 'final_tns_ns',
    'final_setup_violations', 'final_hold_violations',
    'final_power_w', 'final_power_mw'
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Separate sources
aws = df[df['source'] == 'aws'].copy()
local = df[df['source'] == 'local'].copy()

print(f"Total runs: {len(df)} (AWS: {len(aws)}, Local: {len(local)})")

# ── Plot 1: WNS Progression by Stage ────────────────────────────────────────
def plot_wns_progression():
    fig, ax = plt.subplots(figsize=(10, 6))
    stages = ['synth_wns_ns', 'floorplan_wns_ns', 'place_wns_ns', 'cts_wns_ns', 'route_wns_ns', 'final_wns_ns']
    stage_labels = ['Synth', 'Floorplan', 'Place', 'CTS', 'Route', 'Finish']

    for _, row in aws.iterrows():
        vals = [row[s] for s in stages]
        if not all(pd.isna(v) for v in vals):
            ax.plot(stage_labels, vals, 'o-', alpha=0.6, label=row['design_name'])

    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Timing Closure (WNS=0)')
    ax.set_ylabel('WNS (ns)')
    ax.set_title('WNS Progression Across Stages (AWS Runs)')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'wns_progression.png', dpi=150, bbox_inches='tight')
    plt.close()

# ── Plot 2: Final WNS vs Setup Violations ───────────────────────────────────
def plot_wns_vs_violations():
    fig, ax = plt.subplots(figsize=(8, 6))

    # AWS runs
    mask = aws['final_wns_ns'].notna() & aws['final_setup_violations'].notna()
    ax.scatter(aws.loc[mask, 'final_wns_ns'], aws.loc[mask, 'final_setup_violations'],
               c='blue', s=80, alpha=0.7, label='AWS', edgecolors='white', linewidth=0.5)
    for _, row in aws.iterrows():
        if pd.notna(row['final_wns_ns']) and pd.notna(row['final_setup_violations']):
            ax.annotate(row['design_name'], (row['final_wns_ns'], row['final_setup_violations']),
                        fontsize=7, alpha=0.8, xytext=(3, 3), textcoords='offset points')

    # Local runs
    mask = local['final_wns_ns'].notna() & local['final_setup_violations'].notna()
    ax.scatter(local.loc[mask, 'final_wns_ns'], local.loc[mask, 'final_setup_violations'],
               c='orange', s=80, alpha=0.7, label='Local', marker='^', edgecolors='white', linewidth=0.5)
    for _, row in local.iterrows():
        if pd.notna(row['final_wns_ns']) and pd.notna(row['final_setup_violations']):
            ax.annotate(row['design_name'], (row['final_wns_ns'], row['final_setup_violations']),
                        fontsize=7, alpha=0.8, xytext=(3, 3), textcoords='offset points')

    ax.axvline(x=0, color='red', linestyle='--', alpha=0.5, label='Timing Closure')
    ax.set_xlabel('Final WNS (ns)')
    ax.set_ylabel('Setup Violations')
    ax.set_title('Final WNS vs Setup Violations')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'wns_vs_violations.png', dpi=150, bbox_inches='tight')
    plt.close()

# ── Plot 3: TNS vs WNS (log scale for TNS) ──────────────────────────────────
def plot_tns_vs_wns():
    fig, ax = plt.subplots(figsize=(8, 6))

    mask = aws['final_tns_ns'].notna() & aws['final_wns_ns'].notna()
    ax.scatter(aws.loc[mask, 'final_wns_ns'], aws.loc[mask, 'final_tns_ns'].abs(),
               c='blue', s=80, alpha=0.7, label='AWS')
    for _, row in aws.iterrows():
        if pd.notna(row['final_wns_ns']) and pd.notna(row['final_tns_ns']):
            ax.annotate(row['design_name'], (row['final_wns_ns'], abs(row['final_tns_ns'])),
                        fontsize=7, alpha=0.8, xytext=(3, 3), textcoords='offset points')

    ax.set_yscale('log')
    ax.axvline(x=0, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Final WNS (ns)')
    ax.set_ylabel('|Final TNS| (ns, log scale)')
    ax.set_title('TNS vs WNS (AWS Runs)')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'tns_vs_wns.png', dpi=150, bbox_inches='tight')
    plt.close()

# ── Plot 4: Power vs Area (if available) ────────────────────────────────────
def plot_power_vs_area():
    fig, ax = plt.subplots(figsize=(8, 6))

    # Only AWS has power data
    mask = aws['final_power_w'].notna() & (aws['final_power_w'] > 0)
    if mask.any():
        ax.scatter(aws.loc[mask, 'core_utilization'], aws.loc[mask, 'final_power_w'] * 1000,
                   c='green', s=100, alpha=0.7, label='AWS')
        for _, row in aws.iterrows():
            if pd.notna(row['final_power_w']) and row['final_power_w'] > 0:
                ax.annotate(row['design_name'], (row['core_utilization'], row['final_power_w'] * 1000),
                            fontsize=7, alpha=0.8, xytext=(3, 3), textcoords='offset points')

    ax.set_xlabel('Core Utilization (%)')
    ax.set_ylabel('Power (mW)')
    ax.set_title('Power vs Core Utilization (AWS Runs)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'power_vs_util.png', dpi=150, bbox_inches='tight')
    plt.close()

# ── Plot 5: Setup Violations by Design ──────────────────────────────────────
def plot_violations_by_design():
    fig, ax = plt.subplots(figsize=(10, 5))

    # Combine AWS and local
    all_data = pd.concat([aws, local])
    mask = all_data['final_setup_violations'].notna()
    plot_df = all_data[mask].sort_values('final_setup_violations')

    colors = ['blue' if s == 'aws' else 'orange' for s in plot_df['source']]
    bars = ax.barh(plot_df['design_name'], plot_df['final_setup_violations'], color=colors, alpha=0.7)

    ax.set_xlabel('Setup Violations (log scale)')
    ax.set_xscale('log')
    ax.set_title('Setup Violations by Design (Log Scale)')
    ax.grid(True, alpha=0.3, axis='x')

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='blue', alpha=0.7, label='AWS'),
                       Patch(facecolor='orange', alpha=0.7, label='Local')]
    ax.legend(handles=legend_elements)

    plt.tight_layout()
    plt.savefig(OUT_DIR / 'violations_by_design.png', dpi=150, bbox_inches='tight')
    plt.close()

# ── Plot 6: Core Utilization vs WNS ─────────────────────────────────────────
def plot_util_vs_wns():
    fig, ax = plt.subplots(figsize=(8, 6))

    for source, label, color in [('aws', 'AWS', 'blue'), ('local', 'Local', 'orange')]:
        df_src = aws if source == 'aws' else local
        mask = df_src['core_utilization'].notna() & df_src['final_wns_ns'].notna()
        ax.scatter(df_src.loc[mask, 'core_utilization'], df_src.loc[mask, 'final_wns_ns'],
                   c=color, s=80, alpha=0.7, label=label)
        for _, row in df_src[mask].iterrows():
            ax.annotate(row['design_name'], (row['core_utilization'], row['final_wns_ns']),
                        fontsize=7, alpha=0.8, xytext=(3, 3), textcoords='offset points')

    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Timing Closure')
    ax.set_xlabel('Core Utilization (%)')
    ax.set_ylabel('Final WNS (ns)')
    ax.set_title('Core Utilization vs Final WNS')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'util_vs_wns.png', dpi=150, bbox_inches='tight')
    plt.close()

# ── Main ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("📊 Generating visualizations...")
    plot_wns_progression()
    print("  ✅ wns_progression.png")
    plot_wns_vs_violations()
    print("  ✅ wns_vs_violations.png")
    plot_tns_vs_wns()
    print("  ✅ tns_vs_wns.png")
    plot_power_vs_area()
    print("  ✅ power_vs_util.png")
    plot_violations_by_design()
    print("  ✅ violations_by_design.png")
    plot_util_vs_wns()
    print("  ✅ util_vs_wns.png")
    print(f"\n✅ All plots saved to {OUT_DIR}/")
    print(f"   Files: {list(OUT_DIR.glob('*.png'))}")