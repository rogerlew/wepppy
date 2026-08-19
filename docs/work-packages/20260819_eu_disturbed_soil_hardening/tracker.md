# Tracker – EU Disturbed Soil Building Data-Quality Hardening

> Living document tracking evidence, decisions, risks, and validation for the
> EU ESDAC disturbed-soil hardening package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-19 19:37 UTC
**Current phase**: Random invalid-soil search design
**Last updated**: 2026-08-19 19:37 UTC
**Next milestone**: Run a 1,000-sample pilot against the ESDAC raster footprint
and inspect the anomaly rate
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Locate the matching ESDAC, STU, and SoilHydroGrids raster installation.
- [ ] Generate a deterministic 1,000-sample pilot manifest from the actual
  ESDAC footprint.
- [ ] Run the pilot source screen and full-build flagged samples.
- [ ] Scale to the 50,000-sample campaign after pilot performance review.
- [ ] Add Marta's cases later if coordinates or run artifacts become
  available.
- [ ] Add deterministic replay fixture and no-geodata test harness.
- [ ] Define quality taxonomy and valid/degraded/rejected contract.
- [ ] Implement the approved validation boundary and diagnostics.
- [ ] Validate disturbed downstream generated artifacts.
- [ ] Complete correctness, QA, docs, and observation gates.

### In Progress

- [ ] Phase 0 random search: generate and screen a seeded coordinate/pixel
  sample for invalid soils.

### Blocked

- [ ] Search execution is blocked by missing EU raster assets in the current
  workspace; the campaign must run where the matching geodata is installed.

### Done

- [x] Reviewed the ESDAC builder, SoilHydroGrids adapter, shared horizon
  calculations, and current EU integration test (2026-08-19 19:37 UTC).
- [x] Identified initial hypotheses: non-finite acceptance, zero-derived
  erodibility, missing depth ordering, and silent Ksat degradation
  (2026-08-19 19:37 UTC).
- [x] Authored package scaffold, tracker, and active ExecPlan
  (2026-08-19 19:37 UTC).
- [x] Reframed Phase 0 as a deterministic random invalid-soil search with a
  1,000-sample pilot and 50,000-sample target (2026-08-19 19:45 UTC).
- [x] Added the deterministic raster-cell manifest generator and unit tests;
  live execution remains blocked by missing EU geodata (2026-08-19 19:47 UTC).

## Phase Gates

- **Phase 0**: the pilot and full campaign record seed, raster/data versions,
  unique samples, source anomalies, full-build failures, invalid profiles, and
  valid controls.
- **Phase 1**: deterministic fixture reproduces confirmed cases and includes a
  valid control without `/geodata`.
- **Phase 2**: every invariant is evidence-backed and valid zero values are
  distinguished from invalid source values.
- **Phase 3**: proposed result contract preserves valid states and exposes
  invalid-state diagnostics.
- **Phase 4**: generated `.sol` output is finite, ordered, and contract-valid;
  invalid profiles do not silently write.
- **Phase 5**: disturbed downstream artifacts remain valid and reproducible.
- **Phase 6**: review, observation, and documentation gates are complete.

## Timeline

- **2026-08-19 19:37 UTC** – Package opened from EU soil-builder review.
- **2026-08-19 19:45 UTC** – Phase 0 expanded to random invalid-soil search;
  Marta's cases are optional supplemental evidence.
- **Pending** – 1,000-sample pilot run against matching EU geodata.
- **Pending** – 50,000-sample campaign and deterministic fixture accepted.
- **Pending** – Quality contract approved.
- **Pending** – Production hardening implemented and validated.
- **Pending** – Observation window and closeout completed.

## Decisions Log

### 2026-08-19 19:37 UTC: Fixture before behavior change

**Context**: The current builder accepts source values and writes output with
limited quality checks, but the reported zero values and invalid horizons have
not yet been tied to exact source samples in this workspace.

**Options considered**:

1. Add broad defaults immediately — fast, but risks masking valid data and
   changing scientific behavior without evidence.
2. Add a captured source fixture first — slower initially, but produces a
   reproducible failure contract and separates source defects from builder
   defects.
3. Require all EU raster assets in every unit test — realistic, but brittle,
   heavy, and unavailable in the current workspace.

**Decision**: Option 2, with an optional live raster check as a separate
integration layer.

**Impact**: Phase 1 can run deterministically without `/geodata`; production
fallback and rejection choices remain open until Phase 2.

### 2026-08-19 19:45 UTC: Search before known-case reproduction

**Context**: Marta's coordinates are unavailable, but the objective is to find
invalid EU soils rather than wait for a known example.

**Options considered**:

1. Wait for a known coordinate — high fidelity but blocks discovery.
2. Uniform random points over a Europe bounding box — simple but wastes points
   over ocean and outside the source footprint.
3. Seeded, stratified samples from the actual ESDAC raster footprint — broad
   coverage, reproducible, and able to target source anomalies.

**Decision**: Option 3, with a 1,000-sample pilot followed by a 50,000-sample
campaign. Run source screening before full builds and retain raw payloads.

