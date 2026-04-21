# ExecPlan: Omni `contrast_id_definitions.psv` Contract

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

Status: Completed
Last Updated: 2026-04-22 00:24Z (UTC)
Primary Areas: `wepppy/nodb/mods/omni/omni_state_contrast_mixin.py`, `wepppy/nodb/mods/omni/omni_build_router.py`, `wepppy/nodb/mods/omni/omni.pyi`, `tests/nodb/mods/test_omni.py`, `tests/nodb/mods/test_omni_state_contrast_mixin.py`, `tests/nodb/mods/test_omni_build_router_service.py`, `wepppy/nodb/mods/omni/README.md`

## Purpose / Big Picture

Omni contrast runs currently persist per-contrast sidecars (`omni/contrasts/contrast_<id>.tsv`) and a mode-specific build report (`_pups/omni/contrasts/build_report.ndjson`), but there is no single, mode-agnostic artifact that maps contrast run IDs to the selected Topaz hillslopes. After this change, every successful contrast build will also write `omni/contrast_id_definitions.psv` with one row per runnable contrast in the format `<contrast_id>|<topaz_id_1>,<topaz_id_2>,...`. This gives downstream data handlers one stable file path and one stable parser regardless of selection mode (`cumulative`, `user_defined_areas`, `user_defined_hillslope_groups`, `stream_order`).

## Progress

- [x] (2026-04-21 18:25Z) Reviewed Omni contrast build/orchestration code paths, sidecar contract, and status/report shaping for all selection modes.
- [x] (2026-04-21 18:34Z) Verified current per-mode contrast ID behavior and identified cumulative-mode ID nuance (`contrast_id` is sequential run ID; selected hillslope ID is `topaz_id`).
- [x] (2026-04-21 18:43Z) Authored this mini work-package ExecPlan with file-level implementation and validation gates.
- [x] (2026-04-21 19:05Z) Implemented `omni/contrast_id_definitions.psv` writer/loader helpers and lifecycle cleanup hooks in `OmniStateContrastMixin`.
- [x] (2026-04-21 19:16Z) Wired `OmniBuildRouter.build_contrasts()` to write PSV immediately after contrast build and before contrast GeoJSON generation.
- [x] (2026-04-21 20:14Z) Added regression coverage for cumulative, user-defined hillslope groups, and stream-order PSV mappings, plus reset/clear cleanup behavior and router call sequencing.
- [x] (2026-04-21 19:43Z) Updated Omni README artifact and flow documentation with explicit cumulative-mode sequential `contrast_id` clarification.
- [x] (2026-04-21 20:15Z) Re-ran targeted validation: `wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_state_contrast_mixin.py tests/nodb/mods/test_omni_build_router_service.py --maxfail=1` (90 passed).
- [x] (2026-04-21 20:05Z) Re-ran broader Omni confidence suite: `wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni_run_orchestration_service.py tests/nodb/mods/test_omni_station_catalog_service.py --maxfail=1` (23 passed).
- [x] (2026-04-21 20:21Z) Ran full gate `wctl run-pytest tests --maxfail=1`; first failure remains unrelated to Omni and is in OpenAPI metadata validation (`tests/microservices/test_rq_engine_openapi_contract.py::test_frozen_agent_route_metadata_fields_are_non_empty`).
- [x] (2026-04-22 00:24Z) Disposition pass after code/QA/security review: merged duplicate user-defined label selections per contrast ID, promoted PSV loader to strict runtime-contract parsing, kept empty-value rows (`<contrast_id>|`) valid, and strengthened router sequencing coverage.

## Surprises & Discoveries

- Observation: cumulative mode does not currently use selected `topaz_id` as filesystem `contrast_id`.
  Evidence: `build_contrasts_cumulative_default()` writes `contrast_id` as sequential (`1..N`) in `build_report.ndjson`, while `contrast_name` embeds the selected `topaz_id` (`wepppy/nodb/mods/omni/omni_contrast_build_service.py`).

- Observation: sidecar TSV rows contain all watershed Topaz IDs for a contrast, not only selected treatment IDs.
  Evidence: `build_contrast_mapping()` writes every `top2wepp` key, choosing control or contrast path per key (`wepppy/nodb/mods/omni/omni_mode_build_services.py`).

- Observation: stream-order report rows do not include explicit `topaz_ids`, so selected hillslopes must be derived from sidecar path targeting.
  Evidence: stream-order report entries record `subcatchments_group` and `n_hillslopes` but no `topaz_ids` list (`wepppy/nodb/mods/omni/omni_contrast_build_service.py`).

- Observation: user-defined and stream-order modes can produce sparse `contrast_names` with `None` holes (skipped groups/features).
  Evidence: contrast slots are padded and skipped rows do not emit sidecars (`_append_contrast_name_slot`, `_write_*_report` paths in `wepppy/nodb/mods/omni/omni_contrast_build_service.py`).

## Decision Log

