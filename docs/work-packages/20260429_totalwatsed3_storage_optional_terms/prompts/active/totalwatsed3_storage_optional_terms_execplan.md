# totalwatsed3 Optional Storage and Partition Terms (Cross-Repo Contract)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, watershed water-balance interpretation will have explicit, unambiguous storage/partition terms instead of relying on mixed semantics across legacy columns. Operators and analysts will be able to audit closure with clearly defined full-profile storage terms (and optional runoff partition terms) while legacy runs continue to process without breakage.

Observable outcomes:
- enriched runs emit additive optional storage/capacity fields,
- WEPPpy parses both legacy and enriched layouts,
- `totalwatsed3` exposes optional columns with null-safe fallback,
- daily closure audit reports whole-run closure statistics with the enriched terms.

## Progress

- [x] (2026-04-29 22:10 UTC) ExecPlan authored and linked from work-package tracker.
- [x] (2026-04-29 22:10 UTC) Cross-repo source anchors identified (`watbal.for`, `watbal_hourly.for`, `outfil.for`, interchange parsers, `totalwatsed3`, audit tool).
- [x] (2026-04-30 03:19 UTC) Finalized optional-term contract (names, units, formulas, null semantics) from stakeholder direction.
- [x] (2026-04-30 03:43 UTC) Implemented parser-first compatibility changes in WEPPpy WAT interchange reader/tests; legacy layouts emit null optional terms and unknown extra columns fail fast.
- [x] (2026-04-30 03:43 UTC) Implemented WEPP-forest additive `H.wat` output-term writes in daily and hourly water-balance writers; `make wepp wepp_hill` and host smoke checks pass.
- [x] (2026-04-30 03:43 UTC) Extended `totalwatsed3` schema/aggregation/docs/tests for all five optional WAT storage/capacity terms plus existing `TSMF`/`QRain`/`QSnow` optionals.
- [x] (2026-04-30 04:00 UTC) Addressed independent review findings: `H.element` aggregation now joins real date-keyed element rows to WAT for `sim_day_index`, `watbalprint.for` now matches the widened `ivers=3` WAT header, and the audit command example uses the tool's positional parquet argument.
- [x] (2026-04-30 04:09 UTC) Regenerated `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet` on wepp1 without container takedown and captured whole-run closure plus `H2637`/`H2809` reconciliation artifacts.

## Surprises & Discoveries

- Observation: `TSW` in `H.soil` is tied to top-layer saturation diagnostic output formatting, while `H.wat` `Total-Soil Water` is computed from profile `watcon` and represents unfrozen profile water depth.
  Evidence: `/workdir/wepp-forest/src/watbal.for` soil write block and WAT write block around daily output formatting.

- Observation: `TSMF` (full-profile moisture fraction) is already computed in WEPP-forest and available in WEPPpy interchange when present, but not all producer layouts guarantee it.
  Evidence: `/workdir/wepp-forest/src/watbal.for`, `/workdir/wepppy/wepppy/wepp/interchange/hill_soil_interchange.py`.

- Observation: `hill_wat_interchange` currently enforces exact header equality; additive producer columns can break parsing unless alias/layout logic is loosened intentionally.
  Evidence: `/workdir/wepppy/wepppy/wepp/interchange/hill_wat_interchange.py::_extract_header`.

- Observation: The requested rollout-gate run is not available in the current workspace, so Milestone 5 cannot be completed here.
  Evidence: `docs/work-packages/20260429_totalwatsed3_storage_optional_terms/artifacts/production_run_missing_probe.md` records missing checks for `/geodata/wc1/runs/un/uncapped-spectacular` and `/wc1/runs/un/uncapped-spectacular`.

- Observation: The rollout-gate run is present on wepp1, not in the local workspace. Milestone 5 was completed there through a no-restart `weppcloud` container hotfix and one-shot regeneration.
  Evidence: `docs/work-packages/20260429_totalwatsed3_storage_optional_terms/artifacts/wepp1_uncapped_spectacular_20260430/production_rollout_gate.md`.

