# Tracker - SSURGO Intelligent Fallback Empirical Study

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-21 18:00 UTC
**Current phase**: M4 evidence hold
**Last updated**: 2026-07-25
**Next milestone**: Compare broader local rings for local-oracle misses and complete an observed-invalid provenance review before defining an ADR-ready practical-effect criterion.
**Security impact**: none
**Dedicated security review**: no
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Expand the geographically separated masked-valid cohort beyond the
  current 29-case held-out check.
- [ ] Conduct a stratified observed-invalid review with source-field
  provenance, candidate evidence, and explicit fallback disposition.

### In Progress

- [x] Milestone 1: candidate pixel support and synthetic raster fixtures
  complete; native crate tests: 5 passed (2026-07-22 03:28 UTC).
- [x] Added Git-LFS-backed deterministic masked-valid raster corpus: direct
  local candidate, expansion, numeric tie, no candidate, and separated
  clusters; public-binding test passes (2026-07-22).

### Blocked

- None. The public NRCS endpoint is an external availability risk, not a
  current blocker.

### Done

- [x] Authored the fallback strategy and research-only CLI scaffold
  (2026-07-21 18:00 UTC).
- [x] Inventoryed the 2025 gNATSGO VAT: 320,669 MUKEYs and 8,745,483,151 mapped
  pixels (2026-07-21 18:07 UTC).
- [x] Completed a 2,048-draw area-weighted pilot: 40 unbuildable draws (1.95%;
  95% Wilson interval 1.44%-2.65%) (2026-07-21 18:15 UTC).
- [x] Classified five converter-worker failures as nonphysical texture-balance
  errors, not NRCS data-access failures (2026-07-21 18:18 UTC).
- [x] Ran canonical study-tool tests: 3 passed (2026-07-22 01:59 UTC).
- [x] Added and tested a resumable study cohort runner: 4 targeted tests passed
  (2026-07-22 02:10 UTC).
- [x] Completed the 12,288-draw mapped-area cohort: 244 unbuildable draws
  (1.99%; Wilson 95% 1.75%–2.25%; zero data-access failures) (2026-07-22
  02:35 UTC).
- [x] Completed the 2,048-draw uniform-MUKEY cohort: 49 unbuildable MUKEYs
  (2.39%; Wilson 95% 1.81%–3.15%; zero data-access failures) (2026-07-22
  02:39 UTC).
- [x] Scaffolded the concurrent clustered-bounds native candidate kernel in
  WEPPpyo3; crate tests passed (2026-07-22 03:10 UTC).
- [x] Benchmarked 16 adjacent synthetic clusters through a freshly built
  extension: 174 ms / 86 ms / 47 ms at one / two / four workers (2026-07-22
  03:14 UTC).
- [x] Corrected native `exhausted` evidence so a successful maximum-radius
  search is not reported as unresolved; crate tests remain 5 passed
  (2026-07-22).
- [x] Completed Milestone 2 shadow collection with additive NoDb/Parquet
  evidence, legacy hydration coverage, and a read-only local-run proof with
  six invalid hillslopes in one cluster (2026-07-22).
- [x] Completed Milestone 3 read-only masked-valid cohort: 298 hillslopes in
  two local runs, local feature distance better in 108 versus 71 global wins
  (119 ties), and local elevation difference better in 235 versus 62 global
  wins (2026-07-22).
- [x] Completed M3.5 geometry/terrain scoring slice with NED1: geometry-only
  131 local versus 58 global feature-distance wins; 30% terrain 140 versus 62
  (2026-07-22). Profile/failure-class score families remain.
- [x] Completed M3.5 deterministic failure-class gate corpus: profile-free
  dominant classes, partial-profile evidence, nonphysical exclusion, missing
  DEM, stable tie, and explicit global-fallback controls (2026-07-23).
- [x] Completed four-run held-out scoring check (29 cases): geometry-only 2
  local, 3 global, 24 tied; M4 remains HOLD (2026-07-23).
- [x] Completed ranked candidate-set study: 298-case oracle 183 versus 131
  top-one local wins; 29-case held-out oracle 6 versus 2 top-one wins
  (2026-07-24).
- [x] Completed larger ranked-candidate cohort: 18 run manifests, 322 cases,
  275 local-oracle versus 165 top-one local wins, and exact one/four-worker
  parity (2026-07-25).

## Timeline

- **2026-07-21 18:00 UTC** - Strategy and research scaffold created.
- **2026-07-21 18:07 UTC** - VAT inventory completed.
- **2026-07-21 18:15 UTC** - Initial 2,048-draw cohort completed.
- **2026-07-22 02:00 UTC** - User approved expanded area-weighted and
  unweighted-MUKEY cohorts; work package created and amended scope recorded.

## Decisions Log

