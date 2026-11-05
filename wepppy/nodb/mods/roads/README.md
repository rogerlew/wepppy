# Roads NoDb Controller

> Builds road contributor profiles and hillslope replacements from uploaded linework, reruns watershed routing, and publishes a separate Roads result set.

For project setup, input preparation, parameter editing and result interpretation,
start with the [Roads user guide](ENDUSER.md). This README covers implementation,
configuration and operations. See [NoDb conventions](../../AGENTS.md).

## Overview

`Roads` is a run-scoped NoDb controller for projects with a completed baseline
WEPP solution and WBT delineation. The feature registry classifies Roads as
experimental and requires PowerUser access or an authorized higher role.
It supports both inslope and outslope designs. Baseline outputs remain under
`wepp/output/`; Roads publishes separately under `wepp/roads/output/`.

The controller owns upload and mapping state, retained parameterization,
preparation, execution and report publication. Prepared eligibility, completed
execution and current report availability are distinct states. A prepared segment
or a successful background job alone does not establish usable current results.

## Design and execution paths

An overland flow element (OFE) is one modeled profile section with its own soil,
management and geometry. Multiple OFEs can contribute to one road-associated
profile; a profile export is therefore not necessarily road-prism-only export.

| Design | Flow representation | Executed profile / routing |
| --- | --- | --- |
| `Inslope_bd` | Bare-ditch point source | Channel-associated: road only; non-channel routed: road → buffer |
| `Inslope_rd` | Vegetated or rocked-ditch point source | Same routing branches as bare ditch, with different template selection |
| `Outslope_rutted` | Concentrated point source across fill | Road → fill → buffer, including channel-associated branches |
| `Outslope_unrutted` | Sheet-flow hillslope replacement | Landuse → road → fill, with downstream landuse when long enough; unaffected remainder contributors preserve hillslope area |

Design values are normalized case-insensitively. `outrut` resolves to rutted;
`outslope` and `outunrut` resolve to unrutted. Other designs are excluded.
Point-source preparation splits and orients monotonic line segments and identifies
low points. Non-channel hillslope low points require successful run-stage tracing
to a channel; unsuccessful traces are recorded as skipped contributors.

