# `AgFields` mod

Model agricultural fields in WEPP within a watershed with crop schedule (observed climates over a period of time)

Resources stored in weppcloud `ag_fields` directory

## Additional Model Inputs

### GeoJSON of field boundaries within the watershed

- filename saved as `ag_fields\field_boundaries_geojson` property of AgFields
- rasterize to `ag_fields.field_boundaries`

### Plant Database Zip (with 2017.1 files) from Jim's Interface (`<anything>.zip`)

- user uploads a zip archive
- the .zip files are extracted and converted to 98.4 format with normalized file names
- `ag_fields/plant_files` contains the 98.4 format managements
- `ag_fields/plant_files/2017.1` contains the 2017.1 format managements if they were supplied
- can optionally be truncated to just the first year

### Crop name to management lookup
- `ag_fields_dir/rotation_lookup.tsv` is serialied `CropRotationManager`
- encapsulates logic take a crop_name, database, and id and find and stack management files

## Running fields as sub-fields (inital outline)

1. Generate WEPPcloud watershed containing the field boundaries with whitebox-tools delineation backend
   - Make sure climate observed `start_year` and `end_year` match the `rotation_schedule.parquet`
2. Rasterize `ag_fields.field_boundaries_geojson` to `ag_fields.field_boundaries`
3. Intersect `ag_fields.field_boundaries` with `watershed.subwta` to yield `ag_fields.sub_field_boundaries`
   - These "sub" fields will be treated sa hydrologically disconnected
   - filter out `sub_fields` smaller than some pre-determined area threshold `ag_fields.sub_field_min_area_threshold_m2`
4. Abstract the `sub_fields` to hillslopes generating slope files in `ag_fields\slope_files`
5. For each sub field hillslope
   - 5.1 Build multi-year management files
   - 5.2 use soil, climate from sub_fields `topaz` hillslope
   - 5.3 run hillslope in `wepp\ag_fields\runs` and generate outputs in `wepp\ag_fields\output`
6. Compile spatio-temporal outputs

## Data files `/wc1/runs/co/copacetic-note`

### `ag_fields/<field_boundaries_geojson>.geojson`
- `ag_fields/rotation_schedule.parquet`
- `ag_fields/field_boundaries.tif`

#### `ag_fields/rotation_schedule.parquet`
- the rotation schedule has rotations over several years as separate columns
- each field is a separate row and has a unique field id
e.g.
```
 #   Column      Non-Null Count  Dtype  
---  ------      --------------  -----  
 30  field_ID    2177 non-null   float64
 31  Crop2008    2177 non-null   object 
 32  Crop2009    2177 non-null   object 
 33  Crop2010    2177 non-null   object 
 34  Crop2011    2177 non-null   object 
 35  <rotation>    2177 non-null   object 
 ...
```

- Field ID is configurable as `AgFields.field_id_key`
- Crop<year> is accessed by `AgFields.crop_year_accessor.format(year)`
  - e.g 'Crop{}' and is set using `AgFields.set_crop_year_accessor`
  - the `rotation` columns have `crop_name`s


#### `ag_fields/field_boundaries.tif`
- raster with the field id burned in
- aligned with weppcloud project rasters

### Each field is divided into hydrologiccal sub fields `ag_fields/sub_fields` by PERIDOT

#### `ag_fields/sub_fields/sub_field_id_map.tif`
- intersection of subwta and field boundaries has sub field id keys

#### `ag_fields/sub_fields/sub_fields.geojson` and `sub_fields.WGS.geojson`
- polygonized from `sub_field_id_map.tif` with `field_id`, `wepp_id`, `topaz_id` features

#### `fields.parquet` similiar to `watershed/hillslopes.parquet` but for fields

schema
```
 #   Column        Non-Null Count  Dtype  
---  ------        --------------  -----  
 0   field_id      8109 non-null   int64  
 1   topaz_id      8109 non-null   object 
 2   sub_field_id  8109 non-null   int64  
 3   slope_scalar  8109 non-null   float64
 4   length        8109 non-null   float64
 5   width         8109 non-null   float64
 6   direction     8109 non-null   float64
 7   aspect        8109 non-null   float64
 8   area          8109 non-null   float64
 9   elevation     8109 non-null   float64
 10  centroid_px   8109 non-null   int64  
 11  centroid_py   8109 non-null   int64  
 12  centroid_lon  8109 non-null   float64
 13  centroid_lat  8109 non-null   float64
 14  wepp_id       8109 non-null   int64  
 15  TopazID       8109 non-null   int64  
```

