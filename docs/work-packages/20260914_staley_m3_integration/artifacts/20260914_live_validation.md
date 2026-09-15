# Development acceptance and final validation

Status: implementation, live technical acceptance and final full Python/frontend
regressions complete. Package closed 2026-09-14 after explicit owner acceptance
of SEC-06 without rotation; see [closeout](20260914_closeout.md).
No production deployment, shared soil rebuild or shared cache refresh occurred.

## Scope and identities

Source/dispatch checkpoint: `6f64d45a0`; production checkpoint: `b998d44e2`;
final UX/code/evidence checkpoint: `e36c3eb54`.
The subsequent bounded UX correction adds an explanatory `partial_reason` to
accepted state and renders it as text, fulfilling the existing UI contract.
Scientific coefficients, source policy, masks and table schemas are unchanged.
The development rq-engine and rq-worker use UID 1000 / GID 993. Published
results were independently checked as UID 1000 / GID 993, mode 0644. Only these
idle development services were reloaded; no production host was touched.

## Bounded source delivery

The generic path derives original in-basin keys and THICK bounds per project.
Two independent analytical grid/key fixtures exercise activation/execution,
primary/missing sources and rejection of changed authority. Separate composition
tests cover mixed primary/fallback and disjoint missing support. None uses a
named-basin runtime branch or hand-authored project manifest.

The genuine acquisition retained SDA collection evidence for two SSURGO and
eight STATSGO keys, plus six 64-KiB THICK range bodies (393,216 bytes total).
The full object was not downloaded. Original survey vintage of cached horizons
remains unknown; current SDA collection evidence does not establish that vintage.
The first attempt decoded native THICK but failed to serialize its NaN NoData
metadata. It remains visible, unmodified. Reviewed offline replay reconstructed
the receipt without another network request and verified the original native
raster; NaN metadata is represented explicitly without altering samples.

Activated receipt:
`/wc1/runs/ad/addicted-reservist/postfire_debris_flow/source_preparation/d0a0f389b467467ab56d69b1b2b14701/receipt.json`.
SHA-256: `7a84a1c96e4e684c65d6aea4ffdd8dbf3f0b114cdf4211d09d30873bcab9b134`.
Authoritative activation returned `committed`, with no warnings. See the
[reader review](20260914_network_reader_review.md) for bounds and tamper tests.

## Real development RQ/browser results

The browser used normal development login/CAP/session-token/CSRF transport,
discovered configuration, operations, pipeline and readiness, then submitted
the existing Run control. Job status/info, current state, exact-mask download,
reload, model identity and SI/English display were checked. Credentials, CAP
tokens, JWTs, session storage and raw Playwright errors are not retained.

| Case | Job | Accepted attempt | Scientific outcome |
| --- | --- | --- | --- |
| Genuine basin M3 | `8bfbab39-cd3f-495b-b8c4-f5939f6b974e` | `1e2504aae0b04a1db96caa18023188ab` | 4,311,420/4,311,420 soil/SBS cells; T unavailable from potentially truncated terrain |
| Genuine basin M1 | `15e0ebba-789a-497f-b60a-829a28e841f6` | `72d15190034445108ba40742d30c34ff` | 4,311,306/4,311,420 cells, 114 excluded; all requested rows available |
| Controlled synthetic M3 | `47bf3c64-3d7f-459a-a4d6-aa3dafffbe5f` | `08faca63704e476cbeb79d606a715278` | 3/3 cells; real installed WBT/RQ, all requested rows available |
| Synthetic M3 after UX correction | `b77aba77-9e1c-4642-b192-ac80d24a462a` | `5d2980fedf0f4e7197075469334b8993` | Positive-result workflow passes again |
| Genuine M3 after UX correction | `528f1c22-0315-4a49-b164-c5b5f28a90f7` | `8a6aac78039d4a4fab781e879368372e` | Terrain explanation persists after reload; all workflow checks pass |
| Genuine M1 final compatibility | `9645f921-fdb4-4147-9894-d87b1ebc826e` | `34adfb822ae34c9789c04e620efe77ca` | All workflow checks and independent arithmetic pass; left as the current live result |

The genuine basin has 1,123 domain cells on the DEM edge. Full soil/SBS coverage
does not establish full upstream terrain. Native relief is 719.650390625 m,
but the accepted terrain rule correctly withholds T; all 27,669 event, 12 design
and three inverse rows remain explicitly unavailable. This is input evidence,
not a reason to weaken validity, shrink the basin or rebuild the live project.
Final UX review required the summary to explain that distinction; its bounded
message is “Elevation coverage does not establish complete upstream terrain.”
Independent correctness review closes the finding using actual post-reload DOM
text, accepted state and rendering tests. The final M3 PNG is blank and is not
claimed as visual proof; earlier screenshots remain retained.

Independent arithmetic checks transcribe Table 4 and do not call the scalar
production functions. Genuine M1: T=0.05623725154280397,
F=0.32028958810160973, S=0.4144476556758421; all 27,669/12/3 rows match.
Synthetic M3: T=30/sqrt(300), F=2/3, S=100/254; all 90/12/3 rows match.
Both independent reviewers rechecked rows and downloaded-mask bytes.
Final post-correction bundles were independently recomputed again; see
`m1_numbers_final.json` and `m3_numbers_final.json` in the retained roots.
This proves runtime conformance, not field predictive accuracy or applicability
of these out-of-study-size validation basins.