Unrutted replacement uses hillslope-specific overlap rather than requiring
point-source low-point delivery. Inclusion requires at least 10 m overlap and
an overlap-length / modeled-hillslope-width ratio of at least 0.60. At most three
qualifying crossings per hillslope are retained, ranked by descending overlap
length with segment-ID tie breaking. Required fill/buffer inputs, area closure,
and short downstream landuse handling are detailed in the
[implementation specification](specification.md#settled-step-4-contract-details-implemented-2026-04-08).

## Workflow and integration

1. Complete baseline WEPP and enable Roads through the project Mods control.
2. Upload a GeoJSON FeatureCollection containing LineString/MultiLineString roads.
3. Review discovered top-level properties, select design/surface/traffic mappings
   and fallbacks, and apply the mapping.
4. Optionally edit and save **Roads Parameterization** overrides.
5. **Prepare Segment Candidates** establishes current geometry and mapping evidence.
6. **Run WEPPcloud Roads** assembles native inputs, executes contributors, combines
   point-source responses or replaces unrutted hillslope responses, reruns the
   watershed, regenerates reports and publishes current results.

The [user guide](ENDUSER.md) includes a GeoJSON example, required unrutted fields,
exact UI actions and troubleshooting. New uploads or model-affecting settings
require a fresh Prepare and Run.

Roads inherits the baseline project's selected WEPP binary for segment runs and
the watershed rerun. Preparation and execution must use compatible releases;
version-3 PASS inputs cannot be assumed readable by an unversioned executable.
WBT flow tracing consumes Whitebox D8 pointers through `wepppyo3.roads_flowpath`,
which normalizes them in memory. TOPAZ-style subcatchment IDs do not imply TOPAZ
pointer encoding. See the [flow-direction contract](../../../../docs/schemas/roads-flow-direction-contract.md).

## Components

| Component | Responsibility |
| --- | --- |
| [roads.py](roads.py) | NoDb state, upload/mapping, preparation, contributor assembly, execution and queries |
| [monotonic_segments.py](monotonic_segments.py) | Line segmentation and low-point attribution |
| [parameterization.py](parameterization.py) | Retained baseline, validated role overrides and resolution |
| [_parameterization_comparisons.py](_parameterization_comparisons.py) | Execution input evidence and compatible retained-run comparisons |
| [_segment_loss_summary.py](_segment_loss_summary.py) | Mean annual source-profile loss summaries |
| `legacy_templates/` | Repository soil and management baseline assets |
| [roads_bp.py](../../../weppcloud/routes/nodb_api/roads_bp.py) | Run-scoped routes, parameterization view, reports and map queries |
| [roads_rq.py](../../../rq/roads_rq.py) | Prepare/run background jobs |
| [roads_pure.htm](../../../weppcloud/templates/controls/roads_pure.htm) | Run-page control and user-guide link |
| [roads.js](../../../weppcloud/controllers_js/roads.js) | Upload, mapping and job UI |
| [roads_parameterization.js](../../../weppcloud/controllers_js/roads_parameterization.js) | Parameter inspection, editing and comparison UI |

## Parameterization ownership and overrides

The approved [project/view contract](../../../../docs/schemas/roads-settings-contract.md)
defines the dedicated **Roads Parameterization** view and Roads-owned saved state.
The implementation passes the local browser/native/report and archive/restore/fork
workflow. The [program tracker](../../../../docs/work-packages/20261029_roads_parameterization_program/tracker.md)
records final regression/review gates and evidence. This is not a production
deployment or a new-default adoption.

| Authority | Contents | Consumers |
| --- | --- | --- |
| Repository baseline | Bundled soil/management templates plus documented selection and transformation rules in `roads.py` | First explicit project binding |
| Project `roads.nodb` | `_roads_params` for existing physical/mapping settings; `_parameterization` for retained baseline and overrides | Dedicated view, preparation and native-input assembly |
| Generated soil/management files | Resolved inputs and actual serialized values | Native WEPP execution and provenance readback |

The [repository baseline contract](../../../../docs/schemas/roads-parameterization-baseline-contract.md)
lists all 16 soil templates, both management templates, source values, units,
role mappings, traffic adjustments and native consumption. It is the default-value
and formula authority. Do not add independent defaults in the UI or make generated
files an editable parameter store. Shared Disturbed state is not the authority for
Roads template values.

`_parameterization` schema version 1 retains all 18 source texts and hashes, a
content-bound baseline identity, resolver version, and 12 override entries: four
drivers for each of `road`, `fill`, and `buffer`. Existing `_roads_params` values
are not copied into it. The buffer role means every template Forest row, including
unrutted upstream/remainder template Forest; independently sourced landuse is excluded.
The view reports whether repository assets match the retained baseline; a difference
or unavailable repository inspection never rebinds the project. The additive
`repository_baseline` query diagnostic describes this comparison without changing
result eligibility.

| Driver key | Unit | Native meaning |
| --- | --- | --- |
| `ksat_mm_h` | mm/h | Baseline effective hydraulic conductivity, legacy AVKE |
| `ki_kg_s_m4` | kg s/m4 | Interrill erodibility |
| `kr_s_m` | s/m | Rill erodibility |
| `critical_shear_pa` | Pa | Concentrated-flow detachment threshold |

An override is Default, Multiply, or Absolute. First resolve feature/fallback
choices and retained templates, then apply existing traffic and role adjustments,
then apply the override once. For example, gravel/loam road Ki starts at 2,000,000;
low traffic divides it by four to 500,000; Multiply by 2 resolves to 1,000,000.
Fill and buffer Ki do not receive the road traffic division. Conductivity changes
AVKE, not an unrelated horizon Ksat column. Overrides do not alter geometry,
management choice, surface/traffic labels or fragment content.

Save validates the complete override object and persists through Roads locking and
lifecycle guards. Values must be positive and remain finite/positive through native
conversion and serialization; zero invokes native estimation/bypass and is not an
off switch. Validity limits do not establish calibrated ranges or guarantee a
successful native run for extreme values.

### Binding, reset and retained evidence

A legacy read produces an unbound preview without changing saved state. First
explicit Save binds the baseline with the submitted overrides; first Prepare binds
default overrides. An already-prepared unbound project must Prepare before a new
Run. A bound project continues using its retained texts after repository updates.
**Reset overrides** changes the draft to Default; Save commits the reset against
the same project baseline. Adoption of newer repository defaults is separate and
is not a version-1 action.

Accepted model-affecting edits invalidate Roads preparation/results and retain
historical evidence. Geometry Prepare does not emit the final soil/management
files: assembly occurs during Run. The view distinguishes saved intent, preview
and values actually emitted for a recorded run. Mixed projects group differing
source resolutions instead of presenting one universal value. Compatible retained
runs may be compared using runoff/sediment totals and area-normalized values;
missing or incompatible evidence is explicit, never synthesized.

Fork/archive/restore must carry the single authoritative NoDb payload and its
retained baseline. Unsupported resolver versions or corrupt content are explicit
states, not permission to substitute current defaults. Use the reviewed repair
workflow for invalid state; never edit Redis cache, generated inputs or template
copies to repair authority. The baseline WEPP dataset remains independent.

### Runtime reload and validation

After authorized code updates, reload the web and applicable Roads workers through
the environment's canonical orchestration entry point before workflow validation.
Long-lived workers can otherwise keep old lifecycle decoding even when mounted
source files have changed. A source hash from a separate process does not prove
which code an existing worker loaded.

Validate the publication receipt's parameterization and comparison-snapshot hashes
against durable Roads state and actual generated inputs. If old worker code
produced an incomplete receipt, retain that failed attempt and explicitly Prepare
and Run again after reload; do not synthesize or patch a successful receipt.
Deployment remains governed by the normal operator workflow.

## Results and Artifacts

### What the user sees

After a successful Roads run, the WEPPcloud Roads UI and Roads results page expose:

- controller status and run summary state
- Roads-scoped report links
- regenerated resource inventory
- diagnostics JSON for `roads_status` and `roads_summary`

The Roads results summary page is rendered from [summary.htm](../../../weppcloud/templates/reports/roads/summary.htm).

Corrected aggregate water reports use full modeled road, fill, and buffer OFE
areas. At each receiving hillslope, road area replaces an equal amount of
baseline response. If roads exceed baseline area, modeled area expands to retain
the entire road footprint. This is response mixing; it does not estimate
geographic overlap or rerun a smaller residual hillslope.

The same area ledger weights canonical PASS before watershed routing and the
water products afterward. TotalWatSed counts each canonical PASS once and uses
weighted baseline plus road water profiles. The average hillslope water report
reads derived `H.accounting.wat.parquet`. Raw `H.wat.parquet`, dashboard OFE views,
and raw exports retain their diagnostic meaning. TotalWatSed diagnostic `Q` and
physical average-report runoff remain distinct quantities.

The ledger is `wepp/roads/segments/roads.accounting.json`. Missing or changed
corrected lineage requires a fresh Roads execution; copying files or rebuilding
reports alone does not certify old unweighted PASS. Historical unmarked results
remain historical. See the [accounting contract](../../../../docs/schemas/roads-water-accounting-contract.md)
for area authority, optional inputs, cache provenance, and compatibility.

### Important output locations

| Path | Purpose |
| --- | --- |
| `roads/roads.uploaded.geojson` | Staged copy of the uploaded source GeoJSON |
| `wepp/roads/roads.log` | Roads lifecycle and execution log |
| `wepp/roads/segments/roads.inslope.monotonic.geojson` | Prepared monotonic segment GeoJSON |
| `wepp/roads/segments/roads.inslope.low_points.geojson` | Low-point features for prepared segments |
| `wepp/roads/segments/roads.inslope.summary.json` | Prepare-stage summary diagnostics |
| `wepp/roads/segments/roads.segment.pass.manifest.json` | Segment run and pass-combination manifest |
| `wepp/roads/output/interchange/README.md` | Roads-scoped regenerated resource manifest |
| `wepp/roads/output/interchange/roads_segment_loss_summary.parquet` | Segment-level Roads loss summary |

The Road Segment Loss Summary contains mean annual exports from each completed
source profile, selected by `segment_run_id`. Receiving-hillslope IDs provide
routing context only. Volumes and sediment masses are averaged over the complete
simulation, including zero-export years; densities use the full modeled OFE area.
`profile_scope` distinguishes road, mixed-profile and replacement-remainder rows.
`sediment_leaving_buffer_kg` is unavailable (NULL); `road_prism_erosion_kg` is only
populated for proven single-OFE inslope road profiles. Use `sediment_yield_kg` for
full-profile export, not watershed-outlet yield or incremental road impact.

The `roads_segment_pass_v1` policy and source hashes identify corrected artifacts.
Existing historical summaries require regeneration; reading them does not upgrade
their values. Missing or invalid completed-source data fails regeneration and
preserves the prior summary. A failed publication may retain a visible
`roads_segment_loss_summary.pending-*.parquet` candidate for inspection; retry
rebuilds from original sources. See the [accounting contract](../../../../docs/schemas/roads-segment-loss-summary-contract.md)
for equations, units and validation rules.

### Report links

When regeneration succeeds, Roads results can include links such as:

- Watershed Loss Summary
- Return Periods
- Yearly Water Balance
- Daily Streamflow
- Average Annual Water Balance
- GL Dashboard
- Storm Event Analyzer
- Road Segment Loss Summary (`Parquet` and on-demand `CSV`)

These links are gated by the presence of Roads-scoped regenerated resources. If a required output is missing, the link is hidden rather than routed to stale baseline content.

## Configuration

`roads.nodb` owns the saved configuration. `_roads_params` is exposed as
`roads_params`; retained baseline texts and overrides live separately in
`_parameterization`. The run-page form exposes mapping and surface/traffic
fallbacks; the other settings below are controller/API settings, not additional
form controls. Use the validated controller/route mutation surface.

| Parameter | Default | Meaning |
| --- | --- | --- |
| `input_crs` | `EPSG:4326` | Used when GeoJSON has no `crs.properties.name` |
| `sample_step_m` | `null` | Optional elevation-profile sampling interval, m |
| `tolerance_m` | `0.5` | Monotonic segmentation tolerance, m |
| `soil_texture_default` | `loam` | Texture fallback: clay, loam, sand or silt |
| `surface_default` | `gravel` | Surface fallback: gravel or paved |
| `traffic_default` | `low` | Traffic fallback: high, low or none |
| `rfg_pct_default` | `20.0` | Rock fragment input fallback, percent |
| `road_width_m_default` | `4.0` | Road-width fallback, m |
| `fill_length_default_m` | `30.0` | Rutted fill-length fallback, m; not a substitute for required unrutted fields |
| `fill_slope_default_pct` | `10.0` | Rutted fill-grade fallback, percent |
| `trace_max_steps` | `20000` | Maximum downslope trace steps |
| `max_upload_mb` | `50` | Upload-size limit, MB |
| `attribute_field_map` | All three entries `null` | Top-level property names for design, surface and traffic |
| `attribute_discovery_profile_feature_limit` | `5000` | Maximum features profiled for discovery |
| `attribute_discovery_value_preview_limit` | `5` | Sample values retained per field |
| `attribute_discovery_value_max_chars` | `120` | Maximum sample-value text length |

Explicit surface/traffic mappings take precedence and use their selected fallback
when missing or invalid. Unset mappings check legacy keys first. Design has no
fallback class; inspect design diagnostics when features are excluded.
Finite-number validation distinguishes optional defaultable attributes from
required unrutted geometry. The [specification](specification.md) records accepted
aliases and per-path bounds. New uploads rediscover fields and attempt to preserve
mapping by matching field names; users must review the resulting mapping.

## Developer validation

The public package exports `Roads`, `MonotonicConversionSummary`, and the three
`convert_geojson_*_to_monotonic_segments*` helpers listed explicitly in
[__init__.py](__init__.py).

Focused checks for behavior changes:

```bash
wctl run-pytest tests/nodb/mods/test_roads_controller.py tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1
wctl run-pytest tests/nodb/mods/test_roads_parameterization.py tests/nodb/mods/test_roads_parameterization_comparisons.py --maxfail=1
wctl run-pytest tests/nodb/mods/test_roads_segment_loss_summary.py tests/wepp/interchange/test_roads_accounting.py tests/wepp/interchange/test_roads_lifecycle.py --maxfail=1
wctl run-pytest tests/weppcloud/routes/test_roads_bp.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
wctl run-npm test -- roads
wctl run-npm lint
```

Substantive code changes also require the repository-wide pytest gate. Changes to
native assembly or cross-process behavior require actual generated-input readback
and end-to-end execution evidence; unit tests are insufficient. The
[Roads validation suite contract](../../../../docs/schemas/roads-validation-suite-contract.md)
defines the native matrix and opt-in project checks.

## Operational Notes

- Roads persists to `roads.nodb` and follows standard NoDb locking semantics.
- Parameter changes and new uploads clear stale prepare/run summaries and return the controller to `idle`.
- Changing inputs, preparing again, or disabling Roads invalidates current results. Prior outputs, matching prepared geometry, execution inputs, and report caches are retained under `wepp/roads/history/` for explicit browsing.
- Only a successful full Roads run publishes `wepp/roads/output/roads.current.json`. Old beta outputs and postprocessing alone do not establish current results; prepare and run Roads again.
- Model reports and queries reject unavailable current results with 409 `roads_results_unavailable`. Generic browse/download and physical file previews expose actual files, including stale or partial outputs, subject only to security and PII guards ([filesystem contract](../../../../docs/schemas/browse-filesystem-contract.md)). A conflicting model mutation returns 409 `roads_operation_busy`.
- `roads.lifecycle.lock` is a persistent coordination file, not a stale-lock marker. Do not delete it to clear a conflict. Archive/restore preserves its inode and excludes it from archive payloads.
- The [preparation lifecycle contract](../../../../docs/schemas/roads-preparation-lifecycle-contract.md) defines publication, retention, and consumer admission. The shared implementation is `wepppy/wepp/interchange/_roads_lifecycle.py`.
- Warning diagnostics are summarized in prepare/run outputs when mapped fields are missing or invalid.
- Roads requires baseline WEPP outputs and does not replace the baseline `wepp/output/` dataset tree.
- Workspace staging retains `tc.txt` as an input but excludes the generated
  `tc_out.txt` diagnostic, so Roads execution preserves a baseline diagnostic
  still present in `wepp/runs/` after public-controller execution.

Project-page rendering reads saved upload and mapping inputs through `query_inputs()`.
It does not acquire the Roads lifecycle lock or inspect result artifacts, so an
active Roads operation cannot block loading the project. Result queries and reports
still use lifecycle admission. If a Roads report is busy, wait for the operation
to finish; do not delete the coordination lock.

## Documentation authority and further reading

The control links to [ENDUSER.md](ENDUSER.md) so setup and interpretation guidance
is available at the point of use. This README remains the developer/operator
reference; the existing Help model overview links to the detailed guide.

- [Implementation specification](specification.md): design branches, mapping, geometry and artifacts.
- [Parameterization baseline](../../../../docs/schemas/roads-parameterization-baseline-contract.md) and [project settings](../../../../docs/schemas/roads-settings-contract.md): current default and override authority.
- [Preparation lifecycle](../../../../docs/schemas/roads-preparation-lifecycle-contract.md): invalidation, retention and current-result admission.
- [Water accounting](../../../../docs/schemas/roads-water-accounting-contract.md) and [segment loss summary](../../../../docs/schemas/roads-segment-loss-summary-contract.md): output meaning and provenance.
- [Dashboard contract](../../../../docs/schemas/roads-gl-dashboard-contract.md): detachment visualization and output scope.

Read the current topic contracts alongside the implementation specification;
its phase-specific sections describe individual paths, not an inslope-only limit
on the current module. Study proposals and work-package evidence do not change
production defaults or a project's retained parameterization.
