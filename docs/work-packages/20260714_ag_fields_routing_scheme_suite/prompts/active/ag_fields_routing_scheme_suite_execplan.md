# Implement the AgFields routing scheme suite

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current
as work proceeds. Maintain this plan according to
`docs/prompt_templates/codex_exec_plans.md` from the WEPPpy repository root.

The package target is a faithful, wired implementation. A planner, fixture, or
surrogate that does not produce current generated watershed output is an
intermediate result and cannot close the package.

## Purpose / Big Picture

After this work, a user on the AgFields runs page can choose field-aware
hillslope routing, direct sub-field outlet injection, connectivity-aware mixed
routing, or Run All. The visible labels explain the physical behavior; users do
not have to interpret internal concept numbers. A selected scheme produces a
complete isolated watershed result under one fixed composable directory, and Run
All produces all three directories for direct comparison.

Concept 1 routes represented fields through downstream overland flow elements
(OFEs), which are consecutive sections of a one-dimensional WEPP hillslope. Concept
2 retains each independent sub-field run and injects its weighted PASS response at
the parent outlet. Hybrid uses Concept 2 only for sub-fields whose generated
Peridot flowpath boundary enters a channel directly and Concept 1 for the others.

The observable end state on
`/wc1/runs/sa/sacral-self-discipline` is:

    wepp/ag_fields/watershed/concept-1/
    wepp/ag_fields/watershed/concept-2/
    wepp/ag_fields/watershed/hybrid/

Each tree contains complete runs, output, manifests, closure evidence, and scoped
interchange resources. Baseline WEPP, independent AgFields, and the existing
unscoped Concept 2 tree remain byte-identical. Mariana Dobre receives the three
engineering results for a separate science evaluation.

## Progress

- [x] (2026-07-14 15:37 UTC) Scaffolded the work package, tracker, compatibility
  plan, security gate, active ExecPlan, and proposed ADR-0019.
- [x] (2026-07-14 15:37 UTC) Froze the scheme identifiers/slugs, exact
  description-first UI labels, Concept 2 compatibility default, Run All expansion,
  and fixed output roots.
- [x] (2026-07-14 15:37 UTC) Recorded the canonical Peridot hybrid classifier and
  prohibited double-counted or uniformly scaled whole-parent hybrid composition.
- [x] (2026-07-14 16:08 UTC) Passed scaffold documentation lint/link validation,
  heading extraction, spelling preview, whitespace checks, and the root AGENTS
  size gate.
- [x] (2026-07-14 17:01 UTC) Began end-to-end execution, reconciled all three
  repository worktrees, and isolated unrelated dirty Ash Transport, NASA report,
  and Peridot release-binary changes from this package.
- [x] (2026-07-14 19:08 UTC) Completed Milestone 1 engineering evidence: Peridot
  detail, the corrected full-project Concept 1/hybrid census, exact management
  preflight, residual geometry, and a real mixed-parent native WEPP/closure proof.
- [x] (2026-07-14 19:08 UTC) Recorded the package-level feasibility stop and exact
  evidence in ADR-0019. The ADR remains Proposed because 141 Concept 1 and 59
  hybrid residual parents exceed the native 20-scenario management limit.
- [x] (2026-07-14 19:08 UTC) Completed Milestone 2: added and release-tested the
  explicit-breakpoint wepppyo3 slope segmentation kernel and verified WEPPpy
  imports the Python 3.12 release artifact.
- [x] (2026-07-14 20:14 UTC) Expanded this package, at the decision owner's
  direction, to own the synchronized `wepp_hill` management-capacity increase and
  complete Concept 1/hybrid management-corpus validation.
- [ ] Milestone 2B: inventory every generated management section, select and
  accept an evidence-backed capacity, patch/rebuild forest, classify every corpus
  run failure, and vendor a matching binary family with zero invalid-producer or
  numerical-fault failures.
- [ ] Milestone 3: input synthesis and a native mixed-parent spike are complete;
  resume production Concept 1 execution, manifests, watershed rerun, and generated
  all-parent acceptance after Milestone 2B passes.
- [ ] Milestone 4: implement hybrid sub-field classification, residual parent
  sources, pure/mixed parent composition, and closure evidence.
- [ ] Milestone 5: migrate Concept 2 behind the scheme-root interface and add
  backward-compatible NoDb state, API, RQ, and Run All orchestration.
- [ ] Milestone 6: implement the four UI options and independent per-scheme
  status, limitations, stale, clear, and browse behavior.
- [ ] Milestone 7: pass focused/broad gates, security/QA review, and all-scheme
  generated acceptance; publish Mariana's comparison bundle.
- [ ] Move this plan to `prompts/completed/`, update the package/tracker/root board,
  and record outcomes only after all wired generated-output criteria pass.

## Surprises & Discoveries

- Observation: Direct channel drainage is present for only 3,269 of 6,626 retained
  dev-project sub-fields (49.3%).
  Evidence: The completed
  `docs/work-packages/20260713_ag_fields_flowpath_channel_connectivity/package.md`
  records 3,357 without direct channel drainage and identical results from the
  SUBWTA suffix-4 rule and `netful.tif`.
- Observation: The completed Concept 2 path is a substantial full-watershed job,
  not a lightweight report operation.
  Evidence: Its accepted dev run took 59 minutes 25 seconds and peaked at
  6,884,441,600 bytes. Run All must not start three such jobs concurrently.
- Observation: Current AgFields state, RQ job key, route, Stage 5 UI, and artifact
  root are singular and Concept 2-specific.
  Evidence: `wepppy/nodb/mods/ag_fields/ag_fields.py` stores
  `_watershed_integration_*`; `wepppy/rq/ag_fields_rq.py` exposes one
  `agfields_run_watershed`; and the fixed browse root is
  `wepp/ag_fields/watershed`.
- Observation: Existing WEPPpy MOFE raster assignment orders parent cells by
  `DISCHA` rank and assigns contiguous OFE bands from slope distance fractions.
  Evidence: `_build_mofe_map_labels_python_legacy` and `_build_mofe_map` in
  `wepppy/nodb/core/watershed_mixins.py` use `subwta`, `discha`, and
  `assign_mofe_map_with_wepppyo3`.
- Observation: The current Peridot connectivity library returns only aggregate
  counts even though it already accumulates connected sub-field identifiers.
  Evidence: `/workdir/peridot/src/subfield_channel_connectivity.rs` uses a
  `HashSet` of connected ids and returns `SubfieldChannelConnectivitySummary`.
  An additive deterministic detail output can reuse the exact classifier without
  a second topology implementation.
