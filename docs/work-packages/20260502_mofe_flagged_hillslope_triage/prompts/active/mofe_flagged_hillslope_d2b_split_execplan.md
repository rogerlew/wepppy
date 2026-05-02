# ExecPlan: MOFE Flagged Hillslope Taxonomy v3 (D2b Split)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

This plan is the third ExecPlan in the same work-package, succeeding `mofe_flagged_hillslope_triage_execplan.md` (v1) and `mofe_flagged_hillslope_taxonomy_refinement_execplan.md` (v2). It consumes v1 and v2 outputs and emits v3 outputs alongside them. It does not delete or rewrite v1 or v2.

## Purpose / Big Picture

The v2 ExecPlan eliminated the `D_UNCLASSIFIED` sink (`114 → 0`) but did so by creating a single dominant family `D2b` (`99 of 132 = 75.0%` of flagged hillslopes). On profiling, every `D2b` row originates from v1 `D_UNCLASSIFIED`, and the v2 `D2b` qofe-residual threshold (`> 1.0 m³`) sits at the extreme low tail of the D2b distribution (min `1.05`, p25 `13.44`, median `20.95`, max `245.96` m³); the rule does not discriminate, it admits. `D2b`'s mechanism hypothesis ("outlet-element accounting drift visible in the runoff-pass-vs-outlet check") is now load-bearing for 75% of the flagged dataset across closure residuals from 103 mm to 971 mm and persistence from 1 to 28 days. That hypothesis is too broad to bootstrap a focused ablation lane against — H2637 took weeks to root-cause as a single-hillslope incident.

After this work, a contributor opens `campaign_matrix_v3.csv` and sees the 99 `D2b` rows split into five sub-families along a deterministic severity × persistence grid (`D2b1`–`D2b5`). Each sub-family is bounded in severity and persistence, has a population between 5 and 41 hillslopes, and carries a mechanism hypothesis narrow enough to design ablation lanes against. The v3 work is rule design and re-emission of downstream artifacts (seeds, matrix, sensitivity sweep) for the affected families only — D1, D3, D4, D6b, D6c are unchanged from v2 and are propagated forward as-is.

Success is observable: `taxonomy_assignments_v3.csv` has zero `D2b` rows (the parent label is retired), every populated family has population ≥ 5 hillslopes (raised from v2's ≥ 3 gate to prevent another sparse-family scramble), and the largest family is ≤ 40% of flagged hillslopes (down from v2's 75% ceiling).

## Execution Preconditions

- v2 ExecPlan acceptance must already be passed; the artifacts directory must contain `triage_table_hillslopes.csv`, `triage_table_hillslopes_all.csv`, `triage_table_runs.csv`, `taxonomy_assignments.csv` (v1), `taxonomy_assignments_v2.csv`, `representative_seeds_v2.csv`, `campaign_matrix_v2.csv`, and `defect_families_v2.md`.
- `/wc1/runs` must remain mounted (consumed at M4 for shared-context checks on new D2b1–D2b5 representative seeds).
- Python environment: `pandas`, `numpy`, `sklearn` required; `hdbscan` and `sklearn_extra` optional accelerants. Same dependency contract as v2.
- If any precondition fails, record a blocker in `Surprises & Discoveries` and stop before M1.

## Progress

- [x] (2026-05-02) ExecPlan drafted; D2b internal structure profiled by Claude Code and load-bearing findings recorded under `Surprises & Discoveries`.
- [x] (2026-05-02) M1 complete. Authored `tools/split_d2b_taxonomy.py`; emitted `taxonomy_assignments_v3.csv` with counts `D2b1=41, D2b2=5, D2b3=13, D2b4=17, D2b5=23`, `carried_forward=33`, `total=132`; all M1 gates passed.
- [x] (2026-05-02) M2 complete. Cluster cross-check executed with `hdbscan(min_cluster_size=5)`; emitted `taxonomy_disagreements_v3.csv` (38 disagreements) and populated `cluster_label` + `rule_cluster_agreement` for all rows.
- [x] (2026-05-02) M3 complete. Emitted `representative_seeds_v3.csv` with 30 rows (10 families × 3 roles); all D2b1–D2b5 worst/median rows have `missing_shared_context == ""`; carried-forward `missing_shared_context` values match v2 byte-for-byte.
- [x] (2026-05-02) M4 complete. Emitted `campaign_matrix_v3.csv` (10 rows), `defect_families_v3.md`, `taxonomy_evolution_v3.md`, and `threshold_sensitivity_v3.csv` (120 rows across six thresholds).
- [x] (2026-05-02) M5 complete. Updated `package.md`, `tracker.md`, and this ExecPlan closeout sections.

