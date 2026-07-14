# Implement AgFields Concept 2 watershed integration

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as
work proceeds.

Maintain this plan in accordance with
`docs/prompt_templates/codex_exec_plans.md`. Update this file and
`docs/work-packages/20260713_ag_fields_concept2_watershed_integration/tracker.md`
at every stopping point. When the package is complete, move this file from
`prompts/active/` to `prompts/completed/` and add the final outcome before closing
the package.

## Purpose / Big Picture

After this package, an AgFields user can take already-completed independent
sub-field simulations, route their area-weighted water and sediment contributions
through the parent watershed and channels, and inspect auditable accounting for
every source and event. The new operation appears as a separate AgFields workflow
stage and writes only under `wepp/ag_fields/watershed/`; baseline WEPP and existing
independent AgFields artifacts remain unchanged.

The visible proof is a successful run on
`/wc1/runs/sa/sacral-self-discipline`. It must produce exactly one combined or
unchanged parent PASS for every watershed hillslope, complete watershed WEPP,
generate isolated interchange resources, and emit source/event/full-run closure
artifacts. The implementation then produces an evaluation bundle for Mariana Dobre.
Mariana owns scientific evaluation of buffer effects and suitable use. Concept 1
is deferred and must not be built as part of this plan.

## Progress

- [x] (2026-07-13 19:37 UTC) Selected Concept 2, deferred Concept 1, assigned the
  scientific evaluation to Mariana, and designated `sacral-self-discipline` as the
  dev project.
- [x] (2026-07-13 19:37 UTC) Inspected current AgFields, Roads, PASS, RQ/API/UI,
  run-artifact, and native release contracts; created the work package, proposed
  ADR, compatibility plan, security review, and tracker entries.
- [x] (2026-07-13 21:02 UTC) Milestone 1: finalized
  `ag_fields_pass_semantics_v1`, derived quantity-specific closure budgets from
  legacy serialization, and accepted ADR-0018.
- [x] (2026-07-13 21:17 UTC) Milestone 2: implemented and release-tested the
  additive weighted native PASS combiner while preserving the Roads API; 39 Rust
  tests and the release-tree Python API test pass.
- [x] (2026-07-13 21:48 UTC) Milestone 3: implemented the additive AgFields watershed-integration facade and
  collaborator with isolated parent materialization, manifests, combination,
  watershed execution, and interchange.
- [x] (2026-07-13 21:48 UTC) Milestone 4: added the separate RQ/API/UI stage, state, invalidation, clear,
  browse, and dependency graph contracts.
- [x] (2026-07-13 22:46 UTC) Milestone 5: completed focused engineering, compatibility, documentation,
  security, and broad validation.
- [x] (2026-07-14 00:30 UTC) Milestone 6: executed `sacral-self-discipline`, proved existing artifacts are
  unchanged, and published the public evaluation bundle for Mariana. Her scientific
  disposition remains pending and is not an engineering acceptance gate.

## Surprises & Discoveries

- Observation: The dev project already provides a large, useful acceptance matrix:
  6,626 independent sub-field PASS files span 1,869 affected parent hillslopes out
  of 3,543 total parents.
  Evidence: `ag_fields/sub_fields/fields.parquet` and file inventories under the
  designated run.
- Observation: Retained field raster area is 113,774,400 m2 within 176,981,400 m2
  of affected parent area. No parent is overcovered; 482 affected parents are fully
  covered. Median affected-parent coverage is about 0.805.
  Evidence: Counts from aligned `dem/wbt/subwta.tif` at 900 m2 per pixel joined to
  `fields.parquet`.
- Observation: Peridot `length * width` closes to its recorded raster area within
  `5.9e-11` m2 per sub-field on the dev project, but the PASS header area can differ
  slightly and is the modeled area used by WEPP.
  Evidence: `fields.parquet` and the third header line of
  `wepp/ag_fields/output/H1.pass.dat`.
- Observation: The dev project's parent `wepp/output/` contains no
  `H*.pass.dat`, even though `Wepp.pass_family` is `legacy_ascii`, because
  `delete_after_interchange=true` removed those process files.
  Evidence: Only `wepp/output/interchange/H.pass.parquet` remains; 3,543 parent
  plot files show the completed parent hillslope inventory.
- Observation: The existing Roads combiner sums complete sources and has no
  per-source area weight. It also copies the base header and requires exact climate
  token strings after Roads normalizes them.
  Evidence: `/home/workdir/wepppyo3/wepp_interchange/src/hill_pass_combine.rs` and
  `wepppy/nodb/mods/roads/roads.py`.
