# Derive and evaluate SSURGO thickness for Staley M3


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md` in
`/workdir/wepppy`. Keep Progress, Surprises & Discoveries, Decision Log, and
Outcomes & Retrospective current. Package-relative paths below refer to
`docs/work-packages/20260908_staley_m3_soils/`; update its tracker at each
milestone. This plan is ready for a fresh agent, not already implemented.

## Purpose / Big Picture


Deliver a reproducible soil-thickness derivation from project SSURGO data and
determine whether it is an acceptable substitute for the original Staley M3
STATSGO thickness predictor. A soil map unit contains soil components, each
described by horizons (layers with top and bottom depths). The desired
quantity is cumulative soil-layer thickness, not a prescribed simulation depth
or necessarily depth to bedrock. Users eventually need reliable per-catchment
M3 inputs and understandable unavailable reasons instead of silently invented
soil depths. This package delivers offline tooling, source comparison, and
the production data contract; dashboard and NoDb/RQ integration are deferred.

## Progress


- [x] (2026-09-09 02:17 UTC) Scaffold and user direction recorded.
- [ ] M1: Inventory/acquire/freeze inputs and draft ADR plus protocol.
- [ ] M2: Resolve original predictor and interval/component policies.
- [ ] M3: Implement offline derivation, artifacts, and meaningful tests.
- [ ] M4: Run fixed-terrain paired soil-source evaluation.
- [ ] M5: Review, recommend source policy, promote documentation, close out.

## Surprises & Discoveries


The three supplied 10 m live run paths currently lack `soils/` directories.
Terrain fixtures alone cannot establish Soils readiness. Check again at
execution; do not treat an existing controller file as evidence of populated
soil tables. Source acquisition is an explicit first milestone.

`wepppy/soils/ssurgo/spatializer.py` currently computes `SolThk` by summing
`hzdepb_r`, which holds cumulative bottom depths. For 0-10 and 10-30 cm
horizons that gives 40 cm rather than 30 cm. Do not consume this output for M3
or expand this task into changing unrelated consumers.

## Decision Log


Decision (2026-09-09 02:17 UTC, user/Codex conversation): scaffold the M3 soil
work after terrain completion. Rationale: SSURGO source semantics and missing
data are the next unresolved scientific dependency. The user has not selected
an interval policy, coverage threshold, or fixed replacement depth.

Decision (2026-09-09 02:17 UTC, scaffold author Codex): reuse the genuine 10 m
terrain panel and hold terrain/burn/rainfall fixed in each paired soil-source
comparison. Rationale: isolate soil effects without confounding the completed
10 m/30 m study. Offline derivation is in scope; production integration is not.

## Outcomes & Retrospective


Documentation scaffold only. No source acceptance, acquisition, runtime
derivation, test, or soil comparison is complete. Replace this section with
measured outcomes and remaining limitations at each major handoff.

## Context and Orientation


Read `/workdir/wepppy/AGENTS.md`, `wepppy/nodb/AGENTS.md`, the postfire module
AGENTS, and `tests/AGENTS.md` plus any nested guidance before changing code or
fixtures. The canonical specification is
`wepppy/nodb/mods/postfire_debris_flow/specification.md`; its
`docs/ssurgo_m3_feasibility.md` records reviewed source fields and pitfalls.

`wepppy/nodb/core/soils.py` defines `Soils.ssurgo_cache_db_path` as
`soils/ssurgo_tabular_cache.sqlite`, separate from its STATSGO cache.
`Soils.ssurgo_fn` resolves `soils/ssurgo.tif` or `.vrt`. The controller's
`raw_ssurgo_domsoil_d` and `ssurgo_substitution_d` help identify substitution.
Do not assume the current spatial labels still denote original map units:
audit original versus substituted raster/key lineage before joining tables.

`wepppy/soils/ssurgo/ssurgo.py` fetches and caches `component` fields `mukey`,
`cokey`, `comppct_r`, and `chorizon` fields including `chkey`, `hzdept_r`,
`hzdepb_r`, `hzthk_r`, `desgnmaster`, and `hzname`. Confirm current schemas with
read-only SQLite queries. Multiple horizon records can share depth intervals.
The current restrictions cache has `reskind` but not numeric `resdept_r`;
restrictive-depth estimation would require new semantics, not just a join.
Generated WEPP `.sol` files can clip, extend, filter, and round profiles, so
they are unsuitable raw thickness inputs. POLARIS layer intervals are not
measured total soil thickness and RUSLE K does not supply M3's soil predictor.

Original USGS metadata identifies STATSGO `THICK` as cumulative soil-layer
thickness in inches. Verify primary references before finalizing semantics:
`https://pubs.usgs.gov/ds/270/data/DVD-1/METADATA/Soil_att.htm`,
`https://pubs.usgs.gov/ds/270/data/DVD-1/METADATA/Soils250K.htm`, and the NRCS
`https://sdmdataaccess.nrcs.usda.gov/documents/FundamentalQuery.pdf`.
The catalog identifier for the original reference raster is
`https://catalog.data.gov/dataset/statsgo-soil-thickness-thick-cloud-optimized-geotiff-for-the-continental-us`.
Verify publisher, actual asset URL/version, units, coverage, and sentinel
values; never assume a similarly named modern product reproduces the original.
The reviewed catalog described inches, NaN gaps, and a -0.1 water sentinel.
Retrieve bounded windows using the existing geospatial stack; avoid downloading
an entire continental raster when small windows suffice. This is comparison
data, not an authorized automatic production fallback.

