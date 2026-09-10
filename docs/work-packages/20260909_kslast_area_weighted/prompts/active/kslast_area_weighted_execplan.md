# Implement and validate project-grid area-weighted kslast

## Purpose / Big Picture


Replace single-centroid bedrock-map sampling with a reproducible mean over each hillslope's project raster cells. The deliverable includes a generic Rust kernel, an inspectable `soils/kslast.tif`, correct treatment of uncovered area, installed native code, and a completed real WEPP run after restarting local forest Compose. This is a living ExecPlan governed by `docs/prompt_templates/codex_exec_plans.md`. Scaffolding is not implementation completion.

## Progress


- [x] (2026-09-09 UTC) User approved area/default policy and requested scaffolding, native installation, local restart, actual model validation, and both repository pushes.
- [x] (2026-09-09 UTC) Read-only preflight confirmed host forest, local seductive-sabra and configured kslast raster readable inside WEPPcloud; scalar 0.05 and MOFE enabled.
- [x] (2026-09-09 UTC) Package, tracker, durable contract, ADR and evidence checklist scaffolded.
- [x] M1: commit contract checkpoint and capture external rollback baseline.
- [x] M2: implement/test generic native kernel and explicit destination nodata support.
- [x] M3: wire shared WEPPpy preparation and additive diagnostics.
- [x] M4: build/install native release and verify actual runtime import provenance.
- [x] M5: restart local forest Compose and verify fresh processes and imports.
- [x] M6: complete full local seductive-sabra RQ/WEPP execution with input/output parity evidence.
- [ ] M7: close independent reviews and quality gates, commit/push both repositories, archive plan.

## Surprises & Discoveries


The current `raster_stacker` already matches the reference grid and supports nearest/average resampling, but inherits source nodata and does not expose explicit destination nodata. Existing median code is not a safe template for this kernel: it zips arrays without full grid checks and compares nodata numerically without complete nonfinite handling. Use explicit validation rather than copying those weaknesses.

The development Dockerfile installs a `.pth` path to `/workdir/wepppyo3/release/linux/py312`, with an image-vendored fallback. Compose bind-mounts the sibling wepppyo3 repository. Merely rebuilding a `.so` or importing it in a host Python shell does not prove that restarted workers use it. Existing native preflight pins wepp_interchange, not this raster module; preserve that unrelated pin.

The previous Peridot package corrected centroid coordinates and documented TOPAZ geometry nondeterminism. This package does not require re-abstraction: reuse existing delineation, pixel-key grid, climate, soils and management. Do not conflate a new area mean with the previous point-sample values.

## Decision Log


2026-09-09 UTC, user/Codex: apply a generic finite `default_value` only to missing parameter area. Rust accepts finite negative/zero values; WEPPpy alone rejects nonpositive conductivity. Keep nodata visible in the aligned map and audit coverage. Missing area without a default is an explicit error. Both preparation modes must share results; MOFE remains one value per hillslope, not per OFE.

2026-09-09 UTC, user: package execution must build/install wepppyo3 in WEPPpy, perform local `wctl down` and `wctl up -d`, run WEPP end-to-end on local seductive-sabra, then commit/push both repositories. Authorization persists when executing this plan. Do not replace this gate with isolated worker calls, an import test, or a no-prep WEPP run.

## Context and Orientation


WEPPpy checkout: `/home/workdir/wepppy`, branch master. wepppyo3 checkout: `/home/workdir/wepppyo3`, branch main (observed 2c31f6c). Host is forest, development Compose is `docker/docker-compose.dev.yml`. This is not forest1 test production or wepp1/wepp2. Recheck current instructions, branch tips and unrelated dirty changes before editing; do not switch branches.

WEPPpy source paths: `wepppy/all_your_base/geo/geo.py::raster_stacker` and its `geo.pyi` stub; `wepppy/nodb/core/wepp.py::_prep_multi_ofe` and `prep_multi_ofe_hillslope`; `wepppy/nodb/core/wepp_prep_service.py::prep_soils`. `wepppy/nodb/core/soils.py` demonstrates stacking and native key-raster aggregation. Native code is `raster_characteristics/src/lib.rs`, crate `raster_characteristics_rust`; wrappers live under `release/linux/py312/wepppyo3/raster_characteristics/`. Shared raster metadata support is in `raster/`.

Local target is `/wc1/runs/se/seductive-sabra` inside the container, with config `portland-10-mofe`. Source map is `/geodata/extended_mods_data/wepppy-locations-portland/bedrock/combined_ksat_map.tif`, readable at scaffold preflight. Derive the host run/map mounts from the installed local Compose configuration; do not assume the production `/geodata/wc1` host mapping. The route's config suffix is not part of the filesystem run path.

