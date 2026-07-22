# Execute the SSURGO Intelligent Fallback Empirical Study

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be maintained as work proceeds. Follow `docs/prompt_templates/codex_exec_plans.md` when revising it.

## Purpose / Big Picture

This work gives maintainers measured evidence about the SSURGO MUKEYs that do
not produce a WEPP soil. After the work, a maintainer can distinguish the
mapped-area impact from the unique-MUKEY prevalence, see what input is absent
or physically inconsistent, and design a local map-based fallback without
guessing. The work is research-only: the current production fallback remains
unchanged.

## Progress

- [x] (2026-07-21 18:07 UTC) Inventory the complete 2025 gNATSGO VAT.
- [x] (2026-07-21 18:15 UTC) Run and report a 2,048-draw mapped-area pilot.
- [x] (2026-07-22 01:59 UTC) Run canonical study-tool tests after container
  restart: 3 passed.
- [x] (2026-07-22 02:35 UTC) Run and validate 12,288 mapped-pixel draws with
  the current converter.
- [x] (2026-07-22 02:39 UTC) Run and validate 2,048 uniformly sampled
  distinct-MUKEY draws and report it separately from the mapped-area result.
- [x] (2026-07-22 03:14 UTC) Execute a representative clustered-window
  benchmark through the freshly built native extension; it is research tooling
  and is not wired into fallback selection.
- [x] (2026-07-22 03:28 UTC) Milestone 1: return local candidate pixel support
  and prove it with deterministic raster fixtures (five targeted Rust tests).
- [x] Milestone 2: add a shadow-only WEPPpy collector that clusters invalid
  MUKEY bounds and persists proposed local-majority evidence (2026-07-22).
- [x] Milestone 3: evaluator, deterministic GeoTIFF fixture corpus, and a
  read-only 298-case representative-run cohort complete (2026-07-22).
- [ ] Milestone 3.5: evaluate failure-class-aware, per-candidate heuristic
  scoring with contact-aware map geometry and aligned terrain; research only.
- [x] Milestone 3.5 geometry/terrain slice: execute 0%–30% terrain variants
  against 298 read-only masked-valid cases with NED1 (2026-07-22).
- [x] Milestone 3.5 failure-class fixture slice: add deterministic profile
  gates, explicit global-fallback controls, and classifier coverage for the
  dominant `no_components`/`no_horizons` classes (2026-07-23).
- [x] Milestone 3.5 held-out check: execute four independent local runs (29
  masked-valid cases) and retain the unfavorable/non-discriminating result
  rather than selecting a heuristic winner (2026-07-23).
- [x] Milestone 3.5 ranked candidate-set slice: measure top-1/top-2/top-3
  and local-oracle evidence across the original and held-out cohorts
  (2026-07-24).
- [x] Milestone 3.5 larger cohort: execute ranked-candidate diagnostics on 18
  additional runs (322 cases), including a one-worker deterministic repeat
  (2026-07-25).
- [ ] Milestone 4: seek an ADR only if evidence supports opt-in production
  selection, then observe a shadow/opt-in rollout before default promotion.
- [ ] Add deterministic fixtures for all observed primary failure classes.
- [ ] Build and evaluate raster-region/elevation candidate evidence using
  masked-valid trials.

## Surprises & Discoveries

- Observation: the companion gNATSGO VAT contains complete MUKEY pixel counts.
  Evidence: it reports 320,669 MUKEYs and 8,745,483,151 mapped pixels; using
  it completed in about five seconds, whereas the full GeoTIFF block scan
  allocated substantial GDAL cache memory.
- Observation: five apparent worker failures were converter data-quality
  failures.
  Evidence: direct reproduction raised `ValueError` because texture fractions
  implied negative silt; four cases combined defaulted/missing sand with high
  clay and one had measured sand plus clay above 100%.
- Observation: the expanded mapped-area result agrees with the pilot.
  Evidence: 244 of 12,288 draws were unbuildable (1.99%; Wilson 95%
  1.75%–2.25%), compared with 1.95% in the pilot; no cohort draw failed NRCS
  data access.
- Observation: the existing raster-characteristics APIs read complete rasters.
  Evidence: `Raster::<i32>::read()` loads `(0, 0, width, height)` before the
  existing public aggregations; Phase 2 therefore has a separate GDAL-window
  path with worker-local handles.
- Observation: bounded worker concurrency materially reduced this synthetic
  clustered workload's wall time.
  Evidence: 16 adjacent 90 m-wide clusters around a mapped gNATSGO pixel read
  6,400 pixels and completed in 174.344 ms (one worker), 85.852 ms (two), and
  46.784 ms (four); every cluster found its deliberately supplied valid MUKEY.