- Observation: A mixed hybrid cannot add connected sub-field sources to a complete
  Concept 1 parent without representing those areas twice.
  Evidence: The source-area identity requires a residual Concept 1 source whose
  area is `A_parent - sum(A_connected)`.
- Observation: The retained sub-field raster uses the finite NoData sentinel
  `-2147483648`, not only non-finite NoData values.
  Evidence: Normalizing all non-positive values to background removed a phantom
  source from exploratory census runs; the corrected final census has no missing
  or zero-overlap field sources.
- Observation: Geometry is not the implementation blocker. All 1,869 affected
  Concept 1 parents and all 1,644 hybrid residual parents can preserve every
  source with 1-20 OFEs and exact raster-area closure.
  Evidence:
  `artifacts/2026-07-14_concept1_feasibility.md` records the selected-plan
  distributions and zero missing-source/closure residuals.
- Observation: Exact management synthesis still exceeds the native WEPP
  `nmscen <= 20` limit for 141 Concept 1 parents and 59 hybrid residual parents
  after reference-safe structural scenario deduplication.
  Evidence: The failed parents cover 21,607,200 m2 (12.21%) and 9,273,600 m2
  (5.47%), respectively. The prior MOFE NSCEN work explicitly deferred binary
  limit augmentation to a separate work package.
- Observation: Generated management comments must follow the first three native
  header records; a leading comment causes WEPP `verchk` to reject an otherwise
  valid file.
  Evidence: Moving the synthesized description after the `98.4` version and two
  numeric records made the real parent 102 mixed fixture run successfully.
- Observation: The forest build already separates watershed and hillslope
  capacity. Watershed includes use 15,000, while the active `_hill` include family
  sets `mxplan`, `ntype`, and `ntype2` to 20 and `infile.for` validates `nmscen`
  directly against `ntype`.
  Evidence: `/workdir/wepp-forest_260430_baseline/src/makefile` selects
  `includes_hill/` for `_hill` objects; `src/infile.for` calls
  `readin(12,nmscen,1,ntype,...)`.
- Observation: The specified forest baseline is detached at `dac3c950` and
  contains unrelated dirty soil-layer cursor, ablation, change-log, watchlist, and
  binary work.
  Evidence: The initial status and hashes are recorded in
  `artifacts/2026-07-14_management_capacity_and_corpus_validation_plan.md`.
  This package must use isolated diagnostic builds and explicit staging so it
  does not overwrite or claim those changes.

Add new discoveries here with commands, paths, or concise test output. Do not
erase observations that changed the design.

## Decision Log

- Decision: Implement Concept 1, retain Concept 2, and add a hybrid that branches
  per sub-field using the canonical Peridot direct-channel classifier.
  Rationale: The connectivity result was lower than expected; all three results
  are needed to compare buffer-routing and independent-source tradeoffs.
  Date/Author: 2026-07-14, Roger Lew and Codex.
- Decision: Use API/NoDb identifiers `concept_1`, `concept_2`, and `hybrid`, mapped
  only through code to filesystem slugs `concept-1`, `concept-2`, and `hybrid`.
  `all` is request/UI-only.
  Rationale: Exact mapping makes state, paths, manifests, and user choices
  composable while preventing path text from becoming an input surface.
  Date/Author: 2026-07-14, Roger Lew and Codex.
- Decision: Use the exact description-first labels in `package.md`, with Concept 2
  as the initial/default selection and omitted API behavior.
  Rationale: Labels must explain physical routing, and old clients must continue to
  run the completed scheme.
  Date/Author: 2026-07-14, Roger Lew and Codex.
- Decision: Run All enqueues three independent jobs in Concept 1, Concept 2,
  hybrid order, linked by RQ dependencies that allow later execution after prior
  failure.
  Rationale: This preserves independent result/failure/retry state while bounding
  memory to one scheme at a time.
  Date/Author: 2026-07-14, Codex.
- Decision: A mixed hybrid uses a rerun residual Concept 1 source plus connected
  independent PASS sources. It does not inject on top of a full-area Concept 1
  source and does not uniformly scale a complete Concept 1 PASS after the fact.
  Rationale: The rejected alternatives double-count area or silently distort the
  geometry and nonlinear response.
  Date/Author: 2026-07-14, Roger Lew and Codex.
- Decision: Preserve the parent representative profile length in the first
  residual-geometry candidate, set width to `A_residual / parent_length`, exclude
  connected cells from OFE assignment statistics, and retain original normalized
  downslope positions for breakpoints.
  Rationale: A length-preserving rerun keeps downstream buffer distances explicit
  while generating WEPP output at the residual target area. Milestone 1 must prove
  this is parseable, closes area, and fits mixed layouts; if it fails, stop for an
  explicit ADR revision rather than switching geometry silently.
  Date/Author: 2026-07-14, Codex (Proposed under ADR-0019).
- Decision: Existing unscoped Concept 2 artifacts are immutable legacy evidence;
  new Concept 2 execution writes `concept-2`.
  Rationale: Automatic migration would create destructive ambiguity and is not
  needed for additive evolution.
  Date/Author: 2026-07-14, Roger Lew and Codex.
- Decision: Treat 1-20 OFEs, exact source representation, positive field overlap,
  contiguous breakpoints, and raster-area closure as engineering planner gates.
  Retain agreement, area error, fragmentation, source-order, and downstream-buffer
  metrics as visible diagnostics rather than inventing a science threshold before
  Mariana's evaluation.
  Rationale: The planner can preserve source/accounting identity across the dev
  project, while the wide fit distributions quantify the one-dimensional
  abstraction without silently rejecting scientifically unevaluated layouts.
  Date/Author: 2026-07-14, Codex (Proposed under ADR-0019).
- Decision: Use reference-safe management graph deduplication only as an explicit
  Concept 1 synthesis option; preserve the legacy synthesis default.
  Rationale: Reusing structurally equivalent scenarios reduces native counts
  without merging unlike rotations or changing established callers.
  Date/Author: 2026-07-14, Codex.
- Decision: Stop before scheme-aware UI/API/RQ production wiring.
  Rationale: 7.54% of Concept 1 parents and 3.59% of hybrid residual parents still
  exceed the native management ceiling. Dropping sources, merging unlike
  rotations, or silently substituting Concept 2 would violate the frozen faithful
  routing contract.
  Date/Author: 2026-07-14, Codex.
