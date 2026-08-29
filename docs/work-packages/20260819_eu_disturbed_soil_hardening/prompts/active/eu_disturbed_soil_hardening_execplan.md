# Harden EU Disturbed Soil Building Against Invalid Source Profiles

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to
date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, an EU disturbed-soil build will either produce a finite,
ordered, WEPP-valid soil profile or expose a precise, location-specific
diagnostic explaining why it could not. The first deliverable is not a
fallback: it is a reproducible fixture of real locations and source samples
so that later validation decisions are based on observed data rather than
synthetic assumptions.

The package is intentionally phased. Complete and document one phase before
starting the next. The active phase may change as evidence arrives; update this
plan and the companion tracker at every stopping point.

## Progress

- [x] (2026-08-19 19:37 UTC) Reviewed the ESDAC builder, SoilHydroGrids
  adapter, shared horizon calculations, and current EU integration test.
- [x] (2026-08-19 19:37 UTC) Authored the work-package scaffold and recorded
  initial hardening hypotheses.
- [x] (2026-08-19 19:47 UTC) Added the deterministic raster-cell manifest
  generator and pure sampling tests (`4 passed`).
- [x] (2026-08-19 20:46 UTC) Executed the 1,000-sample valid-cell pilot:
  source screening flagged 641 locations; 596 suspicious builds completed,
  35 raised builder exceptions, 59 generated profiles had non-increasing
  horizon depths, and 10 controls built without output-order issues.
- [x] (2026-08-19 20:56 UTC) Captured six minimized pilot cases with source
  payloads, provenance, expected outcomes, and a no-geodata replay harness;
  the fixture suite passed (`7 passed`).
- [x] (2026-08-19 21:04 UTC) Added a seventh degraded replay case and drafted
  the evidence-backed taxonomy and proposed ADR-0043; the fixture suite
  passed (`8 passed`).
- [x] (2026-08-19 21:14 UTC) User reviewed and ratified ADR-0043; Phase 2 is
  complete and Phase 3 may proceed under the accepted contract.
- [x] (2026-08-19 21:28 UTC) Implemented the pure Phase 3 validator/result
  contract and fixture-backed diagnostics tests; targeted suite passed
  (`22 passed`).
- [x] (2026-08-19 22:02 UTC) Integrated Phase 4 validation into the builder,
  added typed worker/batch outcomes, isolated staging, additive
  `soil_quality.json` reports, and regression tests; the EU hardening suite
  passed (`30 passed`).
- [x] (2026-08-19 22:18 UTC) Completed the independent subagent review and
  dispositioned all findings; the final review reported no remaining
  blocker/high/medium findings. Phase 4 is complete and Phase 5 is queued.
- [x] (2026-08-19 22:43 UTC) Executed Phase 5 downstream validation: added a
  canonical-parser artifact validator and replayed valid, degraded, and
  rejected-base fixture cases through the 9002 disturbed transformation;
  downstream tests passed (`6 passed`).
- [x] (2026-08-19 21:39 UTC) Completed targeted, documentation, stub, and
  changed-file exception gates. The full suite reached 170 passed and 13
  skipped before an unrelated Docker CLI compose-contract failure.
- [x] (2026-08-19 23:42 UTC) Executed Phase 6 runtime hardening. The additive
  ESDAC provenance marker and per-location `soil_quality.json` carrier now
  gate single-OFE and MOFE publication through temporary canonical-parser
  validation, typed errors, complete coverage checks, soil-key binding, and
  single/MOFE rollback. Persistence, reuse, rejected/malformed carrier, and rollback
  regressions pass; correctness and QA artifacts are recorded. The production
  observation window remains pending deployment.
- [x] (2026-08-20 00:16 UTC) Replayed the seeded 1,000-cell Phase 0 campaign
  after hardening through the direct ESDAC builder. The source screen selected
  631 suspicious locations and 20 controls; 345 profiles passed serialized
  horizon checks and 306 returned structured rejection diagnostics. No
  successful profile had non-finite values or invalid depth order. The run
  intentionally stopped below the NoDb/WEPPcloud integration boundary.
