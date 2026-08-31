# Tracker – EU Disturbed Soil Building Data-Quality Hardening

> Living document tracking evidence, decisions, risks, and validation for the
> EU ESDAC disturbed-soil hardening package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-19 19:37 UTC
**Current phase**: Phase 6 deployed observation and corrective hardening
**Last updated**: 2026-08-28
**Next milestone**: Validate and deploy the bounded ESDAC batch-failure
diagnostic, then continue the 14–30 day or 20-run observation window
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Scale to the 50,000-sample campaign after pilot performance review.
- [x] Select and minimize pilot cases for the Phase 1 fixture.
- [ ] Add Marta's cases later if coordinates or run artifacts become
  available.
- [x] Add deterministic replay fixture and no-geodata test harness.
- [x] Define and ratify the evidence-backed valid/degraded/rejected contract.
- [x] Implement the pure validation/result contract and fixture-backed
  diagnostics tests.
- [x] Implement the approved validation boundary and diagnostics.
- [x] Validate disturbed downstream generated artifacts.
- [x] Complete correctness, QA, and documentation gates; observation is
  explicitly pending post-deployment.

### In Progress

- [x] Reproduce Forest job `893db465-9012-4489-ab1e-06b8ec73f461` from its
  persisted quality report and identify the missing batch-error context.
- [ ] Complete and deploy the bounded batch-error/status diagnostic, then
  confirm the next rejected ESDAC job exposes its reason without report-file
  archaeology.
- [x] Phase 6 readiness: implement the EU-specific runtime gate, complete QA
  review, and define the observation plan.
- [x] Phase 6 implementation: carry the ESDAC marker and per-location quality
  report through single-OFE and MOFE publication boundaries.

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
- [x] Replayed the same seeded 1,000-cell campaign after hardening: 631
  source-suspicious locations plus 20 controls were targeted; 345 `.sol`
  files were valid and 306 locations returned structured
  `ESDACSoilBuildError` diagnostics. No successful output had non-finite or
  invalid-depth horizons (2026-08-20 00:16 UTC).
- [x] Added a six-case Phase 1 fixture with one control, two output-order
  cases, a zero-valued STU case, and three builder exception classes; replay
  tests pass without EU geodata (2026-08-19 20:56 UTC).
- [x] Added the Phase 2 taxonomy, seven-case valid/degraded/rejected matrix,
  and proposed ADR-0043; replay tests pass without EU geodata
  (2026-08-19 21:04 UTC).
- [x] User reviewed and ratified ADR-0043 for Phase 3 implementation; no
  production behavior changed (2026-08-19 21:14 UTC).
- [x] Added the pure Phase 3 validator, result carrier, diagnostic reason
  codes, and fixture-backed tests; production integration remains pending
  (2026-08-19 21:28 UTC).
- [x] Integrated source, horizon, and Ksat validation into the ESDAC builder;
  added typed worker/batch outcomes, per-worker staging, atomic report output,
  and Phase 4 regression tests (`30 passed` across the EU hardening suite;
  2026-08-19 22:02 UTC).
- [x] Completed the independent Phase 4 subagent review; all findings were
  fixed or explicitly dispositioned, with no remaining blocker/high/medium
  findings (2026-08-19 22:18 UTC).
- [x] Added the Phase 5 canonical-parser downstream validator and replayed
  valid, degraded, and rejected-base cases through the 9002 disturbed
  transformation; serialized water, depth, and Ksat negative controls pass
  (6 downstream tests passed, 2026-08-19 22:43 UTC).
- [x] Executed Phase 6 EU-specific runtime gating: additive ESDAC provenance,
  complete report coverage, `soil_key` binding, canonical single/MOFE output
  validation, typed rejection, and operation-level rollback for both paths
  (2026-08-19 23:42 UTC).
- [x] Completed Phase 6 correctness review and QA disposition; all identified
  P1/P2 findings were fixed and regression-tested. Observation remains open
  until deployment.

## Phase Gates

