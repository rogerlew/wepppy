# Review Remediation (2026-04-26)

This artifact records the disposition of post-implementation review findings for the Peridot documentation repositioning package.

## Findings Addressed

| Severity | Finding | Disposition |
| --- | --- | --- |
| Medium | `docs/contracts/watershed-output-contract.md` stated that `sub_fields_abstraction` expects the same WBT watershed inputs as `wbt_abstract_watershed`, implying `netw.tsv` is required. Runtime source reads the WBT raster stack and field raster, but not `netw.tsv`. | Fixed. The contract now lists sub-field inputs separately and explicitly states that `sub_fields_abstraction` does not read `netw.tsv` or `discha`. |
| Low | Historical culvert integration plan still described Peridot flowpath omission in `flowpaths.csv` terms. | Fixed. Added historical-contract notes to Phase 4e and Phase 4g that map CSV-era wording to the current Parquet-first Peridot contract and link the canonical output contract. |
| Low | Peridot README listed only `discha.tif` for representative-flowpath mode while source and contract allow `.tif` or `.vrt`. | Fixed. README now documents `discha.tif` or `discha.vrt`. |

## Source Evidence

- `/home/workdir/peridot/src/wbt/wbt_sub_fields_abstraction.rs` reads `dem/wbt/subwta`, `relief`, `flovec`, `fvslop`, `taspec`, and the configured field raster.
- `/home/workdir/peridot/src/wbt/wbt_watershed_abstraction.rs` reads `dem/wbt/netw.tsv` for watershed abstraction.
- `/home/workdir/peridot/src/wbt/wbt_watershed_abstraction.rs` uses `find_raster_path("dem/wbt/discha")`, which supports `.tif` and `.vrt` fallback through the same helper used for other WBT rasters.

## Files Updated

- `/home/workdir/peridot/README.md`
- `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`
- `/workdir/wepppy/docs/culvert-at-risk-integration/weppcloud-integration.plan.md`

## Validation

Validation is recorded in `2026-04-26_validation_summary.md`.