- Observation: Real `H.element.parquet` rows are calendar-date keyed and do not carry `sim_day_index`; `totalwatsed3` must obtain `sim_day_index` from the joined WAT row.
  Evidence: `hill_element_interchange.py` schema and regression fixture in `tests/wepp/interchange/test_totalwatsed3.py`.

- Observation: The watershed `ivers=3` WAT path uses `watbalprint.for`, separate from the daily/hourly hillslope writers, so it also must append the optional WAT terms to match the widened header.
  Evidence: independent review finding and successful rebuild after updating `/workdir/wepp-forest/src/watbalprint.for`.

## Decision Log

- Decision: Contract changes will be additive-only and backward-compatible.
  Rationale: Existing runs and report consumers depend on legacy schemas; removing/renaming columns would create avoidable breakage.
  Date/Author: 2026-04-29 / Codex.

- Decision: Implement parser compatibility in WEPPpy before producer enrichment rollout.
  Rationale: Consumer-first rollout reduces operational risk and allows mixed-version data ingestion during deployment windows.
  Date/Author: 2026-04-29 / Codex.

- Decision: Treat `TSMF`, `QRain`, `QSnow`, and new storage/capacity terms as optional columns with null-on-absence semantics.
  Rationale: Mixed producer versions are expected; optional columns preserve stable ingestion contracts.
  Date/Author: 2026-04-29 / Codex.

- Decision: Adopt WEPP-aligned optional `H.wat` storage/capacity columns in `mm`:
  `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`.
  Rationale: Stakeholder preference plus direct mapping to WEPP variable semantics and formulas:
  `watcon + frozwt`, `solthk(nsl)`, `sum(por*dg)`, `sum(thetfc*dg)`, `sum(thetdr*dg)`.
  Date/Author: 2026-04-30 / Codex.

- Decision: Treat WEPP producer values as authoritative for optional terms; WEPPpy should parse/pass through when available.
  Rationale: Avoids divergent derived behavior and ensures closure diagnostics track model-native state.
  Date/Author: 2026-04-30 / Codex.

- Decision: Require `uncapped-spectacular` production closure re-audit as rollout gate.
  Rationale: Stakeholder concern is potential water-balance incorrectness in this run; synthetic validation alone is insufficient.
  Date/Author: 2026-04-30 / Codex.

- Decision: `totalwatsed3` must expose all five optional storage/capacity terms directly when available.
  Rationale: Stakeholder requested full visibility of producer-authoritative terms rather than a subset.
  Date/Author: 2026-04-30 / Codex.

- Decision: Rollout-gate validation will combine whole-run closure stats with hillslope deep dives on `H2637` and `H2809`.
  Rationale: Stakeholders require reasoned physical reconciliation, not only a single aggregate threshold.
  Date/Author: 2026-04-30 / Codex.

- Decision: Legacy executables (for example `wepp_dcc52a6`) remain supported; missing optional `H.wat` terms must parse as non-fatal omissions with null outputs.
  Rationale: Mixed producer versions are expected in active deployments.
  Date/Author: 2026-04-30 / Codex.

## Outcomes & Retrospective