- Decision: Expand this work package to resolve the hillslope management capacity
  and validate the complete Concept 1/hybrid management corpus rather than opening
  a detached follow-up package.
  Rationale: The capacity and any invalid producer/numerical failures are exposed
  by the integrated field-aware management datasets and must pass before the
  routing implementations can be considered faithful or runnable.
  Date/Author: 2026-07-14, Roger Lew and Codex.
- Decision: Classify failures before selecting the patch boundary. Fix parser
  capacity in forest; fix objectively invalid source values at the earliest
  authoritative AgFields ingest boundary only when a canonical rule exists; route
  finite-input numerical failures through the forest observability/ablation
  protocol.
  Rationale: Broad clamping or fallback would hide provenance and can change
  science, while model-state guards require evidence that the producer—not the
  input—is invalid.
  Date/Author: 2026-07-14, Roger Lew and Codex.

## Outcomes & Retrospective

Milestones 1 and 2 established that the geometry, explicit-breakpoint slope
kernel, residual-area input construction, and ADR-0018 mixed-source balance are
implementable. Parent 102 provided a real mixed-parent native WEPP proof with
3,600 m2 residual area, 1,800 m2 connected area, 5,400 m2 combined area, and zero
water/sediment closure residual across 6,210 events.

The original feasibility stop is now an integrated implementation milestone, not
an external decision blocker. The package owns a complete management-corpus
inventory, synchronized hillslope binary capacity, data-contract validation, and
evidence-driven numerical hardening before user-facing behavior. Large planner
and corpus scratch outputs remain outside git; concise input-hashed evidence is in
`artifacts/2026-07-14_concept1_feasibility.md` and the capacity/corpus compatibility
contract is
`artifacts/2026-07-14_management_capacity_and_corpus_validation_plan.md`.
Concept 2 remains the implemented compatibility path until that new milestone and
the remaining wired acceptance pass.

## Context and Orientation

Work in `/home/workdir/wepppy` unless a step names `/workdir/peridot`,
`/home/workdir/wepppyo3`, or `/workdir/wepp-forest_260430_baseline`. Do not create
or switch branches. Inspect each repository status before edits and preserve
unrelated user changes. In WEPPpy, follow the nearest `AGENTS.md`: root rules
apply globally; `wepppy/nodb/AGENTS.md` applies to NoDb;
`wepppy/weppcloud/AGENTS.md` applies to UI/routes; and `tests/AGENTS.md` applies to
tests.

The forest worktree builds the legacy Fortran model engine. Its `_hill` executable
runs Concept 1/hybrid replacement hillslopes. The active hill build includes set
`mxplan`, `ntype`, and `ntype2` to 20; `infile.for` uses `ntype` to validate the
management yearly-scenario count. The same constants size other management and
OFE arrays, so they must be changed as one synchronized capacity contract after a
complete corpus inventory. Read forest root/source `AGENTS.md`, its ablation
protocol, and
`artifacts/2026-07-14_management_capacity_and_corpus_validation_plan.md` before
editing or building. The specified forest worktree begins detached and dirty;
perform diagnostic builds in an isolated copy until its unrelated source/binary
state can be preserved explicitly.

AgFields first rasterizes field boundaries and retains field/hillslope
intersections. Peridot writes a sub-field id raster, representative slope files,
and `fields.parquet`. Stage 4 creates one independent WEPP run/output per retained
sub-field under `wepp/ag_fields/runs` and `wepp/ag_fields/output`.

Concept 2 is implemented in
`wepppy/nodb/mods/ag_fields/watershed_integration.py`. For each parent, it scales
the baseline parent PASS to uncovered area, combines it with every retained
sub-field PASS using the accepted weighted combiner, stages exactly one parent
PASS, and reruns watershed WEPP in an isolated tree. ADR-0018 and
`docs/work-packages/20260713_ag_fields_concept2_watershed_integration/artifacts/pass_field_semantics.md`
are normative for all weighted PASS arithmetic. Do not change that kernel's
semantics as part of Concept 1.

A PASS file is WEPP's hillslope-to-watershed event interface. A parent watershed
run consumes exactly one PASS per parent hillslope. A hybrid therefore cannot send
two independent parent PASS files to watershed WEPP; it must first combine all
sources for that parent into one target-area PASS.

An OFE is a consecutive segment of one WEPP hillslope with its own soil and
management. WEPP routes water and sediment from an upslope OFE through downstream
OFEs. `wepppy/nodb/core/watershed_mixins.py` already segments representative slope
files and maps raster cells to OFE ids by parent `SUBWTA` and `DISCHA` rank.
`wepppy/wepp/soils/utils/multi_ofe.py` and
`wepppy/wepp/management/utils/multi_ofe.py` synthesize multi-OFE soil and
management inputs. `/home/workdir/wepppyo3/wepp_interchange/src/mofe.rs` now
provides the release-tested additive explicit-normalized-breakpoint API while
preserving its older target-length/buffer interface.

The canonical hybrid classifier is
`/workdir/peridot/src/subfield_channel_connectivity.rs`. It starts from every
positive retained sub-field raster cell, follows that cell's D8 successor, and
marks the sub-field connected when at least one first outside cell is a channel.
The CLI in `/workdir/peridot/src/bin/subfield_channel_connectivity.rs` accepts all
resources explicitly and currently returns summary JSON. Extend that
implementation; do not recreate D8/channel rules in Python.

The current facade in `wepppy/nodb/mods/ag_fields/ag_fields.py` persists one
watershed integration status. `wepppy/rq/ag_fields_rq.py` runs one job, and
`wepppy/microservices/rq_engine/ag_fields_routes.py` exposes authenticated
run/clear routes. The Stage 5 template and controller are
`wepppy/weppcloud/templates/controls/ag_fields_pure.htm` and
`wepppy/weppcloud/controllers_js/ag_fields.js`; the durable UI behavior is in
`wepppy/nodb/mods/ag_fields/ui_control_layout.md`.

The compatibility contract is
`docs/work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_scheme_artifact_compatibility_plan.md`.
Read it before every schema/state/path edit. The proposed parameterization decision
is `docs/adrs/ADR-0019-agfields-field-aware-ofe-hybrid-routing.md`. It must be
accepted with exact parameters before user-facing routing is wired.

## Plan of Work

### Milestone 1: Prove connectivity detail, Concept 1 fit, and residual hybrid geometry