- **Phase 0**: the pilot and full campaign record seed, raster/data versions,
  unique samples, source anomalies, full-build failures, invalid profiles, and
  valid controls.
- **Phase 1**: deterministic fixture reproduces confirmed cases and includes a
  valid control without `/geodata`.
- **Phase 2**: every invariant is evidence-backed and valid zero values are
  distinguished from invalid source values.
- **Phase 3**: pure result contract preserves valid states and exposes
  invalid-state diagnostics without production integration.
- **Phase 4**: generated `.sol` output is finite, ordered, and contract-valid;
  invalid profiles do not silently write in the production path; rejected
  batches leave a `soil_quality.json` report and no newly staged `.sol` files;
  independent review findings are dispositioned.
- **Phase 5**: disturbed downstream artifacts remain valid and reproducible;
  valid/degraded/rejected fixture cases and serialized negative controls pass.
- **Phase 6**: review, observation, and documentation gates are complete.

## Timeline

- **2026-08-19 19:37 UTC** – Package opened from EU soil-builder review.
- **2026-08-19 19:45 UTC** – Phase 0 expanded to random invalid-soil search;
  Marta's cases are optional supplemental evidence.
- **2026-08-19 20:46 UTC** – 1,000-sample pilot and targeted builds completed;
  Phase 0 evidence review is pending.
- **2026-08-19 20:56 UTC** – Phase 1 fixture and no-geodata replay harness
  completed; all six cases reproduce.
- **2026-08-19 21:04 UTC** – Phase 2 taxonomy and proposed ADR-0043 drafted;
  the replay suite covers valid, degraded, and rejected outcomes.
- **2026-08-19 21:14 UTC** – User ratified ADR-0043; Phase 2 is complete and
  Phase 3 validation design is queued.
- **2026-08-19 21:28 UTC** – Pure Phase 3 validator and contract tests
  completed; Phase 4 production integration is queued.
- **2026-08-19 22:02 UTC** – Phase 4 builder/worker integration and staged
  batch-report tests completed; independent review and final gates are pending.
- **2026-08-19 22:18 UTC** – Independent subagent review completed with no
  unresolved blocker/high/medium findings; Phase 4 is complete and Phase 5 is
  queued.
- **2026-08-19 22:24 UTC** – Repository-wide gate stopped at the known Docker
  CLI incompatibility after `170 passed, 13 skipped`; the canary smoke test
  reports `unknown shorthand flag: 'f' in -f` before compose contract checks.
- **2026-08-19 22:43 UTC** – Phase 5 downstream fixture validation completed;
  the canonical-parser validator passed valid/degraded/rejected cases and
  serialized water/depth/Ksat negative controls.
- **2026-08-20 00:16 UTC** – Replayed the seeded 1,000-cell Phase 0 campaign
  after hardening. The source screen selected 631 suspicious locations and 20
  controls; 345 direct builds passed serialized horizon checks and 306 were
  rejected with structured diagnostics. This run did not exercise NoDb or
  WEPPcloud integration.
- **Pending** – 50,000-sample campaign; deterministic fixture is accepted.
- **Complete** – Quality contract and ADR-0043 ratified; Phase 4 production
  hardening implementation and focused tests completed.
- **Complete** – Disturbed downstream validation and generated-artifact
  contract replay.
- **Complete for implementation** – Phase 6 runtime, review, QA, and
  documentation gates; production observation remains pending.
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

### 2026-08-19 21:04 UTC: Evidence-backed quality contract

**Context**: The Phase 1 fixture demonstrates both physically valid metadata
degradation and mandatory source/output failures. The builder currently has no
structured outcome boundary.

**Decision**: Propose three outcomes: `valid`, `degraded` with visible
provenance, and `rejected` with field-qualified reason codes. Individual zero
texture components and zero gravel remain allowed; all-zero mandatory STU
texture, non-increasing horizons, provider failures, and all-missing Ksat are
rejected.

