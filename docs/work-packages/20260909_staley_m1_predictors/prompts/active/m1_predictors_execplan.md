# Compose prepared M1 watershed predictors


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes &
Retrospective. Current request scaffolds only; implementation has not started.

## Purpose / Big Picture


A developer can supply prepared project artifacts to a local Python interface,
run the owned Horn/SBS backend and obtain a reproducible T/F/S bundle for the
existing watershed. The same bundle can drive explicit example storms through
the completed scalar M1 engine. Missing inputs remain visible rather than
silently becoming zeros or another model. This is working local integration;
production controllers, climate catalog, public upload and RQ remain separate.

## Progress


- [x] (2026-09-09 15:06 UTC) Inspect precedents and scaffold package/contracts.
- [ ] Resolve K convention/coverage/readiness and freeze interface/schema with ADR.
- [ ] Inventory authentic source fixtures and plan compatibility/regression coverage.
- [ ] Implement prepared-input conversion and owned-tool invocation.
- [ ] Compose T/F/S, provenance, availability and reproducible example outputs.
- [ ] Validate focused/full suites, independent reviews and synchronized closeout.

## Surprises & Discoveries


StaleySlopeSbs does not accept every project GeoTIFF layout. Its bounded owned
reader requires explicit finite NoData and SampleFormat, uncompressed classic
TIFF strips and no palettes. A lossless preparation stage is necessary; do not
pass arbitrary project files and mask failures with another implementation.
RUSLE K already includes source gap-fill provenance; complete numeric coverage
is not necessarily complete measured soil information.

## Decision Log


2026-09-09 15:06 UTC: user requested the next work-package scaffold after
slope/SBS completion. Scope is local M1 composition, not deployment or NoDb/UI/RQ.
Prior accepted rules remain: one project watershed/outlet, Horn on raw DEM,
strict nine-cell neighborhoods, uncertainty-preserving T, normalized observed-
support dNBR F, and area warnings outside inclusive 0.2–8 km². K-specific policy
remains pending in the decision register; no silent approval by analogy.

## Outcomes & Retrospective


Scaffold only. No new implementation, generated predictor bundles or tests.
Completion must identify local evidence separately from production readiness.
Do not mark climate, M3 soil fallback or stage 5 wiring complete here.

## Context and Orientation


Work at `/workdir/wepppy`; the same checkout is `/home/workdir/wepppy`.
Read root/nested AGENTS, `tests/AGENTS.md`, module specification and
`docs/m1_predictors.md` under `wepppy/nodb/mods/postfire_debris_flow`.
Starting WEPPpy revision is `2c4d1a94f`; WBT revision is `a97abb7`.
Verify actual working revisions rather than assuming installed binaries match.

Module `dnbr.py` exports normalization and summary helpers; normalized catchment
mean is F directly. `staley2017.py` provides scalar probability and inverse
threshold functions with accepted finite-input/error rules. `soil_thickness.py`
is M3 offline work and is not needed for M1. `integration.py` and any focused
manifest collaborator will implement this increment; do not add an active NoDb
facade or modify the old debris_flow controller.

The project domain is positive valid `dem/wbt/bound.tif` cells at the existing
resolved outlet in `dem/wbt/outlet.geojson`. Raw elevations are `Watershed.dem_fn`,
not conditioned WBT relief. The prior canonical artifact mapping governs;
no nested enumeration, clipping to burned pixels or new outlet snapping.

RUSLE inputs are `rusle/k_polaris_nomograph.tif` and the K section of
`rusle/manifest.json`. Inspect `wepppy/nodb/mods/rusle/k_integration.py`,
`k_nomograph.py`, `k_manifest.py` and its specification. Selected modes can
exclude Nomograph even when EPIC/default K exists. Never substitute those.
The manifest records near-surface depth weights, statistic, gap filling and
optional fragment adjustments; do not assume it contains a complete per-cell
imputation mask or authoritative artifact hashes without checking.

