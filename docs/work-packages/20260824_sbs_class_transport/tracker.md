# Tracker - SBS Display Class Decoding

## Quick Status

**Timezone**: UTC  
**Started**: 2026-08-24 21:30 UTC  
**Current phase**: Promoted-contract checkpoint review  
**Last updated**: 2026-08-25 02:00 UTC  
**Next milestone**: Implement producer totality and exact lookup  
**Checkpoint ancestor**: `f79aef8fc2290526785a478ad8c490254648d25f`  
**Security impact**: `low`; assessed from the actual changed surface  
**Dedicated security review**: not required

The proposed implementation changes the existing validate-time SBS render path
and both map clients. No implementation has started.

## Task Board

### Ready / Backlog

- [ ] Re-read the cleaned ADR, contract decision, package, and ExecPlan as one
  normative set and remove any remaining contradiction.
- [ ] Obtain a fresh correctness review of that set and disposition all medium
  and high findings.
- [x] Obtain explicit operator approval of the pre-2018 compatibility policy:
  unknown historical opaque colors render Unassigned, while colors previously
  clamped to a valid severity cannot be detected until re-validation.
- [x] Accept ADR-0045.
- [ ] Commit the pre-implementation checkpoint after post-fix review.
- [ ] Implement producer totality and exact GDAL lookup.
- [ ] Implement client decoding, sentinel, legends, count, and tooltip.
- [ ] Consolidate palette/legend definitions and add a parity test.
- [ ] Run focused generated-output and client validation, then broader gates.
- [ ] Update current user/developer documentation in the implementation change
  set.

### In Progress

- [ ] Implement producer totality and exact lookup.

### Blocked

- Implementation remains blocked only until the corrected checkpoint passes two
  independent reviews and is committed as a standalone ancestor.

### Done

- [x] Confirmed stale-palette behavior against a production artifact.
- [x] Proved with GDAL that sparse color tables interpolate between entries and
  clamp outside their range.
- [x] Located three historical endpoint-palette generations.
- [x] Identified unassigned as distinct from masked/NoData.
- [x] Produced reproducible GDAL and sentinel-selection evidence.
- [x] Withdrew the rejected request-time regeneration and closed-encoding
  designs.
- [x] Removed generated observability churn, premature production-doc changes,
  and edits to closed work packages from the dirty tree.
- [x] Obtained two independent reviews of the cleaned proposal; both returned
  Blocked. Artifacts: `2026-08-25_cleaned_contract_review.md` and
  `2026-08-25_cleaned_security_scope_review.md`.
- [x] Operator established that closed work packages are transient historical
  records and durable governance must be promoted outside them.
- [x] Promoted the SBS behavior contract to
  `docs/ui-docs/contracts/sbs-display-transport-contract.md` and amended the
  contract-first and work-package lifecycle standards.
- [x] Two independent post-fix reviews approved the promoted checkpoint with no
  unresolved high/medium findings.
- [x] Committed standalone checkpoint ancestor
  `f79aef8fc2290526785a478ad8c490254648d25f`.

## Current Risks and Decisions Needed

- Historical RGB is not a lossless class encoding. Exact client decoding can
  recognize known endpoint colors, but cannot reconstruct interpolated class
  values or distinguish clamped unassigned values from genuine severity pixels.
- `-exact_color_entry` makes unmatched values transparent, so the producer must
  write an opaque sentinel entry for the union of observed non-NoData values and
  source color-table indices.
- The proposed sentinel is `#800098`. Its selection evidence is retained under
  `artifacts/`; the correctness review should verify that its analysis and the
  user-facing semantics agree.
- Authorization of `resources_baer_sbs` and changes to default layer opacity are
  separate concerns and are not authorized by this package.

## Verification Checklist

- [ ] Real-GDAL producer tests cover Disturbed color-table classification,
  Disturbed breaks classification, and BAER class-map writing with their
  path-specific totality obligations.
- [ ] Out-of-range observed values bake opaque Unassigned, not transparency.
- [ ] Removing `-exact_color_entry` makes the adversarial test fail.
- [ ] Generation-0, generation-A, and generation-B endpoint fixtures recolor
  correctly in both clients and both modes.
- [ ] Historical interpolated and clamped limitations are asserted by tests.
- [ ] Alpha-zero pixels remain masked; other unknown opaque pixels render and
  count as Unassigned.
- [ ] Both legends and the GL Dashboard tooltip use decoded class semantics.
- [ ] Python/JavaScript palette parity test passes.
- [ ] No new route or payload shape is introduced; stored raster bytes are not
  changed by client rendering.
- [ ] Focused Python and frontend tests, frontend lint, full Python suite, and
  scoped documentation lint pass.

## Decision Log

- **2026-08-24** - Unassigned is a first-class display state, distinct from
  masked/NoData.
- **2026-08-24** - Use exact producer lookup plus a total color table; client
  decoding alone cannot prevent newly fabricated pixels.
- **2026-08-24** - Do not automatically rewrite historical run artifacts;
  re-validation remains the complete correction path.
- **2026-08-25** - Treat previous review/disposition files as research history,
  not approval of the cleaned proposal. Require two reviews of the coherent
  normative set.
- **2026-08-25** - Do not amend closed work packages to register or authorize
  this package. Current contracts and user/developer docs change alongside the
  implementation, after the pre-implementation gate.
- **2026-08-25** - Closed work packages are never living governance. Promote
  durable rules to current contracts outside `docs/work-packages/`; assess
  security from the actual changed surface rather than historical owner labels.

## Notes - 2026-08-25 02:00 UTC

The initial scaffold mixed three rejected designs, claimed mutually exclusive
scope for a route authorization change, and edited closed owner packages. The
cleanup restored those closed files and reduced the active gate to decisions
that are actually required to begin implementation.
