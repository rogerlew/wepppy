# WRT-01 independent implementation correctness review

Reviewer: independent Codex correctness agent. Date: 2026-09-28.
Contract ancestor: `728965382`.
Final disposition: **approved; no unresolved correctness findings**.
Initial review requested the bounded parser correction documented below.

Reviewed new `watershed_timeout.py` and its tests, all four changed pipeline
entry points, metadata merging, owned run-file generators, existing dependency
assertions and new state-matrix tests. No runtime files edited by reviewer.

## Finding C1: insufficient structural evidence for prepared workload

Medium priority. `_prepared_workload` checks only mode records, a count position,
and the final numeric record. A truncated seven-record file containing
`M`, `Yes`, `1`, `2`, `1908`, `garbage`, `1000` is accepted as a 27-hour workload.
The reviewer reproduced acceptance directly against the current implementation.
An extra trailing integer similarly replaces the actual years for budgeting.
This does not establish that the number was the native simulation-years record
and violates WRT-01's rejection of malformed required prepared workload.

Requested bounded correction: validate enough owned-layout structure to locate
the declared hillslope block and final simulation-years record, preserving
legacy/modern prompts and variable output choices. Reject truncated and extra
trailing numeric records before child enqueue. Do not expand into validating
all native inputs, changing input files, or a general WEPP parser.

## Verified correct

- Integer arithmetic implements exact whole-hour ceiling and preserves both
  the 12-hour floor and larger supplied pipeline allowance; range is explicit.
- Preparation uses controller workload, while no-preparation reads only the
  checked-out file for workload. File reads are bounded and non-mutating.
- All four applicable entry points calculate before their first child enqueue.
  Hillslope-only and preparation-only paths avoid unused workload reads.
- Only continuous watershed leaf timeout changes. Existing dependency objects,
  task names, arguments, unrelated stage allowances and completion remain intact.
- Single-storm and batch behavior retains existing timeout without new metadata.
- Metadata merge retains fork lineage and failure callback without mutating the
  parent's lineage dictionary. Existing optional absence stays valid.
- Tests exercise arithmetic boundaries, invalid inputs, four submission paths,
  unchanged other-stage allowances, immutable input bytes and stale controller
  values. Existing graph assertions remain in place.

## Validation limits

Owner has completed focused/RQ tests and disposable Redis acceptance; full
repository regression remains in progress. Native model code is unchanged.
This review does not substitute for those pending execution gates or claim
production rollout.

## C1 resolution and final review

Owner added an owned-layout hillslope-block extent check, each expected `M`/`Y`
pair, the following `Yes`/`No` transition, and the generated `pw0.cli`, `pw0.sol`,
`0` tail anchors. The fixed filenames match both owned native template layouts;
arbitrary alternative run-file schemas are outside this bounded reader's scope.
No referenced paths are opened and variable output sections remain unrestricted.
New regression cases cover the seven-record truncation, extra final integer and
inflated hill count. Reviewer repeated the original C1 reproduction: it now
raises `ValueError` before metadata or child-job creation. Code review confirms
these checks close C1 without changing valid owned legacy/modern record offsets.

Final review approves implementation correctness subject to the owner's separate
execution gates. All originally listed arithmetic, pipeline, metadata and
noninterference conclusions remain unchanged.
