# Production M3 and shared analysis support

Status: accepted and implemented 2026-09-14. Analysis support, soil-builder
isolation and ADR-0067 recorded depth are owner-approved. Bounded acquisition
was separately authorized and executed; the runtime reader still consumes
prepared inputs without network in its numerical adapters. The
[Run-preparation amendment](production_m3_runtime.md#2026-09-15-run-preparation-amendment)
requires explicit Run M3 to prepare absent source pointers before calculation;
orchestration and fresh-basin live validation pass. Development M1/M3 RQ and browser checks pass,
including positive synthetic M3 and genuine terrain-unavailable results.
This amends the [selection contract](model_selection.md) and
[production workflow](production_m1.md); production deployment is not implied.

## Accepted analysis support

The project watershed and outlet remain the assessment boundary. Analysis
support means the cells contributing to predictor averages and fractions.
Missing required observations are excluded, never replaced with zero. Valid
unburned cells remain included. Use one shared support per model:

- M1: watershed cells with a determined Horn slope/SBS intersection, valid
  normalized dNBR and valid provenance-backed RUSLE Nomograph K. Compute T as
  the steep-and-moderately/highly-burned fraction of this support, F as its mean
  normalized dNBR, and S as its mean K. Preserve existing encoding and units.
- M3: watershed cells with valid SBS and usable soil thickness after explicit
  SSURGO-primary/original-STATSGO-THICK fallback. F is the moderate/high fraction
  of this support; S is its mean thickness in cm divided by 254.
- M3 T retains the accepted full-upstream relief divided by square root of
  full contributing-basin area, in consistent length units. Masking SBS/soil
  does not change routing, relief extrema, outlet or ruggedness area. Invalid
  terrain cannot be repaired by shrinking the soil/SBS mask.

The common support prevents predictors describing different observed portions
of the basin. This is an explicit departure from complete-area calibration
inputs when coverage is partial; it does not establish representative sampling
or compensate for systematically missing steep/burned areas. Retain full
watershed area for study-size warnings. No minimum coverage cutoff is approved;
zero usable support produces unavailable probabilities with reasons.

Publish `valid_mask.tif` on the project grid as UInt8: 1 used, 0 excluded inside,
255 NoData outside. Report total, valid and excluded cell counts plus unrounded
valid fraction. Display **Valid coverage**, with sufficient precision to reveal
nonzero exclusions, counts, the explanation “Estimates use the area with usable
inputs,” and the mask download using existing summary/table/link conventions.
Coverage is spatial input coverage, not probability confidence. Component
completeness is separate, because soil components are not located within a
map-unit pixel. Do not portray a component percentage as a mapped exclusion.

ADR-0066 governs this accepted direction. The original raw WBT three-state
outputs and version-1 offline study results keep their semantics. New production
predictor/result provenance must identify the support policy; legacy results
without coverage say it was not recorded. Never rewrite earlier probabilities
or claim they used this mask.

## Protect existing soil building

M3 is a downstream, read-only consumer of existing Soils inputs. This package
must not change `Horizon.valid`, WEPP component selection, parameter estimation,
restrictive-layer clipping, SSURGO/STATSGO build fallback, donor assignments,
cache schemas/defaults/refresh, `.sol` output, or generated WEPP soil inputs.
Do not invoke Soils builds, cache initialization/clearing, or builders merely
to read horizons. In particular, `statsgo_tabular_cache.sqlite` is not the
original 1995 THICK raster and cannot silently replace it.

Keep M3 orchestration and policy in this module. Reuse `soil_thickness.py`
through an explicit production policy/adapter; preserve existing offline
defaults and results. Do not add a parallel parser or repurpose `.sol` depth or
`SurgoSpatializer.SolThk`. If a shared-code change proves necessary, retain the
failing evidence and seek separately scoped authority before making it.
M3 rejection must never make a previously buildable WEPP soil unbuildable.

Read raw map-unit keys and their provenance, not donor keys chosen to make WEPP
profiles buildable. A substituted WEPP assignment does not invalidate authentic
raw horizons still available for the original spatial key; neither may it be
misrepresented as original soil. Audit this distinction against actual project
rasters before wiring source selection.

## Accepted soil decisions

The [soil evidence assessment](ssurgo_validity_assessment.md#production-research-2026-09-14)
records source findings. The paper needs cumulative layer thickness, not root
zone depth or depth to a hydraulic restriction. ADR-0067 rules are:

1. Use raw representative top/bottom depths in cm; preserve source keys,
   intervals and validation reasons. Do not reject depth solely because texture,
   conductivity or CEC is missing. No default profile extension or gap filling.
2. Include ordinary soil/organic layers, documented H and weathered Cr;
   exclude explicit terminal hard R and retain unknown/mixed-R diagnostics.
   The owner rejected `strict_soil` as a production policy on 2026-09-14.
   NRCS NSSH 618.38(C)(2) documents legacy H layers in approved map units;
   H designation alone must not be treated as unknown rock. The replacement
   in accepted ADR-0067 uses recorded depth including H/Cr, explicit R
   exclusion and audited disagreement with separate thickness fields.
   Independent analytical, raw-cache and production composition tests pass.
3. Recognize documented paired horizons without double-counting thickness;
   distinguish those from conflicting duplicate keys and unexplained overlap.
   Do not silently accept every overlap by taking its union.
4. Normalize component-percentage-weighted means over positive usable weights,
   disclosing omitted weights. Totals above 100 alone are not corrupt;
   individual invalid weights reject the map-unit estimate. Do not impose complete-only
   usability or infer component completeness from raster coverage.
5. Prefer usable SSURGO map-unit estimates at each project cell, otherwise use
   aligned original STATSGO THICK there. Use nearest-neighbor sampling; avoid
   replacing the entire catchment or mixing unlocated component gaps with a
   coarse raster estimate. Disclose component support separately. Unusable
   both-source cells are excluded, never treated as zero.

Accepted ADR-0067 and the runtime contract fix the exact rules and uncertainty.
Neither mapping detail nor agreement with
STATSGO establishes predictive accuracy. This package preserves source priority.

## Runtime and compatibility requirements

Keep the existing M1/M3 selector, endpoints and dedicated RQ tasks. Replace M3's
`integration_pending` only with actual soil/terrain/rainfall composition. Require
configured 10 m `ned13/2022`, actual aligned grids, built WEPP Soils and an
explicit thickness-source inventory; M1 has no new resolution or Soils gate.
No M3 dependency on dNBR or RUSLE K. Keep current rainfall durations, sources,
design intervals and inverse targets. No new report or dashboard in this package.

Before runtime edits, specify exact source delivery and freshness: existing
read-only project caches, original spatial keys, survey/source versions, aligned
STATSGO window, DEM/routing/outlet, SBS and policy/binary identities. Inventory
missing legacy/custom caches and installed THICK availability. Existing source
priority is not authority for implicit network acquisition, cache mutation or
a live Soils rebuild. Any required new acquisition must have an explicit bounded
source/destination/error contract and authority before implementation.

Snapshot SQLite content consistently, including committed WAL content; never
copy only the main database or mark a live WAL database immutable. Do not change
source journal mode, checkpoint it, or migrate schema. Use existing persistence
contracts and stable read snapshots; source changes during execution must prevent
stale publication. Preflight stays bounded and read-only; no raster computation
or network work during state refresh.

Publish accepted model files directly in `postfire_debris_flow/`, including the
mask. Keep source subsets, soil thickness/source maps, component/map-unit audits,
terrain diagnostics, logs and failed attempts in visible module directories.
Capture exact source contribution and fallback reasons in the manifest; a
successful fallback remains visible. Preserve accepted results on failed
replacement. Downloads, normal browser and archives must include these records.

Evolve result/NoDb schemas additively and version changed numerical semantics.
Legacy missing model means M1. Reuse checks must reject predictors built under
the old support policy; model selection must not relabel results. Freshness is
model-specific, and 🌋 still describes the latest accepted result. New summaries
honor SI/English display without changing canonical numerical units.

## Implementation and regression evidence

The [active package](../../../../../docs/work-packages/20260914_staley_m3_integration/package.md)
specifies the checkpoint, soil-builder protection matrix, real WBT output,
large-10 m development browser/RQ acceptance and independent reviews. Both
complete-support M1 parity and partial-support changed behavior must be checked.
No live production deployment is part of this scaffold.
## Scientific integration amendment — 2026-09-14

For new production execution, [the runtime integration contract](production_m3_runtime.md)
and accepted ADR-0067 govern model-specific common support, recorded-depth soil
policy, version-2 predictors and mask publication. Existing local/offline v1
semantics remain reproducible. Runtime composition is implemented and tested;
source acquisition retains separate bounded authority and deployment is excluded.

## Kf source amendment — 2026-09-16

Status: accepted 2026-09-16 after two independent reviews; implementation
conformance verified on forest, 2026-09-16. The [Kf source/runtime contract](kf_source.md)
is the controlling amendment for new production M1.

Only shared new-M1 composition/readers change; M3 recorded-depth sources, preparation and schema-2 behavior remain unchanged.
Earlier conflicting requirements remain the historical/legacy contract only
once this checkpoint is accepted; do not reinterpret old accepted artifacts.
