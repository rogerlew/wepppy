# Independent inventory timeout/retry review

Date: 2026-10-27 UTC. **PASS for the bounded real-RQ recovery boundary.**
No new security/correctness finding. Fleet capacity and complete legacy execution
under the production attempt budget remain separate acceptance questions.

## Evidence reviewed

Read the [canary report](20261027_inventory_rq_timeout_canary.md),
[structured result](20261027_inventory_rq_timeout_canary.json), exact local
`/tmp/qcat_timeout_probe.py` and `/tmp/qcat_timeout_finalize.py`, and raw log.
Compared their control flow with the current inventory and RQ modules. Candidate
hashes match the independently reviewed implementation:

- Inventory: `d39f056e243b7889b0dd50c2030c518b822f3d54e4263fb6f16a4b5e8cc86791`.
- RQ module: `839bafc4efa1b1f4161b3d7fec1b7f0a4c0c7e0b3652727f70bd6363404c0cac`.
- Probe: `f7f7eb08e8a31a7cd97a26446276ec4bc9452684fe75c62bf62e36340c03f6ac`.
- Finalizer: `317e3e4439d4137bf297e1f8fe06f5dc35d0ef1f784d6098169f246185bcf120`.
- Raw log: `6d00edcf9dc8e0e8e14daeb0d74eec31c7ef442e833e26587c3cd29e9f17ed12`.

The protected scratch path named in the canary report retains exact inputs,
exception, log and results. This review reads retained evidence; it did not
rerun production work or independently reconnect to the live Redis database.

## Verified boundaries

- **Real failure:** the harness subclasses normal forking `rq.Worker`, retaining
  RQ job execution and timeout handling. Workhorse PID 556166 differs from parent
  556159. The retained traceback shows `JobTimeoutException` from RQ's signal
  deadline while the injected iterator sleeps. The first job failed after
  2.000359 seconds; state retained 100 entry observations, a nonempty frontier and
  no completion timestamp. This is not a directly raised synthetic job error.
- **Recovery ownership:** the ordinary scheduler observes the failed job, records
  backoff, queues no immediate replacement, then creates a different job after
  the delay. The harness does not move the cursor, clear the frontier or mark a
  job successful. Removing the injected pause lets the retry replay the prefix.
  It records 213 cumulative observations, four visited directories, an empty
  frontier and exactly the three expected unique scope records.
- **Artifact convergence:** subsequent real worker execution and scheduler ticks
  complete the scratch cycle. All three catalogs contain `values.csv`, and direct
  pending-request readback returns zero. RQ completion is not the sole assertion.
- **Isolation:** uid 1002/gid 130 is asserted. Only a unique scratch root and its
  coordination directory are configured. Candidate imports, compatible-worker
  registration and queue selection are process-local. The queue override asserts
  the requested production timeout is 3600 before substituting test values of
  2/60 seconds; retry backoff is shortened only in this process. Production
  `batch` is never passed to admission or consumption.
- **Cleanup scope:** the harness expires keys only for its unique configuration,
  scratch scope identities, generated jobs, private queue and worker. The
  finalizer verifies an empty private queue before unregistering it, checks the
  diagnostic parent/workhorse are absent, and retains the first failure evidence
  with positive TTL. Recorded cleanup has zero queued/started jobs and a dead
  worker. No global flush, production queue deletion or guard removal occurs.

## Limits

The controlled pause begins after 100 ordinary entry observations; this case
does not by itself establish every child-frontier or scope-emission race.
Those remain covered by the separate implementation regressions and full
discovery/restart evidence. The retry runs after the injected obstruction is
removed, with a 60-second test deadline. It proves the timeout/backoff/retry
mechanism, not that repeated 3600-second attempts always finish an arbitrarily
slow directory or that the fleet meets its reconciliation target.

The separate [full inventory](20261027_full_inventory.md) now establishes 30,891
discovered scopes with complete streams and empty frontiers. Its deliberately
fenced legacy helper is correctly described separately from this RQ timeout
canary. Neither artifact alone proves a complete fleet refresh or shared-queue
capacity. No runtime or production action was performed by this reviewer.
