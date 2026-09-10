# Project-grid area-weighted kslast

**Status**: Implementation, restart and full integration complete; all validation gates passed; publication in progress (2026-09-09 UTC)
**Timezone**: UTC

## Purpose

Replace hillslope-centroid sampling of bedrock conductivity with an arithmetic area-weighted mean over an aligned project raster. Produce run-local `soils/kslast.tif`, a generic wepppyo3 aggregation kernel, and audited fallback coverage. Build/install the native extension in WEPPpy, restart local forest Compose, and validate actual WEPP execution on local seductive-sabra before committing and pushing both repositories.

## Authority and approved scope

The user approved the design and requested this scaffold on 2026-09-09. Execute against [the active ExecPlan](prompts/active/kslast_area_weighted_execplan.md). Durable policy: [kslast map contract](../../schemas/kslast-map-contract.md); decision provenance: [ADR](../../adrs/20260909_kslast_area_weighted.md).

Included: generic Rust mean and coverage statistics; explicit destination nodata in raster_stacker; project-grid kslast preparation shared by ordinary and MOFE paths; native build/release/import verification; local forest `wctl down` then `wctl up -d`; full RQ WEPP preparation, model execution, and post-processing on seductive-sabra; tests, documentation, reviews, scoped commits and pushes in WEPPpy and wepppyo3.

Excluded: wepp1/wepp2 deployment; new external dependencies; Peridot changes; fixing unrelated raster sampling callers or TOPAZ traversal nondeterminism; per-OFE spatial aggregation; changing source map classes, project defaults, simulation duration, or WEPP binary to shorten integration.

## Implementation fidelity and compatibility

Target: faithful implementation of the accepted area-weighted contract, not scaffold/surrogate discovery. This scaffold is non-closable until implemented AND wired behavior passes generated-output and full-run gates. No existing user-visible columns/keys are removed. Add `soils/kslast.tif` and `soils/kslast_summary.json`; preserve nodata in the raster and record coverage/default provenance in the summary. Current runtime is directory-only: archive-only roots fail; mixed roots use the existing directory and leave archives untouched. Resolved publication paths remain inside the run and use the active soils maintenance lock.

Compatibility plan: preserve raster_stacker callers that do not supply the new explicit destination nodata option. Keep the Rust API domain-neutral and existing wrapper imports stable. Preserve the no-map preparation path. Rebuild aligned map and summaries from current map/grid inputs before prep to avoid stale cache reuse. Validate every generated `wepp/runs/p*.sol` against the new result for its hillslope, including every MOFE OFE and existing developed-soil exemptions.

## Scientific behavior

Missing cells contribute configured `wepp.kslast` over their area. With any missing hillslope cells and no configured default, fail explicitly before launching soil workers. WEPPpy converts nonfinite/nonpositive kslast map values to nodata and reports them; Rust accepts generic finite negative/zero values. Mean is over the aligned projected raster, not fractional source-pixel intersections. No minimum coverage cutoff or arbitrary high-value threshold is introduced.

## Required acceptance

- [x] Authoritative contract and ADR checkpoint committed before production code.
- [x] Native function, wrappers, typing, and unit/integration tests implemented.
- [x] Stacker uncovered-area tests pass for sources with and without declared nodata.
- [x] Both soil preparation modes use the same area-weighted map results.
- [x] Rebuilt release artifact installed through the actual WEPPpy import path.
- [x] Local forest restarted with exactly `wctl down` and `wctl up -d`; fresh imports verified in web and worker containers.
- [x] Full local seductive-sabra RQ workflow completes with fresh WEPP outputs and verified kslast inputs.
- [x] Correctness/security reviews and required quality gates closed.
- [ ] Both existing branches committed and pushed; remote tips verified.

## Security impact and authorized operations

Impact: low; existing file-reading/native and run-artifact boundaries are touched, with no new route/auth/queue contract. Require a focused security artifact covering malformed rasters, bounded errors, publication atomicity, archive roots, and installed-library provenance, plus independent correctness review. This is not authorization to modify deployment wiring or security controls.

The requested restart is for host `forest` / local development Compose (`docker/docker-compose.dev.yml`), not `forest1` test production. Verify identity and preset before executing. The user has authorized the local restart and local run validation when this package is executed; do not request that permission again. Drain existing jobs rather than cancel unrelated work. Preserve an external backup of affected run artifacts before the real run.

## Evidence and precedent

Read-only scaffold preflight confirmed host forest and local container run `/wc1/runs/se/seductive-sabra`, MOFE enabled, default kslast 0.05, and readable configured `/geodata/extended_mods_data/wepppy-locations-portland/bedrock/combined_ksat_map.tif`. No build, restart, or model execution occurred while scaffolding.

Related historical package: [Peridot centroid correction](../20260909_peridot_centroid_projection/package.md). Reuse its exact output/reference comparisons and release hash recording; do not reopen it. The new algorithm intentionally stops consuming those centroids. Health signals: exact grid agreement, finite means, coverage totals, generated soil parity, fresh successful model outputs. Danger signals: unexplained default area, stale .so, centroid-dependent results, or silent uncovered zeros. Observe the required integration run and subsequent recurrence-triggered map rebuilds; no temporary fallback or time-based mitigation is added.

## Stakeholders and handoff

Decision owner: requesting user. Implementer: executing Codex session. Independent correctness reviewer and focused security reviewer must be identified in evidence before closeout. Keep tracker and ExecPlan current; archive the plan only after both remote pushes and all integration gates are verified.