- Decision: keep existing sidecar TSV contract unchanged and add `contrast_id_definitions.psv` as an additive artifact.
  Rationale: existing runtime and tests rely on `contrast_<id>.tsv`; additive output avoids compatibility risk while providing a new normalized interface.
  Date/Author: 2026-04-21 / Codex

- Decision: define `contrast_id_definitions.psv` rows as `contrast_id|comma_separated_topaz_ids` with no header.
  Rationale: matches requested parser contract, keeps file minimal, and avoids key-name drift.
  Date/Author: 2026-04-21 / Codex

- Decision: include only runnable contrasts (those with non-empty `contrast_name` and sidecar payload) in the PSV.
  Rationale: skipped contrasts have no sidecar and no executable run artifact; downstream consumers should not have to special-case placeholder rows.
  Date/Author: 2026-04-21 / Codex

- Decision: derive selected Topaz IDs from sidecar mapping by path targeting, reusing existing contrast-path semantics rather than mode-specific ad hoc logic.
  Rationale: one derivation path works for all modes and preserves current behavior semantics.
  Date/Author: 2026-04-21 / Codex

- Decision: always create/refresh `omni/contrast_id_definitions.psv` after `build_contrasts` completes, and remove stale copies on contrast reset/clear.
  Rationale: guarantees a single canonical file lifecycle and prevents stale downstream reads.
  Date/Author: 2026-04-21 / Codex

- Decision: duplicate user-defined area/group label signatures are merged into a single contrast definition per control/contrast pair.
  Rationale: operator decision in review disposition; keeps one stable `contrast_id` for repeated labels and unions selected Topaz IDs.
  Date/Author: 2026-04-22 / Codex

- Decision: `_load_contrast_id_definitions_psv()` is a runtime contract parser, not test-only permissive parsing.
  Rationale: downstream handlers need deterministic failure semantics on malformed/corrupted PSV files.
  Date/Author: 2026-04-22 / Codex

- Decision: empty selected-id rows are valid contract output (`<contrast_id>|`).
  Rationale: operator decision for explicit representation of contrasts that currently resolve to no selected Topaz IDs.
  Date/Author: 2026-04-22 / Codex

## Outcomes & Retrospective

- (2026-04-21 19:43Z) Outcome: implemented additive PSV artifact contract at `omni/contrast_id_definitions.psv`, preserving existing sidecar/report contracts and deriving selected Topaz IDs across supported modes.
- (2026-04-21 19:43Z) Outcome: cumulative-mode behavior is now explicitly documented and covered: `contrast_id` is sequential run/sidecar ID; selected Topaz IDs are PSV value entries.
- (2026-04-21 20:15Z) Outcome: focused Omni tests passed (`90 passed`), confirming writer lifecycle, router invocation, and contract shape across cumulative, user-defined, and stream-order mappings.
- (2026-04-21 20:05Z) Outcome: additional Omni confidence suite passed (`23 passed`).
- (2026-04-21 20:21Z) Outcome: full test gate reported an unrelated failure in RQ-engine OpenAPI metadata token validation; Omni-targeted changes remain green.
- (2026-04-22 00:24Z) Outcome: review findings dispositioned in code with contract updates for duplicate-label merge semantics, strict PSV loader validation, and explicit empty-row allowance.
- (2026-04-21 20:03Z) Retrospective: the additive artifact approach minimized risk and downstream ambiguity while avoiding any queue or external API contract changes.

## Context and Orientation

Omni contrast build flow is routed through `OmniBuildRouter.build_contrasts()` (`wepppy/nodb/mods/omni/omni_build_router.py`), which sets state, executes `_build_contrasts()`, and then builds contrast overlay GeoJSON. Contrast build implementations live in `wepppy/nodb/mods/omni/omni_contrast_build_service.py` and produce:

1. `omni/contrasts/contrast_<id>.tsv` sidecars via `OmniStateContrastMixin._write_contrast_sidecar(...)`.
2. `_pups/omni/contrasts/build_report.ndjson` entries for mode-specific reporting and dry-run status.
3. in-memory `contrast_names` list where index `i` maps to run/sidecar `contrast_id = i + 1`.

Current downstream status and run orchestration code loads sidecars from `OmniStateContrastMixin._load_contrast_sidecar(...)` and infers selected contrast Topaz IDs using path-based comparison helper `_contrast_topaz_ids_from_mapping(...)` (`wepppy/nodb/mods/omni/omni.py`, `wepppy/nodb/mods/omni/omni_station_catalog_service.py`).

This package adds a normalized intermediary artifact:

- Path: `omni/contrast_id_definitions.psv`
- Encoding: ASCII, `\n` line endings
- Row format: `<contrast_id>|<topaz_id_1>,<topaz_id_2>,...`
- Ordering: rows sorted by numeric `contrast_id`, Topaz IDs sorted numerically within each row

## Plan of Work

