# ADR-0039: WEPP Prep-Completion Timeout

**Status**: Accepted
**Date**: 2026-08-07
**Review Date**: Phase-2 activation date plus 14 days

## Context

The prep-only finalizer for `door-to-door-salad` failed at RQ's inherited
180-second limit while committing generated inputs on NFS. A complete recovery
under a four-hour run-scoped lock took 1,234.1167397499084 seconds and produced
commit `1e7fb6b`.

## Decision

Set the prep-only terminal job timeout to 3,703 seconds, the ceiling of three
times the measured total. Set its operation-scoped Git lock lifetime to 4,003
seconds, retaining exclusivity for a five-minute cleanup margin.

## Decision Provenance

- **Decision venue**: WEPPcloud operator/Codex incident conversation,
  2026-08-07 03:05 through 05:09:55 UTC.
- **Participants present**: WEPPcloud operator and Codex.
- **Decision owner**: WEPPcloud operator.
- **Planned implementer**: Codex.
- **Change summary**: prep-only terminal RQ timeout 180 to 3,703 seconds;
  operation-scoped Git lock lifetime 900 to 4,003 seconds.

## Rationale

Rounding up preserves at least the requested three-times margin. The separate
five-minute lock lifetime provides a bounded cleanup margin that reduces expiry
risk while RQ terminates and unwinds a task. The change is limited to the
production-observed prep-only path.

## Alternatives Considered

- Triple the 743-second status scan: rejected because it omitted staging and
  commit time.
- Retain inherited defaults: rejected because both are shorter than the
  measured operation.
- Remove the timeout: rejected because NFS work must remain bounded.
- Change every WEPP completion path: rejected pending equivalent total-runtime
  evidence for those paths.

## Consequences

A default worker can remain occupied for 61 minutes 43 seconds. The run's Git
mutation remains exclusive for up to 66 minutes 43 seconds. NFS metadata cost
is unchanged.

## Evidence

- Host `wepp1`; run `door-to-door-salad`.
- Failed job `9636f1fd-3475-4b32-9216-65a7324c9d80`.
- Recovery elapsed 1,234.1167397499084 seconds, status complete, lock released.
- Recovery commit `1e7fb6b5d031171042f92211b4fdc28c8f6782cf`.
- DOM-14A checkpoint; focused RQ regression tests are pending implementation.

## Risk and Rollback Notes

Monitor finalizer duration and default-queue occupancy daily and after each
prep-only finalizer for 14 days. Fence new prep-only submissions and assess
rollback on any repeat timeout, duration at or above 3,333 seconds, attributable
oldest default-queue wait above 10 minutes, three or more concurrent prep
finalizers lasting over 10 minutes, lock contention, or any Git/index error.
Rollback restores inherited defaults without data migration.
The sunset review 14 days after phase-2 activation must record keep, reduce, or
remove.

## Implementation Notes

Use a two-phase consumer-first rollout. Consumers first derive the prep lock
lifetime from the current job timeout plus 300 seconds with the existing lock
default as a floor. Only after wepp1 and wepp2 workers are compatible may
enqueuers activate 3,703 seconds. Rollback reverses that order after draining
new-format leaves. No serialized keyword, queue edge, or public response
contract changes.
