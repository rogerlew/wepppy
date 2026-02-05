# NED1 VRT Alignment Audit + Correction

**Status**: Closed (2026-02-05)

## Overview
The `ned1/2024` VRT appears to be shifted by about 4 arc-seconds (4 pixels at 1 arc-second resolution). This work package defines a script to validate every tile referenced by the VRT via `vsicurl`, compare each tile's geotransform to the VRT placement, report offsets, and optionally write a corrected VRT.

## Objectives
- Detect per-tile offsets between the VRT and source tiles (UL X/Y in degrees).
- Produce a clear report of offsets (arc-seconds + pixels), summary stats, and any outliers.
- Author a corrected VRT that re-aligns the mosaic to the authoritative tile geotransforms.
- Provide a reproducible workflow for future VRT updates.

## Scope
### Included
- A new audit script (Python) that:
  - Parses the VRT and enumerates all `ComplexSource` entries.
  - Fetches each tile's geotransform via `vsicurl` (GDAL).
  - Computes VRT-UL vs tile-UL offsets (X, Y) in degrees, arc-seconds, and pixels.
  - Writes a correction report (CSV + JSON summary).
  - Optionally writes a corrected VRT (updated `<GeoTransform>` and/or `DstRect` offsets).
- A runbook describing how to execute the audit and apply corrections.

### Explicitly Out of Scope
- Rebuilding the NED1 dataset from scratch.
- Changing DEM retrieval logic in `wmesque` beyond consuming the corrected VRT.
- Updating any NED13 VRTs.

## Stakeholders
- **Primary**: WEPPcloud core maintainers
- **Reviewers**: Ops / geodata maintainers

## Success Criteria
- Audit script can complete against `/wc1/geodata/ned1/2024/.vrt` without errors.
- Report shows the expected 4 arc-second NW shift for `ned1/2024`.
- Corrected VRT aligns to tile ULs within <0.1 arc-second.
- Rerunning a sample DEM request shows map alignment restored.

## Deliverables
- Script: `docs/work-packages/20260205_ned1_vrt_alignment/tools/ned_vrt_audit.py`.
- Report output (CSV + JSON summary).
- Corrected VRT (optional, path specified via CLI).
- Outlier tile list (text).
- Short runbook in `notes/runbook.md`.

## Risks / Notes
- The VRT is large; the script should support sampling or chunking to reduce runtime.
- Network and S3 throughput will dominate runtime; include `--limit` and `--stride` options.
- Ensure GDAL exceptions are enabled for clearer error handling.
