# Security Review - SSURGO Project SQLite Cache

> Dedicated security review artifact for a high-impact work package. Gate status is `pass`; package closure remains blocked separately by the unrelated full-suite validation failure recorded in `tracker.md`.

## Metadata

- **Package**: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/`
- **Reviewer**: Codex
- **Date**: 2026-06-19
- **Scope reviewed**: Project-local SSURGO/STATSGO SQLite cache implementation, NoDb option serialization, RQ route parsing, soil pure checkbox wiring, cache-clear tests, docs, and validation-gate cleanups.
- **Commit/branch context**: Working tree implementation state on `master`.
- **Related artifacts**:
  - Code review: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/code_review_findings.md`
  - QA review: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/qa_review_findings.md`
  - Package authoring review: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/package_authoring_review_findings.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The implementation changes an authenticated build endpoint payload and creates or deletes run-scoped SQLite files under `<wd>/soils/`.
- **Threat model assumptions**:
  - Request payload fields are untrusted even when sent by the first-party UI.
  - Cache file paths must be derived from `Soils.soils_dir`, not from request payloads or serialized absolute paths.
  - Cache clearing must not delete generated `.sol` files, user uploads, cache files outside the run tree, or non-cache artifacts.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | File system boundary | Cache clearing needed path confinement and exact sidecar deletion. | `Soils._project_surgo_cache_path`, `Soils._clear_project_surgo_cache`, `tests/nodb/test_soils_ssurgo_cache.py` | Derive cache paths from `self.soils_dir`, realpath-check the effective soils directory under `self.wd`, realpath-check each candidate under the effective soils directory, delete only `<cache_path>`, `<cache_path>-wal`, and `<cache_path>-shm`, and refuse directories. | Resolved |
| SEC-02 | Medium | RQ route payload | The checkbox option needed typed parsing and persistence before enqueue and batch no-enqueue return. | `wepppy/microservices/rq_engine/soils_routes.py`, `tests/microservices/test_rq_engine_soils_routes.py` | Parse `clear_ssurgo_cache_on_rebuild` as a boolean field and persist it on `Soils` before any enqueue/batch branch. | Resolved |
| SEC-03 | Medium | Queue and worker consistency | Queue shape and cache-clear/use concurrency needed to remain safe. | `build_soils_rq(runid)` call shape unchanged; `_build_spatial_api`, `_build_gridded`, `_build_single`, and `build_statsgo` cache use occur under existing `Soils.locked()` boundaries; `tests/nodb/test_soils_ssurgo_cache.py` constructor-site inspection. | Preserve queue edges and keep cache clearing serialized with cache construction/use. | Resolved |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off. No security risk acceptance is requested.

## Verdict

- **Gate status**: pass
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: no security hold. Non-security validation status is tracked in `tracker.md`.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Existing entry-point auth/session behavior is preserved; no route access policy was widened.
- [x] CSRF and browser session contracts are unchanged; the UI posts the existing soil form.

### 2) Secrets and Credential Handling

- [x] No new plaintext secrets, credentials, mounts, or env defaults were introduced.

### 3) Input Validation and Output Safety

- [x] The new request option is parsed as a boolean boundary field.
- [x] Cache file paths are not accepted from user input.
- [x] No unsafe deserialization or shell interpolation was introduced.

### 4) File System and Run-Tree Boundaries

- [x] Project cache paths are derived from `<wd>/soils/`.
- [x] Cache clearing refuses symlink-resolved soils directories outside the project root.
- [x] Cache clearing removes only the named SQLite file and exact SQLite sidecars.
- [x] Cache clearing refuses non-symlink directories.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Queue shape is unchanged: `build_soils_rq(runid)` is still the worker entry.
- [x] `wctl check-rq-graph` was not required because enqueue sites and dependency edges were not changed.
- [x] Failure handling preserves existing response/error contracts for the changed route.

### 6) Agentic Tooling and MCP Surfaces

- [x] Subagents were used only for required code/QA review and did not receive broader authority than this work package required.

### 7) Network and External Integrations

- [x] No new outbound integrations were introduced.
- [x] Existing NRCS SSURGO request paths, timeouts, and retry behavior were not widened.

### 8) CI/CD and Supply Chain

- [x] No new third-party dependencies or workflow changes were introduced.

### 9) Data Integrity, Locking, and Concurrency

- [x] `Soils` persists the new option through existing NoDb setters/backfill.
- [x] Cache clear and cache use are serialized by existing `Soils.locked()` boundaries in project build paths.
- [x] Redis keyspaces and TTL behavior are unchanged.

### 10) Logging, Monitoring, and Incident Readiness

- [x] No broad production exception swallowing was added.
- [x] Cache path failures raise explicit exceptions with contextual paths.

## Validation Evidence

- Automated checks run:
  - `python -m py_compile wepppy/soils/ssurgo/ssurgo.py wepppy/nodb/core/soils.py wepppy/microservices/rq_engine/soils_routes.py wepppy/microservices/rq_engine/schema_defaults_routes.py`
  - `wctl run-pytest tests/soils/test_ssurgo_cache.py tests/nodb/test_soils_ssurgo_cache.py --maxfail=1`
  - `wctl run-pytest tests/soils/test_ssurgo_cache.py tests/nodb/test_soils_ssurgo_cache.py tests/nodb/test_soils_gridded_root_creation.py tests/microservices/test_rq_engine_soils_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
  - `wctl run-npm test`
  - `wctl run-npm lint`
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- Manual checks run:
  - Verified `build_soils_rq(runid)` queue shape remains unchanged.
  - Verified full-suite blocker is deterministic and outside this security surface: `tests/weppcloud/routes/test_wepp_bp.py::test_view_management_effective_returns_texture_specific_preview[clay-1.1-2.1-0.11]`.

## Residual Risk

- **Accepted residual risks**: none for security.
- **Follow-up packages/issues**:
  - Non-security full-suite blocker: the unrelated WEPP disturbed preview route test recorded in `tracker.md`.
  - Live generated-run smoke coverage remains unrun; current cache-file creation/reuse coverage is deterministic and fixture-based.

## Sign-off

- **Security reviewer**: Codex, 2026-06-19
- **Package owner**: Pending package closure decision, 2026-06-19