**Rationale**: The rules distinguish scientifically valid zero values from
missing evidence and prevent a generic fallback from masking source defects.
The one-percentage texture tolerance, partial-Ksat policy, and depth-class
handling are recorded in ADR-0043 because they affect model inputs.

**Approval state**: Ratified by the user on 2026-08-19. Phase 4 production
integration may proceed under ADR-0043.

### 2026-08-19 22:02 UTC: Additive production integration

**Decision**: Preserve the successful single-location builder tuple and add
quality through the returned horizon attribute and typed worker result.

**Rationale**: Existing direct callers retain `(key, horizon, description)`,
while the worker boundary gains explicit per-location diagnostics without
widening the NoDb mapping contract.

**Decision**: Stage each worker's `.sol` separately and commit only an
all-accepted batch.

**Rationale**: A rejected location must not leave partial current-batch output
or enter the hillslope mapping; `soil_quality.json` remains available for
operator diagnosis.

### 2026-08-19 22:59 UTC: EU-specific runtime downstream gate

**Context**: Phase 5 proves the serialized disturbed-artifact contract, but
the validator is currently an additive fixture/QA boundary. The user selected
runtime enforcement for EU ESDAC-derived soils within this package.

**Options considered**:

1. Keep the validator test-only — lowest compatibility risk, but invalid
   downstream artifacts could still be published by a production run.
2. Add an EU-specific runtime gate — carry the EU base quality result into the
   Disturbed single-OFE and MOFE writers, validate before publication, and
   preserve source plus downstream diagnostics.
3. Gate every disturbed soil format and source — broader protection, but an
   unnecessary compatibility surface for non-EU builders in this package.

**Decision**: Option 2, the EU-specific runtime gate.

**Normative boundary**:

- EU ESDAC base profiles with `valid` or `degraded` quality may enter the
  disturbed transformation; `rejected` profiles must not produce a generic
  replacement soil.
- Generated EU disturbed files are written to an isolated temporary path,
  reparsed with the canonical parser, and published only after the downstream
  contract passes.
- Rejections retain the base quality diagnostics and add downstream reason
  codes in an explicit typed error/report path.
- Non-EU soil builders and their existing Disturbed behavior remain outside
  this gate.

**Rationale**: This closes the confirmed EU data-quality path while preserving
compatibility for unrelated builders and legacy disturbed workflows. A
missing EU quality carrier is a provenance/error condition to resolve during
implementation, not permission to silently treat the profile as generic.

### 2026-08-19 23:09 UTC: Additive provenance carrier for runtime enforcement

**Decision**: Add an optional persisted ESDAC provider marker to `Soils` and
use the existing `soil_quality.json` file as the authoritative per-location
quality carrier. Enforce the downstream gate only when the marker identifies an
ESDAC build.

**Compatibility plan**: Existing NoDb payloads default to an absent/`None`
marker, and non-ESDAC builders keep their existing disturbed behavior. A
marked ESDAC run with a missing, malformed, or incomplete quality report raises
an explicit typed diagnostic rather than falling through to generic generation.
No existing soil keys or report fields are renamed or removed.

**Rationale**: Report presence alone cannot distinguish ESDAC from legacy EU or
user-defined soil workflows. The additive marker makes the enforcement scope
explicit while retaining the already persisted diagnostic evidence.

### 2026-08-19 23:42 UTC: Runtime carrier completeness and rollback

**Decision**: Treat report coverage, source-soil identity, and complete MOFE
publication as runtime correctness boundaries. A marked ESDAC operation must
preflight all required non-channel TopoAZ entries, match each report
`soil_key` to the current base mapping, and restore the pre-operation `.sol`
set if MOFE synthesis fails.