- Observation: `gwbfv` and `gwdsv` lack units in the current Arrow schema, while
  several other PASS fields have metadata that must be checked against the WEPP
  writer before scaling.
  Evidence: `wepp/output/interchange/H.pass.parquet` schema and
  `/home/workdir/wepppyo3/wepp_interchange/src/hill_pass.rs`.
- Observation: WEPP's binary PASS contract and watershed consumer confirm that
  `gwbfv` and `gwdsv` are m3 volumes. The Arrow metadata also incorrectly labels
  `clot` as a flow rate and the remaining particle fractions as percentages.
  Evidence: `/home/workdir/wepp-forest/docs/contracts/hillslope-binary-pass-format.md`,
  `/home/workdir/wepp-forest/src/wshred.for`, and
  `/home/workdir/wepppyo3/wepp_interchange/src/schema.rs`.
- Observation: Fortran `E11.5` and `E10.5` serialize five significant digits in a
  `0.ddddd` mantissa, not six digits as initially inferred from C-style scientific
  notation.
  Evidence: Real legacy PASS rows such as `0.43200E+05`, WEPP `wshpas.f90` format
  declarations, and weighted writer/reparse tests.
- Observation: The as-built real-project raster preflight reproduces every package
  acceptance count exactly, and one real parent can be materialized in about one
  second with the selected binary.
  Evidence: Read-only `sacral-self-discipline` preflight returned 3,543 parents,
  1,869 affected parents, 6,626 sources, 113,774,400 m2 retained area, 482
  full-coverage parents, and zero overcoverage. Parent 747 materialized in 0.93 s.
- Observation: Parent 747 combines one background plus eight field sources across
  6,210 calendar rows with zero serialized area residual; its largest event
  runoff-volume budget ratio is 0.993884, below the accepted bound.
  Evidence: The release-tree weighted API rehearsal under
  `/tmp/agfields-watershed-rehearsal`.
- Observation: Real WEPP `tdep` is signed. The first full RQ attempt rejected a
  valid negative value from parent 86 even though `sedseg.for` emits signed
  deposition-profile totals and `wshred.for` accumulates them unchanged.
  Evidence: Failed job `1c6a2bfd-2629-4a66-a273-a94fac7d9aa0`, exact parent-86
  replay, and the producer/consumer Fortran sources.
- Observation: Real particle-flow component vectors can be finite/nonnegative
  without summing to exactly one. The second full RQ attempt found a parent-158
  source vector totaling 1.008624; `wshimp.for` consumes the emitted components
  without mandatory normalization.
  Evidence: Failed job `f9045f70-2f59-44e9-964d-a728da6755d6`, exact parent-158
  replay, and the producer/consumer Fortran sources.
- Observation: Exhaustive native replay of all 1,869 affected parents passed after
  those semantic corrections. The maximum event budget ratio was
  `0.9999999999305551`.
  Evidence: Release-tree sweep completed in 271 seconds before the final RQ retry.
- Observation: The final authenticated run completed in 59 minutes 25 seconds with
  peak observed unique allocation of 6,884,441,600 bytes. It produced 3,543 parent
  PASS files and every required interchange resource.
  Evidence: RQ job `2fc269a6-12f8-4d74-a876-0619b2ea3cf7`, integration summary,
  monitored allocation, and output inventories.
- Observation: Real completion exercised a state path not covered by the historical
  default test: summaries with upstream timestamps referenced missing facade imports
  for `RedisPrep` and `TaskEnum`. A one-line import correction plus exact regression
  restored the endpoint.
  Evidence: Initial post-completion HTTP 500, direct traceback, regression test, and
  subsequent public HTTPS state response `completed`, `stale=false`.
- Observation: Pre/post hashing proved all four protected source trees identical:
  97,734 files and 18,498,460,698 bytes with digest
  `198212dd58c9301b9d0b6bcd70c980e45b1c09b64374cc7db22dac8d28477426`.
  Evidence: Parquet inventories under the isolated manifest evaluation bundle.
- Observation: Making the run public exposed that the dev compose service mounted
  the CAP secret but did not pass the CAP base, asset, or site-key environment.
  Anonymous run-page requests therefore returned a CAPTCHA-configuration 500 after
  a clean service recreation.
  Evidence: Public HTTP response/error id, WEPPcloud traceback, compose comparison
  with production, exact compose regression, and final public HTTP 200 CAP gate.

## Decision Log