- [x] (2026-08-28) Diagnosed deployed Forest RQ job
  `893db465-9012-4489-ab1e-06b8ec73f461`: all 21 locations shared
  `source.categorical.empty` for `fao90lev1`, but the batch traceback omitted
  that reason and did not name the persisted quality report.
- [x] (2026-08-28) Implemented and validated a bounded batch
  exception/log/status summary. Eight unit tests and two actual-raster tests
  pass, including a replay of the incident coordinate through the real ESDAC
  batch builder.
- [x] (2026-08-28) Proved interface conformance through the shared
  `controlBase` polling path: `jobinfo.exc_info` places the complete ESDAC
  terminal exception in Summary and the traceback in Details (`14 passed`).
  No soil-specific UI branch or canonical behavior change was required.
- [x] (2026-08-28) Dispositioned the independent correctness review's High
  status-telemetry masking finding and Medium grouping finding. Redis publish
  failures can no longer replace the typed ESDAC exception, and only rejection
  errors are grouped by code/field with deterministic representative evidence.
- [ ] (2026-08-28) Deploy the correction and confirm the next live rejection
  is diagnosable without opening the report first.
- [ ] Phase 0 scale-up: decide whether to run the 50,000-sample campaign.
- [x] Phase 1: capture source payload fixture and deterministic replay harness.
- [x] Phase 2: review and ratify the evidence-backed quality invariants and
  ADR-0043.
- [x] Phase 3: define and test the pure validation/result/error contract.
- [x] Phase 4: complete independent review disposition and final gates for the
  production hardening and diagnostics integration.
- [x] Phase 5: validate disturbed downstream generated artifacts.
- [x] Phase 6: complete runtime review gates and observation plan; production
  observation remains an explicitly tracked post-deployment activity.

## Surprises & Discoveries

- Observation: The worker wrapper delegates all quality-sensitive work to
  `ESDAC.build_wepp_soil`; it does not validate the returned horizon or file.
  Evidence: `wepppy/eu/soils/soil_build.py` calls the builder and immediately
  constructs a `SoilSummary`.

- Observation: `isfloat()` accepts `NaN` and infinities.
  Evidence: `wepppy/all_your_base/all_your_base.py::isfloat` only attempts
  `float(f)`; `HorizonMixin._rosettaPredict` relies on that predicate.

- Observation: The current second-horizon omission check is weaker than a
  profile-order check.
  Evidence: `esdac.py` tests only `h1.depth <= 0`; it never requires
  `h1.depth > h0.depth`.

- Observation: The host working tree does not expose the EU raster directories
  directly, but the compose-managed `weppcloud` development container does.
  Evidence: the live campaign completed through `wctl` using the installed
  ESDAC, STU, and SoilHydroGrids assets; direct host execution remains
  environment-dependent.

- Observation: The sampling manifest can be tested without importing or
  opening the EU rasters, but manifest generation itself correctly depends on
  the installed ESDAC anchor raster.
  Evidence: `tests/eu/soils/test_invalid_soil_search.py` passes without
  `/geodata`; `build_manifest` resolves the anchor through `ESDAC.catalog`.

- Observation: The installed anchor raster contains 10,121,083 valid cells
  out of 41,250,000 frame cells, so sampling the raster frame directly would
  overrepresent nodata/ocean cells.
  Evidence: the pilot manifest records `valid_anchor_pixels_only: true` and
  the source raster valid-cell count.

- Observation: Pilot source screening found the reported failure shape in
  real data: zero/missing STU values, missing depth classes, Ksat gaps, and
  generated profiles with decreasing cumulative horizon depths.
  Evidence: the campaign screen artifact reported 641 suspicious locations;
  59 of their generated `.sol` files had `sol.horizon_depth_order`.

- Observation: `Horizon.as_dict()` is not currently a safe evidence boundary;
  it references a missing `wilting_point` attribute and can misclassify a
  successful production build after the `.sol` is written.
  Evidence: the first campaign collector saw 606 such `AttributeError`
  results; the final collector records stable raw fields instead.

- Observation: Direct raster-cell screening and the production query path can
  select different cells on grids with different geometry or rounding. The
  minimized fixture therefore uses production-query payloads for completed
  builds and labels pre-exception screen payloads separately.
  Evidence: sample 0001's screen payload differed from `ESDAC.query` until
  the fixture was recaptured from the production query path; sample 0050
  fails before a complete production payload exists.

