# MACA CCSM4 source-member diagnosis

## Trigger and cause

On 2026-10-16 UTC, a two-day precipitation probe across the 20 MACAv2-METDATA
models and both future scenarios returned usable data for 38 of 40 combinations.
CCSM4/RCP4.5 and CCSM4/RCP8.5 returned HTTP 500. The response body was only
`<h1>Server Error (500)</h1>`; no server-side traceback was available.

`wepppy/climates/downscaled_nmme_client.py` hardcodes `r1i1p1` in its dataset
URL template. The probe copied that assumption. The provider's CCSM4 dataset
uses `r6i1p1`, as shown in the
[provider catalog](https://tds-proxy.nkn.uidaho.edu/thredds/reacch_climate_CMIP5_aggregated_macav2_catalog.html?dataset=agg_macav2metdata_pr_CCSM4_r6i1p1_rcp45_2006_2099_CONUS_daily).
The failure therefore concerns the requested source identity; the original
probe did not establish that CCSM4 itself was unavailable.

## Bounded verification

The corrected diagnostic request changes only the ensemble-member segment from
`r1i1p1` to `r6i1p1`. It uses the existing
`https://climate-dev.nkn.uidaho.edu/Services/get-netcdf-data/` service, longitude
-116, latitude 47, and dates 2030-01-01 through 2030-01-02.

Verification covers `pr`, `tasmax`, `tasmin`, `rsds`, `uas`, `vas` and `huss` for
each of RCP4.5 and RCP8.5. A successful check requires HTTP 200, exactly both
requested dates, finite numeric values and returned source metadata identifying
the requested CCSM4 member, variable and scenario. All 14 checks passed on
2026-10-16 UTC. The original failure records, exact request URLs, successful
response data and source metadata are retained in the
[diagnostic artifact](artifacts/20261016_maca_ccsm4_probe.json).

## Implementation implication and limits

A future client correction should select the cataloged member explicitly:
CCSM4 uses `r6i1p1`; the other models in this probe use `r1i1p1`. This should be
a deterministic model-to-member mapping, not a retry that silently substitutes
another ensemble. Preserve the existing GFDL-ESM2G/RCP8.5 application default.

This investigation does not modify runtime code, deploy services, select a
different projection for a project, or establish full-period coverage, CLI
generation or WEPP execution. It isolates the HTTP failure at a representative
location and dates. The projection selector remains separate implementation work.
