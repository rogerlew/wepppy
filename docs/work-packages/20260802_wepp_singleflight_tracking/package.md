# WEPP Workflow Single-Flight Tracking

**Status**: Open (2026-08-03)
**Timezone**: UTC

## Overview

Two WEPP no-prep submissions for one production run passed the existing guard because it tracked only the short-lived orchestration jobs. Their hillslope children then ran concurrently against the same files. This package makes the guard follow the complete RQ job tree and verifies equivalent protection for normal hillslope, watershed, prep-only, and no-prep workflows.

## Objectives

- Reject a second WEPP submission while any executable descendant of the recorded workflow is active.
- Cover all five tracked WEPP orchestration keys, including both watershed run paths and watershed prep.
- Permit recovery after a failed workflow whose remaining deferred dependents can no longer run.
- Capture regression, RQ graph, documentation, and two-agent review evidence.

## Scope

### Included

- Single-flight inspection in `wepppy/rq/wepp_rq.py`.
- Focused unit and route-level regression coverage.
- Canonical RQ response contract and RQ operator documentation.
- Work-package validation and independent code/QA reviews.

### Explicitly Out of Scope

- A process-wide lock held for the full WEPP runtime.
- Changing existing RQ dependency edges or retry semantics.
- NAS performance tuning, worker concurrency, or rsync throttling.
- Canceling or mutating production jobs as part of implementation.

## Stakeholders

- **Primary**: WEPPcloud operators and users submitting WEPP runs.
- **Reviewers**: Independent code reviewer and QA reviewer agents.
- **Security Reviewer**: Not required.
- **Informed**: RQ and NoDb maintainers.

## Success Criteria

- [ ] A finished orchestration root with a started/queued/scheduled descendant blocks another WEPP submission.
- [ ] A viable deferred workflow blocks another submission.
- [ ] A failed workflow with only stranded deferred descendants permits retry.
- [ ] Hillslope, watershed, prep-only, and no-prep job keys share the behavior.
- [ ] Targeted tests, RQ graph validation, documentation lint, and dual reviews pass.

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`
- **ADR link(s)**: N/A
- **Decision provenance captured**: `yes` (production incident report and operator request, 2026-08-03; implementer: Codex)

## Dependencies

### Prerequisites

- Existing orchestration child links in `job.meta["jobs:..."]`.
- Existing per-run submit mutex and `RedisPrep` job-ID tracking.

### Blocks

- Reliable production mitigation for same-run concurrent WEPP filesystem mutation.

## Related Packages

- **Related**: [WEPP Interchange Dependency Race Guard](../20260428_wepp_interchange_dependency_race_guard/package.md)
- **Related**: [NAS diagnostics](../../infrastructure/ui-rcds-nfs-vs-dev-nfs.md)

## Timeline Estimate

- **Expected duration**: One focused session.
- **Complexity**: Medium.
- **Risk level**: Medium because submission admission behavior changes.

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Existing authenticated routes and authorization remain unchanged; the change only strengthens per-run concurrency admission.
- **Security review artifact**: N/A

## Hardening and Callus Softening

- **Failure signature(s)**: Concurrent same-run `_run_hillslopes_rq` jobs and missing generated inputs such as `wepp/runs/p34.man`.
- **Related prior hardening efforts**: Existing 30-second submit mutex and `WEPP_RQ_JOB_KEYS` active-job guard.
- **Health signals**: Same-run duplicate submissions return HTTP 409 while descendant work is live; no overlapping WEPP leaves appear for a run.
- **Danger signals**: Failed workflows permanently reject retries because deferred dependents remain registered.
- **Observation window**: 30 days after deployment.
- **Temporary calluses introduced**: None; this corrects the existing guard's tracking boundary.
- **Callus softening hypothesis**: None at package start.

## References

- `wepppy/rq/wepp_rq.py` - current single-flight helper and workflow orchestrators.
- `wepppy/rq/wepp_rq_pipeline.py` - child-job metadata and dependency construction.
- `wepppy/microservices/rq_engine/wepp_routes.py` - normal submission admission.
- `wepppy/microservices/rq_engine/bootstrap_routes.py` - no-prep submission admission.
- `docs/schemas/rq-response-contract.md` - canonical admission behavior.

## Deliverables

- Complete descendant-aware single-flight implementation and tests.
- Code-review and QA-review artifacts with findings dispositioned.
- Validation and production observation guidance.

## Follow-up Work

- Observe production for same-run duplicate rejection and any false-positive retry blocks.
