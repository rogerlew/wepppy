# ExecPlan: MOFE Flagged Hillslope Taxonomy Refinement (D_UNCLASSIFIED Split)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

This plan is the second ExecPlan in the same work-package as `mofe_flagged_hillslope_triage_execplan.md`. It consumes the v1 outputs in `docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/` and produces v2 outputs alongside them. It does not delete or rewrite v1; v1 remains the baseline against which v2 is diffed.

## Purpose / Big Picture

The first ExecPlan in this work-package classified 132 flagged MOFE hillslopes with deterministic rules D1–D5 plus a `D_UNCLASSIFIED` sink. 114 of 132 hillslopes (86%) landed in the sink, which makes the resulting `campaign_matrix.csv` operationally weak — you cannot bootstrap a focused ablation lane from "114 hillslopes, mechanism unknown." The science maintainer Open Question 1 in the v1 retrospective made this explicit.

After this work, a contributor can open `campaign_matrix_v2.csv` and see the 114 hillslopes split into mechanistic families with rules grounded in the actual feature distribution, plus an explicit record of which v1 rules were broken and why. The deliverable is rule design + sensitivity analysis, not new model runs and not new data collection. Success is observable: the count of `D_UNCLASSIFIED` rows in `taxonomy_assignments_v2.csv` drops to ≤ 5% of flagged hillslopes (≤ 7 rows on current data), and every retained family has a non-trivial population (≥ 3 hillslopes) plus a defensible mechanism hypothesis.

## Execution Preconditions

- v1 ExecPlan acceptance must already be passed; the artifacts directory must contain `triage_table_hillslopes.csv`, `triage_table_hillslopes_all.csv`, `triage_table_runs.csv`, `taxonomy_assignments.csv`, `representative_seeds.csv`, `campaign_matrix.csv`, and `defect_families.md`.
- `/wc1/runs` must remain mounted (only consumed at M5 for representative-seed shared-context checks).
- Python environment must include `pandas`, `numpy`, and `sklearn`. Prefer `hdbscan` for clustering; if unavailable, use `sklearn_extra` k-medoids when installed, otherwise fall back to `sklearn` KMeans and record the fallback in `Decision Log`.
- If any precondition fails, record a blocker in `Surprises & Discoveries` and stop before M1.

## Progress

- [x] (2026-05-02) ExecPlan drafted; v1 D_UNCLASSIFIED feature distribution profiled by Claude Code and load-bearing findings recorded under `Surprises & Discoveries`.
- [ ] M1. Emit `unclassified_profile.md` reproducing and extending the v1-output profile (statistics + per-axis distributions).
- [ ] M2. Emit `rule_gap_analysis.md` enumerating exactly why each v1 rule (D2, D3, D5) failed to capture the visible signal in D_UNCLASSIFIED.
- [ ] M3. Author and freeze the refined taxonomy (D1, D2a, D2b, D3, D4, D5, D6a, D6b, D6c) in `tools/refine_mofe_taxonomy.py`, emit `taxonomy_assignments_v2.csv`, and assert the D_UNCLASSIFIED population dropped below the 5% gate.
- [ ] M4. Run the cluster cross-check on the v2 labels and emit `taxonomy_disagreements_v2.csv`. Disposition every disagreement in the Decision Log.
- [ ] M5. Re-select representative seeds for every populated v2 family and emit `representative_seeds_v2.csv` with full staged-input manifests.
- [ ] M6. Emit `campaign_matrix_v2.csv`, `defect_families_v2.md`, and `taxonomy_evolution.md` (v1→v2 lineage). Run threshold sensitivity sweep and emit `threshold_sensitivity.csv`.
- [ ] M7. Closeout: update v1 `package.md` `Follow-up Work` section to note the v2 outputs, update tracker, mark this ExecPlan complete.

## Surprises & Discoveries

- Observation: D_UNCLASSIFIED is dominated by outlet-OFE outliers, not topology-diverse outliers. 113 of 114 unclassified rows have `outlier_is_outlet_ofe == True`; only 1 is interior. The structural difference between D1 and D_UNCLASSIFIED is magnitude (D1 requires `> 1000 mm`), not topology.
  Evidence: profiled 2026-05-02 from `triage_table_hillslopes.csv` joined with `taxonomy_assignments.csv`.