M3 uses S = catchment mean thickness in inches / 100, equivalent to mean cm
/ 254. Thus 100 cm gives S = 0.3937007874. Internal thickness may be cm, but
canonical M3 scaling must preserve this factor. Display SI/English values via
Unitizer conventions; changing display units must not change S or probability.
Keep raster value units, display units, and dimensionless S explicit.

The completed terrain work accepted H = upstream maximum raw elevation minus
outlet raw elevation and T = H/sqrt(upstream area including outlet), and
recommends genuine 10 m for initial support. See `docs/adrs/ADR-0052-staley-m3-upstream-terrain.md`
and the closed `20260908_staley_m3_wbt_terrain` artifacts. Do not amend closed
package records. WBT fixtures at
`/workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution/` contain the sites
Moscow Mountain (`desolate-yea` at 10 m), Topanga (`sorrowful-semicircle`), and
user-labeled AZ ponderosa (`full-crocodile`). The last label is provenance,
not geographic proof: its coordinates are near -106.671, 35.732. The terrain
study has 12 outlets, including nested cases and an approximately 23 km2
terminal diagnostic outside the paper's reported area range. Preserve these
labels and range flags. Reuse the committed catchment/command records, but
verify availability of generated masks and reconstruct missing masks with
the accepted tool/routing rather than assuming mutable /tmp outputs persist.

## Plan of Work


### M1 — Inventory and freeze reproducible inputs


Inspect git status and current source schemas without mutating live projects.
Inventory original raster keys, cached map units/components/horizons, source
substitutions, and support for each supplied 10 m catchment. Begin with the
three named sites; no open-ended search for an entirely new panel is required.
If their caches are absent, use existing SSURGO acquisition interfaces to
retrieve only required map units into an isolated study directory, preserving
query/source/version metadata. Do not call a live Soils build, fabricate an
empty cache, or confuse study-acquired data with already-ready project data.
Record exact gaps and external failures while continuing independent work.

Create `artifacts/source_inventory.csv` and version minimal read-only soil
fixtures under `tests/nodb/mods/fixtures/postfire_debris_flow_soils/` (adjust
to nearer test conventions if required, then record the final location).
Include the spatial key subset needed to reproduce joins and public table
subsets sufficient to reproduce interval/component results. Avoid whole NoDb
or unrelated project databases. Keep hashes, source URLs/query parameters,
units, and attribution; use existing storage conventions for binary fixtures.
Prefer small inspectable tables; document the SQLite fixture-generation recipe
if database boundary tests require a database. Inspect real boundary states
before fixing a schema that only fits idealized rows.

Draft the next available parameterization ADR. In `artifacts/study_protocol.md`,
predeclare source comparison metrics, separate common-support/full-support
analyses, coverage sensitivity, and proposed numerical/scientific screens with
rationale. No tolerance from the terrain study is automatically a published
soil-source acceptance limit. Record protocol revisions before interpreting
results rather than tuning limits to obtain a preferred decision.

### M2 — Resolve the thickness and coverage contract


Write `artifacts/soil_contract.md`, then promote settled rules to the canonical
specification and ADR before implementation. Confirm whether the original
STATSGO transformation included particular bedrock/nonsoil layers, how its
map-unit weighting worked, and whether reference THICK is censored by survey
depth. Do not equate an observed profile endpoint with proven bedrock depth.

