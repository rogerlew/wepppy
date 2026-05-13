# ExecPlan: Resolve `ebe_pw0.peak_runoff` All-Zero Regression via Ablation

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan, `ebe_pw0.peak_runoff` will correctly preserve nonzero peak runoff values in runs where channel/event peak products are nonzero, and the corrected binary will be vendored in `wepppy` with reproducible evidence. Users will be able to compare `chan.out` and `ebe_pw0` on the same day/element keys and see consistent peak behavior instead of all-zero event peaks.

## Progress

- [x] (2026-05-13 22:15 UTC) Package scaffold created and registered for execution.
- [x] (2026-05-13 22:28 UTC) Captured reproducible pre-fix evidence bundle and interchange manifest baseline.
- [x] (2026-05-13 22:28 UTC) Executed stage-by-stage ablation and identified first-loss boundary at producer raw `ebe_pw0.txt`.
- [x] (2026-05-13 23:10 UTC) Implemented and validated producer-side fix candidate in `wepp-forest/src/wshrun.f90`; off-run replay confirms peak restoration.
- [ ] Add focused regression tests for the all-zero peak failure mode.
- [ ] Re-run semantic comparison on SOFE/MOFE Am6/IMP cohorts and publish pass/fail evidence.
- [x] (2026-05-13 23:10 UTC) Vendored candidate binaries and published provenance (`artifacts/binary_provenance.md`).

## Surprises & Discoveries

- Observation: For `/wc1/runs/of/off-the-rack-neoprene` (`wepp_260513`), `ebe_pw0.parquet.peak_runoff` is zero for every row while `chan.out.parquet.Peak_Discharge (m^3/s)` is nonzero on the same keys.
  Evidence: `/tmp/off260513_vs_ca_dcc52a6_semantic_compare.json` and direct DuckDB checks.
- Observation: In off-run ablation replay, `wepp/output/ebe_pw0.txt` is already all-zero in the peak column while raw `chan.out` remains nonzero.
  Evidence: `artifacts/ablation_stage_summary.json` (`off_ablation.ebe_raw_txt` vs `off_ablation.chan_raw_txt`).
- Observation: Parser/writer path is non-causal for this defect; pipeline, Python parser, and Rust parser outputs are identical (all-zero).
  Evidence: `artifacts/off_ablation_parser_path_comparison.json`.
- Observation: `pass_pw0.txt` is absent in the off run by pass-family design (`hbp`) and is non-authoritative for this defect signature.
  Evidence: `artifacts/ablation_stage_summary.json` (`off_current.pass_status`, `off_ablation.pass_status`).
- Observation: Post-fix off-run replay restores nonzero EBE peak runoff with chan-vs-ebe deltas back to expected small tolerance envelope.
  Evidence: `artifacts/post_fix_semantic_compare.json`.
- Observation: Candidate HBP binary passes provenance + HBP smoke but default `wepppy` host-smoke fixture set still uses legacy `H*.pass.dat`.
  Evidence: `artifacts/binary_provenance.md`.

## Decision Log

- Decision: Treat this as a contract-surface regression candidate until stage-level ablation proves exact fault location.
  Rationale: Cross-table inconsistency is clear, but producer vs parser vs interchange writer fault is unresolved.
  Date/Author: 2026-05-13 / Codex.
- Decision: Lock immediate repair boundary to producer-side generation path for `ebe_pw0.txt` peak values.
  Rationale: Stage ablation proves first-loss occurs before parser/interchange serialization; parser path is exact-preserving.
  Date/Author: 2026-05-13 / Codex.
- Decision: Vendor fix candidate now with explicit fixture-compatibility disclosure rather than blocking on legacy host-smoke fixture migration.
  Rationale: Defect is resolved on target HBP run family and provenance gates pass; fixture migration can proceed as follow-up without hiding current evidence.
  Date/Author: 2026-05-13 / Codex.

## Outcomes & Retrospective

- Ablation campaign completed and first-loss boundary isolated.
- Defect classification updated from "candidate" to "confirmed producer-side regression" for `wepp_260513` off-run path.
- Producer fix candidate built and vendored with documented evidence.
- Remaining work narrowed to regression test coverage + three-cohort recertification + fixture compatibility disposition.

