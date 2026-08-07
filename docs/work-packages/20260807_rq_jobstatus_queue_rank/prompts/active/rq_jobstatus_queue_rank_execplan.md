# RQ Jobstatus Advisory Queue Rank ExecPlan

## Progress

- [x] (2026-08-07 17:38 UTC) Read required repository guidance, current contracts, RQ/Culvert implementation, tests, and precedents.
- [x] (2026-08-07 17:38 UTC) Recorded starting revision and preserved the unrelated untracked investigation.
- [x] (2026-08-07 17:38 UTC) Created and registered the package scaffold.
- [ ] Amend the canonical contracts and complete two independent pre-implementation reviews.
- [ ] Commit and verify the standalone checkpoint ancestor.
- [ ] Implement bounded queue-candidate collection and optional snapshot.
- [ ] Add focused unit, route, OpenAPI, Culvert-shaped, race, disclosure, and access-bound tests.
- [ ] Update durable documentation and run all required gates.
- [ ] Complete independent code, QA, and security reviews; remediate findings.
- [ ] Archive this plan and close the package.

## Surprises & Discoveries

- RQ is pinned to `1.16.2` in `docker/requirements-uv.txt`.
- Culvert registers descendants under `job.meta` keys beginning with `jobs:` and
  enqueues the parent, per-run children, and finalizer on the `batch` queue.
- The existing status response already emits a `progress` object. The completed
  progress package confirms that behavior is approved; the current schema
  summaries omit it and will receive a separately identified documentation-only
  correction in the checkpoint.
- The route already has `open`, `token_optional`, and `required` polling modes,
  a 400-per-60-second default rate limiter, and unchanged 404 handling.

## Decision Log

- **2026-08-07 17:38 UTC** – Use `wepppy/rq/job_info.py` as the implementation
  home. The existing recursive traversal is the authoritative registered-tree
  walk, and the route remains a thin call-through.
- **2026-08-07 17:38 UTC** – Use a private accumulator passed by backward-
  compatible optional keyword argument rather than private keys in public
  `jobinfo` dictionaries, preventing metadata leakage.
- **2026-08-07 17:38 UTC** – For multiple same-origin candidates, use one ordered
  queue snapshot and a local ID-to-offset map. This meets the one-pass Redis
  access bound and avoids per-child `get_job_position()` calls.
- **2026-08-07 17:38 UTC** – Mixed origins omit the object because offsets from
  separate Redis lists are not comparable. No cross-queue ranking is introduced.
- **2026-08-07 17:55 UTC** – Four independent reviewer agents were attempted in
  two pairs. All remained running without returning review output after bounded
  waits, so the required checkpoint review gate is blocked and implementation
  must not begin.

## Outcomes & Retrospective

Implementation is intentionally pending. The checkpoint is blocked because the
required independent contract reviewers did not return outputs. At closure
this section will state the exact response behavior shipped, validation
outcomes, review dispositions, residual risk, and any deviation from this plan.

## Context and Orientation

`GET /api/jobstatus/{job_id}` is implemented in
`wepppy/microservices/rq_engine/job_routes.py` and delegates to
`get_wepppy_rq_job_status()` in `wepppy/rq/job_info.py`. That helper fetches an
RQ job from Redis DB 9, recursively follows child IDs stored in `job.meta` under
keys beginning with `jobs:`, aggregates status/progress/timestamps, and returns
the response payload. The job-status route must continue to use the helper and
must not gain queue-specific orchestration logic.

RQ 1.16.2 exposes an ordered queue list through its queue API. Queue offsets are
zero based; the public snapshot converts the selected offset to one-based
`rank` and retains the offset as `jobs_ahead`. A candidate is valid only when it
is a registered root/descendant, has normalized status exactly `queued`, has a
non-empty origin, and remains present in the selected queue list at snapshot
time.

The optional object is advisory. It is absent for terminal, started-only,
deferred-only, scheduled-only, missing-origin, mixed-origin, dequeue-race, and
other unreliable cases. The object never contains queue depth, unrelated IDs,
worker details, ETA, or metadata from other jobs.

## Plan of Work

First finish the contract checkpoint: update both canonical schema documents,
the current Culvert integration specification, package artifacts, and tracker;
obtain independent correctness and QA/security contract reviews; disposition
every finding; commit only checkpoint documentation; and verify that commit is
an ancestor before touching runtime code.

Then add a status-normalization helper, an optional candidate accumulator to the
existing recursive traversal, and a private queue-snapshot helper. The status
helper will preserve current aggregate ordering and diagnostics behavior. The
queue helper will deduplicate IDs, reject invalid origins and mixed origins,
read one ordered list for a multi-candidate single-origin snapshot, select the
minimum offset, and return the exact public schema with a UTC second-precision
timestamp. Narrow expected Redis/RQ race exceptions will omit the optional field
while leaving the already-built status response authoritative.