- Observation: Missing land-use metadata can coexist with a physically valid
  profile and valid serialized horizons.
  Evidence: `pilot-0021-missing-landuse-metadata` replays with `usedom=0`,
  ordered depths, and finite output; it is classified as degraded rather than
  rejected.

- Observation: The existing disturbed integration matrix runs WEPP but does
  not independently inspect the serialized disturbed `.sol` contract. The
  canonical `WeppSoilUtil` parser exposes the transformed 9002 metadata and
  horizon values needed for that check.
  Evidence: `tests/disturbed/test_disturbed_matrix.py` generated and ran
  files without asserting parsed horizon ordering or water-content validity;
  `tests/eu/soils/test_esdac_disturbed_downstream.py` now closes that fixture
  gap for EU base soils.

- Observation: `to_over9000()` may insert a 200 mm surface horizon when the
  source top horizon is deeper than 200 mm. This is valid when the resulting
  cumulative depths remain strictly increasing; it is not evidence of a
  source-depth defect by itself.
  Evidence: the valid Phase 1 control becomes `[200.0, 1200.0, 1500.0]` in
  the reparsed 9002 artifact.

- Observation: Runtime enforcement needs more than report readability. A
  marked run must prove complete TopoAZ coverage and bind each accepted result
  to the current base `soil_key` before any output is published.
  Evidence: independent Phase 6 review found lazy partial-report handling and
  stale-key risk; coverage preflight, key matching, and regression tests now
  close both paths.

- Observation: MOFE generation can publish multiple segment artifacts before
  synthesis completes. The runtime wrapper therefore snapshots existing `.sol`
  files and rolls back the complete operation on failure.
  Evidence: the Phase 6 rollback regression restores an overwritten existing
  file and removes a newly created segment.

- Observation: After hardening, the direct 1,000-cell replay converts the
  previously observed invalid-depth outputs into explicit rejection results.
  Evidence: 14 `horizon.depth_order` diagnostics were returned, while all 345
  successful `.sol` files were finite and strictly depth-ordered; eight
  successful profiles had only a zero `smr` value, which remains a permitted
  physical value under ADR-0043.

- Observation: Structured diagnostics are not operationally observable when
  the batch exception lists only rejected location IDs. Forest job
  `893db465-9012-4489-ab1e-06b8ec73f461` retained the exact reason in
  `soil_quality.json`, while its RQ traceback omitted both reason and report
  filename.
  Evidence: all 21 report entries contain `source.categorical.empty` for
  `fao90lev1` with raw value `["24", "", "No information"]`.

## Decision Log

- Decision: Create a captured source-payload fixture before changing builder
  defaults or fallback behavior.
  Rationale: Coordinates alone depend on external raster availability and
  version; source payloads make the reported failure replayable and separate
  upstream data defects from builder defects.
  Date/Author: 2026-08-19 / User + Codex.

- Decision: Keep fixture replay separate from optional live raster checks.
  Rationale: Fast unit tests must run without `/geodata`, while live checks are
  still useful for confirming capture provenance and raster behavior.
  Date/Author: 2026-08-19 / Codex.

- Decision: Do not impose blanket positive-value defaults during the evidence
  phase.
  Rationale: Some zero values may be physically valid; changing them before
  classification would mask the failure and require an ungrounded scientific
  assumption.
  Date/Author: 2026-08-19 / User + Codex.

- Decision: Run source screening by recorded raster cell and run targeted
  builders in isolated processes.
  Rationale: the anchor, STU, and HydroGrids rasters do not all share the
  same geometry, so screening must transform once per source grid; GDAL-backed
  builder instances are isolated to avoid thread contention. This is a
  campaign-runner decision and does not change production behavior.
  Date/Author: 2026-08-19 / Codex.

- Decision: Keep Phase 1 replay at the ESDAC query boundary and monkeypatch
  only source providers in the test.
  Rationale: this exercises the real `Horizon` construction and `.sol`
  serialization while avoiding `/geodata`; it also preserves the exact
  production categorical-key normalization and exception classes.
  Date/Author: 2026-08-19 / Codex.