#### slope files from PERIDOT
- `ag_fields/sub_fields/slope_files`
- names convention is `field_{field_id}_{topaz_id}.slp`

(flowpaths and flowpaths table are also produced by PERIDOT but not used)



### Hangman notes

Hangman is the weppcloud alpha project for developing AgFields

runid: copacetic-note

wd: /wc1/runs/co/copacetic-note/

## remaining for hangman

- [x] 1. Setup a new NoBbBase subclass AgFields to model and rasterize the geojson 
- [x] 2. Intersect the fields raster with the subwta to identify sub fields
- [x] 3. write a program in peridot to abstract representative hillslopes (e.g. wepp slope file) for each subfield and a fields_hillslope.csv metadata. 
- [x] 4. setup a routine in AgFields to prep the sub field hillslopes 
      - using the slope file from rust
      - the stacked managements from the rotation_schedule.parquet
      - the soil and the climate from the associated hillslope
- [x] 5. setup routine in AgFields to run wepp


# model output files

field_id, year, crop_name, runoff, sed_del, sed_det, sed_dep, (hill_wat) Ep+Es+Er, (hill_wat) Dp



## Watershed integration (three-scheme implementation opened)

The current AgFields workflow runs each retained field/hillslope intersection as an
independent WEPP hillslope. Concept 2 is implemented and passed engineering
generated-output acceptance. A subsequent connectivity inventory found direct
channel drainage for only 3,269 of 6,626 retained sub-fields (49.3%) in
`sacral-self-discipline`, so Concept 1 is reopened and a connectivity-aware hybrid
is now an implementation target. Mariana's comparative scientific evaluation
follows engineering delivery of all three schemes.

Related implementation references:

- [AgFields NoDb mod](../../../../nodb/mods/ag_fields/README.md)
- [Roads NoDb integration specification](../../../../nodb/mods/roads/specification.md)
- [WEPP output scope contract](../../../../../docs/schemas/output-scope-contract.md)
- [Concept 2 implementation work package](../../../../../docs/work-packages/20260713_ag_fields_concept2_watershed_integration/package.md)
- [Flowpath-to-channel connectivity inventory](../../../../../docs/work-packages/20260713_ag_fields_flowpath_channel_connectivity/package.md)
- [Routing scheme suite work package](../../../../../docs/work-packages/20260714_ag_fields_routing_scheme_suite/package.md)
- [Management capacity and corpus validation plan](../../../../../docs/work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_management_capacity_and_corpus_validation_plan.md)
- [ADR-0018: AgFields weighted PASS accounting](../../../../../docs/adrs/ADR-0018-agfields-weighted-pass-accounting.md)
- [ADR-0019: Field-aware OFE and hybrid routing](../../../../../docs/adrs/ADR-0019-agfields-field-aware-ofe-hybrid-routing.md)

### Decision posture

Concept 2 was implemented under the completed
[AgFields Concept 2 watershed-integration work package](../../../../../docs/work-packages/20260713_ag_fields_concept2_watershed_integration/package.md).
It retains each sub-field's Peridot slope, crop rotation, and independent WEPP
result, and its weighted merge must preserve each source's water-volume and
sediment-mass contribution event by event and for the full run.

That engineering result remains valid evidence. Concept 2 output must still be
described as **area-weighted outlet injection**, not as field-to-buffer routing: it
does not model runon, deposition, or trapping between a field and the parent
hillslope outlet.

The connectivity inventory established a new decision: implement Concept 1 and a
hybrid in a separate
[routing scheme suite work package](../../../../../docs/work-packages/20260714_ag_fields_routing_scheme_suite/package.md).
The hybrid chooses Concept 2 for each retained sub-field with at least one
generated per-cell flowpath whose first outside cell is a channel, and Concept 1
for every other retained sub-field. This is a topology classifier, not a delivery
ratio or a claim that channel-connected fields have no buffer effects.

Concept 1 and hybrid engineering acceptance requires plan/source-area closure,
parseable and runnable generated WEPP inputs, successful isolated watershed
execution, stable failure provenance, regression coverage, and generated-output
evidence. Mariana Dobre will compare the three result sets from
`/wc1/runs/sa/sacral-self-discipline` and qualify their scientific use and
limitations after engineering delivery.

