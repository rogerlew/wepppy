# Security Review - Landuse Legacy Flask State Route Removal (Post Gate 3)

> Dedicated security gate artifact for removing deprecated Flask landuse state routes.

## Metadata

- **Package**: `docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/`
- **Reviewer**: Codex
- **Date**: 2026-04-24
- **Scope reviewed**:
  - `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/nodb/core/landuse.py`
  - `wepppy/weppcloud/routes/run_0/run_0_bp.py`
  - `wepppy/weppcloud/routes/nodb_api/README.md`
  - `docs/schemas/rq-engine-agent-api-contract.md`
  - `wepppy/weppcloud/controllers_js/landuse.js`
  - `wepppy/weppcloud/controllers_js/landuse_modify_gl.js`
  - `wepppy/weppcloud/templates/controls/landuse_map.htm`
  - `wepppy/weppcloud/templates/controls/landuse_user_defined.htm`
  - `tests/weppcloud/routes/test_landuse_bp.py`
  - `tests/weppcloud/routes/test_pure_controls_render.py`
  - `tests/microservices/test_rq_engine_landuse_routes.py`
  - `tests/nodb/test_root_dir_materialization.py`
  - `tests/nodb/test_landuse_custom_mapping.py`
  - `tests/weppcloud/routes/test_run_0_openet_admin_gate.py`
- **Commit/branch context**: local working tree (`master`) at package scaffolding time
- **Related artifacts**:
  - Gate 3 security closure: `docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_security_review.md`
  - Prior migration package security review: `docs/work-packages/20260423_landuse_first_class_agent_interface_migration/artifacts/2026-04-24_security_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: route-surface removal changes auth/session entry points and may leave stale exposed paths or accidental fallback behavior.

## Gate Status Summary

- **Caller audit gate**: PASS (2026-04-24 06:24 UTC)
- **Route removal gate**: PASS (2026-04-24 06:27 UTC)
- **Render boundary gate**: PASS (2026-04-24 06:33 UTC)
- **Security closure gate**: PASS (2026-04-24 06:33 UTC)
- **Post-closure smoke remediation gate**: PASS (2026-04-24 06:54 UTC)
- **Post-closure state-integrity remediation gate**: PASS (2026-04-24 07:30 UTC)
- **Post-closure run-page recoverability remediation gate**: PASS (2026-04-24 07:38 UTC)
- **Post-closure stale-write recoverability remediation gate**: PASS (2026-04-24 07:50 UTC)
- **Post-closure custom-map description integrity remediation gate**: PASS (2026-04-24 08:00 UTC)
- **Post-closure title-row runid-link parity gate**: PASS (2026-04-24 08:08 UTC)

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-12 | High | Stale exposed legacy routes | Deprecated Flask endpoints might remain reachable post-removal due incomplete handler cleanup. | Route inventory and not-found verification for removed endpoints. | Closed |
| SEC-13 | High | Render-route regression | Removal patch could accidentally remove/modify render route handlers. | Assert render routes remain unchanged and covered by tests. | Closed |
| SEC-14 | Medium | In-repo caller drift | JS/templates/tests/docs may still reference removed endpoints. | Caller grep audit + update + regression checks. | Closed |
| SEC-15 | Medium | Fallback reintroduction | Cleanup could reintroduce cookie-based or silent fallback behavior. | Explicitly reject fallback additions and verify rq-engine-only machine/state paths. | Closed |
| SEC-16 | Medium | Contract/doc mismatch | Route/docs contracts may not reflect actual ownership after removal. | Update route docs/schemas and pass doc-lint + openapi/discovery checks. | Closed |
| SEC-17 | Medium | Upload archive policy | Finder-generated archives with valid `.man` payloads could fail on macOS sidecars (`__MACOSX/._*`, `.DS_Store`) and block run-scoped catalog updates. | Allow/ignore known metadata sidecars while preserving strict root `.man` payload policy and add regression tests. | Closed |
| SEC-18 | High | Destructive build cleanup | `Landuse.clean()` could remove run-scoped user-defined catalog files and `landuse_user_defined_mapping.json`, causing state-loss and cascading build failures. | Preserve run-scoped user-defined assets during clean and add regression coverage. | Closed |
| SEC-19 | High | Run-page recoverability | Stale missing system custom-map references could bubble through `run_0` render reads as unrecoverable `500` project-load failures. | Add explicit render-path stale-system-map recovery boundary with regressions; keep strict errors for non-system custom-map paths. | Closed |
| SEC-20 | High | Stale-write race on render recovery | Stale-system-map cleanup writeback on unlocked render reads could raise `NoDbStaleWriteError`, reintroducing run-page `500` failures. | Keep unlocked stale cleanup in-memory-only and add `NoDbStaleWriteError` retry recovery at `run_0` boundary with regressions. | Closed |
| SEC-21 | Medium | Custom-map description integrity | Changed custom-map assignments could retain stale base-map descriptions (for example key `43` still `Mixed Forest`), masking applied management overrides and severity labeling. | Normalize changed-key descriptions in map-save and relabel legacy stale custom-map descriptions during build summary creation. | Closed |

## Surface Checks

### 1) Auth, Session, and Authorization
- [x] Removed routes are not still reachable through alternate aliases.
- [x] rq-engine remains sole auth boundary for removed state/mutator operations.

### 2) Input Validation and Output Safety
- [x] Removal does not weaken existing rq-engine validation/error behavior.
- [x] No silent fallback wrappers are introduced during cleanup.

### 3) File System and Run-Tree Boundaries
- [x] Removed Flask handlers no longer perform state/file writes for migrated operations.
- [x] Remaining render handlers do not mutate state.
- [x] Landuse build cleanup no longer wipes run-scoped user-defined catalog/map override assets.

### 4) Data Integrity, Locking, and Concurrency
- [x] No stale local mutation path bypasses rq-engine concurrency controls.
- [x] Render-time landuse reads no longer create unrecoverable project-load failures for stale system map state.
- [x] Stale-system-map read recovery no longer performs unlocked writeback that can trigger stale-write hard failures.
- [x] Custom-map changed-key descriptions no longer retain stale base-map labels that mask applied management overrides.

### 5) Agentic Tooling and Discovery Surfaces
- [x] Docs/schemas accurately reflect final route ownership.
- [x] Endpoint discovery/openapi tests remain green.

## Validation Evidence

Executed command evidence:
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `20 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `46 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> `41 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `54 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `10 passed`.
- `wctl run-pytest tests/nodb/test_root_dir_materialization.py --maxfail=1` -> `7 passed`.
- `wctl run-pytest tests/nodb/test_landuse_custom_mapping.py --maxfail=1` -> `10 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1` -> `29 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path wepppy/weppcloud/routes/nodb_api/README.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> `10 files validated, 0 errors, 0 warnings`.

