# Complete production M3 and valid-support estimates


This is a living ExecPlan maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep Progress, Surprises & Discoveries, Decision Log and Outcomes & Retrospective
current, and update this package's tracker at every handoff.

## Purpose / Big Picture


Users already select M1 or M3 in the Post-fire debris flow control. M1 executes;
M3 reaches RQ but fails `integration_pending`. Finish M3 soil/terrain composition
and produce real event probabilities, design-storm probabilities and inverse
rainfall thresholds. Both models must calculate over usable spatial inputs,
display Valid coverage and expose an exact downloadable mask. The user should
use the existing control without another selector/API redesign. Reports and the
dashboard remain deferred.

This plan scaffolds full scientific integration, not a surrogate model. Closure
requires actual output from the installed owned WBT tool and development RQ
workflow. Implemented, wired, validated and deployed are separate states. No
production deployment is authorized by this package.

## Progress


- [x] (2026-09-14) Record owner requirement for basin-independent preparation:
  derive original keys and THICK extent per project; named runs are tests only.
- [ ] Implement reusable source preparation and prove the same path on at least
  two independent basins, without hand-authored per-basin manifests.
- [x] (2026-09-14 16:40 UTC) Scaffolded scope, accepted support/isolation, research,
  frozen source audit, soil regression plan and draft checkpoint.
- [x] (2026-09-14) Audit development sources and ratify soil/prepared-delivery/schema contracts; live missing-source acceptance remains due.
- [x] (2026-09-14 16:58 UTC) Audit actual development grid, original soil keys,
  WAL core records and strict-policy support; retain source hashes and proposal.
- [x] Resolve legacy H material policy and prepared-local delivery contract;
  acquisition remains a separate unapproved action.
- [x] (2026-09-14) Complete two preliminary source-proposal reviews and amend
  provenance, zero-value and bounded-read details; final checkpoint reviews pending.
- [x] (2026-09-14) Record owner rejection of strict material policy; investigate
  NRCS legacy H guidance and four depth candidates on frozen/live records.
- [x] (2026-09-14) Retain replacement experiment, numerical results and sixteen
  analytical cases; fix research duplicate-ID handling discovered in review.
- [x] (2026-09-14) Complete both independent contract reviews and commit standalone
  ancestor `89d673c38` before runtime edits.
- [x] (2026-09-14) Add isolated recorded-depth policy and initial real SQLite tests;
  49 soil tests passed before review corrections.
- [x] (2026-09-14) Add opt-in local M1 common support and version-2 reader;
  79 integration/rainfall tests passed, including real WBT partial/disjoint masks.
- [x] Close implementation review findings on sidecar-free WAL snapshots,
  nonfinite source values and lossless NULL/empty replay.
- [x] Add prepared-local primary/fallback raster composition and close bounded
  security review findings, including real rollback spill and symlink swaps.
- [x] Run increment validation: full Python 8,498 passed/103 skipped; latest
  combined focused gate 153 passed; final M1 reader check 55 passed.
- [x] Commit tested isolated implementation as `587c6b8de`; preserve offline
  defaults and leave production M3 explicitly pending.
- [ ] Implement production thickness adapter; prove unchanged soil building.
- [ ] Implement M3 terrain and shared-support aggregation/masks for both models.
- [ ] Integrate execution, freshness, publication and canonical summaries.
- [ ] Complete full validation, real browser/RQ evidence and independent reviews.
- [ ] Synchronize docs, close package and archive this plan with outcomes.

## Surprises & Discoveries


The initial delivery proposal described one development run's 34 cached keys
and extent as a one-time preparation. The owner clarified that generic basin
support is required. Those inventory observations must not become runtime
constants or a manual per-basin workflow.

NRCS documents legitimate paired horizons sharing depths and component totals
above 100. The offline helper rejects those cases. Frozen three-site records
contain neither; 42 of 44 Moscow Mountain map units have totals below 100.
These are evidence gaps to cover, not reasons to change shared WEPP validation.
The detailed source/code audit is `artifacts/soil_research.md`.

