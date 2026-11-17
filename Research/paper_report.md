# Detailed Proofreading and Technical Review Report

**Manuscript:** *OpenRoad-GUI: An ML-Enhanced EDA Workstation for RTL-to-GDSII Physical Design with Surrogate Modeling, Failure Prediction, and Reinforcement Learning-Based Flow Optimization*  
**Document reviewed:** 10-page PDF  
**Review scope:** Technical consistency, machine-learning methodology, experimental results, literature review and references, academic writing, figures/tables, and PDF layout.

---

## 1. Overall assessment

The manuscript presents a promising systems-oriented contribution: an OpenROAD Flow Scripts (ORFS)-based desktop workstation that brings together PPA surrogate modeling, failure prediction, and a preliminary PPO-based flow optimizer. The integration of ML workflows with an engineer-facing GUI is a clear strength.

The current manuscript is **not ready for submission**. Several issues affect the technical credibility and reproducibility of the results, not just grammar or presentation. In particular:

1. The dataset is described as containing five designs, while six design names are listed elsewhere.
2. The DRC-clean class prevalence is inconsistent between the dataset statistics and classifier description.
3. The surrogate-model tables and abstract do not consistently identify which model produced the reported R² values.
4. PPO is described as an optimization capability even though training is reported as in progress and the current surrogate does not accept flow parameters as inputs.
5. The stated PPO state and action dimensions do not match the listed component dimensions.
6. A claim about FastTuner appears to mischaracterize its parameter-aware surrogate.
7. Figure 7's caption does not match the plotted content.
8. Several references and citation placeholders need correction.
9. The appendix and final-page layout need cleanup.

**Recommended revision order:** resolve dataset and model-result discrepancies first; correct the PPO claims and dimensions next; then repair the literature review, references, figures, appendix, and language.

## 2. Critical technical and factual inconsistencies

### 2.1 Number of designs is inconsistent

**Locations:** Page 1, Abstract; Page 5, Table IV.

The abstract says that the 175 ORFS runs cover five designs:

- riscv32i
- jpeg
- aes
- gcd
- uart-blocks

Table IV lists six names while still stating that there are five designs. The additional name is `picorv32`.

**Required action:** Recompute the number of unique designs from the underlying dataset. If there are five, remove the extra name from Table IV. If there are six, update the abstract and every other description of the dataset. Also verify the number of distinct design groups used by GroupKFold.

### 2.2 DRC-clean prevalence conflicts with the dataset statistics

**Locations:** Page 4, Section V-C; Page 5, Table IV.

The failure-predictor section defines DRC Clean as `DRC violations = 0` and gives a positive rate of approximately 85%. Table IV reports a DRC-clean rate of approximately 20%.

These figures cannot both describe the same set of samples under the same label definition. The reported class weights `{0: 5.67, 1: 1.0}` also appear consistent with class 0 being the minority and class 1 the majority, but the exact mapping must be verified.

**Required action:** Recompute, from the dataset, the total number of samples with valid DRC labels, clean samples, violating samples, positive-class percentage, and class weights. Report the denominators explicitly. Check whether the 20% figure is actually a violation rate or whether the classifier's positive-label definition differs from the table's definition. Report class distributions separately for training, validation, and test partitions.

This issue affects the interpretation of the classifier, its class weights, and the reported classification metrics.

### 2.3 Surrogate-model results are ambiguous and inconsistent

**Locations:** Page 1, Abstract; Page 6, Tables VI and VII; Page 8, Conclusion.

The abstract reports Area R² = 0.989, Power R² = 0.952, and WNS R² = 0.665. Table VI reports the following cross-validation values:

| Target | LightGBM R² | MLP R² |
|---|---:|---:|
| WNS | 0.8522 | 0.3456 |
| TNS | 0.8541 | 0.3437 |
| Area | 0.9964 | 0.9655 |
| Power | 0.9792 | 0.9034 |

The `Ensemble` row contains values 0.6652 and 0.6657, but it does not clearly identify which target or metric those values represent. It is therefore not possible to determine whether the table supports the abstract's results or the claim that the ensemble consistently improves performance.

Table VII reports held-out test performance:

| Target | Test R² | Test RMSE | MAPE |
|---|---:|---:|---:|
| WNS | 0.623 | 1.12 ns | 18.4% |
| TNS | 0.618 | 15.2 ns | 22.1% |
| Area | 0.981 | 1,580 µm² | 3.2% |
| Power | 0.934 | 0.52 mW | 4.8% |

**Required action:** Rebuild Table VI with separate columns for LightGBM, MLP, and Ensemble for every target, including the corresponding RMSE (and any other reported metric). State clearly whether each row reports cross-validation, validation, or held-out test results. Align the abstract and conclusion with the verified results. Explain how the claimed 45% reduction in WNS prediction error was calculated, including the baseline, error metric, and evaluation split.

**Metric concern:** MAPE is problematic for WNS and TNS when target values can be negative or close to zero. Prefer MAE and RMSE, and use a clearly defined normalized error measure only where appropriate.

### 2.4 PPO optimization is described more strongly than the evidence supports

**Locations:** Pages 1, 4, 6, 7, and 8.

The abstract describes autonomous flow parameter optimization across 16 continuous action dimensions. Page 6 states that PPO training is in progress at 200K of 500K timesteps. Page 7 also acknowledges that the PPO environment uses the surrogate as a reward source, but the surrogate does not accept flow parameters as inputs.

This is an important limitation. A surrogate that predicts outcomes only from design-level features cannot, by itself, estimate how changing a candidate flow configuration changes PPA. Without parameter-conditioned predictions or real ORFS evaluations, the agent's reward may not reflect the effect of its actions.

**Required action:** Distinguish clearly between implemented integration, ongoing training, and experimentally validated optimization. Until the agent has been evaluated with an action-sensitive reward and reported outcomes, describe PPO as a preliminary or under-development framework. Do not imply that successful autonomous PPA optimization has already been demonstrated.

Suggested wording:

> A preliminary PPO-based flow-optimization framework is integrated into the workstation. Further work is required to establish a parameter-conditioned surrogate-to-optimizer feedback loop and to validate optimization performance through ORFS executions.

### 2.5 FastTuner is potentially mischaracterized

**Location:** Page 3, Table II.

The manuscript says that FastTuner uses offline surrogates for RL reward but that these surrogates do not accept flow parameters as inputs, thereby breaking the RL loop. This is a high-impact claim because it is used to motivate the research gap. FastTuner's method should be checked against its original paper before this statement is retained; its described framework uses design information together with parameter information in its PPA estimator.

**Required action:** Re-read the original FastTuner paper and revise the comparison. A more defensible distinction may be the difference between FastTuner's GNN-based representation and parameter-aware estimator, and OpenRoad-GUI's current handcrafted features, ORFS-native data collection, and GUI integration. Describe the limitation of OpenRoad-GUI's own surrogate accurately rather than attributing it to FastTuner without evidence.

### 2.6 PPO state-space dimensions do not add up

**Location:** Page 4, Section V-D.

The stated 128-dimensional state contains these listed components:

| Component | Listed dimensions |
|---|---:|
| Design features | 12 |
| Platform one-hot encoding | 4 |
| Current-stage features | 14 |
| Stage history (3 × 6) | 18 |
| **Total listed** | **48** |

The listed dimensions add to 48, not 128. The current-stage description also names seven metrics while claiming 14 features.

**Required action:** Explain the additional 80 dimensions or correct the claimed state dimension. Give a complete, reproducible state-vector specification, including ordering, encoding, normalization, padding, and handling of unavailable stage metrics.

### 2.7 PPO action-space dimensions do not add up

**Location:** Page 4, Section V-D.

The listed action dimensions sum to 14:

| Stage | Listed dimensions |
|---|---:|
| Synthesis | 4 |
| Floorplan | 3 |
| CTS | 3 |
| Routing | 3 |
| Signoff | 1 |
| **Total listed** | **14** |

The manuscript claims 16 continuous action dimensions. In addition, parameters such as strategy, effort, buffer type, and macro placement may be categorical or discrete rather than continuous.

**Required action:** Identify the two missing dimensions or correct the total. Explain the mapping from PPO outputs to the actual ORFS parameters, including scaling, clipping, categorical encoding, rounding, valid ranges, and parameter constraints. Avoid calling the whole action space continuous unless every action is in fact continuous.

