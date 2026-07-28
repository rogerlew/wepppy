# DOM-08A Landuse Build Field and Action Matrix

| Rendered identity/action | Controller behavior | Downstream boundary | Evidence |
| --- | --- | --- | --- |
| `landuse_mode` values `0`, `1`, `4` | Chooses mode and exposes the matching controls | `set-landuse-mode` / Landuse state | Actual render + existing controller/route tests |
| `input_upload_landuse` | Browser FormData carries optional `.img`/`.tif` upload | Build route user-defined upload path | Actual render + existing upload route tests |
| `landuse_management_mapping_selection` | Browser FormData carries mapping key | Mapping normalization/user-defined persistence | Actual render + FormData Jest + existing route tests |
| `mofe_buffer_selection` | Browser FormData preserves selection | `Landuse.parse_inputs` | Multipart route regression |
| `checkbox_burn_shrubs`, `checkbox_burn_grass` | Checked values submit; unchecked values are absent | Disturbed grouped update | Actual render + FormData Jest + multipart route regression |
| `btn_build_landuse` / `hint_build_landuse` | Posts multipart to build route and tracks job | `build_landuse_rq`, completion report reload | Actual render + existing controller/worker tests |

Excluded: catalog/editor/map UI (DOM-08B), modifier UI (DOM-09), mapping
algorithms, authorization/CSRF, and queue wiring are not changed.