The first feasibility gate is now complete. Geometry, explicit-breakpoint input
synthesis, and a real mixed-parent balance proof passed, but exact management
preflight found 141 Concept 1 parents and 59 hybrid residual parents above the
supported WEPP maximum of 20 referenced yearly scenarios. The routing-suite
package now owns a synchronized forest hillslope-capacity increase and full
management-corpus execution, including canonical AgFields input validation or
evidence-driven forest numerical hardening when failures are found. User-facing
wiring remains gated until that milestone and ADR-0019 pass. The measured
evidence is in
[the Concept 1 feasibility artifact](../../../../../docs/work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_concept1_feasibility.md).

### Shared objective and invariants

All three schemes must:

- preserve the baseline `wepp/runs` and `wepp/output` trees;
- use the existing Topaz-to-WEPP translator for parent hillslope identity;
- retain exactly one parent hillslope PASS file for every hillslope consumed by the
  watershed rerun;
- use the same climate realization, simulation years, and calendar for every PASS
  source combined under one parent hillslope;
- initially support only the single-OFE parent inputs used by `ag-fields.cfg`;
  already-MOFE parents require a separate source-to-OFE mapping contract;
- treat filtered or uncovered field-raster cells as baseline/background area;
- fail explicitly on missing inputs, area overlap, calendar mismatch, invalid WEPP
  files, or incomplete watershed outputs;
- write a versioned integration manifest containing scheme id/slug, source paths,
  areas, weights, decisions, warnings, classifier/algorithm versions, and accepted
  parameter ADR version; and
- regenerate watershed interchange/report resources only under an isolated
  AgFields watershed-output tree.

The scheme layout is additive and does not move existing per-field artifacts or
the completed unscoped Concept 2 evidence:

```text
wepp/ag_fields/runs/                 # existing independent sub-field runs
wepp/ag_fields/output/               # existing independent sub-field outputs
wepp/ag_fields/watershed/runs/       # legacy Concept 2 evidence; preserve in place
wepp/ag_fields/watershed/output/     # legacy Concept 2 evidence; preserve in place
wepp/ag_fields/watershed/manifest/   # legacy Concept 2 evidence; preserve in place
wepp/ag_fields/watershed/concept-1/{runs,output,manifest}/
wepp/ag_fields/watershed/concept-2/{runs,output,manifest}/
wepp/ag_fields/watershed/hybrid/{runs,output,manifest}/
```

There is no `watershed/all/` result. The UI-only `all` choice runs the three fixed
schemes separately. The additive schema/state/path compatibility contract is
frozen in
[the scheme artifact compatibility plan](../../../../../docs/work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_scheme_artifact_compatibility_plan.md).
If integrated results become selectable in the standard reports, add explicit
AgFields scheme semantics to the output-scope contract in the same change set; do
not overload the existing `baseline` or `roads` meanings.

### Routing scheme and UI contract

The Python/API identifiers and filesystem slugs are:

| Identifier | Filesystem slug | Routing behavior |
| --- | --- | --- |
| `concept_1` | `concept-1` | Rebuild eligible parents as field-aware OFE profiles and route field response through downstream OFEs |
| `concept_2` | `concept-2` | Inject area-weighted independent sub-field PASS response at the parent outlet |
| `hybrid` | `hybrid` | Inject channel-connected sub-fields and route all other sub-fields through field-aware OFEs |

The runs page offers one selection with these exact description-first labels:

- **Field-aware hillslope routing (routes fields through downstream OFEs)**;
- **Direct sub-field outlet injection (preserves independent sub-field results; no
  buffer routing)**;
- **Connectivity-aware mixed routing (injects channel-connected fields; routes
  other fields through OFEs)**; and
- **Run all routing schemes (writes three separate results for comparison)**.

Do not render bare `Concept 1`, `Concept 2`, or `Hybrid` option labels. Concept 2
is the initial UI default and the behavior for an old API client that omits the
scheme. `all` expands in stable Concept 1, Concept 2, hybrid order to independently
tracked, serial RQ jobs so their full-watershed memory peaks do not overlap. A
failure in one scheme must remain visible but must not prevent a later comparison
scheme from running.

Per-scheme state, staleness, errors, retry, clear, and browse paths are independent.
Clearing one current scheme can remove only its fixed root and state. Clearing all
current schemes still preserves the legacy Concept 2 tree, baseline WEPP, and
independent AgFields trees.