## Surprises & Discoveries

- Observation: 100% of v2's D2b population originated in v1 D_UNCLASSIFIED. D2b is a renamed sink, not a rediscovered family.
  Evidence: cross-tab of `taxonomy_assignments.csv` × `taxonomy_assignments_v2.csv` over the 99 D2b rows; v1_origin Counter shows `D_UNCLASSIFIED: 99`.
- Observation: D2b is uniformly outlet-OFE topology with uniform ratio saturation. 99/99 have `outlier_is_outlet_ofe == True` and 99/99 have `late_max_qofe_to_q_ratio_max_abs ≥ n_ofe_max - 0.01`. Topology is not a usable splitting axis within D2b.
  Evidence: same profile.
- Observation: D2b stratifies cleanly on severity × persistence. The 99 rows distribute into 8 raw cells that collapse deterministically into the 5 v3 family cells with counts ranging from 5 to 41.
  Evidence: profile run produced raw grid `(M1=100-300mm, T1=≤3d): 41`, `(M1, T2=4-9d): 7`, `(M1, T3=10-29d): 6`, `(M2=300-500mm, T1): 5`, `(M2, T2): 12`, `(M2, T3): 5`, `(M3=500-1000mm, T2): 12`, `(M3, T3): 11`. Cells `(M3, T1)` and `(M*, T4=≥30d)` are empty because D4 and D6c already capture those rows ahead of D2b in v2 evaluation order.
- Observation: 40 of 99 D2b rows have `soilwater_to_porosity_fraction_p99 ≥ 0.99`. Storage saturation co-occurs with about 40% of D2b rows but does not align with any single severity × persistence cell — it is a co-occurring annotation, not a splitting dimension.
  Evidence: same profile.
- Observation: D2b's qofe-residual threshold of `> 1.0 m³` was never going to be discriminative on this data. The minimum value across D2b is `1.05 m³`, the 25th percentile is `13.44 m³`, the median is `20.95 m³`, and the maximum is `245.96 m³`. The threshold sits at the extreme tail of the distribution.
  Evidence: same profile.
- Observation: The split landed exactly on the proposed 5-cell counts (`41/5/13/17/23`) with zero unresolved rows; no post-hoc merge was required.
  Evidence: `split_d2b` run output and `taxonomy_assignments_v3.csv` family counts.
- Observation: The v3 cluster cross-check surfaces 38 disagreements (`38/132 = 28.8%`), concentrated in `D2b1` and `D2b3` and mostly in `cochlear-beriberi/disturbed9002-mofe` (31/38).
  Evidence: `taxonomy_disagreements_v3.csv` group-by `(runid, config)` and `family_primary`.
- Observation: Threshold sensitivity is mixed for split boundaries: 17/120 perturbation rows are unstable (`Jaccard < 0.7`), with the strongest instability around `severity_split_500` and `severity_split_300`.
  Evidence: `threshold_sensitivity_v3.csv` (`severity_split_500`: 8 unstable rows; `severity_split_300`: 4; `persistence_split_3`: 4; `severity_upper_1000`: 1; minimum Jaccard 0.20).

## Decision Log

