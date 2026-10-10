# Independent contract reviews and disposition

Date: 2026-10-10 UTC. Scope: preimplementation contract checkpoint only.
Both reviewers were independent read-only agents; neither authored amendments.
Primary author/disposition: Codex root agent.

## Correctness review

Reviewer: `/root/contract_correctness` (reviewer role).
Initial decision: changes required.

Medium finding: unspecified completion/legacy precedence could mistake a modern
rerun's empty state and stale files for completed legacy output. Resolved by
explicit output/READONLY modern completion evidence, distinct absent/empty
metadata rules, and precedence for available current-attempt evidence.

Related guidance incorporated: scoped event/rank datasets and readable Wepp
state define readiness; comparison calls bypass memoization; warmed-cache
method/interval tests and child no-events behavior are required.

Post-fix confirmation: “Approved: medium finding resolved.” Reviewer confirmed
no unresolved medium/high correctness findings. Legacy/restored discovery,
incomplete reruns, actual HTML/CSV agreement, and shared-input links still
require implementation evidence.

## Security review

Reviewer: `/root/contract_security` (security_reviewer role).
Initial decision: changes required.

Medium completion finding resolved by the same explicit completion/readiness
rules. Medium containment finding resolved by anchoring the scenario root
inside the authorized project, protecting child state/output paths, allowing
normal shared parent inputs, and requiring direct escape/noninterference tests.

Low CSV residual addressed by restricting accepted names to definition-generated
enum-prefixed names and requiring a formula-label injection regression. No
shared serializer or numeric-cell behavior changes are authorized.

Post-fix confirmation: “Approved for the contract checkpoint.” Reviewer
confirmed both medium findings resolved and no unresolved medium/high contract
findings. Dedicated implementation security review and evidence remain required.

## Disposition and remaining gate

All contract findings resolved and independently confirmed after amendments.
Documentation lint passes for the contract and package. Production code and
tests remain unchanged. Commit authority is still required for the standalone
ancestor; neither review is implementation or deployment approval.
