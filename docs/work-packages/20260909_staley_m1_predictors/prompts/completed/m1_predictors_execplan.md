# Compose prepared M1 watershed predictors


Completed 2026-09-09: local T/F/S acceptance passed; independent correctness and
security reviews have no open medium/high findings.

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes &
Retrospective. Execution requested 2026-09-09; engineering audit and candidate
inventory completed. Owner accepted P02/P03; local implementation and validation
are delivered. The rebuilt Wallow final assessment now supplies complete authentic
T/F/S evidence with zero unknown intersections.

## Purpose / Big Picture


A developer can supply prepared project artifacts to a local Python interface,
run the owned Horn/SBS backend and obtain a reproducible T/F/S bundle for the
existing watershed. The same bundle can drive explicit example storms through
the completed scalar M1 engine. Missing inputs remain visible rather than
silently becoming zeros or another model. This is working local integration;
production controllers, climate catalog, public upload and RQ remain separate.

## Progress


- [x] (2026-09-09) Audit K scale against primary references and scalar example.
- [x] (2026-09-09) Owner accepted P02/P03; freeze local contract and ADR-0059.
- [x] (2026-09-09) Inventory sources and write additive compatibility plan.
- [x] (2026-09-09) Implement lossless copies, actual WBT invocation and independent T/F/S.
- [x] (2026-09-09) Generate complete synthetic and authentic missing-dNBR bundles/scenarios.
- [x] (2026-09-09) Pass 50 focused actual-file/binary tests and close correctness findings.
- [x] (2026-09-09) Full suite: 8,016 passed, 72 skipped; API/stub/docs checks and final security review passed.
- [x] (2026-09-09) Obtain matching Wallow July 1 dNBR with archive lineage; verify read-only project evidence.
- [x] (2026-09-09) Demonstrate complete real T/F/S after owner rebuild with final polygon SBS and matching June 23 dNBR.
## Surprises & Discoveries


Execution baseline: WEPPpy `0cac0f3a03295075aa805240f7e5b7209e1e2042`,
WBT `a97abb7754a24390edf1d93f3f26a09d80b4669b`. Three real K candidates have
full numeric coverage, but two have legacy provenance. Available Arizona dNBR
fixtures do not overlap these projects. The later rebuilt Wallow assessment establishes a complete authentic M1 set.

Native rasters include palette/sample-layout differences and statistics-only PAM
metadata. The reproduction script materializes byte-identical TIFF copies outside
the project after checking PAM content and original/copy samples, masks and grids.
The runtime rejects auxiliary metadata. Original project hashes remain unchanged.
GDAL NoData comparisons can mask adjacent extreme floats: preparation now chooses
well-separated sentinels and verifies decoded masks. Independent review also
identified disguised VRT masks, worldfiles, companion-set mutation and insufficient
WBT/nested provenance validation; regression checks cover the corrections.
Historical July 1 Wallow follow-up: all 12,973 basin slopes are valid, but only 10,627 SBS cells
are valid. The 149 unknown steep intersections leave T unavailable. F and S
have full coverage; see `artifacts/wallow_evidence.json`.

## Decision Log


2026-09-09: owner answered "proceed as recommended" to the combined P02/P03
question. Adopt full usable K support without new filling, named Nomograph K
readiness independent of other RUSLE factors, and retained production WEPP Soils
prerequisite. ADR-0059 and the canonical M1 contract record rationale and exact rules.

P01 audit establishes multiplier 1. Missing legacy provenance yields unavailable
predictors with retained diagnostics; contradictory metadata is an error. Explicit
hashes establish bytes, not live upstream freshness. No server publication is added.

Retain failure artifacts with an incomplete marker; retry in a fresh directory.
Keep real missing-dNBR evidence distinct from synthetic complete evidence. Do not
archive this plan or mark stage 3 complete without authentic complete T/F/S evidence.
2026-09-09: owner selected the USGS Wallow archive and identified `woolen-refusal`.
Retain lossless June 23 final-severity fixtures separately from the project
July 1 preliminary BARC assessment. Use matching July 1 dNBR for project evidence;
do not substitute dates, fill SBS gaps, or mutate the project to force availability.

2026-09-09: after the owner rebuilt the project with final polygon severity,
select matching June 23 dNBR explicitly and verify the configured upload and
source-to-prepared SBS classes/masks. Keep July 1 results as historical evidence
rather than rewriting them to describe a different assessment.

## Outcomes & Retrospective


Local composition is implemented. Actual container-binary evidence yields synthetic
T=1, F=0.4000000059604645, S=0.3, with valid 15/30/60-minute scenario probabilities.
The authentic `strained-mod` domain has 80,949 cells, T=0.41419906360795067 and
S=0.338206766138312. F is unavailable (`missing_input`); probabilities remain null.
Original sources are unchanged. See `artifacts/generated_evidence.json` and
`artifacts/reproduce.py`; generated rasters remain under ignored `artifacts/generated/`.

Full validation passed (8,016 passed, 72 skipped); final focused suite passed 50
cases. API/stub/docs gates and both independent reviews passed, with no open
medium/high findings. Wallow now supplies authentic normalized dNBR; complete
real T acceptance is now satisfied by the rebuilt June 23 assessment; climate, M3 integration and
stage 5 production wiring remain successor work. Review findings are tracked in
separate correctness/security artifacts; planned evidence is never counted as passed.
Rebuilt Wallow closeout: T=0.1894704386032529, F=0.6141950971236625 and
S=0.43397823632668575, full support on all 12,973 cells. Explicit scenario
probabilities are available; the 11.6757 km² area warning is retained. Source
hashes remain unchanged. `artifacts/wallow_rebuilt_evidence.json` closes the local
authentic complete-source gate; no production publication is implied.

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
Record complete execution validation in `artifacts/validation.md`.

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

Execution revision 2026-09-09: record initial audit/inventory and explicit pending
owner policy gate; do not archive or claim implementation completion.

Execution decision: owner approved both recommendations. Frozen contract and
ADR-0059 precede code; continue all implementation and validation milestones.

Final execution revision 2026-09-09: local milestones and validation delivered;
retain active plan for authentic complete-source acceptance rather than archive
it prematurely. See `artifacts/validation.md` for commands, counts and limitations.

Closeout revision 2026-09-09: owner rebuild resolves SBS coverage; matched June 23
real-source evidence closes the local acceptance gate without changing runtime
policies or mutating the project.
