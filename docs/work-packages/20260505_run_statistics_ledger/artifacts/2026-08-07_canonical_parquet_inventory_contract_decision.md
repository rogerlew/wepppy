# Canonical Parquet Inventory Contract Decision

**Status**: Accepted; implementation pending
**Prepared**: 2026-08-07 13:53 UTC
**Starting implementation revision**: `162b4f3f9`
**Classification**: Operator-authorized bounded enhancement, SURF-19A / GOV-00A-M1H
**Security impact**: High

## Operator Direction

After production job `7aa39c98-de7c-4298-8d5f-35e3784775e4` timed out at ten
hours, the WEPPcloud operator directed Codex to remove per-run globbing from
`compile_dot_logs_rq`, use `watershed/hillslopes.parquet` for hillslopes, find
an efficient ash source, and explicitly stated that parity with the old routine
was not required.

At 2026-08-07 13:52 UTC Roger Lew stated, "roger approves," in response to the
exact proposed matrix: the two named canonical artifacts; no legacy fallback;
isolated missing/corrupt artifacts warning and counting as zero; centroid
decoupling; systemic-failure last-known-good publication containment; stable
keys with intentionally changed current-artifact semantics; and registration
as a bounded incident enhancement separate from the future PostgreSQL ledger.

## Normative Delta

`compile_dot_logs` obtains current-run `hillslopes` from the footer row count of
`watershed/hillslopes.parquet` and `ash_hillslopes` from the footer row count of
`ash/post/hillslope_annuals.parquet`. It performs no per-run `.slp`, ash CSV, or
raw ash-output enumeration. Missing canonical files count as zero. Unreadable
canonical files produce a run-scoped warning and count as zero.

Systemic failure is bounded explicitly: zero discovered logs cannot replace
any prior output; if logs exist, at least one watershed Parquet must be
readable; and 10 or more failed reads affecting at least 25 percent of runs for
either canonical artifact abort publication. A new empty fixture destination
with no prior output may publish an initial empty set. On abort, all generated
outputs retain their last-known-good versions.

The CSV and JSON field names and shapes do not change. Count semantics do:
these fields describe current canonical artifact rows and are not historical
execution totals. The PostgreSQL ledger remains the future canonical source for
historical and repeated execution totals.

## Applicable Contracts and Classification

- SURF-19A/GOV-00A-M1H registration owns this newly registered finite public
  statistics and landing-map output bridge without advancing existing surface
  owners or the broader ledger package.
- `docs/work-packages/20260505_run_statistics_ledger/spec.md` owns the bounded
  bridge matrix and is amended by this checkpoint.
- `docs/schemas/rq-response-contract.md` remains applicable and unchanged;
  the job result/error shape does not change.
- This is an intended output-parameterization change and incident hardening,
  not a conformance fix.

## Compatibility, Data, and Security Impact

Output columns and JSON keys are preserved. Existing values may change because
legacy file inventories are deliberately superseded. No project artifact schema
is modified: the compiler only reads already-canonical Parquet artifacts. No
authentication, authorization, PII, external egress, or queue topology changes.
The governance triage is `high` because these files feed public routes and the
landing map. Dedicated operations/security review is required.

## Exact Output Semantics

- `access.csv`: each access row carries current watershed and ash-post Parquet
  row counts; access identity and timestamps are unchanged.
- `runid-locations.json`: inclusion depends on a valid centroid and active TTL
  state, not a positive hillslope count; count fields use current artifact rows.
- `run_counts.csv`: count columns use current canonical-artifact rows.
- `runs_counter.json`: project keys retain existing date/config eligibility but
  no longer depend on count or centroid presence; hillslope keys sum current
  canonical-artifact rows and are not historical execution totals.
- `/access-by-year` and `/access-by-month` retain access-time semantics;
  `/stats` and `/stats/<key>` expose bridge meanings until ledger migration.

## Regression Evidence

Focused tests will create canonical Parquet fixtures, verify footer-derived
counts, prove legacy `.slp` and ash CSV files are ignored, verify missing and
unreadable artifacts produce zero without aborting the full compile, and retain
existing access-log, location, and TTL behavior tests. Production validation
will compare runtime and warning totals before republishing maintenance output.

## Production Evidence and Rationale

The job ran from 2026-08-07 02:10:26.302297 through 12:10:26.416636 UTC and was
killed at 36,000 seconds inside the per-run `.slp` glob. Parquet footers provide
row counts with one direct file open. `ash/post/hillslope_annuals.parquet` is
written after successful ash post-processing and has one grouped row per
`topaz_id`, making it the bounded successful-output inventory requested by the
operator. Raw ash file counting was rejected because it would retain the NAS
directory-enumeration failure mode.
