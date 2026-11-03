# Current project v2: controller outcome QA

Reviewer: `mipa_qa`, 2026-11-03 UTC. **PASS for the bounded public-controller
baseline workflow.** The missing-directory failure from v1 is repaired by the
canonical initialization in fresh v2. This does not establish RQ, catalog,
browser, later Roads workflow or parameter acceptance.

Independent read-only receipt `resumption-r7-current-project-v2-native-readback.json`
has SHA256 `7cc96450086f02474dd723c2b01b3dd15bf2ec913d98c30180c29935e3f07de6`.
Its additive helper `read_current_r7_native_v2.py` has SHA256
`ed639fd73f73960748a4815543c7711cec4efdc2b9bffe9ee7acc13fc720fa61`.
The helper ran through `wctl exec`, using installed readers, without native calls
or converter execution. Frozen v1 helpers, receipts and outputs remain unchanged.

- All 344 declared inputs remain unchanged. All 67 traces identify the declared
  binaries and show native success, UI/groundwater/PMET activation and all 16
  simulation years. Raw PASS covers 385,704 expected daily hill records;
  installed WAT covers 1,127,892 records for all 193 OFEs; raw channel WAT covers
  157,788 records for all 27 channels. Available WAT values are finite and
  ELEMENT SedLeave is nonnegative. All **470 raw outputs match v1 byte for byte**.
- The completion receipt binds all 494 output/interchange files. Seventeen
  required hill, watershed and summary interchange products are readable and
  nonempty. The installed `Wepp.loss_report` reads 66 hills, 27 channels and
  11 outlet summary entries, with 44.33 ha contributing area. Annual outlet
  summaries cover 2000–2015.
- Configured `loss.tif` and `loss.WGS.tif` open with valid georeferencing and
  finite data. The GeoPackage opens with 66 subcatchment and 27 channel features;
  both GeoPackage and FileGDB export ZIPs pass CRC checks. Export and raster
  hashes are retained in the receipt. The run log reaches `Watershed Run Complete`
  and controller completion without a traceback.
- Runs, output, plots and export inventories are identical before and after QA.
  The review did not modify those artifacts or read withheld native outcomes.

Configured exports were exercised rather than disabled. The logged GeoPackage
POLYGON/MULTIPOLYGON compatibility warnings remain visible; successful artifact
readback is not a separate claim of strict vector-format conformance. The native
channel PMET fallback from `Fallow m` to `loam-forest` also persists and is retained
verbatim in the machine receipt. Uniform hill PMET coefficients do not test
distinct-coefficient ownership. InterceptionStorage remains unavailable, and no
dynamic snow-consumption trace or complete water/particle closure is claimed.

The unchanged raw results isolate this bounded recovery to initialization and
postprocessing, without suggesting a new native scientific result. Fresh Roads
copies still need all four designs, explicit accounting checks, and the retained
full-upload unrutted negative geometry case plus the separately pinned
OSUNUM6-excluded positive control. The original source and frozen scientific
acceptance gates remain unchanged.