Add deterministic fake-job/fake-Redis tests for standalone roots, Culvert child
and finalizer trees, ordering, all omission cases, status normalization, race
handling, unrelated-ID exclusion, and bounded queue reads. Extend route tests
for pass-through, all poll-auth modes, rate limit, 404, and terminal responses.
Run the OpenAPI suite without changing route count or response codes.

Finally update the RQ README, route usersum documentation, canonical contracts,
and current Culvert docs with optional-field examples and token distinctions.
Run focused tests, repository guards, documentation lint, the full test sweep,
and three independent implementation reviews. Remediate all High/Medium
findings, record exact results, archive this plan, and close the package.

## Concrete Steps

Work from `/home/workdir/wepppy` and never touch the unrelated untracked
`docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/` directory.

1. Complete the package checkpoint files and canonical contract amendments.
2. Spawn separate read-only contract correctness and QA/security reviewers; save
   their exact findings and disposition all findings. This milestone is
   currently blocked because four attempted reviewer agents returned no output.
3. Stage only checkpoint/package/contract/review paths, inspect the staged diff,
   and commit `docs: ratify rq jobstatus queue rank contract`.
4. Verify the checkpoint SHA is an ancestor with `git merge-base --is-ancestor`.
5. Implement in `wepppy/rq/job_info.py`; keep `job_routes.py` limited to a concise
   OpenAPI description update if necessary. Add focused tests in the existing RQ
   and rq-engine test files or a new unit file if isolation is materially better.
6. Run the required focused tests after each implementation slice.
7. Update current durable docs and package evidence; do not modify
   `submit_payload.py`, frozen inventory, route checklist, dependency catalog,
   or static RQ graph.
8. Run all required guards, docs lint, and `wctl run-pytest tests --maxfail=1`.
9. Spawn separate code, QA, and security reviewers. Remediate every finding,
   rerun affected validation, and obtain post-fix confirmation for High/Medium
   findings.
10. Stage explicit implementation/review paths and commit the feature; then
    stage closure docs and commit `docs: close rq jobstatus queue rank package`.

## Validation and Acceptance

The implementation is accepted only when a queued standalone root reports its
own one-based rank, a finished Culvert root reports the earliest queued
same-tree `batch` child/finalizer, mixed origins omit the object, and races omit
or select a remaining candidate without raising. The object must contain only
`name`, `rank`, `jobs_ahead`, `position_job_id`, `basis`, and `observed_at`, with
the exact constant basis and timestamp format.

The focused tests must cover aggregate status/progress/timestamps, terminal
diagnostics/errors, 404, route auth/rate limits, no private metadata leakage,
OpenAPI invariants, and a large tree proving one ordered queue read or one
position operation rather than N scans. Guards must report no package-induced
route inventory, checklist, or RQ graph drift. Documentation lint and diff
checks must pass. The full suite must either pass or record its exact unrelated
first failure and preserve focused evidence.

## Idempotence and Recovery

Queue lookup is read-only and no cache or queue mutation is introduced. Repeating
status calculations is safe; each snapshot is freshly observed. Repeating tests
and documentation lint is safe. If the optional lookup encounters a narrowly
expected Redis/RQ race, the authoritative status response is retained and the
queue key is omitted. If a validation gate is blocked by unrelated shared-tree
state, record the exact command and first failure rather than absorbing that
change. Recovery from implementation errors uses targeted patches only; no
reset, clean, stash, branch switch, or broad reformat is allowed.

## Artifacts and Notes

- Package: `docs/work-packages/20260807_rq_jobstatus_queue_rank/`
- Contract decision: `artifacts/20260807_contract_decision.md`
- Pre-implementation reviews: `artifacts/20260807_contract_correctness_review.md`
  and `artifacts/20260807_contract_qa_security_review.md`
- Checkpoint disposition: `artifacts/20260807_checkpoint_review_disposition.md`
- Dedicated security review: `artifacts/20260807_security_review.md`
- Implementation reviews: `artifacts/20260807_code_review.md` and
  `artifacts/20260807_qa_review.md`
- Starting revision: `0f4aaaae5b0f370beb6a6193707fb57d4a8abc5d`

## Interfaces and Dependencies

The public interface is the existing `GET /api/jobstatus/{job_id}` route,
proxied as `/rq-engine/api/jobstatus/{job_id}`. The only new response key is an
optional top-level `queue` object. RQ remains pinned to `1.16.2`; Redis remains
DB 9; the `batch` worker remains unchanged. Existing polling auth modes,
`rq:status`, rate limits, error envelopes, status codes, queue topology, job
dependencies, cancellation, JWT issuance, and browse-token claims remain
unchanged. No new external dependency, endpoint, frontend surface, cache, or
worker control is permitted.
