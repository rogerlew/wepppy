# Correctness and User-Experience Review — Portland combined viewer

## Metadata

Prepared: 2026-10-12 08:21 UTC. Reviewer: unassigned, independent. Scope: collection/generator workflow and legacy artifact-to-map path. Starting revision: `dc6f3879e3372fa35062708b2c2f0caeb7eba18e`; candidate/accepted contract revisions: pending. Related: [security review](2026-10-12_security_review.md), [decision draft](2026-10-12_contract_decision.md).

## User Outcome

A PortlandGroup member opens existing collection links and gets a populated, numerically correct map with preserved units, ranges, title, and drilldown. Missing required data produces an actionable failure; missing optional data does not block supported variables. Never present silently skipped watersheds as complete success. Exact error contracts remain an M0 checkpoint deliverable.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Empty generator entry | Yes | Display usable form | Pending |
| Required artifact absent | Supported legacy/readiness state | Prepare offline; explicit readiness error until available | Pending |
| Optional phosphorus absent | Yes | Preserve other variables; clearly indicate availability | Pending |
| Populated modern artifacts | Yes | Correct per-run values and geometry joins | Pending |
| Legacy output without Parquet | Yes | Additive verified conversion, no silent zero map | Pending |
| Malformed IDs/JSON or hostile title/path | No | Bounded safe error, no unauthorized metadata | Pending |

Input/identity matrix is separate: member, removed member, nonmember, anonymous, independent public/owner/admin grants, mixed authorized/unauthorized runs, duplicate run IDs, variable/unit/range combinations, stale config strings, and share/reload. Reviewer must name covered dimensions and any exclusions.

## User-Reachable Error Policy

| Condition | Classification | Required result | Authority |
| --- | --- | --- | --- |
| Empty generator GET | Expected | Usable form | PCV-01 checkpoint to ratify |
| Invalid submitted list | Expected | Actionable validation error | PCV-01 checkpoint to ratify |
| Run lacks any valid grant | Expected | Auth-safe denial; no partial private collection | PCV-01 checkpoint to ratify |
| Required source/derived data unavailable | Expected readiness condition | Identify repair need to authorized caller | PCV-01 checkpoint to ratify |
| Converter or query failure | Exceptional | Explicit error with retained diagnostics | Existing error contracts plus PCV-01 |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| User intent | Exact old URL and nine-collection inventory | Pending manifest | Pending |
| Reloaded state | Current membership, resource association, actual config | Pending normal readers | Pending |
| Generated intermediate | Geometry/summary/interchange with preserved IDs and units | Pending checksums and semantic comparison | Pending |
| Consumed input | Exact query-engine files/catalog and selected scope | Pending query/file readback | Pending |
| Execution output | Fresh converter/query result under candidate revision | Pending transcripts | Pending |
| User-facing result | Correct map samples, units, ranges, popups, reload | Pending authenticated browser evidence | Pending |

Direct unmocked boundaries: membership/resource resolution, converter writer, query consumer, rendered collection. Actual project gate: copied Portland run, then approved production preparation and wepp1 browser checks. Highest current claim: prior diagnosis only; implementation, deployment, and repair remain outstanding. Fresh model execution is not planned because retained model output is the source; converter and query execution must still be fresh.

## Review Checks

- [ ] Accepted canonical contract and ancestor revision are identified; source behavior is not substituted for intent.
- [ ] Valid-state and input matrices have direct evidence and explicit exclusions.
- [ ] Safety/persistence boundaries are exercised unmocked, including absent optional and supported legacy states.
- [ ] Generated content, consumed rows, and rendered values agree; PUBLIC markers and original model output remain unchanged.
- [ ] Cross-run ID collisions, bounds union, special-character titles, English/SI changes, and old-URL settings pass.
- [ ] Readiness, partial failure, retry, and rollback behavior are explicit and actionable.
- [ ] Existing single-run, public, and batch workflows retain contracted behavior.
- [ ] Implemented, wired, validated, deployed, repaired, and resolved claims match evidence.

## Artifact Observability Gate

- [ ] Existing comparable conversion/export module and artifact inventory are named.
- [ ] Provenance, inputs, intermediates, outputs, and failure evidence remain visible through established authorized project tools.
- [ ] Real writer/failure retention, applicable archive/restore coverage and byte equality, and live browse/download evidence are retained.
- [ ] Any observability exception has exact scope, canonical documentation, and operator approval.

## Findings and Verdict

No independent review performed; findings unassessed. Gate status: pending (not passed). Release recommendation: hold. Record findings with ID, severity, affected state, evidence, required fix, and disposition before sign-off. Close all medium/high findings. Reviewer, date, candidate revision, and final sign-off: pending.
