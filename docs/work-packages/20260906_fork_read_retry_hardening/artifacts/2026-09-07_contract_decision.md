# Contract Decision: FORK-READ-01

**Date**: 2026-09-07 UTC
**Starting implementation**: `87cfe40473108a93cbbd5733fdc13c99d97707ea`
**Classification**: Intended bounded remediation; conformance pending.

## Authorization and Scope

Operator instruction: "scaffold and implement work-package for retry for
identified transiented file system errors and 2, 3"; items 2 and 3 refer to
preserving the real filesystem error and propagating failed prerequisites.
Operator adds: "I don't think it's related to wepp3. i think it's related to
the burst of small file activity from the fork". This authorizes the bounded
implementation and necessary local contract checkpoint commit, not deployment.

## Canonical Matrix

- `docs/schemas/nodb-persistence-concurrency-contract.md`: direct read errno;
  opt-in initial read retry; optional absence and cache/lock invariants retained.
- `docs/schemas/rq-response-contract.md`: fork child failure outcome, exact
  lineage binding, unchanged response envelope and strict dependencies.
- `docs/adrs/ADR-0049-fork-preparation-read-retry.md`: retry budget/backoff.
- `docs/schemas/project-owned-config-contract.md`: applicable preservation and
  lifecycle guards unchanged; no configuration/provenance mutation.
- `docs/ui-docs/controller-contract.md`: existing authoritative polling retained.

## Exact Delta and Compatibility

Initial WEPP preparation NoDb reads opt into a 5-second shared deadline with
0.1-second exponential delays capped at 1 second for ENOENT/ESTALE only. Ordinary
callers do not gain retry latency; required read failures preserve original
errno, while optional missing files return None immediately. Never retry
writes, parsing failures, permissions, EIO, Redis or whole jobs. Cache signature
checks may not hide a filesystem failure by returning stale cached state within
the retry scope. File operations remain disk-authoritative.

Fork WEPP children carry server-generated lineage and a failure callback which
checks that root and destination still match before persisting failure and
publishing FORK_FAILED with the child ID. Callback errors must not replace the
original job failure. No child cancellation or dependency relaxation. No new
public response fields, data schema, model defaults or authentication changes.

## Risk and Evidence

High security triage: filesystem and queue callback boundaries. Validate real
file read errors and isolated real Redis/RQ lineage guards and callback
execution, valid/absent/empty/legacy/malformed states, no replay of mutations,
no cross-run state writes and no false success. Review the original errno
rather than asserting unproven NAS mechanism. Production NAS parity is a
rollout gate; tests with injected errors must be identified as such.

## Independent Reviews

Both independent reviews accepted after amendments; see
[review dispositions](2026-09-07_contract_reviews.md).

## Valid-State and Exception Matrix

| Read state | Expected outcome |
| --- | --- |
| Required populated controller, cold/singleton/Redis cache | Load valid state with no retry sleep; validate on-disk cache signature. |
| Required supported legacy payload | Existing preprocessing/hydration behavior; no new rejection. |
| Required missing file, cold/singleton/Redis cache | ENOENT retries only within opted-in deadline; exhaustion preserves ENOENT. Cached state cannot hide absence. |
| Optional missing file, cold/singleton/Redis cache | None immediately; no absence retry or stale-cache substitution in opted-in scope. |
| Existing file with transient ESTALE at stat/open/read | Opted-in bounded retry; original exception on exhaustion. |
| Empty or malformed required payload | Existing decode/type error immediately; never retry parsing. |
| EACCES/EPERM/EIO/ENOTDIR/ELOOP or other errno | Immediate original error; never retry. |
| Redis/lock/stale-write failure | Existing explicit contract; never filesystem-retried. |
| Outside read context | No new retry sleep; required actual-read errno preserved, optional absence remains None. |

| Callback state | Expected outcome |
| --- | --- |
| Current root, registered target child, matching receipt | Persist failed child ID/outcome and source failure notification. |
| Other siblings queued/started/scheduled | Durable outcome/log fail immediately; aggregate poll remains active until siblings quiesce. |
| Failed prerequisite with only blocked deferred descendants | Poll returns failed without waiting for deferred completion. |
| Missing/legacy lineage or missing receipt/root | No callback mutation or source notification; existing aggregate evidence remains. |
| Wrong source/target/root, unregistered child or superseded receipt | Reject callback with no unrelated state change/event. |
| Already succeeded destination | No failure overwrite/event. |
| Duplicate callback or late parent progress | Idempotent failure; late progress cannot restore running/waiting state. |
| Redis/status publication failure | Log reporting error; preserve original RQ task failure. |

The source log/event and durable failure outcome are immediate. Poll-driven UI
terminal transition still waits for queued/started/scheduled siblings to
quiesce under the unchanged aggregate policy; no claim of immediate terminal
UI is made. Strict downstream jobs need not leave raw deferred state for the
aggregate to report failed.

## Security Review Amendments

- Validate fetched root function, fork-archive origin, source/target args,
  registered child ID and child target arg, not metadata alone. Compare current
  receipt and terminal state atomically with failure persistence; only accepted
  updates may publish. Test receipt replacement between validation and commit.
- Ordinary non-fork and legacy children lacking new linkage are no-ops.
  Duplicate notifications are idempotent. Concurrent read contexts must not
  share retry budgets or affect outside-context reads.
- Keep filesystem diagnostics in operator logs. Source status messages contain
  child job IDs and a generic failure explanation, never raw exception text.
