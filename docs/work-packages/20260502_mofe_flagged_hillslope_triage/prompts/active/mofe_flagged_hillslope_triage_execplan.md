# ExecPlan: MOFE Flagged Hillslope Triage for Ablation Campaign Design

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, a future contributor can open `docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/campaign_matrix.csv` and see a defensible defect taxonomy that maps every flagged hillslope from the MOFE 260501 validation campaign to a defect family, names representative seeds with full staged-input paths, and proposes ablation incident packages ready to bootstrap with `.venv/bin/python /workdir/wepp-forest/tools/ablation_protocol.py init`. The triage output is the bridge between bulk validation flagging and per-incident ablation work — without it, downstream ablations either retread H2637 or scatter across uncorrelated outliers.

The deliverable is data + analysis, not model surgery. No WEPP simulations are launched by this plan.

## Execution Preconditions

- `/workdir/wepp-forest` must be available locally with:
  - `/workdir/wepp-forest/docs/ablation/protocol.md`
  - `/workdir/wepp-forest/tools/ablation_protocol.py`
- `/wc1/runs` must be mounted for live run-context (`wepp.nodb`) and staged-input existence checks.
- Python environment must include `pandas`, `numpy`, `hdbscan`, `sklearn_extra`, and `sklearn`.
- If any precondition fails, record a blocker in `Surprises & Discoveries` and stop before M1.

## Progress

- [x] (2026-05-02) Work-package created.
- [x] (2026-05-02) ExecPlan rewritten to PLANS.md contract; Phase 1 schema and selectors pre-defined.
- [x] (2026-05-02) M1. Built `tools/build_mofe_triage_table.py` and emitted `triage_table_runs.csv`, `triage_table_hillslopes.csv`, `triage_table_hillslopes_all.csv`; acceptance checks passed (`4` runs, `132` flagged, `1166` total).
- [x] (2026-05-02) M2. Applied deterministic D1-D5 rules and emitted `taxonomy_assignments.csv` with complete `family_primary` + non-empty rationale on all 132 flagged rows.
- [x] (2026-05-02) M3. Ran cluster cross-check with HDBSCAN (`min_cluster_size=5`), added `cluster_label` + `rule_cluster_agreement`, emitted `taxonomy_disagreements.csv`, and dispositioned all disagreements.
- [x] (2026-05-02) M4. Emitted `representative_seeds.csv` with worst/median/contrast seeds for populated D-families; staged-input manifests resolved and worst/median seeds have no missing shared-context files.
- [x] (2026-05-02) M5. Emitted `precedent_crosswalk.md` covering all incident directories matching `*_hillslope_*` and family coverage for `D0`–`D5` (plus `D_UNCLASSIFIED`).
- [x] (2026-05-02) M6. Emitted `campaign_matrix.csv` + `defect_families.md`; closeout analysis and retrospective completed.

## Surprises & Discoveries

- Observation: The flag rate is heavily concentrated. Of 132 flagged hillslopes (1166 audited), ~73% live in `cochlear-beriberi/disturbed9002-mofe`. Two of the four runs flag zero hillslopes. Triage must test for runid/config confounding before clustering.
  Evidence: `defect_summary.md` reports 96/520, 36/333, 0/209, 0/104 across the four runs.
- Observation: `late_max_qofe_to_q_ratio` saturates at `n_ofe_max` (≈16) across percentiles. The protocol's `>= 2.0` ratio threshold is functionally redundant for 16-OFE hillslopes; the flag is driven by the closure-mm and pulse-mm thresholds.
  Evidence: `cochlear-beriberi/H461` summary JSON, `full_physical_closure.late_max_qofe_to_q_ratio.{p50, p99}` both ≈ 16.0.
- Observation: Deterministic D1-D5 rules leave a large residual class: `114/132` flagged hillslopes classify as `D_UNCLASSIFIED`, concentrated in two runs.
  Evidence: `taxonomy_assignments.csv` family counts: `D_UNCLASSIFIED=114`, `D1=13`, `D2=3`, `D4=2`.
- Observation: Named `D_UNCLASSIFIED` hillslopes were explicitly carried forward (not dropped) for future taxonomy expansion.
  Evidence: `cochlear-beriberi` = `H3,H13,H25,H32,H34,H38,H42,H63,H65,H67,H68,H71,H80,H99,H105,H106,H107,H111,H112,H120,H125,H131,H136,H141,H148,H150,H152,H154,H191,H199,H215,H218,H228,H239,H246,H251,H254,H255,H259,H265,H267,H268,H273,H275,H278,H282,H295,H305,H312,H317,H339,H346,H351,H354,H360,H378,H399,H400,H403,H409,H412,H422,H428,H440,H448,H457,H463,H465,H468,H472,H476,H488,H492,H495,H498,H501,H504,H513,H516`; `ordained-incentive` = `H17,H33,H52,H61,H66,H71,H80,H81,H93,H95,H96,H104,H110,H138,H141,H151,H154,H157,H161,H174,H195,H198,H201,H204,H213,H219,H221,H224,H249,H257,H273,H276,H284,H288,H289`.
- Observation: HDBSCAN disagreements are sparse and localized (`4/132`), all within `cochlear-beriberi` cluster label `2`.
  Evidence: `taxonomy_disagreements.csv` rows: `H84 (D4)`, `H146 (D1)`, `H202 (D1)`, `H431 (D1)`.

## Decision Log

- Decision: Replace the original F1–F4 family draft with a deterministic D0–D5 taxonomy.
  Rationale: F1–F4 leaned on the ratio axis, which the data show is degenerate for these runs. D0 captures config-correlation as a first-class possibility; D1–D5 separate by outlier OFE position, chain transfer evidence, storage saturation, temporal isolation, and persistence. The new taxonomy is auditable from observable columns alone.
  Date/Author: 2026-05-02 / Claude Code (drafted), Codex (to execute and validate).
