# Advisory Queue Rank in RQ Job Status

**Status**: Closed (2026-08-07 UTC)
**Timezone**: UTC

## Overview

This package adds an optional advisory queue snapshot to successful
`GET /api/jobstatus/{job_id}` responses. A caller can therefore see the current
position of the next queued member of a registered RQ job tree, including the
per-culvert children and finalizer that outlive a Culvert orchestration root.

The snapshot is additive, best effort, single-queue only, and never changes the
authoritative lifecycle status, authentication policy, queue topology, or job
execution behavior.

## Objectives

- Ratify and implement the exact optional `queue` response object.
- Traverse the registered `jobs:*` tree once and perform at most one bounded
  ordered queue read or one position lookup per status calculation.
- Preserve status, progress, diagnostics, error, timestamp, 404, rate-limit,
  and auth/JWT behavior.
- Prove Culvert root-to-child queue ranking, race-safe omission, disclosure
  boundaries, and large-tree Redis access bounds with deterministic tests.
- Update current contracts and Culvert/operator/developer documentation.

## Scope

### Included

- `wepppy/rq/job_info.py` queue-candidate collection and optional snapshot.
- Focused RQ and rq-engine route regression tests.
- Canonical response and rq-engine agent API contract amendments.
- Culvert integration and developer documentation updates.
- This high-impact work package, checkpoint, reviews, validation evidence, and
  closure artifacts.

### Explicitly Out of Scope

- ETA, queue depth, worker capacity, fairness, reservation, priority changes,
  queue topology changes, worker-count changes, or cross-queue global rank.
- New routes, frontend UI, queue wiring, dependency-graph changes, enqueue-order
  changes, cancellation changes, result TTL changes, or JWT issuance changes.
- Changes to the Culvert submit helper `submit_payload.py` or browse-token
  scopes/claims.
- Caching or unrelated job-status refactoring.

## Implementation Fidelity and Evidence (Required for modernization/migrations)

- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**: `wepppy/rq/job_info.py` registered RQ tree
  traversal and the pinned RQ 1.16.2 queue API.
- **Cutover proof required**: Direct unit and route tests must show that the
  production `jobstatus` helper returns the optional snapshot while the route
  remains a thin pass-through.
- **Acceptance evidence type**: `fixture-only`

## Stakeholders

- **Primary**: RQ-engine operators, Culvert_web_app developers, and API clients.
- **Reviewers**: Independent RQ correctness, QA, and security reviewers.
- **Security Reviewer**: Dedicated independent security reviewer required.
- **Informed**: WEPPpy RQ and rq-engine maintainers.

## Success Criteria

- [x] Standalone contract checkpoint is an ancestor of implementation (`7ce0cf524`).
- [x] Exact optional `queue` object is implemented with all omission rules.
- [x] Root and descendant Culvert queue ranking is deterministic and bounded in
  Redis operation count (one ordered snapshot for a multi-candidate tree).
- [x] Existing status, progress, diagnostics, error, auth, rate-limit, 404, and
  OpenAPI behavior remains green.
- [x] Current contracts and durable Culvert documentation are updated.
- [x] Focused gates, guards, and the full-suite attempt are recorded honestly.
- [x] Code, QA, and security reviews have no unresolved High or Medium findings.
- [x] ExecPlan is archived and package is listed under Done.

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`
- **ADR link(s)**: N/A
- **Decision provenance captured**: `yes` (operator-approved response contract,
  2026-08-07 UTC; implementer: Codex)

## Dependencies

### Prerequisites

- Existing registered `jobs:*` child links and RQ 1.16.2 queue semantics.
- Existing rq-engine polling auth and rate-limit behavior.
- The contract-first checkpoint and two independent contract reviews.

### Blocks

- None.

## Related Packages

- **Depends on**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Related**: [20260802_wepp_singleflight_tracking](../20260802_wepp_singleflight_tracking/package.md)
- **Follow-up**: None identified.

## Timeline Estimate

- **Expected duration**: One focused implementation session plus review gates.
- **Complexity**: Medium-High.
- **Risk level**: High because a public open-by-default route gains bounded
  shared queue-state disclosure.

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The public polling response gains bounded queue name,
  position, count, and a same-tree child ID; the implementation must prevent
  unrelated queue disclosure and cost amplification.
- **Security review artifact**: `artifacts/20260807_security_review.md`

## References

- `docs/schemas/rq-response-contract.md` - canonical response contract.
- `docs/schemas/rq-engine-agent-api-contract.md` - agent-facing polling/auth contract.
- `wepppy/rq/job_info.py` - aggregated job-status implementation.
- `wepppy/rq/culvert_rq_pipeline.py` - registered Culvert child/finalizer links.
- `docker/requirements-uv.txt` - pinned RQ dependency.

## Deliverables

Completed at closure: implementation, focused tests, durable docs, review
artifacts, validation evidence, intentional local commits, and archived plan.

## Closure Evidence

- Contract checkpoint: `7ce0cf524d9e7f4d2be6270ca220b574f04e91ed`.
- Implementation: `a416e7dd7a30007fe67e74982db4d7fc0e16063d`.
- Review remediation: `97141ba44`.
- Closure commit: `4565ec00b3b6a6d494b1abf7585cfb5d2b95f19c`.
- The approved one-snapshot queue-read tradeoff is documented in the code,
  contract decision, and dedicated security review. No queue wiring, auth, JWT,
  or route inventory changes were made.

## Follow-up Work

No follow-up is authorized by this package. Cross-queue ranking, ETA, and
worker-capacity estimates would require a separate contract decision.
