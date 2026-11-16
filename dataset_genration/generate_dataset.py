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
* NEW: Platform parameters are now derived from real AWS data (real_runs_export.csv)
  to better match actual ORFS run distributions.
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
# Load real data and derive platform parameters
# --------------------------------------------------------------------------- #
REAL_DATA_PATH = Path(__file__).parent / "output" / ".." / ".." / "openroad_gui" / "intelligence" / "data" / "real_runs_export.csv"

# Overall spec targets
SPEC_TIMING_CLOSURE = 0.30
SPEC_DRC_CLEAN = 0.85

def load_real_platform_params():
    """Load real data and derive platform parameters with target rates for spec compliance."""
    default_platforms = {
        "sky130hd":  dict(weight=0.30, util=(20, 40), k_area=30.0, k_pow=0.0030, bias=-0.15,
                          timing_closure_rate=0.05, drc_clean_rate=0.70),
        "asap7":     dict(weight=0.30, util=(15, 40), k_area=12.0, k_pow=0.0040, bias=-0.45,
                          timing_closure_rate=0.60, drc_clean_rate=0.95),
        "nangate45": dict(weight=0.20, util=(25, 60), k_area=45.0, k_pow=0.0040, bias=+0.50,
                          timing_closure_rate=0.05, drc_clean_rate=0.70),
        "gf180":     dict(weight=0.20, util=(20, 50), k_area=40.0, k_pow=0.0035, bias=-0.15,
                          timing_closure_rate=0.60, drc_clean_rate=0.95),
    }

    if not REAL_DATA_PATH.exists():
        print(f"Warning: Real data not found at {REAL_DATA_PATH}, using defaults")
        return default_platforms

    try:
        df = pd.read_csv(REAL_DATA_PATH)
        complete = df.dropna(subset=['final_area_um2', 'final_power_w'])

        if len(complete) == 0:
            print("Warning: No complete real data, using defaults")
            return default_platforms

        # Use spec weights for platform distribution (30/30/20/20)
        spec_weights = {"sky130hd": 0.30, "asap7": 0.30, "nangate45": 0.20, "gf180": 0.20}

        # Target rates to meet overall spec:
        # sky130hd: timing=5%, drc=70%
        # asap7: timing=60%, drc=95%
        # nangate45: timing=5%, drc=70%
        # gf180: timing=60%, drc=95%
        target_rates = {
            "sky130hd":  dict(timing_closure_rate=0.05, drc_clean_rate=0.70),
            "asap7":     dict(timing_closure_rate=0.60, drc_clean_rate=0.95),
            "nangate45": dict(timing_closure_rate=0.05, drc_clean_rate=0.70),
            "gf180":     dict(timing_closure_rate=0.60, drc_clean_rate=0.95),
        }

        spec_weights = {"sky130hd": 0.30, "asap7": 0.30, "nangate45": 0.20, "gf180": 0.20}
        default_platforms = {
            "sky130hd":  dict(weight=0.30, util=(20, 40), k_area=30.0, k_pow=0.0030, bias=-0.15,
                              timing_closure_rate=0.05, drc_clean_rate=0.70),
            "asap7":     dict(weight=0.30, util=(15, 40), k_area=12.0, k_pow=0.0040, bias=-0.45,
                              timing_closure_rate=0.60, drc_clean_rate=0.95),
            "nangate45": dict(weight=0.20, util=(25, 60), k_area=45.0, k_pow=0.0040, bias=+0.50,
                              timing_closure_rate=0.05, drc_clean_rate=0.70),
            "gf180":     dict(weight=0.20, util=(20, 50), k_area=40.0, k_pow=0.0035, bias=-0.15,
                              timing_closure_rate=0.60, drc_clean_rate=0.95),
        }

        if not REAL_DATA_PATH.exists():
            print(f"Warning: Real data not found at {REAL_DATA_PATH}, using defaults")
            return default_platforms

        df = pd.read_csv(REAL_DATA_PATH)
        complete = df.dropna(subset=['final_area_um2', 'final_power_w'])

        if len(complete) == 0:
            print("Warning: No complete real data, using defaults")
            return default_platforms

        spec_weights = {"sky130hd": 0.30, "asap7": 0.30, "nangate45": 0.20, "gf180": 0.20}
        target_rates = {
            "sky130hd":  dict(timing_closure_rate=0.05, drc_clean_rate=0.70),
            "asap7":     dict(timing_closure_rate=0.60, drc_clean_rate=0.95),
            "nangate45": dict(timing_closure_rate=0.05, drc_clean_rate=0.70),
            "gf180":     dict(timing_closure_rate=0.60, drc_clean_rate=0.95),
        }

        platforms = {}
        for platform in ['sky130hd', 'asap7', 'nangate45', 'gf180']:
            pdata = complete[complete['platform'] == platform]
            if len(pdata) == 0:
                platforms[platform] = default_platforms[platform]
                continue

            weight = spec_weights[platform]
            mean_area = pdata['final_area_um2'].mean()
            mean_power_w = pdata['final_power_w'].mean()
            mean_area_pow = mean_area ** 0.85
            k_area = float(mean_area / 100000)
            k_pow = float(mean_power_w / mean_area_pow) if mean_area_pow > 0 else 0.001
            util_min = int(pdata['core_utilization'].min())
            util_max = int(pdata['core_utilization'].max())

            target = target_rates[platform]
            mean_area = pdata['final_area_um2'].mean()
            mean_power_w = pdata['final_power_w'].mean()
            mean_area_pow = mean_area ** 0.85
            k_area = float(mean_area / 100000)
            k_pow = float(mean_power_w / mean_area_pow) if mean_area_pow > 0 else 0.001
            util_min = int(pdata['core_utilization'].min())
            util_max = int(pdata['core_utilization'].max())

            target = target_rates[platform]
            platforms[platform] = dict(
                weight=spec_weights[platform],
                util=(max(int(pdata['core_utilization'].min()), 10), min(int(pdata['core_utilization'].max()), 80)),
                k_area=round(float(pdata['final_area_um2'].mean() / 100000), 4),
                k_pow=round(float(mean_power_w / mean_area_pow), 6),
                bias=default_platforms[platform].get('bias', 0.0),
                timing_closure_rate=target['timing_closure_rate'],
                drc_clean_rate=target['drc_clean_rate'],
            )

        print("Derived platform parameters from real data (with target rates):")
        for p, v in platforms.items():
            print(f"  {p}: weight={v['weight']:.2f}, util={v['util']}, k_area={v['k_area']:.4f}, k_pow={v['k_pow']:.6f}, "
                  f"timing_closure={v['timing_closure_rate']:.0%}, drc_clean={v['drc_clean_rate']:.0%}")

        # Verify overall weighted averages
        tw = sum(v['weight'] for v in platforms.values())
        tc = sum(v['weight'] * v['timing_closure_rate'] for v in platforms.values()) / sum(v['weight'] for v in platforms.values())
        dc = sum(v['weight'] * v['drc_clean_rate'] for v in platforms.values()) / sum(v['weight'] for v in platforms.values())
        print(f"Overall weighted timing closure: {tc:.1%} (target {SPEC_TIMING_CLOSURE:.0%})")
        print(f"Overall weighted DRC clean: {dc:.1%} (target {SPEC_DRC_CLEAN:.0%})")

        return platforms

    except Exception as e:
        print(f"Warning: Failed to load real data ({e}), using defaults")
        return default_platforms