### Feasibility summary

| Dimension | Field-aware hillslope routing | Direct sub-field outlet injection | Connectivity-aware mixed routing |
| --- | --- | --- | --- |
| Engineering feasibility | Geometry/input spike passed; 141 management overflows are in the integrated capacity/corpus milestone | High; engineering implementation complete | Residual/mixed proof passed; 59 management overflows are in the integrated capacity/corpus milestone |
| Per-subfield source fidelity | Medium at best; parent-profile bands can merge or misclassify field area | High; retains each Peridot slope, rotation, and independent result | High for connected sources; Concept 1 fit for all other sources |
| Field/background runon | Yes, between represented OFEs | No | Yes for non-connected/residual sources; no parent-buffer routing for connected sources |
| Downstream buffer trapping | Represented when a distinct, well-fitted background OFE lies below a field | None before outlet injection | Represented for Concept 1 branches only |
| Water/sediment accounting | Native replacement-hillslope balance plus plan-area diagnostics | Explicit event/run weighted-source closure | Residual Concept 1 balance plus weighted connected-source event/run closure |
| Main scientific risk | A two-dimensional mosaic may lack a defensible one-dimensional representation | Outlet injection can over-deliver when a real buffer lies below a field | Binary topology classification and residual projection combine both approximations |
| Delivery status | Binary/data milestone in progress; production wiring gated | Implemented; scheme-root migration deferred with the suite | Binary/data milestone in progress; production wiring gated |

### Concept 1: rebuild affected hillslopes as field-aware OFE profiles (capacity milestone)

**Status:** The geometry and input-synthesis spike passed. The routing scheme
suite now owns the forest capacity increase and complete management-corpus
validation needed to resolve true native management overflows before production.
The following model, planning, synthesis, validation, and feasibility contract
remains normative. A planner-only or surrogate output does not satisfy the
faithful implementation target.

#### Model contract

Represent each affected parent hillslope as an ordered sequence of OFEs from the
top of the representative profile to the channel. Each OFE has exactly one source
assignment:

- `background`: the parent's existing soil and management; or
- `field`: a field's multi-year crop-rotation management and, initially, the same
  parent soil used by the existing AgFields sub-field run.

Water and sediment are routed through downstream OFEs by WEPP. A background OFE
below a field OFE can therefore represent buffer infiltration, deposition, and
trapping. This is still a one-dimensional abstraction: side-by-side fields,
fragmented polygons, and variable buffer widths are reduced to ordered bands.

One parent hillslope must have one shared set of OFE breakpoints. The original idea
of independently rounding every sub-field to `1/4`, `1/3`, `1/2`, or `1/1` is not
well-defined when several fields intersect the same hillslope. The implementation
must instead solve segmentation and assignment at the parent-hillslope level.

#### Proposed planning artifact

Write
`wepp/ag_fields/watershed/concept-1/manifest/ofe_plan.parquet` with one row per
planned OFE. At minimum, record:

- parent `topaz_id` and `wepp_id`;
- ordered `ofe_id` and normalized start/end distance;
- source kind, `field_id`, and `sub_field_id` when applicable;
- raster area, modeled OFE area, and signed area error;
- fraction of cells in the OFE agreeing with the assigned source;
- distance-to-channel distribution and downstream-background length; and
- eligibility status plus explicit rejection reasons.

The manifest is the boundary between geospatial planning and WEPP input synthesis.
WEPP preparation must consume it rather than recomputing field placement.

#### Implementation plan

1. **Build and evaluate the one-dimensional field plan.**
   - Read aligned `subwta`, `sub_field_id_map`, and `discha` rasters.
   - For each parent hillslope, order cells by the same stable descending discharge
     rank used by the current MOFE map builder.
   - Evaluate a parent-level set of contiguous OFE bands and assign each band to
     its dominant field or to background.
   - Compare one-to-four equal-area bands with generalized and source-order
     searches up to the explicit-breakpoint kernel's 20-OFE cap.
   - Score every candidate using field-area error, cell classification agreement,
     field fragmentation, ordering conflicts, and downstream-buffer error.
   - Reject an affected hillslope when no candidate meets documented acceptance
     criteria. Do not silently reinterpret a poor mosaic or switch algorithms.

