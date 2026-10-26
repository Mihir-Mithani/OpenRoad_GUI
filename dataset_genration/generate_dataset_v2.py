#!/usr/bin/env python3
"""
OpenROAD Flow GUI - Intelligence Module
Synthetic training-data generator grounded in REAL ORFS data.

Usage
-----
    python generate_dataset_v2.py --real-data real_runs.json --rows 3000 --seed 42
    python generate_dataset_v2.py --rows 3000 --seed 42  # Falls back to built-in priors

Phases
------
1. Load real ORFS runs (if provided)
2. Learn distributions & correlations from real data
3. BLEND real priors with SPEC TARGETS for validation
4. Generate synthetic designs matching blended statistics
5. Validate against spec checklist
6. Export dataset + splits
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import polars as pl

# ─────────────────────────────────────────────────────────────────────────────
# SPEC CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
REAL_DESIGNS = [
    "alu4", "alu_4bit", "gcd", "mock-cpu", "Multiplier", "multiplier_4bit",
    "mux4x1", "my_design", "my_design2", "sonibhai", "Sample2", "aes",
    "comparator2bit", "counter4", "ibex", "picorv32_pd", "uart-blocks",
    "riscv32i", "tinyRocket", "mux_2x1_behaviroal", "nangate45_aes",
]

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
    "sobel_filter", "bitonic_sort", "ecc_secded", "arbiter_rr", "cache_ctrl",
    "tlb", "branch_predictor",
]

# ─── SPEC TARGETS (validation targets - these MUST be met) ───
SPEC_TARGETS = {
    "platform_weights": {"sky130hd": 0.30, "asap7": 0.30, "nangate45": 0.20, "gf180": 0.20},
    "closure_rate": 0.30,
    "drc_clean_rate": 0.85,
    "wns_tns_corr_min": 0.85,
    "area_power_corr_range": (0.55, 0.75),
    "util_wns_corr_range": (-0.6, -0.4),
}

# ─── PLATFORM SPECS (used for generation priors) ───
PLATFORMS_SPEC = {
    "sky130hd":  dict(weight=0.30, util_range=(20, 50), k_area=30.0, k_pow=0.0030, timing_bias=-0.15),
    "asap7":     dict(weight=0.30, util_range=(15, 40), k_area=12.0, k_pow=0.0040, timing_bias=-0.45),
    "nangate45": dict(weight=0.20, util_range=(25, 60), k_area=45.0, k_pow=0.0040, timing_bias=+0.50),
    "gf180":     dict(weight=0.20, util_range=(20, 50), k_area=40.0, k_pow=0.0035, timing_bias=-0.15),
    "ihp-sg13g2": dict(weight=0.10, util_range=(15, 45), k_area=25.0, k_pow=0.0035, timing_bias=-0.20),
}

ASPECT_RATIOS = [0.5, 0.67, 0.8, 1.0, 1.2, 1.33, 1.5, 1.67, 2.0, 2.5, 3.0]

TINY_KW = ["mux", "counter", "comparator", "alu", "gcd", "my_design", "sample",
           "multiplier_4bit", "relu", "residual", "skip", "dropout", "pwm", "gpio",
           "timer", "uart", "sonibhai", "crc", "pooling", "pos_enc", "norm"]
LARGE_KW = ["riscv", "picorv32", "vexriscv", "ibex", "rocket", "aes", "sha", "fpu",
            "fft", "transformer", "attention", "lstm", "gru", "conv2d", "matrix",
            "dma", "cache", "tlb", "mock-cpu", "branch"]
TIER_MU = {"tiny": 6.4, "medium": 8.0, "large": 9.6}
TIER_SIGMA = 0.8

COLUMNS = [
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


# ─────────────────────────────────────────────────────────────────────────────
# PRIOR DEFAULTS (used if no real data provided)
# ─────────────────────────────────────────────────────────────────────────────
def _default_real_data_priors() -> Dict:
    """Fallback priors when no real data available."""
    return {
        "design_tier_probs": {"tiny": 0.45, "medium": 0.35, "large": 0.20},
        "platform_weights": SPEC_TARGETS["platform_weights"].copy(),
        "aspect_ratios": ASPECT_RATIOS,
        "core_margin_range": (1, 10),
        "util_by_platform": {p: v["util_range"] for p, v in PLATFORMS_SPEC.items()},
        "area_k_by_platform": {p: v["k_area"] for p, v in PLATFORMS_SPEC.items()},
        "power_k_by_platform": {p: v["k_pow"] for p, v in PLATFORMS_SPEC.items()},
        "timing_bias_by_platform": {p: v["timing_bias"] for p, v in PLATFORMS_SPEC.items()},
        "tier_mu": TIER_MU,
        "tier_sigma": TIER_SIGMA,
        "closure_rate": SPEC_TARGETS["closure_rate"],
        "drc_clean_rate": SPEC_TARGETS["drc_clean_rate"],
        "wns_tns_corr": 0.9,
        "area_power_corr": 0.65,
        "util_wns_corr": -0.5,
    }


# ─────────────────────────────────────────────────────────────────────────────
# REAL DATA ANALYSIS (BLEND with spec targets)
# ─────────────────────────────────────────────────────────────────────────────
def analyze_real_data(real_data_path: str) -> Dict:
    """Learn distributions from real ORFS runs, BLENDED with SPEC TARGETS."""
    print(f"📊 Analyzing real data from {real_data_path}")

    with open(real_data_path) as f:
        real_runs = json.load(f)

    if not real_runs:
        print("  ⚠️  No real runs found, using SPEC default priors")
        return _default_real_data_priors()

    df = pd.DataFrame(real_runs)
    print(f"  Found {len(df)} real runs across {df['platform'].nunique()} platforms")

    priors = {}

    # 1. Design tier distribution (from real data)
    def tier_of(name):
        n = name.lower()
        if any(k in n for k in TINY_KW): return "tiny"
        if any(k in n for k in LARGE_KW): return "large"
        return "medium"

    df["tier"] = df["design_name"].apply(tier_of)
    priors["design_tier_probs"] = df["tier"].value_counts(normalize=True).to_dict()
    priors["tier_mu"] = df.groupby("tier")["num_instances"].apply(lambda x: np.log(x).mean()).to_dict()
    priors["tier_sigma"] = df.groupby("tier")["num_instances"].apply(lambda x: np.log(x).std()).fillna(0.8).to_dict()

    # 2. Platform weights: USE SPEC TARGETS (not real data) for generation
    # This ensures we generate balanced data across all 4 platforms
    priors["platform_weights"] = SPEC_TARGETS["platform_weights"].copy()

    # 3. Aspect ratios & margin: from real data (or spec fallback)
    aspect_vals = sorted(df["core_aspect_ratio"].dropna().unique().tolist())
    priors["aspect_ratios"] = aspect_vals if aspect_vals else ASPECT_RATIOS
    margin_vals = df["core_margin"].dropna()
    priors["core_margin_range"] = (int(margin_vals.min()), int(margin_vals.max())) if len(margin_vals) > 0 else (1, 10)
    # Ensure more margin options
    if priors["core_margin_range"][1] - priors["core_margin_range"][0] < 5:
        priors["core_margin_range"] = (1, 10)

    # 4. Utilization by platform: blend real range with spec
    priors["util_by_platform"] = {}
    for platform in PLATFORMS_SPEC.keys():
        if platform in df["platform"].unique():
            sub = df[df["platform"] == platform]
            real_range = (int(sub["core_utilization"].min()), int(sub["core_utilization"].max()))
            spec_range = PLATFORMS_SPEC[platform]["util_range"]
            # Blend: expand real range to cover spec range
            lo = min(real_range[0], spec_range[0])
            hi = max(real_range[1], spec_range[1])
            # Add more granularity
            priors["util_by_platform"][platform] = (lo, hi)
        else:
            priors["util_by_platform"][platform] = PLATFORMS_SPEC[platform]["util_range"]

    # 5. Area & power scaling by platform: blend real + spec
    priors["area_k_by_platform"] = {}
    priors["power_k_by_platform"] = {}
    for platform in PLATFORMS_SPEC.keys():
        spec_k_area = PLATFORMS_SPEC[platform]["k_area"]
        spec_k_pow = PLATFORMS_SPEC[platform]["k_pow"]

        if platform in df["platform"].unique():
            sub = df[df["platform"] == platform]
            valid_area = sub[(sub["num_instances"] > 0) & (sub["final_area_um2"] > 0)]
            if len(valid_area) > 3:
                real_k_area = float(np.median(valid_area["final_area_um2"] / valid_area["num_instances"]))
                # Blend: 70% real, 30% spec
                priors["area_k_by_platform"][platform] = 0.7 * real_k_area + 0.3 * spec_k_area
            else:
                priors["area_k_by_platform"][platform] = spec_k_area

            valid_pow = sub[(sub["final_area_um2"] > 0) & (sub["final_power_mw"] > 0)]
            if len(valid_pow) > 3:
                real_k_pow = float(np.median(valid_pow["final_power_mw"] / (valid_pow["final_area_um2"] ** 0.85)))
                priors["power_k_by_platform"][platform] = 0.7 * real_k_pow + 0.3 * spec_k_pow
            else:
                priors["power_k_by_platform"][platform] = spec_k_pow
        else:
            priors["area_k_by_platform"][platform] = spec_k_area
            priors["power_k_by_platform"][platform] = spec_k_pow

    # 6. Timing bias by platform: blend real mean + spec bias
    priors["timing_bias_by_platform"] = {}
    for platform in PLATFORMS_SPEC.keys():
        spec_bias = PLATFORMS_SPEC[platform]["timing_bias"]
        if platform in df["platform"].unique():
            sub = df[df["platform"] == platform]
            real_bias = float(sub["final_wns_ns"].mean())
            # Blend: 70% real, 30% spec
            priors["timing_bias_by_platform"][platform] = 0.7 * real_bias + 0.3 * spec_bias
        else:
            priors["timing_bias_by_platform"][platform] = spec_bias

    # 7. CORRELATION TARGETS: USE SPEC TARGETS (not real data)
    # This is KEY - we validate against SPEC, not real data correlations
    priors["closure_rate"] = SPEC_TARGETS["closure_rate"]
    priors["drc_clean_rate"] = SPEC_TARGETS["drc_clean_rate"]
    priors["wns_tns_corr"] = 0.9  # Target for generation
    priors["area_power_corr"] = 0.65  # Target for generation
    priors["util_wns_corr"] = -0.5  # Target for generation

    print("  ✅ Blended priors (real data + SPEC targets):")
    for k, v in priors.items():
        if isinstance(v, dict):
            print(f"    {k}: {v}")
        else:
            print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")

    return priors


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def tier_of(name: str) -> str:
    n = name.lower()
    if any(k in n for k in TINY_KW): return "tiny"
    if any(k in n for k in LARGE_KW): return "large"
    return "medium"


def exact_counts(n: int, weights: Dict[str, float]) -> Dict[str, int]:
    """Largest-remainder rounding for exact stratification."""
    raw = {k: n * w for k, w in weights.items()}
    cnt = {k: int(np.floor(v)) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - cnt[k], reverse=True)[: n - sum(cnt.values())]:
        cnt[k] += 1
    return cnt


def trunc_normal(rng, mean, sd, size, low=0.0):
    """Normal truncated to > low."""
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
    """Zero-truncated Poisson."""
    x = rng.poisson(lam, size)
    bad = x == 0
    while bad.any():
        x[bad] = rng.poisson(lam, bad.sum())
        bad = x == 0
    return x


# ─────────────────────────────────────────────────────────────────────────────
# CORE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate(n: int, seed: int, priors: Dict, anchor: datetime | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    anchor = anchor or datetime.now()

    # ── Platform (exact stratification from SPEC TARGETS) ──
    platform_weights = priors.get("platform_weights", SPEC_TARGETS["platform_weights"])
    cnt = exact_counts(n, platform_weights)
    platform = np.concatenate([[p] * c for p, c in cnt.items()])
    rng.shuffle(platform)

    # ── Design names: 60% real, 40% synthetic ──
    pool = REAL_DESIGNS + SYNTHETIC_DESIGNS
    w = np.array([0.6 / len(REAL_DESIGNS)] * len(REAL_DESIGNS) + [0.4 / len(SYNTHETIC_DESIGNS)] * len(SYNTHETIC_DESIGNS))
    design_name = rng.choice(pool, size=n, p=w)

    # ── Design tier & size ──
    tier_probs = priors.get("design_tier_probs", {"tiny": 0.45, "medium": 0.35, "large": 0.20})
    tiers = rng.choice(list(tier_probs.keys()), size=n, p=list(tier_probs.values()))

    tier_mu = priors.get("tier_mu", TIER_MU)
    tier_sigma = priors.get("tier_sigma", TIER_SIGMA)
    # Handle both dict and float for tier_sigma
    if isinstance(tier_sigma, dict):
        mu = np.array([tier_mu.get(t, TIER_MU[t]) for t in tiers])
        sigma = np.array([tier_sigma.get(t, TIER_SIGMA) for t in tiers])
    else:
        mu = np.array([tier_mu.get(t, TIER_MU[t]) for t in tiers])
        sigma = np.full(n, tier_sigma)

    num_inst = np.clip(np.round(np.exp(rng.normal(mu, sigma))), 100, 1_000_000).astype(int)
    # Stronger correlation: num_nets = num_inst * (1.2 ± 0.03)
    num_nets = np.maximum(num_inst, np.round(num_inst * np.clip(rng.normal(1.2, 0.03, n), 1.15, 1.25))).astype(int)
    p_seq = np.clip(rng.normal(0.20, 0.035, n), 0.10, 0.30)
    num_seq = rng.binomial(num_inst, p_seq)
    num_macros = np.minimum(rng.poisson(2, n), 50)
    macro_area_ratio = np.where(num_macros > 0,
                                np.clip(num_macros * rng.uniform(0.01, 0.05, n), 0, 0.6), 0.0).round(4)

    # ── Floorplan config ──
    util = np.zeros(n, int)
    util_by_platform = priors.get("util_by_platform", {p: v["util_range"] for p, v in PLATFORMS_SPEC.items()})
    for p, (lo, hi) in util_by_platform.items():
        m = platform == p
        util[m] = rng.integers(lo, hi + 1, m.sum())

    aspect_ratios = priors.get("aspect_ratios", ASPECT_RATIOS)
    aspect = rng.choice(aspect_ratios, size=n)
    margin_range = priors.get("core_margin_range", (1, 10))
    margin = rng.integers(margin_range[0], margin_range[1] + 1, size=n)

    timing_bias = np.array([priors.get("timing_bias_by_platform", {p: v["timing_bias"] for p, v in PLATFORMS_SPEC.items()}).get(p, 0) for p in platform])

    # ── WNS: exact closure rate from SPEC ──
    closure_rate = priors.get("closure_rate", SPEC_TARGETS["closure_rate"])
    n_pos = int(round(closure_rate * n))

    marg = np.concatenate([
        trunc_normal(rng, 20, 15, n_pos, low=0.0),
        -trunc_normal(rng, 50, 30, n - n_pos, low=0.0),
    ])
    marg = np.where(marg >= 0, np.round(marg, 2), np.minimum(np.round(marg, 2), -0.01))
    marg = np.sort(marg)[::-1]

    # Latent "goodness" correlated with utilization (target util_wns_corr = -0.5)
    target_corr = priors.get("util_wns_corr", -0.5)
    z_util = zscore(util)
    z_noise = rng.standard_normal(n)
    # Weight to achieve target correlation
    weight = target_corr / np.corrcoef(z_util, -z_util)[0, 1] if np.corrcoef(z_util, -z_util)[0, 1] != 0 else 1.0
    weight = np.clip(weight, -1, 1)
    score = weight * (-z_util) + np.sqrt(max(0, 1 - weight**2)) * z_noise

    wns = np.empty(n)
    wns[np.argsort(-score)] = marg
    closure = (wns >= 0).astype(int)

    # ── TNS: correlated with WNS (target wns_tns_corr = 0.9) ──
    target_wns_tns = priors.get("wns_tns_corr", 0.9)
    base_tns = wns * 10 * np.exp(rng.normal(0, 0.30, n))
    tns = np.where(closure == 1, 0.0, base_tns)
    tns = np.minimum(np.round(tns, 2), 0.0)

    # Adjust correlation if needed
    actual_corr = np.corrcoef(wns[closure==0], tns[closure==0])[0, 1] if (closure==0).sum() > 10 else 1.0
    if actual_corr < target_wns_tns * 0.95:
        noise_scale = np.sqrt(max(0, 1 - target_wns_tns**2))
        tns_corr = wns * 10 * target_wns_tns + rng.normal(0, noise_scale * 100, n)
        tns = np.where(closure == 1, 0.0, np.minimum(np.round(tns_corr, 2), 0.0))

    # ── Area: log-linear in instances ──
    area_k = np.array([priors.get("area_k_by_platform", {p: v["k_area"] for p, v in PLATFORMS_SPEC.items()}).get(p, 30) for p in platform])
    area = num_inst * area_k * np.exp(rng.normal(0, 0.12, n)) * (1 + macro_area_ratio)
    area = np.maximum(np.round(area, 2), 2.3)

    # ── Power: sub-linear in area ──
    power_k = np.array([priors.get("power_k_by_platform", {p: v["k_pow"] for p, v in PLATFORMS_SPEC.items()}).get(p, 0.003) for p in platform])
    target_area_power = priors.get("area_power_corr", 0.65)
    power = power_k * area ** 0.85 * np.exp(rng.normal(0, 0.75, n))
    power = np.maximum(np.round(power, 3), 0.007)

    # Adjust area-power correlation
    actual_ap_corr = np.corrcoef(area, power)[0, 1]
    if abs(actual_ap_corr - target_area_power) > 0.05:
        z_area = zscore(np.log1p(area))
        z_power = zscore(np.log1p(power))
        rho = target_area_power
        z_power_new = rho * z_area + np.sqrt(max(0, 1 - rho**2)) * z_power
        power = np.exp(z_power_new * np.std(np.log1p(power)) + np.mean(np.log1p(power))) - 1
        power = np.maximum(np.round(power, 3), 0.007)

    # ── DRC: exact clean rate from SPEC ──
    drc_clean_rate = priors.get("drc_clean_rate", SPEC_TARGETS["drc_clean_rate"])
    n_dirty = int(round((1 - drc_clean_rate) * n))
    wdrc = np.where(closure == 1, 0.05, 0.19) * np.exp(0.25 * zscore(util))
    wdrc = wdrc / wdrc.sum()
    dirty_idx = rng.choice(n, size=n_dirty, replace=False, p=wdrc)
    drc = np.zeros(n, int)
    drc[dirty_idx] = zt_poisson(rng, 5, n_dirty)
    drc_clean = (drc == 0).astype(int)
    lvs_clean = drc_clean.copy()

    # ── Runtime ──
    runtime = np.clip(num_inst * 0.03 * (1 + util / 100) * np.exp(rng.normal(0, 0.35, n)), 5, 20000).round(2)

    # ── Identifiers ──
    ts = [(anchor - timedelta(seconds=float(s))).isoformat() for s in rng.uniform(0, 365 * 86400, n)]
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


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION (Against SPEC TARGETS)
# ─────────────────────────────────────────────────────────────────────────────
def validate(df: pd.DataFrame, n: int, aspect_ratios: List[float] = None) -> Tuple[List[str], Dict]:
    fails, stats = [], {}

    def check(name, ok, val=None):
        stats[name] = val
        if not ok:
            fails.append(f"{name} = {val}")

    check("rows", len(df) == n, len(df))
    check("columns", df.shape[1] == 35, df.shape[1])

    tc, dc = df.timing_closure_bin.mean(), df.drc_clean_bin.mean()
    check("timing_closure_mean", abs(tc - SPEC_TARGETS["closure_rate"]) < 0.02, round(tc, 4))
    check("drc_clean_mean", abs(dc - SPEC_TARGETS["drc_clean_rate"]) < 0.02, round(dc, 4))

    mix = df.platform.value_counts(normalize=True).round(2).to_dict()
    check("platform_mix", mix == SPEC_TARGETS["platform_weights"], mix)

    c = {
        "wns_tns": df.final_wns_ns.corr(df.final_tns_ns),
        "inst_area": df.num_instances.corr(df.final_area_um2),
        "area_power": df.final_area_um2.corr(df.final_power_mw),
        "util_wns": df.core_utilization.corr(df.final_wns_ns),
        "drc_vs_closure": df.final_drc_violations.corr(df.timing_closure_bin),
        "wns_vs_closure": df.final_wns_ns.corr(df.timing_closure_bin),
    }
    stats.update({f"corr_{k}": round(v, 3) for k, v in c.items()})
    check("corr_wns_tns>0.85", c["wns_tns"] > SPEC_TARGETS["wns_tns_corr_min"], round(c["wns_tns"], 3))
    check("corr_inst_area>0.85", c["inst_area"] > 0.85, round(c["inst_area"], 3))
    check("corr_area_power in [0.55,0.75]", SPEC_TARGETS["area_power_corr_range"][0] <= c["area_power"] <= SPEC_TARGETS["area_power_corr_range"][1], round(c["area_power"], 3))
    check("corr_util_wns in [-0.6,-0.4]", SPEC_TARGETS["util_wns_corr_range"][0] <= c["util_wns"] <= SPEC_TARGETS["util_wns_corr_range"][1], round(c["util_wns"], 3))
    check("corr_drc_vs_closure < 0", c["drc_vs_closure"] < 0, round(c["drc_vs_closure"], 3))

    check("closure<=>WNS>=0", bool((df.timing_closure_bin == (df.final_wns_ns >= 0)).all()))
    check("drc_clean<=>DRC==0", bool((df.drc_clean_bin == (df.final_drc_violations == 0)).all()))
    check("lvs<=drc", bool((df.lvs_clean_bin <= df.drc_clean_bin).all()))
    check("nets>=instances", bool((df.num_nets >= df.num_instances).all()))
    check("seq<=instances", bool((df.num_sequential <= df.num_instances).all()))
    check("util in [10,80]", bool(df.core_utilization.between(10, 80).all()))
    check("aspect discrete", bool(df.core_aspect_ratio.isin(aspect_ratios or ASPECT_RATIOS).all()))
    check("no nulls", int(df.isna().sum().sum()) == 0)
    check("run_id unique", df.run_id.is_unique)

    return fails, stats


# ─────────────────────────────────────────────────────────────────────────────
# SPLITS & EXPORT
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", type=Path, default=Path("dataset_genration/output"))
    ap.add_argument("--real-data", type=Path, help="Path to real ORFS runs JSON from collect_real_data.py")
    ap.add_argument("--max-attempts", type=int, default=25)
    args = ap.parse_args()

    # Learn priors from real data (BLENDED with SPEC targets)
    if args.real_data and args.real_data.exists():
        priors = analyze_real_data(str(args.real_data))
    else:
        print("⚠️  No real data provided, using SPEC default priors")
        priors = _default_real_data_priors()

    anchor = datetime.now()
    allowed_aspects = priors.get("aspect_ratios", ASPECT_RATIOS)
    for attempt in range(args.max_attempts):
        seed = args.seed + attempt
        df = generate(args.rows, seed, priors, anchor)
        fails, stats = validate(df, args.rows, allowed_aspects)
        if not fails:
            break
        print(f"attempt {attempt + 1} (seed {seed}) failed: {fails}")
    else:
        sys.exit("Could not satisfy all validation checks; see failures above.")

    print(f"\n✅ All validation checks passed (seed {seed}).")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    export(df, args.outdir, seed)
    print(f"\n📁 Wrote files to {args.outdir.resolve()}")


if __name__ == "__main__":
    main()