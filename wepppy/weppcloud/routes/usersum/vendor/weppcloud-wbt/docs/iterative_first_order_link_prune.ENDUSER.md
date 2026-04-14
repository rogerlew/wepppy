# Iterative First-Order Link Prune

Use this tool to create a stream raster from D8 flow directions and upstream area, while removing short first-order tributaries in a deterministic way.

## What This Is For

`IterativeFirstOrderLinkPrune` builds a stream mask (`1=stream`, `0=background`) in two phases:

1. Phase A qualifies stream cells from local critical source area (CSA) thresholds.
2. Phase B prunes short first-order links using local minimum source channel length (MSCL) thresholds.

This is useful when you need stable, repeatable channel extraction with explicit controls for source-area sensitivity and short-tributary pruning.

## When to Use It

Use this tool when you need one or more of the following:

- A binary stream raster for downstream watershed/channel workflows.
- Deterministic pruning of short first-order links near confluences.
- Spatially variable thresholds by management zone, climate region, or terrain class.
- A stream extraction method aligned with IFOLP/TopAZ-style parity studies in WEPPcloud-WBT.

## Before You Begin

Prepare these inputs first:

- A D8 pointer raster (`--d8_pntr`) using Whitebox encoding (default) or ESRI encoding (`--esri_pntr`).
- An upstream-area raster in **contributing cells** (`--upstream_area`), aligned to the pointer raster.
- An output path (`--output`).
- Default thresholds:
  - `--csa` in hectares (`> 0`)
  - `--mscl` in meters (`>= 0`)

Optional local-threshold inputs:

- `--threshold_code_raster` (integer zone/code raster)
- `--threshold_table` (maps `code -> csa_ha, mscl_m`)

Important:

- Rasters must match in rows, columns, resolution, and extent.
- `--threshold_code_raster` and `--threshold_table` must be provided together.
- Threshold-table values must be finite with `csa_ha > 0` and `mscl_m >= 0`.

## Key Terms and Settings

| Setting | What it means | Units or values | Why it matters |
| --- | --- | --- | --- |
| `--csa` | Default critical source area for stream qualification | hectares (`> 0`) | Higher values generally produce fewer stream head cells. |
| `--mscl` | Default minimum source channel length for first-order pruning | meters (`>= 0`) | Higher values generally prune more short first-order links. |
| `--threshold_code_raster` | Integer code raster for local threshold lookup | integer codes | Enables spatially variable CSA/MSCL thresholds. |
| `--threshold_table` | CSV/whitespace table mapping `code,csa_ha,mscl_m` | code + numeric thresholds | Defines local threshold policy by code. |
| `--epsilon` | Floating comparison tolerance for threshold boundaries | default `1e-5` | Controls strict comparison edges in Phase A and Phase B. |
| `--esri_pntr` | Interpret D8 pointers as ESRI encoding | boolean | Required if your pointer raster was produced with ESRI code conventions. |
| `--fail_if_only_channel_pruned` | Fail instead of silently pruning when one-channel guard is triggered | boolean (default `true`) | Prevents accidental total removal in minimal-channel cases. |

## Steps

1. Confirm raster geometry alignment.
2. Decide whether global thresholds are enough (`--csa`, `--mscl`) or whether you need local threshold zones.
3. If using local zones, build a threshold table with columns `code,csa_ha,mscl_m`.
4. Run the tool.

Global-threshold example:

```bash
whitebox_tools -r=IterativeFirstOrderLinkPrune \
  --d8_pntr=d8.tif \
  --upstream_area=upstream_cells.tif \
  --output=streams_ifolp.tif \
  --csa=10.0 \
  --mscl=100.0
```

Local-threshold example:

```bash
whitebox_tools -r=IterativeFirstOrderLinkPrune \
  --d8_pntr=d8.tif \
  --upstream_area=upstream_cells.tif \
  --threshold_code_raster=threshold_codes.tif \
  --threshold_table=thresholds.csv \
  --output=streams_ifolp_local.tif \
  --csa=10.0 \
  --mscl=100.0 \
  --epsilon=1e-5
```

5. Inspect the output stream mask and compare against known channels or prior delineations.

## Interpreting Results

Output raster values:

- `1`: stream cell retained after qualification and pruning.
- `0`: non-stream background.
- `NoData`: propagated from input NoData footprint.

Interpretation guidance:

- More stream pixels usually means lower effective CSA/MSCL thresholds.
- Fewer stream pixels usually means higher effective CSA/MSCL thresholds or stronger short-link pruning.
- Local threshold zones can intentionally create different channel densities across the watershed.

## Assumptions and Limits

- Inputs are D8-based; incorrect pointer encoding will invalidate topology.
- Upstream area must be in contributing-cell units, not area units.
- This is a model-driven delineation method and should be reviewed against field knowledge or mapped channels before decision-critical use.
- Threshold sensitivity near boundary values can change local channel presence; keep threshold governance documented for reproducibility.

## Troubleshooting

- **"Raster geometry mismatch"**: input rasters are not perfectly aligned.
- **"Optional threshold inputs must be provided together"**: supply both threshold code raster and table.
- **"No threshold table entry for code"**: table is missing at least one active code value.
- **"No channels remain..."**: thresholds may be too strict for the current watershed.
- **Cycle or pointer errors**: pointer raster contains invalid flow topology for active stream cells.

## Related Docs

- [IFOLP Specification](iterative-first-order-link-prune/specification.md)
- [IFOLP Implementation Plan](iterative-first-order-link-prune/implementation-plan.md)
