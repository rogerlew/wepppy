# Omni thinning 30% and 50%

Status: active, 2026-09-20 19:32 UTC. Owner: requesting operator; implementer: Codex.

## Scope and success criteria

Add 30% and 50% target canopy to Omni thinning, each with existing ground covers
75%, 85%, 90%, 93%. Preserve 40% default, 40%/65% choices, legacy files, mapping
IDs, treatment eligibility, soil behavior, and existing saved runs. Eight new
management files derive from corresponding 40% files by changing canopy alone.
Extend the five catalogs that already contain these thinning treatments; retain
all existing entries. No template refactor, migration, new dependency, queue,
service, deployment or production run mutation. Complexity budget: eight static
assets, additive catalog records, bounded selector/default logic and evidence.

## Compatibility and regression plan

No payload or NoDb schema changes. Existing percent strings and scenario names
remain valid. Allocate unused IDs without renumbering entries. Compare original
entries/files with starting revision; parse new files and compare all other
numerical parameters with their 40% sources. Exercise UI default/hydration and
real management serialization, MOFE synthesis and prepared management readback.
Run frontend lint/tests and full Python suite. New choices become available on
updated installations; saved outputs are not rewritten.

## Governance

Canonical intent: [thinning contract](../../ui-docs/contracts/omni-thinning-contract.md).
Parameterization: [ADR-0071](../../adrs/ADR-0071-omni-thinning-30-50.md).
Security impact: none; no attack-surface change or dedicated security review.
Two independent contract reviews and a standalone ancestor checkpoint precede
implementation under the contract-first standard. Operator authorized scaffolding
and executing this work package in the workspace conversation.

## Generated artifact validation

Use existing thinning layout: landuse managements and `wepp/runs/*.man`, with
existing browse/archive behavior. No writer/storage/lifecycle changes. Validate
new selections through actual parser/writer and preparation boundaries in local
fixtures. Fresh model results and live browser/deployment acceptance are outside
this code-delivery scope; no numerical-output or deployed claim will be made.
Highest current claim: scoped. Evidence and any unavailable gates go in tracker
and correctness review.

## Archive and inspection evidence

Archived/restored runs are supported states: preserve new/legacy selections and
management bytes at existing landuse and prepared-input paths. Exercise the
canonical project archive/restore implementation with these files and compare
restored bytes. Run existing browse/download coverage. Live browser/download
acceptance remains explicitly unverified unless exercised; operator owns that
pre-deployment gate. Local code-delivery closure must state this limitation.