**Rationale**: A readable but partial report can otherwise fail late, stale
quality evidence can be applied to a remapped base soil, and a multi-file MOFE
operation can leave a mixed result. The low-level report parser still permits
an empty accepted profile list for carrier round-trip compatibility; runtime
entry points require the locations they are about to process.

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
- **Post-change health signals**: seven-case fixture covers valid, degraded,
  and rejected outcomes; Phase 4 batch tests pass; Phase 5 reparsed 9002
  artifacts for valid and degraded bases and rejected water/depth/Ksat
  mutations; valid/degraded batches commit staged outputs and rejected batches
  retain a diagnostic report without committing new `.sol` files. Phase 6
  adds complete report coverage, source-key binding, canonical runtime
  publication, and single/MOFE rollback tests. The post-hardening direct
  builder replay rejected 306 targeted locations explicitly and emitted 345
  finite, ordered profiles; detailed evidence is in
  `artifacts/phase0-post-hardening-1000-run.md`.
- **Danger signals observed**: quality checks currently emphasize file
  creation; invalid-source outcomes are not structured; source screening
  found STU zeros/missing values and missing depth classes; full builds are
  materially slower than raster-cell screening.
- **Temporary callus register**: none.
- **Softening experiments**: not applicable during evidence freeze.
- **Observation status**: pending deployment; observe 14–30 days or 20 EU
  disturbed runs, whichever is later.

## Verification Checklist

### Code Quality

