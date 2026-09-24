# Evidence map and evaluation checklist

> Source inspection: 2026-09-21, WEPPpy HEAD `0ab1ce026` with no runtime code edits
> for this task. These are implementation observations, not live validation.

## Claim-to-source map

### Contrast specification and pairs (September 23, 2026)

Section 2.5 reflects two delegated source reviews: selection modes and ordered
scenario-pair semantics. These are implementation observations, not additional
live-run validation.

- `omni_mode_build_services.py::build_contrast_mapping` selects alternative
  hillslope outputs inside the selection and control outputs elsewhere. Pair
  direction matters; the parent/base or another scenario can supply either side.
- `omni_clone_contrast_service.py` copies parent NoDb state and routing inputs,
  assembles selected pass files, and reruns watershed routing. The control
  scenario is a hillslope-output source, not the source of channel configuration.
- `omni_contrast_build_service.py` implements cumulative singleton selections,
  explicit hillslope groups, polygon overlap of at least 50%, repeated-label
  merging, and stream-order groups assigned by greatest raster overlap.
  Empty area/group selections can be skipped. Stream-order grouping requires
  WhiteboxTools and does not replace the routing network.
- `omni.py::get_objective_parameter_from_gpkg` ranks positive control-scenario
  outputs. Depth objectives sum hillslope depths without area weighting.
  `omni_scaling_service.py` recomputes the objective total after cumulative
  filters. Cumulative selection is capped at 100 hillslopes and does not build
  successively larger treatment portfolios.
- `wepppy/weppcloud/templates/controls/omni_contrasts_pure.htm` exposes a single
  pair for cumulative selection and multiple pairs for area/group modes. The
  latter expand pairs across selections and bypass cumulative selection filters.

Module paths above are relative to `wepppy/nodb/mods/omni/` unless explicit.
The manuscript's control comparison describes the analysis design; it does not
assert that the known stream-order aggregate control-column issue is resolved.

### Treatments and scenario construction (September 23, 2026)

Manuscript Sections 2.1–2.3 distinguish prescription parameterization from
scenario orchestration. The inspected sources are:

- `wepppy/nodb/mods/treatments/treatments.py`: `build_treatments`,
  `_apply_thinning`, `_apply_mulch`, `_apply_prescribed_fire`, and `_modify_soil`.
  Treatment assignments change eligible management classes; soil rules are
  resolved by texture and disturbance/treatment class. Mulch retains its burned
  base class and adjusts rill/interrill ground cover.
- `wepppy/nodb/mods/omni/omni_clone_contrast_service.py`: `omni_clone` shares
  climate/watershed assets and copies mutable project state and input resources.
- `wepppy/nodb/mods/omni/omni_mode_build_services.py`: `apply_scenario_mode`
  resolves thinning catalog entries, filters eligible hillslopes, and invokes
  `Treatments.build_treatments`.
- `wepppy/nodb/mods/omni/omni_run_orchestration_service.py`: scenario execution
  builds managements, prepares/runs hillslopes, and prepares/runs the watershed.
- `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv`: supplied
  forest/thinning rows differ in more than cover, including erosion/hydraulic
  parameters and rooting/leaf-area settings. This supports a general mechanism
  description, not numerical attribution of the saved run's responses to each
  parameter. Exact run-consumed parameter files remain to be audited.
- `wepppy/nodb/mods/treatments/mulch_application.py`: `ground_cover_change`
  uses a Hill-type saturation curve with L=100, a=0.8473653284334487, and
  b=1.7369655941662063. The code identifies two construction constraints,
  G(1)=60 and G(2)=80 at G0=30. Roger clarified on September 23, 2026 that
  these targets came from Pete Robichaud's experience with cover achieved
  after known mulch application rates. Section 2.2 credits P. R. Robichaud
  through personal communication (communication date still needed), and
  distinguishes the expert-informed targets from independent field validation
  of the fitted curve across other initial covers and application rates.
  These targets are not attributed to the published ERMiT rate-cover values.
  Numerical examples were
  evaluated directly with that function for initial covers of 10%, 30%, and
  60% and rates of 0.5, 1, and 2 tons/acre. `_apply_mulch` maps catalog suffixes
  to application rates by dividing by 30 and applies the curve separately to
  `inrcov` and `rilcov`. No new field-validation claim or unit conversion is made.