Durable authority: `docs/schemas/kslast-map-contract.md` and `docs/adrs/20260909_kslast_area_weighted.md`. Read NoDb/NoDir contracts and nearest AGENTS before implementation. This is an additive data/artifact change; package.md contains the compatibility/regression plan.

## M1: authority checkpoint and rollback baseline


Before code, review and commit the scaffold contract/ADR in WEPPpy. In wepppyo3 add a maintained generic function specification under `docs/`, linked from the module registry, and commit that contract checkpoint before implementation. Include accepted argument/result/error semantics and all-pixels-missing behavior. Do not put durable policy only in this package or amend the closed Peridot package.

Capture current source commits, branches, dirty status, run settings, expected hillslope/OFE counts, model version, output timestamps and hashes, source-map/grid hashes, package paths and native artifact hashes. Store large rollback data outside the run and outside Git. Back up affected controller state, soils/archive state, WEPP inputs/outputs/reports and orchestration status necessary for recovery. Save the actual old release `.so` and wrapper together. Record the backup inventory and restore procedure in artifacts/baseline.md. Never flatten or discard archived soils merely to simplify testing.

## M2: generic kernel and stacker


Add `identify_area_weighted_mean_single_raster_key(key_fn, parameter_fn, ignore_channels=True, ignore_keys=None, band_indx=1, default_value=None)` to the native module and canonical py312 Python wrapper/types. Return a deterministic string-keyed mapping of records: `mean`, `valid_cell_count`, `missing_cell_count`, `total_cell_count`. Use one native scan and stable float64 accumulation; no Python per-cell aggregation or new dependency. Exclusions follow existing key/channel conventions. On an aligned projected affine grid, equal cell areas cancel in the mean; validate a finite nonsingular affine and reject geographic grids instead of claiming geodesic weighting.

Validate readable rasters, band, equal dimensions/data lengths, equivalent CRS, and matching full affine transforms before scanning. Honor parameter masks and nodata; nonfinite data are missing. Generic finite zero/negative values and defaults remain valid. Any missing cells without a default produce a bounded descriptive error with affected keys/coverage; all missing with a supplied finite default produces the default. An empty eligible key set returns an empty mapping. I/O errors become explicit Python errors, not panics or truncated zip results. Do not omit all-missing keys silently.

Patch raster_stacker with backward-compatible keyword options `dst_nodata=None` and `dst_dtype=None`: omitted values preserve existing source-derived choices. Explicit values update destination metadata and are passed consistently to reproject, with destination initialized to nodata. Reject unrepresentable nodata/dtype combinations before publication. The kslast caller must request Float64 and an explicit negative nodata sentinel such as -9999, even if source nodata is absent. Preserve source masks and source nodata; never relabel a valid source value as missing merely because of the chosen destination sentinel. Existing callsites retain their behavior unless they opt in.

Add Rust and exported-Python tests for exact means, unequal class counts, partial/all/no missing data, defaults, generic zero/negative inputs, nodata NaN and finite sentinels, infinities, masks, empty/excluded/channel keys, deterministic ordering, invalid bands/CRS/alignment, and singular transforms. Stacker tests must include uncovered target regions with source nodata absent and present, valid zeros in a generic raster, explicit dtype/nodata, and existing no-override callers. Use real tiny rasters and direct export calls, not mocks of the changed boundary. Record a representative native scan timing and peak memory; make no unmeasured speed claim.

## M3: shared WEPPpy map preparation


Implement one shared map-preparation collaborator for ordinary and MOFE paths, scoped to existing prep orchestration. Stack the configured source against `watershed.subwta` into a staged Float64 GeoTIFF; normalize nonpositive/nonfinite conductivity to nodata while retaining source mask/nodata and explicit uncovered cells. Avoid Python per-cell loops. Publish `soils/kslast.tif` atomically only after validation. The run-local map remains nodata in missing areas; pass configured `wepp.kslast` to the generic kernel rather than filling the file.

Produce atomic `soils/kslast_summary.json` with source/grid hashes or equivalent content identity, resampling/aggregation policy, default, normalization counts and per-key coverage/results. Rebuild from current inputs at prep; do not trust a stale file just because it exists. Follow existing NoDir materialization/mutation and NoDb locking/cache rules when soils are archived or mixed. Complete results and policy validation before scheduling soil workers, and use one owner for shared artifact publication.

