# Production scratch lock handoff acceptance

Date: 2026-10-26, **23:51:10–23:55:03 UTC**. Reviewer/operator: `/root/science_review`.
Authority: task-specific scratch gate authorization and the
`wepp1-operator` skill.

**PASS: measured guard exclusion, successful bounded handoff/publication and Python
thread heartbeat. HTTP request/readiness acceptance remains conditional.** These
results do not authorize deployment, certify a maximum production wait, or prove
HTTP responsiveness under contention. No kernel/mount/configuration tuning is
justified by this evidence alone.

## Scope and retained evidence

Used only the existing `/wc1/query-catalog-validation/20261026/async-preflight-1719`
scratch namespace and its existing external guard. Ran fresh Python processes in
`docker-rq-worker-batch-1` on wepp1/wepp2 and
`docker-rq-worker-fork-archive-1` on wepp3, asserting uid 1002/gid 130. All processes
report supplementary group 130, guard mode 0640 and the deployed publication source
SHA256 `1f19401a875246e621fdeea398cf4f42d6fb288eef591ad5d611c19b6fd3dcd5`.
No service restart, deployment, real-project write, queue submission, permission
change, mount change, or guard unlink/replacement occurred. Root mapping and
refresh-disabled settings were confined to the canary interpreters.

Retained scripts are `rollout-lock-acceptance-{probe,driver}.py` and
`rollout-lock-receipt-{probe,driver}.py`. Raw per-process stdout, stderr and results
are in the corresponding `*-logs/` directories. Summary:
`rollout-lock-acceptance-summary.json`; host kernels/mounts, script hashes and live
HTTP service commands: `rollout-lock-environment.json`.

Each process had a 90-second signal deadline and each SSH invocation a 115-second
client deadline. All **29 processes exited zero**. The previous incomplete
30-second client-timeout attempt remains in `20261026_production_preflight.json`;
it was not overwritten or reclassified as exclusion failure. These deadlines
bound this harness, not the production guard, which calls blocking `lockf` without
an application deadline.

All acquisitions used the actual `catalog_lifecycle_guard`. A transparent timing
wrapper measured `fcntl.lockf`; a separate Python thread sampled a 100 ms heartbeat.
Holders retained ownership for eight seconds. Contenders began only after an
acquisition event. Same-host and cross-host trials were serialized on the same
guard to avoid unrelated canary contention. Guard inode observations remained
stable per host throughout: wepp1/wepp2 report 248998786; wepp3 reports 4253772674.
The differing host/protocol inode observations are recorded, not treated as a
global inode identity assertion. All participants use the same namespace/path;
exclusion is established by the measured critical-section intervals.

## Measured results

Three uncontended acquisitions on each host took **0.004–0.122 seconds**. Same-host
contenders spent 6.60–7.18 seconds waiting for the intentional holder; handoff after
release was approximately 0–3 ms. A tiny negative post-release timestamp on wepp3
(-0.14ms) is acquisition between unlock and the holder's subsequent log event,
not overlapping protected execution. No contender entered its critical section
before the holder began releasing ownership.

| Holder → contender | Blocking lockf, two trials | Delay after holder release |
| --- | --- | --- |
| wepp1 → wepp2 | 15.29 / 15.64 s | 8.16 / 8.45 s |
| wepp2 → wepp3 | 30.50 / 30.25 s | 23.65 / 23.45 s |
| wepp3 → wepp1 | 7.09 / 7.13 s | 0.37 / 0.59 s |

Cross-host post-release deltas use host wall clocks; per-process durations use
monotonic clocks. Sub-millisecond cross-host precision is not claimed.

Three concurrent canonical activations plus required-path freshness readback
completed in **11.97, 35.38, 12.57 seconds**, respectively, for the same directed
pairs. Initial blocking lockf durations were 7.13, 30.45, 7.14 seconds. Each publication
returned the actual scratch `probe.parquet` entry, `value:int64`, 518 bytes. This is
representative publication-boundary behavior for a tiny fixture, not a production
scan-size or throughput benchmark. Freshness succeeded and the stable guard
remained intact.

A separate actual `record_catalog_refresh` call on wepp1 while wepp2 held the
guard persisted a durable pending receipt in 7.51 seconds, including 7.10 seconds in
lockf. It did not enqueue anything; the receipt remains in scratch as evidence.
Seven unprivileged `/proc/self/task/<main-thread>/wchan` samples during that wait
were `nfs4_retry_setlk`. This directly locates that sampled process in a kernel
NFS lock wait. The holder's sampled waits were chiefly its intentional sleep.

Python thread heartbeat maximum gaps stayed below 0.30 seconds, including the
30-second blocking trials. This rules out multi-second GIL starvation in these
measured guard calls; it does not prove event-loop or HTTP availability.

## Diagnosis and disposition

The delay is **topology-dependent kernel lock waiting**, not a Python retry loop,
initial import cost, scheduler cadence, or an inherent fixed 30-second application
timer. The previously noted kernel retry/callback paths are consistent with the
measurements. These probes do **not** establish a lost callback, a NAS defect, or
the exact kernel branch responsible for each trial. No packet capture, privileged
kernel tracing, or server-side lock instrumentation was used. Extra tracing
privilege or infrastructure changes are unnecessary for the conclusions above.

Observed waits fit the existing 3600-second maintenance job timeout, and all
publication/readback canaries completed with exclusion intact. That supports
worker-side functional acceptance and retaining the current guard implementation.
It does not supply an HTTP latency objective that the contract/ADR never quantified.
Receipt persistence itself waits on this guard before async admission; the receipt
probe confirms that producer latency includes ownership waits.

The deployed query-engine `run_info` handler is async but directly calls synchronous
`resolve_run_context` → `refresh_run_context` → `ensure_catalog_fresh`. The deployed
query service command is a single uvicorn process. A pending/missing/stale catalog
that reaches the blocking guard on this event-loop thread can therefore delay
unrelated coroutine progress. Fresh ordinary reads need not acquire this guard.
The deployed web command has ten workers/four threads and an 1800-second timeout;
those settings do not prove request promptness either. Exact deployed source
excerpts are retained in `rollout-lock-http-source-readback.txt`.

**Recommendation:** accept the measured exclusion and worker-liveness gate without
changing storage settings. Keep HTTP contention responsiveness explicitly open
until the owning rollout review accepts this measured tail for the affected
request path or demonstrates an isolated HTTP/event-loop acceptance case under
contention. This is a concrete code-path exposure supported by measured waits,
not an observed production outage and not authority for a redesign. A successful
RQ capacity/reconciliation canary alone cannot close that distinct request gate.
