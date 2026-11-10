# Contract decision — Declarative DEM vertical slice

**Status**: Preparation scaffold; not ratified, reviewed or committed

**Date**: 2026-11-10 20:18 UTC

**Starting source revision**: `da14ef8b16c6b51b672a0b1396e110aa6c866826` (working tree includes unrelated changes)

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
