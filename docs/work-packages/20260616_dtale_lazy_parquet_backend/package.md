# D-Tale Lazy Parquet Backend

**Status**: Implementation complete locally; production observation pending (2026-06-16)
**Timezone**: UTC

## Overview
The embedded D-Tale service currently loads Parquet artifacts into full pandas DataFrames before opening the viewer. That defeats the June 16 browse memory mitigation for users who launch D-Tale on large run outputs because the separate long-lived D-Tale worker can still retain high RSS after Arrow-to-pandas conversion.

This work package patches the D-Tale integration in a narrow, upstream-aligned way: keep D-Tale as the UI, but make large Parquet datasets use a lazy, page-oriented backend modeled on D-Tale's existing ArcticDB mode. The goal is to avoid full-table Arrow-to-pandas conversion while minimizing the maintenance burden of staying in sync with upstream D-Tale.

## Objectives
- Avoid `pd.read_parquet(...)` and full Arrow `to_pandas()` conversion when `/internal/load` opens supported Parquet files in D-Tale.
- Reuse D-Tale's existing lazy-backend shape so the local patch is small and easy to audit when upgrading upstream D-Tale.
- Serve D-Tale grid pages for Parquet artifacts through bounded DuckDB/PyArrow reads that return only the visible rows and columns as small pandas slices.
- Preserve the current browse-to-D-Tale route contract and existing path/auth validation.
- Document unsupported D-Tale actions for lazy Parquet datasets and keep failures explicit.
- Add tests that prove the wired D-Tale loader no longer materializes a full Parquet DataFrame for the default Parquet path.

## Scope

### Included
- D-Tale service loader and dataset registration in `wepppy/webservices/dtale/dtale.py`.
- A local lazy Parquet backend, likely in `wepppy/webservices/dtale/`, that uses dependencies already present in the runtime image.
- A narrow monkey patch or adapter around D-Tale route behavior when a dataset is marked as lazy Parquet.
- Regression tests under `tests/microservices/` for lazy Parquet registration and paged row loading.
- Work-package, tracker, and D-Tale service documentation updates.

### Explicitly Out of Scope
- Replacing the D-Tale frontend.
- Making every D-Tale analysis/chart/transformation endpoint Arrow-native.
- Adding ArcticDB as a WEPPcloud runtime dependency.
- Changing public browse URL shapes or run-scoped authorization behavior.
- Removing pandas from non-Parquet D-Tale loads.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**:
  - `wepppy/webservices/dtale/dtale.py`
  - `wepppy/microservices/browse/dtale.py`
  - D-Tale 3.20.0 installed source in the service image for `dtale.views.get_data`, `dtale.views.startup`, and `dtale.global_state.DtaleArcticDBInstance`
- **Cutover proof required**: `/internal/load` for unfiltered Parquet registers a lazy backend without calling the eager `_load_dataframe` path, and a D-Tale page-data request returns expected rows from a DuckDB/PyArrow bounded read.
- **Acceptance evidence type**: `both`

## Stakeholders
- **Primary**: WEPPcloud operators and analysts opening large Parquet run artifacts in D-Tale.
- **Reviewers**: WEPPpy maintainers for browse, D-Tale integration, and production operations.
- **Security Reviewer**: Recommended if the work expands to new public routes or subprocesses.
- **Informed**: Production operators monitoring `wepp1`/`wepp2` memory and D-Tale service health.

## Success Criteria
- [x] Parquet `/internal/load` no longer calls `pd.read_parquet(...)` or full-table Arrow `to_pandas()` for the default unfiltered path.
- [x] Lazy Parquet datasets can open `dtale/main/<id>` and serve grid rows through D-Tale's `/data/<id>` route.
- [x] Tests cover the lazy registration path and at least one paged data load from a Parquet fixture.
- [x] Unsupported full-DataFrame actions for lazy Parquet data are documented or explicitly guarded.
- [x] D-Tale service docs explain the lazy Parquet backend, upstream D-Tale sync seam, and validation gates.
- [x] Work-package tracker and active ExecPlan are updated with final validation evidence.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: no

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites
- The browse service no-DataFrame mitigation in [20260616_browse_arrow_pandas_elimination](../20260616_browse_arrow_pandas_elimination/package.md).
- Existing runtime dependencies in `docker/requirements-uv.txt`, especially D-Tale, DuckDB, PyArrow, and pandas.

### Blocks
- Durable resolution of D-Tale memory retention for large Parquet artifacts.
- Any future decision to remove D-Tale or replace it with a purpose-built Arrow explorer.