- Decision: Identify the production gate with an additive ESDAC provider marker
  on `Soils`, and carry per-location quality through the existing
  `soil_quality.json` report.
  Rationale: report presence alone cannot distinguish an ESDAC run from a
  legacy EU or user-defined soil workflow, while a persisted marker makes the
  EU-specific boundary explicit. Existing NoDb payloads default to no marker;
  a marked ESDAC run with a missing or malformed report fails explicitly rather
  than silently bypassing validation.
  Date/Author: 2026-08-19 / Codex.

- Decision: Adopt a three-state quality contract and field-qualified reason
  codes before implementing validation.
  Rationale: the fixture distinguishes optional metadata degradation from
  mandatory source, horizon, Ksat, and serialization failures. The proposed
  texture tolerance and partial-Ksat policy affect generated model inputs and
  are therefore recorded in ADR-0043. The user reviewed and ratified the ADR
  on 2026-08-19.
  Date/Author: 2026-08-19 / User + Codex.

- Decision: Keep Phase 3 pure and defer production wiring to Phase 4.
  Rationale: the validator and diagnostic carrier can be tested against the
  captured fixture without changing current builder behavior. This isolates
  policy failures from multiprocessing and NoDb compatibility changes.
  Date/Author: 2026-08-19 / User + Codex.

- Decision: Preserve the successful single-location builder tuple and add
  quality through the returned horizon attribute and typed worker result.
  Rationale: existing direct callers retain `(key, horizon, description)`,
  while the worker boundary gains explicit per-location diagnostics without
  widening the NoDb mapping contract.
  Date/Author: 2026-08-19 / Codex under ratified ADR-0043.

- Decision: Stage each worker's `.sol` separately and commit only an
  all-accepted batch.
  Rationale: a rejected location must not leave partial current-batch output
  or enter the hillslope mapping; `soil_quality.json` remains available for
  operator diagnosis.
  Date/Author: 2026-08-19 / Codex under ratified ADR-0043.

- Decision: Validate disturbed files after serialization by reparsing them
  with `WeppSoilUtil`, and merge accepted-base diagnostics into the downstream
  result.
  Rationale: in-memory transformation state does not prove that the emitted
  WEPP artifact can be read by the canonical parser. A degraded base remains
  degraded with its source reason, while a rejected base returns its original
  diagnostics plus an explicit downstream rejection rather than becoming a
  generic soil. The check keeps the Phase 4 zero-value policy: only
  nonrepresentable downstream values such as nonpositive Ksat are rejected;
  valid zero flags and gravel values are not blanket-rejected.
  Date/Author: 2026-08-19 / Codex under ratified ADR-0043.

- Decision: Treat report coverage, source-soil identity, and complete MOFE
  publication as runtime correctness boundaries. A marked ESDAC operation
  must preflight all required non-channel TopoAZ entries, match each report
  `soil_key` to the current base mapping, and restore the pre-operation `.sol`
  set if MOFE synthesis fails.
  Rationale: A readable but partial report can otherwise fail late, stale
  quality evidence can be applied to a remapped base soil, and a multi-file
  MOFE operation can leave a mixed result. The low-level report parser still
  permits an empty accepted profile list for carrier round-trip compatibility;
  runtime entry points require the locations they are about to process.
  Date/Author: 2026-08-19 / Codex under Phase 6 review.

- Decision: Duplicate a bounded diagnostic summary at the batch
  exception/log/status boundary while keeping `soil_quality.json` as the full
  authority.
  Rationale: a failed RQ job must explain why it failed without requiring
  filesystem archaeology, but large watersheds must not create unbounded log
  payloads. The summary caps locations and grouped reasons, carries counts and
  representative raw evidence, and makes no scientific-policy change.
  Date/Author: 2026-08-28 / User + Codex during Phase 6 observation.

## Outcomes & Retrospective