`StaleySlopeSbs` resides in `/workdir/weppcloud-wbt`; both wrappers expose
`staley_slope_sbs(dem, sbs, mask, output_dir, elevation_units, sbs_classes,
callback=None)`. Explicit units are m; normalized SBS mapping is 0,1,2,3 with
255 NoData. Outputs are slope/intersection/support rasters and summary.json.
The latter must have status complete and all products present. T is null when
unknown intersections remain. Preserve T bounds but do not turn them into a
probability interval without a separate accepted contract.

## Plan of Work


Milestone 1 establishes units and input policy. Verify Staley's calibrated Kf
convention against primary publication/source metadata and RUSLE's actual
formula/output. Use local reference PDFs lawfully; external verification uses
primary sources, not copied GPL implementation. Write a short unit audit with
an independent numeric example. If units or mapping cannot be established,
report the uncertainty; do not select a conversion from raster magnitudes.

Settle decision register P01–P06, distinguishing technical verification from
owner choices. Recommend artifact-only Nomograph readiness and conservative K
partial-coverage handling, but obtain acceptance before implementing those
workflow/scientific rules. Complete WEPP Soils remains required for production.
Freeze the local contract/signatures, schema and version, source validation,
error/availability vocabulary and parameterization ADR before code. No UI/NoDb/
RQ ancestor checkpoint is needed for this bounded local backend; any expansion
into those interfaces requires the full approved/reviewed/committed checkpoint.

Inventory real immutable project artifacts read-only, starting with canonical
run root `/wc1/runs` and existing terrain fixture manifests. No live rebuilds or
network acquisition are implicit. Establish that SBS, dNBR and K actually
cover the chosen watershed. Existing Arizona dNBR fixtures are not necessarily
co-located with the terrain panel. Use labeled synthetic fields for controlled
checks; do not present them as real M1 source evidence. Small committed fixtures
need rights/provenance and source hashes; do not duplicate large terrain files.
Write a brief additive compatibility/schema and downstream regression plan:
new caller-owned local bundle only, no mutation of RUSLE, Soils, Climate, saved
NoDb, WEPP run artifacts or old debris-flow outputs.

Milestone 2 prepares and invokes. Implement the narrow conversion/caller in
`integration.py` or a focused collaborator if needed for readability. Prefer
existing rasterio/GDAL compiled preparation and owned WBT execution patterns.
Construct numeric grayscale DEM/SBS/mask copies with exact grid/sample identity,
representable collision-free finite sentinels, explicit SampleFormat and the
supported classic TIFF layout. Preserve internal/external masks according to
a documented trusted-source input contract; reject unsupported sources explicitly.
Do not flatten SBS palettes to colors or replace missing SBS with unburned.
If SBS needs alignment, use the accepted categorical preparation contract and
verify target support; no silent K interpolation or DEM grid changes.

Enforce WBT's 10-million-cell and input-layout limits before dispatch. Pin and
validate the actual executable and its StaleySlopeSbs capability. Reuse owned
execution conventions, avoid shell-interpolated paths, and account for wrapper
cwd mutation without thread-unsafe global-directory changes. Execute with
`--elevation_units=m --sbs_classes=0,1,2,3` and record arguments, hashes and
outputs. Never fall back to generic Slope, FVSlope or Python raster traversal.

Milestone 3 composes. Run `summarize_dnbr` using the full watershed mask and
verify normalization manifest identity. Compute K mean/support using existing
owned compiled aggregation precedent, applying only the verified K mapping
and accepted coverage policy. Reuse the WBT T result without resummarizing a
rounded slope raster. Each predictor keeps its own full-domain denominator
and support. Missing T does not erase F/S diagnostics. Null predictors prevent
a single M1 probability. No automatic switch to M3 or likelihood-zero sentinel.

Write the versioned predictor/manifest bundle to a new local directory with
explicit processing completion separate from scientific availability. Preserve
original and prepared SHA-256 identities, raw-source intent, grid/outlet/area,
K configuration, tool version/binary hash and warnings. Check source hashes
before and after work; existing WBT FNV fingerprints alone do not establish
lineage or freshness. Distinguish input mutation, mismatched provenance and
missing provenance. Do not claim a stale artifact is current because its hash
can be computed. Define failure cleanup or visibly incomplete output retention,
never replacing existing products. No active run result is published.

