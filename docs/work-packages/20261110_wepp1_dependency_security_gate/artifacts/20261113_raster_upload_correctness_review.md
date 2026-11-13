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
reuse, and late-part failure coverage. Implementation evidence remains pending.

## Findings and disposition

| ID | Severity | Finding | Disposition | Status |
| --- | --- | --- | --- | --- |
| COR-01 | High | Active records falsely deferred both GDAL work and input enforcement | Corrected every active F6 authority record; only GDAL upgrade/custom compilation is deferred | Resolved; recheck pending |
| COR-02 | High | Per-file `post_save` cannot prove request-wide no-mutation for landuse/Ash/Omni | Contract now requires all request rasters pass private scratch validation before any mutation/publication and requires late-second-file evidence | Resolved; implementation pending |
| COR-03 | High | One restricted probe did not constrain later native consumers | Contract now requires full-band restricted decode, same immutable snapshot for semantic validators, byte/filesystem identity proof, and restricted direct GDAL opens touched here | Resolved; implementation pending |
| COR-04 | Medium | Shared helper ownership and applicable contracts were incomplete | Shared implementation assigned to `microservices/upload_boundary.py`; rq wrapper, RQ response, and NoDb contracts are explicit | Resolved |
| COR-05 | Medium | Self-contained HFA evidence omitted a companion-dependent raster | Regression plan now requires a real `.ige`-dependent HFA with forced band read | Resolved; implementation pending |
| COR-06 | Medium | VRT compatibility removal and UI were incomplete | Operator direction is recorded as authority; batch UI correction is required in the descendant implementation; generated/internal and dNBR VRT remain | Resolved in contract; implementation pending |
| COR-07 | Low | WBT overview still said GeoTIFF only | GeoTIFF/IMG documentation correction is required in the descendant implementation | Resolved in contract; implementation pending |

## Verdict

- **Checkpoint gate:** pass after post-fix confirmation; production UI and user
  documentation edits were removed from this ancestor checkpoint
- **Implementation/release gate:** hold until implementation, real-driver tests,
  full F6 validation, and production-equivalent workflow evidence pass
- **Unresolved design findings:** High 0; Medium 0; Low 0

No new generated artifact class is introduced. Existing run artifacts and
archive/restore observability remain unchanged; implementation conformance must
prove accepted and rejected upload bytes at their real consumer boundaries.
