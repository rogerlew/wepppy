# Features Export WP-2 Dependency Tracking and Options-Aware Caching Foundation

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and must be maintained in accordance with that template.

## Purpose / Big Picture

WP-2 creates the deterministic dependency and cache-key foundation for Features Export without adding exporters, routes, or artifact generation. After this work, the backend can fingerprint resolved filesystem dependencies from a WP-1 `ResolvedExportPlan`, compute an options-aware cache key that includes selector defaults and version markers, and persist/retrieve cache index records at `export/features/cache/index.json` with stable serialization.

## Progress

- [x] (2026-03-26 17:10Z) Read required guidance and source context: root `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, features export specification (including sections 6 and 14), and existing WP-1 module/test files.
- [x] (2026-03-26 17:11Z) Created this WP-2 ExecPlan at the required path.
- [x] (2026-03-26 17:20Z) Implemented `dependency_tracker.py` and `cache_key.py` with deterministic dependency snapshot/fingerprint, request hash/cache key, and persistent cache index helper APIs.
- [x] (2026-03-26 17:20Z) Updated `wepppy/nodb/mods/features_export/__init__.py` exports for new WP-2 APIs.
- [x] (2026-03-26 17:21Z) Added focused WP-2 tests under `tests/nodb/mods/` for dependency tracking and cache key/index helpers.
- [x] (2026-03-26 17:24Z) Ran requested validation commands and captured outcomes.
- [x] (2026-03-26 17:26Z) Updated `specification.md` with WP-2 completion status and contract clarifications.
- [x] (2026-03-26 17:27Z) Completed review pass (no additional fixes required after tests) and finalized retrospective notes.

## Surprises & Discoveries

- Observation: WP-1 normalized request defaults already enforce canonical ordering for `layers` and `output_scopes`, reducing extra cache-key canonicalization logic needed in WP-2.
  Evidence: `planner.py` returns sorted unique `layers` and canonical scope order.
- Observation: The third requested validation command used an incomplete pytest flag (`--maxfail=`), which fails before test collection.
  Evidence: `pytest: error: argument --maxfail: invalid int value: ''`; reran with `--maxfail=1` to obtain usable validation evidence.

## Decision Log

- Decision: Keep WP-2 APIs independent from route/RQ wiring and avoid speculative orchestration abstractions.
  Rationale: User requested strict WP-2-only scope; section 14 sequencing explicitly defers orchestration to later work packages.
  Date/Author: 2026-03-26 / Codex
- Decision: Require explicit `nodb_ref_resolver` input for `nodb_ref` locator resolution in WP-2 helpers.
  Rationale: This keeps resolution explicit/testable and avoids hidden controller import/runtime dependencies before service orchestration exists.
  Date/Author: 2026-03-26 / Codex
- Decision: Require pre-resolved table names for `path_template` locators containing `{table_name}`.
  Rationale: SWAT table discovery belongs to later orchestration steps; WP-2 foundation must fail explicitly when selector resolution is incomplete.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

WP-2 is complete within requested scope. The module now includes deterministic dependency snapshot/fingerprint helpers, options-aware request hash + cache key construction, and persistent cache index load/get/upsert helpers at `export/features/cache/index.json`. New tests cover deterministic behavior and explicit failure contracts (`nodb_ref` resolver requirement, unresolved `{table_name}`, `swat_run_id=\"latest\"` rejection, and `units=project` Unitizer fingerprint requirement).

No route/RQ/UI/exporter logic was introduced. The only execution issue encountered was the malformed `--maxfail=` flag in one requested command; this was reported and rerun with `--maxfail=1`.

## Context and Orientation

Relevant WP-1 code lives in:
- `wepppy/nodb/mods/features_export/contracts.py`
- `wepppy/nodb/mods/features_export/catalog_loader.py`
- `wepppy/nodb/mods/features_export/planner.py`

