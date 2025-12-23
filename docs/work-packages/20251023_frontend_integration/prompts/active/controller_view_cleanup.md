# Controller View Cleanup Findings

## Snapshot
- Verified every control included by `runs0_pure.htm` has a live controller in `wepppy/weppcloud/controllers_js/`; no missing bindings were found.
- Legacy Bootstrap-era views that extend `controls/_base.htm` are no longer referenced by Flask routes or templates—17 templates (plus 15 advanced-option partials) can be archived.
- Non-runs0 templates that remain in service (`archive_console_control.htm`, `fork_console_control.htm`, report views, etc.) were catalogued so we avoid accidental removal.
- Existing documentation (notably `docs/ui-docs/control-ui-styling/control-inventory.md`) still references several legacy templates and will need an update once cleanup lands.

## Active Pure Controls
| Template | JS controller(s) | runs0 anchor | Notes |
| --- | --- | --- | --- |
| `controls/map_pure.htm` | `MapController`, `LanduseModify`, `RangelandCoverModify` | `#map` | Always loaded; embeds `modify_landuse.htm`, `modify_rangeland_cover.htm`, and the hillslope visualization partials. |
| `controls/disturbed_sbs_pure.htm` | `Disturbed`, `Baer` | `#disturbed-sbs` | Only rendered when mods `"disturbed"` or `"baer"` (excluding `"lt"`). Hosts SBS upload + uniform toggles. |
| `controls/channel_delineation_pure.htm` | `ChannelDelineation` | `#channel-delineation` | Core hydrology setup. |
| `controls/set_outlet_pure.htm` | `Outlet` | `#set-outlet` | Locks down watershed outlet selection. |
| `controls/subcatchments_pure.htm` | `SubcatchmentDelineation` | `#subcatchments-delineation` | Drives subcatchment tessellation workflow. |
| `controls/rangeland_cover_pure.htm` | `RangelandCover` | `#rangeland-cover` | Conditional on `"rangeland_cover"` mod; works with modify panel under map tabs. |
| `controls/landuse_pure.htm` | `Landuse` | `#landuse` | Landuse database + mode management. |
| `controls/climate_pure.htm` | `Climate` | `#climate` | Loads station selection, scaling, and monthly summaries (rendered via API). |
| `controls/rap_ts_pure.htm` | `RAP_TS` | `#rap-ts` | Only present when `"rap_ts"` mod enabled. |
| `controls/soil_pure.htm` | `Soil` | `#soils` | Manages soil DB selection and validation. |
| `controls/treatments_pure.htm` | `Treatments` | `#treatments` | Rendered for `"treatments"` mod; shares StatusStream wiring with main controls. |
| `controls/wepp_pure.htm` | `Wepp` | `#wepp` | Primary WEPP runner plus includes for `wepp_pure_advanced_options/*`. |
| `controls/ash_pure.htm` | `Ash` | `#ash` | Conditional on `"ash"` mod; toggles ash depth outputs. |
| `controls/rhem_pure.htm` | `Rhem` | `#rhem` | Conditional on `"rhem"` mod; mirrors RHEM job lifecycle. |
| `controls/omni_scenarios_pure.htm` | `Omni` | `#omni-scenarios` | Renders Omni scenario builder when `"omni"` mod active. |
| `controls/omni_contrasts_pure.htm` | `Omni` | `#omni-contrasts` | Displays contrast runner alongside scenarios. |
| `controls/path_cost_effective_pure.htm` | `PathCE` | `#path-cost-effective` | Only visible with `"path_ce"` mod. |
| `controls/observed_pure.htm` | `Observed` | `#observed` | Conditional on observed datasets being present. |
| `controls/debris_flow_pure.htm` | `DebrisFlow` | `#debris-flow` | Requires `"debris_flow"` mod and `PowerUser` role. |
| `controls/dss_export_pure.htm` | `DssExport` | `#dss-export` | Hidden automatically when DSS export mod disabled. |
| `controls/team_pure.htm` | `Team` | `#team` | Shared collaborator management panel. |

### Run Shell Includes
| Template | Purpose | Notes |
| --- | --- | --- |
| `controls/poweruser_panel.htm` | Preflight + admin shortcuts | Still tied to `preflight.js` and report templates. |
| `controls/unitizer_modal.htm` | Unit conversion modal | Consumed by `input-unit-converters.js`; embeds `controls/unitizer.htm`. |
| `controls/unitizer.htm` | Unitizer body | Modal content shared with reports and UI showcase. |