- Decision: Two output tables (runs + hillslopes) instead of one wide table.
  Rationale: Run-level fields (mods, wepp_bin, n_total, flag_rate) are constant within a runid and would otherwise duplicate across rows. Two tables join cleanly on (runid, config) and keep observation rows narrow.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: Read run-context fields (`_wepp_bin`, `_mods`, `_multi_ofe`, `wd`) from `/wc1/runs/<prefix>/<runid>/wepp.nodb` directly rather than re-parsing the JSON snippets in `defect_summary.md`.
  Rationale: `/wc1` is mounted in the working environment; `wepp.nodb` is the source of truth and the snippet in `defect_summary.md` is a frozen archival copy. Reading the live file keeps run-context fields trustworthy if the validation set is regenerated. Fall back to `defect_summary.md` parsing only if the file is unreadable.
  Date/Author: 2026-05-02 / Claude Code.
- Decision: Implement M2-M6 as a reproducible script pipeline (`tools/triage_pipeline.py`) rather than manual one-off notebook steps.
  Rationale: Keeps deterministic rule assignment, clustering, seed selection, and reporting rerunnable from M1 outputs with a single command and no hidden state.
  Date/Author: 2026-05-02 / Codex.
- Decision: Use HDBSCAN (`min_cluster_size=5`) for M3 clustering; no fallback was required.
  Rationale: `hdbscan` was available in the environment and produced stable cluster/noise partitioning with only 4 disagreements against rules.
  Date/Author: 2026-05-02 / Codex.
- Decision: Do not retune D1-D5 thresholds during M3; accept disagreements for `H84`, `H146`, `H202`, and `H431`.
  Rationale: Disagreements are minority points in a mixed cluster (`cluster_label=2`) dominated by `D_UNCLASSIFIED`; D1/D4 primary-rule predicates still hold strongly for those rows (`outlier_is_outlet_ofe=True` with severe late residuals and D4 day-count condition).
  Date/Author: 2026-05-02 / Codex.
- Decision: Keep `cochlear-beriberi/H84` as `D4` (not relabeled).
  Rationale: Rule predicate remains exact (`requires_scientific_review_days=2`, `late_max_abs_ofe_closure_residual_mm_max_abs=506.304>=500`); disagreement is cluster-context, not rule failure.
  Date/Author: 2026-05-02 / Codex.
- Decision: Keep `cochlear-beriberi/H146` as `D1` (not relabeled).
  Rationale: Rule predicate remains exact (`outlier_is_outlet_ofe=True`, `late_max_abs_ofe_closure_residual_mm_max_abs=1247.79>1000`, ratio saturation true).
  Date/Author: 2026-05-02 / Codex.
- Decision: Keep `cochlear-beriberi/H202` as `D1` (not relabeled).
  Rationale: Rule predicate remains exact (`outlier_is_outlet_ofe=True`, `late_max_abs_ofe_closure_residual_mm_max_abs=1207.166>1000`, ratio saturation true).
  Date/Author: 2026-05-02 / Codex.
- Decision: Keep `cochlear-beriberi/H431` as `D1` (not relabeled).
  Rationale: Rule predicate remains exact (`outlier_is_outlet_ofe=True`, `late_max_abs_ofe_closure_residual_mm_max_abs=1153.171>1000`, ratio saturation true).
  Date/Author: 2026-05-02 / Codex.
- Decision: Do not apply D0 demotion.
  Rationale: No D1-D5 family satisfied all D0 demotion criteria simultaneously (no qualifying family had 5-of-6 standardized deltas `<=0.35` with max delta `<=0.75` at required concentration/size thresholds).
  Date/Author: 2026-05-02 / Codex.
- Decision: Exclude `D_UNCLASSIFIED` from M4 representative-seed triplets.
  Rationale: M4 contract is “per populated D-family”; `D_UNCLASSIFIED` is retained as a taxonomy-gap sink and is not a mechanistic D-family for direct ablation package bootstrapping.
  Date/Author: 2026-05-02 / Codex.

## Outcomes & Retrospective

Execution completed on 2026-05-02. Realized prevalence did not match the initial expectation that D0 would dominate:

- `D0`: `0`
- `D1`: `13`
- `D2`: `3`
- `D3`: `0`
- `D4`: `2`
- `D5`: `0`
- `D_UNCLASSIFIED`: `114`

Interpretation:
- The deterministic D1-D5 rules identify a small set of high-signal mechanistic spikes (`D1`, `D2`, `D4`) but leave most flagged hillslopes outside the current rule envelope.
- No flagged hillslopes were dropped; unmatched rows were explicitly classified as `D_UNCLASSIFIED` with rationales and named in `Surprises & Discoveries`.
- The cluster check found only 4 disagreements and did not justify threshold retuning in this pass.

Closeout artifacts:
- `triage_table_runs.csv`, `triage_table_hillslopes.csv`, `triage_table_hillslopes_all.csv`
- `taxonomy_assignments.csv`, `taxonomy_disagreements.csv`
- `representative_seeds.csv`
- `precedent_crosswalk.md`
- `campaign_matrix.csv`
- `defect_families.md`

Open science-maintainer questions:
1. Should `D_UNCLASSIFIED` be split by additional dimensions (for example lower-amplitude persistent regimes or mixed outlet/interior behavior) before launching broad ablation campaigns?
2. Should D2 chain thresholds be lowered for this campaign because observed residual magnitudes are near-zero in many flagged rows despite interior anomalies?

## Context and Orientation

### Source data (read-only inputs)

All inputs are already in the repository under `docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts/`:

- `hillslope_audit_rollup.csv` — 1166 rows, header is `runid,config,wepp_id,topaz_id,requires_scientific_review,requires_scientific_review_days,max_abs_closure_mm,max_abs_ofe_closure_mm,max_abs_chain_surface_m3,max_abs_chain_subsurface_m3,summary_json_path,top_days_csv_path`. The `summary_json_path` and `top_days_csv_path` columns hold absolute paths into the same artifact tree.
- `validation_summary.json` — campaign metadata (binary, host, verdict). Reference only.
- `defect_summary.md` — per-run narrative including embedded `wepp.nodb` JSON snippets. Use as fallback for run-context fields.
- `<runid>_<config>/H<wepp_id>/hillslope_mofe_daily_closure_audit_summary.json` — per-hillslope rollup of closure metrics. **Primary source for the per-hillslope feature columns.** Schema is fixed by `tools/hillslope_mofe_daily_closure_audit.py`.
- `<runid>_<config>/H<wepp_id>/hillslope_mofe_daily_closure_audit_top_days.csv` — per-hillslope worst-day rows. Used only for representative-seed evidence at M4, not for table-building.

The four (runid, config) pairs in the dataset are: `moth-eaten-blackhead/disturbed9002-wbt-mofe` (0/209), `cochlear-beriberi/disturbed9002-mofe` (96/520), `ordained-incentive/disturbed9002-wbt-mofe` (36/333), `uninsured-deformation/disturbed9002-wbt-mofe` (0/104).

### Live data (read-only, optional)

`/wc1/runs/<prefix>/<runid>/wepp.nodb` (where `<prefix>` is the first two characters of `<runid>`, e.g. `co/cochlear-beriberi`). This is the WEPP NoDb singleton dump — a JSON-on-disk file. Read fields under `py/state`: `_wepp_bin`, `_mods` (list of strings), `_multi_ofe` (bool), `_config` (string ending in `.cfg`), `wd` (run working directory).

### Output location

All outputs land under `docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/`. Codex must create that directory at the start of M1.

### Term definitions (plain language)

- **Flagged hillslope**: a hillslope where `requires_scientific_review = True` in the rollup. The audit tool sets this when, in the late-OFE window of the WEPP run, simultaneously: closure residual ≥ 100 mm, surface pulse proxy ≥ 100 mm, and (when computable) outlet-OFE-to-watershed flow ratio ≥ 2.0.
- **Late OFE window**: the last 3 OFEs (Overland Flow Elements) in a WEPP hillslope profile. `late_ofe_window=3` in the audit summary's `requires_scientific_review_thresholds`.
- **Outlier OFE**: the single OFE within the late window that produced the worst residual on the worst flagged day. Read from `full_physical_closure.max_requires_scientific_review_day.late_outlier_ofe_id`.
- **MOFE chain residual**: WEPP routes water and sediment between OFEs; the audit reconstructs upstream→downstream balances and reports the residual. Surface and subsurface chain residuals appear in the `mofe_chain` block of the summary JSON.
- **Closure residual**: precipitation + storage change − ET − runoff − lateral flow − percolation. Reported in mm/day per OFE and aggregated. Appears under `full_physical_closure.closure_residual_mm` and similar.
- **Defect family**: a label assigned by the M2 taxonomy that groups hillslopes presumed to share a common physical or numerical mechanism for flagging.
- **Representative seed**: a single hillslope chosen to stand in for its defect family during downstream ablation work. Identified by (runid, wepp_id) and accompanied by the staged-input path manifest.

### Flagging Contract (verbatim from the audit tool, for reference)

The day is `requires_scientific_review = True` when in the late-OFE window (last 3 OFEs):
- `late_max_abs_ofe_closure_residual_mm >= 100.0`, and
- `late_max_surface_pulse_proxy_mm >= 100.0`, and
- if computable, `late_max_qofe_to_q_ratio >= 2.0`.

Hillslope-level flag = at least one flagged day. Threshold values are also recorded in each summary JSON under `full_physical_closure.requires_scientific_review_thresholds`.

### Scope

In scope: deriving labels and seeds from existing artifacts; producing the campaign matrix.

