# Implement WBT M3 terrain tooling and evaluate DEM resolution


This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md` in `/workdir/wepppy`. Keep Progress,
Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current.
The canonical package is
`docs/work-packages/20260908_staley_m3_wbt_terrain/` in WEPPpy; all package-relative
artifact names below resolve there. Update its tracker at every milestone.

## Purpose / Big Picture


Provide a working weppcloud-wbt command that calculates the upstream terrain
quantity required by Staley 2017 M3, then determine how 10 m versus 30 m DEMs
affect that quantity and M3 outputs. A DEM is a raster of terrain elevations;
D8 routing assigns each cell one downstream neighbor. A catchment comprises
all cells draining to a specified outlet, including upstream tributaries.
The user should receive runnable tooling, reproducible comparison results,
and a defensible recommendation about M3 resolution requirements.

The present task created a scaffold only. This plan's execution must deliver
working CLI and binding behavior and measurements from the rebuilt binary.
Production Staley NoDb/UI/RQ integration, deployment, binary vendoring, soil
estimation, and changes to live project data are excluded. Do not create or
switch branches or commit unless the user separately authorizes that action.

## Progress


- [x] (2026-09-08 23:30 UTC) Scaffold created and user direction recorded.
- [ ] M1: Repository discovery, scientific/CLI contract, ADR, study protocol.
- [ ] M2: Rust implementation, registration, bindings, and synthetic tests.
- [ ] M3: Current-binary execution and external reference comparison.
- [ ] M4: Catchment selection and paired 10 m/30 m study.
- [ ] M5: Validation, independent reviews, decision report, durable docs.

## Surprises & Discoveries


WEPPpy's existing `wbt/relief.tif` is a conditioned elevation DEM, not a
vertical-relief raster. Evidence: `_create_relief` in
`wepppy/topo/wbt/wbt_topaz_emulator.py` invokes filling/breaching tools.

The local accepted manuscript section 5.2 omits the square root in prose,
whereas pfdf M3 uses relief divided by square root of area. pfdf documentation
alternates between nearest and highest ridge. Its underlying weighted-path
recurrence requires pinned-version verification, including weight indexing;
simple maximum-elevation subtraction is not yet proven equivalent.

The existing WBT maximum-upslope-value plugin derives its own D8 routing.
It demonstrates the traversal pattern but does not already accept the project's
authoritative pointer raster. No numeric comparisons have been run.

## Decision Log


Decision (2026-09-08 23:30 UTC, user via Codex conversation): implement the
tooling in weppcloud-wbt and then evaluate 10 m versus 30 m. Rationale: keep
terrain processing in the owned Rust backend and establish resolution support
from measurements. The user has not approved a final relief definition,
numeric tolerance, or resolution cutoff.

Decision (2026-09-08 23:30 UTC, scaffold author Codex): separate reference parity
from resolution sensitivity, and keep production integration out of this
package. Rationale: matching a reference does not establish 30 m suitability,
and terrain readiness does not resolve the outstanding M3 soil input contract.

## Outcomes & Retrospective


Scaffold only. The six-run fixture inventory is available. No runtime implementation, reference parity,
resolution acceptance, or production integration is complete. At handoff replace
this paragraph with measured outcomes, limitations, and remaining work.

## Context and Orientation


The repositories are `/workdir/wepppy`, `/workdir/weppcloud-wbt`, and the GPL
reference `/workdir/usgs-pfdf`. Read each applicable AGENTS before editing its
files. WBT `DEVELOPING_TOOLS.md` describes Rust registration, argument parsing,
metadata, and mirrored wrappers `whitebox_tools.py` and `WBT/whitebox_tools.py`.
The likely tool location is
`whitebox-tools-app/src/tools/hydro_analysis/`; toolbox `mod.rs` and
`whitebox-tools-app/src/tools/mod.rs` register commands. Existing traversal
precedent is `whitebox-plugins/src/max_upslope_value/main.rs`. Inspect local
build scripts and Cargo manifests before choosing a binary build command.

WEPPpy's canonical domain document is
`wepppy/nodb/mods/postfire_debris_flow/specification.md`, supplemented by
`docs/m3_terrain.md` in that module. Staley predicts conditional debris-flow
occurrence from rainfall and catchment predictors. M3's terrain predictor T is
working-defined as H/sqrt(A), with vertical relief H in meters and total upstream
planimetric area A in square meters. T is dimensionless. The other M3 predictors
are moderate/high burn fraction F and mean cumulative soil thickness in inches
divided by 100, S. Their production derivation is outside this work package.

For diagnostic propagation only, x = B + R*(Ct*T + Cf*F + Cs*S), and
p = 1/(1+exp(-x)), where R is duration-specific rainfall accumulation in mm.
For 15, 30, 60 minutes respectively, M3 B is -3.71, -3.79, -3.46; Ct is
0.32, 0.21, 0.14; Cf is 0.33, 0.19, 0.10; Cs is 0.47, 0.36, 0.18.
Inverse accumulation at probability p is
(log(p/(1-p))-B)/(Ct*T+Cf*F+Cs*S). Divide by duration in hours for mm/hour.
Verify coefficients against the module specification and paper before use.
Use interior probabilities and valid positive denominators in the study;
report unavailable cases explicitly rather than masking numerical failures.

The locally supplied paper may exist at
`/workdir/wepppy/wepppy/nodb/mods/postfire_debris_flow/docs/pdfs/staley_2017.pdf`
or `/tmp/staley2017.pdf`. It is a 42-page accepted manuscript, DOI
10.1016/j.geomorph.2016.10.019, SHA-256
72de34d27231acd14cc0ba8daf431e9121464132072447aef6ff658b687e660b.
Preserve its gitignore status; redistribution permission has not been established.
If absent, use published public references and record the missing local source.
Do not copy or translate GPL pfdf code, tests, or documentation. Independently
derive owned code and fixtures; run pfdf separately for numerical comparison.

## Plan of Work


### M1 — Define the terrain contract and evaluation protocol


Read the full module specification and terrain note, inspect the current WBT
implementation and build conventions, and capture git revisions/status in both
owned repositories. In `artifacts/terrain_contract.md`, resolve the candidate
H(o) = max upstream elevation minus outlet elevation against highest-source
relief and catchment maximum-minus-minimum. These agree for monotonic routing
but can differ when raw elevations are paired with conditioned routing. Pin
the reference and its pysheds version; test simple cases instead of trusting
inconsistent docstrings. If reference behavior is defective, document the
discrepancy rather than encoding a bug solely to claim parity. Escalate a
scientific ambiguity only if primary evidence and diagnostic cases cannot
resolve it; continue independent tool/data discovery in the meantime.

Draft the next available parameterization ADR in WEPPpy `docs/adrs/`, recording
the conversation, user decision ownership, actual implementer, candidate and
selected formulas, alternatives, evidence, units, and risks. Finalize the
terrain algorithm before production implementation. This ADR can remain
proposed on resolution support until the study is complete. Amend the canonical
module terrain specification with settled scientific semantics and rationale.

Specify an additive command, provisionally `D8UpstreamRelief`, with required
`--dem`, `--d8_pntr`, and `--output` (H in meters), plus `--area` output (A in
square meters). Adopt an existing compatible command if discovery proves it
meets this contract; record the exact final name and flags in this plan before
coding. Input DEM is the explicitly chosen elevation measurement surface,
not an instruction to recompute routing. Use the supplied WBT D8 pointer, with
an explicit encoding contract. Outputs must align exactly with inputs. Define
outlet-cell inclusion, elevation conversion, projected horizontal units,
NoData and incomplete-upstream-coverage behavior, flat/pit handling, terminal
cells, boundary routing, and cycle/invalid-pointer errors. Reject unsupported
grids/units explicitly; do not silently reproject or select another DEM.

Write `artifacts/study_protocol.md` before interpreting real-study outcomes.
Predeclare comparison metrics, numeric tolerances justified by storage
precision, and application-level resolution criteria with sensitivity to those
criteria. These are proposed engineering criteria, not published Staley limits.
Use fixed F/S values spanning meaningful diagnostic conditions and rainfall
covering nonsaturated probabilities, recording their exact values and rationale.
This isolates terrain effects without waiting for SSURGO production readiness.
Avoid choosing criteria after seeing results merely to accept 30 m.

### M2 — Implement and register the Rust tool


Implement the resolved flow-based algorithm in weppcloud-wbt with an O(N)
traversal over N cells, combining contributions once per downstream edge.
Reuse owned routing/raster infrastructure. Keep Staley coefficients and UI
behavior out of the terrain command. Register it in the toolbox and global
dispatcher and add wrappers to both Python bindings. Follow WBT error and
metadata conventions, documenting elevation source, pointer encoding, units,
area inclusion, and the relief definition. Update WBT algorithm documentation
and CHANGELOG. Avoid broad refactors and new dependencies; if a new dependency
is essential, follow WEPPpy's dependency-evaluation standard first.

Add independently authored deterministic fixtures with analytical expectations:
descending chain, unequal tributaries, nested outlets, source/outlet cells,
flats, pits/conditioning, internal raw-elevation maximum, NoData/boundary cases,
invalid pointers, cycles, mismatched grids, and unsupported units. A useful
descending 3-cell chain has elevations 130, 120, 100 m and 10 m square cells:
under maximum-minus-outlet semantics its final outlet H is 30 m, A is 300 m2,
and T is 30/sqrt(300). Update expected cases if the scientifically resolved
definition differs, with the reason recorded before changing tests.

### M3 — Verify real command execution and reference behavior


Build the current binary and record revision, local diff, absolute binary path,
hash, and tool metadata. Run fixtures through the CLI and each binding using
that exact binary; compilation alone does not establish wiring. Verify output
values, masks, metadata, and failure behavior from generated files.

Run pinned pfdf in an isolated reference environment against identical grids,
raw elevation inputs, masks, D8 routing converted to its encoding, and outlet
cells. Compare A, H, and T separately; record maximum/median discrepancies and
all meaningful exceptions in `artifacts/reference_parity.md`. Do not compare
different delineations and call their differences algorithm error. Independently
authored expectations are the correctness anchor if reference defects emerge.
Resolve material discrepancies before relying on the tool for resolution claims.

### M4 — Assess representative catchments at both resolutions


The user has supplied three primary paired watersheds, now snapshotted in
`/workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution/`: Moscow Mountain
(bass-elimination 30 m, desolate-yea 10 m), Topanga (untucked-hit 30 m,
sorrowful-semicircle 10 m), and user-labeled AZ ponderosa (offshore-remake 30 m,
full-crocodile 10 m). Run `git lfs pull` in WBT and the fixture `verify.py`.
Start with these three outlet pairs; add matched nested outlets where useful
and expand only when an unrepresented failure mode warrants it. Gate Creek
is optional additional evidence, not a required acquisition task.

The fixture manifest contains source URLs, hashes, grids, and outlet metadata.
Boundary maps are supplied as raster, projected GeoJSON, and WGS84 GeoJSON.
The user identifies the pairs as the same watersheds with identically specified
outlets, but stored requested coordinates and snapped centers differ slightly.
Quantify these offsets rather than assuming equality. Extents intentionally
differ: verify upstream completeness without clipping to their intersection.
These are canonical-workflow comparisons, with source and delineation effects;
controlled resampling remains a separate isolation experiment. Use full upstream
catchments rather than incremental hillslope labels. Record suitability,
geography, matched outlets, and exclusions in `artifacts/catchments.csv`.

Work in an isolated directory such as `/tmp/staley-m3-terrain-study/`, keeping
large rasters out of git and preserving live runs. First compare the 10 m
reference to controlled 30 m aggregation from the same source, using documented
resampling and conditioning. Then compare available native products where
practical, labeling source differences separately. Use matched geographic
outlets with recorded snapping offsets, re-delineating at each resolution.
Report boundary overlap, area, outlet elevation, contributing maximum, H, T,
and cell count. Upsampling 30 m is not a substitute for real 10 m elevation.

Propagate terrain differences through all three M3 durations while holding
F and S constant for each paired diagnostic scenario. Report probability
differences in percentage points and inverse-threshold differences in mm/hour;
include behavior near proposed 50%/75% diagnostic thresholds and avoid claiming
agreement from saturated probabilities alone. This is terrain sensitivity,
not validation against observed debris-flow occurrence. Record runtime, peak
memory, raster dimensions, hardware, and invocation for representative sizes.

Produce `artifacts/resolution_comparison.csv`, plots, and
`artifacts/resolution_decision.md` with per-catchment and aggregate results.
Conclude 10 m required, both supported within explicit evidence-backed bounds,
or insufficient evidence. If insufficiency remains, name the exact additional
data/analysis needed and do not mark the user's resolution determination complete.
Do not generalize a limited Western US panel to all CONUS terrain.

### M5 — Validate, review, and hand off


Run appropriate WBT and WEPPpy checks, collect `artifacts/validation.md`, and
obtain independent correctness and security artifacts using WEPPpy templates
`docs/prompt_templates/correctness_review_template.md` and
`docs/prompt_templates/security_review_template.md`. Repository-required review
delegation is permitted for these bounded review tasks. Close medium/high
findings, revalidating changed paths. Keep CLI/file/binding behavior within the
existing execution boundaries; no deployment or production wiring is required.

Promote the supported formula, units, limitations, and resolution findings into
the module specification and `docs/m3_terrain.md`; update the ADR, WBT docs,
both package trackers as applicable, and WEPPpy PROJECT_TRACKER. Distinguish a
recommended policy from implemented UI enforcement. If execution is complete,
archive active prompts with outcomes using the work-package lifecycle. Keep
incomplete work active with a precise blocker rather than declaring success.

## Concrete Steps


From `/workdir/wepppy`, begin with `git status --short` and read this package's
brief and tracker; repeat status in `/workdir/weppcloud-wbt`. Mark the package
In Progress on WEPPpy PROJECT_TRACKER when execution begins. Read the current
WBT build instructions and nearest AGENTS before edits. Update WBT's active-plan
pointer to this canonical plan during execution without duplicating its content.

From `/workdir/weppcloud-wbt`, baseline and post-change checks are:

    cargo check -p whitebox-tools-app
    cargo test -p whitebox-tools-app
    python -m py_compile whitebox_tools.py WBT/whitebox_tools.py

Use its documented build entry point for the runnable release binary; record
the exact command and path here after discovery. The planned smoke invocation
is the following, replacing the placeholder with that verified current binary:

    <current-binary> -r=D8UpstreamRelief --dem=<fixture-dem> --d8_pntr=<fixture-pointer> --output=<study-dir>/vertical_relief.tif --area=<study-dir>/upstream_area.tif

Before M3 completes replace these placeholders in `artifacts/validation.md`
with actual reproducible commands, fixture creation steps, expected values,
and observed outputs. Record explicit wrapper calls and executable selection
for both bindings. Never accidentally test a globally installed older binary.

From `/workdir/wepppy`, run:

    wctl doc-lint --path docs/work-packages/20260908_staley_m3_wbt_terrain
    wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow

Run targeted tests for any WEPPpy executable study helpers added, following
`tests/AGENTS.md`, and the package closeout gate
`wctl run-pytest tests --maxfail=1`. Record environment failures separately from
code failures and do not claim an unrun gate passed. No frontend gate is needed
without frontend changes. Preview spelling normalization and validate new links.

## Validation and Acceptance


Success requires independently verifiable numeric outputs, not just test counts.
The registered command and both wrappers must produce aligned H/A rasters with
the documented expected fixture values, reject invalid inputs clearly, and
report incomplete coverage according to the contract. Reference differences
must have explanations and supporting cases. The study must include paired
physical outlets and provenance sufficient to reproduce its results; the final
recommendation must follow predeclared criteria and disclose population limits.
No unresolved medium/high review findings may remain at closeout.

## Idempotence and Recovery


Keep generated data under a study directory with scenario-specific names and
an input manifest; never overwrite source DEMs or live project artifacts.
Use rerunnable commands, explicitly track partially written outputs, and
regenerate failed scenarios from unchanged hashed inputs. Preserve unrelated
work in both repositories. Do not reset worktrees, change branches, commit,
vendor binaries, or deploy as a recovery shortcut.

## Artifacts and Notes


The artifact catalog is `artifacts/README.md`. Retain small tabular results,
plots, contracts, commands, hashes, and review reports in this package. Keep
large raster files externally with source acquisition/reproduction instructions.
No copied GPL source/tests or unlicensed paper redistribution belongs here.

## Interfaces and Dependencies


The runtime interface is an additive WBT command accepting an elevation raster
and the existing D8 pointer, producing vertical relief in meters and upstream
area in square meters with explicit valid-data semantics. Its final name and
flags are frozen in M1 and mirrored in both Python wrappers. WEPPpy can later
sample outlet values and compute T = H/sqrt(A); no Staley API/NoDb schema is
introduced by this package. Use owned Rust raster/routing components for bulk
processing. Reference pfdf runs remain isolated and must not become a runtime
dependency. The project-grid, outlet, and source-provenance contract must be
preserved in every comparison.

Revision note (2026-09-08 23:30 UTC): Initial plan scaffolded at user request
for a fresh agent; implementation and resolution acceptance remain pending.

Revision note: User supplied three paired watersheds; terrain and boundary fixtures
are preserved in WBT with LFS and hashes. Replaced open-ended site acquisition
with this primary panel; stored coordinate differences remain explicit.
