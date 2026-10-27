# RQ webhook implementation tracker

**Started / updated**: 2026-10-27 22:09 UTC
**Phase**: Scaffold complete; product decisions and contract checkpoint pending
**Security**: High; dedicated final security review required
**Base revision**: `a44b27cbb3c376fce628ad48134db687c767848f`
**Active plan**: [implementation_execplan.md](prompts/active/implementation_execplan.md)

## Task board

### Done

- [x] Retain reviewed draft and 13 independently confirmed drafting dispositions.
- [x] Scaffold package, tracker, active ExecPlan and decision register.
- [x] Register package on project board and root active-plan index.

### Ready

- [ ] Inventory pilot routes, stable identities, grant capabilities and job retention.
- [ ] Define disposable observer experiments and evidence matrix.

### Pending decisions / implementation gates

- [ ] Resolve [D01-D10](artifacts/decision_register.md) with explicit provenance.
- [ ] Record scoped execution/forest authority before integrated runtime work.
- [ ] Create current canonical webhook contract and applicable amendments/ADR.
- [ ] Obtain two independent contract reviews and disposition findings.
- [ ] Record explicit operator contract approval and commit authority; create
  standalone ancestor checkpoint and retain its revision.

### Implementation and acceptance backlog

- [ ] Implement authorized subscription/endpoint records and canonical APIs.
- [ ] Implement chosen capture and independent delivery design.
- [ ] Run targeted lifecycle, security, persistence and noninterference regressions.
- [ ] Run integrated API/worker/receiver acceptance and model artifact parity.
- [ ] Validate disable/restart/rollback with outstanding deliveries.
- [ ] Run required broad/conditional checks and final independent reviews.
- [ ] Publish client/operator docs and close package with accurate evidence grade.

## Decisions and rationale

2026-10-27 22:09 UTC: User requested an implementation work-package scaffold.
Create an open implementation package while preserving unresolved decisions; do
not infer approval of recommendations from the scaffold request. The observer is
the first evaluation candidate because it could avoid computation-worker changes.
Escalation requires retained acceptance evidence. Native delivery remains excluded
because blocking HTTP does not meet the required isolation.

2026-10-27 22:09 UTC: Prior correctness/security/operations reviews are provenance
only. Their closure addressed wording and decision gates, not a selected API,
storage model, deployment or implementation. Canonical checkpoint reviews remain
separate, as required by the contract-first standard.

## Risks and evidence

Capture can miss expired/deleted/requeued state; verify retention/outage bounds
before choosing observation. Stable principal identity does not authorize durable
delivery; ratify bounded grants. Default RQ registry reads can mutate jobs; prohibit
cleanup in observation. Shared-resource exhaustion requires admission and fairness
limits. Secret retrieval is not an existing encrypted dynamic store. The decision
register and reviewed draft retain these as explicit design gates.

## Verification status

All four package documents pass scoped documentation lint with zero errors and
warnings; spelling previews have no differences. Root AGENTS size passes at 160
lines. No implementation,
synthetic probes, stack restarts, API calls or model runs were performed for this
package. Future validation must retain exact commands, versions, counts, skips,
failures and artifact paths; do not reuse migration evidence as webhook acceptance.

## Handoff

Start with the decision register and active plan. Product choices remain open:
individual-job versus workflow events, reliability level, and registered endpoints
versus per-submission URLs. Capture answers and rationale before promoting the
draft. Preserve unrelated working-tree changes and the closed migration package.
