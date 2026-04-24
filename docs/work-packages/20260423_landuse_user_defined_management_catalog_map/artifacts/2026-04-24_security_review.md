# Security Review - Landuse User-Defined Management Catalog + Mapping Editor

> Implementation closeout security review and finding disposition.

## Metadata

- **Package**: `docs/work-packages/20260423_landuse_user_defined_management_catalog_map/`
- **Reviewer**: Codex
- **Date**: 2026-04-24
- **Scope reviewed**:
  - `wepppy/weppcloud/templates/controls/poweruser_panel.htm`
  - `wepppy/weppcloud/templates/controls/landuse_user_defined.htm`
  - `wepppy/weppcloud/templates/controls/landuse_map.htm`
  - `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/nodb/core/landuse.py`
  - `wepppy/wepp/management/managements.py`
  - `tests/weppcloud/routes/test_landuse_bp.py`
  - `tests/microservices/test_rq_engine_landuse_routes.py`
  - `tests/nodb/test_landuse_custom_mapping.py`
  - `tests/wepp/management/test_management_map_loading.py`
- **Commit/branch context**: local working tree (`master`) after implementation + test pass
- **Related artifacts**:
  - Tracker: `docs/work-packages/20260423_landuse_user_defined_management_catalog_map/tracker.md`
  - ExecPlan: `docs/work-packages/20260423_landuse_user_defined_management_catalog_map/prompts/completed/landuse_user_defined_management_catalog_map_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: feature adds untrusted upload/archive handling, run-tree writes, and run-scoped mapping mutation APIs.
- **Threat model assumptions**:
  - Routes remain authenticated and run-scoped authorization is enforced for all mutations.
  - Uploads are untrusted and may be adversarially crafted.
  - Run roots may be concurrently mutated by multiple requests/jobs.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Input validation / archive ingestion | `.zip` import can be abused via traversal, encrypted entries, unsupported compression, zip bombs, or duplicate paths if custom extraction is implemented ad hoc. | `landuse_bp.py` now routes `.zip` handling through hardened validator with strict `.man` member policy and explicit archive limits; regression added in `tests/weppcloud/routes/test_landuse_bp.py`. | Reuse shared archive validator with strict `.man` member policy and explicit limits; add abuse regression tests. | Resolved |
| SEC-02 | High | File system / run-tree boundaries | Catalog and mapping writes can escape intended run scope or overwrite unintended files if path normalization is weak. | Writes are constrained to run-scoped `landuse/user-defined/` and `landuse/` paths; secure filename handling and validated relative mapping path contract enforced in `landuse.py`. | Restrict writes to `landuse/user-defined/` + `landuse/`; enforce secure filenames and normalized relative paths only. | Resolved |
| SEC-03 | Medium | Auth/CSRF boundary | Browser-session mutations for new WEPPcloud routes can be vulnerable if CSRF/same-origin contracts are not preserved. | New mutation routes use existing Flask session-protected route patterns under nodb API blueprint; no CSRF-exempt mutation route introduced. | Preserve Flask CSRF/session mutation contracts. | Resolved |
| SEC-04 | Medium | Data integrity / concurrency | Concurrent catalog/map edits can create stale writes or mixed state if updates are non-atomic. | Mapping save requires snapshot SHA (`X-If-Match-Sha256`/body fallback) and uses atomic temp-write + rename; route tests cover if-match and stale-write contract. | Use optimistic concurrency and atomic temp-write + rename for mapping/catalog metadata. | Resolved |
| SEC-05 | Medium | Parser safety / denial-of-service | Oversized or malformed `.man` files can stress parser code paths and error handling. | Upload size caps enforced for `.man` and `.zip` inputs; map-loader parsing now throws typed errors for invalid JSON/shape; regression tests cover invalid-map failure modes. | Enforce file size caps and explicit bounded parse failure responses. | Resolved |

Risk acceptance authority: Not required (no unresolved medium/high findings).

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: proceed

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for changed routes/services.
- [x] Session/JWT token validation paths preserve canonical contracts.
- [x] CSRF protections are preserved for browser session mutation paths.
- [x] Error paths avoid leaking auth internals.

### 2) Secrets and Credential Handling

- [x] No new plaintext secrets in repository files, env defaults, or docs examples.
- [x] No secrets passed in argv, query params, or logs.
- [x] Changed code avoids fallback wrappers that silently skip missing secrets.

### 3) Input Validation and Output Safety

- [x] Untrusted input is validated at boundaries (extensions, sizes, map shape, path contract).
- [x] File/path inputs block traversal and out-of-scope path access.
- [x] Failing validation returns explicit contract-compliant errors.

### 4) File System and Run-Tree Boundaries

- [x] Writes remain inside intended run roots and approved `landuse/` subpaths.
- [x] Path joins for upload and map persistence are constrained and validated.
- [x] Temporary files are atomically promoted or discarded.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Queue wiring was not widened for this package (no enqueue graph mutation required).
- [x] rq-engine route validation now rejects invalid configured custom maps before enqueue.
- [x] Failure handling preserves canonical response/error contracts.

### 9) Data Integrity, Locking, and Concurrency

- [x] NoDb lock/dump contracts are preserved in run mutation paths.
- [x] Mapping save supports optimistic concurrency and atomic write semantics.
- [x] Regression coverage includes stale-write and custom-map error paths.

## Validation Evidence

- Automated checks run:
  - `.venv/bin/pytest tests/wepp/management/test_management_map_loading.py tests/nodb/test_landuse_custom_mapping.py tests/microservices/test_rq_engine_landuse_routes.py tests/weppcloud/routes/test_landuse_bp.py tests/weppcloud/routes/test_pure_controls_render.py -q` -> `86 passed`
  - `wctl doc-lint --path docs/work-packages/20260423_landuse_user_defined_management_catalog_map` -> `5 files validated, 0 errors, 0 warnings`
- Manual checks run:
  - Route/auth contract audit for new Flask/rq-engine surfaces.
  - Run-tree path and archive boundary review for catalog/map persistence.

## Residual Risk

- **Accepted residual risks**:
  - None.
- **Follow-up packages/issues**:
  - Optional: add a broader abuse fixture matrix for large mixed zip member sets if future scope expands beyond `.man` catalogs.

## Sign-off

- **Security reviewer**: Codex
- **Package owner**: Codex
- **Sign-off date**: 2026-04-24