- Decision: Concept 2 is the only implementation track in this package; Concept 1
  OFE planning, synthesis, and comparison fixtures are deferred.
  Rationale: Concept 2 retains independent sub-field source simulations and their
  water/sediment accounting without quantizing a two-dimensional field mosaic.
  Date/Author: 2026-07-13 / Roger Lew and Codex
- Decision: Engineering acceptance proves area, water, sediment, serialization,
  orchestration, compatibility, and generated output. Mariana Dobre owns the
  scientific evaluation after delivery.
  Rationale: Buffer effects and suitable-use judgments are scientific questions;
  they must not be replaced by an unapproved engineering heuristic or require
  building Concept 1.
  Date/Author: 2026-07-13 / Roger Lew and Codex
- Decision: Preserve baseline `wepp/{runs,output}` and independent
  `wepp/ag_fields/{runs,output}` trees byte-for-byte. Materialize parent PASS files
  from current prepared inputs inside the isolated tree when cleaned baseline PASS
  files are absent.
  Rationale: The designated project has no retained parent PASS, and changing the
  parent's cleanup setting would mutate an authoritative workflow.
  Date/Author: 2026-07-13 / Codex
- Decision: Add a new weighted native API; do not add weights or new semantics to
  `combine_hillslope_pass_files`.
  Rationale: Roads depends on the current additive API. An additive function keeps
  its contract and regression surface stable.
  Date/Author: 2026-07-13 / Codex
- Decision: Concept 2 v1 uses legacy ASCII PASS end to end under the isolated tree.
  Rationale: Independent AgFields sources are legacy ASCII, the current writer and
  combiner operate on that family, and weighted HBP writing is not required for the
  selected delivery.
  Date/Author: 2026-07-13 / Codex
- Decision: Conserve volumes and per-class sediment masses directly; reconstruct
  depths and concentrations; sediment-mass-weight particle fractions; and derive
  peak rate/time by scaled triangular-hydrograph superposition.
  Rationale: These rules follow the WEPP producer and consumer units, preserve the
  quantities used by watershed routing, and leave no PASS numeric field with an
  implicit operation.
  Date/Author: 2026-07-13 / Codex
- Decision: Use value-specific half-ULP budgets from five-significant-digit
  `E11.5`/`E10.5` serialization, with product bounds for class mass and
  depth-volume identities.
  Rationale: A fixed percentage would be either too permissive for small values or
  too strict for large values and would not reflect the actual legacy writer.
  Date/Author: 2026-07-13 / Codex
- Decision: Preserve the existing Roads writer formatting and use the exact legacy
  five-significant-digit formatter only for the new weighted path.
  Rationale: The Roads public API and byte-level output behavior are outside this
  package's contract; the additive path can meet ADR-0018 without changing them.
  Date/Author: 2026-07-13 / Codex
- Decision: Keep Stage 5 completion in additive AgFields state; do not add or
  overload a global `TaskEnum`.
  Rationale: `run_ag_fields` remains the established Stage 4/preflight contract.
  Stage 5 is an internal experimental result with its own source signature,
  upstream timestamp snapshot, terminal summary, failure, and job id.
  Date/Author: 2026-07-13 / Codex
- Decision: Derive every represented area from paired cells in the exactly aligned
  parent and sub-field rasters; use neither geometry area nor modeled PASS area as
  the retained-area authority.
  Rationale: Common-grid cell ownership gives exact parent/source closure while the
  PASS header area remains the denominator used to derive each source scale.
  Date/Author: 2026-07-13 / Codex
- Decision: Treat `tdep` as a finite signed extensive term and preserve its sign;
  do not apply the nonnegative validation used for other mass/volume fields.
  Rationale: The WEPP producer creates signed deposition totals and the watershed
  consumer accumulates them unchanged. Rejecting negative values rejected valid
  source data.
  Date/Author: 2026-07-13 / Codex
- Decision: Preserve finite nonnegative particle-flow components without requiring
  their serialized vector to sum to one and without silent renormalization.
  Rationale: WEPP normalizes only some producer paths, while its consumer uses the
  emitted components unchanged. Component-wise sediment-mass weighting preserves
  the source shape contract.
  Date/Author: 2026-07-13 / Codex

## Outcomes & Retrospective

All six engineering milestones are complete. Every legacy PASS field has an
accepted rule; the canonical py312 release exports the additive weighted kernel;
the isolated collaborator materializes and combines a complete parent inventory;
and the fifth authenticated RQ/API/UI stage exposes run, clear, hydration, failure,
limitation, and browse behavior.

