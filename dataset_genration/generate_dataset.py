#!/usr/bin/env python3
"""
OpenROAD Flow GUI - Intelligence Module
Synthetic training-data generator (3,000 rows, 35 columns).

Usage
-----
    python generate_dataset.py                      # local engine, 3000 rows
    python generate_dataset.py --rows 5000 --seed 7
    python generate_dataset.py --use-datadesigner   # optional: NVIDIA Data Designer
                                                    # supplies design_name / aspect ratio /
                                                    # margin (needs NVIDIA_API_KEY)

Requires: numpy, pandas, pyarrow (parquet), openpyxl (xlsx)
Optional: nemo-microservices[data-designer]

Outputs (in --outdir, default ./output):
    training_data.parquet / .csv / .xlsx / .jsonl     full dataset
    splits/{train,validation,test}.csv                 70/20/10 stratified split

Design notes
------------
* Data Designer samplers draw each column independently, so they cannot enforce the
  correlations and logical constraints the spec marks as MUST-PRESERVE. The statistical
  core is therefore generated locally (Gaussian-copula-style rank coupling + exact
  class-balance quotas). Data Designer is optional and only feeds the free-standing
  categorical/config columns; if it fails, the script falls back to local sampling.
* The script validates the result against the spec checklist and re-seeds
  (seed, seed+1, ...) until every check passes.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Spec constants
# --------------------------------------------------------------------------- #
REAL_DESIGNS = [
    "alu4", "alu_4bit", "gcd", "mock-cpu", "Multiplier", "multiplier_4bit",
    "mux4x1", "my_design", "my_design2", "sonibhai", "Sample2", "aes",
    "comparator2bit", "counter4", "ibex", "picorv32_pd", "uart-blocks",
    "riscv32i", "tinyRocket", "mux_2x1_behaviroal", "nangate45_aes",
]  # "gcd" appears twice in the spec; de-duplicated -> 21 unique

SYNTHETIC_DESIGNS = [
    "fifo_8x32", "spi_master", "i2c_controller", "uart_tx", "uart_rx", "pwm_gen",
    "crc32", "sha256_core", "aes_encrypt", "aes_decrypt", "dma_controller",
    "interrupt_ctrl", "timer_32bit", "gpio_ctrl", "spi_slave", "jtag_tap",
    "riscv_core", "picorv32", "vexriscv", "ibex_core", "fpu_sp", "fpu_dp",
    "div_sqrt", "mul_acc", "fft_256", "fir_filter", "iir_filter", "cordic",
    "matrix_mul_4x4", "conv2d_3x3", "pooling_max", "relu_activation",
    "batch_norm", "lstm_cell", "gru_cell", "attention_head", "transformer_block",
    "embed_lookup", "pos_encoding", "layer_norm", "dropout_layer", "residual_add",
    "skip_connection",
    # extra names to reach the spec's "50 synthetic"
    "sobel_filter", "bitonic_sort", "ecc_secded", "arbiter_rr", "cache_ctrl",
    "tlb", "branch_predictor",
]

# weight, utilization range, area/instance (um2), power coefficient, timing bias
PLATFORMS = {
    "sky130hd":  dict(weight=0.30, util=(20, 50), k_area=30.0, k_pow=0.0030, bias=-0.15),
    "asap7":     dict(weight=0.30, util=(15, 40), k_area=12.0, k_pow=0.0040, bias=-0.45),
    "nangate45": dict(weight=0.20, util=(25, 60), k_area=45.0, k_pow=0.0040, bias=+0.50),
    "gf180":     dict(weight=0.20, util=(20, 50), k_area=40.0, k_pow=0.0035, bias=-0.15),
}
ASPECT_RATIOS = [0.5, 1.0, 1.5, 2.0]

TINY_KW = ["mux", "counter", "comparator", "alu", "gcd", "my_design", "sample",
           "multiplier_4bit", "relu", "residual", "skip", "dropout", "pwm", "gpio",
           "timer", "uart", "sonibhai", "crc", "pooling", "pos_enc", "norm"]
LARGE_KW = ["riscv", "picorv32", "vexriscv", "ibex", "rocket", "aes", "sha", "fpu",
            "fft", "transformer", "attention", "lstm", "gru", "conv2d", "matrix",
            "dma", "cache", "tlb", "mock-cpu", "branch"]
TIER_MU = {"tiny": 6.4, "medium": 8.0, "large": 9.6}   # log-mean of num_instances
TIER_SIGMA = 0.8

COLUMNS = [  # exact order / names of the 35-column reference dataset
    "run_id", "design_name", "platform", "timestamp",
    "num_instances", "num_nets", "num_sequential", "num_macros", "macro_area_ratio",
    "design_name_config", "platform_config",
    "core_utilization", "core_aspect_ratio", "core_margin",
    "final_wns_ns", "final_tns_ns", "final_area_um2", "final_power_mw",
    "final_drc_violations", "total_runtime_sec",
    "timing_closure", "drc_clean", "lvs_clean",
    "log_instances", "log_nets", "seq_ratio", "macro_ratio",
    "wns_normalized", "tns_normalized", "log_area", "log_power",
    "timing_closure_bin", "drc_clean_bin", "lvs_clean_bin", "platform_cat",
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def tier_of(name: str) -> str:
    n = name.lower()
    if any(k in n for k in TINY_KW):
        return "tiny"
    if any(k in n for k in LARGE_KW):
        return "large"
    return "medium"


def exact_counts(n: int, weights: dict[str, float]) -> dict[str, int]:
    """Largest-remainder rounding so the platform mix is exact."""
    raw = {k: n * w for k, w in weights.items()}
    cnt = {k: int(np.floor(v)) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - cnt[k], reverse=True)[: n - sum(cnt.values())]:
        cnt[k] += 1
    return cnt


def trunc_normal(rng, mean, sd, size, low=0.0):
    """Normal(mean, sd) truncated to > low by redrawing."""
    x = rng.normal(mean, sd, size)
    bad = x <= low
    while bad.any():
        x[bad] = rng.normal(mean, sd, bad.sum())
        bad = x <= low
    return x


def zscore(x):
    x = np.asarray(x, float)
    return (x - x.mean()) / (x.std() + 1e-12)


def zt_poisson(rng, lam, size):
    """Zero-truncated Poisson (violations given at least one)."""
    x = rng.poisson(lam, size)
    bad = x == 0
    while bad.any():
        x[bad] = rng.poisson(lam, bad.sum())
        bad = x == 0
    return x


# --------------------------------------------------------------------------- #
# Optional: NVIDIA Data Designer skeleton
# --------------------------------------------------------------------------- #
def datadesigner_skeleton(n: int, design_pool: list[str], weights: list[float]) -> pd.DataFrame:
    """Draw design_name / core_aspect_ratio / core_margin through Data Designer samplers.
    Raises on any failure (caller falls back to local sampling)."""
    from nemo_microservices.data_designer.essentials import (
        CategorySamplerParams, DataDesignerConfigBuilder, InferenceParameters,
        ModelConfig, NeMoDataDesignerClient, SamplerColumnConfig, SamplerType,
        UniformSamplerParams,
    )

    client = NeMoDataDesignerClient(
        base_url="https://ai.api.nvidia.com/v1/nemo/dd",
        default_headers={"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}"},
    )
    cfg = DataDesignerConfigBuilder([
        ModelConfig(alias="my-model", model="nvidia/nemotron-3-nano-30b-a3b",
                    inference_parameters=InferenceParameters(temperature=0.6, top_p=0.95,
                                                             max_tokens=256))
    ])
    cfg.add_column(SamplerColumnConfig(
        name="design_name", sampler_type=SamplerType.CATEGORY,
        params=CategorySamplerParams(values=design_pool, weights=weights)))
    cfg.add_column(SamplerColumnConfig(
        name="core_aspect_ratio", sampler_type=SamplerType.CATEGORY,
        params=CategorySamplerParams(values=ASPECT_RATIOS)))
    cfg.add_column(SamplerColumnConfig(
        name="core_margin", sampler_type=SamplerType.UNIFORM,
        params=UniformSamplerParams(low=1, high=10), convert_to="int"))

    frames, got, chunk = [], 0, 500
    while got < n:
        k = min(chunk, n - got)
        frames.append(client.preview(cfg, num_records=k).dataset)
        got += k
    return pd.concat(frames, ignore_index=True).iloc[:n]


# --------------------------------------------------------------------------- #
# Core generator
# --------------------------------------------------------------------------- #
def generate(n: int, seed: int, use_dd: bool = False, anchor: datetime | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    anchor = anchor or datetime.now()

    # ---- platform (exact stratification) --------------------------------- #
    cnt = exact_counts(n, {p: v["weight"] for p, v in PLATFORMS.items()})
    platform = np.concatenate([[p] * c for p, c in cnt.items()])
    rng.shuffle(platform)

    # ---- design names: 60% real pool, 40% synthetic pool ------------------ #
    pool = REAL_DESIGNS + SYNTHETIC_DESIGNS
    w = np.array([0.6 / len(REAL_DESIGNS)] * len(REAL_DESIGNS)
                 + [0.4 / len(SYNTHETIC_DESIGNS)] * len(SYNTHETIC_DESIGNS))
    design = None
    if use_dd:
        try:
            design = datadesigner_skeleton(n, pool, list(w))
            print("[datadesigner] skeleton OK")
        except Exception as e:  # noqa: BLE001
            print(f"[datadesigner] failed ({e!r}); falling back to local sampling", file=sys.stderr)
    if design is not None:
        design_name = design["design_name"].to_numpy()
        aspect = design["core_aspect_ratio"].astype(float).to_numpy()
        margin = design["core_margin"].astype(int).to_numpy()
    else:
        design_name = rng.choice(pool, size=n, p=w)
        aspect = rng.choice(ASPECT_RATIOS, size=n)
        margin = rng.integers(1, 11, size=n)

    # ---- design size ------------------------------------------------------ #
    mu = np.array([TIER_MU[tier_of(d)] for d in design_name])
    num_inst = np.clip(np.round(np.exp(rng.normal(mu, TIER_SIGMA))), 100, 1_000_000).astype(int)
    num_nets = np.maximum(num_inst, np.round(num_inst * np.clip(rng.normal(1.2, 0.06, n), 1.1, 1.5))).astype(int)
    p_seq = np.clip(rng.normal(0.20, 0.035, n), 0.10, 0.30)
    num_seq = rng.binomial(num_inst, p_seq)
    num_macros = np.minimum(rng.poisson(2, n), 50)
    macro_area_ratio = np.where(num_macros > 0,
                                np.clip(num_macros * rng.uniform(0.01, 0.05, n), 0, 0.6), 0.0).round(4)

    # ---- floorplan config ------------------------------------------------- #
    util = np.zeros(n, int)
    for p, spec in PLATFORMS.items():
        m = platform == p
        util[m] = rng.integers(spec["util"][0], spec["util"][1] + 1, m.sum())
    bias = np.array([PLATFORMS[p]["bias"] for p in platform])

    # ---- WNS: exact 30% closure, rank-coupled to utilization -------------- #
    n_pos = int(round(0.30 * n))
    marg = np.concatenate([
        trunc_normal(rng, 20, 15, n_pos, low=0.0),           # closed:  WNS > 0
        -trunc_normal(rng, 50, 30, n - n_pos, low=0.0),      # failing: WNS < 0
    ])
    marg = np.where(marg >= 0, np.round(marg, 2), np.minimum(np.round(marg, 2), -0.01))
    marg = np.sort(marg)[::-1]                                # best -> worst
    # latent "goodness": low utilization, favourable platform, smaller design
    score = (-0.58 * zscore(util) + 0.20 * zscore(bias)
             - 0.08 * zscore(np.log(num_inst)) + 0.75 * rng.standard_normal(n))
    wns = np.empty(n)
    wns[np.argsort(-score)] = marg
    closure = (wns >= 0).astype(int)

    # ---- TNS ~ 10 x WNS (0 when timing is met) ---------------------------- #
    tns = np.where(closure == 1, 0.0, wns * 10 * np.exp(rng.normal(0, 0.30, n)))
    tns = np.minimum(np.round(tns, 2), 0.0)

    # ---- Area (log-linear in instances), Power (sub-linear in area) ------- #
    k_area = np.array([PLATFORMS[p]["k_area"] for p in platform])
    area = num_inst * k_area * np.exp(rng.normal(0, 0.12, n)) * (1 + macro_area_ratio)
    area = np.maximum(np.round(area, 2), 2.3)
    k_pow = np.array([PLATFORMS[p]["k_pow"] for p in platform])
    power = k_pow * area ** 0.85 * np.exp(rng.normal(0, 0.75, n))
    power = np.maximum(np.round(power, 3), 0.007)

    # ---- DRC: exactly 15% dirty, more likely when timing fails ------------ #
    n_dirty = int(round(0.15 * n))
    wdrc = np.where(closure == 1, 0.05, 0.19) * np.exp(0.25 * zscore(util))
    dirty_idx = rng.choice(n, size=n_dirty, replace=False, p=wdrc / wdrc.sum())
    drc = np.zeros(n, int)
    drc[dirty_idx] = zt_poisson(rng, 5, n_dirty)
    drc_clean = (drc == 0).astype(int)
    lvs_clean = drc_clean.copy()          # spec: LVS clean iff DRC clean (lvs <= drc)

    # ---- runtime ----------------------------------------------------------- #
    runtime = np.clip(num_inst * 0.03 * (1 + util / 100) * np.exp(rng.normal(0, 0.35, n)), 5, 20000).round(2)

    # ---- identifiers ------------------------------------------------------- #
    ts = [(anchor - timedelta(seconds=float(s))).isoformat()
          for s in rng.uniform(0, 365 * 86400, n)]
    run_id = [f"{d}_{p}_{rng.integers(0, 16**8):08x}" for d, p in zip(design_name, platform)]
    cfg_name = [re.split(r"[-_]", d)[0].lower() for d in design_name]

    df = pd.DataFrame({
        "run_id": run_id, "design_name": design_name, "platform": platform, "timestamp": ts,
        "num_instances": num_inst, "num_nets": num_nets, "num_sequential": num_seq,
        "num_macros": num_macros, "macro_area_ratio": macro_area_ratio,
        "design_name_config": cfg_name, "platform_config": platform,
        "core_utilization": util.astype(float), "core_aspect_ratio": aspect.astype(float),
        "core_margin": margin.astype(float),
        "final_wns_ns": wns, "final_tns_ns": tns, "final_area_um2": area, "final_power_mw": power,
        "final_drc_violations": drc, "total_runtime_sec": runtime,
        "timing_closure": closure, "drc_clean": drc_clean, "lvs_clean": lvs_clean,
        "log_instances": np.log1p(num_inst) / 20, "log_nets": np.log1p(num_nets) / 20,
        "seq_ratio": num_seq / np.maximum(num_inst, 1), "macro_ratio": num_macros / np.maximum(num_inst, 1),
        "wns_normalized": np.clip(wns / 10, -1, 1), "tns_normalized": np.clip(tns / 1000, -1, 1),
        "log_area": np.log1p(area) / 20, "log_power": np.log1p(power) / 20,
        "timing_closure_bin": closure, "drc_clean_bin": drc_clean, "lvs_clean_bin": lvs_clean,
        "platform_cat": platform,
    })
    return df[COLUMNS]


# --------------------------------------------------------------------------- #
# Validation (spec checklist + correlation targets)
# --------------------------------------------------------------------------- #
def validate(df: pd.DataFrame, n: int) -> tuple[list[str], dict]:
    fails, stats = [], {}

    def check(name, ok, val=None):
        stats[name] = val
        if not ok:
            fails.append(f"{name} = {val}")

    check("rows", len(df) == n, len(df))
    check("columns", df.shape[1] == 35, df.shape[1])
    tc, dc = df.timing_closure_bin.mean(), df.drc_clean_bin.mean()
    check("timing_closure_mean", abs(tc - 0.30) < 0.02, round(tc, 4))
    check("drc_clean_mean", abs(dc - 0.85) < 0.02, round(dc, 4))
    mix = df.platform.value_counts(normalize=True).round(2).to_dict()
    check("platform_mix", mix == {"sky130hd": .30, "asap7": .30, "nangate45": .20, "gf180": .20}, mix)

    c = {
        "wns_tns": df.final_wns_ns.corr(df.final_tns_ns),
        "inst_area": df.num_instances.corr(df.final_area_um2),
        "area_power": df.final_area_um2.corr(df.final_power_mw),
        "util_wns": df.core_utilization.corr(df.final_wns_ns),
        "drc_vs_closure": df.final_drc_violations.corr(df.timing_closure_bin),
        "wns_vs_closure": df.final_wns_ns.corr(df.timing_closure_bin),
    }
    stats.update({f"corr_{k}": round(v, 3) for k, v in c.items()})
    check("corr_wns_tns>0.85", c["wns_tns"] > 0.85, round(c["wns_tns"], 3))
    check("corr_inst_area>0.85", c["inst_area"] > 0.85, round(c["inst_area"], 3))
    check("corr_area_power in [0.55,0.75]", 0.55 <= c["area_power"] <= 0.75, round(c["area_power"], 3))
    check("corr_util_wns in [-0.6,-0.4]", -0.6 <= c["util_wns"] <= -0.4, round(c["util_wns"], 3))
    check("corr_drc_vs_closure < 0", c["drc_vs_closure"] < 0, round(c["drc_vs_closure"], 3))

    check("closure<=>WNS>=0", bool((df.timing_closure_bin == (df.final_wns_ns >= 0)).all()))
    check("drc_clean<=>DRC==0", bool((df.drc_clean_bin == (df.final_drc_violations == 0)).all()))
    check("lvs<=drc", bool((df.lvs_clean_bin <= df.drc_clean_bin).all()))
    check("nets>=instances", bool((df.num_nets >= df.num_instances).all()))
    check("seq<=instances", bool((df.num_sequential <= df.num_instances).all()))
    check("util in [10,80]", bool(df.core_utilization.between(10, 80).all()))
    check("aspect discrete", bool(df.core_aspect_ratio.isin(ASPECT_RATIOS).all()))
    check("no nulls", int(df.isna().sum().sum()) == 0)
    check("run_id unique", df.run_id.is_unique)
    return fails, stats


# --------------------------------------------------------------------------- #
# Splits + export
# --------------------------------------------------------------------------- #
def stratified_split(df: pd.DataFrame, seed: int):
    """70/20/10 split stratified by platform x timing_closure."""
    rng = np.random.default_rng(seed)
    tr, va, te = [], [], []
    for _, g in df.groupby(["platform", "timing_closure_bin"]):
        idx = rng.permutation(g.index.to_numpy())
        a, b = int(round(0.7 * len(idx))), int(round(0.9 * len(idx)))
        tr += list(idx[:a]); va += list(idx[a:b]); te += list(idx[b:])
    return df.loc[tr], df.loc[va], df.loc[te]


def export(df: pd.DataFrame, outdir: Path, seed: int):
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "splits").mkdir(exist_ok=True)
    df.to_parquet(outdir / "training_data.parquet", index=False)
    df.to_csv(outdir / "training_data.csv", index=False)
    df.to_excel(outdir / "training_data.xlsx", index=False)
    df.to_json(outdir / "training_data.jsonl", orient="records", lines=True)
    for name, part in zip(["train", "validation", "test"], stratified_split(df, seed)):
        part.to_csv(outdir / "splits" / f"{name}.csv", index=False)
        print(f"  split {name:<10} {len(part):>5} rows")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", type=Path, default=Path("output"))
    ap.add_argument("--use-datadesigner", action="store_true")
    ap.add_argument("--max-attempts", type=int, default=25)
    a = ap.parse_args()

    anchor = datetime.now()
    for attempt in range(a.max_attempts):
        seed = a.seed + attempt
        df = generate(a.rows, seed, a.use_datadesigner, anchor)
        fails, stats = validate(df, a.rows)
        if not fails:
            break
        print(f"attempt {attempt + 1} (seed {seed}) failed: {fails}")
    else:
        sys.exit("Could not satisfy all validation checks; see failures above.")

    print(f"\nAll validation checks passed (seed {seed}).")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    export(df, a.outdir, seed)
    print(f"\nWrote files to {a.outdir.resolve()}")


if __name__ == "__main__":
    main()