First make the classifier useful as a per-sub-field routing input. In
`/workdir/peridot/src/subfield_channel_connectivity.rs`, introduce a deterministic
detail row containing `subfield_id`, `channel_connected`, and
`direct_channel_outlet_cells`. Refactor the existing loop so one analysis returns
both the unchanged aggregate summary and detail rows sorted by integer sub-field
id. Preserve `summarize_subfield_channel_connectivity` as a compatibility wrapper.
In `/workdir/peridot/src/bin/subfield_channel_connectivity.rs`, add an optional
`--out-subfields-json <path>` argument. Keep the current schema-version-1 summary
JSON byte shape unchanged when the new option is absent. The detail file has its
own schema/version, definition, channel-detection provenance, inputs, and sorted
rows. Add tests for row counts, multiple outlet cells, unconnected ids, explicit
mask parity, deterministic order, and existing summary output.

In WEPPpy, create a small planner module under
`wepppy/nodb/mods/ag_fields/`, initially callable from focused tests/read-only
diagnostics without being wired to RQ. It must load aligned `SUBWTA`, `DISCHA`, the
retained sub-field id raster, fields metadata, parent translators, and the Peridot
detail result. Validate raster shape, geotransform, projection, unique cell
ownership, ids, and area before planning.

For each parent, sort its eligible raster cells by the same stable descending
`DISCHA` order used by `assign_mofe_map`; ties remain stable. A candidate Concept 1
plan is a set of contiguous rank bands and one source assignment per band. Score
the candidate using at least raster versus modeled source area, cell agreement,
field fragmentation, source-order conflicts, and downstream background/buffer
length. Generate stable reason codes for invalid ids, no cells, overlap, too many
OFEs, too many management scenarios, poor fit, and invalid geometry. Do not treat
uncovered or filtered cells as dropped; they are background.

The prototype must compare the simple one-to-four equal-band family with a
generalized candidate search bounded by the actual current slope and management
limits. It must not freeze numeric thresholds in code. Write the measured
distributions and proposed thresholds to a package artifact and then update
ADR-0019. Reuse the existing user-visible sub-field retention threshold instead of
adding another small-area filter.

For hybrid planning, remove channel-connected sub-field cells from the residual
assignment population. Preserve the parent representative profile length and
normalized slope positions, set residual width to
`A_residual / parent_profile_length`, and generate candidate OFE assignments from
the remaining non-connected/background cells. Prove three cases with short WEPP
fixtures: no connected sources (pure Concept 1), complete connected coverage
(pure Concept 2), and a mixed parent (residual Concept 1 plus at least one connected
PASS source). The mixed parent must close source area exactly before and after PASS
combination. If length-preserving residual geometry cannot create a parseable,
area-correct, scientifically legible source, record the evidence and stop for a
decision-owner ADR revision. Do not try an unrecorded fallback.

Run the planner read-only against `sacral-self-discipline`, keeping large raw
scratch data outside git and committing a concise
`artifacts/2026-07-14_concept1_feasibility.md`. Record parent/sub-field/area
eligibility, rejection-reason counts, error distributions, representative pure
and mixed parent ids, runtime, and peak memory. The milestone passes only if Roger
accepts exact parameters/rules in ADR-0019. If the evidence fails the faithful
target, update this plan/package as blocked by the design decision; do not wire a
surrogate UI mode.

### Milestone 2: Add explicit-breakpoint native slope segmentation

In `/home/workdir/wepppyo3/wepp_interchange/src/mofe.rs`, add an API that accepts a
validated sequence of normalized breakpoints beginning at zero and ending at one.
It must preserve the existing slope segmenter API and output. The new function
interpolates the original profile at each breakpoint, produces one OFE per
interval, retains the source total length/width unless the caller explicitly
passes an accepted target width, and fails on unsorted, duplicate, non-finite,
out-of-range, zero-length, or over-limit segments.

Expose the function through the existing PyO3 module with a stable name and typed
arguments. Add Rust and release-tree Python tests for one OFE, irregular
breakpoints, exact endpoint interpolation, area/length preservation, target width,
and every invalid boundary. Run existing MOFE and watershed-abstraction tests to
prove no regression. Build the canonical Python 3.12 release artifact using the
repository's established release process, record source commit and SHA-256, and
verify WEPPpy imports the rebuilt function rather than a stale binary.

Do not implement field assignment or scientific thresholds in wepppyo3. The
native API is a deterministic geometry operation; the accepted WEPPpy plan remains
the authority.

### Milestone 2B: Expand hillslope management capacity and validate the corpus

Create a reusable read-only management-corpus command under
`wepppy/nodb/mods/ag_fields/` that consumes the corrected Concept 1 or hybrid OFE
plan plus explicit baseline/sub-field management roots. It must build the same
reference-safe deduplicated graph used by execution and record, for every parent,
counts for every serialized management section, rotations, nested cutting/grazing
cycles, OFEs, source ids, plan hash, input hashes, parse result, and stable failure
classification. Separate graph construction from the current 20-scenario write
guard so the diagnostic can measure the true corpus without serializing an input
that the currently supported binary claims to accept. Keep all large generated
files outside git and commit a concise Parquet/JSON schema description,
distributions, maxima, representative boundary ids, and hashes.

Use that inventory to propose the smallest synchronized `_hill` capacity with
explicit headroom. The observed yearly-scenario maximum is currently 24, making
32 a reasonable candidate, but do not freeze it until every `ntype`, `ntype2`, and
`mxplan`-bounded management section is counted. Update ADR-0019 with the exact
accepted value and rationale before it changes WEPPpy generation or a vendored
binary. Increasing binary capacity does not increase the Concept 1 planner's
20-OFE contract.

In `/workdir/wepp-forest_260430_baseline`, preserve the unrelated detached dirty
state and first build/test an isolated copy. Add regression fixtures at 20, the
observed maximum, and one above the proposed limit. Change `mxplan`, `ntype`, and
`ntype2` together in `src/pmxpln_hill.inc`, `src/pntype_hill.inc`, and all tracked
hill include copies; keep watershed include values unchanged. Update the forest
README, change log, tests, and dated-release provenance. The old binary must
reproduce the `nmscen > 20` rejection, the candidate must parse/run the accepted
boundary fixtures, and both must reject a count beyond their declared capacity.

Generate complete slope, soil, climate, management, and run tuples for every
unique Concept 1 and hybrid residual parent and execute them with the candidate
`wepp_hill`. A successful row requires exit zero, the native completion marker, a
valid PASS header/body, and no parser/runtime, floating-point, non-finite, or
invalid-producer signature. Classify every failure as `capacity_or_parse`,
`invalid_input_contract`, `numerical_model_state`, or `environment_or_fixture`.

