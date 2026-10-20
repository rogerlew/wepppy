# Validation and release handoff

## Revisions and scope

- WEPPpy baseline: `fc67fcad6622202955c18635dd7a0b053ee875a2`.
- Reviewed contract checkpoint: `9651d7af6`.
- WEPPpy implementation: `4d31ef93d`.
- Native baseline: `0515272453e36fe071c7812fb9d8ca2cf1642d08`.
- Native release: `5e42716230dd6f02d218bfbe10509d501edb93a8`.
- Final interchange SHA-256:
  `669579b0e95bc035ce318b1ea49e288b10c20fcbf3e9e7e78739f46931a5be02`.

The canonical Python 3.12 release path, WEPPpy startup preflight, literal startup
regression and image source ref are paired. Only local commits and development
Gunicorn worker reload occurred. No push, image publication, production deploy,
WEPP rerun, or original-project repair is claimed.

## Executable gates

| Gate | Result |
| --- | --- |
| Native release `test_hillslope_watbal.py` + `test_totalwatsed3.py` with `WEPP_INTERCHANGE_TEST_BINARY` pointing to the final release library | 72 passed |
| `PYO3_PYTHON=/usr/bin/python3.12 cargo test -p wepp_interchange_rust` | 107 unit + 17 writer integration passed |
| Final paired startup/report/cache/generated-event-SQL/water-export selection | 99 passed before final joined-date fix |
| Final water-weighting + export service + carrier materializer tests after COR-06 | 112 passed |
| Hillslope report tests, including unequal hillslope-area watershed weighting | 14 passed |
| WEPP interchange/export controls | 113 passed, 1 skipped |
| `wctl run-npm test` | 119 suites, 987 tests passed |
| `wctl run-npm lint` and direct ESLint of both edited dashboard modules | Passed |
| `wctl run-pytest tests --maxfail=1` | 10,818 passed, 126 skipped; stopped on container browser-path configuration |
| WEPPcloud remainder with corrected process-scoped Playwright path | 2,023 passed, including the previously blocked browser test |
| Changed broad-exception enforcement against `origin/master` | Passed, no new broad catches |
| Scoped docs lint | Passed after closeout edits |
| Independent correctness review | All six findings closed; serialized and live readback passed |

A first broad attempt found the startup test's old literal hash; it was paired
with the new release before the current broad run. The final focused export run
covers COR-04 through COR-06, which landed after broad collection.
The broad run stopped at 98% because `PLAYWRIGHT_BROWSERS_PATH` omitted a
`wepppy/` path component. The entire final `tests/weppcloud` segment then passed:

    wctl exec weppcloud env PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers PYTHONPATH=/workdir/wepppy /opt/venv/bin/pytest tests/weppcloud --maxfail=1

This completes broad coverage in segments, not one uninterrupted green run. Existing NumPy/Pandas warning
output on deliberately nonfinite regression inputs is retained in test logs.

## Scientific and serialized evidence

The baseline heterogeneous fixture failed at the actual native and export
boundaries: two daily contributions require ET 10/Dp 14, not summed local depths
or terminal-only values. Tests independently derive the 250/750 square-meter
oracle: daily ET 5/Dp 7, component depths 3.25/.875/.875 mm. They cover subdivision,
sparse days, merged IDs, selected/baseline SQL, invalid areas/components, hidden
Area, joined collisions/null dates, absent observations, cache generations and
unchanged routed metrics. TotalWatSed and the daily Python loader are controls.

The isolated complete project is
`/wc1/runs/mo/mofe-et-dp-validation-20261020`; source is copied from
`/wc1/runs/in/incorporate-cerebrum`. Both H.wat files retain SHA-256
`e6783c21665859cf33382f592f3b007c7f059780e3a0b6736af9982a6f7caf44`.
The final native library matches independent daily SQL for all 8,557,275 input
rows aggregated into 10,465 hill-years across 455 hills. A real multi-OFE hill
(40,175 rows, 8,035 days) also matches the daily loader and calendar export oracle.