- Observation: contact-aware geometry outperformed the crop-majority baseline
  on the first scoring cohort, and terrain changed a material subset of donor
  choices without making evaluation nondeterministic.
  Evidence: geometry-only had 131 local feature-distance wins versus 58 global
  wins; the 30% terrain variant had 140 versus 62. A 295-case repeat produced
  equal result records at one and four workers in 6.08 s and 4.94 s.
- Observation: `exhausted` must distinguish an unresolved search from a
  successful search that happens to use the maximum permitted radius.
  Evidence: the fixture corpus initially exposed `exhausted=True` for a
  successful one-radius query; the native contract now reports exhaustion only
  when the candidate minimum was not met at the maximum radius.
- Observation: the first cohort's geometry/terrain advantage does not
  generalize to the next four available independent runs.
  Evidence: 29 held-out cases yielded 2 local wins, 3 global wins, and 24 ties
  for geometry-only; terrain variants produced at most 2 local wins.
- Observation: candidate discovery and ranking are separable limitations.
  Evidence: in 298 cases, the local oracle beat global 183 times versus 131
  top-one wins; in held-out data it beat global 6 times versus 2 top-one wins,
  while all three `feline-wrangler` cases had no local candidate better than
  global.
- Observation: ranked-candidate headroom persists in a substantially larger
  cohort and grows with candidate-set size.
  Evidence: among 322 cases, local top one beat global 165 times, the local
  oracle 275 times, and global beat all local candidates 11 times. The
  one-worker and four-worker records/aggregates were exactly equal.

## Decision Log

- Decision: Use 12,288 independent mapped-pixel draws and a separate
  2,048-draw unweighted-MUKEY cohort.
  Rationale: the 2,048-draw pilot observed 40 unbuildable draws. The expanded
  mapped-area cohort targets about 240 such draws and approximately ±0.25
  percentage-point 95% precision, while an unweighted cohort exposes rare
  MUKEYs hidden by area weighting.
  Date/Author: 2026-07-22 / user and Codex.
- Decision: Keep source-data access, converter worker failure, and
  residual-invalid profile outcomes distinct.
  Rationale: NRCS outages are not soil quality, and converter failures may be
  repair candidates rather than donor-selection cases.
  Date/Author: 2026-07-21 / Codex.
- Decision: Query clustered invalid MUKEYs by supplied local bounds rather
  than constructing national MUKEY regions or querying individual MUKEYs.
  Rationale: a MUKEY has disconnected national occurrences, while final-run
  invalid MUKEYs are spatially close; one bounded crop therefore serves the
  adjacent group without a national scan.
  Date/Author: 2026-07-22 / user and Codex.
- Decision: Record exact withheld-MUKEY recovery as a diagnostic, but use
  declared soil/WEPP feature distance as the primary later interpretation
  metric.
  Rationale: a spatially local donor can be a good parameterization substitute
  without matching the original MUKEY identifier exactly. No promotion
  threshold is set by this decision.
  Date/Author: 2026-07-22 / user and Codex.
- Decision: Keep the deterministic GeoTIFF corpus in Git LFS even though the
  initial rasters are small.
  Rationale: the corpus is expected to grow with representative map windows;
  storing its raster artifacts through the same clone/pull path avoids a later
  fixture migration.
  Date/Author: 2026-07-22 / user and Codex.
- Decision: Hold Milestone 4 rather than propose an ADR from the first
  representative masked-valid cohort.
  Rationale: local candidates were elevation-closer in 235 of 298 cases and
  had lower unweighted WEPP-feature distance in 108 versus 71 cases, but this
  is only two local runs and no practical-effect threshold or production score
  has been declared.
  Date/Author: 2026-07-22 / Codex.
- Decision: Evaluate hierarchical heuristic scoring as the next research
  policy family.
  Rationale: case-by-case review found that local-window support, retained
  profile evidence, and terrain are distinct signals whose availability varies
  by failure class. Weights are hypotheses to compare on held-out runs, not a
  production parameterization decision.
  Date/Author: 2026-07-22 / user and Codex.
- Decision: Select NED 1 arc-second 2024 as the external terrain source for
  scoring experiments.
  Rationale: it matches the approximately 30-m SSURGO scoring grid; NED13
  adds remote I/O and resampling without useful additional terrain detail for
  this categorical-map experiment.
  Date/Author: 2026-07-22 / user and Codex.
