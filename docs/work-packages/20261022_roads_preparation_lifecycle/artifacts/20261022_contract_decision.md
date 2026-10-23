# Contract decision checkpoint

Status: draft; implementation prohibited until independent approvals and commit.
Starting revision: c3ac573e3. Operator: Roger, task conversation 2026-10-22.
Approval: upstream replacement/invalidation contract approved; explicit request to
scaffold and execute implementation. Prior task-scoped commit authority persists.

Canonical contracts: roads-preparation-lifecycle-contract, output-scope-contract,
roads-segment-loss-summary-contract, Roads module specification. Existing NoDb,
artifact observability/validation and RQ error/locking contracts remain constraints.

Delta: invalidate all previous current Roads results before replacing segments or
accepted model inputs; fresh successful run alone restores current eligibility.
Repeated parent segment IDs in profile rows remain valid; geometry/profile primary
keys remain unique within their sets. No stable-ID repair or beta admission fallback.
Discrepancy: intended behavior change with known current-code gaps, not a numerical
model repair. Security high: retained-history moves and shared read/publication gates.
Compatibility: no beta migration; diagnostic historical files remain inspectable.
No original UM1 mutation, deployment, native changes or new dashboard layer.

Concrete publication/retention paths and concurrency mechanisms are being finalized
from source inspection before review. Regression evidence must cover actual filesystem
transitions, direct readers with stale catalog/cache state, run failure/retry, preserved
baseline and archived history under the existing container identity.

## Concrete checkpoint delta

The canonical lifecycle's implementation admission/retention section now specifies
roads.current.json (roads_current_v1), project-root persistent flock coordination,
visible history snapshots, final publication order, all direct reader classes,
nonblocking 409 domain errors, no-store and bounded client invalidation behavior.
Output-scope canonical contract is amended for retained-history paths/current gates.
This uses existing filesystem/JSON/flock infrastructure and adds no dependency.

Writer lock covers direct controller mutations as well as RQ calls. Removal of the receipt from the current namespace (retained in history)
precedes any source overwrite; publication is last after completed state and output
readback. Read locks cover actual consumption, including lazy DuckDB and deferred
HTTP body streaming. Archive/restore shares the lock and preserves its inode.
No stable-ID reconciliation or geometry-generation token is introduced.

Initial independent findings: mutation-only RQ locks are insufficient; stale query
plans and logical-to-history aliases need actual-read checks; lazy HTTP/DuckDB reads
need full consumption locks; archive restore must preserve the coordination inode;
NoDb completion must precede receipt; synthetic remainder IDs need explicit handling.
All are incorporated as contract obligations before runtime edits. Final independent
review approval and standalone ancestor commit are still required.

Additional applicable amendment: roads-water-accounting-contract current-admission
precedence. Diagnostic rules explicitly preserve prepared geometry and lifecycle
logs while active output is exclusively locked; failed/partial outputs move to
visible history. Archive failure revokes extracted receipts before unlocking.
The existing segment-detail dictionary is not suitable for multi-profile identity
validation; raw manifest list validation is required.

Independent review identified the external Roads hillslope water-balance cache,
sidecar and attempts tree under wepp/reports/cache. Canonical inventory now includes
those exact paths for retention/admission; baseline cache siblings remain untouched.

## Final disposition

Both independent reviews approve the final canonical lifecycle hash
8d1ff31251de6b8223bf0e7f549cbaefb330a65e698c64017ec780e682494e67,
with no unresolved high/medium findings. Earlier draft/pending statements above
record checkpoint development; the decision is now accepted for standalone commit.
No runtime files were edited before these approvals. The review-bound canonical
contract is unchanged by this disposition note.
