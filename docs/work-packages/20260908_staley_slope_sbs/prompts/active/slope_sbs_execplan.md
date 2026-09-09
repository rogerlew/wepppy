# Implement owned Staley slope and burn-severity intersection


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md` in
WEPPpy. Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes &
Retrospective. This request scaffolds the package; execution has not started.

## Purpose / Big Picture


A developer will run a rebuilt weppcloud-wbt tool through its CLI or either
Python binding to obtain surface slope, the steep/moderately-highly-burned
intersection and whole-watershed support statistics. These provide M1's terrain
predictor for an existing project watershed. The result is a working local
Rust backend with evidence, not an installed WEPPcloud model or new UI.

## Progress


- [x] (2026-09-09 05:08 UTC) Inspect initial science/code evidence and scaffold.
- [ ] Determine algorithm, surface, edge and support policy; finalize contract/ADR.
- [ ] Implement registered Rust tooling, bindings and synthetic tests.
- [ ] Run existing three-site terrain panel and inspect current-binary artifacts.
- [ ] Independent correctness/security reviews, validation and documented handoff.

## Surprises & Discoveries


Existing FVSlope measures drop toward the D8 receiver, not a neighborhood surface
gradient. WBT's projected generic Slope uses Florinsky 5×5, not Horn 3×3.
The inspected Staley manuscript establishes 10 m terrain and ≥23°, but no
explicit differentiation stencil. Horn/raw DEM is provisional; do not claim
original calibration parity. Initial web evidence and local source locations
are in `artifacts/slope_method_findings.md` in this package.

## Decision Log


2026-09-09 05:08 UTC: user requests slope/SBS tooling in weppcloud-wbt and
algorithm determination. Reuse the existing project watershed/outlet per
ADR-0055. No nested basin workflow, change to FVSlope, or production caller.
Codex recommends evaluating Horn 3×3/raw terrain; owner disposition of the
selected scientific parameterization and partial-support behavior is pending.

## Outcomes & Retrospective


Scaffold only. No Rust changes, tests, generated slope/intersection products or
deployment. Closure requires actual rebuilt-binary outputs and both bindings,
not only a report or surrogate Python implementation.

## Context and Orientation


Repositories: `/workdir/wepppy` and `/workdir/weppcloud-wbt`. Read each root
AGENTS and any nested instructions before work. WEPPpy's canonical proposal is
`wepppy/nodb/mods/postfire_debris_flow/docs/slope_sbs.md`; scientific authority
is its parent `specification.md`. The single project domain is valid positive
cells of `dem/wbt/bound.tif`, including channels, at the existing resolved outlet
in `dem/wbt/outlet.geojson`. The prior watershed audit in
`docs/work-packages/20260908_staley_watershed_engine/artifacts/` establishes
artifact mapping; do not amend that closed package or silently re-delineate.

The raw DEM is `Watershed.dem_fn`. WBT relief is conditioned terrain. Trace
`wepppy/topo/wbt/wbt_topaz_emulator.py` to confirm the actual FVSlope inputs/units.
Trace `Disturbed.sbs_4class_path`, `_sbs_map_args` and `SoilBurnSeverityMap` in
`wepppy/nodb/mods/baer/sbs_map.py` for class meanings. Landuse burn codes
130–133 do not establish normalized SBS encoding. A dNBR raster is not SBS.

WBT implementation references are `whitebox-tools-app/src/tools/terrain_analysis/slope.rs`,
`whitebox-tools-app/src/tools/hydro_analysis/fvslope.rs`, the existing
D8UpstreamRelief tool, and `DEVELOPING_TOOLS.md`. Register tools using existing
conventions and update `whitebox_tools.py` and `WBT/whitebox_tools.py`.
Do not add a new dependency, copy GPL pfdf code/tests or replace owned raster
processing with a Python implementation. Tiny independently derived analytical
test oracles and tabular summaries are acceptable.

M1 T is joint steep/burned area divided by the full watershed area; fractions
are 0–1 and the inclusive slope cutoff is 23 degrees. It is not the product of
independent slope and burn fractions. Final numerical evaluation already lives
in WEPPpy `staley2017.py`; use it for sensitivity scenarios with explicitly
fixed synthetic F/S and rainfall, without recalibration or production wiring.

## Plan of Work


Milestone 1 resolves method and contract. Read local Staley manuscript section 4,
section 5.2 and Table 4; inspect supporting primary references if they identify
the original preprocessing. The PDF is ignored under its redistribution policy.
Do not contact authors or send messages without user authorization. Bound this
investigation: if original method cannot be established, document the limit,
compare candidates and obtain an explicit engineering choice rather than block
indefinitely or claim inferred ArcGIS usage as fact.

The candidate is Horn's weighted 3×3 gradient: for neighborhood a b c / d e f /
g h i, gx=((c+2f+i)-(a+2d+g))/(8dx), gy=((g+2h+i)-(a+2b+c))/(8dy), slope is
atan(hypot(gx,gy)) in degrees. Recommend raw meter elevations on the full
project DEM, with valid center/eight neighbors, before applying the basin mask.
Compare published Esri planar missing-neighbor behavior separately; generic
GDAL Horn and Esri are not interchangeable at gaps. Current generic WBT Slope
must retain its default for all existing callers. Prefer a dedicated tool or
explicit additive method only after documenting the smallest supported design.

Resolve register S01–S05. In particular, decide whether partial intersection
support permits a point T or only bounds/unavailable. Provide count diagnostics
regardless. Known low/unburned SBS or slope below threshold proves a false
intersection even when the other operand is missing; otherwise propagate
unknown. Never silently renormalize to observed support or zero-fill. No
arbitrary minimum coverage percentage or M1 resolution gate is authorized.
Record the selected method, DEM source, edges, units, class mapping and support
rules in the canonical contract and next available parameterization ADR before
implementing dependent executable behavior. Keep source findings separate from
accepted engineering decisions. Any UI/NoDb/RQ expansion needs the repository's
separate contract-first checkpoint and is not part of this package.

Milestone 2 implements a bounded Rust backend. Freeze registered tool names,
CLI flags, return/output schema and both binding methods in WBT's new
`docs/staley_slope_sbs.md` and the WEPPpy canonical contract first. Proposed
logical inputs: raw DEM, aligned categorical SBS, existing watershed mask,
explicit class mapping/elevation units, and fresh output paths. Proposed outputs:
slope in degrees, three-state intersection/support, and a summary containing
full-area and support counts, bounds, approved T availability, source hashes,
parameters and tool version. Select one tool or a small reusable pair; avoid
a general expression framework. Do not introduce silent warp/resampling.

Validate exact CRS/transform/shape, declared vertical units, mask membership,
recognized SBS classes, finite data, supported raster format and resource bounds.
Require north-up square projected-meter grids initially unless existing owned
support and tests justify more. Freeze nodata/dtypes and behavior for bad paths,
existing outputs and mid-write failures. Preserve source files and previous
outputs; stage products before reporting success. Retain independently useful
SBS-only support/counts for later M3 without making M3 depend on slope validity.

Milestone 3 proves the method on synthetic and existing terrain. Planes in
multiple azimuths must recover analytical gradients and reveal the directional
FVSlope distinction. Test 23° and just-above/below classification using full
precision, flat planes, ridges, pits, missing neighbors, raster edges, missing
SBS, known false with one missing operand, invalid classes, misaligned grids,
empty masks, unit mistakes, and failure preservation. Include an example where
separate burned/steep fractions are identical but spatial overlap differs.
Check deterministic counts and numerator/denominator identities.

Use `/workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution/` for Moscow
Mountain, Topanga and Arizona ponderosa, 10 m and 30 m, using only main project
outlets. Preserve their raw DEMs, routing, masks and boundaries unchanged.
Inventory actual SBS availability; synthetic categorical patterns are adequate
for controlled method comparison but must be labeled synthetic. If real SBS
fixtures are acquired, establish rights/provenance and actual spatial overlap;
never reinterpret the existing Arizona dNBR as SBS. Commit small reproducible
fixtures; reuse existing terrain rather than duplicate large files.

Compare Horn, Florinsky and FVSlope on the same DEM/grid/support first; compare
raw versus conditioned terrain separately. Pin versions/flags and convert all
slopes to a common unit. Report threshold-crossing counts, T deltas, unavailable
support and probability deltas for fixed explicit F/S/rainfall through the
existing engine. Native 10/30 m extents differ: report basin-level contrasts
with area/outlet context, not naive raster subtraction. No predictive accuracy
or universal resolution acceptance follows from these method comparisons.
Record wall time and memory on the real panel; raster traversal remains Rust.

Milestone 4 validates and closes. Run current-binary CLI and both Python
bindings on analytical and at least one real-terrain fixture; record exact
binary hash and invocation. Obtain separate independent correctness and security
reviews with artifacts; close all medium/high findings. Update WBT CHANGELOG,
tool docs, relevant tracker and WEPPpy specification/roadmap in the same work.
Report backend implementation separately from deployment/install status. Do
not mark all of stage 3 complete: K integration, dNBR composition and production
predictor orchestration remain successor work.

## Concrete Steps


At both repository roots inspect `git status --short` and `git rev-parse HEAD`;
record revisions and preserve unrelated changes. Read WBT DEVELOPMENT guidance
and the chosen tool precedent before adding Rust or binding code. Do not switch
branches. At WBT root use:

    cargo check -p whitebox-tools-app
    cargo test -p whitebox-tools-app
    cargo build --release -p whitebox-tools-app
    python -m py_compile whitebox_tools.py WBT/whitebox_tools.py

Record the resulting executable path and its hash, verify tool discovery and
run the finalized CLI through both bindings. Use package-local evidence/scripts
for reproduction. At WEPPpy root, after any executable helpers/tests are added:

    wctl run-pytest tests/nodb/mods --maxfail=1
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow
    wctl doc-lint --path docs/work-packages/20260908_staley_slope_sbs
    git diff --check

Narrow the iteration command to the actual new test file once named. Capture
commands and results in `artifacts/validation.md`; no tests are required merely
for this documentation scaffold. Do not install a binary into live containers.

## Validation and Acceptance


A fresh agent can reproduce slope/intersection/summary files with the rebuilt
owned binary and both wrappers. Analytical gradients meet declared tolerances;
threshold classifications and integer counts meet exact expectations except
explicitly documented floating-point boundary cases. Valid zeros are distinct
from missing. Partial inputs expose support and follow the approved policy.
Same-grid independent Horn comparisons distinguish interior and gap behavior.
The three-site report supports the algorithm recommendation without claiming
original calibration parity. Security tests directly exercise filesystem/input
validation; mocks alone are insufficient evidence of boundary correctness.

## Idempotence and Recovery


Use fresh scratch/output directories and immutable source fixtures. Rejected
inputs and failed writes preserve existing products. Re-running comparisons is
safe and documented. Do not modify live projects or archived work packages.
Any interrupted multi-artifact run must remain visibly incomplete and retryable;
finalize that contract before implementation. Public uploads and NoDb publication
are not authorized by these local trusted-path interfaces.

## Artifacts and Notes


Retain slope-method findings, accepted ADR link, class/source inventory, command
and binary hashes, analytical results, three-site comparison CSV/report,
validation and both review artifacts. Update tracker and roadmap at each handoff.
Archive this plan only after working-backend acceptance, with outstanding
production integration stated. No source fixtures or full copyrighted papers
may be copied from GPL pfdf or redistributed without established rights.

## Interfaces and Dependencies


WBT owns Rust raster computation, tool registration and both bindings. WEPPpy
owns the scientific integration contract and later prepared input selection.
Reuse whitebox-raster and existing serialization utilities. GDAL is an offline
comparison/preparation precedent, not an added runtime fallback. Final public
names/types must be explicit in milestone 1; no production payload or persisted
NoDb schema is introduced. References live in the findings artifact and current
contract; closed packages provide evidence only.

Revision note: initial scaffold separates surface-slope selection from D8
routing slope and bounds delivery to the single-watershed slope/SBS backend.
