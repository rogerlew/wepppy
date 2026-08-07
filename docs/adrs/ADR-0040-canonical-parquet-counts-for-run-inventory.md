# ADR-0040: Canonical Parquet Counts for Run Inventory

**Status**: Accepted
**Date**: 2026-08-07
**Review Date**: 14 calendar days after production activation
**Review Owner**: Roger Lew / WEPPcloud operator

## Context

Production job `7aa39c98-de7c-4298-8d5f-35e3784775e4` spent its entire
36,000-second limit compiling dot logs and was terminated while enumerating
`wepp/runs/*.slp` for one project. The maintenance compiler repeats that
unbounded directory scan for every active run and also enumerates legacy ash
CSV files.

## Decision

For current active-project inventory, derive `hillslopes` from the Parquet
footer row count of `watershed/hillslopes.parquet`. Derive `ash_hillslopes`
from the footer row count of `ash/post/hillslope_annuals.parquet`, which exists
after successful ash post-processing. A missing canonical artifact contributes
zero. A present but unreadable artifact is logged for that run and contributes
zero so one damaged project does not prevent the global maintenance outputs.
Centroid loading and project counting are independent of artifact counts.

All four generated outputs are staged before publication. Publication aborts
and retains the complete last-known-good set when discovery returns zero logs
and any prior output exists; when logs exist but no watershed Parquet can be
read; or when at least 10 watershed or ash Parquet reads fail and failures for
that artifact affect at least 25 percent of discovered runs. A genuinely new
empty destination with no prior output may publish an initial empty set.

Do not scan `.slp`, `*ash.csv`, or raw per-hillslope ash files as a fallback.
The existing output field names and shapes remain unchanged, but the source and
meaning of their values intentionally change.

## Decision Provenance

- **Decision venue**: WEPPcloud operator/Codex production incident conversation,
  approval at 2026-08-07 13:52 UTC.
- **Participants present**: WEPPcloud operator and Codex.
- **Decision owner**: WEPPcloud operator.
- **Planned implementer**: Codex.
- **Change summary**: unbounded legacy file counts become bounded canonical
  Parquet footer counts, with no legacy parity fallback.

## Rationale

A Parquet footer provides the row count with one file open and no directory
enumeration. The watershed table has one row per hillslope. The ash annuals
table has one row per successfully postprocessed ash hillslope. These artifacts
therefore provide useful current-inventory counts while avoiding the NAS
metadata workload that caused the ten-hour timeout.

## Alternatives Considered

- Keep or optimize the `.slp` and ash CSV globs: rejected because their cost
  remains proportional to directory size and the operator explicitly rejected
  legacy parity.
- Count raw `ash/H*_ash.parquet` files: rejected because it repeats the same
  directory-enumeration defect.
- Wait for the PostgreSQL execution ledger: rejected as the immediate compiler
  must be made operational; the ledger remains the durable historical design.
- Treat corrupt canonical Parquet as fatal: rejected because this global
  maintenance job must preserve usable output for other independent runs.

## Consequences

The values describe rows in canonical current-run artifacts, not historical
execution totals. Missing or corrupt canonical artifacts can reduce a run's
reported count to zero. Historical and repeated-run accounting remains owned by
the PostgreSQL statistics-ledger milestones.

## Evidence

- Host: `wepp1`.
- Job: `7aa39c98-de7c-4298-8d5f-35e3784775e4`.
- Runtime: 2026-08-07 02:10:26.302297 through 12:10:26.416636 UTC.
- Failure: `JobTimeoutException` at 36,000 seconds while executing
  `len(glob(run_dir / "wepp" / "runs" / "*.slp"))`.
- Work package: `docs/work-packages/20260505_run_statistics_ledger/`.

## Risk and Rollback Notes

Monitor total compiler duration, per-run warning counts, and output run counts
for 14 days. On danger signals, fence scheduled submissions and preserve or
restore the last-known-good generated outputs while correcting the canonical
read path. Reverting code is permitted only while the known-bad maintenance
job remains disabled; rollback must not reactivate the unbounded legacy glob.