For `invalid_input_contract`, trace the value to its AgFields database/rotation
row and parser field. Add a validation error with exact row, value, unit, and rule
at the earliest authoritative ingest boundary. Normalize only if an existing
canonical contract already defines the unique transformation; otherwise fail
explicitly and record the required science decision. For
`numerical_model_state`, initialize a forest ablation incident, reproduce with
complete shared run context, enable `wepp_observe.on`, and test one guard or
upstream mutation per lane under `docs/ablation/protocol.md`. Do not hide a model
producer failure by clamping an input or disabling floating-point traps.

After the complete corpus passes, run all forest release gates, build matching
hillslope/watershed binaries, verify ELF interpreter and hashes, and vendor the
same release family into WEPPpy. Update
`ManagementMultipleOfeSynth.WEPP_HILLSLOPE_MAX_YEARLY_SCENARIOS` and its stub to
the accepted capacity only in the same cutover. Add regression tests proving
WEPPpy rejects one above the new limit and the vendored binary runs the accepted
maximum. Record the final binary source identity, dirty-base disposition, build
flags, hashes, corpus totals, failure/fix ledger, and protected-output comparisons
before marking Milestone 2B complete.

### Milestone 3: Implement faithful Concept 1 execution

Create `wepppy/nodb/mods/ag_fields/routing_schemes.py` with a string enum whose
only current values are `concept_1`, `concept_2`, and `hybrid`, plus a fixed
identifier-to-slug mapping. Parsing must be exact. No caller-provided slug or path
enters filesystem operations.

Create a Concept 1 collaborator under `wepppy/nodb/mods/ag_fields/` that consumes
the accepted planner artifact rather than recomputing assignments during input
synthesis. Keep the planner and executor separable so plan hashes and reason codes
are testable. A successful parent plan generates:

- an explicit-breakpoint MOFE slope at the target parent area;
- a multi-OFE soil through `SoilMultipleOfeSynth`, initially repeating the parent
  soil exactly as current AgFields does;
- one field management per assigned sub-field from the existing rotation schedule,
  plus the parent background management for background OFEs, combined through
  `ManagementMultipleOfeSynth`;
- consistent slope, soil, and management OFE counts and valid WEPP references; and
- a hillslope run whose PASS header area matches the parent target area.

Reject plans that exceed real slope/OFE or management scenario limits. Do not
truncate, merge, or rename sources after plan acceptance. Parse every generated
input before launching the full parent set and run short fixtures first.

Reuse the current Concept 2 workspace/watershed pattern only after identifying
behavior that is genuinely common. Extract shared staging, baseline parent
materialization, watershed runner, interchange, manifest writer, and protected
path helpers into a focused module if doing so reduces duplication without
changing Concept 2 results. Keep scheme-specific planning/source construction in
separate collaborators.

Concept 1 stages its replacement PASS for every eligible affected parent and the
unchanged/materialized baseline PASS for every untouched parent, then runs
watershed WEPP and scoped interchange below
`wepp/ag_fields/watershed/concept-1`. Persist `ofe_plan.parquet`,
`parent_routing.parquet`, complete source/version/signature provenance, and a
plain-language limitation README. Fail the scheme before publishing completed
state if any required parent or watershed artifact is missing.

Add focused tests for a single upslope field plus buffer, a field at the channel,
two ordered fields, side-by-side fields, fragmented fields, tied DISCHA ranks,
filtered fields/background, OFE/scenario limits, parse/run failures, stale inputs,
and protected-tree isolation. Expected failure fixtures assert stable reason codes
and no fallback scheme artifacts.

### Milestone 4: Implement hybrid composition and closure

Invoke the Peridot detail CLI from a server-derived resource set, validate its
version/input identity, join it to current `fields.parquet`, and write
`hybrid/manifest/subfield_routing.parquet`. Every retained id must join exactly
once. Missing, duplicate, or extra ids fail preflight. Do not reevaluate channel
connectivity in Python.

For each parent, dispatch one of three explicit compositions:

- With no connected retained sub-fields, run the complete Concept 1 parent at
  `A_parent` and stage its PASS directly.
- With connected sub-fields covering `A_parent`, use the Concept 2 weighted source
  composition with zero background/residual source.
- With both connected sources and residual area, generate the accepted
  length-preserving residual Concept 1 parent, run it at `A_residual`, and combine
  its PASS with connected independent sub-field PASS files using the ADR-0018
  weighted combiner to one target `A_parent` PASS.

The residual Concept 1 plan includes non-connected fields and uncovered
background only. Validate cell ownership and the identity
`A_residual + sum(A_connected) = A_parent` before WEPP. Validate climate/calendar
identity, source/header areas, and event/run water/sediment closure during the
weighted merge. Persist source rows, routing branch, classifier provenance,
residual geometry, plan fit, and closure budgets.

Do not post-scale a complete Concept 1 PASS, inject on top of complete Concept 1,
or fall back when the residual plan is ineligible. The scheme fails with its
parent/reason provenance and retains independently usable Concept 1/Concept 2
results from other jobs.

Add fixtures for zero/mixed/full connected coverage, multiple connected sources,
connected fields in upslope/downstream bands, non-connected fields with
background buffers, area overlap/gap, calendar mismatch, ineligible residual plan,
weighted serialization budgets, and source identity. Complete a short generated
hybrid watershed before orchestration/UI work.

### Milestone 5: Add scheme roots, persisted state, and serial RQ/API execution

Refactor `AgFields` additively. Preserve historical `_watershed_integration_*`
loading while introducing a three-key state mapping. Each entry carries status,
phase, stale, source signature, summary, error, fixed root/browse relative paths,
limitation, and current job id. Locks protect short state transitions only; native
and WEPP execution occurs outside NoDb locks. Update `ag_fields.pyi` and stub tests
with the exact public interface.

Change `run_watershed_integration` to require/parse one valid internal scheme when
called by new code, while retaining a compatibility entry point that defaults to
Concept 2 for old callers. Dispatch to the appropriate collaborator. Scheme source
signatures include the scheme/algorithm version, accepted ADR version, Peridot
classifier/resource identity where applicable, upstream task timestamps, Stage 4
signature, and relevant native binary hashes.

