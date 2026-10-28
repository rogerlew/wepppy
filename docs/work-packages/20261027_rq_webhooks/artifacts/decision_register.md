# Webhook decision register

Updated: 2026-10-28 18:20 UTC. Execution record, not canonical authority.
Operator direction on 2026-10-28 supersedes conflicting initial recommendations.

| ID | Decision | Disposition |
| --- | --- | --- |
| D01 | Operation completion | Selected: culvert batch completion and entire selected WEPP workflow, not submission/orchestrator completion. Option A selected: operation.completed plus explicit execution_status; domain results fetched separately. Failure/cancel precedence still needs specification. |
| D02 | Reliability | Selected direction: short bounded delivery and limited transient retries, documented for consumers. Exact capture/recovery/loss guarantees remain open; no promise of guaranteed receipt. |
| D03 | Consumer API | Selected: webhook URL supplied with the operation submission. No mandatory endpoint registration or separate subscription call. Exact field/response/error contract remains to specify. |
| D04 | Delivery authority | Selected: accepting the authenticated submission authorizes its callback; subsequent token expiry must not suppress delivery. No recurring token-validity gate. |
| D05 | Destination admission | Selected: freely supplied HTTPS URLs with auditability and ability to tighten policy later. No challenge/operator allowlist. Baseline SSRF/TLS/redirect controls remain proposed safeguards. |
| D06 | Signing | Operator questioned necessity. Remove mandatory key-management infrastructure from scope; unsigned versus optional/required signature remains a separate decision. Never reuse/forward API bearer tokens. |
| D07 | General mechanism and placement | Selected constraint: no blocking normal computation; maximize consumer flexibility/minimize regression. Selected clarification: generic hierarchical terminal detection, not per-workflow finalizer adapters; use shared enqueue/lineage and dependency semantics with independent delivery. Observer-first prescription withdrawn. Exact placement/storage remains open. |
| D08 | Numeric policy | Operator suggested approximately 10 seconds per attempt. Total deadline, retry classes/count/backoff, retention, quotas and audit bounds need final specification/ADR. |
| D09 | Recovery and audit | Audit required. Specify pending intent/event/attempt recovery and emergency pause. History/replay/endpoint-management APIs are not required by current scope. |
| D10 | Checkpoint/execution | Scaffold committed at 07dbb1452. Revised canonical contract, operator approval of exact matrix, two contract reviews and standalone ancestor commit still required; no runtime restart/implementation authority inferred. |

## Decision rationale and provenance

2026-10-28 user: clients hooking a culvert job want the batch to complete; clients
hooking running WEPP want the entire workflow. Submission notifications add little
value. User specified a webhook URL with submission, honoring it after token expiry,
freely supplied HTTPS URLs with auditing, and independent delivery with short timeout
and limited retries. User rejected the complexity of ongoing authorization and
questioned mandatory secret storage and an observer-first architecture.

Subsequent operator clarification requires generic terminal detection for
hierarchical jobs. Prefer a uniform submission option and a shared hierarchy
evaluator using root membership and actual dependency semantics. Existing culvert
and WEPP pipelines are test cases, not distinct completion adapters. Final-job success alone is insufficient
for partial culvert failure; final-job absence/deferred state must not lose failed
WEPP operation notifications. These are explicit acceptance cases, not authority
to redesign task graphs.

The [current draft](../../../dev-notes/rq-webhooks-contract-draft.md) records the
revised proposal. The [2026-10-27 review](../../../dev-notes/rq-webhooks-draft-review-20261027.md)
is historical design review, not approval of this changed scope. Preserve its
noninterference/idempotency tests; reevaluate superseded policy recommendations.

## Remaining checkpoint work

2026-10-28: operator agreed to generic failure-known versus settled semantics.
HC-03 decision closed by the operator at 2026-10-28 18:20 UTC: "option a is
appropriate." Adopt `operation.completed` and explicit `execution_status`, with
no domain outcome inference or batch summary in the generic callback. Clients
retrieve domain results through existing APIs. Rationale: smallest generic change,
low regression risk and no new task-reporting convention. Option B (generic
reported domain outcome) is deferred, not an implementation prerequisite.

The [hierarchy review](20261028_hierarchy_review.md) retains its original finding
and review history; the operator decision resolves the semantic choice. Remaining
proof obligations cover producer closure, event-commit races, independent evaluation,
safe lineage, recording/playback and mixed-instrumentation activation. Test caught
culvert failure explicitly: execution can finish while the domain API reports a
failed run, with no all-runs-success claim in the callback.

Specify remaining execution failure/cancel precedence and payload details, callback admission failures,
generic hierarchy membership/settled predicate, independent delivery placement, persistence/crash recovery,
audit access/retention, SSRF policy, signing decision and numeric policies. Record
approval and rationale in current canonical contracts and the dated checkpoint.
Do not treat the suggested timeout as a silently adopted final default.

## Concrete checkpoint proposal (2026-10-28 kickoff execution)

D01–D10 now have concrete recommendations in the
[dated matrix](20261028_contract_decision.md#Recommendations-D01–D10), with the
[current proposed contract](../../../schemas/rq-webhook-contract.md) and
[ADR-0109](../../../adrs/ADR-0109-rq-webhook-bounds.md). Earlier “open” entries above
record decision provenance; exact recommendations are now prepared but unratified.
Do not treat a recommendation as accepted product direction. Independent review
and exact operator approval/commit authority remain checkpoint gates.

## Operator ratification (2026-10-28 19:56 UTC)

Operator: "decision matrix is approved. authority grants are authorized".
RQ-WH-01 exact matrix and ADR-0109 are accepted. Package commit and scoped local
implementation/integration/restart authority are granted; production deployment
remains excluded. Earlier pending-approval entries above are historical and
superseded. Create the standalone checkpoint ancestor before implementation edits.
