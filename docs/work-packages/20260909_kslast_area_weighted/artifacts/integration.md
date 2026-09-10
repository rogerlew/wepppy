# Full forest WEPP acceptance

Confirmed 2026-09-09 UTC. Normal RQ `run_wepp_rq('seductive-sabra')` submission:
`90431b48-4138-4f28-89f6-90a5b3806f7e`. All 15 parent/descendant jobs finished,
including MOFE prep, climate/remaining prep, 505 hillslope simulations, watershed
prep/model, hillslope and watershed interchange, totalwatsed3, water balance,
return periods, GeoPackage export and final completion. Final job
`a880a403-5d42-4346-9940-aeb4fb42ace0` ended at 2026-09-09 23:56:19 UTC.
See [job tree](integration-jobs.json) for timestamps and dependency IDs.

The configured 46-year simulation, MOFE mode, default 0.05 and wepp_260430 model
were unchanged. The watershed log ends with year 46 and successful completion.
No re-abstraction, no-prep workflow, shortened simulation or model substitution
was used. Final fresh web/worker import hashes are in release_manifest.json.

The independent oracle uses math.fsum over every included subwta cell; it does
not call the native reducer for expected values. Results:

- Exact CRS/affine/dimensions on the aligned Float64 map; saved nodata -9999.
- 505 hillslope means and coverage counts agree at rtol/atol 1e-12.
- Every one of 1259 generated restrictive-layer OFE values agrees at 1e-12.
- Zero developed exemptions in this real project; synthetic real soil workers
  cover both exempt and nonexempt cases in both preparation modes.
- Full coverage on all hillslopes: zero missing-area defaults. Missing pixels
  elsewhere in the project rectangle remain nodata.
- 25 regenerated Parquet/report tables parse, with 70,151,967 total rows and
  finite non-null floating values. Fresh timestamps exceed this submission;
  per-table row counts and hashes are recorded in integration-verification.json.

Earlier example keys 202, 212, 232, 252, 263 and 282 all average 0.0001. Keys
292 and 293 average 0.05293050847457627 and 0.08279795918367347, reflecting their
whole raster footprints. See kslast-summary.json for all hillslopes. Hydrology
is intentionally not required to match the prior centroid parameterization.

The driver now requires the complete successful job tree before final verify.
The earlier input-and-hillslope-verification.json records only the interim
seven-table check; final acceptance is integration-verification.json (25 tables).
