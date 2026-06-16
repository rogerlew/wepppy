# Tracker - Browse Arrow-to-Pandas Elimination

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-06-16 18:58 UTC  
**Current phase**: Implementation complete locally / production observation pending  
**Last updated**: 2026-06-16 19:24 UTC  
**Next milestone**: Review, commit, deploy when appropriate, then monitor `wepp1` browse worker RSS for the 14-day observation window.  
**Security impact**: high  
**Dedicated security review**: yes  
**Security artifact**: `docs/work-packages/20260616_browse_arrow_pandas_elimination/artifacts/20260616_security_review.md`  
**Implementation plan**: `docs/work-packages/20260616_browse_arrow_pandas_elimination/prompts/active/browse_arrow_pandas_elimination_execplan.md`

## Task Board

### Ready / Backlog
- [ ] Monitor `wepp1` browse worker RSS after deployment and append production observation notes.

### In Progress
- [ ] Review/commit/deploy handoff.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, active ExecPlan, security review stub, prompts/notes/artifacts directories) (2026-06-16 18:58 UTC).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-06-16 18:58 UTC).
- [x] Ran scoped documentation lint for package docs and `PROJECT_TRACKER.md` (2026-06-16 19:02 UTC).
- [x] Inventoried browse parquet DataFrame materialization call sites and captured results in `artifacts/inventory.md` (2026-06-16 19:10 UTC).
- [x] Added Arrow-backed browse parquet helper module for schema projection, HTML rendering, CSV writing, pandas index-column dropping, and RSS telemetry (2026-06-16 19:10 UTC).
- [x] Changed `parquet_filters.query_preview` to return Arrow tables instead of pandas DataFrames (2026-06-16 19:10 UTC).
- [x] Replaced parquet preview path in `flow.py` with bounded Arrow/DuckDB preview rendering (2026-06-16 19:10 UTC).
- [x] Replaced parquet-to-CSV download conversion with Arrow table/batch CSV writing (2026-06-16 19:10 UTC).
- [x] Confirmed D-Tale browse bridge only forwards metadata; pandas conversion remains in separate D-Tale service and is follow-up scope (2026-06-16 19:10 UTC).
- [x] Updated browse README for no-DataFrame parquet behavior and telemetry (2026-06-16 19:10 UTC).
- [x] Ran focused route/helper tests: `31 passed, 5 skipped` (2026-06-16 19:10 UTC).
- [x] Restarted local `browse` service and captured HTTP worker RSS evidence for representative parquet preview and CSV export in `artifacts/rss_validation.md` (2026-06-16 19:24 UTC).
- [x] Completed dedicated security review artifact with no unresolved findings (2026-06-16 19:24 UTC).
- [x] Ran broad microservice validation: `965 passed, 5 skipped` (2026-06-16 19:24 UTC).
- [x] Ran changed-file broad exception gate: PASS, net delta `+0` (2026-06-16 19:24 UTC).

## Timeline

- **2026-06-16 18:58 UTC** - Package created after `wepp1` browse high-RSS incident investigation and upstream PyArrow/pandas RSS research.
- **2026-06-16 19:10 UTC** - Implemented Arrow-backed preview/CSV paths and focused route/helper tests passed.
- **2026-06-16 19:24 UTC** - Local Gunicorn RSS validation, broad microservice tests, broad exception gate, and security review completed.

## Decisions Log

### 2026-06-16 18:58 UTC: Treat this as incident-driven hardening and migration
**Context**: Production `browse` workers retained tens of GiB RSS, and upstream research indicates Arrow-to-pandas conversion can leave high process RSS even after Python objects are deleted.

**Options considered**:
1. Tune `max-requests`, allocator decay, or `release_unused()` only.
2. Remove Arrow-to-pandas conversion from long-lived `browse` workers and keep allocator tuning as secondary cleanup.

**Decision**: Scope this package around eliminating Arrow-to-pandas conversion from `browse` request paths.

**Impact**: The package must produce route-level behavior parity and production-like memory evidence, not just helper refactors.

---

### 2026-06-16 18:58 UTC: Security triage is high
**Context**: Browse serves public and authenticated run files, and this package will change file preview/download/export internals.

**Options considered**:
1. Treat as low risk because the user-visible route contract should remain unchanged.
2. Treat as high risk because route internals touch public download/path handling and may add subprocess isolation.

**Decision**: Mark security impact `high` and create a dedicated security review artifact.