## Shared Partials & Supporting Templates
- `controls/modify_landuse.htm` and `controls/modify_rangeland_cover.htm` live under the map tabset and are wired through `LanduseModify`/`RangelandCoverModify`.
- `controls/map/rhem_hillslope_visualizations.htm` and `controls/map/wepp_hillslope_visualizations.htm` provide the optional hillslope overlays toggled by the map controller.
- `controls/wepp_pure_advanced_options/*.htm` (15 files) are included from `wepp_pure.htm` and remain active.
- `controls/climate_monthlies.htm` is rendered by the climate blueprint for the monthlies panel (AJAX response).
- `controls/edit_csv.htm` is served by `nodb_api/disturbed_bp.py` for CSV-in-place edits.

## Templates Still Used Outside runs0
- `controls/archive_console_control.htm` – rendered by `routes/archive_dashboard`.
- `controls/fork_console_control.htm` – rendered by the fork console route.
- `controls/rhem_reports.htm` – used by `nodb_api/rhem_bp.py`.
- `controls/wepp_reports.htm` – used by `nodb_api/wepp_bp.py`.
- `controls/unitizer_modal.htm` – additionally referenced by `templates/ui_showcase/component_gallery.htm`.

## Legacy / Orphan Templates (no runtime references)
| Template(s) | Last hits | Recommendation |
| --- | --- | --- |
| `controls/ash.htm` | Removed (legacy) | Superseded by `ash_pure.htm`. |
| `controls/baer_upload.htm` | Removed (legacy) | Superseded by `disturbed_sbs_pure.htm`. |
| `controls/climate.htm` | Removed (legacy) | Pure climate control covers all use cases. |
| `controls/debris_flow.htm` | Docs only | Replaced by `debris_flow_pure.htm`. |
| `controls/dss_export.htm` | Removed (legacy) | Replaced by `dss_export_pure.htm`. |
| `controls/export.htm` | Removed (legacy) | Functional overlap now lives under DSS export + reports. |
| `controls/landuse_legacy.htm` | Removed (legacy) | Pure landuse control in use. |
| `controls/observed.htm` | Removed (legacy) | `observed_pure.htm` is the active view. |
| `controls/omni/omni_contrasts_definition.htm`, `controls/omni/omni_scenarios.htm` | Docs only | Legacy Bootstrap Omni views; archive alongside other `_base` templates. |
| `controls/rangeland_cover.htm` | Removed (legacy) | Legacy view, no runtime calls. |
| `controls/rap_ts.htm` | Removed (legacy) | Superseded by `rap_ts_pure.htm`. |
| `controls/rhem.htm` | Removed (legacy) | Pure RHEM panel is the sole implementation. |
| `controls/road_upload.htm` | Removed (legacy) | No routes reference this control anymore. |
| `controls/set_outlet_legacy.htm` | Removed (legacy) | Obsoleted by `set_outlet_pure.htm`. |
| `controls/soil_legacy.htm` | Removed (legacy) | Pure soil control in use. |
| `controls/team.htm` | Removed (legacy) | Team management now relies exclusively on the Pure view. |
| `controls/wepp.htm` | Removed (legacy) | Pure WEPP panel replaces it. |
| `controls/wepp_advanced_options/*.htm` | Removed (legacy) | Superseded by `controls/wepp_pure_advanced_options/*.htm`. |

> All entries above were validated with `rg -l 'controls/<name>.htm'` and `rg -n '<name>.htm'`; only documentation files surfaced for these templates.

## Documentation Updates Needed
- `docs/ui-docs/control-ui-styling/control-inventory.md` – drop references to legacy `_base` templates and confirm Pure coverage.
- `docs/ui-docs/control-ui-styling/control-components.md` and related mod-specific plans – flag that Bootstrap templates have been retired or moved to archive storage.
- `wepppy/weppcloud/controllers_js/README.md` – keep narrative snippets aligned with the Pure templates (`*_pure.htm`) now that legacy views (for example `wepp.htm`) are removed.

## Recommended Next Steps
1. Move the orphaned `_base` templates (and their advanced-option includes) into an archival folder under `docs/work-packages/20251023_frontend_integration/legacy_controls/` or delete them outright after doc updates.
2. Regenerate `controllers-gl.js` after template removal (`python wepppy/weppcloud/controllers_js/build_controllers_js.py`) and rerun the Pure controls render smoke test (`wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py`).
3. Update the documentation set listed above so the control inventory reflects only live templates.
4. Announce the cleanup in the work-package retrospective (`docs/work-packages/20251023_frontend_integration/lessons_learned.md`) once merged.

## Commands Audited
- `rg -l "controls/<template>.htm"` and `rg -n "<template>.htm"` across the repo to trace runtime references.
- `sed -n` inspections of `runs0_pure.htm`, supporting templates, and controller modules for cross-checking.
