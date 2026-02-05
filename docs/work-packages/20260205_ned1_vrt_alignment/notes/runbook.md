# Runbook: NED1 VRT Alignment Audit

## Prereqs
- GDAL available on the host or inside the weppcloud container.
- Network access to `prd-tnm.s3.amazonaws.com`.

## Example Usage
```bash
python docs/work-packages/20260205_ned1_vrt_alignment/tools/ned_vrt_audit.py \
  --vrt /wc1/geodata/ned1/2024/.vrt \
  --out-dir /wc1/geodata/ned1/2024/audit \
  --limit 5000 \
  --stride 1
```

## Full Audit + Corrected VRT
```bash
python docs/work-packages/20260205_ned1_vrt_alignment/tools/ned_vrt_audit.py \
  --vrt /wc1/geodata/ned1/2024/.vrt \
  --out-dir /wc1/geodata/ned1/2024/audit \
  --correction-mode dstrect \
  --write-corrected-vrt /wc1/geodata/ned1/2024/USGS_Seamless_DEM_1.corrected.vrt
```

## Expected Output
- `audit.csv` with per-tile offsets and stats.
- `summary.json` with min/mean/max offsets and outliers.
- Optional corrected VRT path.

## Notes
- Use `--limit` and `--stride` to reduce runtime if needed.
- Re-run with `--strict` once the audit looks stable to fail on any missing tiles.