## Context and Orientation

The defect is observed in run artifacts under `/wc1/runs/*/wepp/output/interchange/`:

- Candidate run: `/wc1/runs/of/off-the-rack-neoprene` (`wepp_260513`, `_pass_family=hbp`).
- Baseline run: `/wc1/runs/ca/carnivorous-adobo` (`wepp_dcc52a6`, `_pass_family=legacy_ascii`).

Primary files used for diagnosis:

- `chanwb.parquet` (daily channel balance and outflow)
- `chan.out.parquet` (daily peak discharge)
- `ebe_pw0.parquet` (daily event runoff/peak/runoff volume)
- `totalwatsed3.parquet` (aggregate hydrology diagnostics)
- `loss_pw0.all_years.chn.parquet` (annualized channel outputs)

The semantic rubric is in `/workdir/wepp-forest/docs/pass-serialization-channel-routing-comparison-report.md`.

## Plan of Work

Milestone 1 establishes reproducible pre-fix evidence and a stable ablation matrix. For each run, capture manifest hashes and stage outputs so comparison is deterministic.

Milestone 2 executes ablation stages where each stage tests whether peak values are already zero before the next transformation:

- Stage A: source producer output (raw WEPP text/binary source where peak is emitted)
- Stage B: parser read object in memory
- Stage C: interchange serialization (`ebe_pw0.parquet` write)
- Stage D: downstream consumer readback and cross-table join checks

The first stage where values collapse to zero is the repair boundary.

Milestone 3 applies the smallest contract-preserving fix at that boundary. The fix must not add silent fallback wrappers. If data is missing/invalid, failure should be explicit and contract-compliant.

Milestone 4 adds regression coverage for the exact failure mode and reruns semantic checks on the three primary cohorts.

Milestone 5 vendors the corrected binary in `wepppy` with provenance (build id, SHA256, source commit) and rollback instructions.

## Concrete Steps

Work from `/workdir/wepppy` unless noted.

1. Build pre-fix manifest evidence for the two key runs and store under this package `artifacts/`.
2. Execute DuckDB cross-table checks to confirm:
   - `chan.out` peak nonzero distribution.
   - `ebe_pw0.peak_runoff` distribution.
   - key-aligned delta statistics (`year`, `julian`, `month`, `day_of_month`, `Elmt_ID/element_id`).
3. Trace stage A->D to identify first-loss boundary.
4. Implement minimal fix in responsible layer (repo may be `wepp-forest` or `wepppy`, depending on boundary).
5. Add regression tests in touched repo for all-zero suppression failure mode.
6. Rebuild corrected binary and rerun target cohorts.
7. Publish post-fix semantic comparison JSON and summary note.
8. Vendor corrected binary in `wepppy` and update provenance docs.

## Validation and Acceptance

Acceptance requires all of the following:

- `ebe_pw0.peak_runoff` is no longer all-zero for runs with nonzero channel/event peaks.
- Cross-table comparison (`chan.out` vs `ebe_pw0`) on aligned keys shows expected numeric agreement/tolerance.
- No unexpected Lane 1 semantic drift is introduced in SOFE/MOFE Am6/IMP cohort comparisons.
- Regression tests fail before fix and pass after fix.
- Vendored binary hash and source provenance are documented.

## Idempotence and Recovery

Ablation steps are evidence-only and can be rerun without mutating run directories. Fix rollout uses standard git commits so rollback is `git revert <fix_commit>` plus re-vendoring the previous binary artifact. Keep pre-fix and post-fix manifests side-by-side in package artifacts.

## Artifacts and Notes

Artifact outputs under `docs/work-packages/20260513_ebe_pw0_peak_runoff_regression_ablation/artifacts/`:

- `pre_fix_semantic_compare.json`
- `pre_fix_interchange_manifest.csv`
- `ablation_stage_matrix.csv`
- `ablation_stage_summary.json`
- `off_ablation_parser_path_comparison.json`
- `summary_verdict.md`
- `post_fix_semantic_compare.json`
- `binary_provenance.md`

## Interfaces and Dependencies

No external dependency additions are planned. This package depends on existing run artifacts under `/wc1/runs/`, DuckDB for analysis, and build/test tooling in `wepp-forest` and `wepppy`.
