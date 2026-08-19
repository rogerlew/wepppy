# Tracker – EU Disturbed Soil Building Data-Quality Hardening

> Living document tracking evidence, decisions, risks, and validation for the
> EU ESDAC disturbed-soil hardening package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-19 19:37 UTC
**Current phase**: Phase 0 evidence freeze
**Last updated**: 2026-08-19 20:46 UTC
**Next milestone**: Select minimized pilot cases and create the Phase 1
source-payload replay fixture
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Scale to the 50,000-sample campaign after pilot performance review.
- [ ] Select and minimize pilot cases for the Phase 1 fixture.
- [ ] Add Marta's cases later if coordinates or run artifacts become
  available.
- [ ] Add deterministic replay fixture and no-geodata test harness.
- [ ] Define quality taxonomy and valid/degraded/rejected contract.
- [ ] Implement the approved validation boundary and diagnostics.
- [ ] Validate disturbed downstream generated artifacts.
- [ ] Complete correctness, QA, docs, and observation gates.

### In Progress

- [ ] Phase 0 random search: review pilot cases and approve the 50,000-sample
  campaign scale-up.

### Blocked

None.

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
  valid-cell-only sampling was corrected after the first nodata-frame pilot
  (2026-08-19 20:05 UTC).
- [x] Ran the 1,000-sample pilot in the dev container using the installed
  ESDAC/STU/SoilHydroGrids assets (2026-08-19 20:46 UTC).
- [x] Captured source payloads and targeted builder outputs: 641 suspicious
  source records, 596 completed builds, 35 builder exceptions, 59 horizon
  depth-order findings, and 10 valid controls (2026-08-19 20:46 UTC).

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
- **2026-08-19 20:46 UTC** – 1,000-sample pilot and targeted builds completed;
  Phase 0 evidence review is pending.
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

- **Baseline health signals**: pilot source screen found 641 suspicious of
  1,000 samples; targeted builds produced 35 exceptions and 59 generated
  files with non-increasing horizon depths. Ten screened controls built with
  no output-order issue.
- **Post-change health signals**: pending fixture and implementation.
- **Danger signals observed**: quality checks currently emphasize file
  creation; invalid-source outcomes are not structured; source screening
  found STU zeros/missing values and missing depth classes; full builds are
  materially slower than raster-cell screening.
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

### 2026-08-19 20:46 UTC: Phase 0 pilot evidence

**Agent/Contributor**: Codex

**Work completed**:

- Used the dev container's matching assets: 148 ESDB rasters, 85 STU layers,
  and 56 SoilHydroGrids files.
- Generated 1,000 unique, deterministic, valid-anchor-cell samples with seed
  `20260819`.
- Screened raw categorical, continuous, and Ksat source values, retaining
  sample pixel provenance and coordinates.
- Built all 641 source-suspicious samples plus 10 controls in isolated worker
  processes and retained generated `.sol` files under the campaign output.
- Found 59 built profiles with non-increasing cumulative horizon depths and
  35 source/build failures (`TypeError`, `RDIOutOfBoundsException`, and
  `KeyError`).

**Blockers encountered**:

- The first sampler included nodata cells because the anchor raster frame is
  larger than its valid land footprint; this was corrected before the final
  pilot. A second diagnostic bug swapped row/column order for grids with
  different geometry; direct-vs-builder checks caught and corrected it.
- The first evidence collector called the broken `Horizon.as_dict()` and
  misclassified successful builds; the collector now records stable raw
  horizon fields and generated-output checks.

**Next steps**:

- Review the 35 exceptions and 59 depth-order cases, then minimize the
  strongest examples into the no-geodata Phase 1 fixture.
- Decide whether the 50,000-sample campaign is warranted after reviewing the
  pilot's issue prevalence and runtime.

**Test results**: `wctl run-pytest tests/eu/soils/test_invalid_soil_search.py`
passed (`6 passed`, 2 deprecation warnings).

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
**Date**: 2026-08-19 20:46 UTC

**What's complete**:

- Work-package scaffold and active ExecPlan are present.
- Initial source-review hypotheses and phase gates are recorded.

**What's next**:

1. Review and minimize the pilot cases into a deterministic fixture.
2. Add the no-geodata replay harness and quality taxonomy.
3. Decide and execute the 50,000-sample campaign if the evidence review
   requires broader prevalence estimates.

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
