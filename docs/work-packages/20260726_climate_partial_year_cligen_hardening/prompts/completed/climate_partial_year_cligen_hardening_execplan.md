# Restore partial climate years and harden CLIGEN station staging

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current.

## Purpose / Big Picture

After this change, a multiple-interpolated observed climate build can include
the current partial year and still produce the full calendar-year CLI required
by WEPP. CLIGEN-generated future values remain intact where an upstream
variable is not yet published. Daymet and GridMET multiple builds also start
their parallel CLIGEN work only after the shared station parameter file is
fully finalized on the run filesystem.

## Progress

- [x] (2026-07-27 03:20 UTC) Captured production failure evidence and ratified
  the full-year restoration behavior.
- [x] (2026-07-27 03:20 UTC) Scaffolded the work package, compatibility plan,
  tracker, ADR, and active ExecPlan.
- [x] (2026-07-27) Added tests for trailing suffix restoration, internal holes, and
  station staging order.
- [x] (2026-07-27) Implemented shared observed-variable overlay validation.
- [x] (2026-07-27) Preserved GridMET publication gaps as missing rather than zero.
- [x] (2026-07-27) Implemented atomic parent-process station staging in both multiple paths.
- [x] (2026-07-27) Ran targeted and repository validation.
- [x] (2026-07-27) Completed independent code and QA reviews and dispositioned findings.
- [x] (2026-07-27) Finalized docs, archived this plan, and closed the package.

## Surprises & Discoveries

- Observation: The `tdew` NaN is a visible symptom of a broader zero-fill
  defect; radiation and wind future slots are also currently represented as
  observed zero.
  Evidence: `_load_raw_gridmet_data` allocates the full requested date range
  with `np.zeros`, then fills only the returned NetCDF length.
- Observation: Station-copy failure is deterministic enough to affect the
  first wave of workers on slow NAS.
  Evidence: Seven of 58 production CLIGEN logs reported Fortran EOF against the
  same `id108062.par`; the finalized file later matched the packaged source.
- Observation: Review found masked-array loss, calendar compaction, and strict
  PRN validation wired to an inactive Daymet producer.
  Evidence: Each issue received a production-call-path regression before
  closure.

## Decision Log

- Decision: Permit only a trailing missing suffix for each independently
  overlaid variable.
  Rationale: Publication dates differ by variable; a shared cutoff loses valid
  observations, while arbitrary internal fill masks corrupt input.
  Date/Author: 2026-07-27, maintainer and Codex.
- Decision: Preserve CLIGEN-generated future values rather than generating a
  scientific fallback in Python.
  Rationale: WEPP requires a complete year and CLIGEN is already the canonical
  generator for `9999` observed inputs.
  Date/Author: 2026-07-27, maintainer and Codex.
- Decision: Finalize the station file in the parent before creating the worker
  pool.
  Rationale: Atomic visibility is a correctness guarantee; reducing
  concurrency only changes race probability and NAS load.
  Date/Author: 2026-07-27, Codex.

## Outcomes & Retrospective

The current-year contract now preserves a complete CLIGEN-generated year while
overlaying each supplemental variable only through its own published prefix.
Both multiple-interpolated paths finalize the shared station file before
workers start. Fifty-three focused tests and the full NoDb suite pass. The full
repository gate has one reproduced unrelated usersum baseline failure. Dual
review materially improved calendar placement, masked-data preservation,
permissions, cleanup, and active-producer coverage; all findings are closed.

## Context and Orientation

`wepppy/nodb/core/climate_gridmet_multiple_build_service.py` retrieves a full
year date index, loads shorter current-year NetCDF arrays into full-size numpy
arrays, interpolates one parquet/PRN pair per hillslope, and launches parallel
CLIGEN builders. `wepppy/nodb/core/climate_build_helpers.py` contains both the
Daymet and GridMET interpolated builders and the Daymet multiple orchestrator.
`wepppy/climates/cligen/cligen.py::Cligen.run_observed` copies the station
parameter file lazily when it is absent. Multiple processes sharing a run
directory can therefore expose an incomplete NAS copy.

CLIGEN observed PRN uses `9999` for missing precipitation or temperature and
still emits a full CLI. Post-processing must overlay only finite observed
supplemental values so generated future radiation, dewpoint, and wind survive.

## Plan of Work

First add a helper that validates a series as a finite prefix followed only by
missing values, returning the dates and values safe to overlay. Use it for each
supplemental variable in both interpolated builders. Preserve GridMET missing
slots by initializing raw arrays with NaN. Ensure PRN serialization sees these
NaNs and emits `9999`.

Add a shared station-staging helper that copies to a same-directory temporary
file, flushes and fsyncs it, atomically replaces the destination, and verifies
the finalized size. Call it synchronously in the Daymet and GridMET parent
orchestrators before creating their CLIGEN process pools. Keep
`Cligen.run_observed` defensive for other callers but remove the race from
these confirmed paths.

Test the overlay contract with generated-value sentinels, full-year length, an
all-missing suffix, and an internal hole. Test staging order by recording the
stage and executor events for both orchestrators. Update the CLIGEN/climate
developer documentation and ADR index.

## Concrete Steps

From `/home/workdir/wepppy`:

1. Run focused tests during implementation:

       wctl run-pytest tests/nodb/test_climate_build_helpers.py \
         tests/nodb/test_climate_gridmet_multiple_build_service.py --maxfail=1

2. Run NoDb validation:

       wctl run-pytest tests/nodb --maxfail=1

3. Run pre-handoff and static gates:

       wctl run-pytest tests --maxfail=1
       python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
       wctl doc-lint --path docs/work-packages/20260726_climate_partial_year_cligen_hardening \
         --path docs/adrs/ADR-0026-partial-year-observed-climate-restoration.md \
         --path docs/adrs/README.md --path PROJECT_TRACKER.md

## Validation and Acceptance

Tests must prove a 365/366-day generated CLI survives post-processing, observed
prefix values replace the corresponding CLIGEN values, and the missing suffix
does not. An internal hole must raise with the variable and date. Parent
orchestration tests must prove staging completes before any pool or future
submission for both Daymet and GridMET.

Complete independent risk-focused code review and maintainability/test-focused
QA review. Record every finding and its fix, rejection rationale, or explicitly
owned follow-up; no unresolved correctness finding may remain.

## Idempotence and Recovery

Same-directory atomic staging is safe to repeat and replaces only the run-local
station copy. Temporary files are removed on failure. No schema migration is
introduced. Tests use temporary directories and mocked CLIGEN execution.

## Artifacts and Notes

Production evidence:

    run: mdobre-undimmed-cellulite
    first job: a4b65525-3f23-4cc5-a5da-6690df28ab37
    retry job: 7e97f4f5-dec8-4fc1-83a9-86c7486e37cd
    tdew missing suffix: 2026-07-24 through 2026-12-31
    station EOF logs: 7 of 58 inspected

## Interfaces and Dependencies

Use pandas finite/missing masks, numpy NaN allocation, `tempfile` in the target
directory, `os.fsync`, and `os.replace`. Do not add dependencies. Keep helper
interfaces private to the climate build modules unless tests demonstrate a
shared public contract is needed.

Revision note (2026-07-27 03:20 UTC, Codex): Initial incident-backed plan
created after maintainer ratification of full-year CLIGEN restoration.
