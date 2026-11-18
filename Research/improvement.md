# Improvement Checklist for OpenRoad-GUI Paper

*Generated from peer review analysis*

---

## Required for Acceptance

### 1. Complete PPO Validation on Real ORFS Runs with Baselines
- [ ] Run PPO-optimized flows on real ORFS executions
- [ ] Compare against: (a) default ORFS parameters, (b) expert-tuned parameters, (c) Bayesian optimization baseline
- [ ] Test on multiple designs (≥5) and PDKs
- [ ] Report: WNS, TNS, Area, Power, DRC, runtime for each

### 2. Clarify Test Set Composition; Report Per-Design Results
- [ ] Explicitly enumerate which design(s) constitute the GroupKFold hold-out test set
- [ ] Report per-design R², RMSE, MAE for all 4 surrogate targets
- [ ] Report per-design AUC, Precision, Recall, F1 for both classifiers
- [ ] State whether test designs were used in ANY model selection

### 3. Document Synthetic Data Generation or Remove Reliance
- [ ] **Option A**: Document synthetic data generation method for failure predictor (3000 samples)
  - [ ] Generation algorithm/code
  - [ ] Distribution parameters
  - [ ] Validation that synthetic data matches real failure distribution
- [ ] **Option B**: Retrain failure predictor on real data only (175 runs) and report results
- [ ] Remove "Trained on 3000 Samples" claim if synthetic data not released

### 4. Add Statistical Rigor
- [ ] **Confidence Intervals**: Bootstrap 95% CIs for all R², AUC, RMSE, MAE metrics
- [ ] **Significance Tests**: Paired t-tests / Wilcoxon for ensemble vs single-model comparisons
- [ ] **Ablation Studies**:
  - [ ] Ensemble vs LightGBM-only vs MLP-only (all targets)
  - [ ] Calibration on/off (Brier Score, ECE, Reliability Index)
  - [ ] Feature importance impact (top-k features only)
  - [ ] Log-scale vs raw-scale targets
  - [ ] PPO: heuristic-only vs heuristic+PPO residual (α=0.1, 0.2)

### 5. Provide Exact Equations and Seeds
- [ ] **Reward Function**: Complete mathematical formulation with normalization, tanh scaling, terminal bonuses
- [ ] **Normalization**: Exact specification for WNS/TNS clipping + scaling (min-max? z-score? per-design?)
- [ ] **Random Seeds**: All seeds for data splits, LightGBM, MLP init, PPO training, synthetic data gen
- [ ] **Hyperparameters**: Complete tables for all models (already mostly present)

### 6. Fix DRC-Clean AUC Interpretation or Improve Method
- [ ] **Interpretation Fix**: Explicitly state: "With only 32 clean samples (18.3%), AUC=0.520 indicates the classifier cannot reliably distinguish clean vs violating designs. This metric is reported for transparency but should not be used for production decisions."
- [ ] **Improvement Options** (choose ≥1):
  - [ ] Stage-specific DRC prediction (post-placement, post-route, sign-off)
  - [ ] Additional features: congestion maps, routing layer utilization, density gradients
  - [ ] Anomaly detection framing (one-class SVM, isolation forest on violating designs)
  - [ ] Focal loss / class-balanced loss for LightGBM
  - [ ] Collect more clean samples via relaxed DRC rules or larger designs

### 7. Resolve PPO Iteration Count Discrepancy
- [ ] **Section 5.4.1 (line 596)**: "500K timesteps" → Update to match actual
- [ ] **Section 5.4.3 (line 800)**: "2000 training iterations completed" → Clarify relationship
- [ ] State: "PPO trained for 2000 iterations (≈X timesteps at batch size Y, n_steps Z)"
- [ ] Or: "PPO trained for 500K timesteps (2000 iterations at 250 timesteps/iteration)"

---

## Additional Recommended Improvements

### 8. Per-Design Analysis
- [ ] Table: Each of 9 designs × 4 PDKs = 36 combos; show which have data
- [ ] Sky130hd 0% timing closure: analyze why (feature distribution? PDK limitations?)

### 9. Compute Requirements Documentation
- [ ] Training: GPU type, hours, memory for each model
- [ ] Inference: Production server specs (Linux x86), not just Apple M2

### 10. ORFS Version Pinning
- [ ] Exact ORFS commit hash / release version used for all 175 runs

### 11. Synthetic Data Release (if used)
- [ ] Release generation code + generated dataset for reproducibility

### 12. PPO Action Space Validation
- [ ] Verify all 14 actions map to valid ORFS parameter ranges
- [ ] Test categorical action rounding/clipping doesn't produce invalid configs

---

## Tracking

| Item | Status | Owner | Target Date |
|------|--------|-------|-------------|
| 1. PPO Validation | ⬜ Not Started | | |
| 2. Test Set Clarity | ⬜ Not Started | | |
| 3. Synthetic Data | ⬜ Not Started | | |
| 4. Statistical Rigor | ⬜ Not Started | | |
| 5. Equations/Seeds | ⬜ Not Started | | |
| 6. DRC-Clean Fix | ⬜ Not Started | | |
| 7. PPO Iteration Count | ⬜ Not Started | | |
| 8. Per-Design Analysis | ⬜ Not Started | | |
| 9. Compute Docs | ⬜ Not Started | | |
| 10. ORFS Version | ⬜ Not Started | | |
| 11. Synthetic Data Release | ⬜ Not Started | | |
| 12. PPO Action Validation | ⬜ Not Started | | |

---

## Notes

- Priority order: 1, 2, 3, 4, 5, 6, 7 (matching reviewer requirements)
- Items 8-12 are recommended but not strictly required for acceptance
- Update this checklist as items are completed
- Target: All Required items (1-7) complete before next submission

---

*Last updated: 2026-11-18*
*Source: Manual peer review (5 perspectives: Journal-Fit, Methodology, Domain, Perspective, Devil's Advocate)*