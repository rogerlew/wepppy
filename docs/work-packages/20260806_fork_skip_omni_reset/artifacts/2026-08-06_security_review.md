# Security Review - Fork Skip Omni Scenarios/Contrasts and Reset

## Metadata

- **Package**: `docs/work-packages/20260806_fork_skip_omni_reset/`
- **Reviewer**: pending independent security reviewer
- **Date**: pending
- **Scope reviewed**: fork UI/API/RQ input, rsync exclusion, destination Omni
  reset, NoDb cache/locks, source/destination run-tree containment
- **Commit/branch context**: `master`; implementation not started

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: yes
- **Triage rationale**: a public fork route controls conditional run-tree
  omission and destination filesystem/NoDb reset in an RQ worker.
- **Threat model assumptions**:
  - Run IDs and destination roots remain resolved by existing trusted helpers.
  - The source tree may contain symlinks or special entries at reset targets.
  - A reset may fail after rsync and must not publish success.

## Required Surface Checks

- [ ] Boolean parsing cannot introduce arbitrary paths or modes.
- [ ] Exclusions are anchored to the two exact destination-relative collections.
- [ ] Reset never follows a source or destination symlink outside the run root.
- [ ] Source content and controller/cache state remain unchanged.
- [ ] NoDb mutation uses canonical locking, dump, cache, and lock invalidation.
- [ ] Exactly the two Omni RedisPrep timestamps are removed; unrelated lifecycle
  timestamps remain unchanged.
- [ ] Copied query-engine catalog/cache cannot advertise removed Omni artifacts,
  and regenerated discovery preserves unrelated datasets.
- [ ] Failure cannot expose a destination as successfully ready.
- [ ] Auth, CSRF/session-token, ownership, queue, cancellation, and error payload
  behavior remain unchanged.
- [ ] Property/integration tests cover all boolean combinations and malicious
  target-entry types.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| Pending | Pending | Pending | Independent review not yet performed | Dispatch reviewer after contract inventory | Open |

## Verdict

- **Gate status**: fail (pending review)
- **Unresolved findings**: review not started
- **Release recommendation**: hold implementation until checkpoint acceptance

## Sign-off

- **Security reviewer**: pending
- **Package owner**: pending final contract acceptance
