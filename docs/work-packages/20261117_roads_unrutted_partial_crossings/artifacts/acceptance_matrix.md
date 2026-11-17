# Scoped acceptance and evidence matrix

**Status:** RUPC-01 validated (191 scoped tests and native slices); RUPC-02 validated with 199 scoped tests and separate native receipts.
**Operator direction:** 2026-11-17, “scope tests to the implementation changes.”
Do not run the full repository suite or unrelated frontend/stub gates. Select
specific tests for changed functions and confirmed consumers; add adjacent tests
only when shared behavior actually changes. Native artifact checks below remain
required because they validate the changed implementation boundary.

## Input and geometry cases

| Case | Required evidence |
| --- | --- |
| Contour road with longitudinal reversal | Unrutted crossing retained; corresponding point-source segmentation unchanged. |
| Partial crossing below 60% | Valid strip executes with documented required parameters. |
| Connected features with identical attributes | Stable geometry/accounting under equivalent feature subdivision and input order. |
| Multipart hillslope polygons | Group by original hillslope identity without losing intersections or overwriting diagnostics. |
| Narrow/full crossing, oblique crossing | Positive native OFEs; total hillslope closure; road-area target/model readback. |
| Infeasible road area or competing strips | Ratified approximation/failure policy with visible residual and reason. |
| Switchback/repeated crossing | Deterministic bounded abstraction and limitation text; no claim of verified connectivity. |
| Insloped and rutted road controls | Existing split, routing and generated input behavior preserved. |
| No-road partitioned control | Use unchanged baseline soil/management/climate/OFE layout with two half-width profiles; report annual/total runoff and sediment differences as a diagnostic, not an assumed response-equivalence gate. |
| Near-zero upstream/remainder dimensions and rounding | Parsed native positivity and 1e-6 m² input-area closure; explicit small-remainder absorption and no hidden WAT/PASS rescaling. |
| Missing fill/buffer fields | Explicit actionable error; no invented defaults. |

## Runtime states (separate from geometry)

| State | Contract checkpoint must specify |
| --- | --- |
| Never-used/absent Roads state | Existing valid setup workflow remains reachable. |
| Present-empty / no usable overlap | Valid zero-contributor runs retain baseline-equivalent success; attempted invalid/failed contributors remain failures; no late comparison crash. |
| Populated/current preparation | Fresh strip execution and replacement results. |
| Supported legacy monotonic preparation | Explicit invalidation/reprepare; retained historical outputs readable. |
| Working, failed, completed | Inspectable artifacts/status; no stale output advertised as fresh. |
| Archive/restore and retry | Retained inputs/provenance preserved; deterministic regeneration. |
| Malformed geometry or invalid dimensions | Bounded validation error without partial current-result publication. |

## Generated-artifact chain

Record exact candidate revision, binary, configuration and input hashes. On a
disposable actual-project copy, trace upload and reloaded state to prepared
crossings and strip accounting; parse generated `.slp`, `.sol`, `.man`, and run
files; execute native WEPP; parse contributor PASS files; read back the actual
combined PASS consumed by the watershed; inspect fresh watershed/report outputs.
Do not replace writers or combiner with mocks for this chain. Verify timing,
units and extensive versus intensive quantities; avoid naive averaging or
summation of all PASS fields. Verify no baseline double count and area closure.

Retain road target/model/residual area alongside original/affected/remainder
hillslope area. Inspect user-facing limitation text and artifacts through normal
project authorization. Native failures and missing-field cases must retain useful
failure evidence. Run 141 and 42 cases with documented parameter provenance.

## Candidate test anchors

Start with targeted cases in `tests/nodb/mods/test_roads_monotonic_segments.py`
and `tests/nodb/mods/test_roads_controller.py`. Inspect
`tests/wepp/interchange/test_roads_accounting.py`,
`tests/wepp/interchange/test_roads_lifecycle.py`, and
`tests/tools/test_roads_pass_completeness_r7.py` for affected consumer cases.
Use existing Rust combiner tests only if combiner logic changes; exercise its real
API regardless. Route/UI/RQ tests are conditional on actual changes to those paths.
Record exact selected node IDs and results once the implementation diff exists.

## Review evidence

Before code: two independent read-only contract reviews and disposition.
Before closeout: independent correctness review from the repository template,
dedicated security review for native/file boundaries, and no unresolved medium/high
findings. Reviews must cite executed scoped evidence and name uncovered limits.
Scaffolding is not a passing review or a completed implementation.

## RUPC-02 incremental acceptance (validated locally)

| Case | Required evidence |
| --- | --- |
| Ordinary upstream > 0 | Existing placement, area and role behavior unchanged. |
| Upstream zero/negative; road + fill < H | No upstream OFE; road/fill/downhill landuse; original and adjusted position retained; zero upstream runon disclosed. |
| 0 < downhill < 10 m | Keep positive section; native parse and run succeed without area loss. |
| Road + fill = H | Native road/fill layout and parameter roles correct; no zero-length landuse. |
| Road + fill > H | Explicit fit failure with dimensions and recovery guidance; no fill shortening. |
| Tiny remainder and floating correction | Downhill adjustment, never upstream creation; parsed area closure <= 1e-6 m². |
| Missing/invalid fields | Existing validation errors; top placement cannot hide missing inputs. |
| RUPC-01 prepared candidates | Reuse preparation; old execution remains historical; Run required for current RUPC-02 output. |
| Absent/empty/malformed/restored/failed state | Existing valid outcomes and retention preserved; marker absent cannot imply current RUPC-02 execution. |
| Full copied upload | Retain prior failure evidence and per-crossing new dispositions for all eight; real PASS and watershed/report checks for successful execution. |

Scope new tests to changed implementation and confirmed consumers. Prior reviews
and successful 141/42 slices do not establish RUPC-02 conformance.

RUPC-02 lifecycle cases must distinguish pure non-unrutted (marker exempt), mixed,
and all-unrutted-but-excluded (marker required) attempts. Test missing, malformed,
unknown and summary/row-mismatched markers, with no fabricated row for empty runs.
Old affected archives restore successfully as historical without provenance edits;
unaffected archives keep existing admission. Failed attempts never become current
merely by having a marker. Read back upstream/downstream compensation fields
separately so area transfer is not mislabeled.

RUPC-02 receipts: `20261117_top_placement_scoped_tests.log`,
`20261117_top_placement_native_evidence.json`, and
`20261117_top_placement_reviews.md`. Original 30 m-fill inputs deliberately retain
five fit failures; the 5 m-fill full run is separately labeled synthetic acceptance.
No deployment or scientific site calibration is implied.