Make clear scheme-specific. Resolve only the fixed mapped root, reject symlinks,
block while relevant AgFields jobs are active, and clear only that state/root. An
explicit clear-all loops over the fixed current identifiers. It never removes
legacy unscoped Concept 2 files. Test clear-one, clear-all, interrupted clear,
concurrent run/clear, stale state, missing artifacts, historical payloads, and
cross-scheme preservation.

In `wepppy/rq/ag_fields_rq.py`, accept one exact scheme per worker invocation and
include it in status/log/result/failure payloads. Define scheme-specific job keys,
while retaining the historical Concept 2 key as a readable compatibility alias if
needed by old state. In `ag_fields_routes.py`, parse request `scheme` as
`concept_1`, `concept_2`, `hybrid`, or `all`; omission/empty means `concept_2`.
Reject all other values with the canonical 400 response before enqueue.

For one scheme, enqueue one job and return existing `job_id` plus an additive
`job_ids` mapping. For `all`, enqueue Concept 1 first, Concept 2 dependent on the
first with `allow_failure=True`, and hybrid dependent on Concept 2 with
`allow_failure=True`. This permits all comparisons even if an earlier scheme
fails, while preventing simultaneous full-watershed memory peaks. Store every job
id and expose every active/terminal state. Preserve the existing per-run
single-flight rules for other AgFields mutations.

Update authenticated run/clear route tests, RQ job tests, state snapshot tests,
OpenAPI/agent API contracts, `wepppy/rq/job-dependencies-catalog.md`, and the
generated dependency graph. Run `wctl check-rq-graph`; regenerate only with the
canonical tool when drift is expected. Manually inspect a real Run All job chain
through `wepppy/rq/job_info.py` or the dashboard.

### Milestone 6: Implement description-first UI and independent results

Update `wepppy/nodb/mods/ag_fields/ui_control_layout.md` first with the as-built
request/state behavior. In `ag_fields_pure.htm`, add a single radio group or select
with exactly these complete visible options:

- Field-aware hillslope routing (routes fields through downstream OFEs)
- Direct sub-field outlet injection (preserves independent sub-field results; no
  buffer routing)
- Connectivity-aware mixed routing (injects channel-connected fields; routes
  other fields through OFEs)
- Run all routing schemes (writes three separate results for comparison)

Use stable DOM ids/data attributes and native labels. The internal values are
`concept_1`, `concept_2`, `hybrid`, and `all`; default to `concept_2`. Do not show
the concepts as bare labels. Keep shared readiness gates and make limitations
specific to each scheme.

Update `controllers_js/ag_fields.js` to send the selected value, hydrate legacy
state as Concept 2, track all returned job ids, and render each scheme's status,
staleness, error, clear action, and fixed browse link independently. Run All shows
three entries and partial completion/failure rather than one generic result.
Clearing a scheme asks for a second click and sends its exact identifier. Clear All
must be explicit and must state that three current result trees are removed while
legacy/baseline/independent outputs are retained.

Add Jest and pure-template tests that assert the full visible labels, default,
payloads, one/all job tracking, partial failure, result roots, limitations,
independent clear, stale behavior, and legacy hydration. Rebuild generated assets
through the repository's canonical frontend workflow. Run frontend lint and the
focused/full Jest gates.

Update the AgFields README, authoritative usersum design, API docs, manifest
READMEs, and any output-scope documentation actually touched. Do not add navigation
entries. If standard reports become scheme-aware, update
`docs/schemas/output-scope-contract.md` and every consumer/test in the same change;
otherwise state that results remain browse/evaluation-only.

### Milestone 7: Review, generated acceptance, and closeout

Complete focused tests as each milestone lands, then run the broad gates in
`Concrete Steps`. Update the high-security artifact with actual changed files,
commit context, findings, evidence, and sign-off. Resolve every medium/high
finding. Run changed-file code-quality/broad-exception observability and disposition
any real regression without rewriting unrelated files.

Before the dev run, inventory the protected trees specified in the compatibility
plan. Exercise Concept 1 alone, Concept 2 alone, hybrid alone, clear/retry, and Run
All through authenticated rq-engine/UI paths. Record job ids/order/status, elapsed
time, peak unique memory, disk usage, source/area/event/run closure, parent routing
counts, fit errors/reasons, required interchange resources, and protected-tree
hashes. Concept 2 current results must match the completed implementation within
ADR-0018 serialization budgets, not necessarily byte-for-byte if fixed path/version
metadata changes.

Publish a comparison bundle inside the current scheme manifest space or another
explicit additive comparison directory agreed in the compatibility plan. It must
not create `watershed/all/` or write into protected trees. Explain each scheme,
classifier, fit/rejection coverage, closures, and limitations. Engineering
acceptance does not label one scheme scientifically superior.

After every gate passes, update `package.md`, `tracker.md`, this plan, ADR-0019,
the security review, and `PROJECT_TRACKER.md`. Move this plan from `prompts/active`
to `prompts/completed` with outcomes, set the root AGENTS active plan to `none`, and
record Mariana's evaluation as pending or linked rather than fabricating it.

## Concrete Steps

Start each work session by inspecting all four repositories and rereading local
instructions:

    cd /home/workdir/wepppy
    git status --short --branch
    cat AGENTS.md
    cat wepppy/nodb/AGENTS.md
    cat wepppy/weppcloud/AGENTS.md
    cat tests/AGENTS.md
    cd /workdir/peridot && git status --short --branch
    cd /home/workdir/wepppyo3 && git status --short --branch
    cd /workdir/wepp-forest_260430_baseline
    git status --short --branch
    cat AGENTS.md
    cat src/AGENTS.md
    cat docs/ablation/protocol.md

For the management-capacity milestone, regenerate the corrected Concept 1 and
hybrid plans, then run the reusable corpus command with explicit resources. The
implemented command may add output-format options, but it must retain these
server-independent required inputs:

    cd /home/workdir/wepppy
    python3 -m wepppy.nodb.mods.ag_fields.management_corpus \
      --ofe-plan /tmp/agfields-concept1-census-v8/ofe_plan.parquet \
      --parent-runs /wc1/runs/sa/sacral-self-discipline/wepp/runs \
      --subfield-runs /wc1/runs/sa/sacral-self-discipline/wepp/ag_fields/runs \
      --output-dir /tmp/agfields-concept1-management-corpus
    python3 -m wepppy.nodb.mods.ag_fields.management_corpus \
      --ofe-plan /tmp/agfields-hybrid-census-v8/ofe_plan.parquet \
      --parent-runs /wc1/runs/sa/sacral-self-discipline/wepp/runs \
      --subfield-runs /wc1/runs/sa/sacral-self-discipline/wepp/ag_fields/runs \
      --output-dir /tmp/agfields-hybrid-management-corpus