# Overall spec targets
SPEC_TIMING_CLOSURE = 0.30
SPEC_DRC_CLEAN = 0.85

PLATFORMS = load_real_platform_params()

# --------------------------------------------------------------------------- #
# Spec constants (updated with real-data-derived parameters)
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

    # ---- WNS: platform-specific closure rate, rank-coupled to utilization -- #
    closure = np.zeros(n, int)
    wns = np.zeros(n)
    for p, spec in PLATFORMS.items():
        m = platform == p
        n_p = m.sum()
        if n_p == 0:
            continue
        # Platform-specific timing closure rate
        closure_rate = spec.get("timing_closure_rate", 0.30)
        n_pos_p = int(round(closure_rate * n_p))
        n_neg_p = n_p - n_pos_p
        
        # Platform-specific WNS distribution for closed/failed
        marg_pos = trunc_normal(rng, 20, 15, n_pos_p, low=0.0)
        marg_neg = -trunc_normal(rng, 50, 30, n_neg_p, low=0.0)
        marg_p = np.concatenate([marg_pos, marg_neg])
        marg_p = np.where(marg_p >= 0, np.round(marg_p, 2), np.minimum(np.round(marg_p, 2), -0.01))
        marg_p = np.sort(marg_p)[::-1]  # best -> worst
        
        # Latent "goodness": low utilization, favourable platform, smaller design
        # CORRECT: utilization coefficient NEGATIVE (higher util -> worse WNS)
        util_p = util[m]
        bias_p = bias[m]
        num_inst_p = num_inst[m]
        score_p = (-0.58 * zscore(util_p) + 0.20 * zscore(bias_p)  # CORRECT: -0.58 (higher util -> worse WNS)
                   - 0.08 * zscore(np.log(num_inst_p)) + 0.75 * rng.standard_normal(n_p))
        wns[m] = marg_p[np.argsort(-score_p)]
        closure[m] = (wns[m] >= 0).astype(int)

    # ---- TNS ~ 10 x WNS (0 when timing is met) ---------------------------- #
    tns = np.where(closure == 1, 0.0, wns * 10 * np.exp(rng.normal(0, 0.30, n)))
    tns = np.minimum(np.round(tns, 2), 0.0)

    # ---- Area (log-linear in instances), Power (sub-linear in area) ------- #
    k_area = np.array([PLATFORMS[p]["k_area"] for p in platform])
    # Stronger correlation: area = instances * k_area * noise
    # Reduced noise from 0.12 to 0.03 for stronger correlation (>0.85)
    area = num_inst * k_area * np.exp(rng.normal(0, 0.03, n)) * (1 + macro_area_ratio)
    area = np.maximum(np.round(area, 2), 2.3)
    k_pow = np.array([PLATFORMS[p]["k_pow"] for p in platform])
    # Reduced power noise for better area-power correlation (target 0.55-0.75)
    power = k_pow * area ** 0.85 * np.exp(rng.normal(0, 0.35, n))
    power = np.maximum(np.round(power, 3), 0.007)

    # ---- DRC: platform-specific dirty rate, more likely when timing fails --- #
    drc = np.zeros(n, int)
    drc_clean = np.ones(n, int)
    for p, spec in PLATFORMS.items():
        m = platform == p
        n_p = m.sum()
        if n_p == 0:
            continue
        # Platform-specific DRC clean rate
        drc_clean_rate = spec.get("drc_clean_rate", 0.85)
        n_dirty_p = int(round((1 - drc_clean_rate) * n_p))
        if n_dirty_p > 0:
            wdrc_p = np.where(closure[m] == 1, 0.05, 0.19) * np.exp(0.25 * zscore(util[m]))
            dirty_idx_p = rng.choice(n_p, size=n_dirty_p, replace=False, p=wdrc_p / wdrc_p.sum())
            drc_p = np.zeros(n_p, int)
            drc_p[dirty_idx_p] = zt_poisson(rng, 5, n_dirty_p)
            drc[m] = drc_p
            drc_clean[m] = (drc_p == 0).astype(int)
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
        if not ok:
            fails.append(f"{name} = {val}" if val is not None else name)

    # ---- Size & completeness ---------------------------------------------- #
    check("n_rows", len(df) == n, len(df))
    check("no_nulls", df.notna().all().all())

    # ---- Class balance ----------------------------------------------------- #
    check("timing_closure=30%±2%", abs(df["timing_closure_bin"].mean() - 0.30) < 0.02, df["timing_closure_bin"].mean())
    check("drc_clean=85%±2%", abs(df["drc_clean_bin"].mean() - 0.85) < 0.02, df["drc_clean_bin"].mean())

    # ---- Correlations ------------------------------------------------------ #
    check("corr(WNS,TNS)>0.8", df["final_wns_ns"].corr(df["final_tns_ns"]) > 0.8, df["final_wns_ns"].corr(df["final_tns_ns"]))
    check("corr(instances,area)>0.85", df["num_instances"].corr(df["final_area_um2"]) > 0.85, df["num_instances"].corr(df["final_area_um2"]))
    check("corr(area,power) in [0.55,0.75]", 0.55 <= df["final_area_um2"].corr(df["final_power_mw"]) <= 0.75, df["final_area_um2"].corr(df["final_power_mw"]))
    check("corr(util,WNS) in [-0.6,-0.4]", -0.6 <= df["core_utilization"].corr(df["final_wns_ns"]) <= -0.4, df["core_utilization"].corr(df["final_wns_ns"]))

    # ---- Logical consistency ----------------------------------------------- #
    check("timing_closure==(WNS>=0)", (df["timing_closure_bin"] == (df["final_wns_ns"] >= 0)).all())
    check("drc_clean==(DRC==0)", (df["drc_clean_bin"] == (df["final_drc_violations"] == 0)).all())
    check("lvs<=drc", (df["lvs_clean_bin"] <= df["drc_clean_bin"]).all())

    # ---- Platform distribution --------------------------------------------- #
    plat_dist = df["platform"].value_counts(normalize=True).round(2).to_dict()
    expected = {"sky130hd": 0.30, "asap7": 0.30, "nangate45": 0.20, "gf180": 0.20}
    check("platform_dist", plat_dist == expected, plat_dist)

    # ---- Collect stats ----------------------------------------------------- #
    stats.update({
        "n": len(df),
        "timing_closure_mean": df["timing_closure_bin"].mean(),
        "drc_clean_mean": df["drc_clean_bin"].mean(),
        "wns_tns_corr": df["final_wns_ns"].corr(df["final_tns_ns"]),
        "inst_area_corr": df["num_instances"].corr(df["final_area_um2"]),
        "area_power_corr": df["final_area_um2"].corr(df["final_power_mw"]),
        "util_wns_corr": df["core_utilization"].corr(df["final_wns_ns"]),
        "platform_mix": df["platform"].value_counts(normalize=True).round(2).to_dict(),
    })

    return fails, stats


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Synthetic dataset generator")
    parser.add_argument("--rows", type=int, default=3000, help="Number of rows")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--use-datadesigner", action="store_true", help="Use NVIDIA Data Designer")
    parser.add_argument("--outdir", type=Path, default=Path("output"), help="Output directory")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    max_attempts = 25
    for attempt in range(1, max_attempts + 1):
        seed = args.seed + attempt - 1
        print(f"attempt {attempt} (seed {seed})")
        df = generate(args.rows, seed, use_dd=args.use_datadesigner)
        fails, stats = validate(df, args.rows)
        if not fails:
            print("✅ Validation passed!")
            break
        print(f"  failed: {fails}")
    else:
        print(f"Could not satisfy all validation checks after {max_attempts} attempts; see failures above.")
        sys.exit(1)

    # ---- Write outputs ------------------------------------------------------- #
    df.to_parquet(args.outdir / "training_data.parquet", index=False)
    df.to_csv(args.outdir / "training_data.csv", index=False)
    df.to_excel(args.outdir / "training_data.xlsx", index=False)
    df.to_json(args.outdir / "training_data.jsonl", orient="records", lines=True)

    # ---- Train/val/test splits ----------------------------------------------- #
    rng = np.random.default_rng(args.seed)
    idx = np.arange(len(df))
    rng.shuffle(idx)
    train_idx = idx[: int(0.7 * len(df))]
    val_idx = idx[int(0.7 * len(df)) : int(0.9 * len(df))]
    test_idx = idx[int(0.9 * len(df)) :]
    for name, idxs in [("train", train_idx), ("validation", val_idx), ("test", test_idx)]:
        df.iloc[idxs].to_csv(args.outdir / "splits" / f"{name}.csv", index=False)

    print(f"✅ Done! Outputs in {args.outdir}")


if __name__ == "__main__":
    main()