# RQ Jobstatus Advisory Queue Rank Contract Decision

**Decision date**: 2026-08-07 UTC
**Starting revision**: `0f4aaaae5b0f370beb6a6193707fb57d4a8abc5d`
**Operator**: User requesting end-to-end execution of this package
**Implementer**: Codex
**Security impact**: High; dedicated security review required
**Parameterization change**: No; ADR not required

## Operator approval

The operator explicitly approves adding an optional advisory `queue` object to
`GET /api/jobstatus/{job_id}` using the exact semantic contract in the request.
The approved rank is the one-based position of the earliest queued member of the
requested registered single-origin job tree. The approval does not extend to
ETA, cross-queue ranking, auth changes, token changes, queue topology changes,
unrelated queue disclosure, or client/UI implementation.

## Normative payload delta

Successful job-status responses may add exactly this optional top-level object:

    "queue": {
      "name": "batch",
      "rank": 17,
      "jobs_ahead": 16,
      "position_job_id": "next-queued-member-job-id",
      "basis": "next_queued_job_in_tree",
      "observed_at": "2026-08-07T18:42:11Z"
    }

`name` is non-empty; `rank` is positive and one-based; `jobs_ahead` is
non-negative and zero-based; `rank == jobs_ahead + 1`; `position_job_id` is the
selected requested-root or registered `jobs:*` descendant; `basis` is the exact
constant `next_queued_job_in_tree`; and `observed_at` is a UTC RFC 3339/ISO-8601
timestamp ending in `Z`, preferably at second precision.

## Queue-tree semantics and omission

The existing recursive traversal follows only registered `job.meta` keys whose
names begin with `jobs:`. During that one traversal, collect deduplicated
members whose normalized raw RQ status is exactly `queued`, together with their
non-empty RQ queue origin. The object is emitted only when at least one queued
candidate exists, every queued candidate has a valid origin, all queued
candidates share one origin, and the selected candidate remains in that queue's
ordered Redis list when the snapshot is read. Select the candidate with the
smallest zero-based offset. If any condition fails, omit the entire key rather
than returning null, partial, zero, negative, guessed, synthetic global, or
unrelated data.

The queue key is absent for no queued member, started-only or terminal trees,
deferred-only or scheduled-only trees, missing/invalid origin, mixed origins,
dequeue races with no remaining candidate, and expected Redis/RQ races that
prevent reliable observation. A remaining same-tree candidate may be selected
after another candidate disappears. The snapshot is advisory and is not an ETA,
reservation, fairness guarantee, worker-capacity estimate, or stable promise.

For multiple same-origin candidates, one ordered queue snapshot (or equivalent
single bounded queue-position operation) is used and a local offset lookup is
performed. No metadata from unrelated queue entries is fetched or returned.
Different queue origins are intentionally incomparable; current Culvert parent,
children, and finalizer use `batch` and are covered.

## Compatibility, auth, and discrepancy classification

This is additive and preserves existing top-level names and meanings, aggregate
status and progress, timestamps, diagnostics, controlled errors, 404
`not_found`, rate limits, and OpenAPI response codes. `jobinfo` does not gain a
queue field. The existing `RQ_ENGINE_POLL_AUTH_MODE` values (`open` by default,
`token_optional`, and `required` with `rq:status`) remain unchanged; queue data
follows the endpoint's existing auth result. JWT issuance, scope bundles, TTLs,
revocation, service groups, run claims, and cancellation compatibility remain
unchanged. The long-lived Culvert service JWT remains the authenticated polling
credential; the returned short-lived browse token remains browse/download-only
and receives no polling scope.

Current `get_wepppy_rq_job_status()` already emits the approved `progress`
object, as demonstrated by runtime tests and the completed
`20260410_rq_controller_state_errors_progress_outputs` package. The current
schema-summary paragraphs omit it. That is a pre-existing documentation
conformance correction in this checkpoint only; progress runtime semantics are
not changed.

## Rejected alternatives

- Ranking only the requested root was rejected because Culvert roots finish
  after registering queued children.
- Calling `get_job_position()` once per child was rejected because polling cost
  would scale with tree size.
- Returning unrelated queue IDs or queue depth was rejected as unnecessary
  disclosure and out of scope.
- Combining offsets from multiple queues was rejected because separate Redis
  lists have no comparable global order.
- Caching was rejected because it would require a separate staleness contract.
- Adding queue logic to Culvert routes was rejected because this is generic
  jobstatus behavior.

## Regression-evidence plan

Add deterministic fake RQ jobs, queue lists, and Redis errors covering standalone
root rank, unrelated entries, descendant/finalizer selection, ordering,
started/deferred/scheduled/terminal omission, origins, races, enum-like and
string status normalization, unrelated-ID exclusion, and bounded large-tree
access. Extend route tests for pass-through, open/optional/required auth,
wrong/missing scopes, 429, 404, and terminal responses. Preserve existing
aggregate status, progress, timestamps, diagnostics, errors, and metadata
leakage assertions. Run focused pytest, OpenAPI, Culvert, RQ graph/inventory,
exception, quality, diff, documentation, and full-suite gates.

## Checkpoint status

Canonical contract amendments and independent contract reviews are required in
this ancestor before implementation conformance can be claimed. **Implementation
conformance is pending.**