Authenticated live HTML and CSV annual results match every hill's independent
ET/Dp oracle, using the unchanged divisor 22. Actual selected and baseline event
queries each match all 455 hills on 2002-07-01. The synthetic browser check separately
exercises differing ET 5/ET 7 and unavailable values. Report cache browse works;
report Parquet and four export bundle downloads match retained local bytes.
Normal run-entry redirects establish scoped browse cookies; no auth bypass was
used for the live checks. Fresh-process view rendering is separately labeled as
a harness outside authorization decorators.

Production export service execution uses
`/wc1/runs/mo/mofe-et-dp-export-20261020`, containing one actual MOFE hill's WAT
rows with original Arrow metadata plus the copied project geometry. CSV and
Parquet each contain one observed hill; GeoJSON and GeoParquet retain 455
geometries and null water values for absent observations. All four serialized
formats match the independent 2002-07-01 oracle ET 3.61/Dp 0 mm. GeoParquet CRS is
EPSG:4326; all identities and dissolved polygons match the original source.
WEPP3 / Topaz31's metrics attach to its own polygon, never WEPP31 / Topaz163.
This readback exposed and repaired a pre-existing identity-domain collision
(COR-06). Export cache v3 invalidates intermediate v2 results. Fixture writer
readbacks additionally cover all three temporal modes and long layout.

The existing GeoJSON ZIP writer wraps its FeatureCollection in a payload envelope.
Numerical readback inspects that collection; standard standalone GeoJSON/GIS
compatibility is not claimed. Changing that format contract is a separate
follow-up. GeoParquet supplies the real GIS-readable spatial acceptance here.

See the retained JSON receipts and reproducible scripts in this directory.
Larger native tables, live HTTP values, CSV files and screenshots remain in the
isolated projects' normal artifact paths, with hashes in the live manifest.
Existing canonical archive/restore regression verifies report cache, provenance
and failed-attempt bytes. Original project data was never regenerated.

## Performance and maintainability

The current representative 217-hill source is 75,354,414 bytes, different from the
historical 81,150,978-byte fixture in the cache contract. Final native timings are
1.20-1.25s at about 79 MiB peak RSS. Complete report rebuild 1.89 s and settled mean
12.4 ms meet the representative 2 s/30 ms budgets. These are OS-cache-warm storage
measurements, not cold-disk benchmarks. The larger 164 MB MOFE project takes 5.39 s
native. A separate fresh-process report series measured 5.69 s initially,
0.58 s on the next construction, and 12-13 ms for the following four settled
constructions. The existing digest admission guard is temporal (one second),
not size-based; an immediate repeated constructor is not a settled-cache benchmark.

Observe-only telemetry reports temporal materializer function length 179 to 201
and file SLOC 655 to 743. The added local-flux helper and separate local date stream
are necessary to preserve routed semantics and correct joined-source absence;
no generic reduction framework was introduced. Carrier/join functions grow by
9/12 lines to derive ET and retain actual renamed source columns. Existing JS
maximum complexities remain 33 and 155. Python cyclomatic complexity was not
measured because the local optional radon tool is absent. Existing root quality
reports were left untouched; telemetry was written to task-specific temporary
files. No further refactor is required by this observe-only gate.

## Rollout and cache recovery

Publish the native commit before any image build referencing it, then publish
the paired WEPPpy revision through the existing authorized release workflow.
Verify the startup SHA and actual imports and restart importing services through
the established deployment procedure. This package does not authorize rollout.

With H.wat and mapping available, the next report request atomically rebuilds
an unmarked summary and verifies `mofe-area-v1`; no bulk cache deletion is needed.
The export version marker prevents reuse of old products. Missing historical
dependencies retain explicit `historical_unverified` access under existing guards;
that does not certify corrected values. A callable obsolete writer cannot publish
a replacement. Rollback must pair compatible native/Python versions and retain
source/provenance evidence. Historical archives and old standalone R helpers
remain intact; only the disabled balance in `new_report.Rmd` was removed.

AgFields mixed-source many-to-many admission remains an explicit limitation.
Duplicate raw daily OFE rows remain malformed upstream input. Annualization,
precipitation and routed-field policies are deliberately unchanged.

Final acceptance: M0-M5 complete in development. The geometry-boundary helper
adds 44 service lines to enforce the existing ID mapping contract; it introduces
no new architecture or dependency. No open correctness review findings remain.
