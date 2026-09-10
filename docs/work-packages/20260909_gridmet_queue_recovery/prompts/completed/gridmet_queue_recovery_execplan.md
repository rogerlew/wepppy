# Restore persistent GridMET queue waiting and transport recovery

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

A live GridMET request must wait in FIFO order until admitted or explicitly canceled, without a queue age deadline. Transient Redis transport failures must recover without duplicate tickets or slots. HTTP may run only under a confirmed, unexpired permit.

## Progress

- [x] 2026-09-10 UTC: traced production release/poll failures and confirmed two-second transport failure and 900-second queue deadline policies.
- [x] 2026-09-10 UTC: revised authoritative contract/ADR-0061 and implementation.
- [x] 2026-09-10 UTC: 145 focused tests, 14 real Redis scenarios and independently observed public client completion passed.
- [x] 2026-09-10 UTC: independent correctness and QA/security reviews passed; no unresolved findings.
- [x] 2026-09-10 UTC: broad suite 8,192 passed/77 skipped; API, docs and exception/stub checks passed. Package publication follows closure as requested.

## Surprises & Discoveries

Production job d4ccb55e-9619-49ba-8bce-8918ba1d52de (downright-houri, wepp2, 2026-09-09T22:51:34Z) failed on release after retrieval. Eleven release/poll TimeoutError failures affected six Marta runs. The original implementation deliberately disabled retries and discarded queued tickets after 900 seconds. Historical infrastructure latency cause remains unproven; these application policies are confirmed.

## Decision Log

The user explicitly requires a queue with no elapsed wait cutoff (2026-09-09 PDT). Keep the legacy wait configuration accepted for compatibility but ineffective; preserve its fingerprint field to avoid rejecting live existing clients during code activation. Remove deadline passing from HTTP clients. Retry only transport failures, never authentication, malformed state, policy conflict or foreign ownership. Matching enqueue/poll replay must confirm and refresh an already granted lease before HTTP starts. Renewal recovery stops at the last confirmed local validity bound or on release; release retries matching-token cleanup. Cancellation attempts bounded cleanup and relies on heartbeat expiry if Redis is unavailable.

## Outcomes & Retrospective

Implementation and all validation gates are complete: 145 focused tests, 14 real Redis cases with final targeted rechecks, 8,192 broad tests, API/stub/doc checks, independent correctness and QA/security reviews, and a two-container observed public download. The request now waits without an admission age cutoff, transient Redis failures reconcile owned state, and cancellation/lease bounds remain enforced. No production rollout performed. The user requested package closure before commit/push; deployment is held pending clarification.

## Context and Orientation

`wepppy/climates/gridmet/admission.py` owns Redis Lua FIFO tickets and leases. `acquisition.py` and `client.py` hold permits through response close. Tests are under `tests/climates/gridmet/`; real Redis scenarios run in fresh interpreters to bypass the test suite's Redis stub. The live admission pool has four slots, 300-second active leases and 60-second waiter heartbeats. Lease expiry is a safety bound, not a waiting deadline.

## Plan of Work

First revise `docs/schemas/gridmet-redis-admission-contract.md` and add ADR-0061 with the explicit user decision. Add an internal transport error classification and operation-aware retry path; make same-token Lua admission replay idempotent without changing foreign-owner rejection. Remove elapsed admission deadlines from the controller and both HTTP callers. Retain lease validity checks and interruptible renewal. Then replace deadline-abort tests with long-wait and transient failure regressions, including lost replies and real delayed Redis responses. Complete independent reviews and full suite.

## Concrete Steps

From `/home/workdir/wepppy`, run `wctl run-pytest tests/climates/gridmet tests/tools/test_gridmet_admission_probe.py`. Run real Redis scenarios against a disposable local service, never pause a shared Redis. Run `wctl run-pytest tests --maxfail=1` and scoped `wctl doc-lint --path` checks. Record exact results in tracker/artifacts. Inspect diff and exclude unrelated quality reports from commits.

## Validation and Acceptance

Waiters remain queued beyond the old budget and enter FIFO after release. Lost enqueue/poll responses do not duplicate occupancy or lose a live ticket's place. Release and renewal survive a transient timeout; renewal cannot resurrect an expired owner or authorize HTTP from a stale reply. Cancellation and fatal state errors still terminate. Real client receives and validates a result with injected release reply failure. Existing corruption, policy conflict, killed-owner, disabled-admission and process concurrency tests pass.

## Idempotence and Recovery

All test namespaces are unique and disposable. Production Redis is read-only during this work. Rollback is a coordinated worker code rollback through the canonical deployment entry point; never independently increase the limit or delete live keys. This package implements and validates the correction locally; production activation must use the real workflow deployment gate.

## Artifacts and Notes

Precedent: closed packages `20260907_gridmet_redis_admission` (reuse atomic FIFO/ownership), `20260831_gridmet_download_hardening` (preserve HTTP validation/retries), and `20260906_batch_climate_rap_contention` (shared contention context). Prior packages remain immutable. Health signal is disappearance of recoverable release/poll aborts; danger signals are occupancy above limit, duplicate grants, silent state errors or stuck abandoned tickets. Use recurrence-triggered observation; a future incident must cite this package. Recovery is permanent queue semantics, not a temporary mitigation.

## Interfaces and Dependencies

Use existing redis-py, threading and Lua; no new dependency. `acquire(request_kind=...)` returns a permit without a scheduling deadline. The legacy wait setting and exception remain import/config compatible but no longer cause wait expiration. Transport retries log sanitized operation/error class and recovery, never credentials, tokens or query URLs.


Revision note (2026-09-10 UTC): review exposed release authority, exceptional cleanup and concurrent renewal races. Closed local authority before release I/O, separated cleanup acknowledgment, made exceptional cleanup bounded even when renewal fails during join, and serialized manual/background renewals. All findings are resolved with regression tests. Canonical production deployment is a full-stack restart and includes unrelated commits; user has not explicitly requested that scope.


Final outcome (2026-09-10 UTC / 2026-09-09 PDT): validated local implementation
complete. Commit and push follow package closure. Production activation remains
separate and no production jobs were interrupted.
