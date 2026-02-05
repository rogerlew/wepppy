# Tracker: NED1 VRT Alignment Audit + Correction

## Status
- Closed (2026-02-05)

## Tasks
1. [x] Define CLI + output schema for the audit script.
2. [x] Implement VRT parser that emits tile entries + VRT UL placement.
3. [x] Implement tile geotransform fetch via GDAL `vsicurl`.
4. [x] Compute offsets (deg, arc-sec, pixels) and summary stats.
5. [x] Write CSV + JSON summary outputs.
6. [x] Implement corrected VRT writer (optional flag).
7. [x] Add runbook + usage examples.
8. [x] Validate on `/wc1/geodata/ned1/2024/.vrt` and spot-check results.

## Questions / Decisions
- Should the corrected VRT adjust only the global GeoTransform or recompute all `DstRect` offsets?
- Where should the corrected VRT live (`/wc1/geodata/ned1/2024/USGS_Seamless_DEM_1.corrected.vrt` vs `/wc1/geodata/ned1/2024/.vrt` backup/replace)?
- Do we need a separate audit mode that only samples every Nth tile?

## Notes – 2026-02-05
- Implemented `docs/work-packages/20260205_ned1_vrt_alignment/tools/ned_vrt_audit.py`.
- Generated corrected VRT using `--correction-mode dstrect`.
- Stored artifacts in `docs/work-packages/20260205_ned1_vrt_alignment/artifacts/`:
  - `USGS_Seamless_DEM_1.corrected.vrt`
  - `outlier_tiles.txt`
- Added `notes/usgs_report.md` with a summary suitable for USGS outreach.
 - Package closed after validation (`audit_corrected` showed sub-micro-arcsecond residuals).