**Impact**: The package cannot close until the security artifact has no unresolved medium/high findings.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| CSV export still materializes a whole parquet file indirectly | High | Medium | Add tests and code search gates that fail on `pd.read_parquet`/`to_pandas` under `wepppy/microservices/browse` | Mitigated locally |
| D-Tale requires pandas and reintroduces high RSS inside `browse` | High | Medium | Keep D-Tale conversion out of `browse`; isolate or defer D-Tale internals if necessary | Mitigated for `browse`; D-Tale follow-up remains |
| Streaming export changes CSV formatting or filter semantics | Medium | Medium | Golden route tests for filtered/unfiltered CSV output and documented compatibility notes | Mitigated locally |
| New helper weakens path/auth validation | High | Low | Reuse existing browse path validators and run security review by surface | Closed |
| Observability logs leak file paths or private data | Medium | Low | Log basename, size, rows, duration, RSS, and status only; avoid file contents, full paths, and query payloads | Closed |
| Memory improvement cannot be reproduced locally | Medium | Medium | Capture production-like validation on local Gunicorn browse stack with explicit run artifact and RSS samples | Closed locally; monitor production after deploy |

## Hardening Signal Log

- **Baseline health signals**: June 16 incident found two `browse` workers around 45-49 GiB RSS and repeated `WORKER TIMEOUT` events.
- **Post-change health signals**: Local Gunicorn probe of a 34 MB parquet preview plus 153 MB CSV export settled with hottest worker around 583 MiB after 15 seconds.
- **Danger signals observed**: None in local validation. Production observation still needed after deployment.
- **Temporary callus register**: None.
- **Softening experiments**: TBD after observation window.

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/microservices/test_browse_routes.py`
- [x] `wctl run-pytest tests/microservices/test_download.py`
- [x] `wctl run-pytest tests/microservices/test_browse_dtale.py`
- [x] `wctl run-pytest tests/microservices --maxfail=1`
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`

### Security
- [x] Security impact triage recorded (`high`) with rationale.
- [x] Dedicated security review artifact created.
- [x] No unresolved medium/high security findings remain in the security artifact.
- [x] Auth/path/download behavior changes are explicitly reviewed.
- [x] Subprocess or worker-isolation behavior is reviewed if added.

### Documentation
- [x] Work package scaffold created.
- [x] Browse README updated for no-DataFrame parquet path.
- [x] Incident mitigation evidence recorded in package artifacts.
- [x] Work package implementation closeout notes complete.
- [x] Parameterization ADR not required because no parameterization behavior changes are planned.

### Testing
- [x] Unit or helper tests cover no-DataFrame parquet helper behavior.
- [x] Route tests cover preview, filtered preview, download, CSV export, and D-Tale launch.
- [x] Compatibility tests verify existing filter semantics from `docs/schemas/weppcloud-browse-parquet-filter-contract.md`.
- [x] Production-like local Gunicorn RSS validation evidence captured.

### Deployment
- [x] Tested in `docker-compose.dev.yml` environment.
- [ ] Deployed to `wepp1` or otherwise validated in production after review.
- [x] Rollback plan documented before production deployment.

## Progress Notes

### 2026-06-16 18:58 UTC: Initial package scaffold
**Agent/Contributor**: Codex

**Work completed**:
- Read work-package, tracker, ExecPlan, and security review templates.
- Scoped the package around eliminating Arrow-to-pandas conversion from long-lived `browse` workers.
- Created package directory and initial docs.
- Added package to `PROJECT_TRACKER.md` backlog.

**Blockers encountered**:
- None for scaffolding. D-Tale pandas dependency remains an implementation discovery item.