Implemented outcomes as of 2026-04-30 03:43 UTC:
- explicit optional storage contract documented and implemented in WEPP-forest output and WEPPpy ingestion/aggregation,
- backward-compatible parser behavior validated for legacy `H.wat` layouts with null optional terms,
- unknown/unmapped extra WAT columns validated as fail-fast errors,
- `totalwatsed3` exposes `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, and `ProfileWPStore` directly,
- closure audit reports whole-run legacy-storage stats and enriched-storage stats when `SoilWaterTotal` is present.

Review follow-up completed as of 2026-04-30 04:00 UTC:
- `totalwatsed3` optional element aggregation is compatible with production-shaped `H.element.parquet` schemas that omit `sim_day_index`,
- WEPP-forest watershed `ivers=3` WAT output rows now append the same five optional storage/capacity fields advertised by the header,
- required tests, WEPP-forest build, and host smoke checks were rerun successfully.

Production rollout gate completed on wepp1 as of 2026-04-30 04:09 UTC:
- regenerated `totalwatsed3.parquet` hash: `20f39d30280c9ccaf20754778e57c9e5595711ea334c8ffab82def2d89f68ca2`,
- previous artifact backup hash: `d649088f1948c3f98de4f4c5868824aba920b8552bacc07da4cfaf40f37c8e73`,
- whole-run reconstructed closure with legacy storage: `-13,813.464759 mm` (`-16.855844%` of rain + melt),
- runoff consistency after regeneration: max absolute `0.0 mm`,
- `H2637` closure with storage: `-119,246.654467 mm` (`-114.007900%` of rain + melt),
- `H2809` closure with storage: `-297,116.718881 mm` (`-278.295506%` of rain + melt).

Residual finding:
- The production `H.wat.parquet` was generated by a legacy producer and lacks the five optional WAT storage/capacity terms. The regenerated `totalwatsed3.parquet` exposes those columns, but they are null for all `12,419` rows. `TSMF` is populated for all rows; `QRain` and `QSnow` are populated for `12,409` rows.

## Context and Orientation

This package spans two repositories:

- Producer: `/workdir/wepp-forest`
  - `/workdir/wepp-forest/src/watbal.for`
  - `/workdir/wepp-forest/src/watbal_hourly.for`
  - `/workdir/wepp-forest/src/watbalprint.for`
  - `/workdir/wepp-forest/src/outfil.for`

- Consumer/aggregation: `/workdir/wepppy`
  - `/workdir/wepppy/wepppy/wepp/interchange/hill_wat_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/hill_soil_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/hill_element_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/totalwatsed3.py`
  - `/workdir/wepppy/tools/totalwatsed3_daily_closure_audit.py`
  - `/workdir/wepppy/docs/dev-notes/totalwatsed-interchange.spec.md`

Primary artifact for validation:
- `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet`

## Plan of Work

Milestone 1 defines the optional-term contract precisely. Finalize column names, units, formulas, and legacy-null behavior for storage/capacity and runoff-partition terms in `docs/dev-notes/totalwatsed-interchange.spec.md` and package decision logs.

Milestone 2 hardens WEPPpy parsers to tolerate additive producer layouts. Update `hill_wat_interchange` and any related parsing assumptions so legacy and enriched files both parse. Add parser-focused regression tests with fixture variants.

Milestone 3 implements WEPP-forest additive output terms. Extend output writers to emit the finalized optional terms without altering legacy column positions/meaning for existing fields. Update/extend fixture expectations.

Milestone 4 updates `totalwatsed3` and audit tooling. Ensure optional columns are ingested when present, null otherwise, and surfaced in schema/docs. Extend closure audit reporting for whole-run and event-level summaries using enriched storage terms.

Milestone 5 validates on `uncapped-spectacular`, captures artifacts, and closes docs. Regenerate `totalwatsed3.parquet` without container takedown, run audit, store artifacts, and finalize package closure notes. Validation must include independent hillslope reconciliation for `H2637` and `H2809`.

## Concrete Steps

Working directories:
- WEPPpy: `/workdir/wepppy`
- WEPP-forest: `/workdir/wepp-forest`

1. Contract finalization and doc updates.

    cd /workdir/wepppy
    rg -n "SoilWaterTotal|ProfileDepth|ProfilePorosityCap|ProfileFCStore|ProfileWPStore|TSMF|QRain|QSnow" docs/dev-notes/totalwatsed-interchange.spec.md

2. Parser compatibility implementation in WEPPpy.

    cd /workdir/wepppy
    rg -n "Unexpected WAT column layout|HEADER_ALIASES|WAT_COLUMN_NAMES" wepppy/wepp/interchange/hill_wat_interchange.py
    wctl run-pytest tests/wepp/interchange/test_hill_wat_interchange.py --maxfail=1

3. WEPP-forest output extension implementation.

    cd /workdir/wepp-forest
    rg -n "TSMF|watcon|frozwt|write \(35|write \(39|QRain|QSnow" src/watbal.for src/watbal_hourly.for src/watbalprint.for src/outfil.for

4. `totalwatsed3` optional-term aggregation updates and regressions.

    cd /workdir/wepppy
    wctl run-pytest tests/wepp/interchange/test_totalwatsed3.py --maxfail=1

5. Closure audit and artifact capture.

    cd /workdir/wepppy
    wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py --maxfail=1
    python tools/totalwatsed3_daily_closure_audit.py /geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet --output-dir docs/work-packages/20260429_totalwatsed3_storage_optional_terms/artifacts

## Validation and Acceptance

Acceptance requires all of the following:

- Legacy hillslope outputs parse without regression.
- Enriched hillslope outputs with optional columns parse and preserve known units/semantics.
- `totalwatsed3` exposes all five optional storage/capacity fields for enriched inputs and nulls for legacy inputs.
- Legacy-executable output layouts that omit optional terms (for example `wepp_dcc52a6`) parse successfully without schema errors.
- Closure audit emits whole-run closure statistics and consistent event-level diagnostics.
- `uncapped-spectacular` evidence includes independent hillslope diagnostics for `H2637` and `H2809`.
- Docs/specs/tests are updated and aligned with implemented behavior.

## Idempotence and Recovery

- Schema evolution is additive; re-running interchange generation should be safe for both legacy and enriched runs.
- If producer rollout lags, consumer null-fallback semantics remain valid.
- If any parser regression appears, rollback can be isolated to parser/layout logic while preserving existing schema outputs.
- Do not remove legacy columns in this package; removal requires a separate deprecation package with migration evidence.

## Artifacts and Notes

Capture and retain:
- closure audit summary JSON and top-days CSV under:
  - `docs/work-packages/20260429_totalwatsed3_storage_optional_terms/artifacts/`
- pre/post regeneration checksums and command transcript excerpts in tracker notes.

Current artifact:
- `docs/work-packages/20260429_totalwatsed3_storage_optional_terms/artifacts/production_run_missing_probe.md` records the missing production run blocker.
- `docs/work-packages/20260429_totalwatsed3_storage_optional_terms/artifacts/wepp1_uncapped_spectacular_20260430/` records the completed wepp1 production rollout gate.

## Interfaces and Dependencies

Required interface behavior at completion:

- Hillslope interchange readers remain compatible with legacy outputs.
- New storage/capacity optional columns are documented and optional.
- `run_totalwatsed3(...)` remains callable with existing signature and returns backward-compatible baseline columns plus additive optional columns.
- `tools/totalwatsed3_daily_closure_audit.py` continues to operate on legacy files and includes enriched-term statistics when columns exist.

Dependencies:
- WEPP-forest producer patch availability and deployment.
- Existing WEPPpy test/tooling via `wctl`.

## Revision Notes

- 2026-04-29 / Codex: Initial ExecPlan authored for optional-term contract implementation across WEPP-forest + WEPPpy.
- 2026-04-30 / Codex: Updated with finalized optional term contract and production rollout gate from stakeholder direction.
- 2026-04-30 / Codex: Updated after implementation of parser, producer, aggregation, audit, and tests; recorded production run mount blocker for Milestone 5.
- 2026-04-30 / Codex: Updated after review fixes for production-shaped element joins, `watbalprint.for` `ivers=3` row width, and the closure-audit command example.
- 2026-04-30 / Codex: Updated after completing the production rollout gate on wepp1 and copying audit/reconciliation artifacts into the package.