### 2.8 Reward-function description is incomplete

**Location:** Page 4, Section V-D.

The listed weights sum to 100%:

- WNS: 30%
- TNS: 15%
- Area: 15%
- Power: 10%
- DRC: 15%
- Congestion: 10%
- Runtime: 5%

However, “multi-objective with tanh scaling” is not sufficient for reproducibility.

**Required action:** Define the exact reward equation and explain:

1. How each metric is normalized and scaled before combination.
2. Whether higher or lower values are rewarded for each metric.
3. How negative WNS and TNS values are treated.
4. How missing metrics and failed runs are handled.
5. How terminal bonuses interact with the weighted reward.
6. Whether reward clipping or bounds are applied.

### 2.9 Failure-predictor validation may leak design information

**Location:** Page 5, Training Pipeline Orchestration.

The surrogate uses GroupKFold by design, while the failure predictor is described as using StratifiedKFold. If multiple runs from the same design occur in both training and validation folds, the failure-predictor evaluation may benefit from design-specific information and overestimate performance on unseen designs.

**Required action:** Consider StratifiedGroupKFold with `design_name` as the group, where the dataset permits it. Clearly distinguish the cross-validation strategy from the independent final test split. Explain whether the reported test data was excluded from model selection, calibration, threshold selection, and hyperparameter tuning.

### 2.10 Partial-run handling is unclear

**Locations:** Page 5, Table IV and Section VI-A.

The dataset reports 175 total runs, including 155 complete and 20 partial runs. The data-collection section says that training data is extracted from completed ORFS runs.

**Required action:** Explain whether partial runs are excluded from regression, used for failure classification, used for intermediate-stage prediction, or excluded entirely. State the valid sample count for each ML target, since the number of usable records may differ by metric.

---

## 3. Machine-learning methodology review

### 3.1 Feature engineering needs a complete feature specification

**Location:** Page 4, Section V-A.

The paper lists platform, core utilization, core margin, instance/net/sequential/macro counts, and engineered ratios, but reports a final feature dimension of approximately 16–17 without enumerating every input.

**Required action:** Add a table listing every feature, its source, data type, preprocessing, and whether it is available before the prediction stage. Include the exact final feature count for each model. Explain how power is extracted from ORFS reports and whether the target represents total, dynamic, leakage, or another power metric.

A useful structure is:

| Feature | Source | Type | Preprocessing |
|---|---|---|---|
| Platform | Run configuration | Categorical | One-hot encoding |
| Core utilization | `config.mk` | Numerical | State exact scaling |
| Core margin | `config.mk` | Numerical | State exact scaling |
| Instance count | Verilog parsing | Numerical | `log1p` if used |
| Net count | Verilog parsing | Numerical | `log1p` if used |
| Sequential count/ratio | Verilog parsing | Numerical | State exact formula |
| Macro count/ratio | Verilog parsing | Numerical | State exact formula |
| Core aspect ratio | `config.mk` | Categorical/numerical | Explain treatment |
| Additional features | Identify source | Specify | Specify |

### 3.2 LightGBM configuration should report the selected model

**Location:** Page 4, Section V-B.

The manuscript gives 500 boosting rounds and early stopping after 50 rounds but does not report the number of boosting rounds selected in each fold or in the final model.

**Required action:** Report the training and validation sample counts, early-stopping procedure, selected iteration count (or its distribution across folds), hyperparameter-selection method, and whether a separate validation set was used.

### 3.3 MLP complexity should be justified for the dataset size

**Location:** Page 4, Section V-B.

The MLP architecture has hidden layers of 256, 128, and 64 units, while the dataset contains only 175 runs. This does not automatically make the model invalid, but it increases the need to demonstrate that the results are not driven by overfitting.

**Required action:** Include training and validation learning curves, fold-wise metrics, regularization details, and preferably a comparison with smaller MLP architectures. Explain how normalization is fitted within each training fold to avoid leakage.

### 3.4 Failure-classifier calibration procedure needs more detail

**Locations:** Pages 4 and 7.

The paper describes LightGBM, isotonic calibration, and Youden's J threshold optimization. It should state exactly how the calibration predictions are generated and how the threshold is selected.

