# Generic hierarchy draft review and disposition

Date: 2026-10-28. Scope: revised webhook draft and implementation acceptance plan,
not implementation or canonical checkpoint approval. Independent read-only agents:
`hierarchy_correctness` (reviewer), `hierarchy_security` (security_reviewer), and
`hierarchy_operations` (ops_security_control_agent).

The operator agreed to separate failure-known from settlement, including batches
that continue after child failure and strict chains whose descendants cannot run.
Per-submission HTTPS URLs, accepted callbacks surviving token expiry and generic
hierarchy evaluation remain fixed scope. Reviews did not reinstate registration,
destination challenges, recurring token validation or mandatory key infrastructure.

## Findings

| ID | Severity | Finding and evidence | Author disposition |
| --- | --- | --- | --- |
| HC-01 | High | Terminal RQ status/task return does not prove producer closure: callbacks can enqueue and canceled work can remain alive. RQ worker lifecycle and `_query_catalog_admission.py:execution_uncertain` demonstrate the distinction. | Accepted; draft requires callback/enqueue closure and execution-exit evidence where ambiguous. Plan adds delayed-callback and canceled-live-producer tests. Addressed in draft; implementation proof pending. |
| HC-02 | Medium | Logical blocked status cannot satisfy allow_failure. A failed -> B strict/deferred -> C allow_failure leaves C unexecutable. | Accepted; draft/plan explicitly pair transitive blocked and directly failure-tolerant cases, with stopped/canceled helper exceptions. No RQ mutation authorized. |
| HC-03 | High | Culvert tasks catch failures and return "failed" normally (`culvert_rq.py`), so all RQ jobs can finish despite failed runs. Promised operation status and deferred domain-outcome convention conflict. | Initially OPEN at independent re-review. CLOSED as a contract decision by operator selection of Option A on 2026-10-28 18:20 UTC: operation.completed with explicit execution_status; domain results retrieved separately. Caught culvert failure acceptance remains mandatory. No domain-success inference or per-domain detector. Runtime proof pending. |
| HC-04 | Medium | Snapshot validation followed by unconditional unique event insertion permits stale completion after membership/retry changes. | Accepted; condition event commit on the same revision, producer closure and state generation; conflict reevaluates. Plan adds barrier-controlled concurrent-change tests. |
| HS-01 | Medium | Existing metadata/child references do not establish who may bind root/parent/destination; unqualified reuse could include foreign jobs or redirect callbacks. | Accepted; admission binds server-owned identities/destination, descendants inherit immutable opaque reference, membership validated. Tests cover spoofed/cross-client/conflicting lineage. Prospective design risk, not a demonstrated current exploit. |
| HS-02 | Medium | Profile recorder does not classify webhook_url as sensitive; dry-run/playback can disclose or resend a recorded URL. | Accepted; entire URL sensitive outside restricted intent, sanitized-host/fingerprint audit, recorder/playback and artifact inventory. Tests prove no raw URL disclosure or unintended callback during replay. |
| HO-01 | Medium | Milestone 1 still allowed immediate failure notification contrary to agreed settlement rule. | Accepted; removed stale choice. Failure can be known internally, but terminal notification waits for settlement. |
| HO-02 | High | Recursive root evaluation inside each worker completion could block tasking or cause quadratic Redis work despite independent HTTP. | Accepted; only bounded bookkeeping/signaling computation-side, independent or demonstrably bounded incremental evaluation, no computation locks. Added contention/storage-failure/evaluator-crash and large-batch latency tests. |
| HO-03 | Medium | Unknown/missing membership could remain unresolved forever with no audit resolution. | Accepted; require published evaluation/retention window, minimal surviving evidence and audited outcome_unavailable state distinct from task failure. Numbers remain open; no consumer history API required. |
| HO-04 | Medium | Mixed instrumentation during activation/rollback could silently omit children. | Accepted; verify all supported producer/worker coverage before admission, reject unsupported callback requests before enqueue or retain explicit incomplete tracking, preserve accepted work across rollback. Added mixed-rollout/child-creation tests. |

## Amended locations and outstanding scope

[Current draft](../../../dev-notes/rq-webhooks-contract-draft.md): Client-facing
contract, Consumer payload and identity proposal, Generalizable implementation
proposal, Reliability and audit proposal, Implementation plan and acceptance.
[Active plan](../prompts/active/implementation_execplan.md): Milestone 1 and
Validation and Acceptance, plus review disposition.

Nine findings have drafting remedies; HC-03 was an open high-severity semantic
decision at independent re-review, not a deployed vulnerability. The operator
subsequently selected Option A, closing that decision as recorded below. Independent re-review verified
the nine drafting remedies. Numeric limits, signing, storage/execution placement and exact wire
contract remain pending. The operator's agreement to generic settlement does not
ratify those choices. Final canonical review and implementation acceptance remain
separate gates.

## Re-review and validation

All three reviewers confirmed their drafting remedies on re-review. Correctness
confirmed HC-01, HC-02 and HC-04 addressed and HC-03 accurately OPEN. Security
confirmed HS-01/HS-02 addressed; operations confirmed HO-01 through HO-04 addressed.
No residual drafting gaps were reported for those nine findings. All withheld
implementation and canonical-contract approval.

The five package Markdown documents and current draft passed scoped `wctl doc-lint`
with zero errors/warnings. Spelling previews showed no differences and
`git diff --check` passed. No runtime changes or acceptance tests were performed
in this drafting review.

## Subsequent operator decision: Option A

2026-10-28 18:20 UTC: operator stated "option a is appropriate" after comparing
execution/domain separation against a generic task-reported outcome convention.
HC-03 is closed at the decision stage. The updated draft and acceptance plan require
operation.completed with explicit execution_status and separate domain-result
retrieval. A caught culvert failure can coexist with finished execution; the
callback must not assert all-runs success. No runtime verification or new independent
canonical-contract approval is claimed by this decision update.
