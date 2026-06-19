# Browse Arrow-to-Pandas Elimination

**Status**: Implementation complete locally; production observation pending (2026-06-16)
**Timezone**: UTC

## Overview
The `browse` service serves WEPPcloud run directories, file previews, compatibility downloads, and parquet quick-look/export paths. It historically also served archive ZIP downloads; exact archive ZIP delivery is now split into the dedicated download service package (`docs/work-packages/20260619_dedicated_download_service/`) when the Caddy matcher is active. A June 16, 2026 production incident showed `browse` workers retaining tens of GiB of RSS after heavy activity, and follow-up research identified Arrow-to-pandas conversion as a plausible contributor because upstream reports show pandas/PyArrow conversions can return Arrow allocated bytes to zero while process RSS remains high.

This work package eliminates Arrow-to-pandas conversion from `browse` request paths while preserving user-visible preview, download, CSV, and D-Tale behavior. The goal is a service that can inspect and export parquet artifacts without long-lived Gunicorn workers retaining large resident memory after requests complete.

## Objectives
- Remove `table.to_pandas()` and `pd.read_parquet(...)` from `wepppy/microservices/browse` request paths.
- Replace full-file DataFrame materialization with bounded DuckDB/PyArrow streaming or batch-oriented helpers.
- Preserve current browse behavior for parquet HTML preview, filtered parquet download, `?as_csv=1`, and D-Tale launch semantics.
- Add worker RSS/request-duration observability around parquet browse/export paths so recurrence is measurable.
- Add regression and operational validation that demonstrates lower worker RSS retention after representative parquet requests.

## Scope

### Included
- Browse microservice parquet preview/export/download paths in:
  - `wepppy/microservices/browse/flow.py`
  - `wepppy/microservices/browse/_download.py`
  - `wepppy/microservices/browse/browse.py`
  - `wepppy/microservices/browse/dtale.py`
- Shared parquet helpers in or near `wepppy/microservices/parquet_filters.py` when reusing the existing filter contract is appropriate.
- Tests under `tests/microservices/` for preview, download, CSV conversion, filtering, and D-Tale handoff behavior.
- Documentation updates for browse service behavior, operational signals, and incident follow-up.
- Production validation plan for `wepp1`/`forest1` that measures worker RSS before and after representative parquet requests.

### Explicitly Out of Scope
- Replacing pandas usage in unrelated NoDb, RQ, or model execution modules.
- Redesigning the public browse URL contract or changing run-scoped authorization semantics.
- Replacing D-Tale itself. If D-Tale requires pandas internally, this package must isolate that conversion outside `browse` rather than attempting to rewrite D-Tale.
- Adding new third-party dataframe engines unless a separate dependency evaluation is completed.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**:
  - `wepppy/microservices/browse/_download.py`
  - `wepppy/microservices/browse/flow.py`
  - `wepppy/microservices/browse/dtale.py`
  - `wepppy/microservices/parquet_filters.py`
  - `docs/schemas/weppcloud-browse-parquet-filter-contract.md`
- **Cutover proof required**: repository search shows no `to_pandas`, `pd.read_parquet`, or `pandas.read_parquet` use under `wepppy/microservices/browse`; tests exercise the wired browse routes rather than only helper functions.
- **Acceptance evidence type**: `both`

## Stakeholders
- **Primary**: WEPPcloud operators and users downloading or inspecting large run artifacts.
- **Reviewers**: WEPPpy maintainers for browse microservice, download routes, D-Tale bridge, and production operations.
- **Security Reviewer**: Required before deployment because this package touches public file/download route behavior and may add subprocess isolation.
- **Informed**: Production operators monitoring `wepp1`/`wepp2` browse health.

## Success Criteria
- [x] No Arrow-to-pandas or pandas parquet read call remains in `wepppy/microservices/browse`.
- [x] Existing parquet preview, filtered preview, parquet download, filtered parquet download, CSV export, and D-Tale launch tests pass with route-level coverage.
- [x] New regression tests prove CSV export can stream or batch without whole-file DataFrame materialization.
- [x] Browse README or schema docs describe the no-DataFrame parquet path and operational limitations.
- [x] Worker RSS/request-duration instrumentation records enough context to identify large parquet browse/export requests without logging secrets or private file contents.
- [x] A representative large parquet request on a production-like Gunicorn browse stack does not leave a `browse` worker above the package-defined RSS threshold after a short settling window.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: no

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites
- Existing browse parquet filter contract and route tests from [20260304_browse_parquet_quicklook_filters](../20260304_browse_parquet_quicklook_filters/package.md).
- Production incident context in [incident-2026-06-16-wepp1-browse-download-slowdown.md](../../infrastructure/incident-2026-06-16-wepp1-browse-download-slowdown.md).
- Current runtime stack includes DuckDB and PyArrow in the production image.

