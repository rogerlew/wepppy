# Contract checkpoint: per-run culvert pruning

Base implementation revision: `7755822d78f79a5830c0d85d1319dfe83c40568e`.
Checkpoint revision: pending standalone commit; implementation not started.

## Approval and normative delta

Operator explicitly requested per-run selection: nominal1m starts at4, then3,2,1,
zero as fallbacks; similar schemes for2/4/8/10m, preferring simplicity for
performance. Proposed concrete mapping is4/3/2/1/1 with upper effective-resolution
boundaries1.5/3/6m. Require point intersection plus polygon coverage, not merely
coverage. Details: `docs/schemas/culvert-stream-selection-contract.md` and ADR-0144.
This is an intended behavior change, not a conformance repair.

## Contract inventory and scope

Affected domain authority: new stream-selection contract and culvert integration
specification. Shared NoDb persistence/concurrency and RQ response contracts remain
unchanged. Exact source scope: RQ batch candidate generation, helper mapping,
CulvertsRunner candidate selection, upload-time internal policy marker, additive
manifest/receipt and targeted tests. The route change only persists internal policy
intent; its endpoint, payload and response contracts do not change.
Exclude queues, auth, dependencies, DEM resampling, re-extraction, unrelated runs.

## Compatibility and regression plan

New policy is identified by an admission-time versioned intent marker independent
of the candidate manifest. Missing markers on retained batches mean legacy behavior;
a present marker with absent/incomplete manifest is an explicit preparation error. Fixed/explicit
pass overrides become starting maxima, with zero selecting original streams.
Retain summary keys and use canonical NoDb locks/cache invalidation for state
mutations. Preserve working unrelated behavior and existing route/error envelopes.
Test real raster intersections, matching junctions,4->3 and deeper fallback,
zero override/miss, legacy resume, partial manifest and missing files, deterministic
new-policy resume, and actual selected per-run topology. Forest RQ acceptance must
include1040 and one of the seven lost native four-pass outlets.

## Valid-state and security assessment

Valid states: new batch; fixed/map/explicit count; selected high or lower candidate;
legacy batch without manifest; complete new-policy resume. Invalid states:
malformed/partial manifest, missing raster, grid mismatch, no eligible unpruned
network. Do not mask infrastructure/data errors as finer-network selection.
Security impact low: internal artifact policy only; no new endpoint, privilege,
identity, or trust boundary. Existing run/payload authorization remains mandatory.

## Reviews and disposition

Two independent read-only reviews approved: `per-run-contract-correctness-review.md`
and `per-run-contract-scope-review.md`. All medium findings resolved. Commit
authority is the remaining checkpoint gate; no new implementation edits before
the standalone ancestor.

Review disposition: corrected configured/map precedence; added independent admission
intent marker, atomic preparing/ready/failed publication, immutable ready artifacts,
and concrete visible artifact/archive/restore obligations. Both reviewers approved the amended checkpoint. Manifest/receipt evidence without
a valid intent marker explicitly fails integrity checks rather than becoming legacy.