- Decision: Gate profile use by failure class and keep the initial 55/30/15
  profile/geometry/terrain blend fixture-scoped.
  Rationale: `no_components` and `no_horizons` retain no trustworthy profile
  evidence, while nonphysical texture must not contribute texture-derived
  fields. The blend makes the partial-profile fixture inspectable without
  turning an uncalibrated research value into a production default.
  Date/Author: 2026-07-23 / Codex.
- Decision: Retain M4 as HOLD after the held-out check.
  Rationale: the four held-out runs do not show a stable improvement over the
  current global baseline, and no observed-invalid provenance review or ADR
  confidence gate exists.
  Date/Author: 2026-07-23 / Codex.
- Decision: Evaluate ranked local candidate sets before modifying candidate
  discovery or tuning another weight matrix.
  Rationale: top-k and oracle comparisons identify whether a failure comes
  from an inadequate local set, an inadequate ranker, or a baseline donor that
  is already locally available. A raw score margin is recorded for later ADR
  calibration; no confidence threshold is selected here.
  Date/Author: 2026-07-24 / user and Codex.
- Decision: Preserve zero-eligible runs in the larger cohort manifest.
  Rationale: a zero-case run is evidence about cohort applicability and must
  not disappear from an aggregate through an implicit exclusion. It is not
  evidence for or against a donor policy.
  Date/Author: 2026-07-25 / Codex.

## Outcomes & Retrospective

The expanded and representative masked-valid cohorts are complete but the
package is not. The mapped-area
cohort found 244 unbuildable draws of 12,288 (1.99%; Wilson 95% 1.75%–2.25%):
211 residual-invalid and 33 nonphysical-texture worker failures. The separate
uniform-MUKEY cohort found 49 of 2,048 (2.39%; Wilson 95% 1.81%–3.15%): 46
residual-invalid and three worker failures. No source-data access failures
occurred. Fixture and masked-valid candidate evidence remain necessary before
proposing a policy. The masked-valid cohort queried 298 hillslopes across two
local runs; all found a local candidate at 250 m. Local candidates were better
on the declared unweighted WEPP-feature distance in 108 cases, global donors
were better in 71, and 119 tied. Local donors were elevation-closer in 235
cases versus 62. This is directional evidence only; Milestone 4 remains HOLD.

The scoring corpus now proves failure-class evidence exclusion and explicit
fallback behavior without production writes. The subsequent 29-case held-out
check did not reproduce the first cohort's improvement. The next evidence
step is therefore a larger geographically separated masked-valid cohort and a
stratified observed-invalid provenance review, not an ADR or production shadow
rollout.

The ranked candidate study adds a concrete intermediate diagnostic. The first
cohort has substantial ranking headroom, while the held-out cohort contains
both rank misses and a local-candidate-discovery miss. M4 stays HOLD until a
larger geographic cohort establishes whether a shortlist, an abstention gate,
or broader candidate rings improve the relevant stratum.

The 322-case larger cohort confirms that top-k/oracle diagnostics are useful,
but it still does not choose a production shortlist length or score margin.
The next research slice should compare a bounded broader candidate ring only
for local-oracle misses and retain global fallback as the explicit baseline.

## Context and Orientation

`wepppy/nodb/core/soils.py` currently maps each hillslope's raw dominant MUKEY
to the watershed's most common valid MUKEY when its own conversion fails.
`wepppy/soils/ssurgo/ssurgo.py` retrieves component/horizon rows from NRCS Soil
Data Access and makes a `WeppSoil`. A residual-invalid MUKEY is one that still
has no valid `WeppSoil` after the current defaults and estimators; it is not
merely a row with a blank source field.

The source map is
`/wc1/geodata/ssurgo/gNATSGSO/2025/gNATSGO_mukey_202502.tif`. Its companion
`.tif.vat.dbf` attribute table contains a `mukey` and a `Count` column. A
mapped-pixel draw chooses a pixel uniformly from those counts, so its result
estimates the proportion of mapped area. A uniform MUKEY draw chooses from the
320,669 distinct MUKEYs with equal probability, so it estimates the prevalence
among map units instead.

The research CLI is `tools/ssurgo_empirical_study.py`; its version-1 diagnostic
records require identity, outcome, failure evidence, raw-data completeness,
retained feature availability, and repair provenance. Raw records go under
`/tmp/ssurgo_empirical_study_20260721/` and are not committed. Aggregate
findings belong in
`docs/investigations/2026-07-21-ssurgo-intelligent-fallback-pilot/README.md`.

## Plan of Work

