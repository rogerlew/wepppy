# Contract decision draft: RUPC-01

**Status:** Proposed scaffold; not a ratified checkpoint.
**Recorded:** 2026-11-17 17:45 UTC
**Starting revision:** `e4eafdd3e2115c527bf30e56b0fbae9f59ec3a57`
**Classification:** Intended scientific behavior change; not merely conformance repair.

## Authority and provenance

Venue: this Codex conversation, 2026-11-17; participants: Roger Lew and Codex.
Roger agreed to replace the 60% rule, preserve total hillslope area, preserve road
area if possible, and explicitly defer switchbacks/flowpath walking because the
model is intentionally simplified. Roger requested a contract-first scaffold and
then directed: “scope tests to the implementation changes.” These approve the
scope and test boundary, not unspecified formulas, implementation, or deployment.
Marta is the affected user, not a recorded participant in the design decision.

## Canonical contract inventory and proposed delta

Paths below are repository-relative. Review all applicable sections together.

| Contract | Required treatment before implementation |
| --- | --- |
| `wepppy/nodb/mods/roads/specification.md`, Step-4 and segment utility sections | Replace 60% gate; separate unrutted preparation from downhill splitting; define simplified strip accounting and road-area objective; reconcile existing monotonicity wording. |
| `docs/schemas/roads-parameterization-baseline-contract.md` | Reconcile geometry transforms and area effects; preserve unrelated soil/management defaults and retained baseline ownership. |
| `docs/schemas/roads-settings-contract.md` | Specify additive diagnostics, project reload, configuration identity and explanatory limitation text where affected. |
| `docs/schemas/roads-preparation-lifecycle-contract.md` | Define preparation invalidation, retained artifacts, retries, archive/restore, and readiness for changed geometry. |
| `docs/schemas/roads-water-accounting-contract.md` | Preserve full native source areas, zero-contributor baseline-equivalent success and WAT/PASS reconciliation; explicitly separate pre-execution width allocation from response weighting. |
| `docs/schemas/roads-segment-loss-summary-contract.md` | Preserve source-qualified profile summaries and unmatched/empty diagnostic semantics; new geometry fields are additive. |
| `docs/schemas/output-scope-contract.md` | Preserve baseline versus Roads output ownership and original hillslope replacement semantics. |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | Preserve existing lock/cache/mutation semantics; no exemption. |
| `docs/schemas/rq-response-contract.md` | Preserve job/error envelope; define domain errors without queue rewiring. |
| `docs/standards/artifact-observability-standard.md` | Retain inspectable geometry/accounting/provenance, failures, and results through existing project tools. |

Amend affected contracts outside this package; unchanged contracts receive an
explicit no-delta disposition. Canonical amendments must say conformance is
pending. The draft here does not supersede the current production specification.

## Concrete proposed delta

The proposed current contract is `docs/schemas/roads-unrutted-strip-contract.md`,
with scientific rationale in `docs/adrs/ADR-0146-unrutted-partial-crossing-strips.md`.
It specifies transverse physical-width road OFEs at 4%, proportional strip width
compression when needed, explicit road-area loss, total hillslope-area closure,
mandatory equivalent connected-geometry normalization, and native input readback.
It preserves the 10 m overlap minimum, three-crossing cap, small-remainder absorption,
required fill/buffer attributes, other road regimes and native WAT/PASS accounting.
No-road partitioning is a measured diagnostic, not an invented equivalence threshold.

## Approval still required

Roger authorized proceeding with the package and mutation/forking on forest.
The exact geometry formula replacement is pending the asynchronous question
presented in this turn. No implementation edits have been made. Upon ratification,
record the response, mark current amendments accepted/conformance pending, and
commit the complete reviewed checkpoint before implementation.

## Compatibility, security and regression

Use the package compatibility plan and acceptance matrix. Keep original IDs,
external schemas and other designs stable; no user-visible key removal. Security
triage is high for planned native/file handling; dedicated review required.
The parameterization ADR must record decision owner Roger Lew, actual implementer,
venue, alternatives, scientific limits, evidence, and rollback triggers.

## Ratification and checkpoint receipt

Exact formula approval: pending. ADR-0146 drafted. Independent review B passed
after three findings were resolved; review A also passed after all four findings
were resolved. See
`20261117_contract_reviews.md` for disposition. Checkpoint ancestor commit pending
ratification; operator “proceed” authorizes execution of the plan and its checkpoint
commit sequence. No implementation may precede that committed checkpoint.

## Operator ratification — 2026-11-17 UTC

Roger Lew: “i approve. proceed with implementation”. The approved proposal is
physical road width as OFE length at 4% slope, overlap-based strip widths with
proportional compression and visible road-area loss, conserved total hillslope
area, and retained 10 m minimum/three-crossing cap. Both independent reviews pass.
This supersedes the pending-approval status above; checkpoint commit is next.

## RUPC-02 follow-up checkpoint

The operator authorized a top-placement amendment on 2026-11-17, after RUPC-01
implementation. See [the incremental decision and review record](20261117_top_placement_contract.md).
It supersedes only the identified placement/area-adjustment/lifecycle rules;
original reviews and implementation receipts do not validate the new behavior.