- Observation: `runoff_pass_vs_outlet_qofe_residual_m3_max_abs` is non-trivial across the entire D_UNCLASSIFIED population. Median 20.1 m³, max 246 m³. The v1 D2 rule requires `outlier_is_interior_ofe == True` and therefore cannot fire on these rows even though a chain-level signal is present.
  Evidence: same profile run.
- Observation: `soilwater_gt_porositycap_days == 0` for every D_UNCLASSIFIED row, while `soilwater_to_porosity_fraction_p99` reaches 1.0 in 75th-percentile rows. The v1 D3 trigger column is dead in this dataset; storage saturation has to be detected from the porosity fraction directly.
  Evidence: same profile run.
- Observation: 5 D_UNCLASSIFIED rows have `requires_scientific_review_days >= 30` and would have matched D5 except the v1 D5 rule has an upper magnitude bound (`<= 500 mm`) that excludes high-magnitude persistent regimes.
  Evidence: same profile run.
- Observation: D_UNCLASSIFIED days-of-flag distribution is bimodal-with-tail. 52 rows ≤ 3 days, 57 rows in 4–29 days, 5 rows ≥ 30 days. The 4–29 day band is a real gap in the v1 ruleset — neither D4 (single-day extreme) nor D5 (persistent moderate) covers it.
  Evidence: same profile run.

## Decision Log

- Decision: Emit v2 artifacts alongside v1 rather than overwriting. v1 remains canonical for the closure already shipped to maintainers.
  Rationale: A v1→v2 diff is the easiest review surface; overwriting destroys the lineage. v1 outputs were reviewed and accepted as a closure-of-record.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: Refactor v1 rules in place rather than only adding new rules. D2 splits into D2a/D2b, D3 changes its trigger, and D5 is explicitly split so moderate-persistent remains D5 (100–500 mm) while severe-persistent moves to D6c (>500 mm). Renamed rules use bare names in outputs.
  Rationale: The v1 retrospective Open Question 2 is partly answered by D2 broadening; D3/D5 fixes are not optional given the D3 dead-column finding and the D5 persistent-severe gap. Adding new families without fixing the broken existing ones would leave overlapping coverage.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: Threshold sensitivity sweep is M6 (after the campaign matrix), not pre-M3.
  Rationale: A sweep is cheap once the rules are coded; running it before the rules exist is busywork. The acceptance gate is "D_UNCLASSIFIED ≤ 5%" — if the proposed thresholds fail that, M3 iterates within the milestone before M4 runs.
  Date/Author: 2026-05-02 / Claude Code.

## Outcomes & Retrospective

Pending execution. To be written at M7 closeout. Compare realized v2 prevalence against the proposed family ranges in M3, list any threshold change made during M3 calibration, and note whether sensitivity sweep flagged any unstable thresholds (Jaccard < 0.7 within ±25% perturbation).

## Context and Orientation

### Source data (read-only inputs)

All inputs are already in this work-package's artifacts directory `docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/`:

- `triage_table_hillslopes.csv` — 132 flagged hillslopes with the full feature schema (64 columns) defined by the v1 ExecPlan. Primary input for all v2 work.
- `triage_table_hillslopes_all.csv` — 1166 audited hillslopes (flagged + unflagged). Used at M5 for v2 contrast-seed selection.
- `triage_table_runs.csv` — 4 (runid, config) rows with run-context fields.
- `taxonomy_assignments.csv` — v1 family assignments. Used at M2 to identify D_UNCLASSIFIED rows and at M6 to compute the v1→v2 diff.

The D_UNCLASSIFIED population is defined as `taxonomy_assignments.family_primary == "D_UNCLASSIFIED"` joined to `triage_table_hillslopes.csv` on `(runid, config, wepp_id)`.

### Output location

All v2 outputs land under the same `artifacts/` directory. New files use the `_v2` suffix on their stem; do not overwrite v1 files. Final v2 file list is enumerated under "Artifacts and Notes" below.

### Term definitions (plain language)

