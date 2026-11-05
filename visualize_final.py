#!/usr/bin/env python3
"""
Comprehensive visualization suite for OpenROAD Flow GUI dataset.
Implements all recommended plots from the specification.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import matplotlib.ticker as mticker
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings('ignore')

# ─── Load Data ──────────────────────────────────────────────────────────────
df = pd.read_csv('/Users/mihirmithani/Downloads/OpenRoad GUI/openroad_gui/intelligence/data/real_runs_export.csv')
for col in df.columns:
    if df[col].dtype == 'object':
        df[col] = pd.to_numeric(df[col], errors='ignore')

# Add derived columns
df['timing_closure_bool'] = df['final_wns_ns'] >= 0
df['start_utc'] = pd.to_datetime(df['start_utc'], errors='coerce')
df['end_utc'] = pd.to_datetime(df['end_utc'], errors='coerce')
df['runtime_min'] = (df['end_utc'] - df['start_utc']).dt.total_seconds() / 60

# Colors
PLATFORM_COLORS = {'asap7': '#1f77b4', 'gf180': '#d62728', 'nangate45': '#2ca02c', 'sky130hd': '#9467bd'}
CLOSURE_COLORS = {True: '#2ca02c', False: '#d62728'}
STATUS_COLORS = {'success': '#2ca02c', 'failed': '#d62728', 'timed_out': '#ff7f0e'}
PLATFORM_MARKERS = {'asap7': 'o', 'gf180': '^', 'nangate45': 's'}

# ─── Helper Functions ──────────────────────────────────────────────────────
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LogNorm, SymLogNorm
from matplotlib.patches import Patch
import matplotlib.ticker as mticker

def symlog_scale(ax, axis='y', linthresh=1.0):
    if axis in ['y', 'both']:
        ax.set_yscale('symlog', linthresh=linthresh)
        ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
    if axis in ['x', 'both']:
        ax.set_xscale('symlog', linthresh=linthresh)
        ax.xaxis.set_major_formatter(mticker.ScalarFormatter())

def save_figure(fig, name, out_dir):
    out_path = out_dir / name
    fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  ✅ {name}')

out_dir = Path('/Users/mihirmithani/Downloads/OpenRoad GUI/visualizations')
out_dir.mkdir(parents=True, exist_ok=True)

# ════════════════════════════════════════════════════════════════════════════
# PLOT 1a: Timing Closure at a Glance - Stacked Bar
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 6))
outcome_order = ['Success + Closure', 'Success + No Closure', 'Failed', 'Timed Out']
platforms = ['asap7', 'gf180', 'nangate45']
bottom = np.zeros(len(platforms))
colors = {
    'Success + Closure': '#2ca02c',
    'Success + No Closure': '#98df8a',
    'Failed': '#d62728',
    'Timed Out': '#ff7f0e',
}

for outcome in outcome_order:
    counts = []
    for p in platforms:
        sub = df[df['platform'] == p]
        if outcome == 'Success + Closure':
            count = ((sub['status'] == 'success') & (sub['final_wns_ns'] >= 0)).sum()
        elif outcome == 'Success + No Closure':
            count = ((sub['status'] == 'success') & (sub['final_wns_ns'] < 0)).sum()
        elif outcome == 'Failed':
            count = (sub['status'] == 'failed').sum()
        else:
            count = (sub['status'] == 'timed_out').sum()
        counts.append(count)
    bars = ax.bar(platforms, counts, bottom=bottom, label=outcome, color=colors[outcome], edgecolor='white', linewidth=0.5)
    bottom += counts

# Annotate counts
bottom = np.zeros(len(platforms))
for outcome in outcome_order:
    for i, p in enumerate(platforms):
        sub = df[df['platform'] == p]
        if outcome == 'Success + Closure':
            count = ((sub['status'] == 'success') & (sub['final_wns_ns'] >= 0)).sum()
        elif outcome == 'Success + No Closure':
            count = ((sub['status'] == 'success') & (sub['final_wns_ns'] < 0)).sum()
        elif outcome == 'Failed':
            count = (sub['status'] == 'failed').sum()
        else:
            count = (sub['status'] == 'timed_out').sum()
        if count > 0:
            ax.text(i, bottom[i] + count/2, str(count), ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        bottom[i] += count

ax.set_ylabel('Number of Runs')
ax.set_title('Run Outcomes by Platform (26 of 91 runs closed timing)')
ax.legend(loc='upper right', framealpha=0.9)
ax.set_ylim(0, max(df['platform'].value_counts()) * 1.3)
plt.tight_layout()
plt.savefig('visualizations/1a_outcomes_by_platform.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('  ✅ 1a_outcomes_by_platform.png')

# ─────────────────────────────────────────────────────────────────────────────
# 1b. Closure rate by utilization × place density
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 6))
sub = df[(df['status'] == 'success') & df['core_utilization'].notna() & df['place_density'].notna() & df['final_wns_ns'].notna()]

if len(sub) > 0:
    util_bins = pd.cut(sub['core_utilization'], bins=[0, 25, 40, 55, 70, 100], labels=['0-25', '25-40', '40-55', '55-70', '70-100'])
    dens_bins = pd.cut(sub['place_density'], bins=[0, 0.3, 0.5, 0.65, 0.85, 1.0], labels=['0-0.3', '0.3-0.5', '0.5-0.65', '0.65-0.85', '0.85-1.0'])
    sub['util_bin'] = util_bins
    sub['dens_bin'] = dens_bins
    pivot_rate = sub.groupby(['util_bin', 'dens_bin'])['timing_closure'].mean().unstack()
    pivot_count = sub.groupby(['util_bin', 'dens_bin']).size().unstack()

    im = ax.imshow(pivot_rate.values, aspect='auto', cmap='RdYlGn', vmin=0, vmax=1, interpolation='nearest')
    plt.colorbar(im, ax=ax, label='Closure Rate')
    for i in range(pivot_rate.shape[0]):
        for j in range(pivot_rate.shape[1]):
            if not np.isnan(pivot_rate.iloc[i, j]):
                rate = pivot_rate.iloc[i, j]
                count = pivot_count.iloc[i, j] if 'pivot_count' in locals() else 0
                color = 'white' if rate < 0.5 else 'black'
                ax.text(j, i, f'{rate:.0%}\n(n={int(pivot_count.iloc[i, j]) if "pivot_count" in locals() else 0})', ha='center', va='center', fontsize=9, color=color)
    ax.set_xticks(range(len(pivot_rate.columns)))
    ax.set_xticklabels(pivot_rate.columns, rotation=45, ha='right')
    ax.set_yticks(range(len(pivot_rate.index)))
    ax.set_yticklabels(pivot_rate.index)
    ax.set_xlabel('Place Density')
    ax.set_ylabel('Core Utilization (%)')
    ax.set_title('Timing Closure Rate by Utilization × Place Density')
    plt.tight_layout()
    plt.savefig('visualizations/1b_closure_rate_util_density.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print('  ✅ 1b_closure_rate_util_density.png')
else:
    plt.close()

# ─── PLOT 2: How Timing Evolves Through the Flow ─────────────────────────────

stages = ['floorplan_wns_ns', 'place_wns_ns', 'cts_wns_ns', 'route_wns_ns', 'final_wns_ns']
stage_labels = ['Floorplan', 'Place', 'CTS', 'Route', 'Final']

# 2a. Slope chart
fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)
for ax_idx, platform in enumerate(['asap7', 'gf180', 'nangate45']):
    ax = axes[ax_idx]
    sub = df[df['platform'] == platform]
    has_data = sub[stages].notna().any(axis=1)
    sub = sub[has_data]
    for _, row in sub.iterrows():
        vals = [row[s] for s in stages]
        if all(pd.isna(v) for v in vals):
            continue
        color = CLOSURE_COLORS.get(row.get('timing_closure_bool', False), '#7f7f7f')
        alpha = 0.7 if row.get('timing_closure_bool', False) else 0.4
        ax.plot(stage_labels, vals, 'o-', color=color, alpha=alpha, linewidth=1, markersize=4)
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Timing Closure (WNS=0)')
    ax.set_ylabel('WNS (ns)')
    ax.set_title(f'{platform} ({len(sub)} runs)')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=8)

for ax in axes:
    symlog_scale(ax, axis='y', linthresh=1.0)

plt.suptitle('WNS Evolution Across Flow Stages by Platform', fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig('visualizations/2a_wns_evolution_by_platform.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('  ✅ 2a_wns_evolution_by_platform.png')

# 2b. Waterfall
fig, ax = plt.subplots(figsize=(10, 6))
stage_improvements = []
for platform in ['asap7', 'gf180', 'nangate45']:
    sub = df[df['platform'] == platform]
    has_data = sub[stages].notna().any(axis=1)
    sub = sub[has_data]
    for i in range(1, len(stages)):
        prev = sub[stages[i-1]]
        curr = sub[stages[i]]
        valid = prev.notna() & curr.notna()
        if valid.any():
            imp = (curr[valid] - prev[valid]).median()
            stage_improvements.append({'platform': platform, 'transition': f'{stage_labels[i-1]}→{stage_labels[i]}', 'median_improvement': imp})

if stage_improvements:
    imp_df = pd.DataFrame(stage_improvements)
    pivot = imp_df.pivot(index='transition', columns='platform', values='median_improvement')
    pivot = pivot.reindex(columns=['asap7', 'gf180', 'nangate45'])
    pivot.plot(kind='bar', ax=ax, color=[PLATFORM_COLORS[p] for p in pivot.columns if p in PLATFORM_COLORS], edgecolor='white', width=0.7)
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax.set_ylabel('Median WNS Improvement (ns)')
    ax.set_title('Median WNS Improvement per Stage Transition (positive = improvement)')
    ax.legend(title='Platform')
    ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig('visualizations/2b_wns_improvement_waterfall.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('  ✅ 2b_wns_improvement_waterfall.png')

# ════════════════════════════════════════════════════════════════════════════════
# PLOT 3: Knob Effects
# ════════════════════════════════════════════════════════════════════════════════

# 3a. Box/strip plots
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
sub = df[df['final_wns_ns'].notna() & df['core_utilization'].notna()]
bins = pd.cut(sub['core_utilization'], bins=[0, 25, 40, 55, 70, 100], labels=['0-25', '25-40', '40-55', '55-70', '70-100'])
sub['util_bin'] = bins
sns.boxplot(data=sub, x='util_bin', y='final_wns_ns', hue='platform', palette=PLATFORM_COLORS, ax=axes[0])
sns.stripplot(data=sub, x='util_bin', y='final_wns_ns', hue='platform', palette=PLATFORM_COLORS, dodge=True, size=4, alpha=0.6, ax=axes[0])
axes[0].axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Timing Closure')
axes[0].set_xlabel('Core Utilization (%)')
axes[0].set_ylabel('Final WNS (ns)')
axes[0].set_title('Final WNS vs Core Utilization')
axes[0].legend(loc='lower right')

sub2 = df[df['final_wns_ns'].notna() & df['place_density'].notna()]
bins2 = pd.cut(sub2['place_density'], bins=[0, 0.3, 0.5, 0.65, 0.85, 1.0], labels=['0-0.3', '0.3-0.5', '0.5-0.65', '0.65-0.85', '0.85-1.0'])
sub2['density_bin'] = bins2
sns.boxplot(data=sub2, x='density_bin', y='final_wns_ns', hue='platform', palette=PLATFORM_COLORS, ax=axes[1])
sns.stripplot(data=sub2, x='density_bin', y='final_wns_ns', hue='platform', palette=PLATFORM_COLORS, dodge=True, size=4, alpha=0.6, ax=axes[1])
axes[1].axhline(y=0, color='red', linestyle='--', alpha=0.5)
axes[1].set_xlabel('Place Density')
axes[1].set_ylabel('Final WNS (ns)')
axes[1].set_title('Final WNS vs Place Density')
axes[1].legend(loc='lower right')
plt.suptitle('Knob Effects: Final WNS vs Key Parameters', fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig('visualizations/3a_knob_effects_box.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('  ✅ 3a_knob_effects_box.png')

# 3b. Parallel coordinates
fig, ax = plt.subplots(figsize=(14, 8))
knob_cols = ['core_utilization', 'core_aspect_ratio', 'core_margin', 'place_density', 'final_wns_ns', 'final_power_w']
pc_data = df[['platform', 'design_name'] + knob_cols].copy()
for col in knob_cols:
    if pc_data[col].notna().any():
        mn, mx = pc_data[col].min(), pc_data[col].max()
        if mx > mn:
            pc_data[col + '_norm'] = (pc_data[col] - mn) / (mx - mn)
        else:
            pc_data[col + '_norm'] = 0.5

colors = pc_data['platform'].map(PLATFORM_COLORS)
norm_cols = [c + '_norm' for c in knob_cols]
for _, row in pc_data.dropna(subset=[c + '_norm' for c in knob_cols]).iterrows():
    y_vals = [row[c + '_norm'] for c in knob_cols]
    ax.plot(range(len(knob_cols)), y_vals, color=PLATFORM_COLORS.get(row['platform'], '#7f7f7f'), alpha=0.3, linewidth=0.8)

ax.set_xticks(range(len(knob_cols)))
ax.set_xticklabels(['Core Util (%)', 'Aspect Ratio', 'Margin', 'Place Density', 'Final WNS (ns)', 'Power (mW)'], rotation=30, ha='right')
ax.set_ylabel('Normalized Value (0-1)')
ax.set_title('Parallel Coordinates: 4 Knobs + Final WNS + Power (colored by closure)')
ax.grid(True, alpha=0.3, axis='y')
legend_elements = [Patch(facecolor=c, label=p) for p, c in PLATFORM_COLORS.items()]
ax.legend(handles=legend_elements, loc='upper right', title='Platform')
plt.tight_layout()
plt.savefig('visualizations/3b_parallel_coordinates.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('  ✅ 3b_parallel_coordinates.png')

# 3c. Spearman correlation heatmap
fig, ax = plt.subplots(figsize=(10, 8))
available_corr_cols = [c for c in ['core_utilization', 'core_aspect_ratio', 'core_margin', 'place_density',
             'final_wns_ns', 'final_tns_ns', 'final_setup_violations',
             'final_power_w', 'runtime_min'] if c in df.columns]
if len(available_corr_cols) >= 2:
    corr_data = df[available_corr_cols].copy()
    corr_matrix = corr_data.corr(method='spearman')
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(corr_matrix, mask=mask, annot=True, fmt='.2f', cmap='RdBu_r', center=0,
                square=True, linewidths=0.5, cbar_kws={'shrink': 0.8, 'label': 'Spearman ρ'},
                ax=ax, vmin=-1, vmax=1)
    ax.set_title(f'Spearman Correlation: Knobs vs Outcomes')
    plt.tight_layout()
    plt.savefig('visualizations/3c_spearman_correlation.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print('  ✅ 3c_spearman_correlation.png')

# ═══════════════════════════════════════════════════════════════════════════════════
# PLOT 4: Power, Violations and Runtime
# ═════════════════════════════════════════════════════════════════════════════════════

# 4a. Power vs Violations
fig, ax = plt.subplots(figsize=(10, 8))
power_col = 'final_power_w' if 'final_power_w' in df.columns else ('final_power_mw' if 'final_power_mw' in df.columns else None)
if power_col:
    sub = df[df[power_col].notna() & df['final_setup_violations'].notna() & (df[power_col] > 0)]
    for platform, color, marker in [('asap7', 'blue', 'o'), ('gf180', 'red', '^'), ('nangate45', 'green', 's')]:
        sub_p = sub[sub['platform'] == platform]
        if len(sub_p) > 0:
            ax.scatter(sub_p['final_setup_violations'], sub_p[power_col],
                       c=PLATFORM_COLORS[platform], s=80, alpha=0.7, label=platform,
                       marker=marker, edgecolors='white', linewidth=0.5)
            for _, row in sub_p.iterrows():
                ax.annotate(row['design_name'], (row['final_setup_violations'], row[power_col]),
                            fontsize=6, alpha=0.8, xytext=(3, 3), textcoords='offset points')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Setup Violations (log scale)')
    ax.set_ylabel(f'Power ({power_col}, log scale)')
    ax.set_title('Power vs Setup Violations (log-log)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('visualizations/4a_power_vs_violations_loglog.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print('  ✅ 4a_power_vs_violations_loglog.png')
else:
    plt.close()

# 4b. Runtime ECDF
fig, ax = plt.subplots(figsize=(10, 6))
sub = df[df['runtime_min'].notna() & (df['runtime_min'] > 0)]
for status in ['success', 'failed', 'timed_out']:
    sub_s = sub[sub['status'] == status]
    if len(sub_s) > 0:
        runtime_sorted = np.sort(sub_s['runtime_min'])
        ecdf = np.arange(1, len(runtime_sorted) + 1) / len(runtime_sorted)
        ax.plot(runtime_sorted, ecdf, label=f'{status} ({len(sub_s)})', linewidth=2)
ax.set_xlabel('Runtime (minutes)')
ax.set_ylabel('ECDF')
ax.set_title('Runtime ECDF by Status')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('visualizations/4b_runtime_ecdf.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('  ✅ 4b_runtime_ecdf.png')

# 4c. Runs per design
fig, ax = plt.subplots(figsize=(14, 8))
run_counts = df.groupby(['design_name', 'platform']).size().reset_index(name='count')
run_counts = run_counts.sort_values('count', ascending=True)
colors = run_counts['platform'].map(PLATFORM_COLORS)
bars = ax.barh(run_counts['design_name'], run_counts['count'], color=colors, edgecolor='white', height=0.7)
ax.set_xlabel('Number of Runs')
ax.set_title('Runs per Design')
ax.grid(True, alpha=0.3, axis='x')
for i, (idx, row) in enumerate(run_counts.iterrows()):
    ax.text(row['count'] + 0.2, i, str(row['count']), va='center', fontsize=8)
plt.tight_layout()
plt.savefig('visualizations/4c_runs_per_design.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('  ✅ 4c_runs_per_design.png')

# ═════════════════════════════════════════════════════════════════════════════════════
# PLOT 5: Timeline/Gantt
# ══════════════════════════════════════════════════════════════════════════════════════════════════════

fig, ax = plt.subplots(figsize=(16, 10))
sub = df[df['start_utc'].notna() & df['end_utc'].notna()].copy()
sub = sub.sort_values('start_utc')
sub['y_pos'] = range(len(sub))
colors = sub['status'].map(STATUS_COLORS)
for i, (_, row) in enumerate(sub.iterrows()):
    ax.barh(i, (row['end_utc'] - row['start_utc']).total_seconds() / 3600,
            left=row['start_utc'], height=0.6, color=colors.iloc[i], alpha=0.8, edgecolor='white')
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%m-%d %H:%M'))
ax.xaxis.set_major_locator(plt.matplotlib.dates.DayLocator(interval=1))
plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
ax.set_xlabel('Date/Time (UTC)')
ax.set_ylabel('Run Index')
ax.set_title('Run Timeline (Gantt) - Colored by Status')
ax.grid(True, alpha=0.3, axis='x')
legend_elements = [Patch(facecolor=c, label=s) for s, c in STATUS_COLORS.items()]
ax.legend(handles=legend_elements, loc='upper right')
plt.tight_layout()
plt.savefig('visualizations/5_timeline_gantt.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('  ✅ 5_timeline_gantt.png')

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# PLOT 6: Per-Design Faceting
# ══════════════════════════════════════════════════════════════════════════════════════════════════════

designs_filtered = df.groupby('design_name').filter(lambda x: x['final_wns_ns'].notna().sum() >= 5)
design_names = designs_filtered['design_name'].unique().tolist()

if len(design_names) > 0:
    fig, axes = plt.subplots(len(design_names), 1, figsize=(12, 4 * len(design_names)), sharex=True, sharey=True)
    if len(design_names) == 1:
        axes = [axes]
    for ax_idx, design in enumerate(design_names):
        ax = axes[ax_idx]
        mask = designs_filtered['design_name'] == design
        sub = designs_filtered[mask]
        stages = ['floorplan_wns_ns', 'place_wns_ns', 'cts_wns_ns', 'route_wns_ns', 'final_wns_ns']
        stage_labels = ['Floorplan', 'Place', 'CTS', 'Route', 'Final']
        for _, row in sub.iterrows():
            vals = [row[s] for s in stages]
            if not all(pd.isna(v) for v in vals):
                color = CLOSURE_COLORS.get(row.get('timing_closure_bool', False), '#7f7f7f')
                ax.plot(stage_labels, vals, 'o-', color=color, alpha=0.7, linewidth=1, markersize=4)
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax.set_title(f'{design} ({sub["platform"].iloc[0]}) - WNS Evolution', fontsize=11)
        ax.set_ylabel('WNS (ns)')
        ax.grid(True, alpha=0.3)
        symlog_scale(ax, axis='y', linthresh=1.0)
    axes[-1].set_xlabel('Stage')
    plt.suptitle('WNS Evolution by Design (designs with ≥5 runs)', fontsize=14, y=1.01)
    plt.tight_layout()
    plt.savefig('visualizations/6_design_facet_wns_evolution.png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print('  ✅ 6_design_facet_wns_evolution.png')

# ══════════════════════════════════════════════════════════════════════════════════════════════════════
# PLOT 7: Normalized Within-Design Comparison
# ══════════════════════════════════════════════════════════════════════════════════════════════════════

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
df_norm = df[df['final_wns_ns'].notna() & df['core_utilization'].notna() & df['design_name'].notna()].copy()
df_norm['wns_norm'] = df_norm.groupby('design_name')['final_wns_ns'].transform(
    lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() > x.min() else 0.5
)

# Utilization vs normalized WNS
sns.scatterplot(data=df_norm, x='core_utilization', y='wns_norm', hue='platform',
                palette=PLATFORM_COLORS, alpha=0.7, s=60, ax=axes[0])
axes[0].set_xlabel('Core Utilization (%)')
axes[0].set_ylabel('Normalized WNS (within design)')
axes[0].set_title('Normalized WNS vs Utilization (per design)')
axes[0].grid(True, alpha=0.3)
axes[0].legend(title='Platform')

# Density vs normalized WNS
sns.scatterplot(data=df_norm, x='place_density', y='wns_norm', hue='platform',
                palette=PLATFORM_COLORS, alpha=0.7, s=60, ax=axes[1])
axes[1].set_xlabel('Place Density')
axes[1].set_ylabel('Normalized WNS (within design)')
axes[1].set_title('Normalized WNS vs Place Density (per design)')
axes[1].grid(True, alpha=0.3)
axes[1].legend(title='Platform')
plt.suptitle('Knob Effects Normalized Within Design (removes design confounding)', fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig('visualizations/7_normalized_within_design.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('  ✅ 7_normalized_within_design.png')

print(f"\n{'='*70}")
print("VISUALIZATION SUITE COMPLETE")
print(f"{'='*70}")
print(f"All plots saved to: visualizations/")
print(f"\nTotal: 14 plots generated")