2. **Settle parameterization before production use.**
   - Treat the proposed `1/8` minimum area, nearest-fraction rule, candidate band
     counts, and fit tolerances as hypotheses, not defaults.
   - Calibrate them on representative watersheds and write the required
     parameterization ADR before they control production behavior.
   - Prefer the existing user-visible `sub_field_min_area_threshold_m2` for basic
     field retention so the watershed-integration step does not introduce a second
     unexplained small-field filter.

3. **Generate field-aware MOFE inputs.**
   - Extend the owned `wepppyo3` slope segmenter with an additive API that accepts
     explicit normalized breakpoints; preserve the existing segmenter contract.
   - Generate a parent MOFE slope whose OFE lengths match the accepted plan and
     whose total length, width, and area remain consistent with the parent slope.
   - Build the MOFE soil with `SoilMultipleOfeSynth`. For the first version, repeat
     the parent soil for every OFE, matching current AgFields behavior.
   - Build one multi-year management per field from the rotation schedule, load the
     parent management for background OFEs, and compose the ordered stack with
     `ManagementMultipleOfeSynth`.
   - Preflight the number of OFEs and referenced yearly scenarios. Both current
     explicit-breakpoint segmentation and hillslope management permit at most 20,
     but multi-field rotations can hit the management limit independently of OFE
     count.

4. **Run replacement hillslopes and the isolated watershed.**
   - Copy or link baseline run inputs into
     `wepp/ag_fields/watershed/concept-1/runs`.
   - Run one replacement hillslope for every accepted affected parent.
   - Stage the replacement PASS for accepted parents and the unchanged baseline
     PASS for untouched parents under
     `wepp/ag_fields/watershed/concept-1/output`.
   - Build `pw0.run` with `make_watershed_omni_contrasts_run`, run watershed WEPP,
     and regenerate scoped interchange artifacts.

5. **Add orchestration and observability.**
   - Make watershed integration a distinct RQ stage after successful sub-field WEPP
     runs so independent field results remain usable on their own.
   - Include baseline WEPP, sub-field outputs, geometry/schema, rotation lookup,
     planner version, and parameter ADR version in the staleness signature.
   - If enqueue sites or dependencies change, update the RQ dependency catalog and
     run `wctl check-rq-graph`.
   - Expose counts for accepted, rejected, untouched, failed, and scenario-limited
     hillslopes plus the aggregate area and fit errors.

#### Validation plan

- Unit-test deterministic segmentation on synthetic layouts: one upslope field and
  downstream buffer, one field at the channel, two ordered fields, side-by-side
  fields, fragmented fields, tiny fields, and flat/tied discharge ranks.
- Assert contiguous OFE IDs; matching slope/soil/management OFE counts; exact source
  ordering; and area closure within a documented raster-discretization tolerance.
- Parse every generated WEPP input and run short hillslope fixtures before attempting
  a watershed run.
- Compare baseline, independent sub-field, MOFE hillslope, and watershed outputs for
  water volume, sediment mass, peak runoff, and per-event calendar alignment.
- Verify the expected direction of buffer response: an otherwise identical field
  with a downstream background OFE should not yield more sediment than the same
  field placed at the outlet without a buffer, absent a documented physical reason.
- Validate generated run artifacts, interchange outputs, staleness, and report-scope
  isolation in addition to unit tests.

#### Feasibility assessment

The planner represented every development-project source with 1-20 OFEs, positive
field overlap, and exact raster-area closure. Assignment agreement and area/order/
fragmentation diagnostics span a wide range, confirming that Concept 1 is not a
general two-dimensional mosaic representation and that Mariana must assess the
scientific effect.

File generation is feasible for most parents, but not all with the supported WEPP
binary. Even after exact structural scenario deduplication, management synthesis
requires 21-24 referenced yearly scenarios for 141 of 1,869 affected parents,
covering 12.21% of affected area. This confirmed native input-contract limit is
the production blocker; no low-fit or scenario-limited parent may be silently
dropped or rerouted.

### Concept 2: area-weighted PASS aggregation and watershed rerun (implemented)

#### Model contract

Treat each existing independent sub-field PASS as a source delivered directly to
the outlet of its parent hillslope. Retain the baseline parent PASS only for the
area not covered by retained sub-fields, then merge the aligned event records and
rerun the watershed.

For parent hillslope area `A_parent` and retained sub-field raster areas `A_i`:

```text
A_background = A_parent - sum(A_i)
baseline_scale = A_background / A_parent
subfield_scale_i = A_i / A_modeled_i
```