- **D-family**: a defect family label from this taxonomy (`D1`, `D2a`, `D6c`, etc.). A label asserts that the hillslope's flag is plausibly explained by the named mechanism. Same definition as in v1.
- **Outlet OFE**: the last OFE in a hillslope's profile (largest `wepp_id` of the OFEs, equal to `n_ofe_max`). Most flow concentration in MOFE runs occurs here.
- **Outlier OFE**: the OFE that produced the worst residual on the worst flagged day (`late_outlier_ofe_id` in the feature table).
- **Ratio saturation**: `late_max_qofe_to_q_ratio_max_abs` approximately equal to `n_ofe_max`. In the validation dataset every flagged hillslope has `n_ofe_max == 16` and ratios saturate at ~16.0; the v1 D1 rule treats this as a marker for outlet-flow concentration.
- **Chain residual**: residual of the upstream→downstream water/sediment-balance check inside `mofe_chain` block. Two signals: `surface_transfer_residual_m3_geometry_sensitive` (between-OFE surface) and `runoff_pass_vs_outlet_qofe_residual_m3` (aggregated outlet check).

### Scope

In scope: refining family definitions, re-running classification + clustering + seed selection, sensitivity-testing thresholds.

Out of scope: re-running the audit tool, modifying `triage_table_hillslopes.csv` columns, opening downstream ablation incidents, changing v1 outputs.

## Plan of Work

### M1 — Profile D_UNCLASSIFIED

Goal: produce a written profile of the D_UNCLASSIFIED population so v2 rules are calibrated against observable structure, not intuition.

Output: `unclassified_profile.md`. Required content:

1. Population size and per-(runid, config) breakdown.
2. Per-axis distribution tables (min / p25 / p50 / p75 / max) for: `late_max_abs_ofe_closure_residual_mm_max_abs`, `late_max_surface_pulse_proxy_mm_max_abs`, `closure_residual_pct_of_rm_total`, `closure_residual_total_mm`, `requires_scientific_review_days`, `flagged_day_fraction`, `late_outlier_ofe_id`, `chain_surface_transfer_residual_m3_p99`, `chain_subsurface_transfer_residual_m3_p99`, `runoff_pass_vs_outlet_qofe_residual_m3_max_abs`, `soilwater_to_porosity_fraction_p99`, `soilwater_gt_porositycap_days`.
3. Topology counts: how many rows are outlet/interior/first/null on `late_outlier_ofe_id`.
4. Day-band counts: ≤ 3, 4–29, ≥ 30.
5. A short prose summary (≤ 200 words) listing the three highest-leverage observations.

Acceptance for M1: file exists, all 12 distributions are present, populations sum to 114, the prose summary references the bimodal day-distribution and the dead D3 trigger column.

### M2 — Diagnose v1 rule gaps

Goal: explain in writing exactly why each v1 rule failed where it did. This is a forcing function — without it, v2 rules will make the same mistakes.

Output: `rule_gap_analysis.md`. Required content (one section per finding):

1. **D2 outlet blind spot**: D2 requires `outlier_is_interior_ofe == True`. Quantify how many D_UNCLASSIFIED rows have non-trivial `runoff_pass_vs_outlet_qofe_residual_m3_max_abs` (suggest threshold > 1.0 m³). Recommend the D2a/D2b split.
2. **D3 dead trigger column**: D3 requires `soilwater_gt_porositycap_days >= 1`. Quantify how many flagged rows ever have that column non-zero (the answer should be near zero across the whole flagged population, not just D_UNCLASSIFIED — verify by checking all 132 rows). Recommend dropping the day-count gate and triggering on `soilwater_to_porosity_fraction_p99 >= 0.99` directly.
3. **D5 upper-bound exclusion**: D5 requires `late_max_abs_ofe_closure_residual_mm_max_abs <= 500`. Identify the rows with `requires_scientific_review_days >= 30` that fail D5 because their residual exceeds 500 mm. Recommend either (a) dropping the upper bound, or (b) splitting D5 into D5 (moderate-persistent, 100–500) and a new D6c (severe-persistent, > 500). The v2 ruleset prefers (b) because the mechanism hypothesis differs.
4. **Coverage gap (4–29 day band)**: list how many D_UNCLASSIFIED rows fall in this band. Recommend a new D6a/D6b family pair (or a single D6 with day-band sub-codes — Codex chooses, records in Decision Log).

