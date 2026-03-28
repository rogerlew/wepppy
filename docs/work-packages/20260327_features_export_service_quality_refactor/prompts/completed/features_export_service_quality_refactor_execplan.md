> Outcome (2026-03-28): Completed all four phases with no unresolved medium/high findings, full validation pass, and verified run-path counts/timings.

# Features Export Service Quality Refactor and Collaborator Extraction (Phases 1-4)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, features export keeps WP-8 key-first behavior and output parity but no longer relies on hidden fallback contracts or broad exception swallow paths in the service layer. The service facade remains stable for rq-engine and WEPPcloud callers, while high-complexity responsibilities move into focused collaborators under `wepppy/nodb/mods/features_export/`. Success is visible when required test suites pass, run-path evidence still shows exactly two baseline layers (`66` and `27` features), and code-quality/QA review gates report no unresolved medium/high findings.

## Progress

- [x] (2026-03-28 03:52Z) Authored work-package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- [x] (2026-03-28 03:52Z) Added package linkage to `PROJECT_TRACKER.md` backlog.
- [x] (2026-03-28 03:53Z) Ran doc-lint for package docs and `PROJECT_TRACKER.md` updates.
- [x] (2026-03-28 04:15Z) Phase 1 complete: removed hidden identity-key fallback and hardened required-source failure semantics in `service.py`.
- [x] (2026-03-28 04:20Z) Phase 2 complete: extracted column-selection and cache-rehydration collaborators with service facade wrappers.
- [x] (2026-03-28 04:24Z) Phase 3 complete: enforced strict required-source behavior on carrier discovery path and aligned spec/tests.
- [x] (2026-03-28 04:33Z) Phase 4 complete: full validation matrix passed, run-path evidence refreshed, and review artifacts closed.

## Surprises & Discoveries

- Observation: `wepppy/nodb/mods/features_export/service.py` is currently a red-band file-size hotspot (`python_file_sloc=1784`, threshold red `>=1200`).
  Evidence: `python3 tools/code_quality_observability.py --base-ref origin/master` output (`code-quality-summary.md`).

- Observation: QA review identified one broad exception swallow boundary and one hidden join-key fallback path that are quality-contract risks.
  Evidence: review findings at `service.py:1870` and `service.py:1359`.

- Observation: Carrier-source discovery still allowed warning-only degradation for required missing/unsupported sources before this package pass.
  Evidence: QA review finding replicated in `discover_layer_sources`; resolved by strict `MaterializationContractError` raises and service-level `materialization_error` translation.

- Observation: `execute_features_export()` cache-hit result can legitimately omit `layer_outputs`; manifest and artifact inspection remain sufficient for acceptance evidence.
  Evidence: cold/warm run results for jobs `manual-wp8-cold-20260328043304050246` and `manual-wp8-warm-20260328043306591594`.

## Decision Log

- Decision: Execute in four phases, safety-first before structural extraction.
  Rationale: Contract-risk changes should land first to avoid masking regressions during module decomposition.
  Date/Author: 2026-03-27 / Codex.

- Decision: Preserve external service and route contracts during refactor unless explicit human approval is provided.
  Rationale: This is a quality refactor package; behavior drift is risk unless intentionally approved and documented.
  Date/Author: 2026-03-27 / Codex.

- Decision: Required-source policy is strict failure for both legacy source merges and carrier discovery.
  Rationale: Mixed strict/warning behavior across hot paths violates spec intent and causes non-deterministic contract outcomes.
  Date/Author: 2026-03-28 / Codex.

## Outcomes & Retrospective

- Package complete (phases 1-4 closed).
- Contract and quality outcomes:
  - removed broad catch from touched `service.py` paths (changed-file broad-catch net delta `-1`),
  - removed arbitrary join-key fallback and now fail explicitly with `materialization_error` when identity candidates do not resolve,
  - required-source failures are strict on both legacy and carrier paths.
- Structural outcomes:
  - extracted `column_selection.py` and `cache_rehydration.py` collaborators,
  - retained stable service facade contracts (`execute_features_export`, `resolve_download_artifact_path`).
- Validation outcomes:
  - required pytest and JS test commands passed,
  - doc-lint passed for spec and package docs,
  - review artifacts report no unresolved medium/high findings.
- Run-path acceptance outcomes:
  - target run: `clogging-starch/disturbed9002-wbt-mofe`,
  - cold job `manual-wp8-cold-20260328043304050246`: `2.541s`, `cache_hit=false`,
  - warm job `manual-wp8-warm-20260328043306591594`: `0.996s`, `cache_hit=true`,
  - artifact `export/features/artifacts/cbaa1b76752641b980ee1a3f119e3456/features_export.gpkg`,
  - manifests:
    - `export/features/jobs/manual-wp8-cold-20260328043304050246/manifest.json`
    - `export/features/jobs/manual-wp8-warm-20260328043306591594/manifest.json`,
  - feature tables and counts:
    - `clogging_starch_sbs_map_subcatchments`: `66`
    - `clogging_starch_chan_map_channels`: `27`.

## Context and Orientation

Primary module under refactor is `wepppy/nodb/mods/features_export/service.py`. It currently mixes these responsibilities in one file:

- submission preparation and cache coordination,
- key-first and legacy payload materialization orchestration,
- source loading and source-to-geometry joins,
- selected-column/unit resolution,
- cache-entry artifact reconstruction and download path resolution,
- utility normalization and serialization helpers.

This package keeps one explicit architecture rule: no feature flags, no temporary parallel runtime path. Refactor must preserve a single production hot path.

Related files and contracts:

- `wepppy/nodb/mods/features_export/specification.md` - source-of-truth behavior contract.
- `wepppy/nodb/mods/features_export/*.py` collaborator modules introduced in WP-8.
- `tests/nodb/mods/test_features_export_service.py` - regression tests for service behavior.
- `tests/microservices/test_rq_engine_features_export_routes.py` - rq-engine payload/route contract.
- `docs/mini-work-packages/20260327_features_export_key_first_materialization_execplan.md` - WP-8 baseline behavior and evidence.
- `docs/mini-work-packages/20260327_features_export_reconciliation_execplan.md` - reconciliation context and constraints.

## Plan of Work

### Phase 1: Safety and contract hardening

This phase removes known quality violations before larger structural edits. In `service.py`, replace broad `except Exception` blocks with narrow expected exception handling and explicit contract-compliant behavior. Eliminate hidden join-key fallback behavior that currently chooses an arbitrary non-geometry column, and replace it with explicit failure (`materialization_error`) unless contract-defined keys resolve. Add targeted regression tests first or in the same commit so behavior changes are intentional and provable.

### Phase 2: Collaborator extraction

This phase reduces complexity in `service.py` while preserving facade behavior. Extract cohesive units into collaborator modules under `wepppy/nodb/mods/features_export/`:

- cache-entry parsing and artifact metadata assembly,
- source loading/parquet unit introspection glue,
- selected-column and unit-resolution logic.

Keep service facade signatures unchanged and delegate to collaborators. Do not move persistence or cache boundary ownership out of service facade methods.

### Phase 3: Required-source policy finalization

This phase resolves ambiguous behavior where required sources can currently degrade to warnings. Decide one explicit policy and encode it consistently:

- strict failure on missing/invalid required sources, or
- explicit degraded-output contract with deterministic warnings and documentation.

Update specification wording and tests to match chosen behavior. If policy changes output behavior, record exact rationale and compatibility impact in Decision Log and tracker.

### Phase 4: End-to-end validation and closure

Run full required validation suite, gather run-path acceptance evidence, and complete review artifacts. Compare cold/warm runtime evidence to WP-8 baseline and record any material deltas with rationale. Finalize package tracker, ExecPlan progress sections, and review artifacts with unresolved finding status.

## Concrete Steps

Run commands from repository root unless a command specifies another path.

1. Capture baseline and safety checks:

    cd /workdir/wepppy
    wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

2. Implement Phase 1 edits and targeted tests:

    cd /workdir/wepppy
    wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "cache or join or required" --maxfail=1

3. Implement Phase 2 collaborator extraction and regression checks:

    cd /workdir/wepppy
    wctl run-pytest tests/nodb/mods/test_features_export_planner.py \
      tests/nodb/mods/test_features_export_service.py \
      tests/nodb/mods/test_features_export_exporters.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1

4. Implement Phase 3 policy alignment and documentation updates:

    cd /workdir/wepppy
    wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md
    wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1

5. Execute Phase 4 final gates and evidence collection:

    cd /workdir/wepppy
    wctl run-pytest tests/nodb/mods/test_features_export_planner.py \
      tests/nodb/mods/test_features_export_service.py \
      tests/nodb/mods/test_features_export_exporters.py \
      tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1
    wctl run-npm test -- features_export
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/package.md
    wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/tracker.md
    wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/prompts/active/features_export_service_quality_refactor_execplan.md

6. Refresh run-path acceptance evidence:

    - Trigger default baseline export for run `clogging-starch/disturbed9002-wbt-mofe`.
    - Record job IDs, artifact relpath, manifest relpath, layer IDs, feature counts, cold runtime, warm runtime.

## Validation and Acceptance

Package is complete only when all items below are true.

- Safety/contract:
  - no broad exception swallow behavior in touched service code,
  - no hidden fallback path that silently selects arbitrary join keys.
- Structure:
  - responsibilities moved from `service.py` into collaborators with stable facade API.
- Correctness:
  - required tests pass,
  - default baseline export still yields exactly two layers with feature counts `66` and `27`.
- Performance evidence:
  - cold and warm runtime recorded for baseline run-path,
  - any material regression is explained and approved in Decision Log.
- Review closure:
  - code review artifact and QA review artifact contain no unresolved medium/high findings.

## Idempotence and Recovery

- All test and lint commands are safe to rerun.
- Collaborator extraction steps should be commit-sized and reversible; keep each phase green before moving to next.
- If a phase introduces behavior drift, revert that phase commit and re-run baseline tests before retry.
- Run-path evidence must be re-collected after final phase changes; do not reuse stale timings from earlier commits.

## Artifacts and Notes

Required package artifacts:

- `docs/work-packages/20260327_features_export_service_quality_refactor/artifacts/20260327_code_review.md`
- `docs/work-packages/20260327_features_export_service_quality_refactor/artifacts/20260327_qa_review.md`

Recommended evidence snippets to record in tracker/retrospective:

- `check_broad_exceptions` output excerpt for changed files.
- `code_quality_observability` before/after hotspot metrics for `service.py`.
- run-path artifact/manifest IDs and cold/warm runtime measurements.

## Interfaces and Dependencies

End-state interface requirements:

- `execute_features_export(...)` request/response contract remains stable for rq-engine consumers.
- `resolve_download_artifact_path(...)` and manifest loading behavior remain backward-compatible.
- Features export cache-hit metadata remains parseable and explicit when malformed.
- Any specification contract change is reflected in `wepppy/nodb/mods/features_export/specification.md` in the same phase.

Dependency boundaries:

- Keep refactor inside `wepppy/nodb/mods/features_export/*`, related tests, and necessary route adapters only.
- Do not introduce external dependencies for this refactor package.

---