Peridot currently constructs each sub-field slope with `width = raster area /
representative length` and preserves area when clipping, so `subfield_scale_i`
should normally be approximately one. It must still be recorded and validated; it
must not be assumed silently.

Each independent sub-field PASS remains the canonical field-scale result. Except
for an explicit area-correction scale, its event water volumes, detachment and
deposition masses, and sediment-class masses are carried into the parent accounting
without replacing the sub-field simulation. The source manifest retains those
per-subfield contributions even though the combined parent PASS no longer carries
source identity.

This gives Concept 2 higher per-subfield source fidelity than Concept 1's lossy OFE
band assignment. The weighted combiner must maintain event-level and full-run water
and sediment closure from its source PASS files into the combined parent PASS,
within documented serialization precision.

This contract preserves represented source area, source water and sediment balance,
and watershed/channel routing after injection. It does not preserve spatial
placement or delivery through the parent hillslope. It also assumes that the
full-hillslope baseline response can be scaled to represent only the background
area, even though runoff generation, erosion, and deposition can be nonlinear with
hillslope length and runon.

#### Routing and closure artifacts

New scheme-suite runs write
`wepp/ag_fields/watershed/concept-2/manifest/pass_sources.parquet` with one row per
parent/source pair. The completed legacy run retains the corresponding artifact in
the unscoped `watershed/manifest` tree. Each artifact records:

- parent `topaz_id`, parent `wepp_id`, source kind, and source PASS path;
- `field_id` and `sub_field_id` for field sources;
- parent raster area, retained field raster area, background area, source modeled
  area, and applied scale;
- coverage ratio and area-closure residual;
- source and target climate tokens plus calendar validation result; and
- integration status, rejection reason, and combiner version.

Compute all areas from the same aligned rasters. Raster overlap or coverage greater
than the parent area must fail explicitly. Cells removed by the configured minimum
area filter remain background; they are not dropped from the parent area balance.

#### Weighted PASS combiner contract

The Roads combiner is useful precedent, but its current API adds complete sources
and has no per-source weights. Do not change its existing semantics. Add a separate
owned `wepppyo3` API for weighted hillslope PASS aggregation.

The new API must:

1. accept an explicit scale and represented area for every PASS source;
2. require compatible climate files, simulation headers, row counts, and day keys;
3. scale volume, mass, and rate terms by represented-area scale while retaining
   source contribution totals;
4. reconstruct depth/flux terms from combined quantities and target area where the
   PASS definition permits it, rather than scaling every numeric column alike;
5. reconstruct sediment concentrations from scaled class mass and runoff volume;
6. reconstruct peak runoff using scaled hydrograph components and recompute shape
   terms under a documented strategy;
7. apply explicit `EVENT`, `SUBEVENT`, and `NO EVENT` precedence; and
8. serialize a parser-round-trippable PASS file; and
9. return source-level, event-level, and full-run water/sediment closure diagnostics
   to the caller.

Before implementing the combiner, write a field-by-field semantic table for every
PASS column, including units, extensive/intensive classification, scaling rule, and
zero-volume behavior. `gwbfv` and `gwdsv` currently lack unit metadata and require
confirmation against the WEPP writer/reader. No unsupported field may be silently
zeroed, summed, or scaled.

#### As-built implementation

1. **Build the parent/source routing plan.** The
   `AgFieldsWatershedIntegrator` collaborator:
   - Group `ag_fields/sub_fields/fields.parquet` rows by parent `wepp_id` and
     reconcile them against `subwta` and `sub_field_id_map` cell counts.
   - Validate parent area, unique cell ownership, sub-field modeled area, uncovered
     area, source PASS existence, and climate/calendar identity.
   - Persist the routing artifact before combining files.

2. **Use the additive weighted combiner in `wepppyo3`.**
   - Add the semantic table and synthetic fixtures first.
   - Keep the current Roads `combine_hillslope_pass_files` API unchanged and add an
     additive weighted API or strategy with structured source metadata.
   - Return conservation diagnostics for each event and aggregate run totals.

3. **Stage parent PASS files and rerun watershed WEPP.**
   - Copy or link baseline inputs into the isolated watershed workspace.
   - For an untouched parent, stage its baseline PASS unchanged.
   - For an affected parent, combine its area-scaled baseline PASS with all retained
     sub-field PASS files into `H<parent_wepp_id>.pass.dat`.
   - Build and run `pw0.run` using the complete staged parent PASS set.
   - Regenerate interchange artifacts under the integrated output directory and
     assert required resources exist.

