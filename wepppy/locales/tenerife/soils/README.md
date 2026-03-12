## Tenerife Soils

Active Tenerife runtime support is intentionally limited to two soil rasters:

- `tf_soil_5.tif` for `tenerife-5m-disturbed`
- `tf_soil_25.tif` for `tenerife-disturbed`

`tf_soil_10.tif` is retained as source/reference inventory from the 2026 bundle,
but no active NoDb config points at it.

The runtime `db/` directory contains two required shim profiles:

- `20.sol` for rock-coded cells
- `21.sol` for urban-coded cells

Those two classes still occur in both supported rasters, so removing the shims
without changing `wepppy/nodb/core/soils.py` will break Tenerife soil builds.

The legacy 250 m Tenerife branch and template-era generation artifacts were
retired during the 2026 ingestion package. This directory is now the current
runtime source of truth rather than a mix of active and preprocessing-era files.
