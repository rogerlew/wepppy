# RQ webhook implementation tracker

**Started**: 2026-10-27 22:09 UTC
**Updated**: 2026-10-28 (implementation acceptance)
**Phase**: Closed 2026-10-28; local implementation and acceptance complete
**Security**: High; independent source and final evidence reviews passed
**Approved checkpoint**: `6ba2d8d9d`
**Completed plan**: [implementation_execplan.md](prompts/completed/implementation_execplan.md)

## Task board

- [x] Ratify D01–D10, canonical contracts and ADR-0109; retain independent reviews.
- [x] Record operator approval/authority and commit the standalone ancestor.
- [x] Implement admission, idempotent recovery, lineage, generic settlement,
  conditional events, independent delivery and capture/playback protection.
- [x] Resolve independent correctness/security source findings.
- [x] Verify real API WEPP runs: 18 finished nodes and 388 fresh artifacts each,
  exact/semantic parity, healthy/failing receiver bytes and token-expiry independence.
- [x] Verify real persisted Redis restart between reservation and publication;
  stale dispatch arming rejected, no restored sends.
- [x] Verify actual culvert failed-execution delivery and existing domain summary.
- [x] Complete actual mixed-result culvert case: one success, 35 caught failures,
  38 finished RQ nodes, fresh model output and exact finished callback bytes.
- [x] Meet both performance limits under verified hung receivers/concurrent evaluation.
- [x] Finish final targeted/process gates and document the unrelated full-suite baseline failure.
- [x] Finalize evidence/docs, remove the disposable fixture and close local scope.

The full suite stopped at 6,826 passes on the preexisting roads publication source-
provenance mismatch. The roads file is unchanged from the approved checkpoint;
its exact SHA-256 is retained in the validation artifact. Do not refresh unrelated
roads scientific evidence merely to make this package's gate green.

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

Use [implementation_kickoff.md](prompts/completed/implementation_kickoff.md) and the
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

## Implementation progress (2026-10-28)

Standalone accepted ancestor: `6ba2d8d9d`. Runtime edits began only afterward.
Implemented initial generic settlement, pinned subprocess HTTP transport, Redis
receipts/claims, and shared publication/worker instrumentation. Initial 38 tests
passed; seven disposable real Redis/worker tests passed via retained
`artifacts/probes/run_container_tests.py` (container lacks redis-server).
Admission wiring and capture protections are in progress, with callbacks disabled
by default. Intermediate independent reviews found attempt-generation closure,
terminal claim atomicity, IPv6 classification, quota cleanup/envelope enforcement,
and evaluator fairness issues; remediation and regression evidence are underway.
No integrated acceptance or activation is claimed.

### Subsequent implementation validation

Existing route/recorder tests: 137 passed. Disposable Redis API/tracking tests:
25 passed, including same-key prepublication recovery, overlapping attempts,
conditional event commit, missing-intent publication rejection and tombstone expiry.
Full suite is running; actual workflow/performance/HTTP acceptance is outstanding.
Intermediate review fixes and remaining gates are recorded in the active ExecPlan.
Development dispatcher profile remains opt-in and disabled; no activation claimed.

- Actual WEPP API runs: three disposable copies, 18 finished nodes and 388 fresh
  artifacts each; semantic parity and receiver delivery still pending.
- Final review remediation in progress: helper-thread/fork coverage, watched
  external prerequisites, audited catalog detachment, deadline-bounded receipts
  and positive bounded observation of adopted helper exit. See active ExecPlan
  and ADR-0109 allocation. No release/activation approval is claimed.

### Final source and workflow evidence

Mixed culvert acceptance passed in `artifacts/culvert_mixed_egress_probe.json`;
`culvert_readback.py` verified actual job states, caught domain errors, fresh model
parquet and persisted/received event equality. The disposable batch worker used
one slot to isolate a preexisting parent/finalizer NoDb lock race; broader
concurrency acceptance is not claimed.

Ten subsequent real process-boundary tests passed after immediate-WATCH handling,
reuse of positive containment evidence and batching attempt registration with the
existing metadata transaction. Both independent reviewers passed these source
deltas with no high/medium findings. Backlog performance remains under measurement;
source review does not waive the approved conjunction of 5% and 50 ms.

### Generation proof and corrected performance fixture

Source review closed lost-attempt, overlap, deletion/recreation and missing initial
publication findings. Ordinary generation/predecessor writes, first-publication seed
and sticky incomplete markers preserve accepted computation while preventing stale
closure. Missing/zero-TTL job hashes remain unknown; see the canonical contract's
settlement section. Real boundary runs reached 51 passes before the final combined
gate. Fresh generation-enabled WEPP and culvert readbacks passed; final guard runs
are in progress.

Prior backlog artifacts had no actual sender attempts and are now explicitly
labeled evaluator-pressure diagnostics. A stale terminal due entry could starve
its principal; recovery now repairs its retention deadline. The corrected benchmark
asserts four active senders and receiver overlap before accepting its performance
result. No source-review approval or earlier timing substitutes for this gate.

## Final outcome

Runtime committed as `62b272a6c`. Canonical six-default/four-batch model and receiver
acceptance passed, including mixed domain failures and delivery after token expiry.
Verified-sender p95 overhead is +0.849% / +0.637 ms across 1,000 transitions each.
109 real-boundary tests and 3,020 targeted tests passed. Both reviewers confirmed
final evidence with no high/medium findings. The unchanged Roads full-suite failure
is isolated in [validation](artifacts/validation_summary.md).

Disposable services, networks, copied data and credentials are removed. Admission
and dispatch remain disabled by default; production deployment is outside scope.
Durable rules are in RQ-WH-01, ADR-0109 and the operator guide outside this package.