- [x] Targeted EU soil tests pass (`37 passed`, 2 deprecation warnings;
  Phase 4's focused suite had 30 before Phase 5 additions).
- [ ] Full `wctl run-pytest tests --maxfail=1` passes before closeout. The
  final-tree run reached `170 passed, 13 skipped, 9 warnings` in 265.05s, then
  stopped at the unrelated Docker CLI failure in
  `tests/docker/test_canary_smoke_contract.py`: `docker compose` rejected
  `-f` with `unknown shorthand flag: 'f'`.
- [x] `wctl check-test-stubs` passes. Direct `wctl run-stubtest
  wepppy.eu.soils.esdac` remains blocked by preexisting mypy build errors in
  `wepppy/eu/soils/esdac/quality.py` (lines 211, 308, 319, 321, 330, 339),
  before the new downstream module is checked.
- [x] Changed-file broad-exception check passes.
- [x] `git diff --check` passes.

### Documentation

- [x] ESDAC/work-package documentation describes quality outcomes, staging,
  report output, and diagnostics.
- [x] User/operator behavior is documented through the additive
  `soil_quality.json` report and typed batch error contract.
- [x] Package and changed docs pass `wctl doc-lint`.
- [x] Parameterization ADR-0043 is ratified for Phase 3 implementation.

### Testing

- [ ] Captured fixture includes valid, zero, missing/nodata, non-finite,
  malformed-texture, depth-order, and Ksat cases as supported by evidence.
- [x] Replay tests run without EU raster installation.
- [x] Phase 3 pure contract tests run without EU raster installation.
- [ ] Optional live raster capture/verification is recorded separately.
- [x] Generated `.sol` parser and downstream disturbed tests pass.
- [x] The matrix covers populated valid metadata, empty/degraded optional
  metadata, a supported legacy 7778 base converted to 9002, and rejected
  mandatory source state.

### Reviews and Observation

- [x] Independent correctness subagent review artifact completed with no
  unresolved medium/high findings.
- [x] QA review artifact completed with no unresolved medium/high findings.
- [x] Health/danger signals and observation window recorded in
  `artifacts/phase6-qa-review.md`; production observation is pending.
- [x] No temporary calluses are retained.

## Progress Notes

### 2026-08-28: Forest rejection observability correction

**Agent/Contributor**: Codex

**Incident evidence**: Forest RQ job
`893db465-9012-4489-ab1e-06b8ec73f461` rejected all 21 locations for run
`conjunctive-observatory`. The traceback listed only TopoAZ IDs. The durable
`soils/soil_quality.json` showed the shared cause as
`source.categorical.empty` on `fao90lev1`, with raw value
`["24", "", "No information"]`.

**Correction**: The batch exception, module log, and status channel now carry
a bounded deterministic summary: at most 10 TopoAZ IDs, at most five grouped
diagnostic signatures, occurrence counts, representative raw values, and the
`soil_quality.json` filename. The persisted report retains every location and
diagnostic. No scientific validation or output-commit behavior changes.

**Interface conformance**: This is a restoration of the unchanged
`docs/ui-docs/controller-contract.md` status-stream and polling-failure
contract, not a new UI behavior. The shared controller already fetches
`jobinfo.exc_info`, renders the terminal exception in the control Summary, and
keeps the traceback in Details. A controller regression now proves the exact
226-character ESDAC diagnostic reaches both surfaces without truncation or a
second soil-specific presentation path (`14 passed`).

**Signals**: Health means a rejected batch can be diagnosed from the RQ
exception/status message and the named report agrees with its summary. Danger
means an `unknown_quality_failure` summary, an absent report, disagreement
between summary and report, or an unbounded error payload. The combined unit
and real-raster regression set passed (`10 passed`); the real-raster case
replayed the incident coordinate through the actual ESDAC batch builder and
verified both the error summary and durable report. Deployment and live RQ
recurrence confirmation remain pending.

**Independent review**: The correctness review found one High and one Medium
issue. The High finding was closed by narrowly catching Redis telemetry
failures so they are logged but cannot replace `ESDACSoilBatchError` in RQ
`exc_info`. The Medium finding was closed by grouping only error-severity
diagnostics by code and field, counting all occurrences, and choosing the
lexically first serialized raw value as the deterministic representative.
Regressions cover both dispositions, and post-fix re-review reported no new
findings. The complete EU soils suite passed (`42 passed`); frontend lint and
all controller tests passed (`821 passed`).

### 2026-08-19 23:42 UTC: Phase 6 runtime gate and closeout evidence

**Agent/Contributor**: Codex, with independent review by Herschel

**Work completed**:

- Added the additive persisted `Soils.soil_source` marker with legacy payload
  defaulting and exact ESDAC builder identity detection.
- Added quality-report parsing, complete non-channel TopoAZ coverage checks,
  accepted/degraded/rejected consistency checks, and `soil_key` binding.
- Enforced canonical parse-before-publish for single-OFE and MOFE outputs;
  reused outputs are revalidated and rejected bases cannot produce generic
  replacements.
- Added shared single/MOFE transaction rollback for preexisting and newly
  created `.sol` files plus controller state, with persistence, stale-key,
  incomplete-report, degraded-report, and reuse regressions.
- Recorded independent correctness findings and all dispositions in
  `artifacts/phase6-correctness-review.md`; QA evidence and the observation
  window are in `artifacts/phase6-qa-review.md`.

**Test results**: Final focused set passed (`50 passed, 2 warnings`). The
combined EU/disturbed/root-Soils suite passed (`139 passed, 20 skipped, 2
warnings`) before the final parser/rollback-only additions; the final focused
set includes those additions. Stub completeness, broad-exception enforcement,
Python compilation, and diff checks pass. Direct ESDAC stubtest remains blocked
by preexisting mypy errors; full repository pytest remains blocked by the
known Docker Compose CLI incompatibility.

**Observation**: Deployment observation is pending. Watch for rejected-base
fallbacks, publication without canonical validation, report coverage errors
after publication, and temporary `.sol` leftovers for 14–30 days or 20 EU
runs, whichever is later.

### 2026-08-19 22:43 UTC: Phase 5 downstream artifact validation

**Agent/Contributor**: Codex

**Work completed**:

- Added `wepppy/eu/soils/esdac/downstream.py` and its stub with a serialized
  artifact validator using the canonical `WeppSoilUtil` parser.
- Replayed `pilot-0001-control` and `pilot-0021-missing-landuse-metadata`
  through `to_over9000(..., version=9002)` and verified the written files,
  not only in-memory objects.
- Preserved degraded source diagnostics and rejected the zero-profile case
  before attempting to parse a missing downstream artifact.
- Added water-order, cumulative-depth-order, and zero-Ksat serialized negative
  controls. The downstream test file passes six tests.

**Scope note**: The validator is additive and establishes the EU artifact
contract. The Phase 6 decision now requires carrying the EU base quality
carrier into the EU disturbed runtime path; implementation and QA remain open.

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

- Define field-level validity rules and valid/degraded/rejected outcomes from
  the fixture evidence.
- Decide whether the 50,000-sample campaign is warranted after reviewing the
  pilot's issue prevalence and runtime.

**Test results**: `wctl run-pytest tests/eu/soils/test_invalid_soil_search.py`
passed (`6 passed`, 2 deprecation warnings); `wctl run-pytest
tests/eu/soils/test_esdac_quality_fixture.py` passed (`7 passed`, 2
deprecation warnings).

### 2026-08-19 21:04 UTC: Phase 2 contract draft

**Agent/Contributor**: Codex

**Work completed**:

- Classified seven minimized cases as valid, degraded, or rejected, including
  the missing-land-use metadata case added to the fixture.
- Documented source, derived-horizon, Ksat, and serialization invariants in
  `artifacts/quality-taxonomy.md`.
- Drafted [ADR-0043](../../adrs/ADR-0043-eu-esdac-soil-quality-contract.md)
  for the threshold and fallback decisions that must precede Phase 3.
- Made no production runtime changes.

**Approval needed**: EU soil maintainer review of the proposed contract,
especially texture tolerance, partial Ksat treatment, and depth-class policy.

**Test results**: `wctl run-pytest
tests/eu/soils/test_esdac_quality_fixture.py` passed (`8 passed`, 2
deprecation warnings). The Phase 0 search test remains green from the prior
phase (`6 passed`, 2 deprecation warnings).

**Next steps**: Approve or amend ADR-0043, then design Phase 3 validation and
structured diagnostics. Decide separately whether the 50,000-sample campaign
is warranted.

### 2026-08-19 21:28 UTC: Phase 3 pure validation contract

**Agent/Contributor**: Codex

**Work completed**:

- Added the pure ESDAC quality module with location-aware result and
  diagnostic dataclasses.
- Added source, horizon, water-content, depth-order, and Ksat validators with
  the ratified valid/degraded/rejected policy.
- Added fixture-backed classification tests plus valid-zero, provider-error,
  water-order, partial-Ksat, and missing-depth contract cases.
- Clarified that Phase 4, not Phase 3, wires the pure contract into the
  production builder and multiprocessing aggregation.

**Production status**: No builder, worker, or NoDb behavior changed.

**Test results**: `wctl run-pytest
tests/eu/soils/test_esdac_quality_contract.py
tests/eu/soils/test_esdac_quality_fixture.py
tests/eu/soils/test_invalid_soil_search.py` passed (`22 passed`, 2
deprecation warnings).

The repository gate `wctl run-pytest tests --maxfail=1` reached 170 passed and
13 skipped before the Docker CLI compose-contract failure documented in the
Code Quality checklist. Documentation lint passed for the package, ADR, and
`PROJECT_TRACKER.md`; stub completeness also passed.

**Next steps**: Integrate the result contract at the source-to-horizon and
worker boundaries in Phase 4; decide separately whether the 50,000-sample
campaign is warranted.

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
**Date**: 2026-08-19 21:28 UTC

**What's complete**:

- Work-package scaffold and active ExecPlan are present.
- Initial source-review hypotheses and phase gates are recorded.
- Phase 1 fixture and replay tests reproduce seven pilot cases without EU
  raster installation.
- Phase 2 taxonomy and accepted ADR-0043 are documented; no runtime behavior
  has changed.
- Phase 3 pure validator and contract tests are complete; Phase 4 production
  integration remains.

**What's next**:

1. Integrate the Phase 3 validation boundary and structured diagnostics under
   ADR-0043.
2. Decide and execute the 50,000-sample campaign if broader prevalence
   estimates are required.
3. Implement the smallest validation boundary only after the contract and
   parameterization decisions are recorded.

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
