# ExecPlan: Continue Omni Hotspot Reduction by Decomposing `omni_contrast_build_service.py`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

Status: Completed on 2026-02-21 (UTC). Archived under `docs/mini-work-packages/completed/`.

This plan is a follow-on to `docs/mini-work-packages/completed/20260221_nodb_omni_quality_refactor_execplan.md`; it keeps the same contract-preserving facade/collaborator approach and narrows scope to the two remaining high-CC builder methods now isolated in `wepppy/nodb/mods/omni/omni_contrast_build_service.py`.

## Purpose / Big Picture

After this work, Omni should keep the same route/RQ/facade behavior while reducing complexity concentration in `OmniContrastBuildService`. User-visible behavior should remain unchanged: same contrast sidecars, same build report schemas, same selection-mode semantics, and same rerun/pruning decisions. The gain is safer iteration in the extracted collaborator without reintroducing risk in `omni.py`.

Proof comes from unchanged contract tests and telemetry showing material complexity reduction for:

1. `OmniContrastBuildService.build_contrasts_stream_order`
2. `OmniContrastBuildService.build_contrasts_user_defined_areas`

## Progress

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for every entry.

- [x] (2026-02-21 01:54Z) Reviewed governing guidance and template references (`AGENTS.md`, `wepppy/nodb/AGENTS.md`, `docs/prompt_templates/codex_exec_plans.md`).
- [x] (2026-02-21 01:54Z) Archived previous completed Omni quality ExecPlan and repointed active ad hoc ExecPlan in `AGENTS.md`.
- [x] (2026-02-21 01:54Z) Captured current baseline context for `omni_contrast_build_service.py` hotspot concentration and authored this follow-on mini package.
- [x] (2026-02-21 01:58Z) Milestone 0 complete: refreshed baseline telemetry and reconfirmed deterministic Omni collaborator + cross-layer contract suites before decomposition edits.
- [x] (2026-02-21 02:01Z) Milestone 1 complete: decomposed `build_contrasts_stream_order` into phase helpers for path validation, stale/prune decisions, hillslope rebuild, grouping, and report emission.
- [x] (2026-02-21 02:02Z) Milestone 2 complete: decomposed `build_contrasts_user_defined_areas` into helper phases for input/CRS checks, lookup construction, feature selection, and report emission.
- [x] (2026-02-21 02:03Z) Milestone 3 complete: added deterministic regression tests for malformed-geometry skip boundary, CRS fallback logging, and missing TopazID contract.
- [x] (2026-02-21 02:09Z) Milestone 4 complete: captured final telemetry deltas and executed Omni-focused + full-suite validation closeout gates.

## Surprises & Discoveries

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-21 01:54Z) Observation: Omni facade hotspot goals were met, but complexity moved intact into the extracted collaborator.
  Evidence: `radon cc -s wepppy/nodb/mods/omni/omni_contrast_build_service.py` reports `build_contrasts_user_defined_areas - F (55)` and `build_contrasts_stream_order - F (50)`.

- (2026-02-21 01:54Z) Observation: compatibility seam for stale stream-order rebuild tests depends on module-level `_prune_stream_order` import path through `omni.py`.
  Evidence: existing test history in the predecessor plan required preserving monkeypatch behavior for `tests/nodb/mods/test_omni.py::test_build_contrasts_stream_order_stale_rebuild_decisions`.

- (2026-02-21 01:54Z) Observation: broad catch remains in a deliberate boundary where malformed user geometry should not abort all feature rows.
  Evidence: `wepppy/nodb/mods/omni/omni_contrast_build_service.py` uses `except Exception as exc` with explicit boundary comment and logger emission inside feature evaluation loop.

- (2026-02-21 01:58Z) Observation: baseline characterization gates are currently green before Milestone 1 extraction.
  Evidence: `wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py -k "build_contrasts_stream_order or build_contrasts_user_defined_areas" --maxfail=1` passed (`6 passed`); cross-layer suite command passed (`64 passed`).

- (2026-02-21 02:02Z) Observation: target entry methods dropped out of hotspot concern once orchestration was split into private phases.
  Evidence: post-refactor `radon cc -s wepppy/nodb/mods/omni/omni_contrast_build_service.py` reports `build_contrasts_stream_order - A (1)` and `build_contrasts_user_defined_areas - A (2)` instead of `F`.

- (2026-02-21 02:04Z) Observation: reducing method-level complexity increased collaborator file size because logic was redistributed into explicit helpers.
  Evidence: `radon raw` moved from `LOC/SLOC 553/484` baseline to `943/818` after decomposition.