**Required action:** Ensure that the calibrator and threshold are fitted using training/validation or out-of-fold predictions only—not the independent test data. Define the reported “Reliability” metric, since the table gives values of 0.67 and 0.94 without a calculation. Add reliability diagrams for both classifiers if available.

---

## 4. Experimental results and tables

### 4.1 Table IV — Dataset Statistics (Page 5)

The table should show the count behind every percentage and identify the denominator. For example, timing closure is reported as 36/175 (20.6%). DRC-clean and LVS-clean rates should similarly show the number of valid observations and the number of clean runs. If partial runs do not have final DRC or LVS reports, they should not silently be included in the denominator.

### 4.2 Table V — Platform Distribution (Page 5)

The platform totals add to 175 runs, but the table's `Complete` and `Timing Closure` columns need unambiguous definitions. Clarify whether closure percentages use all platform runs or only completed runs. The denominator should be visible or stated in a note.

### 4.3 Table VI — Surrogate Cross-Validation Results (Page 6)

Replace the ambiguous `Ensemble` row with per-target columns for LightGBM, MLP, and Ensemble. Include an explicit metric and evaluation protocol in the table title or note. Do not combine incomparable or unexplained scores in one row.

### 4.4 Table VII — Hold-Out Test Set Performance (Page 6)

State the test-set construction and sample count. Confirm that the test set is separated by design if the goal is to evaluate generalization to unseen designs. Avoid MAPE for signed timing metrics, as described in Section 2.3.

### 4.5 Table IX and Table XI — Failure Predictor (Page 7)

The classifier metrics should include the positive-class definition and support (number of positive and negative samples). AUC, precision, recall, F1, and accuracy should be reported at clearly stated thresholds. Explain whether the threshold was selected on validation data and then fixed before testing.

### 4.6 Figure 4 — Model performance comparison (Page 6)

The figure is useful but its labels and values are small. Increase axis-label, tick-label, legend, and annotation sizes. Ensure every plotted value matches Tables VI and VII. If CV and test scores are both shown, distinguish them visually and label them explicitly.

### 4.7 Figure 5 — Timing-closure outcomes (Page 7)

Check that the figure caption, plotted data, and related discussion agree. Ensure axis labels and legend text remain readable at normal PDF zoom. Include the sample count or denominator where class proportions are shown.

### 4.8 Figure 6 — Parameter effects and correlation analysis (Page 8)

The plots are small. Increase text and annotation sizes and state how the knob-effect values and Spearman correlations were calculated. Avoid implying causality from correlation or observational parameter sweeps unless the experiment supports causal interpretation.

### 4.9 Figure 7 — Caption does not match the graph (Page 8)

The caption currently says:

> Fig. 7: PPA Analysis panel showing Predicted vs Actual vs Diff% comparison.

The rendered graph instead shows WNS evolution across flow stages and platforms.

**Suggested corrected caption:**

> Fig. 7: Evolution of worst negative slack (WNS) across physical-design stages for the evaluated technology platforms.

Alternatively, replace the plotted graph with a screenshot of the PPA Analysis panel if the existing caption is intended.

### 4.10 Table XII — Random Forest Results (Page 8)

The table title says Random Forest Results, but the test-result column includes labels such as `Ensemble` and `LGB`. It is unclear whether the values are Random Forest results or comparisons with other models.

**Required action:** Rebuild the table with separate, clearly named model columns and separate CV and test sections. Define whether every reported value is R² or AUC. Do not mix model names inside a test-score cell.

### 4.11 Table XIII — Inference Performance (Page 8)

State the hardware, software versions, warm-up procedure, number of measurements, and whether the values are means or medians. Clarify whether CPU and ONNX measurements use equivalent preprocessing and model configurations. If the reported times are measured, include variability (for example, standard deviation or percentile range).

---

## 5. Literature review and references

### 5.1 Unresolved citations

**Locations:** Pages 2 and 3; Table II.

The manuscript contains unresolved citation placeholders, including `Cadence Cerebrus [?]` and additional `[?]` entries in Table II.

**Required action:** Resolve every placeholder before submission. Verify that each citation points to the primary paper or authoritative product documentation supporting the specific statement.

### 5.2 Literature-review scope does not match the bibliography

