# Correctness and user-experience review — RUPC-01

Date: 2026-11-17 UTC. Independent reviewer: `/root/contract_review_a`.
Scope: implementation after checkpoint `8e87b2363`, current strip contract,
preparation, selection, native geometry, source-member presentation and scoped tests.

## User outcome and findings

Partial contour crossings can execute without 60% eligibility or longitudinal
splitting. Native outputs prove two valid real-geometry slices, not all Marta roads.
High finding: secondary coalesced source features showed no results. Fixed with
membership-aware map/detail joins and a shared-profile label; canonical summaries
remain one row per native profile. Focused consumer tests pass.

Admission finding: stale policy was rejected after workspace mutation. Fixed by
moving validation before retention and execution; tests assert neither occurs.
Reviewer confirmed both findings closed and no remaining medium/high findings.

## State and failure coverage

The acceptance matrix separates input geometry from runtime states. Focused tests
cover fresh/current and stale preparation, valid empty comparison versus failed
contributors, malformed and nonfinite dimensions, source membership conflicts,
small emitted dimensions, subdivision and duplication, other designs, current
result lifecycle, accounting and detachment readers. Existing lifecycle tests
cover never-used state, retention, archive/restore and invalidation consumers.
This is changed-path evidence, not a claim of exhaustive state coverage.

Missing fill/buffer inputs and non-positive upstream lengths remain explicit
contracted failures. The full copied upload failed eight profiles for non-positive
upstream OFEs; failure evidence was retained. No geometry or defaults were silently
changed to make that run succeed.

## Generated-artifact evidence

See `20261117_native_evidence.json` for source hashes, runtime identity, exact
planned/emitted geometry, native input hashes, replacement PASS receipts, watershed
consumer hash, retained byte-equal slope evidence and no-road control differences.
The source upload/baseline hashes remained unchanged. Both valid 141/42 slices
completed with synthetic, labeled fill/buffer parameters. Normal detachment reader
reports complete results; native watershed report has 5,844 daily rows. No baseline
PASS is added to a replaced target; each target is referenced once by `pw0.run`.
Native combination closure receipts pass their existing serialization budgets.

No-road control preserves baseline soil/management/climate/profile layout and
changes only width. Two half-width responses differ from full-width total runoff
by approximately 5–6 parts per million. This is diagnostic, not validation of
physical switchback connectivity or measured site parameters.

## Verdict

Independent review: pass; no unresolved medium/high findings. Final scoped receipt:
191 passed, two preexisting dependency deprecation warnings. Highest supported
claim: implementation and scoped forest validation. No wepp1 deployment, no
full-site repair, no integration/publication claim. Residual limitations are the
approved abstraction, synthetic validation dimensions, and infeasible full-upload
profiles. The user/operator guide documents these limits.