Compare candidate sum-of-valid-intervals, interval-union, and deepest-bottom
derivations on audited records. Deduplicate stable identifiers separately from
duplicate depth ranges; overlapping subhorizons can represent alternate records
and need a source-supported policy. Define zero starts, gaps, reversed/negative
depths, missing endpoints, conflicting `hzthk_r`, and bedrock classifications
including ambiguous/weathered material. Do not fill unsampled gaps or impose
150/200 cm by default. Preserve measured zero/nonsoil classifications separately
from missing or rejected data. Source-backed routine choices may be resolved
autonomously and documented; genuinely unresolved scientific alternatives
remain explicit and should be presented with evidence for the decision owner.

Define component-percentage aggregation and its denominator: known component
percentages, valid-thickness percentages, omitted components, and totals below
or above 100 must all be visible. A mean over known components estimates known
support; it must not silently masquerade as complete map-unit coverage. Define
area weighting over full contributing catchments, channel cells, fractional
map-unit coverage, nonsoil/water, outside-survey coverage, and substituted keys.
Freeze reason codes and unavailable/partial/complete distinctions. Do not copy
dNBR's partial-coverage acceptance rule into soils without evidence. Evaluate
coverage thresholds rather than inventing one merely to permit runs.

### M3 — Implement the offline derivation and verify propagation


Use a narrow module helper, provisionally
`wepppy/nodb/mods/postfire_debris_flow/soil_thickness.py`, with pure interval and
component calculations, an explicit read-only source adapter, and an offline
artifact builder callable by the study harness. This is not a new NoDb class
or automatic Soils action. Confirm the nearest canonical-contract requirements
and finalize helper signatures and artifact schemas in M2 before coding.

The builder must produce inspectable component/map-unit thickness and coverage
tables, a project-grid thickness raster and valid-support/coverage information,
and a catchment table with thickness, S, source identifiers, denominators,
reason codes, and source hashes. Decide exact artifact names/units in the
contract; do not imply planned schemas already exist. Use owned compiled
raster aggregation for bulk work (weppcloud-wbt, wepppyo3, oxidized-rasterstats,
or peridot as appropriate), and normal Python for modest tabular interval logic.
Avoid a new external dependency or pure-Python raster traversal.

Before any data-schema mutation, write the compatibility/regression plan:
new offline outputs in a separate study directory, no renaming existing keys,
no writes to project soil caches or WEPP generated files, and explicit missing
source errors. Read SQLite in read-only mode and keep boundary/path handling
within existing conventions. No source acquisition fallback during evaluation.
If production UI-coupled behavior becomes necessary, stop scope expansion and
apply the ancestor-checkpoint contract-first standard before that separate work.

Add meaningful tests for contiguous 0-10/10-30 cm intervals, duplicates,
overlaps, gaps, bedrock ambiguity, invalid depths, weights, missing components,
substitutions, unknown map units, water, partial catchments, and units. A simple
valid weighting fixture is 60% of 30 cm and 40% of 100 cm = 58 cm; removing a
component must change coverage and follow the explicit contract. Verify 100 cm
and 39.3700787 inches yield the same S within declared precision. Use a small
real public subset as well as synthetic cases. Exercise the actual read-only
adapter and generated raster/table pipeline; assert source hashes remain
unchanged and trace values through to diagnostic M3 outputs. This is required
downstream evidence for these new offline artifacts; no production wiring is
claimed by those tests.

### M4 — Compare sources on fixed 10 m catchments


Acquire and freeze bounded original STATSGO THICK windows with explicit nodata
and water handling. Preserve source mapping scale and units: raster spacing
does not establish detailed soil knowledge. Treat SSURGO keys categorically
when aligning; use a documented support-aware method for continuous THICK.
Do not resample categorical IDs with bilinear interpolation. Fix terrain,
outlet masks, burn fraction, and rainfall for each source pair.

For each available one of the 12 terrain outlets, compare raw thickness,
coverage, S, and M3 outputs; report explicit unavailable rows for missing
sources. Include common valid support and full-catchment policy results so
coverage changes are not misrepresented as thickness differences. Retain
outside-calibration-area diagnostics separately. Compare policy alternatives
only as labeled sensitivity cases; do not silently change the selected builder.

Use the canonical M3 coefficients from the specification for 15/30/60 minutes.
For reference, x = B + R*(Ct*T + Cf*F + Cs*S), p = logistic(x); R is rainfall
accumulation in mm. Inverse accumulation is
(log(p/(1-p))-B)/(Ct*T+Cf*F+Cs*S), with intensity obtained by dividing by hours.
Record diagnostic F and rainfall choices before analysis and sample meaningful
nonsaturated probabilities. Report absolute probability changes in percentage
points and relative/absolute threshold changes at interior target probabilities,
including 50% and 75% as study diagnostics, not approved production defaults.
Use stable numerical evaluation and explicit invalid-denominator handling.

