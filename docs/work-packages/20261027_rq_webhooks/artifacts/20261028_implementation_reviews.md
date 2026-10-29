# Implementation review disposition

Scope: implementation `62b272a6c`, descending from approved checkpoint `6ba2d8d9d`.
This artifact records independent source reviews; it does not approve activation.

## Correctness review

Independent reviewer: `/root/contract_correctness`. Final disposition: **PASS**, no
remaining high/medium source findings after the following fixes:

- Attempt-generation closure, callback lineage and conditional event commit.
- Verified external prerequisite receipts watched with actual RQ state.
- Helper-thread ownership, original supervisor-thread context, pending/live/nested
  thread checks, and workhorse ownership retained until process death.
- Inherited nonblocking failure poison, including fork helpers and publication
  after the task completion byte; positive process containment remains mandatory.
- Explicit catalog-maintenance detachment at the audited server call site.
- Streamed receipt construction deadline and shared closure deadline.
- 410 publication evidence, postcommit culvert Redis failure recovery, and a
  retryable-admission replay race returning 202 with the planned job ID.
- Monotonic generic scheduler deferrals preserving newer retry/retention deadlines.

Evidence: `test_webhook_tracking.py`, `test_rq_engine_webhooks.py`; final review
boundary regressions 8 passed, helper lifetime/nested-thread regressions 6 passed,
and catalog dispatch regressions 39 passed. Earlier full tracking run 29 passed
precedes these additions. The full repository gate remains a separate obligation.

## Security review

Independent reviewer: `/root/contract_security`. Latest disposition: no unresolved
high/medium security source findings. Reviewed URL normalization/pinned TLS/total
sender deadline; raw destination confinement and capture/playback redaction;
principal quotas/cleanup; atomic publication and Redis-process arming; independent
claims; closure poison/thread coverage; detached context and external observations.
Fixture review confirmed owned writable roots, read-only sources, isolated Redis,
controlled receiver trust and no retained bearer credentials.

## Historical acceptance holds

Source approval does not override performance or actual-workflow gates. Retained
backlog measurements initially failed at 40.0% and then 27.6% p95 overhead; both
exceed the approved 5% limit. The idle-only 2.99% result is insufficient. Final
activation remains disabled until the acceptance matrix is complete.

### Final performance-related source review

Both independent reviewers passed batching the pre-fork start receipt with the
existing metadata transaction and sharing the 100 ms evaluator scheduling budget
across active roots, rotating after each bounded generator step. Ordinary RQ
errors, producer closure, retry deadlines and final generator cleanup are preserved.
The slice is cooperative: an in-flight bounded step may finish after its deadline.
Ten process-boundary tests and three scheduler regressions passed. No high/medium
source findings remain; performance acceptance is separately required.

### Generation and publication findings: closed

Both independent reviewers confirmed closure of failed-bookkeeping ABA, missed
overlapping attempts, hash deletion/recreation and missing first publication proof.
The ordinary pre-fork write preserves current/predecessor generation; first
publication seeds unstarted exactly once; discontinuities are sticky incomplete.
Current generation is fenced with actual job state. Missing hashes remain unknown.
Root publication checks preserve computation acceptance while suppressing unsafe
notification proof. Known older registered producers retain their exit obligation.

The late-WATCH proposal was rejected; active-page early return retains early fences
for every potential terminal page. A stale terminal due repair prevents principal
starvation. Prior zero-attempt backlog artifacts are evaluator-only diagnostics;
final measured sender overlap is mandatory. No high/medium source finding remains
after the final publication review; acceptance is still a separate gate.

## Final local acceptance sign-off

Both independent reviewers confirmed the final canonical six-default/four-batch
fixture evidence. Runtime source is committed at `62b272a6c`; no high/medium finding
remains. Final gates: 109 real-boundary tests; 3,020 targeted passes/223 skipped;
actual v6 WEPP artifact parity and post-expiry delivery; parallel mixed culvert
38 finished nodes, one model success and 35 caught failures.

Both reviewers independently recomputed 1,000-transition p95: 75.064 → 75.701 ms,
+0.849% / +0.637 ms, with 11 receiver observations during timing and 15 audited
attempts. The earlier single-batch and zero-sender limitations are superseded by
these final results, not waived. The full-suite roads provenance failure remains
an explicitly isolated baseline issue. Local acceptance passes; production
deployment/activation is outside this package's authority.
