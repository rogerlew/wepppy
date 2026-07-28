# DOM-09 Landuse Modifier Field and Action Matrix

| Rendered identity/action | Controller behavior | Downstream boundary | Evidence |
| --- | --- | --- | --- |
| `checkbox_modify_landuse` | Enables click/box selection and map drilldown suppression | Subcatchment GeoJSON and intersection route | Actual render + Jest |
| `textarea_modify_landuse` | Hydrates normalized selected Topaz IDs | `topaz_ids` JSON array | Actual render + Jest |
| `selection_modify_landuse` | Selects replacement landuse code | `landuse` JSON string | Actual render + Jest |
| `btn_modify_landuse` | Posts exact native payload with run session token | RQ-engine authorization/validation and `Landuse.modify` | Actual render + Jest + route tests |
| Status/stacktrace panels | Present success or canonical failure | Browser lifecycle | Actual render + Jest |

The route mutates synchronously and does not enqueue a build job. DOM-08A owns
Landuse build lifecycle.