The final authenticated job completed the real 3,543-parent watershed. Its 10,169
source rows, 11,606,490 event rows, and 1,869 run rows have zero closure-budget
violations, with maximum event ratio `0.9999999999305551`. All required interchange
resources exist. Pre/post inventories prove the 97,734 protected source files are
byte-identical. The public evaluation bundle is ready for Mariana; her scientific
disposition remains pending, and Concept 1 remains deferred.

The public acceptance URL returns HTTP 200 with its CAPTCHA gate after aligning the
dev compose CAP environment with the production contract and adding an exact
configuration regression.

Validation passed 4,833 WEPPpy tests (60 skipped), 85 frontend suites/621 tests,
41 native Rust tests, two release-tree Python tests, and the applicable security,
docs, graph, stub, exception, vulture, and diff gates. The final native shared
object SHA-256 is
`5d8e1251d84aed97af358d4473413b089a001de000523fbcd41bf9ffba864db3`.

## Context and Orientation

AgFields is a run-scoped NoDb controller in
`wepppy/nodb/mods/ag_fields/ag_fields.py`. A NoDb controller persists project state
to a JSON-backed `.nodb` file and exposes a cached facade to routes and workers. The
current Stage 4 operation, `AgFields.run_wepp_ag_fields`, runs one WEPP hillslope per
row of `ag_fields/sub_fields/fields.parquet`. Every row has `field_id`, `topaz_id`,
parent `wepp_id`, unique `sub_field_id`, `area`, `length`, and `width`. Its PASS is
`wepp/ag_fields/output/H<sub_field_id>.pass.dat`.

A PASS file is WEPP's daily hillslope-to-watershed process input. Its first five
lines contain climate, simulation, modeled-area, and sediment-class metadata; each
remaining day is `EVENT`, `SUBEVENT`, or `NO EVENT`. Event rows carry water depth
and volume, peak runoff, detachment/deposition mass, sediment concentrations, class
terms, and groundwater terms. The parent watershed run consumes one PASS per parent
hillslope. Concept 2 replaces an affected parent's PASS with an area-weighted merge
of its background source and all retained sub-field sources.

For parent raster area `A_parent`, retained field raster areas `A_i`, and source
modeled areas `A_modeled_i`, the selected formulas are:

    A_background = A_parent - sum(A_i)
    baseline_scale = A_background / A_parent
    subfield_scale_i = A_i / A_modeled_i

Extensive quantities are quantities that grow with represented area, such as water
volume or sediment mass. Intensive quantities are depths, fluxes, concentrations,
or shape descriptors that must be reconstructed from combined extensive totals or
under an explicitly documented rule. The implementation must not multiply every
numeric column blindly.

The current native parser and unweighted Roads combiner live in the sibling owned
repository at `/home/workdir/wepppyo3/wepp_interchange/src/hill_pass.rs` and
`hill_pass_combine.rs`. The PyO3 binding is in `wepp_interchange/src/lib.rs`, and
the deployable Python package is
`/home/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/`. Roads calls
`combine_hillslope_pass_files` from
`wepppy/nodb/mods/roads/roads.py`; that API must remain unchanged.

Roads also supplies the WEPPpy orchestration precedent. It prepares isolated run
and output directories, stages a complete parent PASS set, calls
`make_watershed_omni_contrasts_run`, executes `run_watershed`, and regenerates
interchange resources. Reuse its patterns, but implement AgFields logic in a
dedicated collaborator and do not couple the two NoDb mods.

AgFields already has three RQ jobs in `wepppy/rq/ag_fields_rq.py`, authenticated
routes in `wepppy/microservices/rq_engine/ag_fields_routes.py`, a four-stage
runs-page template, `wepppy/weppcloud/controllers_js/ag_fields.js`, and state
hydration. The new operation is a fifth, separate stage after current Stage 4. It
uses the existing single-flight admission and status channel but gets its own job
key and terminal result.

Read before editing:

- root `AGENTS.md` and the nearest subsystem `AGENTS.md` files;
- `docs/adrs/ADR-0018-agfields-weighted-pass-accounting.md`;
- `artifacts/2026-07-13_run_artifact_compatibility_plan.md`;
- `docs/schemas/nodb-persistence-concurrency-contract.md`;
- `docs/schemas/rq-response-contract.md`;
- `wepppy/rq/job-dependencies-catalog.md`; and
- `/home/workdir/wepppyo3/AGENTS.md` plus its release provenance docs.

