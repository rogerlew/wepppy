# Real RQ inventory timeout and recovery canary

Disposition: **PASS for the bounded timeout/retry boundary**. This does not prove
that a complete production inventory fits the 3600-second job budget or establish
fleet capacity. [Aggregate evidence](20261027_inventory_rq_timeout_canary.json)
retains exact candidate/harness hashes, job identifiers, scheduler states and
artifact readback hashes.

## Scope and execution

Verified host `wepp1`; executed in `docker-rq-worker-batch-1` as UID 1002,
GID/groups 130. Candidate helper and RQ module were imported from private `/tmp`
copies into this diagnostic process only; their hashes match the workspace
candidate. No installed source, live service configuration, production queue or
real project was modified.

Private queue/namespace: `qcat-timeout-20261027T013526Z`. Scratch and retained
evidence: `/wc1/query-catalog-validation/20261026/qcat-timeout-20261027T013526Z`
(host prefix `/geodata/wc1`). The harness created 110 ordinary files and three
minimal projects, each with a marker and `values.csv`. Discovery retained the
normal 100-entry checkpoint limit. The queue override asserted the candidate's
requested timeout was 3600, then applied a **test-only 2-second first timeout**
and **60-second retry timeout**. Process-local retry backoff was shortened to
one second. Production defaults were not edited.

## Actual failure and recovery

- Normal forking `rq.Worker` launched workhorse PID 556166 under parent 556159.
  A harness iterator paused after the first 100-entry checkpoint. The actual RQ
  signal deadline raised `rq.timeouts.JobTimeoutException` at 2.000359 seconds;
  RQ recorded the job failed. Discovery had 100 entries, an unfinished frontier,
  and no completion timestamp.
- The scheduler observed failure, applied backoff without immediately queuing a
  replacement, then admitted a different job identifier after the delay. No
  manual cursor advance, frontier deletion, successful-status fabrication, or
  direct call replacing RQ worker execution was used.
- The retry replayed the directory prefix and completed: 213 cumulative entry
  reads (100 before failure plus 113 on replay), four directory visits, empty
  frontier, and exactly three stream records for three distinct expected scopes.
- Subsequent scheduler ticks admitted three scratch refresh jobs and reached
  full-cycle completion. All three generated catalogs indexed `values.csv`;
  direct readback found zero pending receipts. Total canary time: 19.9665 seconds.

## Evidence and cleanup

The protected scratch directory retains `result.json`, `timeout-entry.json`,
`first-job-exception.txt`, `run.log`, the exact candidate source copies,
`qcat_timeout_probe.py`, and `finalize.py`. The aggregate includes hashes for
candidate files, harness, exception and generated catalogs. No raw production
project inventory was collected by this test.

Cleanup readback confirmed worker death, zero queued/started private jobs,
private queue unregistration, and absence of both diagnostic parent and
workhorse processes. Only explicitly owned configuration, scratch-scope,
private queue/worker and job keys received a one-day expiry; the first failed
job's measured remaining TTL was 86345 seconds. Scratch artifacts remain for
review. Production `batch` was never an admission target.