Out of scope: changing audit thresholds, re-running WEPP, modifying the model, opening downstream ablation incident packages (those are spawned *from* this work-package's outputs).

## Plan of Work

The work decomposes into six milestones, each producing one or more files and a clear acceptance check. M1 is the only milestone with a fully frozen schema; M2–M6 specify required columns and formats but allow Codex to resolve secondary details autonomously.

### M1 — Build the triage tables

Goal: emit two primary CSVs that fully describe every flagged hillslope and every (runid, config) pair, plus one all-hillslope helper CSV used by M4 contrast-seed selection.

Tool to author: `tools/build_mofe_triage_table.py`. The script must accept `--rollup-csv`, `--output-dir`, and `--include-passing/--no-include-passing` flags (default exclude passing rows from `triage_table_hillslopes.csv`). The script must also always emit `triage_table_hillslopes_all.csv` (all audited hillslopes) so M4 does not depend on rerunning M1 with different flags. Default values must point to this work-package's input/output paths so a no-arg invocation works.

#### Phase 1 schema — `triage_table_runs.csv`

One row per (runid, config) present in the rollup. Four rows expected from current data (four configs total; emit one row per pair). Columns are listed in order. Selector format: `rollup` = column from `hillslope_audit_rollup.csv`; `wepp.nodb` = JSON path from `/wc1/runs/<prefix>/<runid>/wepp.nodb` under `py/state`; `derived` = computed by the tool.

| Column | Type | Nullable | Selector | Description |
| --- | --- | --- | --- | --- |
| `runid` | str | no | `rollup.runid` (first occurrence) | Run identifier, e.g. `cochlear-beriberi`. |
| `config` | str | no | `rollup.config` | Configuration filename without `.cfg`. |
| `wepp_bin` | str | yes | `wepp.nodb._wepp_bin` | Binary identifier, e.g. `wepp_260501`. |
| `mods` | str | yes | `wepp.nodb._mods` joined with `;` | Active mod set, semicolon-joined. |
| `multi_ofe` | bool | yes | `wepp.nodb._multi_ofe` | True for MOFE runs. |
| `wd` | str | yes | `wepp.nodb.wd` | Run working directory absolute path. |
| `staged_runs_dir` | str | yes | `derived` = `wd + "/wepp/runs"` | Path to the directory holding `p<id>.run` files. |
| `n_hillslopes_total` | int | no | `derived` = count of rollup rows for the pair | All audited hillslopes in this run. |
| `n_hillslopes_flagged` | int | no | `derived` = count where `requires_scientific_review == True` | Count of flagged hillslopes. |
| `flag_rate_pct` | float (1 dp) | no | `derived` = 100 * flagged / total | Round to one decimal place. |
| `max_abs_closure_mm_run_max` | float | no | `derived` = max of `rollup.max_abs_closure_mm` for the pair | Worst single-hillslope closure magnitude in the run. |
| `max_abs_ofe_closure_mm_run_max` | float | no | `derived` = max of `rollup.max_abs_ofe_closure_mm` for the pair | Worst per-OFE closure magnitude. |
| `wepp_nodb_path` | str | yes | `derived` = `/wc1/runs/<prefix>/<runid>/wepp.nodb` where `<prefix>=runid[:2]` | Source path for `wepp.nodb` lookups. |
| `wepp_nodb_source` | str | no | `derived`, one of `live_wc1`, `defect_summary_md`, `unavailable` | How run-context fields were obtained. |

Fallback rule for run-context fields: if `wepp_nodb_path` is unreadable, parse the embedded JSON in `defect_summary.md` (search for the line `- binary evidence B (run artifact snippet): \`<path>:1:<json>\`` within the per-run section `## <runid> / <config>`). Set `wepp_nodb_source = defect_summary_md`. If neither succeeds, set fields to null and `wepp_nodb_source = unavailable`; emit a non-fatal warning.

#### Phase 1 schema — `triage_table_hillslopes.csv`

One row per flagged hillslope. 132 rows expected from current data. Filter applied: `rollup.requires_scientific_review == True` (boolean, after parse/normalization). The `summary_json` column refers to the per-hillslope summary JSON; selectors are dot-paths starting at the JSON root. Use `null` (empty cell) when any element of the path is absent.

Identification:

| Column | Type | Nullable | Selector | Description |
| --- | --- | --- | --- | --- |
| `runid` | str | no | `rollup.runid` | Joins to `triage_table_runs.runid`. |
| `config` | str | no | `rollup.config` | Joins to `triage_table_runs.config`. |
| `wepp_id` | int | no | `rollup.wepp_id` | Hillslope id; matches `H<wepp_id>` directory and `p<wepp_id>.run`. |
| `topaz_id` | int | yes | `rollup.topaz_id` | Often blank in MOFE configs. |
| `summary_json_path` | str | no | `rollup.summary_json_path` | Source-of-truth artifact for downstream readers. |
| `top_days_csv_path` | str | no | `rollup.top_days_csv_path` | Used at M4 for evidence. |

Magnitude axis (all selectors rooted at `summary_json.full_physical_closure` unless noted):

| Column | Type | Nullable | Selector |
| --- | --- | --- | --- |
| `late_max_abs_ofe_closure_residual_mm_max_abs` | float | no | `late_max_abs_ofe_closure_residual_mm.max_abs` |
| `late_max_abs_ofe_closure_residual_mm_p99` | float | no | `late_max_abs_ofe_closure_residual_mm.p99` |
| `late_max_abs_ofe_closure_residual_mm_p95` | float | no | `late_max_abs_ofe_closure_residual_mm.p95` |
| `late_max_abs_ofe_closure_residual_mm_p90` | float | no | `late_max_abs_ofe_closure_residual_mm.p90` |
| `late_max_surface_pulse_proxy_mm_max_abs` | float | no | `late_max_surface_pulse_proxy_mm.max_abs` |
| `late_max_surface_pulse_proxy_mm_p99` | float | no | `late_max_surface_pulse_proxy_mm.p99` |
| `late_max_qofe_to_q_ratio_max_abs` | float | yes | `late_max_qofe_to_q_ratio.max_abs` |
| `late_max_qofe_to_q_ratio_p99` | float | yes | `late_max_qofe_to_q_ratio.p99` |
| `closure_residual_pct_of_rm_total` | float | no | `closure_residual_pct_of_rm_total` |
| `closure_residual_total_mm` | float | no | `closure_residual_total_mm` |
| `max_abs_ofe_closure_residual_mm_max_abs` | float | no | `max_abs_ofe_closure_residual_mm.max_abs` |
| `closure_residual_mm_max_abs` | float | no | `closure_residual_mm.max_abs` |
| `closure_residual_mm_p99` | float | no | `closure_residual_mm.p99` |

Topology axis (selectors rooted at `summary_json` and `summary_json.full_physical_closure.max_requires_scientific_review_day`):

| Column | Type | Nullable | Selector |
| --- | --- | --- | --- |
| `n_ofe_max` | int | no | `n_ofe_max` |
| `n_ofe_min` | int | no | `n_ofe_min` |
| `late_outlier_ofe_id` | int | yes | `full_physical_closure.max_requires_scientific_review_day.late_outlier_ofe_id` |
| `outlier_is_outlet_ofe` | bool | no | `derived` = `late_outlier_ofe_id == n_ofe_max` (False if `late_outlier_ofe_id` is null) |
| `outlier_is_first_ofe` | bool | no | `derived` = `late_outlier_ofe_id == 1` (False if null) |
| `outlier_is_interior_ofe` | bool | no | `derived` = `1 < late_outlier_ofe_id < n_ofe_max` (False if null) |

Chain-transfer axis (selectors rooted at `summary_json.mofe_chain`; the entire `mofe_chain` block can be absent — emit nulls if so):

| Column | Type | Nullable | Selector |
| --- | --- | --- | --- |
| `chain_subsurface_transfer_residual_m3_max_abs` | float | yes | `subsurface_transfer_residual_m3.max_abs` |
| `chain_subsurface_transfer_residual_m3_p99` | float | yes | `subsurface_transfer_residual_m3.p99` |
| `chain_surface_transfer_residual_m3_max_abs` | float | yes | `surface_transfer_residual_m3_geometry_sensitive.max_abs` |
| `chain_surface_transfer_residual_m3_p99` | float | yes | `surface_transfer_residual_m3_geometry_sensitive.p99` |
| `runoff_pass_vs_outlet_qofe_residual_m3_max_abs` | float | yes | `runoff_pass_vs_outlet_qofe_residual_m3.max_abs` |
| `runoff_pass_vs_outlet_qofe_residual_m3_p99` | float | yes | `runoff_pass_vs_outlet_qofe_residual_m3.p99` |
| `first_ofe_nonzero_subrin_days` | int | yes | `first_ofe_nonzero_subrin_days` |
| `first_ofe_nonzero_upstrmq_days` | int | yes | `first_ofe_nonzero_upstrmq_days` |
| `strict_chain_invariants_applicable` | str | yes | `strict_chain_invariants_applicability` |

Storage axis (mixed roots; see selector column):

| Column | Type | Nullable | Selector |
| --- | --- | --- | --- |
| `soilwater_to_porosity_fraction_max_abs` | float | yes | `summary_json.soilwater_to_porosity_fraction.max_abs` |
| `soilwater_to_porosity_fraction_p99` | float | yes | `summary_json.soilwater_to_porosity_fraction.p99` |
| `soilwater_minus_fc_mm_max_abs` | float | yes | `summary_json.soilwater_minus_fc_mm.max_abs` |
| `soilwater_minus_wp_mm_max_abs` | float | yes | `summary_json.soilwater_minus_wp_mm.max_abs` |
| `soilwater_gt_porositycap_days` | int | yes | `summary_json.whole_run_closure.soilwater_gt_porositycap_days` |
| `soilwater_lt_wpstore_days` | int | yes | `summary_json.whole_run_closure.soilwater_lt_wpstore_days` |
| `profile_order_fc_gt_porosity_days` | int | yes | `summary_json.whole_run_closure.profile_order_fc_gt_porosity_days` |
| `profile_order_wp_gt_fc_days` | int | yes | `summary_json.whole_run_closure.profile_order_wp_gt_fc_days` |
| `precip_total_mm` | float | yes | `summary_json.whole_run_closure.precip_total_mm` |
| `runoff_reported_total_mm` | float | yes | `summary_json.whole_run_closure.runoff_reported_total_mm` |
| `lateral_reported_total_mm` | float | yes | `summary_json.whole_run_closure.lateral_reported_total_mm` |
| `et_reported_total_mm` | float | yes | `summary_json.whole_run_closure.et_reported_total_mm` |
| `storage_change_mm` | float | yes | `summary_json.whole_run_closure.storage_change_mm` |

Temporal axis (selectors rooted at `summary_json.full_physical_closure`):

| Column | Type | Nullable | Selector |
| --- | --- | --- | --- |
| `requires_scientific_review_days` | int | no | `requires_scientific_review_days` |
| `total_simulation_days` | int | no | `summary_json.rows` |
| `flagged_day_fraction` | float | no | `derived` = `requires_scientific_review_days / total_simulation_days` (4 dp) |
| `max_anomaly_year` | int | no | `max_abs_day.year` |
| `max_anomaly_month` | int | no | `max_abs_day.month` |
| `max_anomaly_julian` | int | no | `max_abs_day.julian` |
| `worst_review_day_year` | int | yes | `max_requires_scientific_review_day.year` |
| `worst_review_day_month` | int | yes | `max_requires_scientific_review_day.month` |
| `worst_review_day_julian` | int | yes | `max_requires_scientific_review_day.julian` |
| `worst_review_day_reason` | str | yes | `max_requires_scientific_review_day.reason` |
| `worst_review_day_late_residual_mm` | float | yes | `max_requires_scientific_review_day.late_max_abs_ofe_closure_residual_mm` |
| `worst_review_day_late_pulse_mm` | float | yes | `max_requires_scientific_review_day.late_max_surface_pulse_proxy_mm` |
| `worst_review_day_qofe_to_q_ratio` | float | yes | `max_requires_scientific_review_day.late_max_qofe_to_q_ratio` |

Audit-thresholds (constants — emit as columns to make the table self-describing):

| Column | Type | Selector |
| --- | --- | --- |
| `threshold_late_ofe_residual_mm` | float | `summary_json.full_physical_closure.requires_scientific_review_thresholds.late_max_abs_ofe_closure_residual_mm` |
| `threshold_late_pulse_mm` | float | `…late_max_surface_pulse_proxy_mm` |
| `threshold_late_qofe_to_q_ratio` | float | `…late_max_qofe_to_q_ratio` |
| `threshold_late_ofe_window` | int | `…late_ofe_window` |

Acceptance for M1: row count of `triage_table_hillslopes.csv` equals the count of `requires_scientific_review == True` rows in `hillslope_audit_rollup.csv` (currently 132). Row count of `triage_table_hillslopes_all.csv` equals total rollup rows (currently 1166). Row count of `triage_table_runs.csv` equals the number of distinct (runid, config) pairs in the rollup (currently 4). Every required (non-nullable) column has a non-null value in every row. Tool exit code is 0 and prints a one-line summary `triage_table built: <runs> runs, <flagged> flagged hillslopes, <total> total hillslopes`.

### M2 — Deterministic taxonomy

Goal: assign one or more defect family labels to every flagged hillslope using rules over the M1 columns. Rules must be pure functions of the table.

Output: `taxonomy_assignments.csv` with columns `runid, config, wepp_id, family_primary, family_secondary, family_tertiary, family_rationale`. `family_primary` is required; secondary/tertiary are blank when not applicable. `family_rationale` is a short English sentence naming the columns and threshold values that triggered the primary label.

Initial family definitions (calibrate thresholds during M3 if data demand it; record any change in the Decision Log):

- **D0 — Config-correlated background.** Assigned only after M3 and evaluated per candidate primary family (`D1`-`D5`) within the dominant `(runid, config)` for that family. Use this fixed feature set:
  - `late_max_abs_ofe_closure_residual_mm_max_abs`
  - `late_max_surface_pulse_proxy_mm_max_abs`
  - `closure_residual_pct_of_rm_total`
  - `requires_scientific_review_days`
  - `chain_surface_transfer_residual_m3_p99` (null treated as `0.0`)
  - `chain_subsurface_transfer_residual_m3_p99` (null treated as `0.0`)
  Compute run-background moments from all flagged hillslopes in the same `(runid, config)` with the same null-to-zero preprocessing. Compute standardized mean deltas per feature as `abs(mean_family - mean_run) / max(std_run, 1e-9)`. Demote the family to D0 iff all of the following are true:
  - family concentration in one `(runid, config)` is `>= 0.95`
  - family size is `>= 5`
  - at least 5 of 6 feature deltas are `<= 0.35`
  - maximum feature delta is `<= 0.75`
  Threshold comparisons are inclusive (for example, `== 0.95` passes).
- **D1 — Outlet-OFE saturation spike.** `outlier_is_outlet_ofe == True` and `late_max_abs_ofe_closure_residual_mm_max_abs > 1000` and `late_max_qofe_to_q_ratio_max_abs >= n_ofe_max - 0.01` (ratio saturated). Mechanism hypothesis: outlet-element flow concentration coincident with ratio saturation.
- **D2 — Mid-OFE chain anomaly.** `outlier_is_interior_ofe == True` AND any of `chain_surface_transfer_residual_m3_p99 > 1e-3`, `chain_subsurface_transfer_residual_m3_p99 > 1e-3`, `runoff_pass_vs_outlet_qofe_residual_m3_max_abs > 1.0`. Mechanism hypothesis: between-OFE accounting drift in chain routing.
- **D3 — Storage-cap pressure.** `soilwater_to_porosity_fraction_p99 >= 0.99` AND `soilwater_gt_porositycap_days >= 1`. Mechanism hypothesis: storage saturation forces pulse-like discharges.
- **D4 — Single-day extreme.** `requires_scientific_review_days <= 3` AND `late_max_abs_ofe_closure_residual_mm_max_abs >= 500`. Mechanism hypothesis: aligns with the H2637 day-44 closure-spike incident.
- **D5 — Persistent moderate.** `requires_scientific_review_days >= 30` AND `late_max_abs_ofe_closure_residual_mm_max_abs` between 100 and 500. Mechanism hypothesis: parameter or structural rather than numerical.

Assignment policy: evaluate D1, D2, D3, D4, D5 in that order; the first matching rule sets `family_primary`. Subsequent matches populate `family_secondary` and `family_tertiary`. After M3, apply the D0 demotion rule above. If demoted, set `family_primary = D0` and preserve the previous primary label as `family_secondary` (shifting prior `family_secondary` to `family_tertiary` when needed).

Acceptance for M2: every flagged hillslope has a non-null `family_primary`. If any hillslope matches no rule, emit it with `family_primary = D_UNCLASSIFIED` and add a `Surprises & Discoveries` entry naming the hillslopes; do not silently drop them.

### M3 — Unsupervised cluster check

Goal: validate the deterministic labels against a feature-space clustering, surface disagreements, and decide whether to retune thresholds.

Procedure:

1. Standardize the magnitude, topology, chain, storage, and temporal feature columns from `triage_table_hillslopes.csv` (z-score, NaN → 0 after standardization).
2. Run HDBSCAN with `min_cluster_size=5`. If HDBSCAN is unavailable, fall back to k-medoids (`n_clusters=6`). If k-medoids is unavailable, fall back to KMeans (`n_clusters=6`). Record the choice in the Decision Log.
3. Emit `taxonomy_assignments.csv` with two added columns: `cluster_label` (-1 for noise) and `rule_cluster_agreement` (`agree` if cluster contains majority of family or vice versa, `disagree` otherwise, `noise` if cluster_label == -1).
4. Emit `taxonomy_disagreements.csv` listing the disagreement rows with all M1 columns plus `family_primary` and `cluster_label`.
5. Manual review of disagreements: for each disagreement, decide either to relabel the hillslope (record in Decision Log), retune a D-family threshold (record + re-run M2), or accept the disagreement (record rationale).

Acceptance for M3: `taxonomy_disagreements.csv` exists; each disagreement has a Decision Log entry; if any threshold was retuned, M2 outputs are regenerated and the change is documented.

### M4 — Representative seeds

Goal: for each populated D-family, pick three seeds — worst, median, and a passing comparator — and capture the staged-input manifest each one needs for downstream ablation.

Output: `representative_seeds.csv` with columns `family, role, runid, config, wepp_id, late_max_abs_ofe_closure_residual_mm_max_abs, requires_scientific_review_days, staged_runs_dir, run_file, shared_context_files, missing_shared_context, top_days_csv_path, summary_json_path`.

Selection rules per family:

- **Worst**: max of `late_max_abs_ofe_closure_residual_mm_max_abs` within the family.
- **Median**: hillslope whose `late_max_abs_ofe_closure_residual_mm_max_abs` is closest to the family median; ties broken by lower `requires_scientific_review_days`.
- **Contrast** (passing comparator): for each family, find the unflagged hillslope from the same `(runid, config)` whose feature vector (standardized) has the smallest L2 distance to the family centroid. Use `triage_table_hillslopes_all.csv` as the candidate pool for unflagged rows. Family centroid is the mean of the standardized feature vectors of the family's flagged hillslopes. If `(runid, config)` has no unflagged hillslopes, choose from the nearest sibling run sharing the same `config`.

Staged-input manifest population: for each seed, list paths under `staged_runs_dir` for the target file `p<wepp_id>.run` plus the run-shared context files required by `/workdir/wepp-forest/docs/ablation/protocol.md` step 1: `wepp_ui.txt`, `pmetpara.txt`, `snow.txt`, `gwcoeff.txt`, `chan.inp`, `chntyp.txt`, `tc.txt`. Set `missing_shared_context` to a semicolon-joined list of any files that do not exist on disk; empty string when complete. Use the same file-existence check the protocol prescribes (a simple `os.path.exists`).

Acceptance for M4: `representative_seeds.csv` has `3 * (number of populated families)` rows. Every `worst` and `median` row has `missing_shared_context == ""` (if any are missing, emit a Surprises & Discoveries entry — they cannot serve as ablation seeds without that context).

### M5 — Precedent crosswalk

Goal: align this triage with existing ablation packages to avoid duplicate campaigns.

Output: `precedent_crosswalk.md` — a short document (one section per existing relevant incident) noting:

1. The incident id, status, and signature.
2. Whether any flagged hillslope in the current dataset overlaps the incident's runid+wepp_id (zero overlap is a valid finding).
3. Whether any defect family (D1–D5) plausibly matches the incident's signature (e.g., D4 `Single-day extreme` ↔ `20260430_uncapped-spectacular_h2637_hillslope_closure-spike`).
4. Recommendation: spawn a new incident, extend the existing one, or hold.

Authoritative incident list to cross-walk: every directory under `/workdir/wepp-forest/docs/ablation/` whose name starts with a date and ends with `_hillslope_*` or `_mixed_*`. Read each `incident.md` first paragraph (summary + status) and `matrix.csv` for runid/wepp_id mentions.

Acceptance for M5: `precedent_crosswalk.md` exists with one entry per matching incident; every D-family is addressed (even if "no precedent found").

### M6 — Campaign matrix and closeout

Goal: emit the ablation-ready campaign matrix and the human-readable defect summary; close out the work-package.

Outputs:

1. `campaign_matrix.csv` — one row per D-family with columns `family, hypothesis, representative_worst, representative_median, representative_contrast, expected_observable, pass_fail_criterion, suggested_lane_type, candidate_incident_id, recommendation`. `representative_*` cells use the format `<runid>/H<wepp_id>`. `expected_observable` names specific summary JSON columns and threshold values that an ablation lane should move. `suggested_lane_type` is one of `O*`, `G*`, `U*` (per `/workdir/wepp-forest/docs/ablation/protocol.md` § 4); default to `G*` per protocol preference for guard-first lanes. `candidate_incident_id` follows the protocol format `YYYYMMDD_<best_runid>_<scope>_<short-signature>`. `recommendation` is one of `new_incident`, `extend_<existing_incident_id>`, `hold`.
2. `defect_families.md` — a short narrative report covering each family's prevalence (n hillslopes, % of flagged), severity (median and max of `late_max_abs_ofe_closure_residual_mm_max_abs`), signature stability (range of features within family), and recommended next step.

Acceptance for M6: both files exist; the matrix is consistent with `taxonomy_assignments.csv` and `representative_seeds.csv`; the work-package's `Outcomes & Retrospective` section is filled in; the `Progress` checklist marks every milestone done.

## Concrete Steps

All commands run from the repository root `/workdir/wepppy` unless noted. The work-package's artifacts directory must exist before any output is written.

Step 0. Verify preconditions:

    test -f /workdir/wepp-forest/docs/ablation/protocol.md
    test -f /workdir/wepp-forest/tools/ablation_protocol.py
    test -d /wc1/runs
    test -x /workdir/wepppy/.venv/bin/python
    /workdir/wepppy/.venv/bin/python -c "import pandas, numpy, hdbscan, sklearn_extra, sklearn"

Step 1. Create the output directory (idempotent):

    mkdir -p docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts

Step 2. Author `tools/build_mofe_triage_table.py`. Implementation notes:

- Use the standard library plus `pandas`, which is already a project dependency. Do not add new dependencies.
- Read the rollup CSV; for each flagged row open the JSON at `summary_json_path` and pull the columns named in M1.
- For run-context fields, attempt `json.loads(open(wepp_nodb_path).read())` first; on `OSError` or `json.JSONDecodeError` fall back to a regex parse of `defect_summary.md`.
- Write `triage_table_runs.csv`, `triage_table_hillslopes.csv`, and `triage_table_hillslopes_all.csv` to the artifacts directory.
- Print the summary line described in the M1 acceptance check.

Step 3. Run the tool:

    .venv/bin/python tools/build_mofe_triage_table.py

Expected transcript fragment:

    triage_table built: 4 runs, 132 flagged hillslopes, 1166 total hillslopes

Step 4. Validate the outputs:

    head -1 docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/triage_table_hillslopes.csv
    wc -l docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/triage_table_hillslopes.csv
    wc -l docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/triage_table_hillslopes_all.csv

Expect the flagged-table line count to be 133 (header + 132 data rows). Expect the all-hillslope table line count to be 1167 (header + 1166 data rows). Header order must match the schema above.

Step 5. Implement and run M2–M6 in sequence. Each milestone has an acceptance check; do not advance until the prior milestone's acceptance passes. Update `Progress` and `Decision Log` after each milestone.

## Validation and Acceptance

Final acceptance for the work-package is observable behavior, not file existence alone:

1. A reviewer opens `campaign_matrix.csv` and can identify, for any D-family, the worst-case representative seed, its `staged_runs_dir`, and the protocol-required shared-context file list — sufficient information to start `.venv/bin/python /workdir/wepp-forest/tools/ablation_protocol.py init --incident-id <candidate_incident_id>` without re-deriving anything from the validation artifacts.
2. `defect_families.md` answers the question "how many distinct mechanisms might be in play?" with a number and prose justification.
3. `precedent_crosswalk.md` confirms whether `20260430_uncapped-spectacular_h2637_hillslope_closure-spike` covers any of the new families.
4. Every flagged hillslope (132 in current data) has exactly one `family_primary` value and a non-empty rationale.
5. The work-package's `Outcomes & Retrospective` summarizes families realized vs. predicted, threshold retunes performed, and any open questions for the science maintainers.

A negative finding ("the flag set is dominated by a single config; we recommend a config-diff investigation rather than per-family ablations") is an acceptable outcome. Record it in `Outcomes & Retrospective` and emit a `campaign_matrix.csv` whose only row is the D0 recommendation.

## Idempotence and Recovery

`tools/build_mofe_triage_table.py` overwrites its output CSVs on each run. Re-running the tool after fixing a selector bug is safe and required after any schema change. Do not version individual triage table runs; the artifacts directory holds the canonical latest output.

If `/wc1` becomes unmounted mid-execution, the tool falls back to `defect_summary.md` parsing for run-context fields only; mark `wepp_nodb_source = defect_summary_md` in `triage_table_runs.csv` and continue M1-M3. M4-M6 still require staged-input file checks and ablation precedent crosswalk inputs; if those checks cannot run, stop and record a blocker.

If a milestone's outputs exist but are stale (rollup or summary JSONs were regenerated upstream), delete the artifacts directory and re-run from M1. Each milestone is reproducible from M1 outputs alone.

## Artifacts and Notes

Final artifact tree at completion:

    docs/work-packages/20260502_mofe_flagged_hillslope_triage/
    └── artifacts/
        ├── triage_table_runs.csv
        ├── triage_table_hillslopes.csv
        ├── triage_table_hillslopes_all.csv
        ├── taxonomy_assignments.csv
        ├── taxonomy_disagreements.csv
        ├── representative_seeds.csv
        ├── precedent_crosswalk.md
        ├── campaign_matrix.csv
        └── defect_families.md

The validation work-package's artifacts (`docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts/`) are inputs only and must not be modified.

## Interfaces and Dependencies

New code module to author at `tools/build_mofe_triage_table.py`. Python module path: `tools.build_mofe_triage_table` (run as a script, not imported by other modules). Required public CLI:

    .venv/bin/python tools/build_mofe_triage_table.py \
        --rollup-csv docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts/hillslope_audit_rollup.csv \
        --output-dir docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts

All flag defaults are set so that a no-arg invocation from the repository root produces the canonical outputs.

Subsequent milestones may add `tools/triage_taxonomy.py` (M2 + M3), `tools/triage_seeds.py` (M4), and `tools/triage_campaign_matrix.py` (M6). Codex chooses whether to consolidate these into a single `tools/triage_pipeline.py` or keep them split; either is acceptable as long as each milestone's acceptance check passes from the repository root with no manual setup.

Dependencies: existing project dependencies only (`pandas`, `numpy`, standard library, plus `hdbscan` if available — fall back to `sklearn.cluster.KMedoids` from `sklearn-extra` only if both are already present, otherwise use `sklearn.cluster.KMeans` as a documented degradation and record the choice in the Decision Log). Do not add new pinned dependencies for this work.

Read-only consumed interfaces:

- `hillslope_audit_rollup.csv` schema is treated as a contract; if a future audit run changes column names, this work-package must be re-validated before re-execution.
- Per-hillslope summary JSON schema is owned by `tools/hillslope_mofe_daily_closure_audit.py`. The selectors above name the exact dot-paths in use as of 2026-05-02; verify by reading one summary JSON before extending the schema.
- `/workdir/wepp-forest/docs/ablation/protocol.md` defines the staged-input manifest, lane-type vocabulary, and incident-id format consumed at M4–M6.

## Revision Notes

- 2026-05-02: ExecPlan rewritten by Claude Code from a thin work-package outline into a PLANS.md-conformant, autonomously executable specification. Pre-defined Phase 1 schemas for `triage_table_runs.csv` and `triage_table_hillslopes.csv` with explicit selectors. Replaced the F1–F4 family draft with a deterministic D0–D5 taxonomy whose rules are decidable from observable columns. Added M3 unsupervised cluster cross-check, M4 staged-input manifest contract, M5 precedent crosswalk, and M6 campaign matrix schema. Rationale: the consumer of this work-package is the ablation protocol, which expects single-factor seeds with full shared-context paths; the original outline did not give Codex enough scaffolding to deliver that without re-prompts.
