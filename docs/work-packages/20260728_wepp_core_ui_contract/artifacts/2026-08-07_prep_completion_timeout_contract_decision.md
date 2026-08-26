# DOM-14A Prep-Completion Timeout Contract Decision

**Status**: Accepted; implementation pending
**Prepared**: 2026-08-07 04:58 UTC
**Starting implementation revision**: `f1599c71fdfae82aaecd7f3c0ddc1838608a8d22`

## Operator Direction

After production job `9636f1fd-3475-4b32-9216-65a7324c9d80` timed out, the
WEPPcloud operator directed Codex to measure the complete operation and make
the timeout three times that total. The complete locked recovery measured
1,234.1167397499084 seconds. This explicitly approves a 3,703-second integer RQ
timeout for the affected prep-only terminal leaf.

At 2026-08-07 05:09:55 UTC, after Codex identified the lock and mixed-version
requirements, the operator explicitly approved the 4,003-second lock lifetime
and a two-phase consumer-first rollout in addition to the timeout.

## Normative Delta

The prep-only WEPP pipeline terminal job has an explicit 3,703-second execution
timeout. Its run-scoped bootstrap Git lock remains exclusive for 4,003 seconds,
which is the job timeout plus a 300-second termination and cleanup margin. The
lock is still token-owned and released immediately when the operation finishes.

Rollout is compatibility-safe. Phase 1 deploys consumer logic that derives the
prep-completion lock lifetime from the current RQ job timeout plus 300 seconds,
with the existing 900-second lock default as a floor; enqueuers still emit the
old 180-second job. After all default workers on wepp1 and wepp2 accept that
behavior, phase 2 activates the 3,703-second enqueue timeout. No new serialized
job keyword is introduced. Rollback first restores old enqueue behavior, waits
for new-timeout leaves to drain, and only then may remove consumer compatibility.

Normal WEPP and watershed completion jobs retain existing timeouts. This
incident checkpoint is limited to the observed prep-only path; broadening other
paths requires their own timing evidence and decision.

## Applicable Contracts and Classification

- DOM-14A is the registered canonical owner of WEPP core run/prep RQ behavior.
- `docs/schemas/rq-response-contract.md` remains applicable and unchanged;
  response and error payload shapes do not change.
- `docs/schemas/nodb-persistence-concurrency-contract.md` remains applicable
  and unchanged; the longer token-owned Git lock strengthens exclusivity.
- This is an intended behavior change and production incident hardening, not a
  conformance fix.

## Compatibility and Security Impact

Queue, dependencies, function arguments visible to callers, response payloads,
status events, authentication, and run artifacts remain compatible. A default
worker may remain occupied longer. The longer lock reduces concurrency risk; it
does not weaken token ownership or permit a new mutation. Security impact is
high under the repository's queue/worker classification, so an independent
security review is required before checkpoint acceptance and after code changes.

## Regression Evidence

Focused RQ tests will verify timeout-to-lock derivation, prep-only scoping, old
job compatibility, and lock release on success and exception. Exact 3,703- and
4,003-second values use source/live-job direct readback. Existing bootstrap
auto-commit, RQ graph, stub, broad-exception, docs, and full pytest gates remain
required.

## Production Evidence

The original job started at 2026-08-07 03:02:09.434231 UTC and failed at
03:05:09.661254 UTC with `JobTimeoutException` at 180 seconds. The recovery ran
from 04:36:04.542398 UTC through 04:56:38.659138 UTC. A staged operator script
acquired `bootstrap:git-lock:door-to-door-salad` for 14,400 seconds, invoked
`Wepp.bootstrap_commit_inputs("WEPP prep-only pipeline timing recovery")`, and
recorded JSON in the worker container. It returned status `complete`, elapsed
1,234.1167397499084 seconds, commit `1e7fb6b5d031171042f92211b4fdc28c8f6782cf`,
and `lock_released: true`.

## Rationale and Rejected Alternatives

The value is the ceiling of exactly three times the observed total, preserving
the requested margin in integer seconds. Retaining 180 seconds is disproved by
production. Tripling only the 743-second status scan was rejected because it
excluded staging and commit time. An unbounded timeout was rejected because NFS
work must remain bounded. A 900-second lock was rejected because it expired
before the measured operation completed.