Retained roots:

- `/wc1/runs/ad/addicted-reservist/postfire_debris_flow/validation/20260914_m3/`:
  `browser_m1/`, `browser_m1_final/`, `browser_m3_inspect2/`,
  `browser_m3_final2/`, `browser_browse2/`, numerical reports,
  protected inventories and archive report. Failed browser trials remain beside
  the successful evidence, including incorrect early smoke assertions about
  M1-only upload summaries and project-specific display units.
- `/wc1/runs/pf/pfdf-m3-validation-20260914b/postfire_debris_flow/validation/`:
  `browser_m3/`, `browser_m3_final/`, numerical evidence. This is explicitly
  synthetic, prepared from a canonical fork of a small disposable validation
  template. Copied legacy module records remain under `template_history/`.
- The earlier isolated fixture `pfdf-m3-validation-20260914` retains its expected
  `migration_required` rejection, without bypassing or rewriting legacy records.

## Noninterference and archive/browse

`protected_before.json`, `protected_after.json` and post-final-M1
`protected_final.json` independently compare exactly
22,357 files (~13 GB): `soils.nodb`, `rusle.nodb`, `soils/**`, `rusle/**` and
`wepp/runs/**`. **Zero changed, removed or added protected files.** Real NoDb/native
tests additionally compare these surfaces around M3 success, result-writer
failure and retry, on both independent grids and with absent/full sources.

The [independent builder comparison](soil_builder_regression_review.md) proves
eight base/candidate cases, including historical SSURGO and STATSGO records and
depth-valid/WEPP-invalid component selection. All 22 built soils, 44 downstream
soil files and 44 actual `.run` files per revision match. Source routing,
substitution precedents and existing NoDb soil gates also pass. Its stated
limits do not claim a full live soil rebuild.

Canonical archive/restore ran against a fresh module-only copy, never the live
project: `/wc1/runs/pf/pfdf-archive-validation-20260914/`.
All **521 files** are byte-identical after restoration, including 111 preparation
records, 13 HTTP bodies, 24 SQLite-related files, nine masks, one failed
acquisition record and two native THICK windows. The retained ZIP is
`archives/pfdf-archive-validation-20260914.20260915T012636Z.zip`.
Only disposable copied payloads were replaced during restore; the ZIP preserves
them. This exercises the canonical filesystem engine, not archive API admission.
Ordinary authenticated browse and download returned HTTP 200 and exact hashes
for failure JSON, native THICK, HTTP body, receipt, copied WAL and exact mask.

## Gates and qualifications

- Final full Python (`wctl run-pytest tests --maxfail=1`): **8,602 passed,
  103 skipped**, 3,128 warnings, 1034.93 s, exit 0. The earlier 8,590-pass sweep
  predates the final two-grid/partial-message additions.
- Final production/runtime gate: **70 passed**; covers two independent basins,
  finalization authority and success/failure/retry noninterference.
- Network/results combined gate: **81 passed**; final reader-only gate: 26 passed.
- Independent existing soil gate: **78 passed, 5 network-dependent skips**.
- Canonical archive regressions, including added M3 source/WAL/mask records:
  **22 passed**.
- Final npm lint passes; full npm: **111 suites, 877 tests passed**.
  Controller bundle rebuilt; targeted controller gate: 23 passed.
- RQ graph, preflight Go tests, stub hygiene and changed broad-exception
  enforcement pass. Package/module/UI docs lint and diff whitespace checks pass.
- Module stubtest could not run: mypy build errors report missing typing for
  installed rasterio/pyarrow/whitebox and preexisting unannotated containers
  in `results.py`. No stub surface changed; no suppression or dependency was
  introduced to make this optional diagnostic appear green.
- Targeted isolation checker: both seeded runs and all three per-file runs
  pass tests; tool exits 1 for `pyexpat.errors`/environment-state observations.
  The unchanged Fairpoint soil suite reproduces the same two observations.
  No randomization plugin is installed. These are shared harness/import-state
  observations, not a suppressed test failure. An accidental default five-full-
  suite diagnostic was stopped and replaced with the scoped check.
- Observe-only [quality telemetry](code_quality_final.md) reports longer native
  composition/acceptance routines in the yellow function-length band. Keeping
  sequential hash/authority/publication checks adjacent is deliberate; no
  unrelated refactor or threshold waiver was introduced. Source reader helpers
  remain in the green file/function bands.
- Exact-value secret scan: **524 text files, zero matches** across package and
  live validation records. Only counts and matching filenames were emitted;
  this does not remove the separately recorded earlier tool-output exposure.

Final scientific/runtime limits: historical cache lineage vintage unknown;
genuine basin terrain unavailable; synthetic positive evidence is not field
validation; reports/dashboard and production deployment remain outside scope.
SEC-06 is closed by explicit owner risk acceptance; package archival is complete.
