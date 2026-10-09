# Historic PRISM menu through WEPP on forest

Completed on forest, 2026-10-08 UTC. Both methods passed generated-input/model
readback; original and both cases retained; target left nearest-cell. Regression
coverage completed in segments, with bounded compatibility fixes and unrelated
test-isolation/allowlist observations recorded in artifacts/validation.md.

## Purpose / Big Picture

Enable users of continental-US projects to select historic 800 m PRISM daily data and choose monthly PRISM revision or nearest native cells per hillslope. Demonstrate generated climate and WEPP results on the user-selected forest run, not only unit tests. This is wired production behavior, not a scaffold.

## Progress

- [x] Inspect source, stack and target run; forest uses dev Compose and the run exists under /wc1/runs/ch/chemotherapeutic-scope.
- [x] Complete independent contract reviews and commit checkpoint ancestor d3b5958c5; reader floor e25299022 precedes writer exposure.
- [x] Implement catalog/menu, raw-to-CLI adapter, staged builders and regression tests.
- [x] Run focused and broad gates; targeted Python, frontend and API checks passed. Full-suite coverage completed in segments; dispositions recorded. Dev services refreshed under existing identities.
- [x] Exercise menu/RQ climate and WEPP end to end for both methods, inspect artifacts, restore portable source evidence and close independent correctness findings.
- [x] Record full-suite disposition and close documentation/package.

## Surprises & Discoveries

ObservedPRISM=9 is Daymet; new PRISM needs a new enum. Existing monthly revision uses native Rust cli_revision. Existing run is stochastic PRISM, single, 50 years, legacy generated seed 84568 (explicit override is unset), station wy481175; preserve original configuration/output before testing. No observed year bounds are set. Target has 104 hillslopes; use explicit seed 84568 for repeatable test cases, retaining the original unset override in backup.

Review found that shared same-cell CLI filenames collide under later per-hillslope precipitation scaling. Generate once per cell, then publish separate hillslope files. Diagnostic-only revision status writes must not fail an already committed build. Both fixes have focused regressions (45 tests passed together). Initial host bundle build lacked Jinja2; the canonical container build succeeded. Two initial browser probes stopped on a collapsed seed field before enqueue; expanding its ancestors resolved the probe.

The full suite stopped after 4,964 passes on valid single-input Builder creation:
adding PRISM also changes that variant's catalog identity. The ordinary-only
reader floor omitted it. Two independent reviews ratified the bounded correction
in checkpoint 5b97490e7; aggregate reader floor 6781de988 appends the missing
climate-only structure, preserving all nonclimate restrictions and prior graphs.
Builder/capability 94-test and creation/refresh 14-test runs passed. Resume broad
validation at the failed module; do not repeat unchanged completed slow tests.

## Decision Log

2026-10-08 UTC user approved the preceding walkthrough and both multiple spatial methods, end-to-end forest execution, and dev stack restart. Use previous completed calendar year as menu maximum, 1981 minimum, explicit failures for incomplete data. Use common watershed GridMET wind and station/seed; new cell mapping does not introduce synthetic spatial randomness. Proposed bounded test years 2019–2021 include leap day; finish target in nearest-cell mode with both test cases retained.

2026-10-08: preserve OpenET/AgFields mode eligibility; mode 16 integration there is separate follow-up, not claimed here. Ratified reader-first capability amendment supports the new structure without reinterpreting historical stored graphs.

## Outcomes & Retrospective

Both methods completed all 18 RQ jobs, including watershed WEPP. Numerical readback passed for all 104 hillslopes and 113,984 daily water-balance rows per case. Original run and both case snapshots are retained under the target's archives directory. Nearest-cell mode preserves 24 distinct wet-day calendars across 24 cells. Browser/download, 993-file portable restoration and committed-reader-floor reopening passed; independent review closed all four findings. Aggregate reader floor 6781de988 reopens ordinary/single-input variants with both OFE representations. Full-suite coverage completed via a 4,964-pass prefix, 5,219-pass continuation and 301-pass tail, with overlaps/skips and failed probes documented; no unique-count sum or one-clean-run claim. Detailed evidence and limitations are in artifacts/forest-results.md and artifacts/validation.md. Retain CLIGEN convergence warning, defer OpenET/AgFields mode 16 eligibility, and preserve unrelated concurrent edits.

