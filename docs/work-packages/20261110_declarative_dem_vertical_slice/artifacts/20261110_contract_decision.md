# Contract decision — Declarative DEM vertical slice

**Status**: M1 concrete contract independently approved; ancestor commit pending

**Date**: 2026-11-10 20:18 UTC

**Starting source revision**: `3a113ac28df9c5b2cdf453a4223e1c42e83b81bb` (working tree includes unrelated changes)

## Authority and intended delta

The user requested this package scaffold and selected open-wepp-org as the
implementation/validation environment. Accepted product direction is recorded in
`docs/schemas/declarative-model-build-spec.md`: full builds, shared RQ processing,
Git audit, operator-only submission, approved images, protected finalization,
allowed derived viewing tasks and no Bootstrap. Deferred scope includes reuse,
determinism/comparison and compatibility machinery. Scaffolding is not permission
to bypass contract-first ancestry or infrastructure live-change requirements.

## Applicable contracts

Review and amend the declarative spec, NoDb persistence/concurrency, RQ response,
query-engine catalog refresh, shared UI controller and any exact viewer contract
identified in M1. Preserve batch-task-boundary mandatory receipts. Apply artifact
observability and generated-artifact validation. Exact section changes and approved
record/write layouts must be entered here before review.

## Compatibility and security

Additive opt-in metadata; missing fields keep ordinary project behavior. No scientific
parameter default changes. New read-only derived-write permission must be bounded
by operation and owned paths, with server-side enforcement. Security impact high:
worker/image authority, queue routing, external resources and filesystem writes.
No arbitrary commands, secret selection, mount overrides or visibility widening.

## Discrepancy classification and evidence plan

New capability, not a demonstrated incident repair. Existing implementation is
baseline evidence, not authority for the new contract. Exact mismatch inventory
pending M1. Retain absent/empty/populated/legacy/hostile tests; real DEM and view
readbacks; image/task binding; failure/recovery; read-only deny/allow tests; and
normal project behavior. See `validation_matrix.md`.

## Checkpoint gate

- [ ] Exact normative amendments and compatibility matrix complete.
- [ ] Operator decisions mapped; any new policy approval recorded explicitly.
- [ ] First independent read-only contract review and disposition retained.
- [ ] Second independent read-only contract review and disposition retained.
- [ ] Standalone contract ancestor commit created with applicable commit authority.
- [ ] Revision and ancestry recorded in tracker before implementation edits.

Reviewer identities, results and checkpoint revision: **pending**. Prior architecture
reviews do not substitute for review of the concrete implementation contracts.

## Execution authority and concrete delta

On 2026-11-10 the user requested: “execute
docs/work-packages/20261110_declarative_dem_vertical_slice/ let me know when it
is ready to deploy to open-wepp-org and we can handoff the work-package”. This
authorizes package implementation and its required checkpoint commit/reviews,
with deployment and live cluster acceptance deferred to handoff. No branch switch.

The complete proposed delta is `docs/schemas/declarative-dem-v1-contract.md`.
Affected canonical contracts are linked from their new “Declarative DEM v1”
sections: NoDb persistence, RQ responses, UI controller, query-catalog refresh,
Bootstrap and the parent declarative spec. All conformance remains pending.

Exact source boundary: new `wepppy/declarative/` helpers/adapter and independent
`tools/declarative_dem.py`; shared DEM task observation in `project_rq.py`; RQ
execution guard; NoDb readonly setter; central Flask/rq-engine mutation admission;
Bootstrap API/core/transport eligibility; archive restoration protection; existing
run template presentation. Deployment worker template and operator instructions
remain in open-wepp-org. No parameterization default/formula changes.

Public source/public-project restriction is explicit: elevationquery is an existing
unauthenticated zero-write DEM consumer, not an RQ job. Its JSON is the derived
result. Do not claim private source/project coverage or add a catalog bypass.
The initial fixture retains ordinary public access plus explicit owner registration.

Compatibility plan: missing marker, present-empty provenance directory and legacy
projects remain ordinary; malformed/empty/symlinked marker rejects mutation;
populated marker binds a single nonreplayable task. Test real Git/filesystem/raster
reads and canonical archive/restore, direct/HTTP/queued protection, source failure,
identity mismatch, interruption and normal DEM/Bootstrap parity. Local evidence
cannot close cluster identity or production-equivalent workflow gates.

Preliminary independent discovery found incomplete READONLY enforcement, Bootstrap
Git writes before NoDb failure, unauthenticated elevation query, and completion-path
manifest ordering. The concrete contract addresses these by additive declarative
guards, public-only admission, zero-write viewing, and creating the build-record
path before finalization. Formal reviews and dispositions follow.

## Independent review disposition

Both reviewers approved the revised contract after all four medium/high findings
were resolved; see [contract reviews](20261110_contract_reviews.md). Runtime and
final implementation approval remain pending.
