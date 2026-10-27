# RQ compatibility repairs

**Owner**: compat_fixes implementation worker
**Date**: 2026-10-27 19:19 UTC
**Checkpoint ancestor**: `b1054fac7`

## Scope and unchanged contracts

These are conformance repairs for the released RQ 2.12.0 API. No enqueue edges,
queue names, authorization, locks, model parameters or webhook settings changed.
The unchanged application contracts are `docs/schemas/rq-response-contract.md`,
`docs/schemas/batch-task-boundary-contract.md`,
`docs/schemas/query-engine-catalog-refresh-contract.md`,
`docs/schemas/run-sync-contract.md`, and
`docs/schemas/weppcloudr-render-execution-contract.md` (existing tracking/polling).
The source remains usable by the still-running 1.16.2 baseline through cutover.

## Confirmed failures and repairs

| Shared assumption | Confirmed consumers repaired | Regression evidence |
| --- | --- | --- |
| `rq.utils.utcnow` remains importable | `job_info.py`, `job_listings.py`, wctl RQ registry snippet, run-catalog tests | Standard-library UTC clock; both runtime test selections import successfully |
| `str(JobStatus)` yields a status token | Roads active-job admission; AgFields active/recovery status and finalizer; batch active summaries; job-info completed count; Culvert manifest; DEVAL initial HTML; shared active/recent job listings | Actual `rq.job.JobStatus` values through each consumer; DEVAL renders `data-state="started">STARTED` |
| Job timestamps are naive UTC | Job-info elapsed time and wire timestamps; recent job cutoff/listing; run-sync job serialization; run-catalog safe status; Culvert creation field | Both naive and aware UTC cases preserve existing offset-free strings and correct elapsed/filter results; non-RQ run-sync database formatting unchanged |
| Raw started-registry members are job IDs | Trusted query-catalog pilot ordinary-work accounting | Real RQ `Execution.create` stores composite member, public `get_job_ids(cleanup=False)` yields plain ID, correct job hash/status/wait readback |

The expanded read-only inventory identified DEVAL's Jinja path and Culvert's
manifest as indirect enum-string consumers. A subsequent independent correctness review found the shared active/recent
listing payloads also reach Jinja. They now emit plain status values, preserving
both JSON and HTML consumers. The earlier equality-only recent-job test could
not distinguish a string enum from a plain string; new exact-type and actual
template rendering assertions cover that gap. Query catalog
public disclosure reads timestamp fields directly from Redis and remains
unchanged. This is a bounded assessed consumer set, not proof of every historical
state or every production workflow.

Timestamp handling is explicit: RQ 1.x naive values represent UTC; RQ 2.x returns
aware UTC values for the same persisted records. Preserve the old wire format
instead of introducing `+00:00` changes as an accidental dependency side effect.
Job-info and listing arithmetic normalize UTC consistently; run-sync only strips
RQ timestamp offsets and preserves its independent database date serialization.

## Validation

All commands ran through canonical wctl inside the existing application container.
The isolated candidate uses `PYTHONPATH=/workdir/wepppy/.pytest_cache/rq212-deps:/workdir/wepppy`
and leaves installed runtime 1.16.2 untouched. These results do not establish
rebuilt-runtime or model acceptance; that remains the parent package's gate.

- [Baseline 1.16.2 focused suite](compat-baseline-pytest.log): **156 passed**,
  13 warnings, 29.36s.
- [Candidate 2.12.0 identical selection](compat-candidate-pytest.log):
  **156 passed**, 13 warnings, 20.95s.
- [Real execution-registry/catalog/DEVAL selection](compat-execution-registry-pytest.log):
  **24 passed**, 4 warnings, 9.98s. Redis used only the disposable package socket,
  DB0, with baseline owner coordination. Composite execution cleanup was limited
  to the created execution; shared application Redis was never touched.
- [DEVAL rendered-chip regression and existing route tests](compat-deval-pytest.log):
  **22 passed**, 4 warnings, 8.90s. Real child Jinja template renders with a minimal
  unrelated base shell; exact job/source/destination binding remains tested.
- [Aggregate progress follow-up](compat-progress-pytest.log): **22 passed**,
  2 warnings, 10.12s. Existing aggregate cases now use real JobStatus values and
  explicitly verify completed counts for active, terminal and blocked trees.
- [Changed broad-exception enforcement](compat-broad-exceptions.log): **PASS**.
  Exactly seven existing line-based allowlist entries moved with unchanged code:
  six run-sync boundaries +3 lines, batch `BEA-20260223-P2-0165` 510 to 511.
  No broad catch or suppression ID was added. The reported -7 reflects the
  checker's use of current line positions against both source revisions.
- `git diff --check`: pass. Scoped documentation lint: pass.

The first two local iterations exposed test fixture omissions (queue name and
valid batch task identity); these were corrected before the retained passing
runs. They were test-authoring errors, not runtime regressions.

## Remaining parent gates and durable guidance

The parent owns dependency/image work, metadata hooks, lifecycle tests, full
suite, deployed-container readback, model/API acceptance and final independent
review. No standalone correctness/security approval is claimed here.

Promote these developer rules into the RQ operator/developer guide: preserve
opaque job IDs via the public registry API, convert enum status using its value
before string formatting, and keep legacy wire timestamp shape independent from
internal UTC-awareness. The main package must retain the historical-state and
rollback policy separately.

A concrete tooling painpoint: exact-line broad-exception allowlisting reports
unchanged handlers after unrelated lines move. This package only updates those
locations; a future tool change could map unchanged handlers across the diff.


## Independent review follow-up: shared listing rendering

The independent correctness reviewer identified raw enums returned by both shared
listing functions. Although JSON encoded them as ordinary strings, the RQ info
Jinja page rendered `JobStatus.FINISHED`/`JobStatus.FAILED`. Normalize both fields
at their shared producer before either consumer sees them.

The [new pre-fix regression](compat-listings-before.log) fails on the active
listing's exact plain-string assertion under 2.12. The repaired
[listing and route selection](compat-listings-after.log) passes **15 tests**,
8 warnings, 11.43s. It includes actual `info_details.htm` rendering for FINISHED
and FAILED with both naive and aware timestamps, and type checks for active
STARTED/QUEUED values. Existing route access tests pass in the same selection.
No template, authorization or queue-wiring change was required.