Development inventory found only 8,705 of 4,311,420 basin cells usable under
the strict offline soil policy. The other cells map to legacy H horizons.
The live cache lacks mapunit/legend/sacatalog lineage, and no prepared THICK
asset was found for this basin. USGS object HEAD succeeds with byte ranges;
acquisition has not occurred. See `artifacts/source_inventory.md`.

NRCS NSSH 618.38(C)(2) explicitly recognizes legacy H layers in approved map
units. The earlier recommendation missed that guidance. H-only eligibility
restores thickness estimates to all 4,311,420 basin cells, with mean
163.55344468875683 cm before SBS masking. The broader depth-no-R candidate
recovers additional frozen profiles; the Cr and endpoint choices remain explicit
scientific proposals, not prerequisites for making this development basin pass.

## Decision Log


Decision: source preparation derives original in-basin keys and DEM extent
from the selected project and produces the same local evidence/manifest contract
for any eligible basin. Require at least two independent basin acceptance cases.
Rationale: source evidence and THICK fallback are per-project dependencies, not
special fixtures for `addicted-reservist`. Existing acquisition limits and the
separate network-authority gate remain unchanged. Owner clarification recorded
by Codex, 2026-09-14.

Decision: owner approved the recorded-depth replacement by “proceed”; accepted
ADR-0067 and the prepared-local runtime contract are committed at `89d673c38`.
The earlier strict-material proposal and pending-ratification notes below are
historical. No acquisition or deployment is implied. Codex, 2026-09-14.

Decision: copy bounded main/WAL into visible attempt-owned snapshot directories
before opening SQLite. Independent review reproduced `mode=ro` creating shared
sidecars for a clean WAL database. Original stat identities bracket copying and
reading; retained SQLite copies preserve SQL NULL/empty distinctions lost in
inspection CSVs. This closes source-isolation/replay defects without changing
scientific policy. Codex, 2026-09-14.

Decision: use common valid spatial inputs per model; retain full-basin geometry
for M3 ruggedness and study-area warnings. Rationale: predictors should describe
the same observed area without changing the drainage basin when soil/SBS is
missing. Owner accepted the explanation, 2026-09-14; Codex recorded it.

Decision: protect SSURGO/STATSGO builders as read-only upstream dependencies.
Rationale: M3 depth validity differs from WEPP parameter readiness; new model
policy must not change existing soil construction. Owner requested particular
regression protection, 2026-09-14. Exact soil policies are still pending.

Decision: prepare an explicit conservative soil and bounded source-delivery
proposal rather than infer H material or collection lineage from cache names.
Rationale: this affects almost the entire development basin. ADR-0067 is
proposed, not accepted; S05–S09 and acquisition authority remain unresolved.
Codex recorded this execution finding on 2026-09-14.

Decision: owner rejected the strict-material proposal as non-viable and
authorized depth-based investigation. Replace the proposed ADR-0067 material
section with recorded-depth inclusion of H/Cr, explicit hard-R exclusion,
endpoint-based thickness with separate-field warnings, and bounded legacy-pair
recognition. Rationale and measured alternatives are retained in
`artifacts/depth_policy_assessment.md`. Replacement ratification and source
acquisition remain pending; the earlier conservative recommendation is rejected.

## Outcomes & Retrospective


Milestone 1 is complete at checkpoint `89d673c38`. Milestone 2 implementation is
in progress: recorded-depth derivation, bounded snapshots and prepared-local
cellwise soil composition have focused tests; both bounded soil implementation
reviews closed their source-isolation/replay findings. Local opt-in M1 common
support and v2 reading pass real WBT tests but are not wired to production.
M3 terrain composition, runtime,
builder/generated-input parity and live acceptance remain. No acquisition,
shared soil rebuild or deployment has occurred.
The owner has clarified generic delivery scope: reusable source preparation and
multi-basin acceptance remain required, rather than one-off validation inputs.

## Context and Orientation


Work from `/home/workdir/wepppy` (container path `/workdir/wepppy`); remain on
the current branch. Starting revision is `97800607c30c0979d422f99b1e2c65f1b8a89ab5`.
Preserve unrelated dirty quality reports. Read root AGENTS and nearest guides
for NoDb, the module, tests, RQ and UI before touching those areas.

