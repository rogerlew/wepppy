# Security Review - Browse Arrow-to-Pandas Elimination

## Metadata

- **Package**: `docs/work-packages/20260616_browse_arrow_pandas_elimination/`
- **Reviewer**: Codex
- **Date**: 2026-06-16
- **Scope reviewed**:
  - `wepppy/microservices/browse/_download.py`
  - `wepppy/microservices/browse/browse.py`
  - `wepppy/microservices/browse/flow.py`
  - `wepppy/microservices/browse/parquet_tables.py`
  - `wepppy/microservices/parquet_filters.py`
  - route/helper tests updated under `tests/microservices/`
- **Commit/branch context**: local `master` working tree before implementation commit
- **Related artifacts**:
  - Inventory: `docs/work-packages/20260616_browse_arrow_pandas_elimination/artifacts/inventory.md`
  - RSS validation: `docs/work-packages/20260616_browse_arrow_pandas_elimination/artifacts/rss_validation.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package changes internals for public and authenticated browse/download routes that resolve run-scoped file paths and process user-selected parquet filter payloads.
- **Threat model assumptions**:
  - Users may control URL path components and parquet filter query payloads within existing browse route contracts.
  - Public runs can be accessed without an authenticated session, but private run access must remain restricted.
  - Run artifacts may be large or malformed and must not cause unbounded memory, process, or disk growth.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| None | N/A | N/A | No security findings were identified in the changed scope. | Review of changed routes/helpers plus validation gates below. | None. | Closed |

Risk acceptance authority: no accepted-risk entries required.

## Verdict

- **Gate status**: pass
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: acceptable for normal code review and deployment validation.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Existing run authorization entry points remain in `browse.py`; parquet preview/export helpers are called only after the existing route path and run-context resolution.
- [x] No role checks or token classes were widened.
- [x] No browser session mutation path was added, so CSRF scope is unchanged.
- [x] Error paths continue to use existing HTTP exceptions and parquet filter error payloads without token disclosure.

### 2) Secrets and Credential Handling

- [x] No new secrets, environment variables, secret mounts, or documentation examples were added.
- [x] Logs do not include tokens, query payloads, file contents, or credential-derived values.

### 3) Input Validation and Output Safety

- [x] Existing path validation and run-root checks remain the boundary for browse/download targets.
- [x] Parquet filter validation still flows through `compile_filter_payload_for_path`.
- [x] HTML table rendering escapes column names and cell values before emitting preview markup.
- [x] CSV serialization uses Python `csv.writer`; no shell interpolation or unsafe deserialization is introduced.
- [x] Unfiltered parquet previews are now capped by `BROWSE_PARQUET_PREVIEW_LIMIT`.

### 4) File System and Run-Tree Boundaries

- [x] No new file writes are introduced in production request paths.
- [x] CSV and filtered parquet responses are generated in memory and returned to the requester; no temporary run-tree artifacts are created.
- [x] The helper module assumes already-authorized paths but does not broaden path joins or symlink handling.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] No queue enqueue sites or dependency edges were changed.
- [x] No subprocesses were added.
- [x] `wctl check-rq-graph` is not required because queue wiring is unchanged.

### 6) Agentic Tooling and MCP Surfaces

- [x] No runtime MCP, agent, or tool-execution surface was added.
- [x] Development-time validation artifacts omit secrets and private payload contents.

### 7) Network and External Integrations

- [x] No new outbound network calls were added.
- [x] The D-Tale browse bridge remains a metadata-forwarding route to the existing D-Tale service.

### 8) CI/CD and Supply Chain

- [x] No workflows or runner permissions were changed.
- [x] No third-party dependency was added.

### 9) Data Integrity, Locking, and Concurrency

- [x] No NoDb persistence or locking contract was changed.
- [x] New helpers are request-local and do not mutate shared state.
- [x] CSV export is batch-oriented for unfiltered parquet files and does not require shared temp files.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Parquet preview/export telemetry logs operation, basename, size, row count when known, duration, RSS before/after, RSS delta, and status.
- [x] Telemetry intentionally omits full paths, query payloads, file contents, secrets, and auth state.
- [x] New exception handling is narrow; no new broad catch was introduced.
- [x] Rollback is the normal code rollback plus targeted `browse` restart to reload workers.

## Validation Evidence

Automated checks run:

```text
wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_download.py tests/microservices/test_browse_dtale.py tests/microservices/test_parquet_filters.py
-> 31 passed, 5 skipped

wctl run-pytest tests/microservices/test_download.py tests/microservices/test_browse_routes.py tests/microservices/test_parquet_filters.py
-> 28 passed

wctl run-pytest tests/microservices --maxfail=1
-> 965 passed, 5 skipped

python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
-> PASS, net unsuppressed broad-catch delta +0

wctl doc-lint --path docs/work-packages/20260616_browse_arrow_pandas_elimination
-> 6 files validated, 0 errors, 0 warnings

wctl doc-lint --path PROJECT_TRACKER.md
-> 1 file validated, 0 errors, 0 warnings

wctl doc-lint --path wepppy/microservices/browse/README.md
-> 1 file validated, 0 errors, 0 warnings
```

Manual checks run:

```text
rg -n "to_pandas|read_parquet|pd\.|pandas" wepppy/microservices/browse wepppy/microservices/parquet_filters.py
```

The remaining matches are documented in `artifacts/inventory.md` and are limited to DuckDB SQL `read_parquet`, pandas metadata handling, non-parquet CSV/TSV/pickle previews, schema helper names, and documentation text.

Worker RSS evidence is documented in `artifacts/rss_validation.md`.

## Residual Risk

- **Accepted residual risks**:
  - D-Tale itself may still use pandas internally in the separate D-Tale service. This package keeps parquet-to-pandas conversion out of `browse`, but does not replace D-Tale.
  - Local Gunicorn RSS validation is not a substitute for post-deployment observation on `wepp1`.
- **Follow-up packages/issues**:
  - Evaluate D-Tale replacement or disposable-process isolation for large parquet artifacts.
  - Monitor `wepp1` browse RSS after deployment over the package's 14-day observation window.

## Sign-off

- **Security reviewer**: Codex, 2026-06-16
- **Package owner**: Codex, 2026-06-16