Write `source_comparison.csv`, `m3_sensitivity.csv`, plots, and
`soil_decision.md`. Recommend SSURGO under explicit conditions, retaining the
original source, or insufficient evidence with the precise missing information.
Agreement with STATSGO is source-comparability evidence, not validation against
observed debris flows. Improved spatial detail alone does not justify model
substitution. If original reference data remain unavailable, do not call the
source-comparison milestone complete based only on synthetic examples.

### M5 — Review and publish durable findings


Run targeted and repository-required checks and capture commands/output in
`artifacts/validation.md`. Obtain independent correctness and security reviews
using the repository templates; required bounded review delegation is permitted.
Close medium/high findings and rerun affected checks after fixes. Account for
absent, empty, partial, legacy/custom, and malformed input states, not merely
the happy-path table arithmetic.

Update the module README, specification, feasibility assessment, ADR, test
fixture documentation, package tracker, and PROJECT_TRACKER with results.
Distinguish offline implementation from production wiring and scientific
recommendation from an approved availability policy. Archive prompts with
outcomes only when the plan's deliverables are achieved. If blocked, leave
explicit incomplete milestones and evidence rather than declaring readiness.

## Concrete Steps


From `/workdir/wepppy`, first run `git status --short`, read the named AGENTS
and specification, then mark this package In Progress on PROJECT_TRACKER.
Use `/tmp/staley-m3-soils-study/` or a documented persistent study directory
for acquisition and generated files. Record commands and hashes in the artifact
catalog; temporary workspace disappearance must not destroy reproducibility.

Baseline discovery is read-only. A current project cache can be inspected with
Python's standard `sqlite3` using an encoded `file:` URI with `?mode=ro`
and `uri=True`, or the existing read-only
database helper. Record actual table schemas before writing adapters. Replace
this descriptive example with exact executable audit/build commands in
`artifacts/validation.md` once M2 freezes paths and signatures.

From `/workdir/wepppy`, use these validation entry points:

    wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_soil_thickness.py
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260908_staley_m3_soils
    wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow

The focused test path is planned; update this plan if nearest test conventions
require a different path. Follow stub/API checks for any new public surface.
Do not run frontend or RQ gates absent those changes. Record environment
failures separately from code failures; never report unrun tests as passed.
Run the final offline builder against frozen fixtures and the full acquired
panel, record exact invocations and expected artifacts, and verify hashes of
inputs before and after. Compile-time or unit-test success alone is insufficient.

## Validation and Acceptance


The same frozen inputs must reproduce the same derived thickness/support
tables and rasters within declared precision. Missing data must never become
an ordinary zero-thickness soil. Source joins and weighting denominators must
be auditable, unitized displays must preserve scientific values, and catchment
S must propagate to diagnostic outputs. The source decision must be supported
by a real paired comparison and explain its geographic/sample limits. No
unresolved medium/high review findings may remain at implementation closeout.

## Idempotence and Recovery


Use immutable source snapshots and scenario-specific output directories.
Retry bounded failed downloads without modifying valid snapshots or live runs;
record failures and partial outputs explicitly. Keep generated rasters outside
versioned input fixtures. Preserve unrelated edits and branches. Do not deploy,
rebuild live soils, change production defaults, or reset working trees as a
recovery shortcut. Commit only with explicit authorization for execution.

## Artifacts and Notes


The catalog is `artifacts/README.md`. Keep minimal public source fixtures,
hashes, provenance, tabular results, plots, contracts, commands, and reviews.
Do not redistribute the Staley PDF or GPL pfdf implementation/tests. The
closed terrain package is immutable reference evidence, not living governance.

## Interfaces and Dependencies


The proposed helper accepts explicit component/horizon records plus spatial
map-unit and catchment inputs, and returns thickness/support/provenance with
stable unavailable reasons. Freeze actual function signatures and additive
artifact fields in M2 before implementation. Existing Soils owns source
preparation; the M3 evaluator consumes prepared artifacts. This package's
acquisition harness is offline and cannot silently become production fallback.
Use existing SQLite and owned geospatial components; follow dependency evaluation
before adding any new library. No new production NoDb/RQ/UI contract is shipped.

Revision note (2026-09-09 02:17 UTC): Initial scaffold created for a fresh agent;
source acquisition, policy resolution, implementation, and comparison are pending.