Phase 1 confirmed that the reported classes are replayable without live
rasters: source zeros can reach the current builder, cumulative horizons can
be written in decreasing order, and source/provider failures surface as
unstructured exceptions. The fixture also exposed a distinction between
screen-cell payloads and production query payloads, which is now recorded as
provenance rather than silently merged. Phase 2 ratified a seven-case
valid/degraded/rejected contract and ADR-0043. Phase 3 provided a pure
validator and diagnostic carrier. Phase 4 now wires that contract into the
builder and batch worker, preserving the successful tuple while rejecting bad
profiles before commit and retaining per-location evidence in
`soil_quality.json`. Independent review found and closed
report-serialization, malformed-shape, staging atomicity, duplicate-key, and
STU normalization issues; the final review has no unresolved
blocker/high/medium findings. Phase 5 adds a canonical-parser downstream
artifact validator: the valid control and degraded metadata case produce
valid serialized 9002 transformations (with degradation retained), the
rejected zero-profile produces no downstream artifact, and deliberately
mutated water, depth, and Ksat fields are rejected after reparsing.

Phase 6 carries the ESDAC quality result through the additive `Soils` provider
marker into Disturbed single-OFE and MOFE runtime paths. Marked runs fail
before generation on missing, malformed, incomplete, or stale quality
carriers; valid and degraded results publish only after canonical parsing;
rejected bases never receive a generic replacement; and MOFE failures restore
the prior `.sol` set and controller state for both single-OFE and MOFE
operations. The independent correctness review dispositioned all findings,
and the QA artifact records the gates and the post-deployment observation plan.

The post-hardening Phase 0 replay provides a direct-builder health checkpoint:
345 targeted profiles serialized as finite, ordered two-horizon files, while
306 source or profile defects were rejected with location-specific diagnostics.
The campaign is intentionally not an integration test; NoDb, Disturbed, and
WEPPcloud behavior remains covered by the focused suites and deployment
observation plan.

The first recorded Forest rejection during observation proved that the full
quality carrier was durable but the RQ boundary was not self-diagnostic. The
Phase 6 correction now mirrors a bounded reason summary and report filename
into the exception, log, and status channel; the full report remains the
source for per-location evidence. Live deployment confirmation remains open.

## Context and Orientation

The EU path begins in `wepppy/nodb/core/soils.py`, which selects the ESDAC
builder for EU gridded soils. It calls `wepppy/eu/soils/soil_build.py`, whose
worker invokes `ESDAC.build_wepp_soil`. The builder samples categorical ESDAC
rasters through `query`, continuous STU rasters through
`query_derived_db`, and Ksat depth rasters through
`wepppy/eu/soils/eusoilhydrogrids/eusoilhydrogrids.py`. It creates two
`Horizon` objects, uses `HorizonMixin` for derived conductivity, erodibility,
and Rosetta values, and writes a version-7778 `.sol` file.

An ESDAC horizon is a soil layer represented by bottom depth plus physical
parameters. In the WEPP file, layer depths are cumulative depths from the soil
surface, so a two-layer profile must have a strictly deeper second horizon.
SoilHydroGrids Ksat values describe hydraulic conductivity by standard depth
slice; missing values must not be silently confused with measured near-zero
conductivity.

The current test at `tests/eu/soils/test_esdac_build.py` requires external
geodata and asserts only that a file exists. The new fixture should therefore
test the builder contract independently of the raster installation, then add a
separate optional live verification.

The package target is faithful extraction of the current ESDAC behavior into a
replayable test boundary. The fixture and replay adapter are scaffolding only;
they are not a substitute data source and cannot close the implementation
phase by themselves. Implementation closeout requires generated output from
the current production path.

## Plan of Work

### Phase 0: Random invalid-soil search and evidence freeze

Generate a deterministic set of 50,000 unique raster-cell samples from the
actual ESDAC footprint. Use a fixed seed and spatial strata, and record the
source raster versions, cell indices, coordinates, and sampling manifest. Do
not use a simple Europe bounding box without footprint filtering, because the
sample would be dominated by ocean and out-of-coverage points.

Before the full campaign, run a 1,000-sample pilot to benchmark source-screen
and full-build cost. The pilot can tune worker count or implementation details,
but must not silently change the seed, target size, or classification rules.

Run a cheap source screen over the random set. Flag missing/nodata,
non-finite, zero, out-of-range, inconsistent texture, invalid CEC, suspicious
depth ordering, and incomplete Ksat profiles. Run the full builder for all
flagged cells plus a fixed valid control sample. Preserve the source payload,
generated `.sol` or exception, and classification for each flagged case.