The manuscript describes existing behavior; no parameterization or runtime code
was changed. Canopy/ground-cover labels denote complete treatment prescriptions,
not cover-only sensitivity experiments. This distinction also applies to the
interpretation of the Tenderfoot results.

### Existing implementation and case evidence

The September 23, 2026 [Tenderfoot analysis](data/tenderfoot/analysis.md) adds
retained model artifacts, acquisition and analysis scripts, tables, and figures
for two thinning scenarios and 36 spatial-group contrasts. It supports a
narrative about conditional, nonadditive outlet sediment responses. It also
documents incorrect control/difference columns in the stream-order contrast
export; analysis differences are independently recomputed from raw baseline and
contrast outputs. This is an internally checked model demonstration, not
observational validation or independent full-run equivalence verification.

| Claim or boundary | Source | Remaining evidence |
| --- | --- | --- |
| Scenario types, eligibility, and selection semantics | [OMNI user guide](../../wepppy/nodb/mods/omni/ENDUSER.md) | Actual generated/prepared inputs for the case |
| Cumulative selector constructs single-hillslope contrasts | [Contrast builder](../../wepppy/nodb/mods/omni/omni_contrast_build_service.py), `build_contrasts_cumulative_default` | Retained selection mappings |
| Selected control/treatment outputs feed a fresh watershed run | [Clone service](../../wepppy/nodb/mods/omni/omni_clone_contrast_service.py), `run_contrast` | Agreement with fully simulated equivalents |
| OMNI combined metrics retain scenario identity and refresh catalog | [Artifact exporter](../../wepppy/nodb/mods/omni/omni_artifact_export_service.py), `scenarios_report` | Schema and query readback on case artifacts |
| Dashboard map selection and graph scenario lists are distinct | [Dashboard README](../../wepppy/weppcloud/static/js/gl-dashboard/README.md) | Captured UI state and network requests |
| Map comparison ranges use base-minus-scenario values | [Scenario manager](../../wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js) | Rendered value/sign/legend checks |
| Scenario/contrast requests use scenario body selectors or composite contrast run IDs | [Dashboard query helper](../../wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js) | Exact requests for the case |
| Multi-scenario graph data loads through scenario-specific queries | [Graph loaders](../../wepppy/weppcloud/static/js/gl-dashboard/graphs/graph-loaders.js) | Series identities, quantities, weighting, response readback |
| Query filtering, joins, aggregation, and scenario context | [Query documentation](../../wepppy/query_engine/README.md), [context resolver](../../wepppy/query_engine/context.py) | Payloads executed against retained catalogs |
| Unburned and burned conditions use the same parameterization harness | [Disturbed guide](../../wepppy/nodb/mods/disturbed/ENDUSER.md), Lew et al. (2022), Table 1 and section 4.1.5 | Verify active lookup table and generated management/soil inputs for the case |
| Parent geometry, climate, configuration, and parameterization are inherited at scenario construction | [Scenario cloning](../../wepppy/nodb/mods/omni/omni_clone_contrast_service.py), `omni_clone` | Compare inherited WEPP Advanced Options and intended scenario differences; check rebuild status after edits |
| Serialized hillslope pass files feed watershed routing | [Runner documentation](../../wepp_runner/README.md), `make_watershed_omni_contrasts_run`, and clone-service `run_contrast` | Record selected pass paths/hashes and binary compatibility; compare routed outputs with independent runs |

The dashboard README and graph-loader comments include a helper-call example
with arguments in a different order from the current implementation. Use the
actual function signature and call sites (`payload, scenarioPath`) for retained
examples. This scaffold does not change production documentation or code.

## Bounded evaluation