## Context and Orientation

Work from /home/workdir/wepppy on master. New client is wepppy/climates/prism/bulk_client.py. Climate catalog lives in wepppy/nodb/locales/climate_catalog.py; core/climate.py enum and parser feed climate_mode_build_services.py and climate_build_router.py. Existing climate_observed_build.py and nodb/_derived_build.py provide staged collect/finalize. climate_build_helpers.py contains observed CLIGEN helpers and monthly PRISM revision. Climate menu uses templates/controls/climate_pure.htm and controllers_js/climate.js. Existing WEPP prep resolves climate.sub_summary; validate its actual prepared files.

## Plan of Work

First ratify docs/schemas/prism-historic-climate-contract.md and ADR with independent reviews and ancestor commit under the repo contract-first rule. Then add enum16 and catalog observed_prism_800m with spatial0/1/2; preserve9/5. Implement per-cell observed adapter with source copies, radiation conversion, wind join, raw dewpoint retention and derived flooring. Retain attempts and use existing finalize safeguards. Multiple calls existing monthly revision with final Tmin floor. Mode2 maps unique-cell outputs to hillslopes with no revision. Add tests before relevant UI/controller changes. Update users and developer/operator docs.

Run wctl focused pytest and npm gates, stub checks, broad exception enforcement, documentation lint, and full pytest. Before restart inspect worker activity and normal dev entrypoints; use wctl up/restart only affected services and propagate PRISM_CACHE_DIR via recreation. No identity/mount changes. Use current run UI/auth/RQ contracts for acceptance, back up target climate and WEPP state before authorized mutation, retain case outputs. Inspect dates, source conversions, cell aliases, CLI assignment hashes, output calendar/values, and source archive independence. Document limitations and failed probes honestly.

## Concrete Steps

Use wctl run-pytest tests/nodb/test_climate* and new PRISM tests; wctl run-npm lint/test for changed JS. Run wctl run-pytest tests --maxfail=1 to file. Live commands execute inside configured rq-worker/weppcloud identities through wctl. Discover existing authenticated test account/token handling without printing secrets. Poll RQ jobs and inspect files, not only job status. Keep evidence scripts/results under this package artifacts, no keys or tokens.

## Validation and Acceptance

Contract contains full valid-state/error and numerical criteria. Verify both methods through WEPP and menu reload. Verify bulk cache reuses cells with unchanged manifests, raw source retained, final CLI temperature/radiation/precipitation and dewpoint constraints, and source records survive portable archive/restore. No claims of atomic provider revision or observed within-day storms. Run existing suites to prevent regressions in legacy Daymet/GridMET.

## Idempotence and Recovery

Copy original live run configuration and affected climate/WEPP output before testing, record path/hash. Never restore stale NoDb snapshots over active jobs. Retain failed build attempts and logs. Rebuild normally on failure; changed-input finalization rejects stale candidates. No cache deletion or permission workaround. User authorized restart, not deleting unrelated work or interrupting active unrelated jobs.

## Artifacts and Notes

Checkpoint, ADR, review findings, targeted/broad test outcomes, live identity/configuration and per-mode generated-output evidence are required. Update this plan and tracker throughout. Retire plan when both cases and review finish.

## Interfaces and Dependencies

No new dependencies. PRISM_API returns raw SI daily frames. Existing df_to_prn does in-place unit changes, so pass only a copy. Existing CLIGEN observed mode synthesizes missing storm structure. New ClimateMode16 is additive and included in all observed-year/calendar routing. Runtime cache environment already configured in docker/.env and Compose defaults.