Milestone 4 demonstrates and validates. Generate inspectable local bundle and
explicit 15/30/60-minute scenario examples through the existing scalar engine.
Inputs are rainfall accumulations in mm and already prepared T/F/S; no Climate
parquet conversion or frequency estimation in this increment. Carry the accepted
area warning. Real-project evidence must identify genuine input sources and
successful actual-binary output; synthetic evidence complements it and is labeled.

Tests cover complete T/F/S, valid zeros, negative normalized dNBR, partial and
empty dNBR, uncertain T with bounds, K partial/missing/invalid values under the
accepted policy, EPIC-only sources, malformed/stale/legacy provenance, grid
mismatch, sentinel collisions, palette/sample preservation, tool absence/failure,
truncated WBT output, mid-build source mutation and preexisting output protection.
Use direct file/binary tests for boundaries, not only mocked dispatch. Compare
source/prepared arrays and masks and independently check mean/intersection counts.
Keep SI/English display out of computations and preserve scientific units in
exports. Existing upstream gap-fill provenance must survive composition.

Obtain independent correctness and dedicated security reviews, close every
medium/high finding, run required validation and update canonical docs plus
roadmap. Record exactly what stage 3 local work is complete and which live
preparation/publication prerequisites remain. Archive this plan with outcomes
only when all accepted exit evidence exists. Do not modify closed predecessors.

## Concrete Steps


At WEPPpy root inspect `git status --short` and `git rev-parse HEAD`; preserve
unrelated changes and do not switch branches. Read applicable docs before edits.
Create focused tests at `tests/nodb/mods/test_postfire_debris_flow_integration.py`.
During iteration use:

    wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_integration.py --maxfail=1

Before handoff use:

    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow
    wctl doc-lint --path docs/work-packages/20260909_staley_m1_predictors
    git diff --check

Run applicable stub checks if API/stub surface changes. Record an exact
reproduction command/script and the actual executable path/hash in package
validation evidence; make the binary available in the test environment through
existing supported mounts/tooling, without production installation. If execution
crosses a container boundary, exercise real identity/mount permissions there.
No full tests or implementation are needed merely for this scaffold.

## Validation and Acceptance


A developer can reproduce a local M1 predictor bundle from prepared sources,
inspect independent coverage and source identities, and evaluate explicit storms
with the existing engine when T/F/S are available. Accepted incomplete states
produce readable diagnostics and no fabricated probability. At least one real
project source set and controlled edge fixtures have direct binary/file evidence.
If an authentic source is missing, record the blocked acceptance evidence and
continue independent tests without claiming real-project completion.

## Idempotence and Recovery


Inputs and existing outputs remain unchanged. New outputs have an explicit final
completion marker and documented failure/retry semantics. Repeat in a fresh
scratch directory; never repair source manifests silently, alter project caches
or trigger upstream builds. No run-scoped persisted schema migration is included.
Any production boundary expansion requires a new scoped compatibility/security
assessment and the applicable contract checkpoint before implementation.

## Artifacts and Notes


Expected evidence: K unit audit, source inventory and hashes, accepted decision
record/ADR, compatibility plan, reproducible generated bundle/scenarios,
validation, independent correctness and security review. Planned evidence does
not count as passed validation. Keep tracker and roadmap synchronized at handoff.

## Interfaces and Dependencies


Proposed local entry point: `build_m1_predictors(inputs, output_dir, *,
wbt_executable)`, with explicit immutable input paths/provenance and a typed
or documented result. Freeze exact input and result types in the canonical
contract before implementation; these are not HTTP/NoDb schemas. Reuse
`dnbr.summarize_dnbr`, `staley2017.probability`, owned WBT and compiled aggregation.
No new scientific model, automatic source fallback or external dependency.

Revision note: initial scaffold isolates local M1 composition and input-format
preparation from later production publication and climate/dashboard work.