Acceptance for M2: file exists; each finding cites a row count and a column threshold; the recommendations together cover ≥ 95% of D_UNCLASSIFIED.

### M3 — Author refined taxonomy

Goal: implement the v2 ruleset, run it against `triage_table_hillslopes.csv`, and emit `taxonomy_assignments_v2.csv`.

Tool to author: `tools/refine_mofe_taxonomy.py`. Default no-arg invocation reads from this work-package's artifacts directory and writes back to it. The script must be a pure function of `triage_table_hillslopes.csv`; do not consult v1 `taxonomy_assignments.csv` for assignment (only for the M6 diff).

Initial v2 ruleset (Codex calibrates thresholds during M3 if M3 acceptance fails):

- **D1 — Outlet-OFE saturation spike (severe).** `outlier_is_outlet_ofe == True` AND `late_max_abs_ofe_closure_residual_mm_max_abs > 1000` AND `late_max_qofe_to_q_ratio_max_abs >= n_ofe_max - 0.01`. Unchanged from v1.
- **D2a — Interior-OFE chain anomaly.** `outlier_is_interior_ofe == True` AND any of `chain_surface_transfer_residual_m3_p99 > 1e-3`, `chain_subsurface_transfer_residual_m3_p99 > 1e-3`. Inherits the v1 D2 mechanism; the geometry constraint is preserved.
- **D2b — Outlet runoff-vs-qofe mismatch.** `outlier_is_outlet_ofe == True` AND `runoff_pass_vs_outlet_qofe_residual_m3_max_abs > T_D2b` AND NOT D1, where initial `T_D2b = 1.0` and M3 calibration may raise it using the guardrail ladder below. Mechanism hypothesis: outlet-element accounting drift visible in the runoff-pass-vs-outlet check even when ratio saturation does not close the failure with D1.
- **D3 — Storage saturation pressure.** `soilwater_to_porosity_fraction_p99 >= 0.99` (NO day-count gate). Mechanism hypothesis unchanged from v1; trigger column corrected.
- **D4 — Single-day extreme.** `requires_scientific_review_days <= 3` AND `late_max_abs_ofe_closure_residual_mm_max_abs >= 500`. Unchanged from v1.
- **D5 — Persistent moderate.** `requires_scientific_review_days >= 30` AND `late_max_abs_ofe_closure_residual_mm_max_abs` between 100 and 500 inclusive. Unchanged in narrative; D5 keeps its upper bound, severe-persistent goes to D6c.
- **D6a — Sub-severe single-day spike.** `requires_scientific_review_days <= 3` AND `late_max_abs_ofe_closure_residual_mm_max_abs >= 100` AND `< 500`. Mechanism hypothesis: the same numerical surge mechanism as D4 but below the severe-magnitude bar.
- **D6b — Multi-day moderate.** `requires_scientific_review_days` between 4 and 29 inclusive AND `late_max_abs_ofe_closure_residual_mm_max_abs >= 100`. Mechanism hypothesis: parameter or boundary-condition error producing a multi-day moderate residual without crossing into "persistent" territory.
- **D6c — Persistent severe.** `requires_scientific_review_days >= 30` AND `late_max_abs_ofe_closure_residual_mm_max_abs > 500`. Mechanism hypothesis: structural model gap rather than numerical surge — long-duration severity is unlikely to be a one-off floating-point event.

Assignment policy: evaluate D1, D4, D5, D6c, D2a, D2b, D3, D6a, D6b in that order. First match wins for `family_primary`. Subsequent matches populate `family_secondary` and `family_tertiary`. This ordering preserves precedent-linked severe families before broader outlet-mismatch buckets. After all rules run, apply the v1 D0 demotion check — if any v2 family satisfies all D0 demotion criteria (concentration ≥ 0.95 in one (runid, config), size ≥ 5, ≥ 5 of 6 standardized feature deltas ≤ 0.35, max delta ≤ 0.75), demote that family to D0 and record in Decision Log.

