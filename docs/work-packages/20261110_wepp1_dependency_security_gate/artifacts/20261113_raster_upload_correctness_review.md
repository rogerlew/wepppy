# Correctness and user-experience review - raster upload boundary

## Metadata

- **Package:** `docs/work-packages/20261110_wepp1_dependency_security_gate/`
- **Reviewer:** independent Codex reviewer
  `/root/raster_contract_correctness_review`
- **Date:** 2026-11-13
- **Scope:** `F6-RU-01` contract checkpoint, general rq-engine raster uploads,
  DEM upload UI, persisted reuse, and multi-raster request failure behavior
- **Starting revision:** `419fa0b320d83456cbbd6fc7ad3b6119108da015`
- **Canonical contracts:** `docs/schemas/upload-endpoint-contract.md`,
  `docs/schemas/rq-response-contract.md`, and
  `docs/schemas/nodb-persistence-concurrency-contract.md`
- **Related security artifact:**
  `artifacts/20261113_raster_upload_security_review.md`

## User outcome and valid states

Users may provide self-contained GeoTIFF or IMG rasters, including DEMs. Success
preserves existing scientific validation and publishes only exact bytes that
passed restricted driver validation. A malformed, renamed, companion-dependent,
escaped, or legacy VRT input returns an explicit 400 and preserves previously
accepted files and controller state. Optional persisted reuse remains valid only
when server state resolves one run-owned, contained, unchanged GTiff/HFA file.

The valid-state and request matrix is authoritative in
`artifacts/20261113_raster_upload_contract_decision.md`. Generated/internal VRT
and the postfire dNBR identity-VRT workflow are unchanged. General uploaded VRT
is an explicitly authorized compatibility removal.

## Failure-class coverage

The broken shared assumption is that an allowed filename extension makes later
native opens safe. Confirmed consumers are DEM, disturbed/HUC/batch SBS,
landuse, treatments, Ash, and Omni SBS. The contract requires request-wide
scratch validation before mutation/publication, exact driver/full-band read,
immutable byte identity through semantic validation, run-root containment for
reuse, and late-part failure coverage. The descendant implementation at
`cb839e7d7` satisfies those requirements.

## Findings and disposition

| ID | Severity | Finding | Disposition | Status |
| --- | --- | --- | --- | --- |
| COR-01 | High | Active records falsely deferred both GDAL work and input enforcement | Corrected every active F6 authority record; only GDAL upgrade/custom compilation is deferred | Resolved |
| COR-02 | High | Per-file `post_save` cannot prove request-wide no-mutation for landuse/Ash/Omni | Request-wide boundary prevalidation now covers new and persisted raster inputs before publication/mutation | Resolved |
| COR-03 | High | One restricted probe did not constrain later native consumers | Restricted decode, identity receipts, complete companion rejection, and restricted touched opens preserve the validated snapshot | Resolved |
| COR-04 | Medium | Shared helper ownership and applicable contracts were incomplete | Shared implementation assigned to `microservices/upload_boundary.py`; rq wrapper, RQ response, and NoDb contracts are explicit | Resolved |
| COR-05 | Medium | Self-contained HFA evidence omitted a companion-dependent raster | Real `.ige`-dependent HFA coverage forces a read and rejects the detached primary | Resolved |
| COR-06 | Medium | VRT compatibility removal and UI were incomplete | General VRT admission is removed; generated/internal and dNBR VRT remain; batch UI is corrected | Resolved |
| COR-07 | Low | WBT overview still said GeoTIFF only | User documentation now describes GeoTIFF/IMG and format matching | Resolved |

## Implementation re-review

The reviewer iteratively rejected Landuse mutation ordering, Omni request-wide
prevalidation, overbroad rollback wording, and incomplete target-sidecar
coverage. Commit `cb839e7d7` was approved after the implementation added
server-authoritative reuse receipts, owning-lock identity assertion, trusted
run-root containment, and one shared companion inventory applied through the
async Omni copy/admission path. The final focused receipt is 239 passed.

## Verdict

- **Checkpoint gate:** pass after post-fix confirmation; production UI and user
  documentation edits were removed from this ancestor checkpoint
- **Implementation gate:** pass at `cb839e7d7`
- **Release gate:** full F6 and production-equivalent deployment evidence remain
  separate rollout requirements
- **Unresolved design findings:** High 0; Medium 0; Low 0

No new generated artifact class is introduced. Existing run artifacts and
archive/restore observability remain unchanged; implementation conformance must
prove accepted and rejected upload bytes at their real consumer boundaries.