## Plan of Work

### Milestone 1: Settle every PASS transformation before coding it

Create
`docs/work-packages/20260713_ag_fields_concept2_watershed_integration/artifacts/pass_field_semantics.md`.
For every header and row field, record its WEPP name, unit, extensive/intensive or
shape classification, source evidence, transformation, zero-volume behavior, and
closure check. Ground the table against the WEPP writer/reader source, not only the
current Arrow descriptions. Resolve `gwbfv`, `gwdsv`, the five concentration/class
fields, `clot` through `sdot`, `oalpha`, `tcs`, and `peakro`.

Update ADR-0018 with the final table conclusions and a numeric tolerance derived
from legacy `E11.5` serialization and reparsing. Change its status to Accepted only
when no field remains unspecified. The tolerance is a parameterization decision;
do not invent or tune it inside tests. Milestone acceptance is an Accepted ADR and
a reviewed table that leaves no numeric PASS field with an implicit operation.

### Milestone 2: Add the weighted native kernel without changing Roads

In `/home/workdir/wepppyo3/wepp_interchange/src/hill_pass_combine.rs`, keep
`combine_hillslope_pass_files` behavior and tests intact. Add a separate internal
`combine_weighted_hillslope_pass_files` path with typed source metadata. Parse the
modeled area from header line 3, validate every source's represented area and
derived scale, validate simulation headers and day keys, and accept a caller-owned
output climate token after WEPPpy has proved climate identity.

The Python-facing API in `wepp_interchange/src/lib.rs` must be additive and named
`combine_weighted_hillslope_pass_files`. Its stable v1 shape is:

    combine_weighted_hillslope_pass_files(
        sources: list[tuple[source_id: str, pass_path: str, represented_area_m2: float]],
        out_pass: str,
        target_area_m2: float,
        output_climate_token: str,
        strategy: str = "ag_fields_v1",
    ) -> dict

The kernel derives each scale from represented area divided by the source PASS
header area. It writes target parent area to the output header, applies the approved
field transformations, writes the combined legacy PASS, reparses it, and returns
bounded diagnostics for one parent: source full-run totals, per-event weighted
input versus reparsed output totals and residuals, and full-run residuals. This
one-parent return keeps Python memory bounded; the collaborator writes each result
to Parquet before processing the next parent.

Reject empty sources, duplicate source ids, non-finite or negative areas, zero
modeled area, represented-area sum mismatch, header/calendar mismatch, unsupported
events, non-finite rows, and a reparsed residual beyond ADR tolerance. A zero-area
background source remains in provenance but need not contribute row data. Use a
temporary output and atomic replace so a failed combine cannot destroy the current
parent source.

Add Rust identities for one unchanged source, zero-weight background plus full
field coverage, half background plus an identical half field, two sources,
zero-runoff days, all event labels, invalid numeric input, mismatched calendars,
and output reparse. Update the release package `__init__.py`, top-level README,
module registry, and release provenance as required by the sibling repository's
instructions. Build and copy the canonical py312 extension, then prove the exported
function imports from the release tree. Existing Roads tests must pass unchanged.

### Milestone 3: Implement isolated AgFields orchestration

Create `wepppy/nodb/mods/ag_fields/watershed_integration.py` with a focused
`AgFieldsWatershedIntegrator` collaborator. Keep `AgFields` as the public facade.
Add facade properties for the watershed root, runs, output, and manifest paths;
add `run_watershed_integration`, `clear_watershed_integration`, and
`get_watershed_integration_state`; and persist only additive signature, terminal
summary, and status fields. Historical NoDb payloads default to not run. Hold the
NoDb lock only while mutating persisted state, never across raster scans, native
combination, or WEPP subprocesses.

The collaborator executes these phases in order:

1. Preflight current independent sub-field outputs, prepared parent WEPP inputs,
   observed calendar, single-OFE support, translator ids, legacy PASS capability,
   and absence of an overlapping AgFields job.
2. Read `fields.parquet`, aligned `dem/wbt/subwta.tif`, and
   `ag_fields/sub_fields/sub_field_id_map.tif`. Derive all parent and retained source
   areas from that common grid. Confirm unique cell ownership, no overcoverage,
   `A_background >= 0`, unique sub-field ids, and complete parent/source mappings.
