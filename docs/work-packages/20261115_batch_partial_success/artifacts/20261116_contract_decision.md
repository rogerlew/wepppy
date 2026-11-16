# BATCH-OUTCOME-01 draft contract decision

Date: 2026-11-16 06:13 UTC. Status: proposed; not ratified or implemented.
Base revision: `df8b5249c70a3d98fd27f2b3b3b16ac1d96deb52`.

## Intent and rationale

An RQ tree may be failed while its batch has useful results. Add `batch` on enrolled root jobinfo and jobstatus responses; keep existing top-level status and child exception semantics. The user requested scaffolding this direction for ordinary batch and culvert. Exact schema approval, independent reviews, canonical promotion, and checkpoint commit remain pending. This is an intended contract addition, not conformance to an unchanged contract.

## M1 concrete proposal and authority

The exact proposed contract is [Batch result outcomes](../../../schemas/batch-outcome-contract.md).
It supersedes the illustrative payload below for field types and semantics.
Source/consumer inventory and the compatibility/regression plan are retained in
[20261116_inventory.md](20261116_inventory.md). Applicable contracts are RQ
response/webhook, batch task boundary, feature-access projections, existing browse
access/containment, NoDb persistence and artifact observability/validation.
Canonical RQ response, webhook and batch task boundary amendments are marked
proposed; no conformance claim is made.

The 2026-11-16 user instruction to execute this package authorizes inventory,
proposal preparation and required independent reviews. Newly specified choices
not settled by the scaffold are baseline-WEPP-only derivative ZIPs, selected-only
ordinary cohorts, prep-only skips, explicit-finalize source receipts, non-expiring
leaf identity retention, bounded blocked-Omni reconciliation, and a narrow
poll-triggered terminal-failure persistence exception. Exact operator ratification
of these concrete choices remains pending. This record does not manufacture it.
Implementation has not started; the required ancestor has not been committed.

This is a normative addition, not a conformance fix. Existing unrelated dirty
contract and project-board changes are preserved. The checkpoint commit must
include only this package's hunks in those shared files. Implementation gates
include direct output/readiness validation, both workflows and the real external
client; deployment and production requeue remain excluded.

## Proposed payload

```json
{
  "status": "failed",
  "batch": {
    "state": "completed",
    "outcome": "partial_success",
    "succeeded": 32,
    "failed": 1,
    "skipped": 0,
    "results_available": true,
    "download_url": "<existing authorized artifact route>"
  }
}
```

Proposed states: `running`, `finalizing`, `completed`, and `failed` for finalization/publication failure. Outcome is null before settlement, otherwise `success`, `partial_success`, or `failed`. Counts describe selected logical runs, not orchestration jobs. Terminal counts partition that cohort. At least one validated success and no failures means success, even with skips; successes plus failures mean partial success. Zero usable runs, including empty/all-skipped selections, produce an explicit no-results reason and no download readiness. Ratify exact reason/error fields before implementation.

Finalizers publish readiness only after validating and publishing current-attempt artifacts. Download URL is null when unavailable and must never contain credentials or host paths. Resolve ordinary batch artifact representation before ratification rather than assuming a universal culvert ZIP. Keep bounded summary counts in polling; expose per-run reasons through existing authorized manifests and leaf diagnostics.

## State and regression matrix

| Case | Required result |
| --- | --- |
| Absent/legacy summary | Preserve existing response; absence never implies availability |
| Active leaves or queued/running finalizer | Nonterminal batch; results unavailable |
| All successful | Completed/success with validated results |
| 32 successful, one timeout/abandonment | Completed/partial_success; download 32; retain leaf exception |
| Caught versus uncaught application failure | Same domain outcome for equivalent failed runs |
| All 33 SSURGO failures | Failed outcome; no usable-results claim |
| Empty or all skipped | Explicit terminal no-results reason; no endless polling |
| Finalizer crash or packaging failure | Observable terminal failure; stale archive cannot imply readiness |
| Worker killed before writing metadata | Reconcile RQ state; do not infer success |
| Success marker with missing/corrupt output | Validation excludes unusable output |
| Retry or re-finalization | Attempt identity prevents stale summary/archive reuse |
| Redis expiry and archive/restore | Defined retention/inspection behavior without stale resurrection |
| Foreign batch, hostile path, restricted job | Preserve authorization, containment, and disclosure restrictions |

## Checkpoint requirements

Promote the exact schema and rationale to `docs/schemas/rq-response-contract.md`; inventory all related contracts, including webhook terminal semantics, and reconcile conflicts. Specify finalizer ownership, root lookup, atomic publication, attempt identity, retention, and observable finalizer failure. Preserve unrelated job payloads, auth, and generic RQ aggregation. Legacy clients still reject aggregate failures, so explicitly coordinate consumer adoption.

Security impact is high. Before runtime edits, record approval, two independent read-only contract reviews, disposition, and a standalone canonical checkpoint ancestor commit. Review artifacts and approval are not manufactured by this scaffold.

## Review disposition

Two independent read-only reviews pass the concrete proposal at SHA-256
`42d00a1931ea77e862412349ff91414bfae47d3dc33dd57faf0eb6ac7f8fed92`.
See [correctness review](20261116_contract_correctness_review.md) and
[security review](20261116_contract_security_review.md). All findings were
incorporated and independently rechecked; none remain medium/high. These are
technical proposal approvals, not operator ratification or runtime evidence.

Operator approval (2026-11-16 06:31 UTC): “i approve. proceed with commit and implementation”. This ratifies the reviewed contract (pre-status-update SHA-256 `42d00a1931ea77e862412349ff91414bfae47d3dc33dd57faf0eb6ac7f8fed92`) and authorizes the standalone checkpoint and implementation commits. Runtime conformance remains pending.
