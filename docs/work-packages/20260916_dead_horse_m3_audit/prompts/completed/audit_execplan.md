# Audit Dead Horse Creek M3 against Rengers et al. (2024)

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


Explain whether the user's saved Dead Horse Creek M3 probabilities are computed
correctly and whether the available observations support an external validation.
The deliverable is a reproducible audit and findings, not changed model behavior.

## Progress


- [x] Scope, reference and accepted attempt identified, 2026-09-17 UTC.
- [x] M1: inventory and protect saved run; inspect source and report identity.
- [x] M2: independently recompute predictors, support, probability and inverse tables.
- [x] M3: compare SBS, basin extent and observed rainfall/response with paper/data.
- [x] M4: retain findings, preservation evidence, lint and close package.

## Surprises & Discoveries


The 26.8329 km² basin has only 54.4708% shared SBS/soil support. Missing SBS
accounts for all exclusions: 97,075 native value-127 cells and 25,093 outside
the official raster. Soil thickness covers the entire basin. Its climate
contains 100 simulated years rather than observations of the 2021 storms.

## Decision Log


The owner selected https://nhess.copernicus.org/articles/24/2093/2024/ as the
comparison on 2026-09-16. Use its documented M1 scope and uncertain Dead Horse
Creek timing explicitly; do not label a mismatch an M3 implementation defect.
No live mutations or model reruns are required for an audit of saved results.

## Outcomes & Retrospective


Completed 2026-09-17 UTC. Independent arithmetic, source and authenticated
report checks pass; findings.md contains four scientific limitations. All 181
protected files unchanged. No product changes. Exact storm-pair validation is
not established because published timing is uncertain and raw CSV requests
returned 403. This audit is complete with explicit limitations.

## Context and Orientation


Repository: `/home/workdir/wepppy`. Run: `/wc1/runs/th/thespian-cleanness`.
Accepted manifest: `postfire_debris_flow/manifest.json`; attempt:
`0a34c96cd0dc4e6bb7bb7780d8f8915b`. M3 predicts occurrence probability using
terrain ruggedness T (full upstream relief divided by square root of area),
moderate/high burned fraction F and recorded mean thickness in cm divided by
254 (S). F and S use common valid raster cells; T retains the full basin.
Source policy is `recorded_depth_v1`. Current domain contracts are in
`wepppy/nodb/mods/postfire_debris_flow/docs/production_m3.md`,
`m3_terrain.md`, `staley2017_engine.md` and `production_m3_runtime.md`.
The run report is at https://wc.bearhive.duckdns.org/weppcloud/runs/thespian-cleanness/config/report/postfire_debris_flow/ .

## Plan of Work


M1 inventories relevant run inputs/results by SHA-256 and copies small scientific
records into package artifacts. Inspect the report via ordinary read endpoints.
M2 uses existing rasterio/numpy/parquet tooling within the normal wctl container
to recompute support, means, relief/area and probability/inverse rows without
calling the production scalar evaluator. Check source hashes and raw soil
aggregation. Retain scripts and machine-readable results, including failures.
M3 retrieves official SBS and available publication/data references, checks
spatial correspondence, and separates first/second-year and basin/fire-wide
comparisons. Do not infer an exact triggering storm when timing is uncertain.
M4 produces findings with numerical comparisons, severity, limitations and next
steps; repeats protected checks and validates documentation.

## Concrete Steps


From the repository root, execute retained scripts through `wctl exec -T
weppcloud python ...` when host libraries are unavailable. Scripts may write
only to this package's artifacts. Use public HTTP GET for reference sources,
retaining URL, retrieval date and hash. Run `wctl doc-lint --path
 docs/work-packages/20260916_dead_horse_m3_audit` before closure.

## Validation and Acceptance


All saved rows match independent equations within recorded floating-point
tolerances, or discrepancies have explicit findings. Raster support and input
lineage have counts and reasons, not just an available flag. Compare the
published reference at its actual spatial, temporal and model scope. Hash
checks demonstrate that the audit did not modify scientific inputs or results.
No full regression suite is needed for read-only audit scripts and docs.

## Idempotence and Recovery


No writes to the run. Retain failed retrieval/calculation diagnostics and use
new evidence filenames if superseding a finding. If the user reruns concurrently,
report that identity change and continue against the captured immutable attempt.

## Artifacts and Interfaces


Store inventories, small manifests, tabular summaries and findings under
`docs/work-packages/20260916_dead_horse_m3_audit/artifacts/`. Record source
provenance and avoid authentication secrets in retained records. Use installed
libraries only. No production interfaces change.

Revision 2026-09-17 UTC: created for owner-requested audit and paper comparison.

Completed 2026-09-17 UTC: evidence and findings retained, documentation lint passed.