### 2026-07-21 18:07 UTC: Use the gNATSGO raster attribute table for coverage

**Context**: A full block scan of the 2.7 GB GeoTIFF used unnecessary memory,
while the companion VAT supplies `mukey` and mapped-pixel `Count` values.

**Options considered**:

1. Stream every raster block for national frequency.
2. Use the companion VAT for national frequency and retain block streaming for
   rasters without a VAT or for smoke tests.

**Decision**: Use the VAT when available.

**Impact**: The complete inventory is fast, reproducible, and does not confuse
edge NoData blocks with national coverage.

### 2026-07-22 02:00 UTC: Expand with complementary sampling frames

**Context**: The 2,048-draw area-weighted pilot observed 40 unbuildable draws.
It estimates mapped-area impact but underrepresents rare MUKEYs.

**Options considered**:

1. Stop at the pilot.
2. Scan all 320,669 MUKEYs immediately.
3. Expand the area-weighted cohort and add an unweighted-MUKEY cohort.

**Decision**: Run 12,288 area-weighted draws and 2,048 unweighted-MUKEY draws.

**Impact**: The first cohort targets approximately 240 unbuildable draws and a
roughly ±0.25 percentage-point 95% precision for the mapped-area rate; the
second exposes rare-MUKEY failure prevalence. This is still research, not a
production policy decision.

### 2026-07-22 02:40 UTC: Preserve separate sampling-frame estimates

**Context**: The expanded mapped-area cohort observed 244 unbuildable draws
of 12,288, while the uniform-MUKEY cohort observed 49 of 2,048.

**Decision**: Report the results separately and use the mapped-area result for
grid coverage impact.

**Impact**: The similar point estimates provide confidence in the initial
area-weighted pilot without claiming they estimate the same population.

### 2026-07-22 03:10 UTC: Use clustered bounded-window discovery

**Context**: Invalid MUKEYs in one final run are expected to be spatially
close. A national adjacency graph or an individual national MUKEY lookup would
not meet the required query cost.

**Decision**: The Phase 2 native interface accepts adjacent source-MUKEY sets
plus their run-local EPSG:5070 bounds, expands one window per cluster, and
uses worker-local GDAL handles for concurrent clusters.

**Impact**: Candidate discovery is proportional to bounded crops, not the
national raster. This remains research tooling until benchmark and masked-valid
evidence supports production wiring.

### 2026-07-22 03:20 UTC: Stage candidate selection as four milestones

**Decision**: First return local pixel support from the native candidate
kernel, then shadow the simple local-majority proposal, evaluate it, and only
then consider an ADR-governed production policy.

**Impact**: Selection remains explainable and testable; no score or fallback
behavior is introduced during Milestone 1.

### 2026-07-22 03:35 UTC: Ratify shadow evidence storage and clustering

**Decision**: Persist additive per-hillslope shadow evidence in
`ssurgo_candidate_shadow_d` and matching nullable `soils/soils.parquet`
columns. Cluster invalid hillslope bounds after a 250 m expansion.

**Impact**: Existing final assignments and substitution fields remain
unchanged. Consumer review found current report, export, DuckDB, and migration
paths project known parquet fields and remain compatible with additive columns.

### 2026-07-22 03:55 UTC: Scaffold masked-valid evaluation

**Decision**: Milestone 3 evaluates read-only local-majority proposals against
the present global baseline; it does not set a production promotion threshold.

**Impact**: Exact-MUKEY recovery and declared soil/WEPP summary distance can
be reported side by side before an ADR chooses an acceptance criterion.

### 2026-07-22: Make feature similarity primary and establish the fixture corpus

**Decision**: Keep exact withheld-MUKEY recovery as a diagnostic, interpret
declared soil/WEPP feature distance as the primary later metric, and track the
growing GeoTIFF fixture corpus with Git LFS.

**Impact**: The test suite has deterministic coverage for candidate discovery
without treating an identifier match as the only good donor outcome. There is
still no production threshold or fallback policy change.

### 2026-07-22: Hold Milestone 4 after representative masked-valid evidence

**Decision**: Do not author a parameterization ADR or opt-in fallback policy.

**Impact**: The full 298-case local cohort supplies promising directional
feature and elevation evidence, but two runs, an unweighted feature distance,
and incomplete converter-failure fixtures do not support a production choice.

### 2026-07-22: Evaluate heuristic scoring as a research policy family

**Decision**: Score candidates with eligible profile, map-geometry, and terrain
families after failure-class gating; compare weight variants on held-out runs.

**Impact**: Pixel support remains a bounded-window prevalence feature, not a
claim of shared-boundary adjacency. Production scoring remains blocked on
per-source geometry evidence, deterministic fixtures, and an ADR.