Phase 2 proceeds in four independently verifiable milestones. Milestone 1
extends `wepppyo3/raster_characteristics` so the smallest successful window
returns `mukey -> pixel_count`, not merely membership. Its synthetic GeoTIFF
fixtures prove expansion, valid filtering, support counts, exhaustion, and
stable MUKEY tie order. This is a native research kernel only.

Milestone 2 adds additive, nullable shadow evidence in WEPPpy. It groups
nearby invalid MUKEY bounds before calling the native kernel and records the
cluster, candidate counts, proposed local-majority MUKEY, and present global
fallback. It never changes the final assignment.

The shadow mapping is `Soils.ssurgo_candidate_shadow_d`, keyed by string
TOPAZ ID, with legacy hydration default `{}`. Each entry records raw MUKEY,
cluster identifier/bounds, 250 m initial search radius and final radius,
ordered local `(mukey, pixel_count)` support, proposed local-majority MUKEY,
current global replacement, and exhaustion/reason. `soils/soils.parquet` gains
matching nullable additive columns. Existing final maps and current
substitution provenance are immutable to this computation; tests must show old
NoDb hydration and unaffected parquet columns retain their behavior.

Milestone 3 runs masked-valid fixtures and representative run cohorts. The
comparison is the current watershed-global dominant MUKEY versus the valid
MUKEY with the greatest count in the smallest successful local window; equal
counts break by numeric MUKEY. It reports availability, disagreement,
determinism, and withheld-soil similarity.

### Milestone 3 Evaluation Scaffold

Milestone 3 is read-only. A masked-valid case starts with a successfully built
raw dominant MUKEY, removes that MUKEY from the valid candidate set for the
query, and compares the shadow local-majority proposal with the current
watershed-global dominant baseline. It writes a versioned evaluation row with
the withheld MUKEY, cluster bounds, candidate support, both proposals, and
their available soil/WEPP summary values. It never changes `domsoil_d` or
generates a new model run.

The fixture corpus includes direct local success, expansion, tie, no-local
candidate, and geographically separated clusters. Its GeoTIFF files live in
`tests/data/ssurgo_masked_valid/`, are tracked by a directory-local Git LFS
rule, and are exercised through the public native binding with two workers.
Representative local runs are read-only evidence sources and are never test
dependencies. Results are stratified by fixture class and run, not pooled into
a production claim.

The scaffold records exact withheld-MUKEY recovery and distance on declared
soil/WEPP summary features. Because masked-valid trials remove the withheld
MUKEY from candidate eligibility, exact recovery is not interpretable in this
protocol. Feature/WEPP similarity and aligned elevation comparison are the
usable diagnostic evidence. No observed improvement threshold is set before a
future ADR.

### Milestone 3.5 Scoring Experiment

Milestone 3.5 is read-only and does not change `domsoil_d`. It introduces a
WEPPpyo3 bounded-window geometry query keyed by individual source requests,
not by a coalesced hillslope group. For every source request it returns valid
candidate pixel support and four-neighbor shared raster-edge count separately.
Support is local-window prevalence; it is never labeled or scored as shared
boundary contact. The query remains worker-concurrent and reads only bounded
crops.

The first scoring experiment applies only source-local geometry and terrain to
otherwise valid masked MUKEYs. It compares geometry-only and 0%, 10%, 20%, and
30% terrain-weight variants; profile scoring waits for fixtures that preserve
only the source fields available to each partial-invalid failure class. The
geometry component prefers normalized shared edge and falls back to normalized
local support only when no candidate shares an edge. The terrain component is
rank-normalized source-to-candidate elevation difference. These are research
variants, not production weights.

Terrain queries use `/wc1/geodata/ned1/2024/.vrt` when an external source is
needed. NED 1 arc-second is the selected source because its approximately
30-m resolution matches the study grid; NED13 adds resampling and remote I/O
without adding information at this scale. Run-aligned DEMs remain the
hermetic fixture and local-run source; a NED1 query must record CRS,
resampling, source path, and NoData behavior.

Acceptance requires deterministic geometry fixtures for edge-versus-support,
corner/no-edge, per-source results in a coalesced crop, elevation
disambiguation, missing DEM, and stable ties. Report every component and score
variant on held-out runs. Any no-edge/no-terrain or insufficient-margin case
retains the explicit global fallback in a future production policy.

Milestone 4 is conditional. A parameterization ADR is required before any
production threshold or selection order changes. If approved, the policy is
first shadowed or opt-in with preserved global fallback and explicit rollback.

