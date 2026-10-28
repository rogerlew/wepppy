# RQ webhook implementation tracker

**Started**: 2026-10-27 22:09 UTC
**Updated**: 2026-10-28 (kickoff execution)
**Phase**: Reviewed checkpoint proposal; awaiting exact operator approval and commit authority
**Security**: High; dedicated final security review required
**Base revision**: `a44b27cbb3c376fce628ad48134db687c767848f`
**Active plan**: [implementation_execplan.md](prompts/active/implementation_execplan.md)

## Task board

### Done

- [x] Retain reviewed draft and 13 independently confirmed drafting dispositions.
- [x] Scaffold package, tracker, active ExecPlan and decision register.
- [x] Register package on project board and root active-plan index.
- [x] Incorporate accepted generic hierarchy and Option A decisions.
- [x] Add fresh-agent kickoff and acceptance matrix with all evidence marked pending.

- [x] Execute kickoff source audit and disposable real Redis/RQ substrate probes.
- [x] Prepare D01–D10 recommendations, proposed canonical amendments and ADR-0109.
- [x] Prepare [dated checkpoint](artifacts/20261028_contract_decision.md) for review.
### Ready

- [ ] Map culvert/WEPP completion, partial failure, deferred-finalizer and cancellation paths.
- [ ] Define generic hierarchical terminal-state evaluator and independent delivery experiments.

### Pending decisions / implementation gates

- [ ] Resolve [D01-D10](artifacts/decision_register.md) with explicit provenance.
- [ ] Record scoped execution/forest authority before integrated runtime work.
- [ ] Create current canonical webhook contract and applicable amendments/ADR.
- [ ] Obtain two independent contract reviews and disposition findings.
- [ ] Record explicit operator contract approval and commit authority; create
  standalone ancestor checkpoint and retain its revision.

### Implementation and acceptance backlog

- [ ] Implement per-submission callback intent and ratified payload/admission contract.
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

## 2026-10-28 direction update

Operator selected operation completion, per-submission freely supplied HTTPS URLs,
callback delivery despite later token expiry, auditability and short independent
attempts (10 seconds suggested) with limited retries. Registration/challenge,
ongoing grant revalidation and mandatory key storage are removed as prerequisites.
The observer-first recommendation is withdrawn in favor of evaluating existing
workflow completion boundaries and a shared delivery mechanism. No runtime changes
or commits performed in this revision. Earlier review approval does not cover it.

## 2026-10-28 18:00 UTC: Generic hierarchy clarification

Operator requires generic terminal detection for hierarchical jobs. Per-workflow
completion adapters are withdrawn. Evaluate existing recursive `jobs:*` membership,
central enqueue interception and dependency rules; distinguish settled state from
outcome and prove graph registration/completion races. Missing metadata is unknown,
not success. Culvert/WEPP become representative tests of the same mechanism.

## Risks and evidence

2026-10-28 operator clarification: batch may expose parent failure while continuing
children, whereas strict trees halt dependent execution. Added paired acceptance
for failure-known/unsettled batch and settled-failure strict chain. Current source
confirms failure-tolerant batch edges and parent failure projection in job_info;
that projection is not evidence of persisted parent RQ failure. Evaluator must
traverse all descendants regardless of parent status and follow actual edges.

WEPP completion jobs can remain deferred after failed prerequisites; culvert
finalizers may complete with partial run failure. A shared notifier must reflect
the operation outcome rather than raw parent/finalizer status. Callback persistence
and dispatch failures must not escape into tasking. Shared-resource exhaustion and
unsafe destinations remain acceptance concerns. Capture/delivery loss windows,
optional signing and exact audit/timeout/retry limits need specification.

## Verification status

2026-10-28: three independent reviewers returned ten hierarchy-design findings.
Nine received explicit drafting remedies; HC-03 was initially retained as an open
execution/domain outcome contract choice before the checkpoint. See the
[review disposition](artifacts/20261028_hierarchy_review.md). All three reviewers
confirmed the nine drafting remedies; correctness confirmed the then-open HC-03 disposition.
Five package documents and the draft pass scoped lint; no runtime tests performed.

Initial scaffold documentation passed lint and root size checks. The refreshed
seven-file package and project tracker pass scoped lint with zero errors/warnings;
package spelling previews and diff whitespace checks are clean. No implementation,
synthetic probes, stack restarts, API calls or model runs were performed for this
package. Future validation must retain exact commands, versions, counts, skips,
failures and artifact paths; do not reuse migration evidence as webhook acceptance.

## 2026-10-28 18:20 UTC: HC-03 operator decision

User selected Option A. Callback reports operation.completed and execution_status;
finished execution does not assert domain success. Clients fetch domain results
from existing APIs. No task-reported domain convention or embedded batch summary
in the initial generic callback. HC-03 decision is closed, with implementation
proof pending. See draft Consumer payload and identity proposal and decision
register for rationale and acceptance. No runtime change or commit performed.

## Handoff

Use [implementation_kickoff.md](prompts/active/implementation_kickoff.md) and the
[acceptance matrix](artifacts/acceptance_matrix.md). The 2026-10-28 request refreshes
this package for implementation; it does not start runtime work in this turn.

Start with the updated decision register and active plan. Product direction is
recorded; next specify completion/failure payloads and the smallest shared mechanism
for arbitrary supported hierarchies, using culvert/WEPP as acceptance cases. Do not reintroduce endpoint registration, ongoing
token revalidation or mandatory encryption as inferred requirements. Preserve
unrelated working-tree changes and closed migration/review history.

### Kickoff execution update (2026-10-28)

The kickoff has now been invoked. Starting HEAD is
`dd4e5381ba4e3fd66e82c0e14e8d82faa174ff47`; the earlier Handoff text describes the
pre-invocation scaffold. [Source/probe evidence](artifacts/20261028_source_and_probe_evidence.md)
and the [exact matrix](artifacts/20261028_contract_decision.md) supersede open-ended
recommendation drafting. No implementation or environment acceptance is claimed.

Remaining immediate authority: exact matrix approval and permission to commit the
standalone checkpoint. No branch switch or commit performed. Review results and
scoped documentation validation will be retained before handoff. Stack integration
and production deployment remain separately governed.

## Kickoff review and validation handoff

Two independent read-only reviewers passed proposal readiness after fixing and
confirming five findings (two overlap on credential replay). See
[review/disposition](artifacts/20261028_checkpoint_reviews.md). No unresolved high
or medium drafting findings. Decisions remain proposed until operator ratification.

The disposable Redis/RQ probe passed all assertions. Package and six external
contract/ADR documents passed scoped lint with zero errors/warnings; spelling
previews and diff whitespace checks passed. No production source or stack changes,
commits, full regression suite or integrated acceptance. Exact approval matrix:
[20261028_contract_decision.md](artifacts/20261028_contract_decision.md).

## Operator ratification (2026-10-28 19:56 UTC)

Operator: "decision matrix is approved. authority grants are authorized".
RQ-WH-01 exact matrix and ADR-0109 are accepted. Package commit and scoped local
implementation/integration/restart authority are granted; production deployment
remains excluded. Earlier pending-approval entries above are historical and
superseded. Create the standalone checkpoint ancestor before implementation edits.