### 2026-07-22: Select NED1 for the scoring experiment

**Decision**: Use `/wc1/geodata/ned1/2024/.vrt` and bilinear warp to the run
SSURGO grid for external elevation evidence.

**Impact**: The 1 arc-second product matches the 30 m scoring scale. NED13 is
not used because its finer source resolution would be resampled away while
increasing remote VRT I/O.

### 2026-07-23: Retain M4 HOLD after failure-class and held-out evidence

**Decision**: Do not seek a parameterization ADR or implement a production
shadow policy from the present heuristic evidence.

**Impact**: The deterministic fixtures establish safe score-family gates, but
the four held-out runs do not demonstrate a consistent improvement over the
global fallback. Next work must enlarge geographic evaluation and review real
residual-invalid provenance before defining a confidence threshold.

### 2026-07-24: Separate local-candidate coverage from ranking

**Decision**: Persist all local-candidate distances, ranks, and raw score
margins; compare the local oracle with top 1/2/3 before changing candidate
rings or score weights.

**Impact**: The study can now distinguish a ranker miss from a local-set miss.
No margin threshold or production shortlist has been selected.

### 2026-07-25: Preserve larger-cohort discovery and ranking diagnostics

**Decision**: Keep zero-eligible runs in the cohort manifest and use local
oracle misses to target the next broader-ring experiment.

**Impact**: The study now distinguishes 110 ranker-headroom cases from 11
local-candidate-set misses without setting a production cutoff.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| NRCS source data changes between cohorts | Medium | Medium | Record source date, seed, cache/provenance, and cohort separately | Open |
| NRCS request outage is mislabeled as invalid soil | High | Low | Keep data-access and converter-worker failures distinct | Mitigated |
| Area weighting hides rare failures | Medium | High | Add the unweighted-MUKEY cohort | In progress |
| Research score becomes a silent production default | High | Low | Require a later ADR and separate implementation package | Mitigated |

## Verification Checklist

### Code Quality

- [x] Canonical targeted test passes: `wctl run-pytest
  tests/tools/test_ssurgo_empirical_study.py --maxfail=1` (4 passed).
- [x] Expanded-cohort runner has atomic batch/resume/retry evidence.
- [x] Native clustered-window kernel compiles and targeted crate tests pass:
  `cargo test -p raster_characteristics_rust` (3 passed).
- [x] Representative clustered-window benchmark records worker/crop evidence.
- [ ] Full-suite validation considered before package closure.

### Security

- [x] Security impact triage recorded as `none`.
- [x] No dedicated security review required.

### Documentation

- [x] Strategy and initial pilot report recorded.
- [x] Active work package, tracker, and ExecPlan created.
- [x] Expanded-cohort aggregate report recorded.
- [ ] Fixture and masked-valid evidence recorded.

### Testing

- [x] Synthetic raster inventory and diagnostic aggregation tests pass.
- [ ] Expanded cohort validates all diagnostic records against schema version 1.
- [ ] Fixture tests cover each observed primary failure class.
- [x] Masked-valid candidate fixture corpus exercises the public native binding
  with direct, expansion, tie, exhaustion, and separated-cluster cases.
- [x] Read-only representative cohort compares local/global donor feature and
  aligned-elevation differences for all eligible hillslopes in two local runs.

## Progress Notes

### 2026-07-21 18:00 UTC: Initial cohort and scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Added `tools/ssurgo_empirical_study.py` with a VAT-aware national inventory,
  versioned diagnostic-record contract, and aggregate helpers.
- Added `tests/tools/test_ssurgo_empirical_study.py`.
- Ran a seeded 2,048-draw mapped-area cohort through the current converter.
- Published aggregate findings in the investigation report; raw NRCS-derived
  JSONL remains outside git under `/tmp/ssurgo_empirical_study_20260721/`.

**Blockers encountered**:

- The first full raster block scan was stopped after the VAT was discovered;
  the VAT is the authoritative count source and avoids unnecessary resource use.

**Next steps**:

- Run the approved expanded cohorts.
- Turn the observed failure types into fixtures before considering candidates.

**Test results**: canonical `wctl` targeted test passed: 3 passed.

### 2026-07-22 02:40 UTC: Expanded cohort execution

**Agent/Contributor**: Codex

**Work completed**:

- Added a research-only resumable cohort command with atomic JSONL batch
  checkpoints and a distinct `data_access_failed` outcome.
- Completed and schema-validated both approved cohorts against the 2025 VAT.
- Recorded the separate rates, reason distributions, and zero NRCS access
  failures in the investigation report and ExecPlan.

**Next steps**:

- Build fixtures for no component, no horizons, missing attributes,
  nonphysical texture balance, and the residual-unclassified cases.

**Test results**: canonical targeted test passed: 4 passed.