**Impact**: Phase 0 can discover failure cases independently of Marta, while
the pilot provides a performance and anomaly-rate checkpoint before scaling.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Coordinates or matching raster versions are unavailable | High | Medium | Request run IDs and preserve source/output artifacts; mark provenance gaps explicitly | Open |
| A zero value is scientifically valid for a particular property | High | Medium | Include valid-zero controls and classify each field by domain rule | Open |
| Validation rejects valid EU profiles | High | Medium | Valid-state matrix and downstream generated-output tests | Open |
| Invalid source is silently replaced by a generic soil | High | Medium | Explicit result contract and diagnostic reason codes | Open |
| Captured source fixture drifts from live rasters | Medium | Medium | Record dataset/version metadata and keep optional live verification | Open |
| Worker error loses location context | Medium | Low | Include TopoAZ/coordinate context in structured result and logs | Open |

## Hardening Signal Log

- **Baseline health signals**: not yet quantified; current evidence is code
  review plus the report of zero parameters and invalid horizons.
- **Post-change health signals**: pending fixture and implementation.
- **Danger signals observed**: quality checks currently emphasize file
  creation; invalid-source outcomes are not structured; broad random samples
  may be too expensive if full builds precede screening.
- **Temporary callus register**: none.
- **Softening experiments**: not applicable during evidence freeze.

## Verification Checklist

### Code Quality

- [ ] Targeted EU soil tests pass.
- [ ] Full `wctl run-pytest tests --maxfail=1` passes before closeout, or the
  blocker is documented.
- [ ] Changed-file broad-exception check passes.
- [ ] `git diff --check` passes.

### Documentation

- [ ] ESDAC module documentation describes quality outcomes and diagnostics.
- [ ] User/operator documentation describes invalid-source behavior.
- [ ] Package and changed docs pass `wctl doc-lint`.
- [ ] Parameterization ADR is added if defaults, thresholds, formulas, units,
  or fallback heuristics change.

### Testing

- [ ] Captured fixture includes valid, zero, missing/nodata, non-finite,
  malformed-texture, depth-order, and Ksat cases as supported by evidence.
- [ ] Replay tests run without EU raster installation.
- [ ] Optional live raster capture/verification is recorded separately.
- [ ] Generated `.sol` parser and downstream disturbed tests pass.
- [ ] Absent, empty, populated, and supported-legacy states are covered where
  applicable.

### Reviews and Observation

- [ ] Correctness review artifact completed with no unresolved medium/high
  findings.
- [ ] QA review artifact completed with no unresolved medium/high findings.
- [ ] Health/danger signals and observation window recorded.
- [ ] Temporary calluses have owner and sunset criteria, or none are retained.

## Progress Notes

### 2026-08-19 19:37 UTC: Package scaffold and initial source review

**Agent/Contributor**: Codex

**Work completed**:

- Reviewed `wepppy/eu/soils/esdac/esdac.py` and its direct dependencies.
- Confirmed the existing EU test is optional and only checks file creation.
- Recorded initial failure hypotheses and the evidence-first phase plan.
- Added `package.md`, `tracker.md`, and the active ExecPlan.
- Added `tools/eu_invalid_soil_search.py` and pure sampling tests that do not
  require the EU raster installation.

**Blockers encountered**:

- `/geodata/eu/ESDAC_ESDB_rasters`, `/geodata/eu/ESDAC_STU_EU_Layers`, and
  EU SoilHydroGrids assets are not present in the current workspace, so live
  reproduction must wait for an external run or fixture payload.

**Next steps**:

- Locate matching EU geodata on a host where the campaign can run.
- Begin Phase 0 with the 1,000-sample pilot.

**Test results**: `wctl run-pytest tests/eu/soils/test_invalid_soil_search.py`
passed (`4 passed`); package and `PROJECT_TRACKER.md` documentation lint passed.

## Watch List

- **Source-version drift**: ESDAC and SoilHydroGrids values must be captured
  with enough provenance to distinguish code changes from dataset changes.
- **Zero-value semantics**: do not impose blanket `> 0` rules until each field
  has a domain decision and a valid-zero control.
- **Silent Ksat degradation**: the current `0.001` all-missing behavior needs
  an explicit policy before implementation.
- **Dead second-horizon guard**: mapped depth defaults are positive, so the
  current `h1.depth <= 0` check may not protect any real case.
- **Search cost**: full builds for every random coordinate may be too slow;
  benchmark the pilot and keep source screening separate.

## Communication Log

### 2026-08-19 19:37 UTC: Initial hardening request

**Participants**: User, Marta (reported cases), Codex
**Question/Topic**: How should EU disturbed-soil zero values and invalid
horizons be made reproducible and hardened?
**Outcome**: Search a large seeded coordinate set for invalid soils, then use
the captured cases to drive evidence-backed hardening.

## Handoff Summary

**From**: Codex
**To**: User / next session
**Date**: 2026-08-19 19:37 UTC

**What's complete**:

- Work-package scaffold and active ExecPlan are present.
- Initial source-review hypotheses and phase gates are recorded.

**What's next**:

1. Locate matching EU geodata on a host where the campaign can run.
2. Generate and run the 1,000-sample pilot.
3. Scale to 50,000 samples, then add the deterministic fixture and replay test.

**Context needed**:

- The EU test currently depends on `/geodata` and is skipped when those assets
  are absent.
- The wrapper delegates quality behavior to `ESDAC.build_wepp_soil`.
- The campaign should sample raster cells from the actual source footprint,
  not a naive geographic bounding box.

**Open questions**:

- Which run IDs/coordinates reproduce Marta's report?
- Which exact zero-valued fields are unacceptable versus scientifically valid?
- Should invalid locations reject the full build, be omitted with a surfaced
  report, or use a documented fallback?