4. **Expose a separate RQ/API/UI stage.**
   - Require successful baseline WEPP and current AgFields sub-field runs.
   - Job key `agfields_run_watershed`, authenticated `run-watershed` and
     `clear-watershed` routes, additive hydration state, and Stage 5 DOM/controller
     hooks remain separate from Stage 4.
   - Track job state separately from the existing sub-field run and invalidate it
     when baseline outputs, field geometry, rotation mapping, sub-field outputs, or
     combiner version changes.
   - Update the RQ dependency catalog and graph when the new enqueue/dependency edge
     is introduced.
   - Initially label the feature experimental and surface the outlet-injection and
     no-buffer-routing limitations in the UI and result manifest.

5. **Keep report and download isolation.**
   - Keep new integrated results under
     `wepp/ag_fields/watershed/concept-2/output`; preserve the completed unscoped
     result in place as legacy evidence.
   - Add an output scope only when the standard reports are ready to consume these
     results, updating the canonical scope contract and its route tests together.
   - Preserve direct access to independent field outputs for field-scale analysis.

#### Validation plan

- Weighted-combiner unit identities:
  - no fields produces a semantically identical baseline PASS;
  - full field coverage gives the baseline source zero weight;
  - half coverage with a field identical to baseline reproduces the baseline within
    PASS serialization precision;
  - two fields conserve combined area, water volume, and sediment class mass;
  - zero-runoff, `SUBEVENT`, and `NO EVENT` records remain valid; and
  - climate, calendar, overlap, missing-file, negative-area, and non-finite inputs
    fail explicitly.
- Integration tests must stage every parent PASS exactly once, run watershed WEPP,
  regenerate interchange, and leave baseline artifacts byte-for-byte unchanged.
- For every event and the full run, report water-volume and sediment-mass closure
  between weighted sources, combined parent PASS files, and watershed inputs.
- Produce an evaluation bundle for Mariana Dobre containing baseline outputs,
  independent sub-field results, integrated Concept 2 outputs, source-area and
  closure manifests, and geometry diagnostics for outlet and upslope fields.
- Treat scientific suitability and buffer-bias findings as Mariana's evaluation
  task after engineering delivery. Record her disposition before changing the
  feature's scientific-use guidance or production labeling.

#### Feasibility assessment

Concept 2 has high engineering feasibility for an experimental MVP. Existing
AgFields runs already produce the required sub-field PASS files, Peridot preserves
their represented raster area, and Roads demonstrates isolated staging plus a
watershed rerun. The contained new kernel is area-aware PASS combination.

Concept 2 is designed for high per-subfield source fidelity: each source keeps its
own representative slope, crop rotation, and WEPP process result, and the merge can
conserve its weighted water and sediment contribution. This is expected to be
better per-subfield fidelity than Concept 1's quantized OFE representation. Its
scientific qualification remains pending Mariana's evaluation. Fidelity is
moderate for replacing the parent source load and preserving channel routing, but
low for delivery through the remaining parent hillslope.

The approximation is most credible when a field reaches the parent outlet, occupies
most of the parent, or when the decision metric is dominated by watershed/channel
routing rather than downslope buffer treatment. It is least credible for erosive
fields high on long, depositional or vegetated hillslopes. Those cases must be
diagnosed from distance-to-channel geometry and disclosed, not corrected with an
uncalibrated delivery-ratio heuristic.

### Hybrid: connectivity-aware mixed routing (capacity milestone)

#### Classification contract

Reuse the owned Peridot direct-channel classifier; do not duplicate its D8 logic
in WEPPpy. A retained sub-field is channel-connected when at least one generated
per-cell flowpath has a valid D8 successor outside that sub-field and the first
outside cell is a channel. Positive cells in an explicit channel mask take
precedence when supplied; otherwise a SUBWTA id whose final digit is `4` identifies
a channel.

The reusable Peridot CLI now emits one deterministic detail row per retained
sub-field while preserving the existing aggregate summary contract. Production
execution will join those rows exactly once to current `fields.parquet` and persist
`wepp/ag_fields/watershed/hybrid/manifest/subfield_routing.parquet` with parent,
field, sub-field, connectivity, direct-outlet-cell count, routing branch,
classifier version/definition, channel source, and input identities. Missing,
duplicate, or extra ids fail preflight.