- (2026-02-21 02:03Z) Observation: deterministic CRS fallback coverage required test stubs to support configurable CRS and project SRID inputs.
  Evidence: `_stub_user_defined_geodata(...)` in `tests/nodb/mods/test_omni_contrast_build_service.py` was expanded with `hillslope_crs`, `user_crs`, and `project_srid` parameters to exercise fallback branches.

## Decision Log

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- Decision: Keep `omni.py` facade delegators unchanged and perform all new decomposition internally to `OmniContrastBuildService`.
  Rationale: facade-level contracts were just stabilized; this follow-on should reduce collaborator complexity without widening contract surface.
  Date/Author: 2026-02-21 01:54Z / Codex

- Decision: Preserve module-level seam behavior for `_prune_stream_order` import and monkeypatch compatibility.
  Rationale: deterministic tests and regression debugging rely on existing seam location.
  Date/Author: 2026-02-21 01:54Z / Codex

- Decision: Prioritize helper extraction order as stream-order first, then user-defined areas.
  Rationale: stream-order method has stronger coupling to filesystem/raster rebuild control flow and benefits most from early extraction of independent phases.
  Date/Author: 2026-02-21 01:54Z / Codex

- Decision: Use phase-oriented private helpers and a shared report-path reset helper instead of introducing new collaborator classes.
  Rationale: this kept call signatures and seams stable while cutting entry-method CC with minimal contract risk.
  Date/Author: 2026-02-21 02:01Z / Codex

- Decision: Expand collaborator test fixtures to allow CRS/SRID parameterization rather than duplicating geo-stub scaffolding per test.
  Rationale: this enables deterministic branch coverage for fallback behavior with lower test maintenance overhead.
  Date/Author: 2026-02-21 02:03Z / Codex

- Decision: Accept increased SLOC in `omni_contrast_build_service.py` as a tradeoff for lower per-method complexity and clearer phase boundaries.
  Rationale: current observability is non-blocking and this package targets hotspot risk reduction over line-count minimization.
  Date/Author: 2026-02-21 02:04Z / Codex

## Outcomes & Retrospective

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-21 01:54Z) Outcome: planning/setup phase completed; no additional production refactor edits beyond prior extraction set were made in this authoring step.
- (2026-02-21 01:54Z) Retrospective: current risk has shifted to collaborator internals rather than facade orchestration, so next improvement should focus on internal helper structure and deterministic seam tests.
- (2026-02-21 01:58Z) Outcome: Milestone 0 baseline metrics captured for collaborator file.
  Evidence: `radon raw wepppy/nodb/mods/omni/omni_contrast_build_service.py` -> `LOC 553`, `SLOC 484`; `radon cc -s ...` -> `build_contrasts_user_defined_areas F (55)`, `build_contrasts_stream_order F (50)`.
- (2026-02-21 01:58Z) Outcome: Milestone 0 characterization suite summary.
  Evidence: collaborator/facade-targeted baseline command -> PASS (`6 passed`, `50 deselected`); cross-layer Omni contracts command -> PASS (`64 passed`).
- (2026-02-21 02:01Z) Outcome: Milestone 1 stream-order decomposition completed with seam-preserving orchestration.
  Evidence: `build_contrasts_stream_order` now delegates through helper phases (`_stream_order_*`) and milestone command `wctl run-pytest ... -k "stream_order"` passed (`7 passed`).
- (2026-02-21 02:02Z) Outcome: Milestone 2 user-defined-area decomposition completed with boundary behavior retained.
  Evidence: `build_contrasts_user_defined_areas` now delegates through helper phases (`_require_user_defined_inputs`, `_resolve_target_crs`, `_write_user_defined_report`, etc.) and milestone command `wctl run-pytest ... -k "user_defined_areas"` passed (`5 passed`).
- (2026-02-21 02:03Z) Outcome: Milestone 3 regression-gap tests added and passing.
  Evidence: new tests cover malformed geometry skip/log boundary, CRS fallback logs, and missing TopazID contract; milestone command `wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1` passed (`69 passed`).
- (2026-02-21 02:09Z) Outcome: Milestone 4 telemetry delta summary.
  Evidence: `radon cc -s` shows target methods reduced from `F (55/F 50)` to `A (2/A 1)`; file max method CC is now `C (12)`; observability report (`/tmp/omni-contrast-build-followup.md`) reports changed-file `python_function_len` at `77` and `python_cc` at `12` for `omni_contrast_build_service.py`.
- (2026-02-21 02:09Z) Outcome: Milestone 4 validation command summary.
  Evidence: Omni-focused cross-layer command passed (`123 passed`); full suite command `wctl run-pytest tests --maxfail=1` passed (`1919 passed`, `27 skipped`).
