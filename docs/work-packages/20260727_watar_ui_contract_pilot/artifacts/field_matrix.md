# DOM-01 WATAR/Ash Field Matrix

**Date**: 2026-07-28 UTC

This is the concise intended/observed record for DOM-01. A field is included
when its value changes submitted, persisted/reloaded, queued, or visible
workflow state.

| Field group | Rendered identity and state | Downstream contract | Evidence |
| --- | --- | --- | --- |
| Fire date | `id`/`name` `fire_date`; current stored date is rendered | `run-ash` passes it to `run_ash_rq`; `Ash.run_ash` persists the date | Existing controller/RQ tests plus `test_project_rq_ash.py` |
| Depth mode and depth values | radio `name="ash_depth_mode"`, tokens `0`, `1`, `2`; `ini_black_depth` and `ini_white_depth` render by canonical names | rq-engine validates the mode, persists it, and queues derived depths | Actual-template and rq-engine route tests |
| Load mode and bulk density | `ini_black_load`, `ini_white_load`, `field_black_bulkdensity`, and `field_white_bulkdensity` render by canonical names | rq-engine validates numeric values and derives depths before queuing | Actual-template and existing rq-engine route tests |
| Map upload mode | `input_upload_ash_load` and optional `input_upload_ash_type_map`; accepted extensions are `.tif`, `.tiff`, `.img` | rq-engine saves validated uploads to Ash state before a run | Actual-template, controller upload validation, and rq-engine upload tests |
| Wind transport | `checkbox_run_wind_transport` renders as the current checked or unchecked state | controller posts `{run_wind_transport: boolean}` to the dedicated Flask route; route persists both states in `Ash.run_wind_transport` | Controller and `test_watar_bp.py` regression tests |
| Model and transport selectors | DOM ids remain `ash_model_select` and `ash_transport_mode_select`; submitted names are `ash_model` and `transport_mode`; selected values reload | rq-engine accepts canonical names and legacy aliases, rejects conflicts, and `Ash.parse_inputs` persists model parameters | Actual-template, controller FormData, and rq-engine persistence tests |
| Advanced model parameters | rendered names match parser keys, including bulk density, erodibility, organic matter, initial transport capacity, and depletion coefficient | `Ash.parse_inputs` stores the applicable Alex or Srivastava parameter object; the template reloads that object | Actual-template and rq-engine parameter persistence tests |

## Exclusions

Reports, calculation results, and controller status/hint nodes are read-only
presentation in this pass. Calibration formulas, defaults, units, and model
output are out of scope because DOM-01 changes no parameterization.

## Historical Selector Mismatch

The historical defect was a DOM-id/submitted-name mismatch for the model and
transport selectors. The current actual-template test requires the canonical
submitted names and explicitly rejects the DOM ids as names. The DOM-01 audit
found the production template already conforms, so no production patch is
needed; the retained regression fails if the old names return.
