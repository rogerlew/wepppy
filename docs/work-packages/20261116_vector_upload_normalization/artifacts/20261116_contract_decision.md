# VUN-01 contract checkpoint

Status: ratified M0 checkpoint; standalone implementation ancestor `1aebebfe0`.
Starting revision: `05e3450fa7d3b24572e65161100670ae542a6ea8`.
Task branch: `codex/vector-upload-normalization`.
Task checkout: `/tmp/wepppy-vector-upload-normalization`.

## Authorization and finite scope

The operator explicitly requested M0–M5 execution for Roads, AgFields, Omni run
and dry-run, and Batch Runner; approved sibling Rust CLI normalization through
shape-converter; and selected Polygon/MultiPolygon-only new Batch uploads.
Culvert API, D-Tale, saved-project migration, publication and deployment are
excluded. Commit/checkpoint work is part of the authorized execution. No shared
master reset, clean or rebase is authorized.

## Canonical contract set and normative delta

| Contract | Delta / preserved obligation |
| --- | --- |
| `docs/schemas/vector-upload-normalization-contract.md` | New bounded binary profile, receiving validation, lifecycle, canonical CRS, failure safety |
| `docs/schemas/upload-endpoint-contract.md` | Amended: three binary suffixes at exactly four workflows; existing fields/caps/auth/errors retained |
| `wepppy/microservices/shape_converter/docs/specification.md` | Amended: sibling CLI, mandatory same-descriptor preflight, inspect/convert format dispatch, readiness and provenance |
| `docs/adrs/ADR-0145-geoparquet-upload-resource-bounds.md` | Accepted implementation ceilings inside ADR-0142 envelope; exact-image qualification remains M2 |
| `docs/schemas/rq-response-contract.md` | Preserve envelopes and job behavior; no queue edges or new public response schema |
| `docs/schemas/weppcloud-csrf-contract.md` | Preserve Flask CSRF and bearer/session bridge distinction |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | Preserve locks, caches and composite-operation failure rules |
| `docs/ui-docs/controller-contract.md` | Preserve controller lifecycle, hydration, error and retry behavior; tests before implementation |
| `docs/standards/artifact-observability-standard.md` | Original within-limit uploads, normalized artifacts, failed candidates and receipts are visible and archived; hostile originals are quarantined/download-only and denied to anonymous public-run access |
| `docs/standards/generated-artifact-validation-standard.md` | Actual downstream semantic readback required for every workflow/format |
| `docs/standards/dependency-evaluation-standard.md` | Exact graph conditionally accepted behind owned same-descriptor preflight; direct unpreflighted decoding rejected |

This is an intended capability change, not a conformance-only fix. Current code
is evidence of discrepancies, not authority to silently retain them. AgFields
and Omni need explicit polygon checks. Batch checks apply at new admission only.
Roads and AgFields need trusted canonical CRS context. Omni must validate before
`parse_inputs` changes saved state.

## Compatibility and regression plan

Preserve direct GeoJSON behavior except explicitly required polygon admission.
Do not migrate old resources or tighten the shared saved-collection loader.
Admit compressed binary data only within independent input, decoded and output
caps. Preserve feature order, multipart structure and scalar properties; retain
AgFields duplicate-ID warning semantics. The source and correctness matrices
name accepted files, reloaded state and downstream artifacts. Failed conversion
or receiving validation must preserve an already accepted resource and state.
Do not claim full filesystem/NoDb transactionality for later I/O failure.

## Security impact and evidence

Impact is high: hostile compressed binary input crosses a parser and service
boundary. Threat matrix, resource ADR, deterministic fixtures and exact graph
probe are checkpoint inputs. They do not prove runtime containment. The resumed
independent Daybreak review conditionally accepts the exact graph only behind
the canonical owned same-descriptor preflight. It reproduced 64 GiB and 2 GiB
allocation attempts from unpreflighted hostile declarations and rejects direct
upstream decoding. Exact-image containment remains an M2 gate.

## Review disposition and stop condition

Correctness/source, QA, operations and independent security reviews retain their
findings separately. Canonical amendments, dependency evidence and fixture
readback are prepared. No M0 acceptance or standalone implementation ancestor is
claimed until the raw-input decision is recorded and the amended canonical set
passes the required read-only contract and focused retention reviews.

The operator resolved original-input retention on 2026-11-16: users must be able
to recover complete within-limit files they submitted, and receipts must bind the
original SHA-256 to conversion provenance. Complete rejected/hostile originals
are retained for review and possible account-governance action. The canonical
contract stores them with a neutral `.upload` suffix, private modes, owner/root
authorization, public-run denial and download-only handling; it records verified
actor identity without tokens, sessions or client IP. Automatic bans and new
identity/network stores remain excluded.

Focused retention review found public-path and cumulative-storage risks. The
canonical disposition standardizes four sensitive `vector_upload_attempts` roots,
requires one cross-tool classifier plus explicit owner/root or Batch group
authorization that bypasses public-run reads, places evidence-containing archives
under `archives/private/` with hash-bound sidecars, and adopts ADR-0145 project
and shared-filesystem aggregate quotas, atomic existing-Redis reservations,
principal budgets, free-space and lock controls. Shape-converter returns source size
and SHA-256 for receiver reconciliation. Attempts have atomic working/prepared/
terminal receipts and fail-closed recovery. Structured rejected-upload security
events are bounded and follow existing log retention; project evidence is only
project/archive-lifetime evidence and does not independently authorize a ban.

The previous account-security blocker is resolved; the resumed review is retained
in `20261116_m0_dependency_security_review.md`. Focused retention correctness
re-review passed. Retention security re-review is being repeated after closure of
its explicit authorization and filesystem-wide admission findings; it remains
required before the standalone ancestor commit.

The repeated retention security review passed with no unresolved High/Medium
finding. M0 is ratified for the standalone contract ancestor. This decision does
not claim runtime, exact-image, workflow, publication or deployment acceptance.