- (2026-02-21 02:09Z) Retrospective: hotspot risk for the two target entry methods is resolved, but collaborator-local maintainability still benefits from keeping helper boundaries coherent as future edits land.
  Evidence: top complexity after refactor is helper-level (`_build_hillslope_lookup C 12`) rather than entrypoint-level red-band methods.

## Context and Orientation

Primary files in scope:

1. `wepppy/nodb/mods/omni/omni_contrast_build_service.py` (new collaborator with remaining heavy methods).
2. `wepppy/nodb/mods/omni/omni.py` (facade delegators and module-level seams).
3. `tests/nodb/mods/test_omni_contrast_build_service.py` (collaborator-focused deterministic tests).
4. `tests/nodb/mods/test_omni.py` (facade delegator and stream-order stale rebuild seam tests).
5. `tests/nodb/mods/test_omni_facade_contracts.py`, `tests/rq/test_omni_rq.py`, `tests/microservices/test_rq_engine_omni_routes.py`, `tests/weppcloud/routes/test_omni_bp.py`, `tests/weppcloud/routes/test_omni_bp_routes.py` (cross-layer contract checks).

Current baseline context for collaborator complexity:

1. `build_contrasts_user_defined_areas`: `F (55)`.
2. `build_contrasts_stream_order`: `F (50)`.
3. `omni.py` facade methods for those paths are now delegators, so additional reductions should happen inside collaborator internals.

## Invariants

1. Preserve route/RQ/facade observable behavior unless explicit contract changes are approved.
2. Preserve NoDb lock/persistence boundaries (mutations still through `omni.locked()` and existing sidecar/report writers).
3. Preserve contrast sidecar payload schema and `build_report.ndjson` entry schema across selection modes.
4. Preserve compatibility seam behavior for `_prune_stream_order` monkeypatch usage in deterministic tests.
5. Avoid new broad catch handlers in production flow unless explicitly documented as a boundary.

## Milestone Plan

### Milestone 0: Baseline Refresh and Contract Characterization

Scope:
Re-run current metrics and characterization suites before further refactor edits.

Target files:

1. `wepppy/nodb/mods/omni/omni_contrast_build_service.py` (read-only this milestone).
2. `wepppy/nodb/mods/omni/omni.py` (read-only this milestone).
3. `tests/nodb/mods/test_omni_contrast_build_service.py`.
4. `tests/nodb/mods/test_omni.py`.
5. Cross-layer Omni contract suites listed in Context section.

Validation commands:

    radon raw wepppy/nodb/mods/omni/omni_contrast_build_service.py
    radon cc -s wepppy/nodb/mods/omni/omni_contrast_build_service.py
    wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py -k "build_contrasts_stream_order or build_contrasts_user_defined_areas" --maxfail=1
    wctl run-pytest tests/nodb/mods/test_omni_facade_contracts.py tests/rq/test_omni_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1

Go/No-Go:

1. `NO-GO` if characterization suite fails before refactor edits.
2. `NO-GO` if baseline CC metrics are not recorded in this plan.

### Milestone 1: Decompose Stream-Order Builder

Scope:
Split `build_contrasts_stream_order` into cohesive private helper methods with clear phase boundaries.

Target files:

1. `wepppy/nodb/mods/omni/omni_contrast_build_service.py`.
2. `tests/nodb/mods/test_omni_contrast_build_service.py`.
3. `tests/nodb/mods/test_omni.py` (only if seam/delegator assertions need expansion).

Required work:

1. Extract private helpers for WBT input resolution/validation, stale/prune decision, hillslope rebuild, group-map assembly, and contrast report emission.
2. Keep public entrypoint method name and behavior unchanged (`build_contrasts_stream_order`).
3. Preserve exact error message contracts where currently asserted.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py -k "stream_order" --maxfail=1

Go/No-Go:

1. `NO-GO` if stale rebuild decisions or `_prune_stream_order` seam compatibility regress.

### Milestone 2: Decompose User-Defined-Areas Builder

Scope:
Split `build_contrasts_user_defined_areas` into cohesive private helpers while keeping feature-level skip behavior and report schemas unchanged.

Target files:

1. `wepppy/nodb/mods/omni/omni_contrast_build_service.py`.
2. `tests/nodb/mods/test_omni_contrast_build_service.py`.
3. `tests/nodb/mods/test_omni.py` (if delegator coverage needs augmentation).

Required work:

1. Extract private helpers for geojson prerequisites/CRS alignment, hillslope lookup construction, feature-to-topaz selection, and report entry assembly.
2. Preserve deliberate boundary behavior for malformed feature geometry (skip feature row, continue processing, log context).
3. Preserve contrast label/signature ID behavior and sidecar/report emission semantics.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py -k "user_defined_areas" --maxfail=1