- [ ] Select one watershed and document why its spatial treatment question matters.
- [ ] Freeze a reviewed burned control and one treatment scenario, including
  simulation years, climate inputs, parameterization, and selected executable.
- [ ] Select representative individual hillslopes plus one explicit multi-hillslope
  group. Include a case capable of detecting wrong scenario/input selection.
- [ ] Generate equivalent independent full-run references. Check actual consumed
  model inputs before interpreting output agreement.
- [ ] Compare scientific outputs using justified, predeclared tolerances.
- [ ] Measure source-scenario costs and incremental contrast costs separately;
  identify whether storage measurements count logical or physically allocated bytes.
- [ ] Compare untreated contribution ranks with modeled outlet-benefit ranks.
  Define area-normalized quantities and denominators if used.
- [ ] Retain one dashboard map and one scenario graph; verify selected values,
  colors/sign conventions, series identities, and units against artifacts.
- [ ] Retain a query over combined OMNI metrics and matched scenario-scoped queries.
  Check group membership, joins, time alignment, weighting, and missing values.
- [ ] Replace manuscript placeholders with evidence-backed findings, including
  failures or limitations. Claim no user-performance benefit without a user study.

## Figure and artifact plan

### Lookout demonstration retained September 21, 2026

- Case: `traveled-calligrapher` on wepp1; SBS-based parent, undisturbed reference,
  and `mulch_30_sbs_map` / `mulch_60_sbs_map` alternatives.
- Original screenshots: [watershed map](figures/lookout-map.png),
  [scenario configuration](figures/omni-control.png), and
  [GL-Dashboard difference map](figures/gl-dashboard-difference-map.png).
  [Image inventory](figures/sources.json) records dimensions and SHA-256 hashes.
- [Scenario summary](data/lookout/scenarios/scenarios.out.parquet) and
  [provenance](data/lookout/scenarios/provenance.json) retain the reported model
  outputs. Draft Results includes their preliminary whole-scenario comparisons.
- Scope decision: observational flow and precipitation checks provide context;
  the paper remains a workflow demonstration, without further calibration or
  claims of validated treatment effectiveness. See manuscript section 5.
- Still outstanding: exact averaging-period and treatment-mask verification,
  map-value readback, scenario graph, contrasts, and independent reference runs.
  The supplied screenshots do not establish any of those checks.

### Remaining evaluation figures

| Figure | Content | Required inputs |
| --- | --- | --- |
| 1 | Scenarios -> selected hillslope outputs -> watershed routing -> map/query analysis | Verified workflow and source references |
| 2 | Spatial selection, comparison map, and multi-scenario graph | Same retained run, explicit UI state, query responses |
| 3 | Untreated contribution versus treatment outlet benefit | Contrast mappings, routed metrics, actual treated areas |
| 4 | Correctness and cost | Full-run references, comparison rules, timing/resource records |

Place supporting artifacts under a case-specific directory when collected;
do not create fabricated datasets or placeholder images. Every displayed result
must identify its metric, units, reference, time support, and source artifact.
Keep source/query data alongside figure-generation code. Pubroot requires durable
absolute HTTPS figure links at submission; local drafting paths are insufficient.

## Literature tasks

- [x] Review WEPPcloud Parts I/II, forest and fire-model literature, and Pi-VAT;
  draft a cited introduction. [Review and source inventory](references/literature-review.md).
- [x] Retain seventeen PDFs with acquisition provenance and Git exclusions.
- [x] Obtain and review relevant passages in the [three requested full texts](references/access-needed.md),
  including the foundational watershed-routing paper.
- [ ] Cite treatment parameterizations actually used in the eventual case.
- [ ] Compare OMNI's spatial assembly/rerouting with existing treatment-assessment
  workflows in detail before claiming novelty.
- [ ] Keep platform implementation evidence separate from scientific validation.

The manual-fork synchronization burden is Roger's operational account, anchored
to the cloning workflow documented in WEPPcloud Part I. No user study or measured
error-rate reduction has been performed. The source review supports inheritance
at child construction; it does not establish complete invalidation for every
later edit to parent advanced options or parameter tables.