- Decision: Split `D2b` on a severity × persistence grid; retire the `D2b` parent label.
  Rationale: Severity bands (100–300, 300–500, 500–1000 mm) and persistence bands (≤3 days, 4–29 days) carve the population into mechanism-tractable cells. Topology and ratio saturation are constant within D2b and would not split. Storage saturation is annotated but not split-on.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: Use flat IDs `D2b1`, `D2b2`, `D2b3`, `D2b4`, `D2b5` (numeric suffixes, no separators).
  Rationale: Preserves the v2→v3 lineage in the ID itself, keeps the family token as a single CSV-friendly word, and avoids exhausting the D-letter namespace prematurely.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: Raise the populated-family gate from v2's `>= 3` (with D4 sentinel exemption) to `>= 5` for v3, and add a "no family captures more than 40% of flagged rows" gate.
  Rationale: v2's `>= 3` gate allowed sparse-family merges to reshape the taxonomy mid-run; v2's lack of a maximum-fraction gate allowed `D2b` to absorb 75% of the dataset. v3's two-sided gate forces the split to be both granular enough and balanced enough.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: D4 keeps its v2 sentinel exemption from the `>= 5` minimum.
  Rationale: D4 is precedent-linked to the H2637 closure-spike incident, and the H2637 lane is already the consumer for D4 seeds. Population size (currently 2) does not invalidate that linkage.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: Emit storage saturation as a co-occurring annotation column (`storage_saturation_observed: bool`) on `taxonomy_assignments_v3.csv` rather than splitting families further on it.
  Rationale: Storage saturation co-occurs with ~40% of D2b rows but does not stratify cleanly within any severity × persistence cell. Splitting on it would multiply families without sharpening mechanism hypotheses.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: Carry forward D1, D3, D4, D6b, D6c assignments and representative seeds from v2 unchanged.
  Rationale: Those families were not affected by the D2b problem. Re-running their classification would be wasted work and would risk breaking the H2637 D4 linkage.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: Keep the M1 split thresholds unchanged after M2 disagreement review; do not relabel rows.
  Rationale: Disagreements are concentrated in adjacent outlet mild/moderate cells and primarily reflect geometric overlap in a confounded dominant run, not a deterministic-rule contract failure. The v3 goal was to retire the D2b sink while preserving auditable rule boundaries.
  Date/Author: 2026-05-02 / Codex.
- Decision: Use `hdbscan(min_cluster_size=5)` as the M2 clustering backend.
  Rationale: `hdbscan` was available in the runtime and is the first-choice algorithm in the ExecPlan fallback chain.
  Date/Author: 2026-05-02 / Codex.
- Decision: Set `D2b2` recommendation to `extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike`.
  Rationale: D2b2 is the explicit D4-adjacent cell (single-day, 300-500 mm) and is best treated as a lower-magnitude generalization lane of the H2637 closure-spike pattern before opening a fully separate incident.
  Date/Author: 2026-05-02 / Codex.
- Decision: Disposition all 38 M2 disagreements as accepted for now (no threshold retune in v3).
  Rationale: Each disagreement row was reviewed by family/cluster cohort (`D2b1`:16, `D2b3`:10, `D2b4`:3, `D1`:3, `D3`:2, `D6b`:2, `D6c`:1, `D4`:1). No cohort indicated a broken rule boundary; all map to intentional severity×persistence bins.
  Date/Author: 2026-05-02 / Codex.

## Outcomes & Retrospective

Execution completed on 2026-05-02.

Realized prevalence matched the proposed split exactly: `D2b1=41`, `D2b2=5`, `D2b3=13`, `D2b4=17`, `D2b5=23` (99 total ex-D2b rows). No D2b sub-family was empty and no merge was needed. The largest family is now `D2b1=41` (`31.1%` of flagged), below the v3 40% gate (`<=53` rows).

Sensitivity sweep on the six introduced thresholds produced 120 rows (5 families × 6 thresholds × 4 perturbations). Seventeen rows were unstable (`Jaccard < 0.7`), concentrated at `severity_split_500` and `severity_split_300`; this indicates boundary sensitivity near moderate/severe transitions but does not invalidate the split's primary objective (retire sink label, balance family mass).

Cluster cross-check disagreement count is 38 (`28.8%`). Disagreements were reviewed and accepted without relabeling or threshold retune for v3 because they concentrate in adjacent outlet cells and appear driven by overlap in the dominant run/config geometry rather than by deterministic-rule defects.

v3 is operationally ready for downstream ablation packaging with `campaign_matrix_v3.csv`, with one intentional precedent extension: `D2b2 -> extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike`.

## Context and Orientation

This plan is narrowly scoped — it splits one v2 family (`D2b`) while keeping the rest of the v2 taxonomy unchanged. A contributor can execute this plan without re-reading prior plans because all required file paths, rules, outputs, and acceptance gates are restated below. v1/v2 are referenced only for lineage and carry-forward provenance.

### Source data (read-only inputs)

All inputs are in `docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/`:

- `triage_table_hillslopes.csv` — 132 flagged hillslopes, 64-column feature schema. Primary input.
- `triage_table_hillslopes_all.csv` — 1166 audited hillslopes. M3 contrast-seed source.
- `taxonomy_assignments_v2.csv` — v2 family labels. Identifies the D2b rows to split.
- `representative_seeds_v2.csv` — v2 seeds. Carry-forward source for non-D2b families.
- `campaign_matrix_v2.csv` — v2 matrix. Carry-forward source for non-D2b family rows.

### Output location

All v3 outputs land under the same `artifacts/` directory. New files use the `_v3` suffix. v1 and v2 files are untouched.

### Term definitions (delta from v2)

- **Severity band**: a closed magnitude bin on `late_max_abs_ofe_closure_residual_mm_max_abs`. v3 uses three bands: `M1 = [100, 300)`, `M2 = [300, 500)`, `M3 = [500, 1000]`. Boundaries chosen because they align with v2 family boundaries (D2b's lower bound at 100 mm, D4's bound at 500 mm, D1's bound at 1000 mm).
- **Persistence band**: a closed bin on `requires_scientific_review_days`. v3 uses two bands: `T1 = [1, 3]` (single-day-or-near-single), `T2 = [4, 29]` (multi-day moderate). Persistence ≥ 30 is captured by D5 / D6c upstream and never reaches D2b in v2's evaluation order.
- **Severity × persistence cell**: a (Mi, Tj) pair. v3 splits D2b into the five non-empty cells of this grid.

## Plan of Work

### M1 — Author the v3 split ruleset

Goal: implement the D2b split, emit `taxonomy_assignments_v3.csv`, and verify the acceptance gates.

Tool to author: `tools/split_d2b_taxonomy.py`. Default no-arg invocation reads from this work-package's artifacts directory and writes back to it. The script must:

1. Read `taxonomy_assignments_v2.csv` and `triage_table_hillslopes.csv`.
2. For every row not assigned `D2b` in v2, copy the v2 family assignment unchanged into v3 (`family_primary`, `family_secondary`, `family_tertiary`, `family_rationale`, `cluster_label`, `rule_cluster_agreement` all preserved).
3. For every row assigned `D2b` in v2, apply the v3 split rules (below) and assign one of `D2b1`–`D2b5`. Set `family_secondary` and `family_tertiary` to blank for split rows; rewrite `family_rationale` with a sentence naming the (severity, persistence) cell. Leave `cluster_label` and `rule_cluster_agreement` blank for split rows; M2 will populate them.
4. Add a new column `storage_saturation_observed` (bool) to every row, derived as `soilwater_to_porosity_fraction_p99 >= 0.99` (False if the value is null).
5. Verify the acceptance gates and exit non-zero if any gate fails.

#### v3 D2b split rules

For each v2 D2b row, evaluate in order:

- **D2b1 — Outlet sub-severe single-day mild.** `requires_scientific_review_days <= 3` AND `100 <= late_max_abs_ofe_closure_residual_mm_max_abs < 300`. Mechanism hypothesis: low-magnitude single-day surge at the outlet element; likely numerical noise just above the audit threshold. Expected count ≈ 41.
- **D2b2 — Outlet sub-severe single-day moderate.** `requires_scientific_review_days <= 3` AND `300 <= late_max_abs_ofe_closure_residual_mm_max_abs < 500`. Mechanism hypothesis: D4-adjacent single-day spike below the severe-magnitude bar; ablation lane should test whether the H2637 fix generalizes. Expected count ≈ 5.
- **D2b3 — Outlet sub-severe multi-day mild.** `4 <= requires_scientific_review_days <= 29` AND `100 <= late_max_abs_ofe_closure_residual_mm_max_abs < 300`. Mechanism hypothesis: low-magnitude multi-day pattern; candidate parameter or boundary-condition error rather than numerical surge. Expected count ≈ 13.
- **D2b4 — Outlet sub-severe multi-day moderate.** `4 <= requires_scientific_review_days <= 29` AND `300 <= late_max_abs_ofe_closure_residual_mm_max_abs < 500`. Mechanism hypothesis: same as D2b3 but more severe; warrants its own lane because the magnitude band is mechanism-distinguishing. Expected count ≈ 17.
- **D2b5 — Outlet sub-severe multi-day severe.** `4 <= requires_scientific_review_days <= 29` AND `500 <= late_max_abs_ofe_closure_residual_mm_max_abs <= 1000`. Mechanism hypothesis: structural model gap — sustained severe outlet residual without ratio saturation crossing into D1's > 1000 mm band. Expected count ≈ 23.

Every D2b row must match exactly one rule (the cells partition the (severity, persistence) grid for the in-range data). If a row matches none, emit `family_primary = D_UNRESOLVED_D2B_SPLIT` and write the row to `Surprises & Discoveries` with its exact severity and persistence values; do not silently absorb it.

#### Acceptance gates for M1

1. `taxonomy_assignments_v3.csv` has 132 rows.
2. Zero rows have `family_primary == "D2b"` (the parent label is retired).
3. Zero rows have `family_primary == "D_UNRESOLVED_D2B_SPLIT"`.
4. Zero rows have `family_primary == "D_UNCLASSIFIED"` (carry-forward should not introduce one; verify).
5. Every populated family except D4 has `>= 5` rows.
6. The largest family by count is `<= 53` rows (40% of 132). If exceeded, the split has not stratified D2b enough — record in `Decision Log` and stop.
7. Tool prints the line `split_d2b: D2b1=<a> D2b2=<b> D2b3=<c> D2b4=<d> D2b5=<e>; carried_forward=<f> total=132`.

### M2 — Cluster cross-check (v3)

Goal: validate v3 labels against feature-space geometry and record disagreements.

Procedure mirrors v2 M4: standardize the magnitude, topology, chain, storage, and temporal feature columns from `triage_table_hillslopes.csv`; run HDBSCAN with `min_cluster_size=5` (fall back to k-medoids then KMeans if unavailable; record selection in `Decision Log`); populate `cluster_label` and `rule_cluster_agreement` columns on all 132 rows of `taxonomy_assignments_v3.csv` (overwrite the blanks left by M1 for split rows; recompute for carried-forward rows because the cluster geometry changes when D2b explodes into five labels).

Output: `taxonomy_disagreements_v3.csv` listing all disagreement rows with all M1 columns, `family_primary`, and `cluster_label`. Disposition every disagreement in `Decision Log` (relabel, retune, or accept).

Acceptance for M2: file exists; disagreement count is reported in `Surprises & Discoveries`; every disagreement has a Decision Log entry.

### M3 — Representative seeds (v3)

Goal: select worst/median/contrast seeds for D2b1–D2b5; carry forward D1/D3/D4/D6b/D6c seeds from v2.

Output: `representative_seeds_v3.csv`. Schema matches v2 `representative_seeds_v2.csv`.

For D2b1–D2b5: apply the v2 selection rules (worst = max `late_max_abs_ofe_closure_residual_mm_max_abs` within the family; median = closest to family median, ties broken by lower `requires_scientific_review_days`; contrast = nearest unflagged hillslope from the same (runid, config) by L2 distance in standardized feature space, using `triage_table_hillslopes_all.csv` as the candidate pool). Staged-input manifest population unchanged from v2.

For D1, D3, D4, D6b, D6c: copy the corresponding rows from `representative_seeds_v2.csv` verbatim. Do not re-run selection.

Acceptance for M3: total row count is `3 * 10 = 30` (5 split families + 5 carried-forward families × 3 roles each); every D2b1–D2b5 worst and median row has `missing_shared_context == ""`; every carried-forward row's `missing_shared_context` matches the v2 value byte-for-byte unless the idempotence recovery path is invoked for manifest drift.

### M4 — Campaign matrix v3, narrative, lineage, and sensitivity

Goal: emit the ablation-ready v3 matrix and supporting documents.

Outputs:

1. `campaign_matrix_v3.csv` — same schema as v2. One row per populated family (10 rows expected). For D2b1–D2b5: each row gets a distinct mechanism hypothesis copied from M1's rule definitions, a representative seed triplet, and a `recommendation` of `new_incident` (with one exception below). For D1, D3, D4, D6b, D6c: copy v2 rows verbatim, including their `recommendation` (D4 retains `extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike`).

   Exception for D2b2: because D2b2 is the D4-adjacent band (single-day, 300–500 mm), its `recommendation` should be `extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike` if the H2637 incident's ablation lane work is plausibly applicable to magnitudes below 500 mm. Default to `new_incident` if Codex cannot defend the extension; record the choice in `Decision Log`.

2. `defect_families_v3.md` — one paragraph per family (10 paragraphs). For D2b1–D2b5: prevalence (n hillslopes, % of flagged), severity band, persistence band, mechanism hypothesis, fraction with `storage_saturation_observed == True`, recommended next step. For D1, D3, D4, D6b, D6c: a one-sentence "unchanged from v2" pointer plus the v2 paragraph repeated for self-containment.

3. `taxonomy_evolution_v3.md` — short document (≤ 300 words). Required sections: "What changed" (one sentence: D2b retired, split into D2b1–D2b5 on severity × persistence; carry-forward families unchanged), "Coverage delta" (table: family, v2 count, v3 count), "Disposition of v2 D2b" (table: D2b1–D2b5 with cell coordinates and counts).

4. `threshold_sensitivity_v3.csv` — perturbation sweep limited to the new D2b1–D2b5 thresholds (severity boundaries 100, 300, 500, 1000 mm; persistence boundaries 3 and 29 days). Same format as v2 `threshold_sensitivity.csv`. Perturbations: ±10%, ±25% on each threshold. Jaccard ≥ 0.7 = stable; < 0.7 = unstable. Record any unstable threshold in `Surprises & Discoveries`. Do not re-sweep the carried-forward families; v2 already covered them.

Acceptance for M4: all four files exist; matrix row count = 10; every D2b sub-family has a non-empty mechanism hypothesis paragraph in `defect_families_v3.md`; sensitivity sweep covers all six v3-introduced thresholds.

### M5 — Closeout

Goal: integrate v3 outputs into the work-package narrative.

Steps:

1. Update `package.md` `Follow-up Work` to note v3 outputs and the operational status of `campaign_matrix_v3.csv`. Do not change the "Open ablation execution packages" line.
2. Update `tracker.md` with the v3 milestone timeline and final family counts.
3. Fill in this ExecPlan's `Outcomes & Retrospective`.
4. Mark all `Progress` items checked.

Acceptance for M5: `package.md` mentions v3 alongside v2; `tracker.md` reflects v3 closeout; this file's retrospective is non-empty; all Progress items checked.

## Concrete Steps

All commands run from the repository root `/workdir/wepppy` unless noted.

Step 0. Verify preconditions:

    test -f docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/taxonomy_assignments_v2.csv
    test -f docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/representative_seeds_v2.csv
    test -d /wc1/runs
    .venv/bin/python -c "import pandas, numpy, sklearn"

Step 1. Author `tools/split_d2b_taxonomy.py` (M1). Run:

    .venv/bin/python tools/split_d2b_taxonomy.py

Expected transcript fragment (approximate counts; may vary by ±2 in any cell):

    split_d2b: D2b1=41 D2b2=5 D2b3=13 D2b4=17 D2b5=23; carried_forward=33 total=132

Validate:

    awk -F, 'NR>1 {c[$4]++; tot++} END{for(k in c) print k": "c[k]; print "total="tot}' \
      docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/taxonomy_assignments_v3.csv

Expect `D2b` absent and the largest count `<= 53`.

Step 2. Run M2 cluster cross-check. Codex may extend `tools/split_d2b_taxonomy.py` or call back into existing pipeline modules — either is acceptable.

Step 3. Run M3 seed selection.

Step 4. Run M4 matrix + narrative + lineage + sensitivity.

Step 5. Closeout (M5).

## Validation and Acceptance

Final acceptance for the v3 phase is observable behavior:

1. A reviewer opens `campaign_matrix_v3.csv` and sees 10 rows, none labeled `D2b` or `D_UNCLASSIFIED`. Each D2b1–D2b5 row names a (severity, persistence) cell, a mechanism hypothesis distinct from its siblings, a representative seed triplet, and a recommendation.
2. The largest family by count is `<= 53` rows (40% of flagged). If a future audit-tool change shifts the D2b distribution, this gate must continue to hold or M1 must iterate.
3. `defect_families_v3.md` answers "what mechanism families are operationally distinct?" with 10 paragraphs that a science maintainer can read in under five minutes.
4. `taxonomy_evolution_v3.md` shows the v2 → v3 D2b disposition row-count by row-count.
5. `threshold_sensitivity_v3.csv` covers all six new thresholds; any Jaccard < 0.7 perturbation is referenced in `Surprises & Discoveries` with an explicit follow-up note.
6. `package.md` and `tracker.md` reference v3 outputs.

A negative finding ("D2b1 dominates at > 40% even after the split; severity boundaries need finer slicing") is acceptable. Record it in `Outcomes & Retrospective` and either iterate within M1 or stop with the gate failure documented; do not lower the gate.

## Idempotence and Recovery

All v3 tools overwrite their own outputs. Re-running after a rule tweak is safe; v1 and v2 outputs are untouched. The carry-forward step is purely a CSV copy and is idempotent.

If M1 fails the 40% maximum-family gate, iterate within the milestone — likely candidates are tightening the M3 (500–1000 mm) band into M3a (500–700) and M3b (700–1000), or splitting D2b1's 41-row population further by chain residual quartiles. Do not advance to M2 with a failing gate.

If the carried-forward seed manifests have changed on disk between v2 and v3 execution (for example, `/wc1/runs/.../wepp_ui.txt` deleted), record the change as a v2 regression in `Surprises & Discoveries` and re-run the v2 seed selection for that family — do not silently propagate stale paths.

## Artifacts and Notes

Final v3 artifact additions to `docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/`:

    artifacts/
    ├── taxonomy_assignments_v3.csv     (M1, M2)
    ├── taxonomy_disagreements_v3.csv   (M2)
    ├── representative_seeds_v3.csv     (M3)
    ├── campaign_matrix_v3.csv          (M4)
    ├── defect_families_v3.md           (M4)
    ├── taxonomy_evolution_v3.md        (M4)
    └── threshold_sensitivity_v3.csv    (M4)

v1 and v2 artifacts are untouched. The `tools/split_d2b_taxonomy.py` module is the new authored code; reuse of `tools/refine_mofe_taxonomy.py` and `tools/triage_pipeline.py` for clustering, seed selection, and sensitivity is encouraged.

## Interfaces and Dependencies

Required tool: `tools/split_d2b_taxonomy.py`. Public CLI (defaults shown):

    .venv/bin/python tools/split_d2b_taxonomy.py \
        --input-dir docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts \
        --output-dir docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts \
        [--no-cluster] [--no-sensitivity]

Same flag semantics as v2's `tools/refine_mofe_taxonomy.py`.

Dependencies: `pandas`, `numpy`, `sklearn`; `hdbscan` and `sklearn_extra` optional. No new pinned dependencies.

Read-only consumed interfaces:

- `triage_table_hillslopes.csv` and `triage_table_hillslopes_all.csv` — schemas treated as frozen contracts from v1.
- `taxonomy_assignments_v2.csv` — read at M1 to identify D2b rows and to carry forward non-D2b family assignments. Never written.
- `representative_seeds_v2.csv` — read at M3 to carry forward non-D2b family seeds. Never written.
- `campaign_matrix_v2.csv` and `defect_families_v2.md` — read at M4 to carry forward non-D2b family rows and paragraphs. Never written.

## Revision Notes

- 2026-05-02: ExecPlan drafted by Claude Code following v2 closeout. v2's D2b family was identified as a renamed v1 D_UNCLASSIFIED sink (99/99 D2b rows came from v1 D_UNCLASSIFIED) and as too broad to seed an ablation campaign. Profile of D2b on the severity × persistence grid revealed five non-empty cells with cell counts 5–41, giving a deterministic split rule. v3 retires the D2b parent label, introduces D2b1–D2b5, raises the populated-family gate to ≥ 5 (D4 sentinel-exempt), adds a 40% maximum-family gate to prevent another single-family takeover, and emits storage saturation as a co-occurring annotation rather than a splitting axis. Carry-forward of D1/D3/D4/D6b/D6c is mechanical; only D2b is reworked.
- 2026-05-02: Execution-readiness pass by Codex. Corrected a quantitative overstatement in the Purpose section (qofe residual threshold position in D2b distribution), tightened self-containment language in Context and Orientation to match the ExecPlan contract, and reconciled M3 acceptance wording with the documented manifest-drift recovery path.
