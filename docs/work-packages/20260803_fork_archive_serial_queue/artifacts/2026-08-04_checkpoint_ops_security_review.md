# Independent Operations and Security Checkpoint Review

**Reviewer**: operations/security control agent (Archimedes)
**Date**: 2026-08-04
**Initial verdict**: reject pending fixes or explicit residual-risk disposition

## Findings

1. **High**: Route-first rollback could recreate concurrent NAS work. Fence
   admission, drain/reconcile both queues, retain fencing through any D-state
   host recovery, then revert routing and reopen.
2. **High**: A restore lock recheck is a snapshot rather than an exclusion fence
   across deletion and extraction. Add a cross-mutator fence or explicitly
   reduce scope.
3. **Medium**: Copying the broad default-worker privilege set to wepp3 would
   expose unrelated secrets and the Docker socket. Define and test a minimal
   capability set.
4. **Medium**: A shared profiled compose does not durably enforce wepp3 as the
   sole production consumer. Use host-specific placement or a fail-closed host
   sentinel.
5. **Medium**: `wctl rq-info` assumes service `rq-worker`, which will not exist
   on the otherwise-idle wepp3 host. Add a service selector or identify a
   surviving remote control host plus host-local checks.

The reviewer accepted the incomplete queued fork-destination behavior if
authorization and readiness gating remain proven. The reviewer later required
the cancellation amendment to be explicitly queue-origin-specific so other
queue and Culvert behavior remains compatible.