If Marta later provides coordinates, add them as separately labeled cases; do
not replace the random sample or its provenance.

The 50,000 target provides approximately 95% probability of observing at least
one defect when the defect prevalence is about 0.006% or greater, under the
usual independent-sampling approximation. This is a discovery target, not a
claim that unobserved cells are valid.

If matching raster assets are unavailable, mark the search as blocked rather
than presenting a synthetic payload as a real reproduction.

### Phase 1: Fixture and replay harness

Add a fixture under `tests/eu/soils/fixtures/` containing the pilot/full-search
case metadata
and the sampled source payloads needed by the builder. The preferred schema is
one JSON document with `schema_version`, `source`, `captured_at`, `coordinates`,
`esdb`, `stu`, `hydrogrids`, `expected_issues`, and `expected_output` fields.
Use JSON-safe finite numbers; represent source nodata explicitly as `null` and
represent non-finite test values with a documented token or a Python-side test
case rather than invalid JSON.

Add a deterministic test seam at the narrowest practical boundary. It may use
an in-memory provider or monkeypatched `query`, `query_derived_db`, and
`SoilHydroGrids.query` methods, but the replay must exercise `Horizon`
construction and `.sol` serialization. Assert issue reproduction and parse
the generated file rather than comparing build timestamps or comments.

Keep the existing real-raster integration test, and add a capture/verification
test only when the required geodata exists. That test should report the source
dataset paths or versions used so fixture drift is visible.

### Phase 2: Quality taxonomy and invariant contract

For each captured case, classify the first invalid boundary: source sample,
horizon derivation, Rosetta result, Ksat profile, or serialization. Define
field-specific rules rather than a blanket rule that every numeric field must
be greater than zero. At minimum, evaluate finite values, valid categorical
CEC, texture fractions and balance, positive density, ordered cumulative
depths, valid water-content relationships, and Ksat missingness.

Include a valid-zero control for any property where zero is scientifically
possible. A field that is mathematically valid but produces a zero WEPP
parameter may still require a separate model-output policy; document that
distinction explicitly.

### Phase 3: Pure validation/result contract and observability design

Define the pure per-location validator, result carrier, reason-code mapping,
and batch rejection policy. Preserve TopoAZ and coordinate context in every
diagnostic. Demonstrate valid, degraded, and rejected outcomes against the
captured fixture without wiring the validator into production execution yet.
If a fallback is approved, specify its source, scope, reason, and
observability; do not add a generic fallback merely to keep the worker pool
alive.

The ratified ADR-0043 is the policy input for this design. Phase 4 will wire
the pure contract into the builder and worker aggregation.

### Phase 4: Production integration

Add the smallest explicit validation boundary to `esdac.py`, then update the
worker/result aggregation only if needed to carry diagnostics. Validate before
writing the `.sol`. Ensure non-finite values, malformed texture balances,
invalid depth ordering, and unrepresentable Ksat states cannot silently become
valid-looking output. Use narrow exception types and preserve useful context.

The successful single-location builder tuple remains `(key, horizon,
description)`, with its additive quality result attached to the top horizon.
Workers return a result for every input location, including expected rejection
diagnostics. Each worker writes into an isolated staging directory. The parent
commits staged `.sol` files and the additive `soil_quality.json` report only
when all locations are valid or degraded; a rejected batch writes its report,
discards staged files, and raises an actionable typed batch error before the
NoDb mapping is returned.

Add regression tests for every confirmed failure case, at least one valid and
one degraded case, accepted/rejected staging behavior, and JSON report
serialization. Keep source sampling and validation separable so future raster
versions can be recaptured without rewriting the contract tests.

### Phase 5: Disturbed downstream validation

Feed valid generated base soils through the EU disturbed transformation path.
Write the transformed 9002 file, reparse it with `WeppSoilUtil`, and validate
finite OFE/horizon parameters, positive and strictly ordered cumulative
horizons, `0 <= wp <= fc <= 1`, positive Ksat, and expected `luse`/`stext`
metadata through `validate_disturbed_soil_artifact()`. Replay the valid
`pilot-0001-control` and degraded `pilot-0021-missing-landuse-metadata`
cases, and pass the rejected `pilot-0014-zero-stu` result into the downstream
boundary to prove its source diagnostics are preserved without a generic
artifact. Mutated serialized water, depth, and Ksat values are negative
controls for the parser boundary.

