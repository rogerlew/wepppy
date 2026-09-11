# Correctness review — batch task boundary

## Scope and authority

Reviewer: `/root/contract_correctness` (independent read-only reviewer),
2026-09-11. Source baseline `0c34afdb5`; contract ancestors `869ca7dcf` and
`f221e7f2a`. Reviewed BatchRunner extraction, batch RQ chain, tests and current
canonical batch boundary contract. User goal: two observable ordered tasks on
existing workers, preserving scientific behavior, retry and terminal summary.

## Findings and disposition

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| COR-I01 | Medium | Required upstream identities could expire during queue delay | Root/hillslope successful retention is non-expiring; actual Redis TTL assertions |
| COR-I02 | Medium | Terminal timing omitted hillslope work | Upstream start anchors whole-leaf metadata; 120-second regression |
| COR-I03 | Medium | Omni could be dispatched before attachment lock failed | Intent published before dispatch; failed attachment retains pending flag and prevents false completion |
| COR-I04 | Medium | Attachment lock enclosed synchronous Omni science | Two short metadata-only lock sections; dispatch outside; multiprocessing barrier regression |

All four findings independently confirmed resolved. No additional scientific
ordering regression found. The compatibility wrapper has a concrete standalone
WATAR evidence caller; RQ uses only the two phase APIs.

## State and boundary evidence

Runtime states and directive combinations are enumerated separately in
`docs/schemas/batch-task-boundary-contract.md`. Tests cover absent/partial and
legacy complete leaves, disabled/already-completed tasks, WATAR-only reuse,
valid and malformed handoffs, foreign task identity, cancellation, duplicate
submission, mixed outcomes, root/stage failure and retry, concurrent Omni, and
archive/restore. Direct NoDb evidence defeats stale memory/Redis payloads with
same-size/same-mtime disk state and preserves unrelated cache/foreign locks.
Actual `WepppyRqWorker` tests verify distinct work-horse processes and identity.

The live zero-science fixture uses explicit full rerun. Existing timestamp
precedence can classify its failed metadata as stale/complete; reviewer
confirmed this is preserved behavior, not a reason to redesign retry selection.
Normal retry/partial-output evidence comes from the separate regression suite.

## Verdict

Code review approved; zero unresolved high/medium findings. Review is based on
source/test inspection and primary-agent test reports. Reviewer did not
independently rerun tests. Full-suite and live Forest/browser evidence remain
package acceptance gates, recorded separately in validation/integration artifacts.

## Final acceptance review

The same independent reviewer approved the final Forest and validation
artifacts on 2026-09-11: zero open high/medium findings. Actual separate-stage
execution, safe failure/full-rerun, authenticated byte-parity downloads and
empty test registries close the deployment gates. Publication remains pending.