3. Reset only the isolated tree, copy or hard-link current prepared parent inputs
   into `wepp/ag_fields/watershed/runs`, and create a legacy ASCII parent run for
   every translator hillslope. Run parent hillslopes there with bounded concurrency
   and retain their PASS files in the isolated output. The implementation may remove
   non-PASS hillslope products created solely during materialization after each
   successful parent, but must retain errors and explicit provenance. Never read
   summary parquet as a replacement for a process PASS.
4. Write the versioned source plan before combining. Validate each independent
   sub-field PASS and its climate path against the corresponding parent climate.
   Normalize climate tokens only in the new combined output; never edit a source.
5. Leave untouched parent PASS files as materialized. For each affected parent,
   pass the parent background represented area plus every sub-field represented area
   to the weighted kernel, write to a temporary path, and replace that parent's
   isolated PASS only after closure succeeds.
6. Stream returned diagnostics into `pass_sources.parquet`,
   `pass_event_closure.parquet`, and `pass_run_closure.parquet`. Use run-relative
   paths and schema metadata containing algorithm and ADR versions.
7. Build `pw0.run` with `make_watershed_omni_contrasts_run`, pass a complete ordered
   parent list and `legacy_ascii`, execute `run_watershed`, and regenerate isolated
   hillslope/watershed interchange plus `totalwatsed3` where supported. Assert the
   required resource inventory before recording success.
8. Atomically persist `integration_summary.json`, the NoDb source signature, and the
   terminal facade summary. On failure, persist the failed phase and actionable
   error while leaving existing authoritative trees untouched.

The source signature includes current parent prepared-input identity, AgFields
sub-field source signature, `fields.parquet` and aligned-raster identity,
independent PASS inventory, parent and AgFields executable identities, calendar,
weighted-kernel version, semantic-table/ADR version, and artifact schema version.
Upstream boundary/schema, sub-field, rotation, plant, Stage 4, parent WEPP, watershed,
soil, landuse, or climate changes make integration stale. Do not use an mtime-only
shortcut where an existing canonical task timestamp or source signature is
available.

Add manifest documentation with the exact schemas from the compatibility plan.
The manifest warning must say that field water and sediment are injected at the
parent outlet and that downslope buffer/runon effects are not represented.

### Milestone 4: Add the fifth workflow stage

Extend `wepppy/rq/ag_fields_rq.py` with job key
`agfields_run_watershed`, a worker that clears the integration timestamp on start,
calls the facade, publishes structured phase/result/failure events, and stamps a new
additive preflight task only after required artifacts exist. If a new TaskEnum is
not needed for user-facing global preflight, keep completion in AgFields state
rather than overloading `run_ag_fields`; decide explicitly and record the result in
the plan. Add the job to AgFields single-flight enumeration and queue dependency
catalog.

Add authenticated rq-engine routes under the existing AgFields router:

- `POST /runs/{runid}/{config}/agfields/run-watershed`
- `POST /runs/{runid}/{config}/agfields/clear-watershed`

Both call `authorize_run_access`, preserve the canonical response/error contract,
and accept no filesystem path. The run route requires current successful Stage 4,
current parent inputs, supported climate/PASS family, and no active job. The clear
route may remove only the isolated tree and additive integration state. Extend the
existing state response with additive `watershed_integration`, job id, readiness,
staleness, result links, and limitation text.

Update `wepppy/nodb/mods/ag_fields/ui_control_layout.md`, the AgFields pure template,
and `wepppy/weppcloud/controllers_js/ag_fields.js` to render Stage 5 after Stage 4.
The button starts the job; hydration disables it when prerequisites are incomplete
or stale; completion shows counts, closure status, limitation text, and a browse
link rooted at `wepp/ag_fields/watershed/`. Do not add a standard report scope in
this package. Rebuild generated controller assets and add Jest, template, route,
and RQ tests.

Update `wepppy/rq/job-dependencies-catalog.md`, regenerate the dependency graph if
needed, run `wctl check-rq-graph`, and inspect a live local job tree before closure.

### Milestone 5: Prove engineering and security contracts

Add deterministic synthetic fixtures that are small enough for unit tests and do
not require the large dev project. Cover all weighted identities, source-area
planning, parent materialization, climate-token normalization, exactly-one-parent
staging, stale/failed state, clear boundaries, symlink/path rejection, queue
single-flight, route auth, UI hydration, and isolated interchange.

Update the AgFields README, usersum design, UI contract, ADR, compatibility plan,
native docs, work package, tracker, and this ExecPlan to describe as-built behavior.
Do not modify generated usersum `docs_index.json`. Run focused tests first, then
native release import, frontend gates, queue graph, stub checks, broad-exception
enforcement, docs lint, code-quality observability, and the repository-wide pytest
gate. Resolve every medium/high security finding before moving to the dev project.