First, run the expanded mapped-area cohort from the VAT population with a fixed
seed and bounded batches. Reuse the current converter settings (`initial_sat`
0.75, `ksflag=True`) and capture every worker exception separately. A retry
must never change a completed record's outcome; it should resume only missing
MUKEYs and record its source date.

Second, construct the unweighted cohort by deterministic random sampling of
distinct VAT MUKEYs. Do not combine its rate with the mapped-area rate. For
each cohort, validate JSONL through the research CLI, calculate outcome and
reason-code counts, and use a Wilson interval for the combined unbuildable
proportion. Report data-access failures separately and do not count them as
soil invalidity.

Third, update the investigation report and this plan with both cohort results.
Then build small no-network fixtures that represent no component, no horizon,
missing required attributes, and nonphysical texture balance. The fixtures must
prove the classifier, not change converter validity.

Finally, create map-region adjacency from the SSURGO raster and pair it with an
explicitly aligned elevation raster. Mask otherwise valid MUKEYs, compare
candidate policies, and retain the global fallback as a baseline. A later ADR
is required before any production score, threshold, or selection order changes.

## Concrete Steps

Work from `/home/workdir/wepppy`.

1. Verify the study tool before each cohort:

       wctl run-pytest tests/tools/test_ssurgo_empirical_study.py --maxfail=1

   Expect three passing tests.

2. Create or reuse the complete inventory:

       .venv/bin/python tools/ssurgo_empirical_study.py inventory \
         --raster /wc1/geodata/ssurgo/gNATSGSO/2025/gNATSGO_mukey_202502.tif \
         --output /tmp/ssurgo_empirical_study_20260721/gnatsgo_2025_mukey_inventory.json

   Expect `inventory_method` to be `raster_attribute_table`, `complete` to be
   true, and the known 2025 MUKEY/pixel counts.

3. Run the two cohorts through a resumable runner added to the study tool. It
   must write separate JSONL and summary paths and record random seed, draw
   count, source date, batch size, and converter configuration. Do not use the
   2,048 pilot result as though it were the 12,288 cohort.

4. Validate each output:

       .venv/bin/python tools/ssurgo_empirical_study.py diagnostics \
         --input <cohort>.jsonl --output <cohort>_diagnostic_summary.json

5. Update the investigation report, package tracker, and this ExecPlan with
   raw draw count, unique MUKEY count, valid/residual-invalid/worker-failed
   outcomes, Wilson interval, nonexclusive reason codes, and limitations.

## Validation and Acceptance

The expanded mapped-area cohort is accepted when it has exactly 12,288 draws,
the raw records validate, data-access failures are separately visible, and the
report gives its Wilson interval. The unweighted cohort is accepted when it
has 2,048 distinct equal-probability MUKEY draws and is reported separately.
The package cannot claim an intelligent fallback implementation until fixture
and masked-valid candidate evidence exists and a parameterization ADR approves
the behavior.

## Idempotence and Recovery

The inventory is idempotent because the VAT is read only. Cohort output must be
written atomically by batch or resume from a manifest of completed MUKEYs; do
not overwrite a completed cohort with a different seed or source date. If NRCS
is unavailable, preserve a `data_access_failed` outcome, stop the cohort after
the documented retry budget, and rerun only those records later. Never edit a
source raster or a production run directory.

## Artifacts and Notes

The completed pilot artifacts are under `/tmp/ssurgo_empirical_study_20260721/`.
The versioned aggregate interpretation is in
`docs/investigations/2026-07-21-ssurgo-intelligent-fallback-pilot/README.md`.
The strategy that governs candidate design is
`docs/planning/ssurgo-intelligent-fallback-strategy.md`.

## Interfaces and Dependencies

Keep `tools/ssurgo_empirical_study.py` research-only. Its raster inventory may
use the VAT when present and must fall back to native block streaming otherwise.
Use `SurgoSoilCollection` and `WeppSoil` for the same conversion behavior as a
gridded build, but do not import the research runner into production controller
code. Use `rasterio`/GDAL only for local map access and the existing NRCS Soil
Data Access client already used by `ssurgo.py`; do not add dependencies.

Updated 2026-07-22: recorded user approval for expanded complementary cohorts
and created the dedicated work package.

Updated 2026-07-23: recorded deterministic failure-class score gates and the
four-run held-out result; both preserve the M4 HOLD decision.

Updated 2026-07-24: added ranked candidate-set/oracle diagnostics to separate
candidate discovery from ranking before any future parameterization ADR.

Updated 2026-07-25: recorded the 18-run ranked-candidate cohort, zero-case
manifest records, and worker-count determinism evidence.