**Next steps**:
1. Search `wepppy/microservices/browse` for `to_pandas`, `pd.read_parquet`, and pandas import paths.
2. Read current preview/download/D-Tale route code and tests.
3. Update the active ExecPlan with discovered exact call sites and replacement helper signatures before editing code.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260616_browse_arrow_pandas_elimination` -> pass (`4 files validated, 0 errors, 0 warnings`).
- `wctl doc-lint --path PROJECT_TRACKER.md` -> pass (`1 files validated, 0 errors, 0 warnings`).

### 2026-06-16 19:10 UTC: Arrow-backed browse parquet implementation
**Agent/Contributor**: Codex

**Work completed**:
- Added `wepppy/microservices/browse/parquet_tables.py` for Arrow table projection, pandas physical index-column removal, HTML rendering, CSV writing, and RSS telemetry.
- Updated `wepppy/microservices/parquet_filters.py::query_preview` to return Arrow tables.
- Updated `wepppy/microservices/browse/flow.py` so filtered and unfiltered parquet previews use bounded Arrow/DuckDB tables and direct HTML rendering.
- Updated `wepppy/microservices/browse/_download.py` so parquet-to-CSV export avoids DataFrames:
  - unfiltered CSV uses `ParquetFile.iter_batches`
  - filtered CSV uses the existing row-capped Arrow export
- Updated `wepppy/microservices/browse/README.md` with no-DataFrame parquet behavior and telemetry expectations.
- Updated focused tests in `tests/microservices/test_download.py` and `tests/microservices/test_parquet_filters.py`.
- Captured implementation inventory in `artifacts/inventory.md`.

**Blockers encountered**:
- Production-like RSS validation still needs an environment decision. Local route tests prove behavior, but not worker RSS behavior under a real Gunicorn browse worker.

**Next steps**:
1. Run broad microservice tests and docs lint.
2. Complete security review artifact.
3. Capture local or production-like RSS validation evidence.

**Test results**:
- Baseline before changes: `wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_download.py tests/microservices/test_browse_dtale.py tests/microservices/test_parquet_filters.py` -> pass (`31 passed, 5 skipped`).
- After implementation: same focused suite -> pass (`31 passed, 5 skipped`).
- After batched CSV change: `wctl run-pytest tests/microservices/test_download.py tests/microservices/test_browse_routes.py tests/microservices/test_parquet_filters.py` -> pass (`28 passed`).

### 2026-06-16 19:24 UTC: Local validation and security closeout
**Agent/Contributor**: Codex

**Work completed**:
- Restarted the local `browse` service so Gunicorn workers loaded the new code.
- Ran HTTP preview and full CSV export probes against a 34 MB `H.wat.parquet` artifact from `/wc1/runs/ho/honeyed-marathoner`.
- Captured worker RSS evidence in `artifacts/rss_validation.md`.
- Fixed parquet telemetry logger visibility so INFO-level operation logs appear in the `browse` container logs.
- Completed the high-impact security review artifact with no unresolved findings.
- Ran broad microservice tests and changed-file broad exception enforcement.

**Blockers encountered**:
- None for local execution. Production observation on `wepp1` remains a post-deployment activity because local validation cannot prove NFS, Caddy, public traffic, or long-lived production worker behavior.

**Next steps**:
1. Review and commit the package implementation.
2. Deploy/restart `browse` when ready.
3. Append `wepp1` observation notes during the 14-day monitoring window.

**Test results**:
- `wctl run-pytest tests/microservices --maxfail=1` -> pass (`965 passed, 5 skipped`).
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> pass (`net delta +0`).
- `wctl doc-lint --path docs/work-packages/20260616_browse_arrow_pandas_elimination`, `wctl doc-lint --path PROJECT_TRACKER.md`, and `wctl doc-lint --path wepppy/microservices/browse/README.md` -> pass.
- Code-search gate -> no `pd.read_parquet(...)` or `table.to_pandas()` remains in production `browse` request paths; expected matches are documented in `artifacts/inventory.md`.
- Local HTTP RSS probe -> preview `200` in `0.281098s`, CSV export `200` in `103.551648s`, hottest worker settled at about `582856 KiB`.

## Watch List

- **D-Tale coupling**: D-Tale may still require pandas internally; the package target is to keep conversion out of `browse` even if D-Tale remains pandas-backed elsewhere.
- **Allocator knobs**: `pyarrow.default_memory_pool().release_unused()` and `jemalloc_set_decay_ms(0)` can be cleanup aids, but this package should not depend on them as the primary fix.
- **NFS stalls**: The June 16 incident also showed NFS metadata stalls; this package targets high RSS from parquet conversion, not all possible browse latency causes.

## Communication Log

### 2026-06-16 18:58 UTC: Package requested
**Participants**: User, Codex  
**Question/Topic**: Scaffold a work package to eliminate Arrow-to-pandas conversion in the browse service.  
**Outcome**: Package scaffold created with high security triage and active ExecPlan.

## Handoff Summary Template

**From**: Current agent  
**To**: Next agent  
**Date**: YYYY-MM-DD HH:MM UTC

**What's complete**:
- Package scaffold and tracker entry exist.

**What's next**:
1. Execute Milestone 1 in the active ExecPlan.
2. Keep `tracker.md`, the ExecPlan `Progress`, and the security artifact synchronized.
3. Preserve browse route behavior while removing DataFrame materialization.

**Context needed**:
- The package was motivated by `wepp1` `browse` workers retaining tens of GiB RSS during the June 16, 2026 download slowdown incident.
- Upstream Arrow/pandas issues indicate high RSS can remain after Arrow-to-pandas conversion even when Arrow allocated bytes return to zero.

**Open questions**:
- Can D-Tale handoff avoid pandas entirely, or must conversion be isolated outside `browse`?

**Files modified this session**:
- `docs/work-packages/20260616_browse_arrow_pandas_elimination/package.md`
- `docs/work-packages/20260616_browse_arrow_pandas_elimination/tracker.md`
- `docs/work-packages/20260616_browse_arrow_pandas_elimination/prompts/active/browse_arrow_pandas_elimination_execplan.md`
- `docs/work-packages/20260616_browse_arrow_pandas_elimination/artifacts/20260616_security_review.md`
- `PROJECT_TRACKER.md`

**Tests to run**:

    wctl doc-lint --path docs/work-packages/20260616_browse_arrow_pandas_elimination
    wctl doc-lint --path PROJECT_TRACKER.md