### Milestone 6: Generate the Mariana evaluation bundle

Use `/wc1/runs/sa/sacral-self-discipline` only after Milestones 1-5 pass. Capture a
pre-run inventory and SHA-256 manifest of existing baseline and independent
AgFields trees. Execute the new operation through its actual RQ/API path, not by
calling private helpers. Monitor progress and disk use without changing parent
cleanup settings.

Acceptance expects the current data facts unless upstream inputs have deliberately
changed: 6,626 independent sub-fields, 1,869 affected parents, 3,543 total parents,
113,774,400 m2 field area, 176,981,400 m2 affected-parent area, zero overcovered
parents, and 482 full-coverage parents. If facts differ, stop and record the source
change rather than weakening assertions.

Verify one PASS per parent, zero missing/duplicate source assignments, accepted
area and serialized water/sediment closure, successful watershed output, required
interchange resources, terminal state, and byte-identical preexisting artifacts.
Record runtime, peak disk use if observable, counts, closure maxima, output paths,
and any failure/retry evidence in the tracker.

Write an evaluation README under the isolated manifest tree that points Mariana to
baseline, independent sub-field, integrated watershed, source/closure, and geometry
artifacts. State the outlet-injection limitation prominently. Hand off the bundle;
record scientific status as pending rather than inventing conclusions. Concept 1
remains deferred regardless of engineering success unless Roger explicitly reopens
it after the evaluation.

## Concrete Steps

Run commands from `/home/workdir/wepppy` unless a command changes directory.

Before each milestone, inspect both repositories for unrelated changes:

    git status --short
    git -C /home/workdir/wepppyo3 status --short

For native iteration:

    cd /home/workdir/wepppyo3
    cargo fmt --check
    cargo test -p wepp_interchange_rust

After the native API passes, refresh only the canonical `wepp_interchange`
extension according to `/home/workdir/wepppyo3/README.md`, then verify:

    PYTHONPATH=/home/workdir/wepppyo3/release/linux/py312 python3.12 -c \
      "from wepppyo3.wepp_interchange import combine_weighted_hillslope_pass_files; print('ok')"

For WEPPpy focused iteration, choose the final test paths created by the package and
record exact outputs in the tracker. The expected command families are:

    wctl run-pytest tests/nodb/mods/test_ag_fields_watershed_integration.py
    wctl run-pytest tests/rq/test_ag_fields_rq.py
    wctl run-pytest tests/microservices/test_rq_engine_ag_fields_routes.py
    wctl run-npm lint
    wctl run-npm test
    wctl check-rq-graph
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

For documentation:

    wctl doc-lint --path docs/work-packages/20260713_ag_fields_concept2_watershed_integration
    wctl doc-lint --path docs/adrs/ADR-0018-agfields-weighted-pass-accounting.md
    wctl doc-lint --path wepppy/weppcloud/routes/usersum/weppcloud/ag_field-mod.md

Before handoff:

    wctl run-pytest tests --maxfail=1
    git diff --check
    git -C /home/workdir/wepppyo3 diff --check

Use the actual authenticated run route and job polling surface for the dev project.
Record job ids and terminal payloads in the tracker without recording credentials.

## Validation and Acceptance

Milestone 1 passes only when every PASS field has an evidence-backed operation and
ADR-0018 is Accepted. "Unknown but zero it" and "copy the base value" are not
acceptable unspecified fallbacks.

Milestone 2 passes when the new API is imported from the canonical release, all
weighted identities and reparsed closure tests pass, and every existing Roads
combiner test remains green. Tests must prove output header target area and climate
token, event precedence, day alignment, sediment class mass, extensive water terms,
zero-weight handling, non-finite rejection, and atomic output behavior.

Milestone 3 passes on a synthetic project when current parent PASS files are
materialized inside the isolated tree, affected sources combine, untouched parents
stage, watershed WEPP consumes the complete set, required interchange resources
exist, manifests match documented schemas, and original project artifacts have not
changed.

Milestone 4 passes when an authorized caller can hydrate Stage 5, enqueue it, poll
the job, observe terminal result, browse outputs, and clear only the isolated tree.
Unauthorized, stale, overlapping, malformed, and cross-run requests must fail with
the canonical error contract. UI tests must show correct disabled/ready/running/
failed/complete states and limitation text.