Replace both centroid loops with the same key-indexed results. WEPPpy supplies explicit background/non-hillslope key exclusions, including zero; verify the result key set equals the hillslopes being prepared. Do not alter the existing no-map scalar/no-override path, initial saturation, clipping, or developed-soil exemption. Apply each hillslope mean to all its MOFE OFEs. Preserve useful source/default/coverage provenance in soil modification comments; no stale centroid coordinates in those comments. Missing coverage with no default must fail explicitly before workers write new soil inputs. If map configured but unreadable/invalid, fail rather than silently default.

Test both modes, partial/no coverage and invalid values, changed source/grid/default between preparations, ordinary/no-map behavior, existing developed exemptions, archive/mixed roots, and every downstream OFE value. Update user/operator/developer documentation and touched typing/stubs. Avoid queue wiring changes; if one proves necessary, update the RQ dependency catalog and run its graph/live-tree gates.

## M4: build and install the actual release


Read wepppyo3 README and docs/release-provenance.md at execution time. Use the py312 interpreter matching the runtime ABI and build only the affected crate, for example from the wepppyo3 root:

    PYO3_PYTHON=/usr/bin/python3.12 PYTHON_SYS_EXECUTABLE=/usr/bin/python3.12 cargo build --release -p raster_characteristics_rust

Verify that interpreter exists and matches the container ABI first. Refresh `target/release/libraster_characteristics_rust.so` into `release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so` through a same-directory temporary file, chmod 0755, and atomic rename. Never truncate a library that workers may have mapped. Refresh the matching wrapper/export and applicable package version/provenance metadata. Do not copy unrelated shared objects or bypass the existing interchange hash pin.

The development install path is the mounted release tree selected by `/opt/venv`'s `.pth` file. Inspect actual `module.__file__` and native extension `__file__` rather than assume pip/site-packages location. If the local import wiring differs, repair through the canonical install mechanism and document it; do not count temporary PYTHONPATH overrides as installation. Record source SHA, ABI, build command, runtime path, .so hash and import callable in artifacts/release_manifest.json. Update wepppyo3 module registry and release provenance.

## M5: required local forest restart


Verify host identity, working directory, installed wctl development preset and Compose service mapping. Read the canonical deployment entrypoint/docs before any proposed deployment mechanics; this package uses the user's explicit bounded local restart, not a production deployment. Record queue state and wait for active local jobs to drain; do not cancel unrelated work. Require seductive-sabra to be quiescent and the baseline backup complete.

From `/home/workdir/wepppy`, execute the authorized commands, without volume deletion or an alternate stack:

    wctl down
    wctl up -d
    wctl docker compose ps

Wait for expected services to be healthy/ready. Record old/new container IDs/start times and import/hash checks in weppcloud, rq-engine, rq-worker and rq-worker-batch. Existing worker startup inherits the .pth configuration; verify the native path/hash in fresh processes with the actual worker environment and user, not only a host Python shell. Run a tiny real-raster call through the new function after restart. If readiness/import fails, collect logs, repair the cause and repeat this gate; do not proceed to model submission with stale or mismatched native code.

## M6: real local WEPP run and end-to-end assertions


Create `artifacts/run_seductive_sabra_integration.py` during implementation. It must run in the local runtime, have explicit baseline/submit/poll/verify phases, preserve artifacts for failure diagnosis, and return nonzero for unmet gates. Submit the full existing RQ WEPP workflow for run seductive-sabra with configuration portland-10-mofe. Use the current authenticated rq-engine `/runs/{runid}/{config}/run-wepp` contract or its supported operator enqueue path, discovered from `wepppy/microservices/rq_engine/wepp_routes.py` and `wepppy/rq/wepp_rq.py::run_wepp_rq`. Use the rq-agent-operator skill if operating through the HTTP API. Never log credentials. Do not call an internal worker directly as the end-to-end substitute, use a no-prep endpoint, shorten the simulation, or change the model binary.

Record parent and descendant job IDs; poll all required leaves and the final completion job. Parent enqueue success or completed preparation is insufficient. Require hillslope and configured watershed WEPP stages plus expected post-processing/interchange to complete. Verify new job timestamps and model outputs against the preserved baseline to exclude stale successes. Capture any numerical/model failure and keep this milestone open until resolved within scope or explicitly blocked.

Independently validate `soils/kslast.tif` grid/CRS/nodata and calculate reference per-hillslope means and coverage from all included subwta cells using a separate test oracle. The oracle must not call the new native aggregation or reuse its result as expected data. Compare all native means and summary counts with a documented float64 tolerance (rtol 1e-12, atol 1e-12 for aggregation; account for existing soil text precision separately). Compare every generated hillslope `p*.sol`, identified through the actual translator, and every OFE restrictive-layer conductivity against its assigned mean; explicitly enumerate developed-soil exemptions.