Go/No-Go:

1. `NO-GO` if any `build_report.ndjson` field set drifts or sidecar naming/ID stability changes.

### Milestone 3: Deterministic Regression Gap Closure

Scope:
Add targeted tests for newly extracted helper boundaries and edge contracts not already covered.

Target tests to add/expand:

1. Stream-order stale/prune decision branches (already-existing seam tests remain authoritative).
2. User-defined area malformed geometry boundary (logs + non-aborting skip behavior).
3. CRS fallback and missing-field contracts after helper decomposition.

Validation commands:

    wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py --maxfail=1

Go/No-Go:

1. `NO-GO` if helper extraction reduced coverage of existing branch contracts.

### Milestone 4: Telemetry Delta and Closeout

Scope:
Capture post-refactor complexity deltas and run broad Omni/full validation before archiving this plan.

Validation commands:

    radon raw wepppy/nodb/mods/omni/omni_contrast_build_service.py
    radon cc -s wepppy/nodb/mods/omni/omni_contrast_build_service.py
    python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/omni-contrast-build-followup.json --md-out /tmp/omni-contrast-build-followup.md
    wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_facade_contracts.py tests/rq/test_omni_rq.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1
    wctl run-pytest tests --maxfail=1

Acceptance targets:

1. Both target methods are reduced out of `F` band complexity.
2. No Omni contract or cross-layer regression appears in deterministic suites.
3. Full-suite validation passes or any blocker is documented with exact failing tests and cause.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Execute Milestone 0 commands and record baseline metrics and gate summaries in this plan.
2. Implement Milestones 1 and 2 sequentially, updating `Progress`, `Surprises & Discoveries`, and `Decision Log` after each pass.
3. Fill deterministic test gaps in Milestone 3 and run listed suites.
4. Run Milestone 4 telemetry + full validation and write closeout `Outcomes & Retrospective` entries.

## Validation and Acceptance

Global acceptance requires all of the following:

1. No route/RQ/facade contract drift in Omni behavior.
2. No lock/persistence boundary regressions.
3. No schema drift in contrast sidecar outputs and build reports.
4. Deterministic collaborator tests cover extracted helper behavior and edge contracts.
5. Complexity in `omni_contrast_build_service.py` trends materially better than current baseline and is recorded in this plan.

## Risk and Rollback

1. Risk: helper extraction accidentally changes contrast naming or IDs.
   Mitigation: deterministic sidecar/report assertions and facade contract tests.
   Rollback: revert latest helper split and re-run milestone-local tests.

2. Risk: stream-order stale/prune semantics drift after phase extraction.
   Mitigation: preserve seam imports and stale-rebuild branch tests.
   Rollback: restore prior stream-order method body and keep new tests as characterization.

3. Risk: malformed-geometry boundary behavior changes from skip-and-continue to hard fail.
   Mitigation: explicit malformed-geometry regression tests and logger assertions.
   Rollback: restore boundary behavior and isolate helper-level error handling.

## Idempotence and Recovery

This plan is incremental and idempotent by milestone. If a milestone fails:

1. Revert only the failing milestone diff.
2. Re-run that milestone’s validation commands.
3. Update `Progress`, `Surprises & Discoveries`, and `Decision Log` with failure evidence and revised approach.

Do not proceed to the next milestone until the current milestone is green.

## Out of Scope

1. New Omni selection modes or report schema expansions.
2. Route/RQ contract redesign or queue dependency rewiring.
3. Large refactors outside Omni contrast builder internals and directly related tests.

## Artifacts and Notes

Record concise evidence as work proceeds:

1. Before/after CC and LOC snapshots for `omni_contrast_build_service.py`.
2. Milestone command pass/fail summaries.
3. Any contract-preservation decision affecting seams or exception boundaries.

Revision Note (2026-02-21 01:54Z, Codex): Created this follow-on mini ExecPlan to continue the completed Omni hotspot program by targeting the two remaining high-CC methods isolated in `OmniContrastBuildService`.
Revision Note (2026-02-21 01:58Z, Codex): Updated living sections with Milestone 0 baseline telemetry and characterization evidence so the plan reflects current executable state before new refactor edits.
Revision Note (2026-02-21 02:09Z, Codex): Updated the plan through Milestone 4 completion with helper-decomposition outcomes, expanded regression coverage, telemetry deltas, and full validation results.
Revision Note (2026-02-21 02:10Z, Codex): Marked plan complete and prepared archival move to `docs/mini-work-packages/completed/`.