The validator is an additive EU quality boundary and the Phase 5 fixture
closeout does not change the general Disturbed controller's write API. The
Phase 6 decision is now to carry the EU base result into the EU disturbed
runtime path for enforcement; non-EU builders and legacy workflows remain
outside this scope.

### Phase 6: Reviews, observation, and closeout

Implement and review the EU-specific runtime downstream gate. Carry the
per-location Phase 4 quality result into the Disturbed single-OFE and MOFE
paths, write generated EU files to isolated temporary paths, reparse them with
the canonical validator, and publish only accepted artifacts. Preserve base
and downstream diagnostics in the typed error/report path; do not broaden the
gate to non-EU soil builders. Add correctness and QA review artifacts under
`artifacts/`, disposition all medium/high findings, run the required targeted
and repository gates, and record exact evidence in the tracker. If behavior is
deployed, observe target error recurrence and valid-state rejection for 14–30
days. Any temporary compatibility branch must have an owner, review date, and
sunset condition.

The compatibility plan for the runtime carrier is additive. `Soils` will gain
an optional persisted provider marker that is set only by the ESDAC builder and
defaults to absent/`None` for existing NoDb payloads and all other builders.
The existing `soil_quality.json` report remains the authoritative per-location
quality carrier; no user-visible soil keys or report fields are renamed or
removed. Disturbed will enforce the gate only when that marker identifies an
ESDAC build. If the marker is present but the report is missing, malformed, or
does not contain the requested location, the EU path raises a typed diagnostic
instead of falling through to generic disturbed behavior. Non-EU and legacy
non-ESDAC paths retain their current behavior.

## Concrete Steps

Until matching EU geodata is available, run only read-only discovery and
documentation checks from `/home/workdir/wepppy`:

    rg -n "ESDAC|SoilHydroGrids|zero|invalid horizon|NaN|nan" wepppy tests docs/work-packages -S
    wctl doc-lint --path docs/work-packages/20260819_eu_disturbed_soil_hardening

When source artifacts are available, capture them without modifying production
data. Store only the minimal source samples and provenance needed for replay;
do not commit secrets, credentials, or entire external raster datasets.

The expected Phase 0 campaign commands are:

    python tools/eu_invalid_soil_search.py --pilot 1000 --seed 20260819 --output /tmp/eu-invalid-soils-pilot
    python tools/eu_invalid_soil_search.py --samples 50000 --seed 20260819 --output /tmp/eu-invalid-soils-full

The exact tool path and options may be adjusted during the pilot if an existing
canonical raster-sampling utility is identified. The output must include a
machine-readable manifest and a summary of valid, anomalous, rejected, and
builder-exception cases.

For Phase 1 validation, run:

    wctl run-pytest tests/eu/soils/test_esdac_build.py
    wctl run-pytest tests/eu/soils/test_esdac_quality_fixture.py

The first command may skip the live test when EU geodata is absent. The
fixture test must not skip for that reason.

For implementation closeout, run targeted tests, the changed-file broad
exception check, documentation lint, and `wctl run-pytest tests --maxfail=1`.
Record exact pass/skip counts in `tracker.md`.

## Validation and Acceptance

Phase 0 is accepted when the 1,000-sample pilot and, after review, the
50,000-sample campaign record the seed, raster/data versions, unique samples,
source anomalies, full-build failures, invalid profiles, and valid controls.
Each discovered invalid soil must have exact provenance and a reproducible
symptom classification. Phase 1 is accepted when replay tests
reproduce the cases without `/geodata` and a valid control generates a valid
file. Phase 2 is accepted when every invariant is tied to evidence or an
explicit scientific decision. Phase 3 is accepted when the valid/degraded/
rejected contract is documented with worker-level diagnostics.

The implementation is accepted only when generated `.sol` files from the
current EU path contain finite, ordered, contract-valid horizons; invalid
cases produce explicit diagnostics; valid controls remain accepted; disturbed
downstream outputs remain valid; and the required review and repository gates
pass.

