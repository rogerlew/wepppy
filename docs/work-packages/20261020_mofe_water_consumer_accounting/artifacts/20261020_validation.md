# Development validation

## Release pairing

Contract checkpoint: WEPPpy `6e689a902`; upstream schema exception:
wepp-forest `04f1c4d26`. Native implementation `21d2d93`, final performance/release
commit `54d0867`; final interchange SHA256
`60b8da3c77aa8465e262b8978ac173ba681d14745de7aec74392db9308c5c5eb`.
Startup preflight and image-source pins are paired. The development release
library was replaced atomically and web workers gracefully reloaded. An initial
live report request explicitly rejected a worker still holding the obsolete native
aggregation marker; the paired fresh process and reloaded browser checks pass. No push,
image publication, production deployment or historical project repair occurred.

## Numerical and artifact evidence

- Native suite: 163 passed; Rust: 107 unit and 17 writer tests passed.
- Expanded export/loader/dashboard/provenance suite: 230 passed.
- Paired report/cache/archive/provenance suite: 79 passed.
- Ash and audit-tool follow-up: 32 passed. Frontend: 987 passed; lint passed.
- Stub completeness, daily-loader stubtest and changed broad-exception enforcement
  passed. Stubtest also exposed four existing undeclared public constants; their
  declarations are now present without runtime changes.
- Actual unequal-length three-OFE replay: five-year ordinary and hourly runs
  complete; hourly header confirms the hourly seepage path. Serialized native
  report, daily loader and feature-export values agree with the daily oracle.
- Actual export service: CSV/Parquet/GeoJSON/GeoParquet ZIP members preserve
  keys/geometry/CRS and agree on the nonzero 2022-11-04 event: P 111.8, Q 122.4746,
  terminal lateral 2.1700005359mm. Selected/base live queries agree on P/Q/ET.
- Real HTTP HTML/CSV report, browse and all five report/export downloads pass.
  CSV and browser numeric cells agree with annual Parquet using the unchanged
  five-year divisor (six observed water-year bins). Event ET is 1.61mm.
- Actual Ash model and native post output use fresh replay water; the baseline
  is explicitly constructed from one hill's PASS, not a routed watershed run.
  Corrected flow agrees with modeled replacement plus the retained lateral term.
  The real `AshPost.run_post` facade also publishes all five artifacts, schema
  manifest, README, NoDb return periods and catalog entry; current warning is null.
- Historical watershed and contaminant reports on an isolated fixture both
  return HTTP 200 with visible historical/unverified notices. Initial no-results,
  missing translator, pickle-only, malformed/partial proof, source replacement,
  changed mapping and failed-refresh preservation regressions pass.

## Performance

Final library, 3.57 million single-OFE rows: native 1.19–1.23s; complete report
rebuild 1.88s; settled report mean 12.67ms. 8.55 million MOFE rows: native 7.39–7.50s;
complete report 8.52s; settled mean 14.23ms. Imports and translator are warmed;
these are complete cold-cache builds, not cold-storage claims. Retained JSON
receipts bind the exact binary. Compact daily uniqueness tracking and cached
group mapping preserve the pre-existing single-OFE rebuild budget. Large-MOFE
cold rebuild is slower than the prior ET/Dp-only observation of 5.69s: the new
outlet-volume and daily uniqueness checks add work. Settled MOFE reads preserve
the existing fast-hit budget; no general MOFE cold-speedup claim is made.

## Scientific limits and failures retained

The original six-year isolated model replay fails with SIGFPE in evap.for in 2025;
bounded five-year replays pass. No physics change was made. Contour normalization
is source-supported without runtime certification. Historical artifact hashes
do not establish producing-binary lineage. Raw TotalWatSed Q/QOFE stay diagnostic
and its sparse lateral behavior stays a documented legacy limitation.

Both legacy R calc_watbal functions were executed in the actual R container:
single-OFE input succeeds and MOFE input fails explicitly. Original projects
and closed work-package artifacts remain intact.

The first broad pytest run stopped after 506 passes/28 skips on the old expected
native SHA; the paired-release assertion was updated. The second stopped after
2,970 passes/48 skips on a same-tick source-rewrite regression. The loader now
captures its digest before reading, with reuse limited to one explicit Ash batch;
new batches and standalone loads rehash. Independent collision/retry review and
33 focused tests pass, followed by repeated real Ash model/facade publication.
The broad resume omits only the two expensive disturbed-soil matrices already
passed in the second run. Its process-local PLAYWRIGHT_BROWSERS_PATH points to
the installed browsers (the configured path omits the inner wepppy directory).
The browser environment was independently verified by eight run-catalog tests.
The resumed result is **10,703 passed, 126 skipped** in 1,201.09s. Combined
coverage includes the previously passed disturbed matrices and the final 33-test
provenance run; this is not a claim of one uninterrupted full-suite pass.
Code-quality observability ran to temporary files without overwriting unrelated
working-tree reports; Python complexity was unavailable because radon is absent.
The telemetry is observe-only. No new production broad exception was introduced.
