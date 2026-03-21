# RUSLE POLARIS K Completion with NRCS Benchmark Harness

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Complete RUSLE Milestone 4 (`K`) by implementing `polaris_nomograph` and `polaris_epic`, adding a benchmark harness (`gnatsgo_*` / `gssurgo_*`) for point sampling, and shipping comparison artifacts so reviewers can sanity-check both POLARIS estimators against the selected benchmark reference.

## Progress

- [x] (2026-03-21 08:20Z) Reviewed RUSLE spec K scope and pending milestones.
- [x] (2026-03-21 08:35Z) Authored package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- [x] (2026-03-21 09:00Z) Milestone 0 complete: locked modeled mapping, depth-weight, benchmark precedence, thresholds, and `cfvo` defer contracts.
- [x] (2026-03-21 09:25Z) Milestone 1 complete: implemented `polaris_nomograph` path.
- [x] (2026-03-21 09:30Z) Milestone 2 complete: implemented `polaris_epic` path.
- [x] (2026-03-21 09:40Z) Milestone 3 complete: implemented benchmark harness (`k_reference.py`).
- [x] (2026-03-21 09:45Z) Milestone 4 complete: implemented comparison utility + artifact path (`k_compare.py`, `k_benchmark_comparison_summary.md`).
- [x] (2026-03-21 09:50Z) Milestone 5 complete: correctness review artifact with no unresolved high/medium findings.
- [x] (2026-03-21 09:55Z) Milestone 6 complete: QA-review artifact with no unresolved high/medium findings.
- [x] (2026-03-21 10:10Z) Milestone 7 complete: full validation, docs sync, and package closure updates.

## Surprises & Discoveries

- Observation: `check_broad_exceptions.py --enforce-changed` only scanned tracked changed files, so untracked new files were not included automatically.
  Evidence: tool output reported one tracked changed Python file (`wepppy/nodb/mods/rusle/__init__.py`) during this run.

- Observation: existing RUSLE code had no K scaffolding, so introducing K modules was additive and low-risk to existing behavior.
  Evidence: pre-change `wepppy/nodb/mods/rusle/` contained only LS integration and specification/docs.

## Decision Log

- Decision: Keep package scope K-only (no C/P/controller implementation in this package).
  Rationale: User request and Milestone 4 boundary in spec.
  Date/Author: 2026-03-21 / Codex.

- Decision: `polaris_nomograph` uses modeled mappings:
  - structure class from texture proxy (`clay`, `sand`) -> classes `1-4`
  - permeability class from `ksat_cm_hr` proxy -> classes `1-6`
  Rationale: required inputs are not directly observed in POLARIS, but implementation needed explicit deterministic behavior.
  Date/Author: 2026-03-21 / Codex.

- Decision: Near-surface aggregation fixed to depth weights `0_5=5 cm`, `5_15=10 cm`.
  Rationale: lock identical support for nomograph and EPIC comparisons.
  Date/Author: 2026-03-21 / Codex.

- Decision: `polaris_epic` conversion fixed to `OC = OM / 1.724` with OM clamp `[0, 20]%`.
  Rationale: deterministic and documented conversion contract.
  Date/Author: 2026-03-21 / Codex.

- Decision: Benchmark precedence fixed to `gssurgo_kffact` -> `gnatsgo_kffact` -> `gssurgo_kwfact` -> `gnatsgo_kwfact`.
  Rationale: deterministic selection with `kffact` preference first and finer-grid source first.
  Date/Author: 2026-03-21 / Codex.

- Decision: Comparison defaults fixed to `abs_error_warn=0.10`, `rel_error_warn=0.35`; `cfvo` deferred.
  Rationale: enables clear default review behavior while keeping coarse-fragment adjustment out of this milestone.
  Date/Author: 2026-03-21 / Codex.

## Outcomes & Retrospective

Delivered outcomes:

- Added K modules:
  - `wepppy/nodb/mods/rusle/k_nomograph.py`
  - `wepppy/nodb/mods/rusle/k_epic.py`
  - `wepppy/nodb/mods/rusle/k_reference.py`
  - `wepppy/nodb/mods/rusle/k_compare.py`
  - `wepppy/nodb/mods/rusle/k_manifest.py`
  - `wepppy/nodb/mods/rusle/k_integration.py`
- Updated exports in `wepppy/nodb/mods/rusle/__init__.py`.
- Added tests:
  - `tests/nodb/mods/test_rusle_k_nomograph.py`
  - `tests/nodb/mods/test_rusle_k_epic.py`
  - `tests/nodb/mods/test_rusle_k_reference_harness.py`
  - `tests/nodb/mods/test_rusle_k_compare.py`
  - `tests/nodb/mods/test_rusle_k_integration.py`
- Added package artifacts:
  - `artifacts/milestone4_review.md`
  - `artifacts/milestone5_qa_review.md`
  - `artifacts/k_benchmark_comparison_summary.md`

Validation outcome:

- Targeted K suite passed (`16 passed`).
- Full WEPPpy suite passed (`2410 passed, 34 skipped`).
- Broad-exception changed-file enforcement passed.
- Code-quality observability completed (observe-only).

## Context and Orientation

Primary implementation paths:

- `wepppy/nodb/mods/rusle/` for K computation + harness + comparison.
- `tests/nodb/mods/test_rusle_k_*.py` for unit/integration regression coverage.
- `docs/work-packages/20260321_rusle_k_polaris_implementation/` for package lifecycle artifacts.

## Plan of Work

All milestones are complete for this package. Follow-up work is controller-level integration (Milestones 5-7 in `specification.md`).

## Concrete Steps

Executed commands from `/workdir/wepppy`:

1. Targeted K tests.

    wctl run-pytest tests/nodb/mods/test_rusle_k_nomograph.py tests/nodb/mods/test_rusle_k_epic.py tests/nodb/mods/test_rusle_k_reference_harness.py tests/nodb/mods/test_rusle_k_compare.py tests/nodb/mods/test_rusle_k_integration.py --maxfail=1

2. Quality checks.

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

3. Full sanity gate.

    wctl run-pytest tests --maxfail=1

## Validation and Acceptance

Acceptance achieved:

- Both POLARIS K estimators implemented and tested.
- Benchmark harness implemented with deterministic precedence and point sampling.
- Sanity comparison artifact produced.
- Review and QA-review artifacts completed with no unresolved high/medium findings.
- Full suite gate passed.

## Idempotence and Recovery

- K modules are additive and can be rerun against existing run directories.
- Comparison artifacts can be regenerated by rerunning `run_rusle_k_factors` with the same points and reference mode map.
- Manifest updates are deterministic and overwrite prior `k` section state.

## Artifacts and Notes

- `artifacts/milestone4_review.md`
- `artifacts/milestone5_qa_review.md`
- `artifacts/k_benchmark_comparison_summary.md`

## Interfaces and Dependencies

Implemented entrypoints:

- `wepppy.nodb.mods.rusle.k_integration.run_rusle_k_factors(...)`
- `wepppy.nodb.mods.rusle.k_nomograph.compute_polaris_nomograph_k(...)`
- `wepppy.nodb.mods.rusle.k_epic.compute_polaris_epic_k(...)`
- `wepppy.nodb.mods.rusle.k_reference.run_reference_harness(...)`
- `wepppy.nodb.mods.rusle.k_compare.compare_k_modes_to_reference(...)`

Dependencies remain inside existing stack (`numpy`, `rasterio`, existing WEPPpy modules).

---
Revision Note (2026-03-21, Codex): Initial active ExecPlan created for POLARIS K completion package.
Revision Note (2026-03-21, Codex): Completed Milestones 0-7, validated gates, and prepared plan for archive under `prompts/completed/`.