## Idempotence and Recovery

Fixture capture is additive and may be repeated by creating a new capture
record or updating a case's provenance after review. Never overwrite an
original incident artifact without preserving its hash or source reference.
Production code changes must be staged behind tests so an unsuccessful
validation-policy experiment can be reverted without deleting fixture
evidence. Do not regenerate the ignored generated documentation index as part
of this package.

If a fallback policy is rejected, retain the diagnostics and fixture tests and
remove only the fallback implementation. If a generated output changes
unexpectedly, compare parsed horizon values and source payloads before any
rollback or threshold adjustment.

## Artifacts and Notes

Planned artifacts:

- captured source fixture and provenance note;
- fixture schema and replay test evidence;
- quality taxonomy/contract decision record;
- parameterization ADR if required;
- correctness review and QA review artifacts;
- final validation and observation summary.

The package currently contains no committed live-raster production-output
artifact. The compose-managed development container has the matching EU
rasters for campaign execution, but the generated manifest, source payloads,
and `.sol` files remain in container `/tmp` until a reviewed, minimized
fixture is selected. Deterministic Phase 4 tests cover staged output and
report serialization.

## Interfaces and Dependencies

The current interfaces that must remain understandable and testable are:

- `ESDAC.query(lng, lat, attrs)` returns categorical raster samples.
- `ESDAC.query_derived_db(lng, lat, attrs)` returns continuous STU samples.
- `SoilHydroGrids.query(lng, lat, "KS")` returns depth-keyed Ksat samples.
- `ESDAC.build_wepp_soil(...)` writes a version-7778 `.sol` and returns soil
  identity, top-horizon metadata, and description.
- `build_esdac_soils(...)` maps hillslope identifiers to generated soil keys.

If the hardening changes a return type or error payload, update the `.pyi`
stubs and all callers in the same phase. The final behavior must preserve
location context through the worker boundary and must not make a valid control
depend on the presence of the optional live raster installation.

---

Revision note (2026-08-19 19:37 UTC): Initial multi-phase hardening plan
authored from source review. No production behavior changed.

Revision note (2026-08-19 19:45 UTC): Phase 0 changed from waiting for Marta's
coordinates to a deterministic 1,000-sample pilot and 50,000-sample random
invalid-soil search. Marta's cases remain supplemental evidence.

Revision note (2026-08-19 19:47 UTC): Added and tested the manifest generator;
live campaign execution remains pending matching EU raster assets.

Revision note (2026-08-19 22:02 UTC): Executed Phase 4 production integration;
the builder now rejects invalid profiles with structured diagnostics, batches
stage output atomically, and persists `soil_quality.json`. Independent review
and final gates remain active.

Revision note (2026-08-19 22:18 UTC): Completed the required independent
subagent review and dispositioned every finding. Phase 4 is complete; Phase 5
downstream generated-artifact validation is queued.

Revision note (2026-08-19 22:43 UTC): Executed Phase 5. Added the
canonical-parser downstream artifact validator, 9002 fixture replay coverage,
negative serialized-parameter cases, and explicit rejected-base diagnostic
propagation. Six downstream tests pass; Phase 6 review and runtime wiring
decision remain.

Revision note (2026-08-19 23:59 UTC): Executed Phase 6. Added the additive
ESDAC provenance marker, quality-report parser and coverage/key checks,
single-OFE/MOFE runtime validation, single/MOFE rollback, structural carrier
checks, persistence regressions,
independent correctness review disposition, QA evidence, and the
post-deployment observation plan. Full repository validation remains blocked
by the known local Docker Compose CLI incompatibility; direct ESDAC stubtest
remains blocked by preexisting quality.py mypy errors.

Revision note (2026-08-20 00:16 UTC): Replayed the seeded 1,000-cell Phase 0
campaign after hardening through the direct ESDAC builder. The run targeted
631 suspicious cells plus 20 controls, emitted 345 finite and ordered `.sol`
files, and returned 306 structured rejections. No NoDb or WEPPcloud
integration was exercised; the campaign evidence is recorded in
`artifacts/phase0-post-hardening-1000-run.md`.
