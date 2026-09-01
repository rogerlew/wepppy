# Harden GridMET single-location and gridded downloads

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

## Purpose / Big Picture

GridMET climate builds must either receive the requested scientific data or
fail before publishing an artifact. After this work, transient upstream errors
receive bounded retries, malformed JSON and HTML/truncated NetCDF responses are
rejected explicitly, and a prior valid grid cannot be replaced by failed bytes.
The behavior is visible through focused tests that construct each response
state and through a Forest1 valid-response integration check.

## Progress

- [x] (2026-08-31) Captured the production failure and scaffolded this package.
- [x] (2026-08-31) Ratified retry, timeout, publication, and concurrency values
  in ADR-0028.
- [x] (2026-08-31) Implemented shared failure semantics without changing
  public client APIs.
- [x] (2026-08-31) Added focused valid/transient/malformed/date-completeness/
  atomic-publication tests; final focused gate is 37 passed.
- [x] (2026-08-31) Correctness, QA, and security gates passed with no open
  Critical, High, or Medium findings; broad-exception and docs gates passed.
- [x] (2026-08-31) Forest1 directly fetched and structurally validated a
  current-year classic NetCDF3 prefix (HTTP 200, 241 × 4 × 4, 13,004 bytes).
- [x] (2026-08-31) Full repository gate passed: 7,306 passed, 63 skipped;
  package closed.

## Surprises & Discoveries

- The gridded path already requests spatial bounding-box grids. Its defect is
  unvalidated fragmented acquisition, not point-to-grid reconstruction.
- Production created 36 small HTML files with final `.nc` names because
  `retrieve_nc` copied `response.raw` without checking status or format.
- The single-location client retries broad exceptions but has no timeout,
  schema validation, narrow error contract, or response-body redaction.
- `netCDF4` alone accepts some valid-header, tail-truncated NetCDF3 files and
  supplies zeros for missing records. The stricter SciPy NetCDF3 parser rejects
  that corruption without materializing the arrays.
- Syntactically valid point JSON can still be scientifically incomplete; exact
  contiguous requested-date coverage is therefore part of payload validity.

## Decision Log

- Decision: retain annual NCSS grids and aggregated single-location JSON for
  this repair. Rationale: changing source topology or caching would broaden an
  urgent correctness fix without parity/performance evidence.
- Decision: validate a staged NetCDF for the requested variable and coordinate
  axes before atomic replacement. Rationale: content type and filename are not
  trustworthy scientific-data checks.
- Decision: retry only transient transport/status/payload failures and fail
  permanent client errors immediately. Rationale: retries must not conceal bad
  requests or amplify upstream load.
- Decision: bound JSON at 32 MiB and annual grids at 512 MiB, then enforce
  calendar and bounding-box dimensions. Rationale: a read timeout does not bound
  a continuously streaming response or later decompression/allocation.
- Decision: treat classic NetCDF3 as the NCSS wire contract and validate its
  complete record layout before `netCDF4` semantic checks. Rationale: semantic
  first-cell reads do not detect missing tail records.
- Decision: require the exact requested point-date axis. Rationale: partial or
  hybrid climate series are a silent scientific correctness failure.

## Outcomes & Retrospective

Implementation and all validation evidence are complete. Two independent High
findings materially improved the boundary: structural NetCDF3 completeness and
exact point-date coverage. The resulting design preserves existing APIs and
scientific transforms while preventing malformed final artifacts. The full
repository suite passed 7,306 tests with 63 expected skips.

## Context and Orientation

`wepppy/climates/gridmet/gridmet_singlelocation_client.py` calls an aggregated
service returning JSON arrays for one coordinate. `wepppy/climates/gridmet/client.py`
calls THREDDS NCSS for one variable, year, and watershed bounding box, producing
a NetCDF grid. `wepppy/nodb/core/climate_gridmet_multiple_build_service.py`
fans those grid calls across variables and years. The caller expects the final
path `<cli_dir>/<GridMetVariable>_<year>.nc` to be complete when `retrieve_nc`
returns.

## Plan of Work

First add hermetic response fixtures that reproduce HTTP 502/503 HTML, invalid
JSON, malformed JSON shape, truncated NetCDF, missing variables, success after
retry, and exhausted retry while a good destination exists. Tests must use no
network and must inspect final and temporary files.

Then introduce one small GridMET acquisition support module for timeout,
transient-status classification, bounded backoff, response redaction, and
typed acquisition errors. Refactor the three single-location entry points to
use it and validate required arrays and consistent lengths. Refactor
`retrieve_nc` to download each attempt to a unique same-directory file, flush
and fsync it, validate it with `netCDF4`, and atomically publish it. Cleanup is
a deliberate boundary and may catch `OSError` narrowly.

Finally apply the ADR-approved gridded concurrency ceiling, run focused and
full tests, run correctness/QA/security reviews, execute one Forest1
valid-response integration gate on disposable output, and update the package
records. Do not mutate production run data during this package.

## Concrete Steps

From `/home/workdir/wepppy` run:

    wctl run-pytest tests/climates/gridmet tests/nodb/test_climate_gridmet_multiple_build_service.py -vv
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260831_gridmet_download_hardening

The Forest1 gate must use a disposable directory, fetch one small recent grid
subset, open the resulting NetCDF, assert the requested variable and
coordinates, and remove the disposable artifact. It must not touch a run.

## Validation and Acceptance

A 502 followed by a valid response succeeds after one recorded delay. A 400
fails after one request. HTML or truncated bytes returned with HTTP 200 retry
and never appear at the final path. Exhaustion leaves a prior valid destination
byte-for-byte intact and leaves no staging file. Valid JSON produces the same
columns, units, conversions, and dates as before. Invalid JSON shape fails with
a GridMET acquisition error rather than a raw `KeyError` or response body.

## Idempotence and Recovery

Every failed attempt removes only its uniquely created staging file. Atomic
replacement makes reruns safe and prevents readers from observing partial
content. Recovery of the production run is separate: deploy the validated fix,
then rerun its climate build so every annual file is reacquired under the new
contract.

## Interfaces and Dependencies

Do not add dependencies. Continue using `requests`, `netCDF4`, pandas, NumPy,
and the existing public retrieval functions. Preserve their arguments and
successful return types. New exceptions may subclass `RuntimeError` so callers
continue to fail normally while receiving an actionable bounded message.

Revision note (2026-08-31): initial incident-driven execution plan.
