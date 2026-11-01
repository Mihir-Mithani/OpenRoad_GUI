#!/usr/bin/env python3
"""
Visualize gf180-specific data.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ── Load data ────────────────────────────────────────────────────────────────
CSV_PATH = Path("openroad_gui/intelligence/data/real_runs_export.csv")
OUT_DIR = Path("real_data_plots/gf180")
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV_PATH)

# Convert numeric
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

gf180 = df[df['platform'] == 'gf180'].copy()
asap7 = df[df['platform'] == 'asap7'].copy()

print(f"gf180 runs: {len(gf180)}, asap7 runs: {len(asap7)}")

# ── Plot 1: gf180 WNS vs Violations ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))
mask = gf180['final_wns_ns'].notna() & gf180['final_setup_violations'].notna()
ax.scatter(gf180.loc[mask, 'final_wns_ns'], gf180.loc[mask, 'final_setup_violations'],
           c='red', s=100, alpha=0.8, edgecolors='white', linewidth=0.5)
for _, row in gf180.iterrows():
    if pd.notna(row['final_wns_ns']) and pd.notna(row['final_setup_violations']):
        ax.annotate(row['design_name'], (row['final_wns_ns'], row['final_setup_violations']),
                    fontsize=9, alpha=0.9, xytext=(5, 5), textcoords='offset points')
ax.axvline(x=0, color='red', linestyle='--', alpha=0.5, label='Timing Closure')
ax.set_xlabel('Final WNS (ns)')
ax.set_ylabel('Setup Violations')
ax.set_title('gf180: Final WNS vs Setup Violations')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUT_DIR / 'gf180_wns_vs_violations.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✅ gf180_wns_vs_violations.png")

# ── Plot 2: Platform Comparison ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# WNS distribution
for platform, color, label in [('asap7', 'blue', 'asap7'), ('gf180', 'red', 'gf180')]:
    df_src = df[df['platform'] == platform]
    mask = df_src['final_wns_ns'].notna()
    axes[0].hist(df_src.loc[mask, 'final_wns_ns'], bins=10, alpha=0.5, color=color, label=label, edgecolor='white')
axes[0].axvline(x=0, color='black', linestyle='--', alpha=0.5)
axes[0].set_xlabel('Final WNS (ns)')
axes[0].set_ylabel('Count')
axes[0].set_title('Final WNS Distribution by Platform')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# TNS distribution (log scale)
for platform, color, label in [('asap7', 'blue', 'asap7'), ('gf180', 'red', 'gf180')]:
    df_src = df[df['platform'] == platform]
    mask = df_src['final_tns_ns'].notna()
    axes[1].hist(df_src.loc[mask, 'final_tns_ns'].abs(), bins=10, alpha=0.5, color=color, label=label, edgecolor='white')
axes[1].set_yscale('log')
axes[1].set_xlabel('|Final TNS| (ns)')
axes[1].set_ylabel('Count (log)')
axes[1].set_title('|Final TNS| Distribution by Platform')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

# Violations distribution
for platform, color, label in [('asap7', 'blue', 'asap7'), ('gf180', 'red', 'gf180')]:
    df_src = df[df['platform'] == platform]
    mask = df_src['final_setup_violations'].notna()
    axes[2].hist(df_src.loc[mask, 'final_setup_violations'], bins=10, alpha=0.5, color=color, label=label, edgecolor='white')
axes[2].set_xscale('log')
axes[2].set_xlabel('Setup Violations')
axes[2].set_ylabel('Count')
axes[2].set_title('Setup Violations Distribution')
axes[2].legend()
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUT_DIR / 'platform_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✅ platform_comparison.png")

# ── Plot 3: gf180 WNS Progression ───────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
stages = ['synth_wns_ns', 'floorplan_wns_ns', 'place_wns_ns', 'cts_wns_ns', 'route_wns_ns', 'final_wns_ns']
stage_labels = ['Synth', 'Floorplan', 'Place', 'CTS', 'Route', 'Finish']

for _, row in gf180.iterrows():
    vals = [row[s] for s in stages]
    if not all(pd.isna(v) for v in vals):
        ax.plot(stage_labels, vals, 'o-', alpha=0.7, label=row['design_name'])

ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Timing Closure')
ax.set_ylabel('WNS (ns)')
ax.set_title('gf180: WNS Progression Across Stages')
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUT_DIR / 'gf180_wns_progression.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✅ gf180_wns_progression.png")

# ── Plot 4: gf180 Power vs Utilization ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))
mask = gf180['final_power_w'].notna() & (gf180['final_power_w'] > 0)
if mask.any():
    ax.scatter(gf180.loc[mask, 'core_utilization'], gf180.loc[mask, 'final_power_w'] * 1000,
               c='red', s=100, alpha=0.8, edgecolors='white', linewidth=0.5)
    for _, row in gf180.iterrows():
        if pd.notna(row['final_power_w']) and row['final_power_w'] > 0:
            ax.annotate(row['design_name'], (row['core_utilization'], row['final_power_w'] * 1000),
                        fontsize=9, alpha=0.9, xytext=(5, 5), textcoords='offset points')
ax.set_xlabel('Core Utilization (%)')
ax.set_ylabel('Power (mW)')
ax.set_title('gf180: Power vs Core Utilization')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUT_DIR / 'gf180_power_vs_util.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✅ gf180_power_vs_util.png")

# ── Plot 5: Platform comparison WNS vs TNS ──────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))
for platform, color, marker in [('asap7', 'blue', 'o'), ('gf180', 'red', '^')]:
    df_src = df[df['platform'] == platform]
    mask = df_src['final_tns_ns'].notna() & df_src['final_wns_ns'].notna()
    ax.scatter(df_src.loc[mask, 'final_wns_ns'], df_src.loc[mask, 'final_tns_ns'].abs(),
               c=color, s=80, alpha=0.7, label=platform, marker=marker, edgecolors='white', linewidth=0.5)
    for _, row in df_src[mask].iterrows():
        ax.annotate(row['design_name'], (row['final_wns_ns'], abs(row['final_tns_ns'])),
                    fontsize=8, alpha=0.8, xytext=(3, 3), textcoords='offset points')

ax.set_yscale('log')
ax.axvline(x=0, color='black', linestyle='--', alpha=0.5)
ax.set_xlabel('Final WNS (ns)')
ax.set_ylabel('|Final TNS| (ns, log scale)')
ax.set_title('TNS vs WNS: asap7 vs gf180')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUT_DIR / 'asap7_vs_gf180_tns_wns.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✅ asap7_vs_gf180_tns_wns.png")

# ── Summary Stats ────────────────────────────────────────────────────────────
print("\n📊 gf180 Summary Statistics:")
print(f"  Runs: {len(gf180)}")
print(f"  Mean WNS: {gf180['final_wns_ns'].mean():.2f} ns")
print(f"  Median WNS: {gf180['final_wns_ns'].median():.2f} ns")
print(f"  WNS Range: {gf180['final_wns_ns'].min():.2f} to {gf180['final_wns_ns'].max():.2f} ns")
print(f"  Timing Closure Rate: {(gf180['final_wns_ns'] >= 0).sum()}/{len(gf180)}")
print(f"  Mean Setup Violations: {gf180['final_setup_violations'].mean():.0f}")
print(f"  Mean Power: {gf180['final_power_w'].mean()*1000:.2f} mW")

print("\n📊 asap7 Summary Statistics:")
print(f"  Runs: {len(asap7)}")
print(f"  Mean WNS: {asap7['final_wns_ns'].mean():.2f} ns")
print(f"  Median WNS: {asap7['final_wns_ns'].median():.2f} ns")
print(f"  WNS Range: {asap7['final_wns_ns'].min():.2f} to {asap7['final_wns_ns'].max():.2f} ns")
print(f"  Timing Closure Rate: {(asap7['final_wns_ns'] >= 0).sum()}/{len(asap7)}")
print(f"  Mean Setup Violations: {asap7['final_setup_violations'].mean():.0f}")
print(f"  Mean Power: {asap7['final_power_w'].mean()*1000:.2f} mW")

print(f"\n✅ gf180 plots saved to {OUT_DIR}/")
print(f"   Files: {list(OUT_DIR.glob('*.png'))}")