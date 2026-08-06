# Security Review - Fork Skip Omni Scenarios/Contrasts and Reset

## Metadata

- **Package**: `docs/work-packages/20260806_fork_skip_omni_reset/`
- **Reviewer**: independent security reviewer agent
- **Date**: 2026-08-06
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
- [ ] Source model/Omni state, Omni timestamps, query-engine data, and all
  source-tree content except the existing `redisprep.dump` fork-job tracking
  delta remain unchanged; no source reset/cache/lock helper is invoked.
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
| SEC-01 | High | Query engine | Path cleanup can follow copied `_query_engine` links outside the destination | Destination-rooted descriptor/no-follow cleanup and external sentinels | Resolved |
| SEC-02 | High | RedisPrep | Copied `redisprep.dump` can redirect timestamp/job-marker mutation | Regular-file/no-follow verification and malicious-entry tests | Resolved |
| SEC-03 | Medium | Request | Unknown/repeated values can become truthy | Enumerate accepted scalars; reject all others before registration/enqueue | Resolved |
| SEC-04 | Medium | NoDb lock | Unconditional recovery could erase a live writer lock | Prove ownership, reject active locks, lock before refresh/mutation | Resolved |
| SEC-05 | Medium | Path scope | Profile destination copy and cache/lock resolution can diverge | Resolve one canonical destination under the approved target root | Resolved |
| SEC-06 | Medium | Persistence | “No replacement” conflicted with canonical atomic `os.replace` dump | Forbid controller substitution while requiring canonical atomic dump | Resolved |
| SEC-07 | Medium | Source integrity | Existing fork-job tracking mutates source `redisprep.dump` | Name it as the sole allowed delta and hash/diff all other source state | Resolved |

## Verdict

- **Gate status**: pass after post-fix confirmation
- **Unresolved findings**: zero high; zero medium
- **Release recommendation**: proceed after the standalone checkpoint commit

## Sign-off

- **Security reviewer**: independent security reviewer agent; final PASS
- **Package owner**: accepted final contract matrix on 2026-08-06