## Related Packages
- **Depends on**: [20260616_browse_arrow_pandas_elimination](../20260616_browse_arrow_pandas_elimination/package.md)
- **Related**: [20260304_browse_parquet_quicklook_filters](../20260304_browse_parquet_quicklook_filters/package.md)
- **Follow-up**: If route patching proves too broad, create a replacement Arrow explorer package rather than expanding this package into a D-Tale fork.

## Timeline Estimate
- **Expected duration**: 1-3 focused sessions for first wired lazy-grid implementation.
- **Complexity**: High.
- **Risk level**: Medium-High because the patch sits on upstream D-Tale internals, but it is behind the D-Tale service boundary.

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: The work preserves existing internal token verification and run path resolution. It changes how already-authorized Parquet files are read inside the D-Tale service, but does not add a new public route or weaken auth/path validation.
- **Security review artifact**: N/A

Use `docs/prompt_templates/security_review_template.md` if this package later adds new public routes, subprocesses, or external egress.

## Hardening and Callus Softening

- **Failure signature(s)**:
  - D-Tale Parquet load currently materializes full pandas DataFrames through `pd.read_parquet(...)` or full Arrow `to_pandas()`.
  - Large D-Tale Parquet launches can leave the long-lived D-Tale worker with retained high RSS.
- **Related prior hardening efforts**:
  - [20260616_browse_arrow_pandas_elimination](../20260616_browse_arrow_pandas_elimination/package.md)
  - [incident-2026-06-16-wepp1-browse-download-slowdown.md](../../infrastructure/incident-2026-06-16-wepp1-browse-download-slowdown.md)
- **Health signals**:
  - D-Tale Parquet launch completes without eager full-table DataFrame load.
  - D-Tale grid page requests read bounded row/column windows.
  - D-Tale worker RSS remains materially below the June 16 browse failure signature during representative Parquet opens.
- **Danger signals**:
  - Local D-Tale patches spread across many upstream routes.
  - Unsupported D-Tale actions silently load the whole file.
  - D-Tale upgrades require manual diffing of large local forks.
- **Observation window**: 14 days after production rollout.
- **Temporary calluses introduced**: None planned.
- **Callus softening hypothesis (if applicable)**: If lazy D-Tale Parquet mode proves stable through the observation window, remove any operator guidance that treats D-Tale Parquet launches as a known high-RSS risk.

## References
- `wepppy/webservices/dtale/dtale.py` - embedded D-Tale loader and current eager pandas readers.
- `wepppy/webservices/dtale/AGENTS.md` - service notes and monkey-patch convention.
- `wepppy/microservices/browse/dtale.py` - browse-to-D-Tale handoff contract.
- `tests/microservices/test_browse_dtale.py` - existing D-Tale loader regression tests.
- `docker/requirements-uv.txt` - pinned D-Tale, DuckDB, PyArrow, and pandas versions.
- D-Tale upstream ArcticDB integration docs - reference design for lazy paging with reduced functionality.

## Deliverables
- Active ExecPlan at `prompts/active/dtale_lazy_parquet_backend_execplan.md`.
- Code changes implementing a lazy Parquet D-Tale backend in `wepppy/webservices/dtale/dtale.py`.
- Focused regression tests for lazy Parquet registration, paged reads, sorted reads, filtered dataset IDs, and explicit export rejection in `tests/microservices/test_browse_dtale.py`.
- Updated D-Tale service docs in `wepppy/webservices/dtale/AGENTS.md`.
- Validation notes in `tracker.md` and the active ExecPlan.
- Stub and broad microservice validation evidence: `wctl run-stubtest wepppy.webservices.dtale`, `wctl check-test-stubs`, and `wctl run-pytest tests/microservices --maxfail=1`.

## Follow-up Work
- Evaluate whether D-Tale chart/export routes for lazy Parquet should receive bounded DuckDB-backed adapters or be hidden in the UI.
- Consider an independent Arrow explorer if future D-Tale internals make the lazy patch too expensive to maintain.

## Closure Notes

**Closed**: Not closed; implementation is complete locally and production observation remains.

**Summary**: The D-Tale service now handles Parquet, GeoParquet, and PQ files through lazy DuckDB/PyArrow page reads. The eager Parquet reader was removed from `_load_dataframe`, and `/dtale/data/<id>` is intercepted only for registered lazy Parquet datasets. Filtered D-Tale launches remain lazy by using the existing parquet filter compiler's DuckDB SQL fragment.

**Lessons Learned**: Upstream D-Tale's ArcticDB mode is the right compatibility model. The `data_loader` hook is not suitable for lazy loading in D-Tale 3.20.0 because it is called immediately. D-Tale also requires unique display names, so filtered datasets include a short filter hash in their display label.

**Archive Status**: Package docs remain active for the production observation window.
