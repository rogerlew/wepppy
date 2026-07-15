# Code Review - AgFields Routing Scheme Suite

Date: 2026-07-15 (UTC)

Reviewer: Codex self-review; no independent reviewer participated

Scope:

- Concept 1, Concept 2, and hybrid planning/integration collaborators
- per-scheme NoDb state, isolated publication, clear, and interrupted-job recovery
- authenticated RQ/API orchestration and serial Run All dependencies
- description-first Stage 5 UI and controller behavior
- management capacity/corpus changes and dated WEPP binaries
- wepppyo3 slope segmentation, PASS repair, and direct WAT Parquet path

The unrelated Ash Transport commit `5da847b40` and NASA summary draft are not part
of this review.

## Review Focus

- Exact scheme identifiers, default compatibility, and fixed path containment.
- Source-area ownership, closure validation, and explicit scientific limitations.
- NoDb locking, job admission, retry publication, and terminal-state integrity.
- Native input validation and management scenario capacity.
- Generated-run memory behavior and interchange schema/order parity.

## Findings

No unresolved high or medium correctness findings.

### CR-01 - Non-integer worker bounds crossed the API boundary

Severity: Medium

The initial range check accepted values that Python could coerce to integers in
the RQ layer, including booleans and fractional values. The shared validator now
requires a real integer before enforcing `1 <= max_workers <= 16`; API and RQ
regressions cover booleans, floats, strings, and both range edges.

Status: Resolved in `fc45a3c55`.

### CR-02 - Scheme clearing was not part of the active-state contract

Severity: Medium

The initial clear implementation released the NoDb lock while deleting a large
tree without persisting an active phase, so a run request could enter during
deletion. Clear now persists `clearing`, run admission treats it as active, and
success or failure leaves explicit terminal state. Focused race regressions cover
run-during-clear and clear failure.

Status: Resolved in `1983d01eb`.

### CR-03 - Bounded futures still handed full multi-OFE WAT tables to Python

Severity: Medium

The rolling process-pool fix bounded the number of futures, but Hybrid showed
that complete multi-OFE Arrow tables could still consume 46,695,247,872 bytes of
sampled anonymous memory. The default path now calls one additive wepppyo3 API
that parses source-ordered files and writes Parquet row groups directly. Exact
fixture parity passed, and the real 25,567,139,478-byte Hybrid corpus wrote
108,308,610 rows in 571.737 seconds at a 489,709,568-byte peak.

Status: Resolved in wepppyo3 `361c9ac`/`c84c586` and WEPPpy `dd6852a14`; final
authenticated Hybrid completed without taking the Python fallback.

### CR-04 - `totalwatsed3` evaluated last-OFE identity on every WAT row

Severity: Medium

Direct WAT writing completed at low memory, but Concept 1 then reached
59,396,808,704 bytes of sampled anonymous memory while `run_totalwatsed3()`
evaluated `MAX(ofe_id) OVER (...)` across 172,364,760 rows. The query now computes
one final-OFE id per hillslope and joins that bounded relation to WAT. A full
Concept 1 regeneration completed in 28.55 seconds at 10,238,947,328 bytes
maximum RSS. The 6,210-row, 79-column before/after outputs have identical schema
metadata and pass `rtol=1e-12, atol=1e-12`; the worst relative difference is
`2.34e-15` from parallel summation order.

Status: Resolved in WEPPpy `90817edb2`; full Hybrid parity passed.

### CR-05 - DuckDB retained buffers across independent aggregates

Severity: Medium

Final Hybrid completed successfully but briefly reached 20,510,617,600 sampled
anonymous bytes after direct WAT writing. Isolated measurements showed the WAT,
soil, and element queries at 0.85 GB, 5.86 GB, and 1.54 GB maximum RSS; their
buffers accumulated because all three used one long-lived DuckDB connection.
Each large aggregate now owns and closes a separate connection. Full Hybrid
regeneration completed in 16.73 seconds at 6,104,309,760 bytes maximum RSS. Its
6,210 rows and 79 columns preserve schema metadata and non-floating values, with
all floating values within `rtol=1e-12, atol=1e-12`.

Status: Resolved in WEPPpy `be60b6fc9`.

## Closed Review Checks

- Scheme values are closed enums; filesystem paths come only from fixed enum-to-
  slug mappings.
- Omitted scheme remains Concept 2 for old clients and historical state remains
  readable without rewriting the legacy tree.
- Run All preassigns and persists all job ids before enqueue and chains three
  independent jobs with failure-tolerant serial dependencies.
- Staging and publication preserve a prior result until a terminal manifest is
  durable; published resources contain no staging-root path.
- Interrupted reconciliation requires the exact persisted job id and an
  authoritative terminal/missing RQ status.
- Hybrid ownership uses connected outlet-injection sources plus a residual
  Concept 1 source; it never overlays those sources on a full-parent source.
- Management inputs reject invalid/non-finite records and do not silently clamp
  producer values or substitute another routing scheme.
- Exact corpora prove all 1,869 Concept 1 and 1,644 Hybrid residual parents under
  synchronized hillslope capacity 32.
- UI labels describe physical behavior, show scheme-specific limitations, and do
  not present internal concept numbers as the primary labels.

## Residual Risks

- `clear all` intentionally performs three independently safe, idempotent clears;
  a client disconnect can leave only a subset cleared, but cannot expose or
  corrupt sibling/protected trees. Retrying `clear all` completes the operation.
- An old wepppyo3 deployment without the additive direct WAT API takes an explicit
  logged compatibility path. The committed py312 release contains the direct API;
  operators should treat a compatibility-fallback warning as an availability
  signal.
- Routing-scheme scientific fitness is outside this engineering review and
  remains assigned to Mariana Dobre. ADR-0019 remains Proposed pending owner
  disposition.

## Gate Decision

- Code review: Pass for implementation.
- Generated acceptance: Pass. All three scheme roots and the engineering
  comparison bundle are complete; 160,671 protected files remain byte-identical.
