# PF-R02 implementation budget correction

Base:57e60aae9; ancestor166c8f79d defines the unchanged producer/proof contract.
This amendment changes measured performance acceptance only, before release.
Operator authority remains execution of this package and its measured bounded
implementation choices. No scientific parameter or user behavior changes.

The prototype used generic file access and omitted required strict post-fire
path traversal. Actual full predicate failed5ms settled and the large eviction
case failed40ms. Those failures remain in the implementation QA artifacts.
Profiles attribute46–49% of initial time to fourteen descriptor opens. Reusing
one parent descriptor within the call reduced that to eight opens and settled
means5.82/6.98ms; independent security probes verify replacement with hardlinked
leaves, denied directories/leaves, symlinks and descriptor closure.

Correct the representative warm-NFS component means to<=10ms settled and<=50ms
cold/evicted; keep zero settled payload reads and<=1.5s export/<=200ms overhead.
The predicate executes once per normal state check, at most twice for differing
historical selections. Added allowed latency relative to the initial budget is
therefore5–10ms, while earlier full-state measurements are213–695ms. This is a
comparison, not current full-state/runtime acceptance. Required access checks
outweigh an unproven extra cache or permission change for2ms.

Independent correctness, security and QA reviewers ratify this correction; see
`cli_lineage_parent_reuse_correctness_review.md`,
`cli_lineage_parent_reuse_security_review.md` and
`cli_lineage_performance_contract_qa.md`. Final actual budget_revision measurements
pass: settled4.85/6.14ms, cold/admission maxima13.79/26.35ms and actual512-entry
eviction means14.69/27.86ms. Full settled exports394/876ms, added56/66ms. Both
producers retain exact native rows/types and output permissions; all settled
checks reread zero CLI bytes. `cli_lineage_budget_acceptance.json` records the
explicit revised gate. Original5/40-ms failures remain unchanged. Runtime and
whole-package gates remain open; this is scoped performance acceptance.