Do not build over the initial dirty forest binaries during diagnosis. Make an
isolated copy that preserves the exact source state, apply only the candidate hill
include delta there, and use the forest-native build commands. Once the source
boundary and ownership are explicit, repeat the accepted patch and release in the
canonical worktree:

    cd /workdir/wepp-forest_260430_baseline/src
    make clean
    make wepp
    make wepp_hill
    cd ..
    tools/smoke_wepp_binary_host.sh src/wepp
    tools/smoke_wepp_binary_host.sh src/wepp_hill
    python tools/run_hillslope_watchlist.py --binary src/wepp_hill
    python tools/check_ablation_artifact_policy.py
    pytest

Run the complete AgFields corpus with an explicit candidate binary and write one
machine-readable result row per parent. Keep native stdout/stderr for failures and
representative boundaries, and scan every log for parser/runtime, floating-point,
non-finite, and invalid-producer signatures. A numerical failure must create or
update a forest ablation incident before any behavioral source edit.

For Peridot detail work, use its repository-native commands after reading its
`AGENTS.md` or contributor guidance. At minimum run formatting, the focused
connectivity tests, and the full debug suite. Record exact commands/results here
when discovered; do not guess a release invocation.

For targeted WEPPpy iteration from `/home/workdir/wepppy`, use:

    wctl run-pytest tests/nodb/mods/test_ag_fields_watershed_integration.py
    wctl run-pytest tests/rq/test_ag_fields_rq.py
    wctl run-pytest tests/microservices/test_rq_engine_ag_fields_routes.py
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py

Find the exact current filenames with `rg --files tests | rg 'ag_fields'` before
adding new targets. Add focused planner, Concept 1, hybrid, routing-scheme, legacy
state, path-clear, route, and RQ tests next to existing coverage rather than
creating an unrelated test hierarchy.

For frontend iteration:

    wctl run-npm lint
    wctl run-npm test -- --runInBand

If the wrapper's Jest pass-through differs, inspect `wctl/` and existing package
tracker commands, then record the working command here. Regenerate controller
assets only through the canonical build command documented by the nearest
frontend AGENTS file.

For queue/API/stub gates:

    wctl check-rq-graph
    wctl run-stubtest wepppy.nodb.mods.ag_fields
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

For broad WEPPpy acceptance:

    wctl run-pytest tests --maxfail=1
    python3 tools/code_quality_observability.py --base-ref origin/master

For every changed Markdown file, use the docs-maintainer workflow:

    wctl doc-lint --path <changed-file>
    markdown-extract --all '.*' <changed-file>
    diff -u <changed-file> <(uk2us <changed-file>)

The spelling command is preview-only unless a deliberate normalized edit is made
with `apply_patch` or `markdown-edit`. Do not rewrite unrelated prose mechanically.

Before and after dev-project execution, use or extend the completed Concept 2
inventory tool in
`docs/work-packages/20260713_ag_fields_concept2_watershed_integration/artifacts/capture_authoritative_inventory.py`.
The new compatibility artifact defines the protected roots. Write evidence under
the new package/scheme manifests and compare the inventories for zero protected
changes.

Exercise authenticated RQ routes using the rq-agent operator workflow if an
implementation session invokes live orchestration. Submit one scheme at a time
first, then `all`; poll every returned job id and inspect the dependency chain.
Record exact JSON requests/responses, job ids, and terminal states in the tracker
without exposing tokens.

## Validation and Acceptance

Milestone 1 is accepted when the existing Peridot summary output remains
compatible; every retained dev-project id has one deterministic detail row; the
Concept 1 census reports parent/sub-field/area eligibility and stable rejection
reasons; a mixed residual fixture produces a valid WEPP run and exact area closure;
and ADR-0019 contains owner-accepted numeric rules. A large amount of planner code
without those observations is not acceptance.

Milestone 2 is accepted when old and new wepppyo3 APIs pass tests, the explicit
breakpoint output reparses with expected OFE endpoints and area, invalid inputs
fail explicitly, and WEPPpy imports the current release hash.

Milestone 2B is accepted when the complete Concept 1 and hybrid management section
inventory supports an exact synchronized hill capacity in Accepted ADR-0019; the
current binary reproduces the old boundary; the rebuilt candidate runs every
required parent with valid PASS output and no failure signatures; all input
corrections and numerical guards have their required provenance/ablation evidence;
legacy boundary fixtures and forest release gates pass; and the matching binary
family plus WEPPpy generation guard are vendored and exercised together.

Concept 1 is accepted when synthetic physical layouts produce the expected OFE
source order, every generated slope/soil/management triple agrees on OFE count,
short and full hillslope runs parse, exactly one PASS is staged per parent, the
isolated watershed/interchange completes, plan/source areas close, and ineligible
layouts fail with no fallback artifacts.

Hybrid is accepted when each sub-field branch exactly matches Peridot detail,
pure/mixed/full-connected parents follow their specified composition, every mixed
parent satisfies the source-area identity, weighted event/run water and sediment
stay within ADR-0018 budgets, and a rejected residual plan cannot silently become
Concept 2.

Orchestration is accepted when omitted scheme runs Concept 2; exact one-scheme
requests alter only one scheme; invalid values enqueue nothing; Run All returns
three job ids in stable serial order and later jobs run after a prior failure;
per-scheme status/retry/clear/stale behavior is independent; queue graph/contracts
pass; and no path operation can touch a sibling, legacy, baseline, or independent
tree.

UI is accepted when a human can load the runs page, read the four full descriptive
labels, observe Concept 2 selected by default, run one or all, see separate status
and result links, and clear one without affecting the others. Jest/template tests
must assert the complete labels and paths, not only element existence.

The package is accepted only when all three current scheme trees are generated on
`sacral-self-discipline` through authenticated paths, required artifacts and
interchange resources exist, protected inventories are byte-identical, broad
tests/lint/stubs/graph/docs gates pass, the security review passes with no open
medium/high findings, and the comparison bundle is ready for Mariana. Her
scientific conclusion may remain pending; engineering cannot claim it.

## Idempotence and Recovery

Planner analysis is read-only with caller-selected output paths and can be repeated
without changing the run. Peridot detail output uses atomic replacement or a
temporary path followed by rename so a failed write does not masquerade as a
complete classifier result.

