# USGS NED1 Seamless VRT Alignment Issue (Preliminary Report)

## Summary
We found a spatial misalignment in the VRT distributed at:

- `https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF/USGS_Seamless_DEM_1.vrt`

The VRT's global origin and a subset of tile placements are shifted relative to the source tiles by approximately **4 arc-seconds** (4 pixels at 1" resolution), resulting in a visible northwest offset when mosaicked.

## Data Sources
- VRT: `USGS_Seamless_DEM_1.vrt` (1 arc-second, NAD83)
- Tile examples:
  - `.../Elevation/1/TIFF/current/n45w124/USGS_1_n45w124.tif`
  - `.../Elevation/1/TIFF/current/n33w100/USGS_1_n33w100.tif`

## Determination Method
We authored a GDAL-based audit tool that:

1. Parses the VRT and enumerates all `ComplexSource` entries.
2. Opens each tile via `vsicurl` and reads the tile geotransform.
3. Computes each tile's expected upper-left (UL) position from the VRT.
4. Reports offsets in degrees, arc-seconds, and pixel units.

Script location:
- `docs/work-packages/20260205_ned1_vrt_alignment/tools/ned_vrt_audit.py`

## Findings
- Total tiles analyzed: **3811**
- Tiles with ~4" NW offset: **37**
- The outlier tiles are consistently shifted by:
  - **dx = -4 arc-seconds** (west)
  - **dy = +4 arc-seconds** (north)
- All other tiles are aligned within ~0.001 arc-seconds.

Outlier list:
- `docs/work-packages/20260205_ned1_vrt_alignment/artifacts/outlier_tiles.txt`

Example mismatch (n45w124):
- Tile UL (from tile GeoTransform): `(-124.0005555565, 45.0005555563)`
- VRT UL (computed from VRT GeoTransform + DstRect): `(-124.0016666671, 45.0016666669)`
- Offset: **-0.001111111 deg**, **+0.001111111 deg** (exactly 4 arc-seconds)

## Correction
We generated a corrected VRT that repositions the affected tiles by recomputing `DstRect` offsets while keeping the global geotransform intact. The corrected file:

- `docs/work-packages/20260205_ned1_vrt_alignment/artifacts/USGS_Seamless_DEM_1.corrected.vrt`

Re-auditing the corrected VRT shows residual offsets within ~5e-7 arc-seconds (sub-micro-arcsecond), indicating the fix is clean.

## Reproduction Steps
```bash
python docs/work-packages/20260205_ned1_vrt_alignment/tools/ned_vrt_audit.py \
  --vrt /wc1/geodata/ned1/2024/.vrt \
  --out-dir /wc1/geodata/ned1/2024/audit
```

To generate a corrected VRT:
```bash
python docs/work-packages/20260205_ned1_vrt_alignment/tools/ned_vrt_audit.py \
  --vrt /wc1/geodata/ned1/2024/.vrt \
  --out-dir /wc1/geodata/ned1/2024/audit \
  --correction-mode dstrect \
  --write-corrected-vrt /wc1/geodata/ned1/2024/USGS_Seamless_DEM_1.corrected.vrt
```

## Notes
- The VRT's global origin appears to be shifted by 4 arc-seconds from the expected NED 1" grid.
- Only a small subset of tiles are impacted in the current VRT (37 / 3811), but the offset is large enough to cause a visible map shift.
- We can provide full CSV audit output upon request.