Calibration guardrails (required before freezing thresholds):

1. Run a dry classification pass with the initial thresholds and report family counts.
2. If `D2b` captures more than 75% of flagged rows, increase the `D2b` runoff threshold using this deterministic ladder until `D2b` is ≤ 75%: `1.0`, `p60`, `p70`, `p75` of `runoff_pass_vs_outlet_qofe_residual_m3_max_abs` on non-D1 outlet rows.
3. If `D3` captures more than 50% of flagged rows, tighten the `D3` porosity threshold from `0.99` to `0.995` and re-run the dry pass.
4. Preserve D4 as a sentinel family even when population is < 3; this family is precedent-linked to the H2637 closure-spike incident.
5. Record every threshold change in `Decision Log` with before/after counts.

Output schema for `taxonomy_assignments_v2.csv` matches v1: `runid, config, wepp_id, family_primary, family_secondary, family_tertiary, family_rationale, cluster_label, rule_cluster_agreement`. (Cluster columns are populated at M4; emit blanks at M3.)

Acceptance for M3: file exists; every flagged hillslope has a non-null `family_primary`; `D_UNCLASSIFIED` count ≤ 7 (5% of 132); every populated family except D4 has ≥ 3 hillslopes (drop or merge any other family with < 3 — record in Decision Log). If the gate fails, calibrate thresholds within M3 (do not advance).

### M4 — Cluster cross-check

Goal: validate v2 labels against feature-space geometry; surface disagreements; decide whether to retune thresholds.

Procedure mirrors v1 M3: standardize features, run HDBSCAN with `min_cluster_size=5`; if unavailable, fall back to k-medoids (`sklearn_extra`) and then KMeans (`sklearn`) in that order. Record the selected algorithm in `Decision Log`, emit `cluster_label` and `rule_cluster_agreement` columns into `taxonomy_assignments_v2.csv` (overwriting the blanks left by M3). Emit `taxonomy_disagreements_v2.csv` with the disagreement rows.

Acceptance for M4: `taxonomy_disagreements_v2.csv` exists; the disagreement count is reported in `Surprises & Discoveries`; every disagreement has a Decision Log entry (relabel, retune, or accept).

### M5 — Representative seeds (v2)

Goal: re-pick worst/median/contrast seeds per populated v2 family.

Output: `representative_seeds_v2.csv`. Same schema as v1 `representative_seeds.csv`. Selection rules unchanged (worst = max `late_max_abs_ofe_closure_residual_mm_max_abs`; median = closest to family median; contrast = nearest unflagged hillslope from same (runid, config) by L2 in standardized feature space). Staged-input manifest population unchanged.

Exclude `D0` and any `D_UNCLASSIFIED` residual from seed selection (a residual ≤ 7 may exist; treat it the same way v1 did — taxonomy-gap sink, not a mechanistic family).

Acceptance for M5: `representative_seeds_v2.csv` has `3 * (number of populated mechanistic families)` rows; every `worst` and `median` row has `missing_shared_context == ""`. If a representative seed cannot resolve shared context, emit a Surprises & Discoveries entry naming the hillslope.

### M6 — Campaign matrix v2 + sensitivity sweep + lineage doc

Goal: produce the ablation-ready v2 campaign matrix, document v1→v2 evolution, and stress-test thresholds.

Outputs:

