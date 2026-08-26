# SBS-A11Y-01 Security Review

**Status**: SUPERSEDED — reviewed the pre-correction removal contract
**Security impact**: `high` by inherited DOM-23 owner rule

## Review Boundary

Review the contract checkpoint, ADR, DOM-04B and DOM-23 matrix amendments, and
the proposed parser/export/UI boundary. Confirm that no route, upload, path,
authentication, authorization, queue, external egress, or model parameter
surface is broadened.

## Required Checks

- Exact RGB lookup remains finite and deterministic; no fuzzy matching.
- Unknown and malformed color-table entries do not gain an unsafe fallback.
- Source recognition, four-class export, and web display preserve masked value
  `255` as NoData/transparent; model-facing consumers retain class `130` fallback.
- Python and Rust fast paths share a bounded mapping and compatible failure
  behavior.
- No test fixture or evidence artifact contains sensitive production data.
- Preservation of client recoloring does not introduce new remote resource or
  canvas handling boundaries; both palettes remain finite exact mappings.

## Findings and Disposition

- **SEC-01 (High), NoData/model/export ambiguity**: accepted and fixed. The
  contract now distinguishes source color-table NoData, model-facing class-130
  fallback, mask-aware coverage, `0..3 + 255` interchange export, and
  transparent web display. Both coverage consumers and the all-masked result
  are now explicit.
- **SEC-02 (High), rollback-unsafe fifth JSON severity**: accepted and fixed.
  The shared JSON remains four-severity; exact white is a separate Python-side
  NoData-index rule, with mixed-version tests required.
- **SEC-03 (Medium), missing/corrupt fallback parity**: accepted and fixed.
  Built-in maps must be synchronized and exercised through forced Python and
  direct Rust paths; corrupt explicit paths may not silently diverge.
- **SEC-04 (Medium), incomplete GL Dashboard scope**: accepted and fixed.
  The template and live bootstrap are explicitly in scope, while the base image
  loading/sampling pipeline remains unchanged.
- **SEC-05 (Medium), tracker risk mismatch**: accepted and fixed. All package,
  register, tracker, and review metadata now state inherited `high` impact.
- **SEC-06 (Low), artifact privacy**: accepted and fixed. Fixtures/screenshots
  must be synthetic/redacted and free of production metadata and identifiers.

## Final Disposition

The original PASS covered a superseded removal contract. A corrective
independent review must confirm the preserved shifted-mode boundary before this
artifact returns to PASS.
