# Independent scheduler tick canary review

Date: 2026-10-27 UTC. **PASS for the measured 25-candidate boundaries.**
No new security/correctness finding. This does not close fleet capacity.

Reviewed the [report](20261027_inventory_scheduler_tick_canary.md),
[aggregate](20261027_inventory_scheduler_tick_canary.json), both exact local
probe scripts, finalizer and retained raw logs. No production action or rerun
was performed by this reviewer.

## Findings and evidence

- Timers surround the actual candidate `reconcile_query_catalogs` call; worker
  execution and 30-second scheduler spacing are excluded. The harness does not
  edit cursors or fabricate job success. Normal forking workers execute inventory
  in both waves and all 25 refresh jobs in the first wave. Admission/drain limits
  remain 25/100; every recorded job retains timeout 3600.
- First-wave admission takes 11.668846 seconds, completion retirement 0.623231
  seconds, and the completed no-op 0.002755 seconds. All 26 jobs finish. Direct
  readback verifies 25 `values.csv` catalog entries, actual source size/mtime and
  fixture values, and zero pending receipts. The separate 132.111483-second
  worker phase is not counted as scheduler overhead or representative service.
- Second-wave admission takes 6.716834 seconds; the queued recheck takes 0.790840
  seconds while queue count stays 25. This supports the warning that returned
  `admitted=25` can mean coalesced existing jobs. After normal cancellation of the
  private queued jobs and owned READONLY markers, 25 exclusions take 0.135262
  seconds. All 25 receipts remain and no catalogs exist: cycle completion here
  means READONLY exclusion, not successful refresh or acknowledgment.
- Identity assertions retain uid 1002/gid 130. Unique scratch roots, namespaces,
  private queues, compatible diagnostic worker registrations and module overlays
  confine admission/execution. Production `batch` is not consumed. Cleanup is
  scoped to owned configuration/scope/job/queue/worker keys; both queues are empty
  and unregistered, both workers have death records, and finalizer readback finds
  both parent PIDs absent. No global flush or guard removal occurs. Scratch and
  retained receipts remain available.

## Provenance and limits

Candidate helper/RQ hashes match the earlier independent implementation review
and the full hashes in the aggregate. Independently recomputed harness hashes:

- Admission: `98149404ef454b6cb70d154e54f9833956649fc2ac395f9922668a2aca64c50b`.
- Recheck: `9694eb5c887bdeee5f2cd0c536099c9641c3d6ce6b5a2ee7abb040c08a3bfb93`.
- Finalizer: `66288f2ff1a38bb82cd813f8de871a812d6a8c0b592ce966a52347c805ae4763`.

Raw-log hashes independently match the aggregate. Cleanup evidence was read
from retained artifacts; this reviewer did not reconnect to live Redis.

The measured operations fit within 30 seconds for these tiny scratch cohorts.
That supports the plausibility of the nominal cadence; two admission observations
are not a latency distribution or a worst-case bound. The actual pending JSON is
only 3,375 bytes for 25 items, not a full-population backlog. Production scheduler
interference, current-scale cursor processing, cold metadata/lock delays, and
representative whole-job service remain unmeasured by this canary. The minimum
49,405-consideration / approximately 16.47-hour scheduler arithmetic is unchanged.
These measurements narrow uncertainty without certifying a 24-hour fleet cycle.