Each scheme runs in its own fixed root and stages attempts before terminal publish.
Rerunning a scheme either replaces only that current scheme atomically or preserves
the last completed attempt with explicit new failure provenance, as finalized in
the compatibility contract. It never changes a sibling or legacy result.

If Run All partially fails, retain successful scheme results and independent job
states. Correct the failed scheme and rerun only it; do not clear successful
siblings. Dependency `allow_failure` permits later jobs but does not convert the
failed job to success.

If NoDb state and filesystem artifacts disagree, report stale/failed with the
missing required artifact. Do not reconstruct a completed state from partial files.
Historical singular state remains readable; do not destructively rewrite it on
load.

If an explicit-breakpoint or Peridot release is built but WEPPpy imports an older
binary, stop, compare module paths/version/hash, and fix the canonical release
installation. Do not add a Python fallback that masks the missing owned native
dependency.

The management corpus command is read-only with respect to source runs and writes
only to its caller-selected output directory. It must use staged/atomic manifests
so an interrupted execution cannot be mistaken for a complete corpus. Forest
diagnostic builds start in an isolated copy because the designated baseline is
detached and dirty; do not clean, rebuild, stage, or overwrite its existing
source/release binaries until the package has recorded which dirty changes are
being retained in the candidate base.

If Concept 1 or residual hybrid geometry fails the Milestone 1 gate, preserve the
evidence, keep ADR-0019 Proposed, mark the package decision-blocked, and ask Roger
for the next design choice. Do not ship a surrogate under the promised label.

Never use destructive git resets or rewrite unrelated dirty files. Restore or
remove only artifacts created by this package and only through fixed, verified
paths.

## Artifacts and Notes

The package begins from these evidence points:

    Connectivity: 3,269 / 6,626 connected (49.3%)
    Not connected: 3,357 / 6,626 (50.7%)
    Direct channel outlet cells: 12,365
    Concept 2 parent count: 3,543
    Concept 2 affected parents: 1,869
    Concept 2 peak unique allocation: 6,884,441,600 bytes

The target route/directory expansion is:

    concept_1 -> wepp/ag_fields/watershed/concept-1
    concept_2 -> wepp/ag_fields/watershed/concept-2
    hybrid    -> wepp/ag_fields/watershed/hybrid
    all       -> enqueue the three mappings above; no all directory

The mixed-parent source identity is:

    A_residual = A_parent - sum(A_connected_i)
    A_target = A_residual + sum(A_connected_i) = A_parent

Add concise feasibility tables, test transcripts, release hashes, job ids,
resource counts, closure maxima, timing/memory, and protected inventory hashes as
work proceeds. Keep large generated Parquet/WEPP trees in their intended run
locations, not in git, unless the package explicitly approves a small fixture.

## Interfaces and Dependencies

In `/workdir/peridot/src/subfield_channel_connectivity.rs`, the additive analysis
must expose summary plus sorted detail without breaking the current summary
function. Names can follow repository style, but the semantic interface is:

    SubfieldChannelConnectivityDetail {
        subfield_id: i32,
        channel_connected: bool,
        direct_channel_outlet_cells: usize,
    }

    SubfieldChannelConnectivityAnalysis {
        summary: SubfieldChannelConnectivitySummary,
        subfields: Vec<SubfieldChannelConnectivityDetail>,
    }

The CLI keeps current required inputs and adds:

    --out-subfields-json <path>

The detail document has its own schema version and embeds classifier definition,
channel-detection source, input resource paths, and sorted rows. Existing summary
JSON remains compatible.

In `wepppy/nodb/mods/ag_fields/routing_schemes.py`, define one closed string enum
and one immutable slug map. Provide exact parsing for API/internal identifiers and
reject filesystem slugs as API values. This module is the only source for current
scheme iteration order.

The planner returns a typed/logically equivalent parent plan and writes the frozen
Parquet contracts. It consumes aligned raster/resource identities and explicit
connected-id membership; it does not query global run paths or recompute
connectivity. The executor consumes the plan/version/hash and refuses mismatched
inputs.

The wepppyo3 explicit-breakpoint API accepts source slope data/path, normalized
breakpoints, output path, and optional accepted target width. Preserve the old
segmenter signature. The new function fails rather than normalizing invalid
breakpoints or hiding a missing dependency.

The AgFields facade exposes scheme-aware run, clear, and state methods with typed
scheme arguments. Exact names must be reflected in `ag_fields.pyi`; retain old
Concept 2-compatible wrappers until tests and the compatibility plan explicitly
permit removal.

The rq-engine request field is `scheme`. The one-scheme response preserves
`job_id`; all responses may add `job_ids` keyed by machine identifier. Errors use
the canonical RQ response contract. Scheme job functions receive the machine
identifier, never a filesystem path.

Use only owned existing dependencies: Peridot for topology, wepppyo3 for native
slope/PASS operations, WEPPpy MOFE soil/management synthesis, RQ for serialized
jobs, `wepp-forest` for the model binary, and existing frontend/control patterns.
Do not introduce a new geospatial, raster, workflow, or UI dependency without the
repository dependency evaluation gates.

## Plan Revision Note

2026-07-14 15:37 UTC: Created this plan after the channel-connectivity inventory
motivated reopening Concept 1 and adding a per-sub-field hybrid. The initial
revision freezes user-visible/API/path contracts, makes residual hybrid geometry
the first feasibility gate, and requires faithful wired generated output rather
than a planner-only surrogate.

2026-07-14 17:01 UTC: Recorded the start of end-to-end execution and the unrelated
dirty worktrees that must remain isolated while milestones proceed.

2026-07-14 19:08 UTC: Completed the geometry census, exact management preflight,
explicit-breakpoint release, and mixed-parent native execution proof. Recorded a
package-level stop before production wiring because 141 Concept 1 and 59 hybrid
residual parents exceed the supported WEPP management scenario ceiling after
exact structural deduplication. ADR-0019 remains Proposed pending a binary-limit
work package or an explicit fidelity-contract revision.

2026-07-14 20:14 UTC: At Roger Lew's direction, expanded this package to own the
forest hillslope capacity increase and complete management-corpus validation.
Added a compatibility/regression plan that separates parser capacity, invalid
input contracts, numerical producer failures, and environment/fixture failures.
The former blocker is now Milestone 2B; UI/RQ wiring remains gated until the
rebuilt binary family runs the full Concept 1/hybrid corpus.