**Location:** Page 2 and Page 9.

The manuscript says that its synthesis covers 20 recent papers, but the numbered bibliography contains 17 entries. It also points readers to Appendix A for detailed analysis, while the current appendix mainly contains a model-file listing and does not provide the promised paper-by-paper analysis.

**Required action:** Either add the missing references and include the promised appendix, or revise the stated number of papers and remove the unsupported appendix reference.

### 5.3 Reference metadata needs verification

The following entries were flagged during review and should be checked against the original publisher or proceedings record before submission:

- **[4] Auto-PPA:** The manuscript's 42% power-performance-product improvement claim needs verification against the original paper. The figure should not be retained unless the source's exact definition and experimental context support it.
- **[10] AI-assisted IC design:** The publication year and full title should be checked and corrected against the publisher record.
- **[12] FastTuner:** Verify the exact published title, author list, venue, year, and page/article details. The title in the manuscript should match the published record.
- **[13] GNN critical-path paper:** The exact citation could not be confidently established from the information given. Add a DOI, publisher page, or other primary bibliographic record.
- **[14] INSTA:** Verify the full published title and correct venue/year. Do not attribute results from a separate work such as LEGO-Size to this reference unless the source explicitly supports that attribution.
- **[17] Shrirao:** The title and venue details appear incomplete. Verify the full title, proceedings name, volume, pages, and year.

**Important:** Do not use a corrected-looking reference unless it has been checked against the actual publication. Citation accuracy is essential because the literature review uses these works to establish novelty and compare quantitative results.

### 5.4 Claims about competing systems should be qualified

Phrases such as “the only open-source workstation,” “first to integrate,” and “state-of-the-art” require a documented literature and product comparison. Unless a systematic search supports an exclusivity claim, use qualified phrasing such as “to the best of our knowledge” and describe the precise scope of the comparison.

### 5.5 Recommended literature-review improvements

- Distinguish surrogate modeling, Bayesian optimization, RL, GNN-based representations, differentiable optimization, and agentic workflows without suggesting that all systems solve the same problem.
- Describe the input features, optimization variables, target metrics, and evaluation setup of the closest related systems.
- Compare OpenRoad-GUI with prior work using specific capabilities rather than broad statements about what other systems cannot do.
- Support every numerical improvement claim with a citation to the primary source and preserve the source's original metric definition.

---

## 6. Academic writing and terminology corrections

The writing is generally understandable, but some expressions are promotional or imprecise. Prefer evidence-led language and consistent terminology.

| Current wording | Suggested wording |
|---|---|
| Power-Performance-Area (PPA) | Power, Performance, and Area (PPA) |
| modern Tkinter-based GUI | Tkinter-based desktop GUI |
| state-of-the-art results | Experimental results |
| complete desktop workstation | Integrated desktop workstation |
| First to integrate | To the best of our knowledge, one of the first systems to integrate |
| The system achieves | The experimental results indicate |
| DRC Clean prediction | DRC-clean prediction |
| 5-fold GroupKFold | Five-fold GroupKFold cross-validation |
| real-time PPA prediction | Low-latency PPA prediction, if experimentally supported |
| ONNX export capability | ONNX-based model deployment support |

### Suggested sentence-level revisions

**Page 1 — Abstract**

Current:

> Experimental results demonstrate significant improvement over baseline surrogate models, with ensemble methods reducing WNS prediction error by 45% compared to single-model approaches.

Suggested, pending verification of the exact results:

> Experimental results evaluate the proposed surrogate models across multiple PPA metrics and compare the ensemble against its individual component models.

If the 45% reduction is verified, add it back with the exact metric, baseline, and test protocol.

**Page 1 — Introduction**

Current:

> The OpenROAD has evolved across multiple distinct but intersecting research threads.

Suggested:

> Machine-learning applications in physical design have evolved across several distinct but interconnected research directions.

**Page 3 — GUI Layer**

Current:

> The GUI implements a 4-zone layout per industrial EDA workstation standards.

Suggested:

> The GUI uses a four-zone layout consisting of a navigation panel, a central workspace, an AI sidebar, and a header.

**Page 3 — Flow Execution Layer**

Current:

> Sources use-openroad.sh environment script before each invocation.

