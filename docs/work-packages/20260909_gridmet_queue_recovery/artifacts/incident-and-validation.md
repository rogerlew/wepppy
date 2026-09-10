# Incident and validation evidence

## Confirmed failure path

Production job `d4ccb55e-9619-49ba-8bce-8918ba1d52de`, run `downright-houri`, config `portland-10-mofe`, ended 2026-09-09T22:51:34.686503Z on wepp2. The failure was `GridMetAdmissionUnavailable: GridMET admission release unavailable (TimeoutError)`. Eleven release/poll transport failures were found in six Marta-owned runs. The traceback ends in permit release after GridMET retrieval, not a 900-second queue expiry. Both the terminal two-second transport policy and separate 900-second admission cutoff were confirmed in deployed/current code.

Redis was reachable during investigation, no stuck admission state was found, and latency monitoring was disabled. Retained slowlog included a 1.661-second XREVRANGE at 22:41:54Z and Redis persistence overlapped some failures. These are possible latency contributors, not proof of the physical cause of any individual timeout. No Redis tuning or production restart was performed.

Read-only 150-second follow-up measurements:

- gridmet-latency-wepp1: 559 probes, max 33.588 ms, p99 5.665 ms, errors 0; start 2026-09-10T00:32:14.962456+00:00.
- gridmet-latency-wepp2: 558 probes, max 2002.697 ms, p99 317.451 ms, errors 1; start 2026-09-10T00:32:15.813632+00:00.

## Local validation

Focused suite: 145 passed, 14 opt-in Redis tests skipped (final focused run, 9.67s). Real Redis full boundary run: 14 passed in 192.53s. Four tests paused only a dedicated disposable Redis for 2400ms, observing actual redis-py TimeoutError and successful recovery for enqueue, poll, renew and release. Release fault injection used real HTTP against a local fixture plus response closing and payload validation. Lost committed reply tests exercise the actual Lua result then drop its acknowledgment. Final renewal serialization changes are additionally rechecked below.

An initial real Redis suite overlapped a pause suite on the same disposable service, causing an observer snapshot timeout in killed-owner testing. This was test orchestration interference; the complete suite reran serially and all 14 passed. Production/shared Redis was never paused.

A public GridMET client in Forest rq-worker `6a5a81f81002` returned 366 valid daily records for 2020. A repeat was observed from rq-worker-batch `6c90246e0aec` under a unique test namespace; final queue/active counts were zero. Final observer peak and suite/review outcomes are recorded when complete.

## Deployment boundary

The canonical `wctl rq-info --detailed` gate is incompatible with the installed RQ CLI (`No such option: --detailed`). Its wrapper also performs worker-registration reconciliation before calling the CLI; use raw read-only registry/hash evidence for investigation instead. The smallest tooling follow-up is correcting that documented gate. A direct read found default started job `43cf5b09-5065-4632-923f-0e3450710c60`, no queued jobs, and no batch started jobs. Production deployment remains gated by active work; no worker restart or live namespace mutation was performed by the fix workflow. A subsequent read found both queues idle. Canonical wepp1 deployment still recreates the full stack and incorporates prior unrelated commits, so it is separate from this local code fix.


Final boundary rechecks after review corrections: 4 ownership/lost-reply/clocks/heartbeat scenarios passed in 54.63s; 4 actual socket-delay scenarios passed in 46.18s. The independent observer collected595 samples, peak 1, no limit violations and zero final active/queued state. Stub completeness passed.

The wepp2 follow-up probe timed out at 2026-09-10T00:32:45.841056Z after 2002.697ms; contemporaneous wepp1 observations (five samples in the surrounding window) peaked at 27.308ms. This establishes a real transient affecting the wepp2 path/process during the investigation, but does not distinguish network latency from process scheduling or prove the cause of historical failures.


API validation: `wctl run-stubtest wepppy.climates.gridmet.admission` passed
("Success: no issues found in 1 module"). The check exposed pre-existing typing
ambiguities in environment parsing, wait bookkeeping and context exit return
type; annotations were corrected without changing behavior. `wctl check-test-stubs`
also passed. No broad exception handlers were added; changed-file enforcement passed.
The disposable Redis container was stopped and removed after all probes finished.


## Final gate results

`wctl run-pytest tests --maxfail=1`: **8,192 passed, 77 skipped, 3,109 warnings**,
852.04 seconds, exit 0. Opt-in Redis cases ran separately as recorded above.
The final broad run covers the final behavioral code; the subsequent typing-only
correction passed stubtest. Focused tests: **145 passed, 14 opt-in skips**.
Documentation lint, test-stub completeness, API stubtest, changed-file broad
exception enforcement and `git diff --check` all passed. An earlier broad run
was intentionally interrupted after review corrections, then restarted to
obtain this complete result.