1. `campaign_matrix_v2.csv` — same schema as v1 `campaign_matrix.csv`. One row per populated v2 family. The `recommendation` column should reference v1 incident IDs only when the family genuinely matches an existing precedent (D4 ↔ H2637 closure-spike incident is the only known precedent at v1 close); otherwise recommend a new incident.
2. `defect_families_v2.md` — one paragraph per family covering prevalence, severity, signature stability, mechanism hypothesis, and recommended next step. Replaces v1 `defect_families.md` for the v2 reader (do not delete v1).
3. `taxonomy_evolution.md` — short document (≤ 300 words) explaining the v1→v2 changes with row-count deltas. Required sections: "What changed" (per-rule narrative), "Coverage delta" (table: family, v1 count, v2 count), "Disposition of v1 D_UNCLASSIFIED" (cross-tab of v1 family vs v2 family for the 114 rows).
4. `threshold_sensitivity.csv` — one row per (rule_id, threshold_name, perturbation, jaccard_with_baseline). Perturbations: `-25%`, `-10%`, `+10%`, `+25%` of each numeric threshold in the v2 ruleset. `jaccard_with_baseline` is the Jaccard similarity between the perturbed family-membership set and the M3 baseline set. Threshold columns to sweep: D1 magnitude (1000), D2a chain p99 (1e-3), D2b qofe-mismatch (`T_D2b` after calibration), D3 porosity fraction (0.99 or 0.995 after calibration), D4 magnitude (500), D5 day-count lower (30), D6a magnitude lower (100), D6b magnitude lower (100), D6c day-count lower (30) and magnitude lower (500). Emit Jaccard ≥ 0.7 as "stable", < 0.7 as "unstable" — record any unstable threshold in Surprises & Discoveries.

Acceptance for M6: all four files exist; matrix rows align with `taxonomy_assignments_v2.csv` and `representative_seeds_v2.csv`; sensitivity sweep covers every numeric threshold; any unstable threshold has a follow-up note.

### M7 — Closeout

Goal: integrate v2 outputs into the work-package narrative.

Steps:

1. Update `package.md` `Follow-up Work` to note that v2 outputs are in place and the taxonomy is now operational. Do not change the "Open ablation execution packages" line — that remains the next-tier follow-up.
2. Update `tracker.md` with the v2 milestone timeline.
3. Fill in this ExecPlan's `Outcomes & Retrospective` section.
4. Mark all `Progress` items checked.

Acceptance for M7: `package.md` mentions v2; `tracker.md` reflects v2 closeout; this file's retrospective is non-empty; all Progress items checked.

## Concrete Steps

All commands run from the repository root `/workdir/wepppy` unless noted.

Step 0. Verify preconditions:

    test -f docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/triage_table_hillslopes.csv
    test -f docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/taxonomy_assignments.csv
    test -d /wc1/runs
    .venv/bin/python - <<'PY'
    import importlib.util
    import pandas, numpy, sklearn  # noqa: F401
    print("hdbscan_available", bool(importlib.util.find_spec("hdbscan")))
    print("sklearn_extra_available", bool(importlib.util.find_spec("sklearn_extra")))
    PY

Step 1. Profile and emit `unclassified_profile.md` (M1). May reuse existing pipeline modules from v1 (`tools/triage_pipeline.py`); add a `--profile-unclassified` mode or write a small new tool — Codex's choice, recorded in Decision Log.

Step 2. Author `rule_gap_analysis.md` (M2) by hand from the M1 profile data plus direct queries against `triage_table_hillslopes.csv`. This is a written analysis — no new tool needed.

Step 3. Author `tools/refine_mofe_taxonomy.py` (M3). Run:

    .venv/bin/python tools/refine_mofe_taxonomy.py

Expected transcript fragment:

    refine_mofe_taxonomy: 132 flagged hillslopes classified, D_UNCLASSIFIED=<N> (gate <= 7)

If `<N>` exceeds 7, iterate within M3.

Step 4. Run M4 cluster cross-check. Codex may extend `tools/refine_mofe_taxonomy.py` or call back into `tools/triage_pipeline.py`'s clustering module — either is acceptable.

Step 5. Re-run representative-seed selection (M5) and emit campaign matrix + sensitivity sweep (M6). Reuse v1 modules where possible; do not re-invent the wheel.

Step 6. Closeout (M7).

## Validation and Acceptance

Final acceptance for the work-package's v2 phase is observable behavior:

1. A reviewer opens `campaign_matrix_v2.csv` and sees ≤ 1 row attributed to `D_UNCLASSIFIED` (if any). Every other row names a mechanism, a representative seed triplet, and a recommendation.
2. `defect_families_v2.md` answers the question "what mechanism families are operationally distinct?" with a defensible count and one paragraph per family.
3. `taxonomy_evolution.md` shows the v1→v2 migration of the 114 D_UNCLASSIFIED rows row-count-by-row-count.
4. `threshold_sensitivity.csv` flags any rule that swings family membership wildly (Jaccard < 0.7) under ±10% and ±25% perturbations. Stable rules are calibration-safe; unstable rules carry an explicit warning into the next ablation campaign.
5. The work-package's `package.md` and `tracker.md` reference the v2 outputs.

