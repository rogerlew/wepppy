# ExecPlan: Continue Omni Hotspot Reduction by Decomposing `omni_contrast_build_service.py`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

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
- [ ] Milestone 0 complete: refresh baseline telemetry and reconfirm current deterministic Omni contract suite status before further decomposition.
- [ ] Milestone 1 complete: decompose `build_contrasts_stream_order` into cohesive private helpers while preserving all observable behavior and seams.
- [ ] Milestone 2 complete: decompose `build_contrasts_user_defined_areas` into cohesive private helpers while preserving all observable behavior and schemas.
- [ ] Milestone 3 complete: fill deterministic collaborator tests for extracted helper boundaries and retained error contracts.
- [ ] Milestone 4 complete: capture final telemetry deltas and run full validation closeout.

## Surprises & Discoveries

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-21 01:54Z) Observation: Omni facade hotspot goals were met, but complexity moved intact into the extracted collaborator.
  Evidence: `radon cc -s wepppy/nodb/mods/omni/omni_contrast_build_service.py` reports `build_contrasts_user_defined_areas - F (55)` and `build_contrasts_stream_order - F (50)`.

- (2026-02-21 01:54Z) Observation: compatibility seam for stale stream-order rebuild tests depends on module-level `_prune_stream_order` import path through `omni.py`.
  Evidence: existing test history in the predecessor plan required preserving monkeypatch behavior for `tests/nodb/mods/test_omni.py::test_build_contrasts_stream_order_stale_rebuild_decisions`.

- (2026-02-21 01:54Z) Observation: broad catch remains in a deliberate boundary where malformed user geometry should not abort all feature rows.
  Evidence: `wepppy/nodb/mods/omni/omni_contrast_build_service.py` uses `except Exception as exc` with explicit boundary comment and logger emission inside feature evaluation loop.

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

## Outcomes & Retrospective

Use UTC timestamps in `YYYY-MM-DD HH:MMZ` format for new entries.

- (2026-02-21 01:54Z) Outcome: planning/setup phase completed; no additional production refactor edits beyond prior extraction set were made in this authoring step.
- (2026-02-21 01:54Z) Retrospective: current risk has shifted to collaborator internals rather than facade orchestration, so next improvement should focus on internal helper structure and deterministic seam tests.

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
