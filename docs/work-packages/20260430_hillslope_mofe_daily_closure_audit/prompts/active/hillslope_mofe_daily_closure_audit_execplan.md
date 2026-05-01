# hillslope_mofe_daily_closure_audit Tool + MOFE Contract

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, analysts can run a repeatable MOFE-specific daily closure audit and interpret results against a producer-authoritative contract derived from `/workdir/wepp-forest` source. This reduces ambiguity when diagnosing OFE-chain anomalies (for example, single-day OFE outliers that appear to propagate downslope).

## Progress

- [x] (2026-04-30 15:20 UTC) ExecPlan authored and linked to package tracker.
- [x] (2026-04-30 16:02 UTC) Milestone 1 drafted: authored `docs/dev-notes/hillslope_mofe_water_balance_contract.md` with WEPP-source rule citations and interchange mapping.
- [x] (2026-04-30 16:10 UTC) Milestone 1 gate completed: reviewer subagent findings dispositioned in `artifacts/20260430_contract_review_disposition.md`.
- [x] (2026-04-30) Milestone 2 implemented and reworked to full-physics closure reporting (`Residual_full_exported` + implied unresolved term diagnostics).
- [x] (2026-04-30) Milestone 3 tests updated for full-physics closure behavior, selector parity, and artifact generation.
- [ ] Milestone 4: Run `drilled-plight` exemplar evaluations and capture artifacts. (refresh complete; strict MOFE validation blocked because run has only single-OFE hillslopes)
- [ ] Milestone 5: Independent implementation review + disposition.

## Surprises & Discoveries

- Observation: Exact adjacent-OFE surface transfer closure cannot be fully reconstructed from interchange alone because required geometry terms (`efflen`, `slplen`, OFE widths) are not exported.
  Evidence: Surface runon uses `runoff(i-1)*efflen(i-1)/slplen(i)` while `QOFE` uses `runoff(i)*efflen(i)/slplen(i)` in producer output logic (`/workdir/wepp-forest/src/watbal.for:362-363,1093-1100`).
- Observation: Canonical WEPP daily balance includes interception/unexported terms not fully present in interchange-only hillslope audit inputs.
  Evidence: Interception is subtracted in runtime `fin` construction (`/workdir/wepp-forest/src/watbal.for:331-346`) and `etplcp` is computed but not emitted in `H.wat` writes (`/workdir/wepp-forest/src/watbal.for:942-951,1077-1105`).

## Decision Log

- Decision: Contract definition is a first-class milestone that must close before implementation closes.
  Rationale: User requirement and risk reduction for MOFE semantics.
  Date/Author: 2026-04-30 / Codex.

- Decision: Milestone 1 includes required subagent reviewer gate.
  Rationale: User requirement for delegated contract quality gate.
  Date/Author: 2026-04-30 / Codex.

- Decision: Treat adjacent-OFE surface transfer residuals as geometry-sensitive diagnostics and keep subsurface transfer residuals as strict closure checks.
  Rationale: WEPP source equations require geometry factors for exact surface equivalence, while `SubRIn` volume closure is directly reconstructable from exported terms.
  Date/Author: 2026-04-30 / Codex.

- Decision: Close Milestone 1 only after applying reviewer findings and recording a disposition artifact.
  Rationale: Enforces explicit contract quality gate before tool validation proceeds.
  Date/Author: 2026-04-30 / Codex.

- Decision: Rework from legacy/storage-only closure interpretation to full-physics exported-term closure plus explicit implied-unresolved-term reporting.
  Rationale: Hydrology review correctly identified that `Total-Soil Water + frozwt + Snow-Water` alone is not equivalent to canonical WEPP Eq. 5.1.1 closure; audit outputs must expose residual interpretation limits directly.
  Date/Author: 2026-04-30 / Codex.

## Outcomes & Retrospective

Implementation complete for contract/tool/tests with full-physics scope update; remaining package closure work is Milestone 4 evidence refresh and Milestone 5 independent implementation review disposition.

## Context and Orientation

Relevant paths and baseline tools:
- WEPP source of truth: `/workdir/wepp-forest`
- Existing closure tools:
  - `tools/hillslope_daily_closure_audit.py`
  - `tools/totalwatsed3_daily_closure_audit.py`