### Blocks
- Durable retirement of ad hoc `browse` restarts as the primary mitigation for high-RSS browse workers.
- Any future large-artifact browse/export features that would otherwise add more DataFrame materialization to request workers.

## Related Packages
- **Related**: [20260304_browse_parquet_quicklook_filters](../20260304_browse_parquet_quicklook_filters/package.md)
- **Related**: [20260224_correlation_id_structured_logging](../20260224_correlation_id_structured_logging/package.md)
- **Related**: [20260619_dedicated_download_service](../20260619_dedicated_download_service/package.md) for exact archive ZIP isolation from the browse worker pool.
- **Follow-up**: A separate package may be needed for D-Tale replacement or isolation if D-Tale itself remains a pandas-only endpoint.

## Timeline Estimate
- **Expected duration**: 1-2 weeks.
- **Complexity**: Medium-High.
- **Risk level**: High because the work touches public file/download routes and performance-sensitive production behavior.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: This package changes public browse/download route internals, parquet filter/export handling, file path processing, and possibly subprocess isolation around user-selected run artifacts.
- **Security review artifact**: `docs/work-packages/20260616_browse_arrow_pandas_elimination/artifacts/20260616_security_review.md`

Use `docs/prompt_templates/security_review_template.md` for the security artifact format and by-surface checks.

## Hardening and Callus Softening

- **Failure signature(s)**:
  - `browse` workers retained about 45-49 GiB RSS before targeted restart on June 16, 2026.
  - `browse` logged repeated `WORKER TIMEOUT` events before mitigation.
  - Workers can transiently grow during parquet/download probes, then may or may not release RSS.
- **Related prior hardening efforts**:
  - [incident-2026-06-16-wepp1-browse-download-slowdown.md](../../infrastructure/incident-2026-06-16-wepp1-browse-download-slowdown.md)
  - [20260304_browse_parquet_quicklook_filters](../20260304_browse_parquet_quicklook_filters/package.md)
- **Health signals**:
  - Worker RSS returns near baseline after parquet preview/export requests.
  - No `WORKER TIMEOUT` events during representative browse parquet workloads.
  - Browse parquet/export route probes remain fast through Caddy and direct `browse`; exact archive ZIP probes remain fast through the dedicated `download` route after cutover.
- **Danger signals**:
  - New streaming code weakens path validation or auth behavior.
  - CSV export behavior changes silently for existing users.
  - Process isolation adds unbounded subprocesses or orphaned temporary files.
- **Observation window**: 14 days after production rollout.
- **Temporary calluses introduced**: None planned. If an RSS watchdog or subprocess cap is added, record owner and sunset criteria in `tracker.md`.
- **Callus softening hypothesis (if applicable)**: If RSS retention remains low for the observation window, reduce reliance on manual targeted `browse` restarts for this incident class.

## References
- `wepppy/microservices/browse/_download.py` - download and parquet-to-CSV handling.
- `wepppy/microservices/browse/flow.py` - directory render flow and parquet preview logic.
- `wepppy/microservices/browse/dtale.py` - browse-to-D-Tale handoff.
- `wepppy/microservices/parquet_filters.py` - shared parquet filter contract and execution helpers.
- `tests/microservices/test_download.py` - download route regression coverage.
- `tests/microservices/test_browse_routes.py` - browse route regression coverage.
- `tests/microservices/test_browse_dtale.py` - D-Tale handoff regression coverage.
- `docs/schemas/weppcloud-browse-parquet-filter-contract.md` - existing parquet filter contract.
- `docs/infrastructure/incident-2026-06-16-wepp1-browse-download-slowdown.md` - incident that motivated this hardening package.
- Apache Arrow memory pool documentation - explains best-effort `release_unused()` semantics.
- pandas PyArrow documentation - distinguishes PyArrow read engine from PyArrow-backed dtype behavior.
- Apache Arrow GitHub issues `#44472`, `#45504`, and `#45882` - upstream reports of high RSS after PyArrow/pandas conversion.

## Deliverables
- Active ExecPlan at `prompts/active/browse_arrow_pandas_elimination_execplan.md`.
- Code changes eliminating Arrow-to-pandas conversion from `wepppy/microservices/browse`.
- Updated browse parquet tests and any new helper tests.
- Updated browse documentation and incident follow-up notes.
- Completed security review artifact.
- Production-like local Gunicorn validation evidence showing worker RSS behavior before/after representative parquet requests.

## Follow-up Work
- Evaluate whether D-Tale should be replaced or moved behind a separate disposable service for large parquet artifacts.
- Consider an operator dashboard or alert for `browse` worker RSS thresholds after this package lands.
- Consider broader pandas/PyArrow RSS hardening outside `browse` in a separate package.
