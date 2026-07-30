# DOM-05A Checkpoint Operations and Security Review

**Reviewer**: Independent operations/security control reviewer

**Date**: 2026-07-30 UTC

**Review mode**: Read-only, pre-implementation

## Verdict

FAIL - reject current checkpoint and hold implementation.

## Blocking Finding

Required durable checkpoint evidence was incomplete. The security artifact was
still a pending template, and the two review artifacts and disposition did not
yet exist.

## High Findings

1. The untrusted enum was not explicitly allowlisted before mutation/enqueue,
   and the defensive NoDb setter used an optimization-removable `assert`.
   Require four-token validation before mutation/enqueue, explicit defensive
   validation at the worker/NoDb boundary, and negative normal plus batch/base
   tests proving an error response, no persistence, and no job.
2. The route lacked the canonical path-config versus `Ron.config_stem`
   integrity guard. Reject mismatches before controller, timestamp, or queue
   mutation and test that order.
3. Native-process containment was not proven. The WBT wrapper used
   `shell=False` but lacked a timeout, process-group termination, reliable
   wait, and explicit nonzero-exit evidence. Require bounded containment or
   kill-tree evidence before enabling the selector/default.
4. Full rollback was not safely executable. Prefer staged rollback: first
   restore the new-run default while retaining additive `topaz` compatibility;
   permit full removal only after an authorized, lock/cache-safe inventory and
   migration procedure proves that no persisted `topaz` remains.

## Medium Findings

1. Strengthen release provenance and fleet ordering with a clean committed WBT
   source revision, `cargo build --locked`, source/lockfile/built/installed
   hashes, preservation of the prior-binary hash, a WBT release commit, and
   per-worker-host discovery plus execution before the WEPPpy/default deploy.
2. Constrain the discoverable operation schema to the four-value enum and add
   negative hostile-value, batch/base, config-mismatch, native-timeout/cleanup,
   and rollback-inventory evidence.

## Low Findings

None.

## Confirmed Controls

The browser call retains bearer session-token transport; the route retains
`rq:enqueue` plus run authorization; CSRF classification is unchanged; native
arguments are fixed and use `shell=False`; output remains the run-scoped
`dem/wbt/relief.tif`; and no queue edge, secret, external dependency, or silent
algorithm fallback is intended.
