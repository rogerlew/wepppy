# Soil format amendment tracker

Status: **closed, 2026-09-26 (code/local acceptance)**. No deployment performed.
Starting revision: `64dc33a0d`. Contract ancestor: `313951562`.
Runtime implementation: `f6ee5b527`; final commit retains fixture and review closeout.

- Strict admission, preserving WSU path, both preparation flags, metadata and guidance complete.
- All four formats execute natively at 1/2/12/32 OFEs; modifier cases pass at 1/3 OFEs.
- Authenticated live uploads, real RQ/NoDb, both normal preparation entry points,
  native 2/12-OFE runs and downloads pass for all new formats. 9002 archive/restore
  preserves metadata and raw source hashes.
- Focused regression: 248 passes; final format suite: 115 passes; conductivity-map
  fixture/wiring module: 32 passes. Existing template/preparation suite: 229 passes.
- Broad coverage: all 667 collected files covered. Initial 4,492 passes and 51 skips,
  then fixture correction and continuation with 5,366 passes, 49 skips and 12 subtests.
  Phase counts overlap; no unresolved failures. Exact split is retained below.
- Frontend: 919 passes; lint, WSU stubtest, test-stub completeness, docs, whitespace,
  root AGENTS size and broad-exception gates pass.
- Independent correctness/QA and dedicated security reviews pass. Owner accepts
  every finding closure; no risk acceptance or outstanding medium/high findings.

## Evidence and decision location

[Validation summary](artifacts/20260926_validation_summary.md),
[coverage split](artifacts/20260926_regression_coverage.json),
[live acceptance](artifacts/20260926_live_acceptance.json),
[correctness/QA](artifacts/20260926_correctness_review.md),
[security review](artifacts/20260926_security_review.md).

The durable format and preservation decision is in
[SUDI-02: Upload interface and validation](../../schemas/single-user-defined-inputs-contract.md#upload-interface-and-validation)
and [ADR-0075: SUDI-02 soil-format amendment](../../adrs/ADR-0075-single-user-defined-inputs.md#sudi-02-soil-format-amendment).
Execution record: [completed plan](prompts/completed/soil_formats_execplan.md).

## Operational limit

Live acceptance used synthetic development geometry. Long-lived workers required
fresh-process retry because their imports predated the amendment. Install web and
workers together and restart workers through the normal deployment workflow;
local acceptance is not production rollout approval.
