#!/usr/bin/env python3
"""
Compare real vs synthetic EDA-flow runs.
Produces a multi-page PDF + PNGs for visual inspection.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
import numpy as np
import pandas as pd
import seaborn as sns

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
})

PALETTE = {"real": "#1f77b4", "synthetic": "#ff7f0e"}
PLATFORMS = ["sky130hd", "asap7", "nangate45", "gf180"]
PAIRS = [
    ("num_instances", "final_area_um2"),
    ("final_area_um2", "final_power_mw"),
    ("core_utilization", "final_wns_ns"),
    ("final_wns_ns", "final_tns_ns"),
]

def load_df(path, tag):
    df = pd.read_csv(Path(path))
    df = df[df["status"] == "success"].copy()
    df["source"] = tag

    # Unify power column name
    if "final_power_w" in df.columns and "final_power_mw" not in df.columns:
        df["final_power_mw"] = df["final_power_w"] * 1000

    # Add missing columns with NaN for real data
    if "num_instances" not in df.columns:
        df["num_instances"] = np.nan
    if "final_drc_violations" not in df.columns:
        df["final_drc_violations"] = np.nan

    # Ensure all expected columns exist
    for col in ["status", "final_wns_ns", "final_tns_ns", "final_area_um2",
                "final_power_mw", "final_power_w", "core_utilization",
                "platform", "drc_clean", "lvs_clean", "timing_closure",
                "num_instances", "final_drc_violations"]:
        if col not in df.columns:
            df[col] = np.nan

    return df.copy()


def violin_panel(ax, real, syn, y, title):
    real_data = real[y].dropna()
    syn_data = syn[y].dropna()
    if len(real_data) == 0 or len(syn_data) == 0:
        ax.text(0.5, 0.5, f"No data for {y}", ha='center', va='center', transform=ax.transAxes)
        return

    parts = ax.violinplot([real[y].dropna(), syn[y].dropna()],
                          positions=[0, 1], widths=0.6, showmeans=True,
                          showmedians=True, showextrema=False)
    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(["#1f77b4", "#ff7f0e"][i])
        pc.set_alpha(0.6)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Real", "Synth"])
    ax.set_ylabel(y)
    ax.set_title(title)


def scatter_panel(ax, real, syn, x, y, title):
    real_clean = real[[x, y]].dropna()
    syn_clean = syn[[x, y]].dropna()

    if len(real_clean) > 0:
        ax.scatter(real_clean[x], real_clean[y], c="#1f77b4", s=6, alpha=0.35, label="Real")
    if len(syn_clean) > 0:
        ax.scatter(syn_clean[x], syn_clean[y], c="#ff7f0e", s=6, alpha=0.35, label="Synth")
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=7, markerscale=2)


def ecdf_panel(ax, real, syn, x, title):
    for tag, df, color in [("Real", real, "#1f77b4"), ("Synth", syn, "#ff7f0e")]:
        data = df[x].dropna().sort_values()
        if len(data) > 0:
            ax.plot(data, np.arange(1, len(data) + 1) / len(data), label=tag, color=color)
    ax.set_xlabel(x)
    ax.set_ylabel("ECDF")
    ax.set_title(title)
    ax.legend(fontsize=7)


def correlation_heatmap(ax, real, syn):
    cols = ["num_instances", "final_area_um2", "final_power_mw",
            "core_utilization", "final_wns_ns", "final_tns_ns"]
    for i, (tag, df) in enumerate([("Real", real), ("Synth", syn)]):
        available = [c for c in cols if c in df.columns]
        if len(available) < 2:
            ax[i].text(0.5, 0.5, f"Not enough data for {tag}", ha='center', va='center', transform=ax[i].transAxes)
            continue
        c = df[available].corr()
        sns.heatmap(c, ax=ax[i], vmin=-1, vmax=1, center=0, cmap="RdBu_r",
                    annot=True, fmt=".2f", cbar=i==1, square=True, cbar_kws={"shrink": 0.7})
        ax[i].set_title(f"{tag} Pearson")


def per_platform_corr_bar(ax, real, syn):
    PLATFORMS = ["sky130hd", "asap7", "nangate45", "gf180"]
    x = np.arange(len(PLATFORMS))
    w = 0.35
    pairs_local = [("inst_area", "num_instances", "final_area_um2"),
                    ("area_power", "final_area_um2", "final_power_mw"),
                    ("util_wns", "core_utilization", "final_wns_ns")]
    colors = ["#1f77b4", "#ff7f0e"]
    for j, (tag, df) in enumerate([("Real", real), ("Synth", syn)]):
        vals = []
        for name, a, b in pairs_local:
            vals.append([df[df.platform == p][a].corr(df[df.platform == p][b])
                         if len(df[df.platform == p]) > 1 else np.nan
                         for p in PLATFORMS])
        ax.bar(x + (j - 0.5) * w, vals, width=w, label=tag, color=colors[j], edgecolor="k")
    ax.set_xticks(range(len(PLATFORMS))); ax.set_xticklabels(PLATFORMS)
    ax.set_ylabel("Pearson r"); ax.set_title("Per-platform correlations")
    ax.legend(fontsize=7); ax.axhline(0, color="k", lw=0.5)


def violin_panel(ax, real, syn, y, title):
    real_data = real[y].dropna()
    syn_data = syn[y].dropna()
    if len(real_data) == 0 or len(syn_data) == 0:
        ax.text(0.5, 0.5, f"No data for {y}", ha='center', va='center', transform=ax.transAxes)
        return

    parts = ax.violinplot([real[y].dropna(), syn[y].dropna()],
                          positions=[0, 1], widths=0.6, showmeans=True,
                          showmedians=True, showextrema=False)
    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(["#1f77b4", "#ff7f0e"][i])
        pc.set_alpha(0.6)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Real", "Synth"])
    ax.set_ylabel(y)
    ax.set_title(title)


def scatter_panel(ax, real, syn, x, y, title):
    real_clean = real[[x, y]].dropna()
    syn_clean = syn[[x, y]].dropna()

    if len(real_clean) > 0:
        ax.scatter(real_clean[x], real_clean[y], c="#1f77b4", s=6, alpha=0.35, label="Real")
    if len(syn_clean) > 0:
        ax.scatter(syn_clean[x], syn_clean[y], c="#ff7f0e", s=6, alpha=0.35, label="Synth")
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=7, markerscale=2)


def ecdf_panel(ax, real, syn, x, title):
    for tag, df, color in [("Real", real, "#1f77b4"), ("Synth", syn, "#ff7f0e")]:
        data = df[x].dropna().sort_values()
        if len(data) > 0:
            ax.plot(data, np.arange(1, len(data) + 1) / len(data), label=tag, color=color)
    ax.set_xlabel(x)
    ax.set_ylabel("ECDF")
    ax.set_title(title)
    ax.legend(fontsize=7)


def correlation_heatmap(ax, real, syn):
    cols = ["num_instances", "final_area_um2", "final_power_mw",
            "core_utilization", "final_wns_ns", "final_tns_ns"]
    for i, (tag, df) in enumerate([("Real", real), ("Synth", syn)]):
        available = [c for c in cols if c in df.columns]
        if len(available) < 2:
            ax[i].text(0.5, 0.5, f"Not enough data for {tag}", ha='center', va='center', transform=ax[i].transAxes)
            continue
        c = df[available].corr()
        sns.heatmap(c, ax=ax[i], vmin=-1, vmax=1, center=0, cmap="RdBu_r",
                    annot=True, fmt=".2f", cbar=i==1, square=True, cbar_kws={"shrink": 0.7})
        ax[i].set_title(f"{tag} Pearson")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--synthetic", required=True)
    ap.add_argument("--outdir", default="comparison_plots")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    real = load_df(args.real, "real")
    syn = load_df(args.synthetic, "synthetic")

    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 200,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
    })

    PALETTE = {"real": "#1f77b4", "synthetic": "#ff7f0e"}
    PLATFORMS = ["sky130hd", "asap7", "nangate45", "gf180"]
    PAIRS = [
        ("num_instances", "final_area_um2"),
        ("final_area_um2", "final_power_mw"),
        ("core_utilization", "final_wns_ns"),
        ("final_wns_ns", "final_tns_ns"),
    ]

    real = load_df(args.real, "real")
    syn = load_df(args.synthetic, "synthetic")

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 200,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
    })

    PALETTE = {"real": "#1f77b4", "synthetic": "#ff7f0e"}
    PLATFORMS = ["sky130hd", "asap7", "nangate45", "gf180"]
    PAIRS = [
        ("num_instances", "final_area_um2"),
        ("final_area_um2", "final_power_mw"),
        ("core_utilization", "final_wns_ns"),
        ("final_wns_ns", "final_tns_ns"),
    ]

    real = load_df(args.real, "real")
    syn = load_df(args.synthetic, "synthetic")

    # ============================================================
    # FIG 1: Marginal distributions (violin)
    # ============================================================
    fig, axes = plt.subplots(2, 3, figsize=(10, 6), constrained_layout=True)
    for ax, (y, title) in zip(axes.flat,
        [("final_wns_ns", "Final WNS (ns)"),
         ("final_tns_ns", "Final TNS (ns)"),
         ("final_area_um2", "Area (µm²)"),
         ("final_power_mw", "Power (mW)"),
         ("core_utilization", "Core Utilization (%)"),
         ("num_instances", "Instance Count")]):
        violin_panel(ax, real, syn, y, title)
    fig.suptitle("Marginal Distributions: Real vs Synthetic")
    fig.savefig(outdir / "marginals.pdf"); fig.savefig(outdir / "marginals.png"); plt.close()

    # ============================================================
    # FIG 2: Scatter pairs (joint distributions)
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(9, 9), constrained_layout=True)
    for ax, (x, y) in zip(axes.flat, PAIRS):
        scatter_panel(ax, real, syn, x, y, f"{x} vs {y}")
    fig.suptitle("Joint Distributions: Real vs Synthetic")
    fig.savefig(outdir / "scatter_pairs.pdf"); fig.savefig(outdir / "scatter_pairs.png"); plt.close()

    # ============================================================
    # FIG 3: ECDFs
    # ============================================================
    fig, axes = plt.subplots(2, 3, figsize=(10, 6), constrained_layout=True)
    for ax, (y, title) in zip(axes.flat,
        [("final_wns_ns", "Final WNS"),
         ("final_tns_ns", "Final TNS"),
         ("final_area_um2", "Area"),
         ("final_power_mw", "Power"),
         ("core_utilization", "Utilization"),
         ("num_instances", "Instances")]):
        ecdf_panel(ax, real, syn, y, title)
    fig.suptitle("ECDFs: Real vs Synthetic")
    fig.savefig(outdir / "ecdfs.pdf"); fig.savefig(outdir / "ecdfs.png"); plt.close()

    # ============================================================
    # FIG 4: Correlation heatmaps
    # ============================================================
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    correlation_heatmap(axes, real, syn)
    fig.suptitle("Pearson Correlations (pooled)")
    fig.savefig(outdir / "corr_heatmaps.pdf"); fig.savefig(outdir / "corr_heatmaps.png"); plt.close()

    # ============================================================
    # FIG 5: Per-platform correlation bars
    # ============================================================
    fig, ax = plt.subplots(figsize=(9, 4), constrained_layout=True)
    per_platform_corr_bar(ax, real, syn)
    fig.savefig(outdir / "per_platform_corr.pdf"); fig.savefig(outdir / "per_platform_corr.png"); plt.close()

    # ============================================================
    # FIG 6: Scatter matrix (pairplot subset)
    # ============================================================
    cols = ["num_instances", "final_area_um2", "final_power_mw",
            "core_utilization", "final_wns_ns"]
    g = sns.pairplot(pd.concat([real, syn], ignore_index=True),
                     vars=cols, hue="source", palette=PALETTE,
                     diag_kind="kde", plot_kws=dict(s=5, alpha=0.3),
                     corner=True, height=1.8)
    g.fig.suptitle("Pairwise Relationships", y=1.02)
    g.savefig(outdir / "pairplot.pdf"); g.savefig(outdir / "pairplot.png"); plt.close()

    # ============================================================
    # FIG 7: WNS vs Utilization by platform
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    for ax, p in zip(axes.flat, ["sky130hd", "asap7", "nangate45", "gf180"]):
        for tag, df in [("Real", real), ("Synth", syn)]:
            g = df[df.platform == p]
            if len(g) > 10:
                ax.scatter(g["core_utilization"], g["final_wns_ns"],
                           c=PALETTE[tag.lower()], s=8, alpha=0.4, label=tag)
        ax.set_xlabel("Core Utilization (%)")
        ax.set_ylabel("Final WNS (ns)")
        ax.set_title(f"{p}")
        ax.axhline(0, color="k", ls=":", lw=0.5)
    axes[0,0].legend()
    fig.suptitle("WNS vs Utilization by Platform")
    fig.savefig(outdir / "wns_vs_util.pdf"); fig.savefig(outdir / "wns_vs_util.png"); plt.close()

    print(f"\n✅ All plots saved to {outdir}")


if __name__ == "__main__":
    import argparse
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gs
    import numpy as np
    import pandas as pd
    import seaborn as sns
    from pathlib import Path

    def load_df(path, tag):
        df = pd.read_csv(Path(path))
        df = df[df["status"] == "success"].copy()
        df["source"] = tag

        # Unify power column name
        if "final_power_w" in df.columns and "final_power_mw" not in df.columns:
            df["final_power_mw"] = df["final_power_w"] * 1000

        # Add missing columns with NaN for real data
        if "num_instances" not in df.columns:
            df["num_instances"] = np.nan
        if "final_drc_violations" not in df.columns:
            df["final_drc_violations"] = np.nan

        # Ensure all expected columns exist
        for col in ["status", "final_wns_ns", "final_tns_ns", "final_area_um2",
                    "final_power_mw", "final_power_w", "core_utilization",
                    "platform", "drc_clean", "lvs_clean", "timing_closure",
                    "num_instances", "final_drc_violations"]:
            if col not in df.columns:
                df[col] = np.nan

        return df.copy()

    def violin_panel(ax, real, syn, y, title):
        real_data = real[y].dropna()
        syn_data = syn[y].dropna()
        if len(real_data) == 0 or len(syn_data) == 0:
            ax.text(0.5, 0.5, f"No data for {y}", ha='center', va='center', transform=ax.transAxes)
            return

        parts = ax.violinplot([real[y].dropna(), syn[y].dropna()],
                              positions=[0, 1], widths=0.6, showmeans=True,
                              showmedians=True, showextrema=False)
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(["#1f77b4", "#ff7f0e"][i])
            pc.set_alpha(0.6)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Real", "Synth"])
        ax.set_ylabel(y)
        ax.set_title(title)

    def scatter_panel(ax, real, syn, x, y, title):
        real_clean = real[[x, y]].dropna()
        syn_clean = syn[[x, y]].dropna()

        if len(real_clean) > 0:
            ax.scatter(real_clean[x], real_clean[y], c="#1f77b4", s=6, alpha=0.35, label="Real")
        if len(syn_clean) > 0:
            ax.scatter(syn_clean[x], syn_clean[y], c="#ff7f0e", s=6, alpha=0.35, label="Synth")
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title(title)
        ax.legend(loc="upper right", fontsize=7, markerscale=2)

    def ecdf_panel(ax, real, syn, x, title):
        for tag, df, color in [("Real", real, "#1f77b4"), ("Synth", syn, "#ff7f0e")]:
            data = df[x].dropna().sort_values()
            if len(data) > 0:
                ax.plot(data, np.arange(1, len(data) + 1) / len(data), label=tag, color=color)
        ax.set_xlabel(x)
        ax.set_ylabel("ECDF")
        ax.set_title(title)
        ax.legend(fontsize=7)

    def correlation_heatmap(ax, real, syn):
        cols = ["num_instances", "final_area_um2", "final_power_mw",
                "core_utilization", "final_wns_ns", "final_tns_ns"]
        for i, (tag, df) in enumerate([("Real", real), ("Synth", syn)]):
            available = [c for c in cols if c in df.columns]
            if len(available) < 2:
                ax[i].text(0.5, 0.5, f"Not enough data for {tag}", ha='center', va='center', transform=ax[i].transAxes)
                continue
            c = df[available].corr()
            sns.heatmap(c, ax=ax[i], vmin=-1, vmax=1, center=0, cmap="RdBu_r",
                        annot=True, fmt=".2f", cbar=i==1, square=True, cbar_kws={"shrink": 0.7})
            ax[i].set_title(f"{tag} Pearson")

    def per_platform_corr_bar(ax, real, syn):
        PLATFORMS = ["sky130hd", "asap7", "nangate45", "gf180"]
        x = np.arange(len(PLATFORMS))
        w = 0.35
        pairs_local = [("inst_area", "num_instances", "final_area_um2"),
                        ("area_power", "final_area_um2", "final_power_mw"),
                        ("util_wns", "core_utilization", "final_wns_ns")]
        colors = ["#1f77b4", "#ff7f0e"]
        for j, (tag, df) in enumerate([("Real", real), ("Synth", syn)]):
            vals = []
            for name, a, b in pairs_local:
                vals.append([df[df.platform == p][a].corr(df[df.platform == p][b])
                             if len(df[df.platform == p]) > 1 else np.nan
                             for p in PLATFORMS])
            ax.bar(x + (j - 0.5) * w, vals, width=w, label=tag, color=colors[j], edgecolor="k")
        ax.set_xticks(range(len(PLATFORMS))); ax.set_xticklabels(PLATFORMS)
        ax.set_ylabel("Pearson r"); ax.set_title("Per-platform correlations")
        ax.legend(fontsize=7); ax.axhline(0, color="k", lw=0.5)


if __name__ == "__main__":
    import argparse
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gs
    import numpy as np
    import pandas as pd
    import seaborn as sns
    from pathlib import Path

    def load_df(path, tag):
        df = pd.read_csv(Path(path))
        df = df[df["status"] == "success"].copy()
        df["source"] = tag

        # Unify power column name
        if "final_power_w" in df.columns and "final_power_mw" not in df.columns:
            df["final_power_mw"] = df["final_power_w"] * 1000

        # Add missing columns with NaN for real data
        if "num_instances" not in df.columns:
            df["num_instances"] = np.nan
        if "final_drc_violations" not in df.columns:
            df["final_drc_violations"] = np.nan

        # Ensure all expected columns exist
        for col in ["status", "final_wns_ns", "final_tns_ns", "final_area_um2",
                    "final_power_mw", "final_power_w", "core_utilization",
                    "platform", "drc_clean", "lvs_clean", "timing_closure",
                    "num_instances", "final_drc_violations"]:
            if col not in df.columns:
                df[col] = np.nan

        return df.copy()

    def violin_panel(ax, real, syn, y, title):
        real_data = real[y].dropna()
        syn_data = syn[y].dropna()
        if len(real_data) == 0 or len(syn_data) == 0:
            ax.text(0.5, 0.5, f"No data for {y}", ha='center', va='center', transform=ax.transAxes)
            return

        parts = ax.violinplot([real[y].dropna(), syn[y].dropna()],
                              positions=[0, 1], widths=0.6, showmeans=True,
                              showmedians=True, showextrema=False)
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(["#1f77b4", "#ff7f0e"][i])
            pc.set_alpha(0.6)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Real", "Synth"])
        ax.set_ylabel(y)
        ax.set_title(title)

    def scatter_panel(ax, real, syn, x, y, title):
        real_clean = real[[x, y]].dropna()
        syn_clean = syn[[x, y]].dropna()

        if len(real_clean) > 0:
            ax.scatter(real_clean[x], real_clean[y], c="#1f77b4", s=6, alpha=0.35, label="Real")
        if len(syn_clean) > 0:
            ax.scatter(syn_clean[x], syn_clean[y], c="#ff7f0e", s=6, alpha=0.35, label="Synth")
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title(title)
        ax.legend(loc="upper right", fontsize=7, markerscale=2)

    def ecdf_panel(ax, real, syn, x, title):
        for tag, df, color in [("Real", real, "#1f77b4"), ("Synth", syn, "#ff7f0e")]:
            data = df[x].dropna().sort_values()
            if len(data) > 0:
                ax.plot(data, np.arange(1, len(data) + 1) / len(data), label=tag, color=color)
        ax.set_xlabel(x)
        ax.set_ylabel("ECDF")
        ax.set_title(title)
        ax.legend(fontsize=7)

    def correlation_heatmap(ax, real, syn):
        cols = ["num_instances", "final_area_um2", "final_power_mw",
                "core_utilization", "final_wns_ns", "final_tns_ns"]
        for i, (tag, df) in enumerate([("Real", real), ("Synth", syn)]):
            available = [c for c in cols if c in df.columns]
            if len(available) < 2:
                ax[i].text(0.5, 0.5, f"Not enough data for {tag}", ha='center', va='center', transform=ax[i].transAxes)
                continue
            c = df[available].corr()
            sns.heatmap(c, ax=ax[i], vmin=-1, vmax=1, center=0, cmap="RdBu_r",
                        annot=True, fmt=".2f", cbar=i==1, square=True, cbar_kws={"shrink": 0.7})
            ax[i].set_title(f"{tag} Pearson")

    def per_platform_corr_bar(ax, real, syn):
        PLATFORMS = ["sky130hd", "asap7", "nangate45", "gf180"]
        x = np.arange(len(PLATFORMS))
        w = 0.35
        pairs_local = [("inst_area", "num_instances", "final_area_um2"),
                        ("area_power", "final_area_um2", "final_power_mw"),
                        ("util_wns", "core_utilization", "final_wns_ns")]
        colors = ["#1f77b4", "#ff7f0e"]
        for j, (tag, df) in enumerate([("Real", real), ("Synth", syn)]):
            vals = []
            for name, a, b in pairs_local:
                vals.append([df[df.platform == p][a].corr(df[df.platform == p][b])
                             if len(df[df.platform == p]) > 1 else np.nan
                             for p in PLATFORMS])
            ax.bar(x + (j - 0.5) * w, vals, width=w, label=tag, color=colors[j], edgecolor="k")
        ax.set_xticks(range(len(PLATFORMS))); ax.set_xticklabels(PLATFORMS)
        ax.set_ylabel("Pearson r"); ax.set_title("Per-platform correlations")
        ax.legend(fontsize=7); ax.axhline(0, color="k", lw=0.5)


if __name__ == "__main__":
    import argparse
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gs
    import numpy as np
    import pandas as pd
    import seaborn as sns
    from pathlib import Path

    def load_df(path, tag):
        df = pd.read_csv(Path(path))
        df = df[df["status"] == "success"].copy()
        df["source"] = tag

        # Unify power column name
        if "final_power_w" in df.columns and "final_power_mw" not in df.columns:
            df["final_power_mw"] = df["final_power_w"] * 1000

        # Add missing columns with NaN for real data
        if "num_instances" not in df.columns:
            df["num_instances"] = np.nan
        if "final_drc_violations" not in df.columns:
            df["final_drc_violations"] = np.nan

        # Ensure all expected columns exist
        for col in ["status", "final_wns_ns", "final_tns_ns", "final_area_um2",
                    "final_power_mw", "final_power_w", "core_utilization",
                    "platform", "drc_clean", "lvs_clean", "timing_closure",
                    "num_instances", "final_drc_violations"]:
            if col not in df.columns:
                df[col] = np.nan

        return df.copy()

    def violin_panel(ax, real, syn, y, title):
        real_data = real[y].dropna()
        syn_data = syn[y].dropna()
        if len(real_data) == 0 or len(syn_data) == 0:
            ax.text(0.5, 0.5, f"No data for {y}", ha='center', va='center', transform=ax.transAxes)
            return

        parts = ax.violinplot([real[y].dropna(), syn[y].dropna()],
                              positions=[0, 1], widths=0.6, showmeans=True,
                              showmedians=True, showextrema=False)
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(["#1f77b4", "#ff7f0e"][i])
            pc.set_alpha(0.6)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Real", "Synth"])
        ax.set_ylabel(y)
        ax.set_title(title)

    def scatter_panel(ax, real, syn, x, y, title):
        real_clean = real[[x, y]].dropna()
        syn_clean = syn[[x, y]].dropna()

        if len(real_clean) > 0:
            ax.scatter(real_clean[x], real_clean[y], c="#1f77b4", s=6, alpha=0.35, label="Real")
        if len(syn_clean) > 0:
            ax.scatter(syn_clean[x], syn_clean[y], c="#ff7f0e", s=6, alpha=0.35, label="Synth")
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title(title)
        ax.legend(loc="upper right", fontsize=7, markerscale=2)

    def ecdf_panel(ax, real, syn, x, title):
        for tag, df, color in [("Real", real, "#1f77b4"), ("Synth", syn, "#ff7f0e")]:
            data = df[x].dropna().sort_values()
            if len(data) > 0:
                ax.plot(data, np.arange(1, len(data) + 1) / len(data), label=tag, color=color)
        ax.set_xlabel(x)
        ax.set_ylabel("ECDF")
        ax.set_title(title)
        ax.legend(fontsize=7)

    def correlation_heatmap(ax, real, syn):
        cols = ["num_instances", "final_area_um2", "final_power_mw",
                "core_utilization", "final_wns_ns", "final_tns_ns"]
        for i, (tag, df) in enumerate([("Real", real), ("Synth", syn)]):
            available = [c for c in cols if c in df.columns]
            if len(available) < 2:
                ax[i].text(0.5, 0.5, f"Not enough data for {tag}", ha='center', va='center', transform=ax[i].transAxes)
                continue
            c = df[available].corr()
            sns.heatmap(c, ax=ax[i], vmin=-1, vmax=1, center=0, cmap="RdBu_r",
                        annot=True, fmt=".2f", cbar=i==1, square=True, cbar_kws={"shrink": 0.7})
            ax[i].set_title(f"{tag} Pearson")

    def per_platform_corr_bar(ax, real, syn):
        PLATFORMS = ["sky130hd", "asap7", "nangate45", "gf180"]
        x = np.arange(len(PLATFORMS))
        w = 0.35
        pairs_local = [("inst_area", "num_instances", "final_area_um2"),
                        ("area_power", "final_area_um2", "final_power_mw"),
                        ("util_wns", "core_utilization", "final_wns_ns")]
        colors = ["#1f77b4", "#ff7f0e"]
        for j, (tag, df) in enumerate([("Real", real), ("Synth", syn)]):
            vals = []
            for name, a, b in pairs_local:
                vals.append([df[df.platform == p][a].corr(df[df.platform == p][b])
                             if len(df[df.platform == p]) > 1 else np.nan
                             for p in PLATFORMS])
            ax.bar(x + (j - 0.5) * w, vals, width=w, label=tag, color=colors[j], edgecolor="k")
        ax.set_xticks(range(len(PLATFORMS))); ax.set_xticklabels(PLATFORMS)
        ax.set_ylabel("Pearson r"); ax.set_title("Per-platform correlations")
        ax.legend(fontsize=7); ax.axhline(0, color="k", lw=0.5)

    main()