### Milestone 1: Add contrast-ID definition helpers and lifecycle hooks

Implement helper methods in `wepppy/nodb/mods/omni/omni_state_contrast_mixin.py` to:

1. Resolve PSV path (`_contrast_id_definitions_path`).
2. Compute selected Topaz IDs for each runnable contrast ID from sidecar payload and contrast scenario targeting.
3. Write deterministic PSV output (`_write_contrast_id_definitions_psv`).
4. Optionally load/parse PSV for tests (`_load_contrast_id_definitions_psv`) if that keeps tests cleaner.
5. Remove stale PSV during `clear_contrasts()` and reset path(s) where contrast runs are cleared.

Wire write call in `wepppy/nodb/mods/omni/omni_build_router.py` immediately after `omni._build_contrasts()` and before `omni._build_contrast_ids_geojson()`.

Update `wepppy/nodb/mods/omni/omni.pyi` for any new mixin methods.

### Milestone 2: Add regression coverage for all selection modes

Extend tests to lock down the new artifact contract:

1. `tests/nodb/mods/test_omni.py`
   - cumulative mode: sequential `contrast_id` maps to selected Topaz IDs (not assumed equal).
   - user-defined areas/hillslope groups: multi-Topaz row shape and sparse-ID behavior.
   - stream-order: row generation from sidecar-targeted IDs.
2. `tests/nodb/mods/test_omni_state_contrast_mixin.py`
   - writer formatting, numeric sort order, stale-file cleanup behavior.
3. `tests/nodb/mods/test_omni_build_router_service.py`
   - router contract invokes new PSV write seam once per build call.

### Milestone 3: Document the new artifact contract

Update `wepppy/nodb/mods/omni/README.md` in the contrast execution flow section and artifacts list to include:

1. new canonical intermediary file path.
2. exact row format.
3. cumulative-mode clarification (`contrast_id` is run ID, selected hillslope appears in value list).

If implementation introduces additional user-facing semantics, update `wepppy/nodb/mods/omni/ENDUSER.md` minimally.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement helper methods and routing calls:

    edit wepppy/nodb/mods/omni/omni_state_contrast_mixin.py
    edit wepppy/nodb/mods/omni/omni_build_router.py
    edit wepppy/nodb/mods/omni/omni.pyi

2. Add and update tests:

    edit tests/nodb/mods/test_omni.py
    edit tests/nodb/mods/test_omni_state_contrast_mixin.py
    edit tests/nodb/mods/test_omni_build_router_service.py

3. Update docs:

    edit wepppy/nodb/mods/omni/README.md

4. Run targeted validation:

    wctl run-pytest tests/nodb/mods/test_omni.py tests/nodb/mods/test_omni_state_contrast_mixin.py tests/nodb/mods/test_omni_build_router_service.py --maxfail=1

5. Run broader Omni confidence suite:

    wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni_run_orchestration_service.py tests/nodb/mods/test_omni_station_catalog_service.py --maxfail=1

6. Run broad regression gate:

    wctl run-pytest tests --maxfail=1

7. Lint changed docs:

    wctl doc-lint --path docs/mini-work-packages/20260421_omni_contrast_id_definitions_psv_execplan.md
    wctl doc-lint --path wepppy/nodb/mods/omni/README.md

## Validation and Acceptance

Acceptance criteria:

1. Every successful contrast build creates `omni/contrast_id_definitions.psv`.
2. Each row is parseable as `<int>|<csv_of_ints>` with deterministic ordering.
3. Cumulative mode row values correspond to selected Topaz IDs even when `contrast_id != topaz_id`.
4. User-defined and stream-order modes emit correct multi-Topaz lists for runnable contrasts only.
5. `clear_contrasts()` removes the PSV so stale mappings are not retained.
6. Existing sidecar TSV and build report behavior remains unchanged.

## Idempotence and Recovery

The change is additive and idempotent. Rebuilding contrasts rewrites the PSV from current sidecars and state. If the file generation path fails during development, rollback is limited to removing the new helper calls and helper methods; existing sidecar-driven behavior remains intact.

## Interfaces and Dependencies

No new external dependencies are required.

Expected internal interface additions in `OmniStateContrastMixin`:

1. `_contrast_id_definitions_path(self) -> str`
2. `_write_contrast_id_definitions_psv(self) -> str`
3. Optional test helper: `_load_contrast_id_definitions_psv(self) -> Dict[int, List[int]]`

Expected router call-site update in `OmniBuildRouter.build_contrasts(...)`:

- invoke `omni._write_contrast_id_definitions_psv()` after `omni._build_contrasts()` and before `omni._build_contrast_ids_geojson()`.

Revision Notes:

- (2026-04-21 18:43Z, Codex) Created this mini work-package after codebase review to scope additive Omni contract work for `omni/contrast_id_definitions.psv`.
- (2026-04-21 20:03Z, Codex) Updated plan status to completed after implementation, tests, and docs updates.
