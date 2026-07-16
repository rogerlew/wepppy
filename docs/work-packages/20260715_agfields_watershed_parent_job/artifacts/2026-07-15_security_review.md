# Security Review - AgFields Watershed Parent Job

## Metadata

- **Package**: `docs/work-packages/20260715_agfields_watershed_parent_job/`
- **Reviewer**: Independent QA/security review subagent
- **Date**: 2026-07-15
- **Scope reviewed**: authenticated AgFields enqueue, worker child registration,
  recursive status/cancellation, Redis metadata, and local live verification
- **Commit/branch context**: `master`, local implementation in progress
- **Related artifacts**: `2026-07-15_code_review.md` and
  `2026-07-15_qa_security_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: queue topology and cancellation behavior change behind an
  authenticated run-scoped mutation.
- **Threat model assumptions**:
  - The existing route remains protected by `rq:enqueue` and run authorization.
  - Scheme names and child IDs are generated/validated server-side.
  - Workers retain the same run-root and model-execution boundaries.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-1 | High | Cancellation authorization | Session-only checking allowed user/service/MCP cross-run cancellation. | Wrong-owner and wrong-run route regressions. | Enforce `authorize_run_access` for the `rq:status` path. | Closed |
| SEC-2 | High | Dependency release | Already-failed dependencies could strand later schemes or finalization. | Ready-deferred helper and call-order tests. | Apply the Batch Runner release guard to every failure-tolerant dependent. | Closed |
| SEC-3 | High | Dispatch/cancellation | Cancellation could race a partial child tree or a stale parent save. | Complete parent `meta=`, shared lock/marker, concurrent-cancel regression. | Refresh/check/update/save under the dispatch lock before any state write or enqueue. | Closed |
| SEC-4 | Medium | Audit metadata | Child metadata could be published before its follow-up save. | Enqueue metadata assertions. | Supply complete metadata atomically at enqueue. | Closed |
| SEC-5 | Medium | Response contract | Root versus named-child mapping semantics were undocumented. | Route assertions and canonical contract text. | Document the existing named-child compatibility form. | Closed |
| SEC-6 | Medium | Culvert compatibility | Normal run authorization would reject legacy Culvert submit credentials; a broad bypass would be unsafe. | Single-/dual-scope Culvert positives and non-Culvert denial. | Collect accepted scopes and allow the Culvert path only for server-owned `culvert_batch_uuid` metadata. | Closed |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: proceed after the remaining automated and live
  acceptance gates pass

## Surface Checks

- [x] Auth/session/run authorization is regression-tested.
- [x] No secrets or tokens are persisted in code, logs, or evidence.
- [x] Request enum/worker inputs remain validated.
- [x] Writes remain inside the designated run tree.
- [x] Enqueue edges are intentional, documented, and graph-checked.
- [x] Cancellation cannot escape the registered descendant tree.
- [x] No new network, dependency, CI, or supply-chain surface.
- [x] NoDb and Redis state updates remain consistent under retries/failures.
- [x] Errors remain explicit and observable without credential disclosure.

## Validation Evidence

- Independent final security re-review: 28 focused job-control tests passed.
- Owner focused suite: 118 tests passed across AgFields RQ/routes, job info,
  cancellation, and Culvert routes.
- RQ graph and diff checks passed.

## Residual Risk

The legacy Culvert submit scope remains intentionally batch-wide because the
batch UUID is server-generated after submission. Its cancellation exception is
limited to jobs carrying server-owned `culvert_batch_uuid` metadata. Ordinary
run jobs always require `rq:status` plus run authorization.

## Sign-off

- **Security reviewer**: Pass, 2026-07-15
- **Package owner**: Pass, 2026-07-16; authenticated live acceptance completed
  with all five registered jobs terminal-success and no worker exception