Suggested:

> Sources the `use-openroad.sh` environment script before each invocation.

**Page 7 — Comparison**

Current:

> It trades peak optimization performance (FastTuner's 79% TNS gain) for reproducibility, deployability, and engineer-in-the-loop usability.

Suggested:

> The workstation prioritizes reproducibility, deployability, and engineer-in-the-loop interaction; its optimization performance should be compared with specialized frameworks only under a consistent evaluation setup.

**Page 8 — Conclusion**

Current:

> OpenRoad-GUI represents a significant advance in democratizing ML-enhanced EDA workflows.

Suggested:

> OpenRoad-GUI presents an integrated approach to making machine-learning-assisted physical-design workflows more accessible through an open-source desktop workstation.

---

## 7. Page-by-page editorial review

| Page | Section/content | Findings | Priority |
|---|---|---|---|
| 1 | Title and Abstract | Abstract is lengthy; design count and model metrics need reconciliation; contribution claims should reflect actual implementation status. | High |
| 1 | Introduction | Broad statements about flow runtime and manual tuning need appropriate support or qualification. | Medium |
| 2 | Related Work | Unresolved citation and claims that need closer alignment with original papers. | High |
| 2 | Section II-A–F | Some subsection transitions are abrupt; Section III follows a literature synthesis that needs a clearer evidence trail. | Medium |
| 3 | Tables I and II | Table II includes a potentially incorrect FastTuner criticism and unresolved citation markers. | Critical |
| 3 | Architecture and GUI | Architecture is understandable, but diagram labels are small and some GUI capability statements need implementation evidence. | Medium |
| 4 | Feature Engineering | The stated feature count cannot be reconstructed from the listed features. | High |
| 4 | Surrogate Models | MLP complexity needs justification for the small dataset; CV and test protocols need detail. | High |
| 4 | Failure Predictor | DRC-clean class prevalence needs reconciliation. | Critical |
| 4 | PPO Optimizer | State and action dimensions do not match the listed components; action types and reward are under-specified. | Critical |
| 5 | Dataset Statistics | Five-versus-six design discrepancy; partial-run handling is unclear. | Critical |
| 5 | Training Pipeline | The Dataset Statistics subsection is effectively empty in the body text despite the preceding table. | Medium |
| 6 | Surrogate Results | Ensemble row in Table VI is ambiguous; ensure values and model comparisons agree with the abstract and figures. | Critical |
| 6 | PPO Results | Training is reported as in progress; avoid presenting the optimizer as a validated result. | Critical |
| 6 | GUI Integration | Distinguish completed functions from placeholders and planned integration. | Medium |
| 7 | Calibration | Define the reliability metric and clarify the data used for calibration and threshold selection. | High |
| 7 | Comparison | “Only,” “first,” and peak-performance comparisons need evidence and careful qualification. | High |
| 8 | Figures and Tables | Figure 7 caption mismatch; Table XII mixes model labels; figure readability could improve. | High |
| 8 | Conclusion | Claims should be aligned with the actual status of PPO and the independent test results. | Critical |
| 9 | Appendix and References | Appendix content does not match the Appendix A promise; JSON/schema presentation has an extra brace/fragment; references need checking. | High |
| 10 | Table XV | Page is almost entirely blank apart from the comparison table; table should be moved or layout adjusted. | High |

---

## 8. PDF layout and visual presentation

### 8.1 General appearance

The two-column format is broadly consistent, and the body text does not show widespread overlap in the reviewed rendering. The main visual problems are small figure labels, dense tables, awkward placement, and unnecessary whitespace.

### 8.2 Pages 3–8: figures and diagrams

Increase the font sizes inside figures, especially:

- Figure 1: four-layer architecture.
- Figure 2: platform outcomes and closure-rate plots.
- Figure 3: WNS evolution plots.
- Figure 4: model-performance comparison.
- Figure 6: parameter effects and correlation heatmap.
- Figure 7: WNS evolution plot.

Where possible, export charts and diagrams as vector graphics (PDF or SVG) rather than low-resolution raster images. Ensure that axes, legends, and labels remain readable at normal PDF zoom.

### 8.3 Page 9: appendix

The JSON-like schema is split across the two columns and is difficult to read as a single structured object. There also appears to be an unmatched opening brace or stray `{` after the model-file listing. The appendix does not include the detailed literature synthesis promised as Appendix A.

**Required action:** Present the schema in a properly formatted code listing or a compact table, remove the stray character, and either add the promised literature appendix or revise the reference to it. Remove “Detailed in the supplementary material” unless supplementary material is actually included and accessible.

### 8.4 Page 10: nearly empty final page

Table XV occupies a page that is otherwise nearly blank. This makes the manuscript look unfinished and wastes space.

**Required action:** Move Table XV to the end of Section X or resize/reformat it so it fits naturally in the preceding page or pages. Preserve readability rather than shrinking the table excessively.

---

## 9. Prioritized revision checklist

### Critical — resolve before submission

- [ ] Verify whether the dataset contains five or six unique designs and make the manuscript consistent.
- [ ] Recalculate the DRC-clean rate, positive-class definition, sample counts, and class weights.
- [ ] Rebuild Table VI with clearly identified LightGBM, MLP, and Ensemble scores for every target.
- [ ] Correct or remove the FastTuner criticism after checking the original publication.
- [ ] Reconcile PPO state dimension (128 claimed versus 48 listed) and action dimension (16 claimed versus 14 listed).
- [ ] Explain the PPO action encoding and parameter mapping.
- [ ] Characterize PPO as preliminary until action-sensitive optimization is demonstrated experimentally.
- [ ] Correct Figure 7's caption or replace the graph.
- [ ] Clarify the test-set protocol and prevent design-level leakage in classifier validation.

### High — resolve before final formatting

- [ ] Verify all reference metadata, particularly references [4], [10], [12], [13], [14], and [17].
- [ ] Resolve every `[?]` citation placeholder.
- [ ] Reconcile the claimed 20-paper review with the 17 numbered references and the missing Appendix A.
- [ ] Rebuild Table XII with unambiguous model columns and metrics.
- [ ] Explain how partial runs are used or excluded for each prediction task.
- [ ] Define the calibration “Reliability” metric and describe the calibration split.
- [ ] Align all figures, tables, abstract, results, and conclusion with the same verified numbers.
- [ ] Move Table XV so that Page 10 is not almost entirely blank.
- [ ] Repair the appendix schema and remove the stray brace.

### Medium — improve quality and reproducibility

- [ ] Add a complete feature-definition table.
- [ ] Report LightGBM early-stopping iterations and data split sizes.
- [ ] Add MLP learning curves or other evidence against overfitting.
- [ ] Fully define PPO reward normalization and failed-run handling.
- [ ] Improve figure labels, legends, and chart resolution.
- [ ] Standardize terminology, capitalization, units, and hyphenation.
- [ ] Perform a final grammar and IEEE-style consistency pass.

---

## 10. Final evaluation

| Evaluation category | Assessment |
|---|---|
| Research idea | Very good |
| System architecture | Good |
| Literature review | Needs improvement |
| Technical consistency | Major revision required |
| ML methodology | Promising; stronger validation and reproducibility detail required |
| Experimental presentation | Major revision required |
| Academic writing | Good foundation; wording and claims need refinement |
| References | Verification and correction required |
| PDF formatting | Needs improvement, especially figures, appendix, and final page |

### Main strength

The strongest aspect of the manuscript is its systems contribution: integrating multiple ML capabilities into a real ORFS-based EDA workstation rather than presenting only an isolated prediction algorithm.

### Main weakness

The main weakness is the gap between what has been experimentally demonstrated and what the manuscript claims the complete system can achieve, particularly for PPO-based autonomous optimization. The numerical inconsistencies in the dataset and model results also need to be resolved before the paper's conclusions can be trusted.

### Overall recommendation

**Major revision before submission.** Resolve the dataset, DRC-label, surrogate-result, and PPO discrepancies first. Then correct the literature comparison, references, figures, appendix, and PDF layout. Finish with a complete academic-language and formatting pass.

---

*This report is based on the supplied 10-page manuscript and its rendered page images. Numerical discrepancies are flagged for verification against the underlying dataset, training logs, model artifacts, and original cited publications; they should not be “corrected” by guessing values from the paper alone.*