WP-2 files to add now:
- `wepppy/nodb/mods/features_export/dependency_tracker.py`
- `wepppy/nodb/mods/features_export/cache_key.py`

Tests to add now:
- `tests/nodb/mods/test_features_export_dependency_tracker.py`
- `tests/nodb/mods/test_features_export_cache_key.py`

Docs to update now:
- `wepppy/nodb/mods/features_export/specification.md`

## Plan of Work

Implement dependency tracking first. This includes strict locator validation, path-template expansion from resolved selectors, optional nodb-ref resolution through an explicit resolver contract, deterministic dependency entry generation, and fingerprinting from canonical JSON. Include catalog signature/version and project-unit `unitizer.nodb` dependency handling.

Implement cache-key logic next. Build request hashes only from normalized payloads with concrete `swat_run_id`, include unitizer preference fingerprint for `units=project`, include version markers, then build final cache keys by combining request hash and dependency fingerprint.

Add a persistent cache-index helper that reads/writes `export/features/cache/index.json` deterministically and supports load/get/upsert semantics only.

Then add focused tests for behavior and error contracts, update package exports, run requested validations, and document WP-2 status/clarifications in the specification.

## Concrete Steps

From `/workdir/wepppy`:

1. Add `dependency_tracker.py` and `cache_key.py` under `wepppy/nodb/mods/features_export/`.
2. Update `wepppy/nodb/mods/features_export/__init__.py` exports.
3. Add tests:
   - `tests/nodb/mods/test_features_export_dependency_tracker.py`
   - `tests/nodb/mods/test_features_export_cache_key.py`
4. Run required validation commands:
   - `wctl run-pytest tests/nodb/mods/test_features_export_dependency_tracker.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_features_export_cache_key.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_features_export_catalog_loader.py --maxfail=1`
5. Update `wepppy/nodb/mods/features_export/specification.md` with WP-2 status/contract notes.
6. Update this ExecPlan with final evidence and retrospective.

## Validation and Acceptance

Acceptance for WP-2 requires:
- Deterministic dependency entry + fingerprint generation from resolved plan and catalog locators.
- Strict locator contract enforcement (`kind` and `value` only; supported kinds only).
- Inclusion of catalog signature and `unitizer.nodb` dependency when `units=project`.
- Deterministic cache-key generation from normalized request + dependency fingerprint.
- `swat_run_id="latest"` rejection for cache-key inputs.
- Persistent cache index helper with load/get/upsert semantics and deterministic JSON serialization.
- Requested validation commands passing.

## Idempotence and Recovery

Changes are additive and isolated to the features export module/tests/docs. All requested test commands are safe to rerun. If a test fails, patch only affected files, rerun targeted tests, and then rerun the requested command set.

## Artifacts and Notes

Validation evidence from `/workdir/wepppy`:
- `wctl run-pytest tests/nodb/mods/test_features_export_dependency_tracker.py --maxfail=1` -> pass (3 passed).
- `wctl run-pytest tests/nodb/mods/test_features_export_cache_key.py --maxfail=1` -> pass (4 passed).
- `wctl run-pytest tests/nodb/mods/test_features_export_catalog_loader.py --maxfail=` -> expected CLI failure (invalid empty `--maxfail` value).
- `wctl run-pytest tests/nodb/mods/test_features_export_catalog_loader.py --maxfail=1` -> pass (2 passed).

## Interfaces and Dependencies

Planned WP-2 interfaces:
- Dependency tracking dataclasses/helpers in `dependency_tracker.py`.
- Cache-key and cache-index helpers in `cache_key.py`.

No new external dependencies will be introduced.

## Revision Notes

- 2026-03-26 (Codex): Created WP-2 ExecPlan with implementation/test/doc update plan and required living sections.
- 2026-03-26 (Codex): Marked implementation complete, recorded dependency/cache contract decisions, captured validation evidence (including malformed-command rerun), and finalized retrospective.
