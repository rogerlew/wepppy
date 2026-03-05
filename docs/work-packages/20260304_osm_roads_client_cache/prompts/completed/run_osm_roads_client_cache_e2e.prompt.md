# Outcome (Completed 2026-03-05)

- Status: Completed end-to-end implementation and validation for the OSM roads client cache package.
- Accomplished: Milestones 1-5 shipped across `wepppy/topo/osm_roads/`, TerrainProcessor consumer seam wiring, runtime docs, and regression tests.
- Extended completion artifact: added dedicated Postgres functional suite (`tests/topo/test_osm_roads_postgres_integration.py`) and rollout/migration runbook (`artifacts/postgres_migration_setup.md`) for forest1/production deployment.
- Validation: Required gates passed, including targeted topo suites, full `tests --maxfail=1`, broad-exception enforcement, and required doc-lint checks.
- Notes: Implementation follows the hybrid contract (PostgreSQL metadata/locks + file payloads) with lock-safe refresh, bounded stale/expired fallback, clip/reproject, and deterministic keying.

# Prompt: Execute OSM Roads Client Cache Work-Package End-to-End

You are implementing the WEPPpy OSM roads client with persistent server-side cache.

## Mandatory startup
1. Read `/workdir/wepppy/AGENTS.md`.
2. Read `/workdir/wepppy/docs/work-packages/20260304_osm_roads_client_cache/package.md`.
3. Read `/workdir/wepppy/docs/work-packages/20260304_osm_roads_client_cache/module_contract.md`.
4. Read `/workdir/wepppy/docs/work-packages/20260304_osm_roads_client_cache/prompts/active/osm_roads_client_cache_execplan.md`.

## Execution rule
Follow the active ExecPlan milestone by milestone. Do not skip validation gates. Keep the ExecPlan and package tracker as living documents while implementing.

## Goal
Deliver a production-ready OSM roads module in WEPPpy with:
- concrete request/response contract compliance,
- persistent server-wide hybrid cache (PostgreSQL metadata/locks + `/wc1` payload files),
- deterministic keying and TTL behavior,
- per-key lock-safe cache population,
- Overpass fetch + normalization + clip/reproject pipeline,
- consumer seam for `roads_source="osm"`.

## Required outputs
- New module files under `wepppy/topo/osm_roads/`.
- Tests for contracts/cache/service concurrency and stale/expired-on-error behavior.
- Updated docs for config/runtime operation.
- Updated work-package docs (`tracker.md` and ExecPlan living sections).

## Validation gates (must pass)
- `wctl run-pytest tests/topo/test_osm_roads_contracts.py`
- `wctl run-pytest tests/topo/test_osm_roads_cache.py`
- `wctl run-pytest tests/topo/test_osm_roads_service.py`
- `wctl run-pytest tests/topo -k osm_roads`
- `wctl run-pytest tests --maxfail=1`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- `wctl doc-lint --path docs/work-packages/20260304_osm_roads_client_cache`
- `wctl doc-lint --path PROJECT_TRACKER.md`
- `wctl doc-lint --path AGENTS.md`

## Review requirements
Before handoff:
1. Perform correctness review (cache keying, PostgreSQL advisory lock behavior, CRS clip/reproject correctness).
2. Perform maintainability review (module boundaries, explicit errors, test readability).
3. Fix all high/critical findings before final summary.

## Handoff format
Provide:
1. Summary of implemented behavior.
2. Full list of changed files.
3. Commands run with key outputs.
4. Review findings and fixes.
5. Residual risks/follow-up recommendations.