Verify fresh WEPP outputs and downstream tables/reports exist and parse, have finite expected numeric fields, and are associated with this run's new successful job tree. Record model executable identity and unchanged configured simulation period. Do not demand equality of hydrology with old centroid results: the mean intentionally changes parameterization. Synthetic partial/all-missing fixtures must still cover policy cases even if this project's source map has full coverage. Runtime soil prep and actual model execution, not mocked/isolated prep alone, are required acceptance evidence.

## M7: reviews, quality gates and publication


Run crate formatting/check/tests and release-tree Python tests. In wepppyo3:

    cargo fmt -p raster_characteristics_rust -- --check
    cargo check -p raster_characteristics_rust
    RUSTFLAGS='-C link-arg=-lpython3.12' cargo test -p raster_characteristics_rust --lib
    PYTHONPATH=release/linux/py312 python3.12 -m pytest tests/raster_characteristics

Use actual available ABI/link flags from the canonical release runbook; record deviations. In WEPPpy run targeted real-raster/prep tests via wctl, relevant stub tests and check-test-stubs for changed public interfaces, then:

    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260909_kslast_area_weighted

Also lint changed canonical docs, run changed broad-exception enforcement and code-quality observability, and complete independent correctness plus focused security artifacts. Test invalid states separately from input flag combinations. Close introduced medium/high findings; record preexisting unrelated failures separately without masking them. Do not mark the package complete if the restart/full-model gate is unrun or failed.

Commit only package-owned files/hunks in both repositories, including native release wrapper/.so and provenance in wepppyo3. Preserve unrelated dirty files and do not create branches. Push existing wepppyo3 main and WEPPpy master without force after fetching/checking divergence. Verify remote branch tips match the published local commits. Record both SHA values and push evidence in tracker/validation artifacts. Update package, tracker, PROJECT_TRACKER and this plan, then move this plan to prompts/completed using wctl doc-mv. Keep durable policy in the canonical contract/ADR, not only the closed package.

## Idempotence and Recovery


Staging/atomic publication and explicit current-input validation make map preparation repeatable. Repeated model submissions still overwrite run artifacts, so verify quiescence and keep the external baseline. Preserve failed output for diagnosis before a rerun. Do not clear Redis globally, delete Docker volumes, edit production runs, or force-push. A rollback must restore a compatible Python/native pair and restart affected local processes before any retry. Run restoration must use saved artifacts and canonical NoDb cache invalidation rather than blind serialized-object edits.

## Outcomes & Retrospective


Implemented and installed the generic area mean and shared project-grid prep.
All 15 RQ jobs completed the unchanged 46-year local run; independent checks
matched 505 means, 1259 OFEs and 25 fresh output tables. Rust tests: 8 passed;
release Python: 43 passed; new WEPPpy tests: 28 passed; broad suite: 8174 passed,
72 skipped. Independent correctness/security findings were corrected and closed.
Publication/archival is the only remaining step.

Discoveries: NoDir runtime was already directory-only, so the contract was
corrected before implementation. Generic nodata needs validation after GDAL
resampling and conversion, not merely against source values. Signed cancellation
requires scaled Neumaier accumulation. Resolved soil publication paths must
remain inside the run. The final restart followed the reviewed native rebuild.
All changes use existing owned components; no dependency or queue wiring changed.

Revision: 2026-09-09 UTC, initial scaffold from the accepted user requirements and read-only source/runtime inspection.

2026-09-09 UTC execution update: contract checkpoints and external backup complete. Native kernel builds; 8 Rust tests and 42 real-raster release tests pass. Shared prep/stacker targeted suite: 21 pass. M2/M3 implemented with further integration tests pending. Directory-only correction and staging rationale are in the canonical contract.

2026-09-09 UTC: M2–M5 complete. 43 native release tests and 28 project-grid/prep tests pass; both real soil workers verified for two OFEs and developed exemptions. Independent numerical, nodata conversion and path-containment findings were fixed and retested. Two authorized local restarts completed; final fresh service hashes match release_manifest.json. Full RQ job 90431b48-4138-4f28-89f6-90a5b3806f7e has completed prep and is executing hillslopes. Broad suite running; M6/M7 remain open.

2026-09-09 23:57 UTC: M6 passed. All 15 RQ jobs finished; unchanged 46-year model completed. Final oracle validates 505 hillslopes / 1259 OFEs and 25 fresh finite output tables (70,151,967 rows), zero defaulted hillslopes. Full-suite and publication gate remain open.