This binary classification selects an engineering routing approximation. It is not
a sediment delivery ratio, buffer efficiency, travel-time estimate, or evidence
that a connected sub-field has no buffer effect.

#### Parent composition and area contract

For parent raster area `A_parent`, connected sub-field raster areas
`A_connected_i`, and residual Concept 1 source area `A_residual`:

```text
A_residual = A_parent - sum(A_connected_i)
A_residual + sum(A_connected_i) = A_parent
```

The residual Concept 1 plan includes non-connected retained sub-fields and
uncovered background; it excludes connected sub-field cells from plan assignment
and area. The first feasibility candidate preserves the parent representative
profile length and normalized downslope breakpoint positions, then sets the rerun
width to `A_residual / parent_length`. This preserves downstream distances while
rerunning WEPP at the residual represented area. A real mixed parent passed this
geometry and exact area/water/sediment closure. ADR-0019 still requires acceptance
of the management-limit response before the UI path is wired.

Compose each parent explicitly:

- When no retained sub-field is connected, run/stage a pure Concept 1 parent at
  `A_parent`.
- When connected retained sub-fields cover the complete parent, use pure Concept 2
  composition with no residual source.
- When both connected and residual areas exist, run the residual Concept 1 parent
  at `A_residual`, then use the ADR-0018 weighted combiner to merge its PASS with
  each connected independent sub-field PASS into one target `A_parent` PASS.

Adding connected sources to a complete Concept 1 parent is prohibited because it
double-counts area. Uniformly scaling an unchanged whole-parent Concept 1 PASS to
the residual area is also prohibited because it hides changes to non-connected
field/background geometry and nonlinear hillslope response. If the residual plan
is ineligible or cannot produce a valid area-correct source, hybrid fails that
parent/scheme with stable manifest provenance; it does not silently substitute
Concept 2.

#### Execution and validation contract

Hybrid writes only under
`wepp/ag_fields/watershed/hybrid/{runs,output,manifest}`. It stages exactly one
PASS per parent, runs watershed WEPP, regenerates isolated interchange resources,
and preserves the baseline, independent AgFields, legacy Concept 2, and sibling
scheme trees.

Fixtures must cover no/mixed/full connected coverage; connected sources above and
below non-connected fields; uncovered background; multiple connected sources;
overlap/gap; ineligible residual plans; OFE/scenario limits; climate/calendar
mismatch; and weighted serialization budgets. For mixed parents, validate raster
cell ownership, exact source-area closure, source/header areas, event/full-run
water and sediment closure, and the one-target-PASS rule.

The dev-project acceptance must route exactly 3,269 sub-fields through Concept 2
and 3,357 through Concept 1 when classifier inputs match the completed inventory.
Any count change requires recorded input/version evidence rather than silent
acceptance.

### Recommended delivery sequence

1. Continue the active
   [routing scheme suite ExecPlan](../../../../../docs/work-packages/20260714_ag_fields_routing_scheme_suite/prompts/active/ag_fields_routing_scheme_suite_execplan.md)
   through integrated Milestone 2B; its Peridot detail, planner census,
   explicit-breakpoint kernel, and mixed-parent proof are complete.
2. Inventory every generated management section, select the synchronized forest
   hillslope capacity, and execute every Concept 1/hybrid input tuple. Fix proven
   invalid source values at canonical AgFields ingest and finite-input numerical
   producer faults through forest ablation evidence.
3. Accept ADR-0019 only after the matching forest/WEPPpy limits, release evidence,
   complete passing corpus, and regression results are explicit. Do not ship a
   surrogate, omitted parent, clamped input, or silent fallback.
4. Then complete faithful Concept 1 hillslope execution, manifests, watershed
   execution, and remaining fixtures.
5. Build hybrid pure/mixed parent composition, reuse ADR-0018 weighted accounting,
   and prove area/water/sediment closure plus stable rejection behavior.
6. Move Concept 2 additively behind the current `concept-2` scheme root and evolve
   persisted state, authenticated API/RQ, serial Run All jobs, and the exact
   description-first UI contract with historical defaults.
7. Generate all three current trees through the authenticated path on
   `sacral-self-discipline`, prove protected artifacts byte-identical, complete
   security/QA/broad gates, and publish a self-contained comparison bundle.
8. Mariana Dobre performs the comparative scientific evaluation. Record her
   suitable-use guidance and limitations without substituting engineering
   judgment for that review.