The module is `wepppy/nodb/mods/postfire_debris_flow/`. `staley2017.py` is the
verified scalar engine. `soil_thickness.py` derives offline component/map-unit
diagnostics; its defaults stay reproducible. `integration.py` prepares M1
predictors; `m1_inputs.py` validates rasters; `production.py` inventories inputs
and has `execute_model` and the scaffold `execute_m3`. `publication.py` installs
accepted outputs. `rainfall.py`, `rainfall_io.py` and `results.py` already deliver
event/design/inverse results for M1. The facade is `postfire_debris_flow.py`;
RQ functions are in `wepppy/rq/postfire_debris_flow_rq.py`.

WBT owns `D8UpstreamRelief` and `StaleySlopeSbs` in `/workdir/weppcloud-wbt`.
Read module `docs/m3_terrain.md` and `docs/slope_sbs.md` for the accepted formulas,
routing, raw DEM, strict neighborhoods and native-output interfaces. Do not
replace them with Python terrain algorithms or copy GPL pfdf implementation.

Soils stores raw component/horizon tables in project SQLite caches; map units
identify mapped soil associations, while components are unlocated proportions
within each map unit. `wepppy/soils/ssurgo/ssurgo.py` builds WEPP-compatible
profiles; `wepppy/nodb/core/soils.py` owns source mappings and cache lifecycle.
Both are protected from behavioral changes. The original STATSGO THICK raster
is a separate historical dataset, not the project's STATSGO soil-build cache.

## Plan of Work


### Milestone 1: Source evidence and accepted contract


Read module `docs/production_m3.md`, `docs/ssurgo_validity_assessment.md`, the
specification, ADR-0053/0066 and this package's contract decision and regression
plan. Audit `/wc1/runs/ad/addicted-reservist/` read-only: configured DEM/grid,
Soils completion, original MUKEY raster and substitutions, raw cache schemas and
committed contents, and available original THICK asset. This is the large 10 m
development basin previously used for browser tests; do not assume inventory or
credentials remain unchanged. Do not rebuild its soils or mutate shared caches.

Use frozen soil fixtures under `tests/nodb/mods/fixtures/postfire_debris_flow_soils/`
and authentic cached horizons to compare WEPP-valid and depth-valid sets. Record
reasons, material classes, duplicate/paired intervals, gap/overlap, component
weights and source contributions. NRCS depth endpoints are representative cm;
paired horizons can legitimately have identical endpoints. Thickness must count
physical depth once, but arbitrary overlapping records need not be legitimate
pairs. Evaluate explicit identification rules rather than accepting all overlap.
Totals above 100 can occur in source data; distinguish that case from invalid
individual percentages. Assess weathered material with authoritative NRCS
documentation and acknowledge the original THICK aggregation's material limits.

Propose exact material, component weighting and fallback rules with hand-worked
examples and real-fixture effects. Start with existing strict policy plus bounded
source-backed corrections; do not silently change offline defaults. Candidate
production fallback selects usable SSURGO per cell, then original THICK. A
component's missing percentage is not a located hole; keep component completeness
separate from binary spatial Valid coverage. Compare this candidate to existing
fractional-component-weighted offline means and record which method is chosen.

Inventory THICK delivery before proposing acquisition. If prepared inputs cannot
support execution, define a bounded existing-source acquisition path and obtain
authority for that delta; no implicit rebuilding/refresh or invented service.
Specify stable SQLite snapshots including WAL, resampling, source/policy hashes,
artifact schemas, resource limits and errors. Preflight must remain cheap and
read-only. Legitimate missing records can trigger documented fallback; malformed
files, unsafe paths and operational errors must retain their explicit failures.

Complete S05–S09 in `artifacts/20260914_contract_decision.md`, amend affected
canonical docs and record the soil parameterization ADR. Owner has already
accepted support/isolation; do not ask again for those. Obtain resolution of
remaining scientific/acquisition choices, two independent read-only contract
reviews and their disposition. Commit a standalone approved checkpoint before
code under `docs/standards/contract-first-change-standard.md`; if commit authority
is absent, prepare the concrete checkpoint before asking. This milestone ends
with exact numerical/runtime rules and the soil nonregression evidence plan.