Milestone 5 passes when all focused gates, security review, queue graph, docs, and
release-provenance checks pass. The full suite must pass or stop only on a reproduced
unrelated baseline failure recorded with exact evidence.

Milestone 6 passes when the real run completes with the expected inventories,
accepted closure, immutable source trees, and a self-contained Mariana evaluation
bundle. It does not require Mariana to approve scientific use before engineering
delivery is recorded; her disposition is a subsequent explicit record.

## Idempotence and Recovery

Planning and validation reads are non-mutating. The integration run owns only
`wepp/ag_fields/watershed/` plus additive integration state. Starting a fresh run
may replace that isolated tree after preflight and single-flight admission. It must
never delete or rewrite baseline or independent AgFields files.

Write combined PASS and manifest artifacts to temporary files in the target
directory, fsync where repository conventions require it, and atomically replace
only after successful write/reparse/closure. A failed parent combine leaves its
materialized parent PASS and a failed terminal summary. A retry begins from a clean
isolated workspace; it does not try to infer success from partial files.

If parent materialization fails, preserve the failing `p<id>.err`, record the parent
id and phase, and stop before watershed execution. If watershed execution or
interchange fails, retain the isolated tree for diagnosis and mark the state failed.
The clear route removes it after active-job checks.

Rollback is disabling/removing Stage 5 and its additive routes/state while leaving
the independent AgFields workflow unchanged. The isolated tree is regenerable and
requires no migration rollback.

## Artifacts and Notes

The package owns these checked-in evidence documents:

- `artifacts/pass_field_semantics.md` (created in Milestone 1)
- `artifacts/2026-07-13_run_artifact_compatibility_plan.md`
- `artifacts/2026-07-13_security_review.md`
- optional concise generated-output evidence summaries from the dev run

The generated evaluation bundle remains under
`/wc1/runs/sa/sacral-self-discipline/wepp/ag_fields/watershed/`. Its manifest
includes the scientific README, source/event/run closure Parquets, terminal summary,
materialized parent provenance, and
`evaluation_evidence/authoritative_{pre,post}.parquet`.

Do not commit multi-gigabyte model outputs or the evaluation bundle. Keep them under
the authorized run's isolated tree and record paths, counts, hashes, and concise
transcripts in the tracker.

## Interfaces and Dependencies

No new external dependency is expected. Use Rust/PyO3, Arrow/Parquet support already
present in `wepp_interchange`, pandas/GDAL already used by WEPPpy, existing
`wepp_runner` functions, the NoDb lock/persistence contract, existing RQ/status
machinery, and existing UI controller utilities.

The final native public interface is the additive
`wepppyo3.wepp_interchange.combine_weighted_hillslope_pass_files` function described
in Milestone 2. The existing `combine_hillslope_pass_files` signature and semantics
do not change.

The final WEPPpy public facade is `AgFields.run_watershed_integration()`,
`AgFields.clear_watershed_integration()`, and
`AgFields.get_watershed_integration_state()`. Long work belongs in
`AgFieldsWatershedIntegrator`; routes and RQ workers call the facade rather than the
collaborator directly.

The final HTTP interface adds only the two run-scoped endpoints in Milestone 4 and
additive state fields. It accepts bounded options such as optional worker count only
if an existing server-side validation contract supports them; it never accepts
paths, source lists, scales, or executable names from the browser.

## Revision Note

Completed 2026-07-14 after final authenticated generated-output acceptance. This
revision records the two evidence-driven semantic corrections, exhaustive native
sweep, final job/runtime/disk evidence, state-endpoint regression, exact closure
results, immutable source-tree proof, public Mariana bundle, and passing broad
validation. Scientific qualification remains pending Mariana's disposition.

Updated 2026-07-13 after completing Milestones 3-4 to record the as-built facade,
collaborator, schemas, fifth workflow stage, no-new-TaskEnum decision, security
disposition, real-project preflight, and one-parent executable rehearsal.

Updated 2026-07-13 after completing Milestone 2 to record the native API, exact
five-significant-digit serialization behavior, release refresh, and validation
evidence.

Updated 2026-07-13 after completing Milestone 1 to record the accepted field
semantics, serialization-derived closure formulas, source evidence, and decisions.

Created 2026-07-13 after Roger Lew selected Concept 2 for implementation, assigned
the scientific evaluation to Mariana Dobre, deferred Concept 1, and designated
`/wc1/runs/sa/sacral-self-discipline` as the dev project. The initial plan records
the discovered missing parent PASS condition and makes isolated materialization a
required implementation behavior.