Caller audit evidence:
- `rg -n "tasks/set_landuse_mode|tasks/set_landuse_db|tasks/modify_landuse_coverage|tasks/modify_landuse_mapping|api/landuse/user_defined/catalog|tasks/landuse/user_defined/(upload|delete|update-description)|api/landuse/map_snapshot|tasks/landuse/map/(save|clear-override)|tasks/modify_landuse/" wepppy tests | grep -v "tests/weppcloud/routes/test_landuse_bp.py"` -> no output.
- `rg -n "tasks/set_landuse_mode|tasks/set_landuse_db|tasks/modify_landuse_coverage|tasks/modify_landuse_mapping|api/landuse/user_defined/catalog|tasks/landuse/user_defined/(upload|delete|update-description)|api/landuse/map_snapshot|tasks/landuse/map/(save|clear-override)|tasks/modify_landuse/" wepppy` -> no output.

## Verdict

- **Current verdict**: `pass`
- **Release recommendation**: `go` (no unresolved medium/high findings).

## Residual Risk and Follow-up

- No accepted residual medium/high risk.
- Remaining references to removed endpoints are limited to intentional negative regression tests and historical package documentation.
- Finder-sidecar compatibility risk is closed with explicit member-policy + staging filters and regression coverage.
- Landuse cleanup state-loss risk is closed by preserving `user-defined/` + `landuse_user_defined_mapping.json` during clean and covering the regression in NoDb tests.
- Run-page recoverability risk is closed by `run_0` stale-system-map recovery wrappers for landuse read paths with route-level regression coverage.
- Stale-write race risk is closed by in-memory-only unlocked stale cleanup and route-level stale-write retry coverage at the `run_0` boundary.
- Custom-map description integrity risk is closed by changed-key description normalization in map-save and build-time relabeling for legacy stale custom-map description drift.

## Sign-off

- **Security reviewer**: Codex
- **Sign-off date**: 2026-04-24 08:08 UTC
