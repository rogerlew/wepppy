# Tracker - WEPP Direct-HBP Hillslope Area Index Repair

## Quick Status

**Timezone**: UTC
**Current phase**: Forest regeneration
**Last updated**: 2026-07-27 UTC
**Next milestone**: Production output validation

## Task Board

### In Progress

- [ ] Regenerate the Forest base and Omni watershed outputs sequentially.

### Ready

- [x] Complete QA review and disposition.
- [ ] Commit and push the WEPPpy vendoring and work package.

### Done

- [x] Reproduced the shifted-area sequence and final zero.
- [x] Confirmed every HBP shard contains its correct positive area.
- [x] Identified zero-based actual-array association at the reader boundary.
- [x] Added the one-based slice repair and focused source regression.
- [x] Built the corrected binaries and replayed the copied incident watershed.
- [x] Validated WEPPpyo3 and WEPPpy consumers.
- [x] Published the uniquely named WEPP source release and tag.
- [x] Received independent code-review approval after closing its test gap.
- [x] Closed the QA same-build replay and HBP sidecar metadata findings.

## Decisions

- **2026-07-27 UTC** - Fix the WEPP bridge by passing explicit one-based
  `hlarea` and `dia` slices. This preserves HBP bytes and model calculations
  while correcting the legacy common-block indexing contract.
- **2026-07-27 UTC** - Do not make `HillSummaryReport` silently substitute
  geometry for invalid model output. Generated LOSS must be correct.

## Risks

- A source-only assertion could miss runtime association behavior. Mitigation:
  require a generated 587-hillslope watershed replay and compare LOSS areas
  against HBP metadata.
- A new LOSS row could break native consumers. Mitigation: convert generated
  LOSS and SOIL files through the WEPPpyo3 release path and exercise WEPPpy
  report consumers.
- Replacing `wepp_260726` would destroy provenance. Mitigation: publish a new
  dated release and preserve all historical artifacts.

## Review Disposition

Code review approved after the executable regression in commit `633bce99`
closed the initial medium-severity test gap. QA initially blocked deployment
on mixed-build replay evidence and incorrect HBP sidecar metadata. The replay
was repeated after regenerating all 587 shards with the matching hillslope
binary, and sidecars plus generator coverage were corrected. QA approved the
release subject to matching-version production regeneration.