### Milestone 2: Isolated soil preparation


Implement preparation as one project-parameterized path: derive unique original
MUKEYs inside the watershed mask and the THICK native window from the DEM
extent. Never hard-code development-run keys, bounds or run IDs. Preserve the
bounded acquisition gate and prepared-local runtime boundary; no additional
service or queue is implied. Exercise this path on at least two independent
basins with distinct keys/extents, including primary/fallback/missing cases.

Implement module-owned M3 input/soil composition, using existing raw helpers
with an explicit versioned production policy. Never instantiate WEPP soil
builders to validate horizons or mutate shared caches. Preserve offline v1
defaults. Use authentic original key provenance, component percentages and
source versions. Publish thickness in cm, source identity/fallback map,
component/map-unit audit tables and residual missing-data reasons to visible
attempt directories. Retain input snapshots/subsets sufficient to reproduce
the calculation, with hashes and attribution.

Follow `artifacts/soil_regression_plan.md` before/after: unchanged existing
SSURGO and STATSGO build outputs, selected components, substitutions, `.sol`
files and propagated `wepp/runs/*` soil inputs on isolated projects. Prove
M3 success/failure/retry does not write upstream files. Include actual SQLite
WAL and concurrent-change tests. A shared soil repair is outside this scope;
stop at the affected boundary if evidence requires one. This milestone ends
with usable M3 thickness and demonstrable upstream noninterference.

### Milestone 3: Terrain and analysis support


Invoke installed owned `D8UpstreamRelief` and validate configured 10 m
`ned13/2022`, actual aligned grids, authoritative watershed and outlet. Use
the full contributing-area relief and area for T. Do not feed conditioned WBT
relief or a local surface roughness substitute into the model.

M1 common support is watershed AND determined slope/SBS intersection AND valid
normalized dNBR AND valid K. Preserve raw WBT three-state outputs; intersect
their determined support with the other inputs. Compute T/F/S over the same
support. M3 common support is watershed AND valid SBS AND usable thickness;
compute burned fraction and mean thickness/254 there, retaining full-basin T.
Valid unburned cells are included; missing values never become zeros. Full
watershed area still drives size warnings. Zero support is unavailable; no
arbitrary coverage cutoff. Independently verify complete-support M1 parity and
new partial-support estimates, including disjoint per-input valid regions.

Publish UInt8 `valid_mask.tif`: 1 used, 0 excluded inside, 255 outside NoData;
record counts, unrounded fraction, grid and policy version. Use existing owned
native raster primitives and bounded operations. Benchmark actual large-10 m
execution; retain resource evidence and respect existing 96 MiB predictor
artifact admission rather than silently altering limits. If a native extension
is needed, scope it to measured missing capability and follow its repo guidance.
This milestone ends with reproducible predictors and exact inspectable masks.

### Milestone 4: Runtime completion and user-facing coverage


Connect M3 preparation to its existing task and shared rainfall/results engine;
remove `integration_pending` only when it really evaluates M3. Keep 15/30/60
minutes, 1/2/5/10-year CLI or available NOAA, project event rows and 50% inverse
target. Unsupported rainfall ranks retain unavailable rows per ADR-0062.
No coefficients, model selection transport or rainfall algorithm redesign.

Extend model-specific source freshness, readiness and reuse identity to actual
terrain/thickness/support dependencies. Sources changed during execution cannot
publish stale results. Preserve current state/admission/NoDb lock order and
immutable attempt identities; release mutation locks during scientific work.
M3 ignores dNBR/K, M1 has no independent Soils prerequisite. Publish latest
accepted files directly under `postfire_debris_flow/`; retain visible attempts,
failures, logs and intermediate/source artifacts. No hidden staging records.

Use established summary-table/link patterns for Valid coverage, counts, meaning
and mask download. Keep linked job IDs and Status/Details across reload; theme
and SI/English behavior follow existing conventions. Preserve accepted results
after failed replacement and legacy coverage-not-recorded behavior. Preflight 🌋
tracks the latest accepted result, not the current radio choice. This milestone
ends with actual M1/M3 RQ publication and correct browser readback.

