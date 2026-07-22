# Code Review - SSURGO Intelligent Fallback M4 Rollout

## Review Metadata

- **Reviewer**: Planck, independent review agent
- **Review date**: 2026-07-22 UTC
- **Review turn**: independent read-only scaffold review
- **Reviewed base**: `def1d3243` plus uncommitted M4 scaffold
- **Reviewed scope**: ADR-0025, fallback specification, rollout ExecPlan,
  package/tracker, persistence and RQ-adjacent implementation orientation.
- **Validation observed**: documentation inspection only; no implementation
  claim was reviewed.

## Findings

| ID | Severity | Evidence / required action | Disposition |
| --- | --- | --- | --- |
| CR-01 | High | Preserve the existing global donor as the mode of valid **primary** outcomes only. Added candidates must never alter the baseline. Add a fixture with high-support but profile-ineligible added candidate and prove the primary global donor remains selected. | accepted-pending; M1/M2 contract and test |
| CR-02 | High | Clarify that a valid primary-map MUKEY and a valid added MUKEY are both eligible candidates. Only selected added donors need final materialization. Test both origins and unused-added absence. | accepted-pending; specification and M2 test |
| CR-03 | High | Add donor-materialization failure and persisted-selection-raster proof. Selection must use only validated candidate map metadata/checksum, never VRT/project map. | accepted-pending; M1/M3 implementation and failure injection |
| CR-04 | Medium | Trigger only for residual-invalid **dominant hillslopes**. An invalid non-dominant map MUKEY must not open/crop/enumerate/build candidates. | accepted-pending; M1 no-op matrix |
| CR-05 | Medium | Test exact first OM-valid direct profile, accepted ranges, texture balance, at-least-three fields, scale equation, first successful radius, support tie, numeric MUKEY tie. | accepted-pending; M2 fixture matrix |
| CR-06 | Medium | Complete a compatibility note defining all additive provenance values, null/empty types, Parquet representation, hydration, and consumers before persistence changes. | accepted-pending; M1 compatibility artifact |
| CR-07 | Medium | Specify explicit error for missing native categorical dependency; exclude individual nonbuildable candidates while another valid candidate may win; make retry output atomic. | accepted-pending; M1/M2 contract and tests |
| CR-08 | Medium | Persist WGS84 source location for every affected raw map occurrence and prove disconnected same-MUKEY locations can select differently. | accepted-pending; M2/M3 fixture |

## Summary

- **Gate**: HOLD
- **Unresolved critical/high findings**: 3
- **Unresolved medium findings**: 5
- **Release recommendation**: do not begin M1 implementation until all high
  findings are reflected in the active implementation contract.

## M5 Implementation Re-review

- **Reviewer**: `m5_code_review` (independent read-only agent)
- **Review date**: 2026-07-22 UTC
- **Review turn**: independent M5 implementation review and committed delta
  review
- **Reviewed base**: `8dac222dfdd7d54eead918526dc9c6bb488191d0`
- **Supplemental evidence commit**: `a334ced452ce707123acf920f0ac3d62352a219e`
- **Scope**: fallback implementation, NoDb propagation, RQ config guard,
  ADR/specification, M3/M4 evidence, and the concurrent-publication delta.
- **Validation**: fallback/NoDb/masked-valid suite 41 passed; RQ route suite
  6 passed; adversarial corpus 10/10 passed; the committed concurrent retry
  regression passed independently.

**Result**: No new critical, high, or medium code finding. CR-01 through CR-08
are resolved by the reviewed implementation and executable evidence. The delta
has deterministic overlapping publishers, one injected crop failure, immutable
completed artifacts, no temporary files, and a clean active-manifest retry.

**M5 recommendation**: GO.