A negative finding ("D6 splits do not stratify cleanly; we recommend running ablations on the existing D1/D2/D4 seeds and treating the D6 band as an open science question") is acceptable. Record it in `Outcomes & Retrospective` and emit a `campaign_matrix_v2.csv` whose D6 rows have `recommendation = hold` rather than `new_incident`.

## Idempotence and Recovery

Every v2 tool overwrites its own outputs. Re-running after a rule change or threshold tweak is safe; v1 outputs are not touched.

If a milestone fails its acceptance gate, do not advance — iterate within the milestone (M3 calibration is the most likely loop). Document each iteration in Decision Log so the lineage is reconstructable.

If the M3 acceptance gate cannot be met after three calibration passes, stop and write a `Surprises & Discoveries` entry with the closest-achieved D_UNCLASSIFIED count and the residual rows' identifiers; do not lower the gate silently.

## Artifacts and Notes

Final v2 artifact additions to `docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/`:

    artifacts/
    ├── unclassified_profile.md         (M1)
    ├── rule_gap_analysis.md            (M2)
    ├── taxonomy_assignments_v2.csv     (M3, M4)
    ├── taxonomy_disagreements_v2.csv   (M4)
    ├── representative_seeds_v2.csv     (M5)
    ├── campaign_matrix_v2.csv          (M6)
    ├── defect_families_v2.md           (M6)
    ├── taxonomy_evolution.md           (M6)
    └── threshold_sensitivity.csv       (M6)

v1 artifacts are untouched. The `tools/refine_mofe_taxonomy.py` module is the new authored code; reuse of `tools/triage_pipeline.py` and `tools/build_mofe_triage_table.py` is encouraged but not required.

## Interfaces and Dependencies

Required tool: `tools/refine_mofe_taxonomy.py`. Public CLI (defaults shown):

    .venv/bin/python tools/refine_mofe_taxonomy.py \
        --input-dir docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts \
        --output-dir docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts \
        [--no-cluster] [--no-sensitivity]

`--no-cluster` skips the M4 cluster step (useful during M3 calibration). `--no-sensitivity` skips the M6 sweep (useful when iterating on prose deliverables).

Dependencies: `pandas`, `numpy`, `sklearn`; `hdbscan` and `sklearn_extra` are optional accelerants for clustering quality. No new pinned dependencies.

Read-only consumed interfaces:

- `triage_table_hillslopes.csv` — schema is treated as a frozen contract from v1. Any column rename in a future audit-tool change must be reconciled in v1 before this v2 plan is re-executed.
- `triage_table_hillslopes_all.csv` — used only at M5 for contrast-seed selection.
- `taxonomy_assignments.csv` — read at M2 (to identify D_UNCLASSIFIED rows) and M6 (to compute the v1→v2 cross-tab). Never written.

## Revision Notes

- 2026-05-02: ExecPlan drafted by Claude Code following v1 closeout. Profile of D_UNCLASSIFIED conducted from v1 outputs identified four concrete v1 rule defects (D2 outlet blind spot, D3 dead trigger column, D5 upper-bound exclusion, 4–29 day coverage gap). v2 ruleset proposes D2a/D2b split, D3 trigger fix, retained D5 with severe-persistent escalated to a new D6c, and three new D6 families covering the 4–29 day band and sub-severe magnitudes. Rationale: v1's 86% D_UNCLASSIFIED rate is operationally weak for downstream ablation campaigns; this plan refines the taxonomy from observable feature distributions rather than first principles.
- 2026-05-02: Execution-readiness pass by Codex. Fixed internal inconsistencies (D5 split semantics, dependency/fallback contract), added deterministic M3 calibration guardrails to prevent D2b threshold collapse, and added a D4 sentinel-family carve-out in acceptance criteria so precedent-linked sparse families are not accidentally merged away.
