# E-OBS sampling implementation validation

The contract checkpoint is `9671cc1c0` and implementation is `55e417ca0`. On forest, a private HTTP instance of candidate metquery served the installed E-OBS v19.0e VRTs. The application used the normal metquery client and unmodified unit conversions. The normal E-OBS localization entry point ran CLIGEN with the original station `SPE00119882`, original centroid and 30-year duration. All 10,957 daily rows and the twelve precipitation headers parsed as finite values. The daily output had nonnegative precipitation and ordered minimum and maximum temperatures, with wet days in every calendar month. The scripts, JSON readback, CLIGEN log, `.par` and `.cli` are retained under `/var/tmp/wepppy-eu-run-recovery-baseline/`.

| Control | Result |
| --- | --- |
| Es Fangar coast | January and July precipitation of 1.223 and 0.124 mm/day. Corresponding monthly minimum temperature means of 5.019 and 18.405 °C and maximum means of 13.920 and 28.624 °C. |
| Paris-area inland | For twelve months and all three variables, largest absolute change against the old raster interpolator was about `2.14e-14`. |
| Inland cubic undershoot | January rainfall near 41.5498502 E, 64.0498689 N stayed at -0.258627 mm/day in the metquery response, with the existing downstream dry-month handling. |
| Offshore and mixed legacy rainfall | Missing offshore coverage and a known negative non-sentinel rainfall source at 31.74985026 E, 40.24986998 N produced actionable January errors. Raw-source samples confirmed that the latter cell mixed valid values with missing records during historical aggregation. |

The isolated focused suite passed 61 tests, including the normal configured HTTP client, a station ranking failure that preserved the saved selection, legacy method and default provider controls, and a preprocessing round trip with mixed valid and missing daily observations. The receipt is `.wctl-test-runs/1f1e9c9142be4352b4c3b27c741acf2e/receipt.json`. Independent reviews verified real-raster parity and a sanitized 503 when a VRT's source raster is unreadable.

The broad run passed 369 tests and skipped 28 before stopping at the same culvert lock conflict reproduced on the unchanged baseline. The receipt is `.wctl-test-runs/29141fc7a6e444e987eb679d86977f21/receipt.json`.

The candidate Compose configuration resolves the opt-in address into the web, default worker, and batch worker environments. The private readback used a loopback service. A full forest deployment and browser/RQ replay must still establish the running worker and provider identities. Keep the replay pinned to the original station. The existing global latitude-based heuristic returned duplicate U.S. candidates at the Es Fangar centroid in the probe. That result verifies that the new provider works in ranking and exposes a separate station-selection issue. Previously installed mixed-observation monthly rasters still need a validated regional rebuild to recover plausible-looking contaminated variables.

## Private regional rebuild on forest

Rebuilt 96 monthly mean and population-standard-deviation GeoTIFFs and eight
relocatable VRTs from the four original E-OBS v19.0e series. Each has 25,202
days from 1950-01-01. A bounded streaming read used NetCDF fill values, tracked
per-cell valid counts, applied each variable's stored scale, preserved the
original affine coordinates and wrote EPSG 4326 explicitly. Confirmed all
written pixels against the calculated masks and statistics and checked that the
new VRTs use relative source filenames. The published raster tree was left
alone. The private rebuilt tree and scripts are retained under
`/var/tmp/wepppy-eu-run-recovery-baseline/`.

The candidate HTTP provider and regular CLIGEN client again generated all
10,957 valid daily rows for the original station. The offshore control remained
uncovered. The previous mixed-record rainfall control passes January and fails
in August where the rebuilding and sampling still cannot supply coverage.
The resumed fixture used the original pinned station. The private data are
ready for full forest deployment verification.

An independent NetCDF masked read reproduced the January and August mean and
standard deviation at four coastal, inland, offshore and mixed-record
controls for all four measures. At the mixed-record rainfall control, January
had 83 valid daily observations and August had zero.

## Forest provider override

The forest replay's private Compose overlay supplies
`EOBS_METQUERY_URL=http://metquery:8004/` to `weppcloud`, `rq-engine`,
`rq-worker`, `rq-worker-batch`, and `rq-worker-fork-archive`. It also mounts
the rebuilt E-OBS tree read-only at `/geodata/eu/e-obs` in metquery.
Select the retained `forest-eobs-verified.compose.yml` overlay with
`WCTL_COMPOSE_FILE_EXTRAS` when reproducing the forest validation.
The shared Compose configuration uses the application's default provider.
