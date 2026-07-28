# DOM-10 Soils Field and Action Matrix

| Rendered identity/action | Browser/downstream behavior | Evidence |
| --- | --- | --- |
| `soil_mode` values `0`, `1`, `2` | Native mode selection persisted by Flask route | Actual render + Jest + route |
| `initial_sat` | URL-serialized build input | Actual render + Jest + RQ-engine |
| `soil_single_selection`, `soil_single_dbselection` | Native integer/database selection | Actual render + Jest + route |
| `checkbox_ksflag`, `clear_ssurgo_cache_on_rebuild` | Boolean state/build-cache option | Actual render + Jest + route |
| `sol_ver` when disturbed | Disturbed version update/build input | Jest + route/schema tests |
| Build button/hint/status/stacktrace | Enqueue, poll, and hydrate completion | Actual render + Jest + RQ/worker |

Upload-specific soils behavior is absent from this rendered controller and is
therefore not a DOM-10 field seam.