### Milestone 5: Acceptance and closure


Exercise real development browser/RQ workflows with production-equivalent user,
group, mounts and installed binary. Record jobs, output identities and masks;
verify event/design/inverse numbers independently. Use isolated copies for
fault injection and builder comparisons. Prove ordinary browse/download and
archive/restore include intermediate and failed records. Run focused then full
gates; perform independent correctness/UX, QA and dedicated security review,
closing medium/high findings. Update specification, detailed docs, README,
roadmap, tracker and PROJECT_TRACKER with actual evidence. Archive this plan
only after both models genuinely execute and soil regression evidence passes.

## Concrete Steps


From `/home/workdir/wepppy`, start with `git status --short` and the milestone-1
read-only inventory. Retain compact source/policy comparison artifacts, not raw
unbounded database dumps. For implementation validation run:

    wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_*.py --maxfail=1
    wctl run-pytest tests/soils tests/nodb/test_soils_ssurgo_cache.py --maxfail=1
    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl check-rq-graph
    wctl run-preflight-tests

Run RQ/API focused tests discovered for the changed paths. Update the RQ catalog
and regenerate its graph only if wiring changes. Run stubtest/check-test-stubs
for public API changes, broad exception enforcement and scoped doc lint. Record
exact commands/counts and failures in `artifacts/validation.md`; do not copy
prior package pass counts as evidence. Validate live job trees through
`wepppy/rq/job_info.py` when queue execution changes.

## Validation and Acceptance


Construct absent, empty, populated, supported legacy and malformed/hostile
states separately from model/source options. Cover missing raw caches, valid
custom WEPP soils, original versus donor keys, missing/invalid thickness and
paired horizons, component weights, fallback, zero/disjoint masks, WBT failures,
active source changes, repeated jobs, switching model while running, failed
replacement and reload. Each changed filesystem/persistence boundary needs an
unmocked test. Security containment must also allow ordinary valid project files.

Accept only with complete-support M1 numerical parity, hand-checked partial
M1/M3 scalar results, unchanged ruggedness when only soil/SBS coverage changes,
actual large-project M3 results, and original soil-builder/generated-file parity.
Source contribution and component completeness must remain distinguishable from
spatial coverage. Confirm SI/English changes presentation only. A probability
bundle full of unexplained nulls or a successful no-op does not satisfy M3.

## Idempotence and Recovery


Use fresh visible attempt directories, preserve previous accepted results and
input snapshots, and obey existing publication ownership. Retry through ordinary
job submission without clearing another writer's locks. Rollback changes future
execution/policy; it never deletes or reinterprets prior results. Do not mutate
live soils to recover from missing M3 inputs. Source acquisition and production
deployment require their own explicit authorized boundaries.

## Artifacts and Notes


Existing scaffold artifacts: `soil_research.md`, `soil_regression_plan.md` and
`20260914_contract_decision.md`. Add source inventory, soil decision examples,
before/after soil parity, analytical/native output evidence, performance,
validation, correctness/QA and security reports here. Keep project records
inside visible `postfire_debris_flow/` paths. No publisher PDF redistribution.

## Interfaces and Dependencies


Use the existing PostfireDebrisFlow facade and M1/M3 task/response contracts.
Detailed production authority is module `docs/production_m3.md`; shared NoDb,
RQ, CSRF and artifact observability standards remain binding. Production policy
is explicitly versioned; existing offline APIs/defaults and accepted output
semantics remain reproducible. SQLite and owned native raster tools are existing
dependencies. No additional service, queue, datastore or parser is budgeted.

Revision note (2026-09-14): recorded the development inventory and dominant
legacy-H/source-delivery decision discovered while executing milestone 1.
Subsequent revision: record owner rejection and the researched recorded-depth
replacement, including corrected H evidence and explicit scientific limits.
Implementation revision: record checkpoint `89d673c38`, isolated soil/M1 helpers,
real SQLite review corrections and remaining production/live acceptance work.
Scope clarification: require reusable basin-derived source preparation and
multi-basin acceptance after the owner rejected a named-basin-only framing.