- Interchange aggregation logic:
  - `wepppy/wepp/interchange/totalwatsed3.py`
  - `wepppy/wepp/interchange/hill_wat_interchange.py`
  - `wepppy/wepp/interchange/hill_pass_interchange.py`
- Candidate evaluation run: `/wc1/runs/dr/drilled-plight`

## Plan of Work

Milestone 1 defines the MOFE contract from WEPP source. Identify and document exact source variables and daily accounting transitions (including lateral/subsurface transfer semantics across OFEs, storage terms, and precipitation/rain+melt basis behavior). Produce a contract document with equations, field mapping to interchange columns, and explicit invariants/known non-closure modes.

Milestone 1 Gate dispatches a `reviewer` subagent to review only the contract milestone output. Milestone 1 is not complete until findings are dispositioned in an artifact.

Milestone 2 implements `tools/hillslope_mofe_daily_closure_audit.py` using the contract terms. Ensure selector contract parity with existing tool conventions (`--wepp-id` XOR `--topaz-id`) and MOFE-specific outputs for OFE transfer/closure checks.

Milestone 3 adds synthetic regression tests for MOFE transfer chains, selector behavior, and output generation.

Milestone 4 runs exemplar audits against `drilled-plight`, captures summary/top-day outputs, and writes consolidated evaluation notes.

Milestone 5 runs independent review and disposition for implementation quality.

## Concrete Steps

Working directory: `/workdir/wepppy`

1. Milestone 1 contract drafting.

   rg -n "subrin|latqcc|sbrunf|watbal|QOFE|runoff|ofe" /workdir/wepp-forest -S
   # Draft contract doc path (to be finalized in milestone):
   # docs/dev-notes/hillslope_mofe_water_balance_contract.md

2. Milestone 1 review gate.

   # Dispatch reviewer subagent on contract doc only.
   # Save findings + disposition in package artifacts.

3. Tool implementation.

   $EDITOR tools/hillslope_mofe_daily_closure_audit.py

4. Tests.

   $EDITOR tests/tools/test_hillslope_mofe_daily_closure_audit.py
   wctl run-pytest tests/tools/test_hillslope_mofe_daily_closure_audit.py --maxfail=1

5. Regression guards.

   wctl run-pytest tests/tools/test_hillslope_daily_closure_audit.py --maxfail=1
   wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py --maxfail=1

6. Real-run evaluation.

   # Run the new MOFE audit tool against selected drilled-plight MOFE hillslopes.
   # Save summary/top-day outputs under this package artifacts.

## Validation and Acceptance

Acceptance requires:
- Contract doc exists with explicit equations and WEPP-source references.
- Contract milestone review gate artifact exists and findings are dispositioned.
- MOFE audit tool runs with selector contract parity and generates expected outputs.
- New tests pass and baseline closure-audit suites remain green.
- `drilled-plight` artifact evidence captured for representative MOFE hillslopes.

## Idempotence and Recovery

- Contract and evaluation artifacts are additive and can be regenerated.
- Tool runs are read-only against run artifacts; reruns replace output files only.
- If run artifacts are unavailable, keep milestone status blocked and capture evidence in tracker.

## Artifacts and Notes

Expected artifact paths:
- `docs/work-packages/20260430_hillslope_mofe_daily_closure_audit/artifacts/<date>_contract_review_disposition.md`
- `docs/work-packages/20260430_hillslope_mofe_daily_closure_audit/artifacts/<run>_<hill>/...`
- `docs/work-packages/20260430_hillslope_mofe_daily_closure_audit/artifacts/evaluation_summary.md`

## Interfaces and Dependencies

Required interfaces at completion:
- CLI `tools/hillslope_mofe_daily_closure_audit.py`:
  - positional `interchange_dir`
  - selector `--wepp-id` or `--topaz-id` (mutually exclusive)
  - optional `--output-dir`, `--top-n`
- Contract document with normative MOFE closure equations linked to source terms.

## Revision Notes

- 2026-04-30 / Codex: Initial ExecPlan authored with contract milestone and mandatory subagent review gate.
- 2026-04-30 / Codex: Updated Milestone 1 progress after contract authoring and recorded geometry-sensitivity discovery for surface transfer diagnostics.
- 2026-04-30 / Codex: Completed Milestone 1 review gate and added disposition artifact with all findings closed.
- 2026-04-30 / Codex: Reworked package scope to full-physics closure diagnostics, updated contract/tool/tests accordingly, and marked Milestones 2-3 complete.
