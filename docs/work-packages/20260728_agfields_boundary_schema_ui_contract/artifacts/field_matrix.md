# DOM-13A AgFields Boundary/Schema Field and Action Matrix

| Rendered identity/action | Downstream behavior | Evidence |
| --- | --- | --- |
| `field_boundaries` GeoJSON input | Multipart upload validates extension/size and updates boundary inventory | Actual render + Jest + RQ-engine route |
| `field_id_key`, `rotation_accessor` | Schema confirmation validates atomically and persists the selected mapping | Actual render + Jest + route |
| `agfields_min_area` | Serialized as the sub-field minimum-area threshold for queued delineation | Actual render + Jest + route/enqueue |
| Upload/schema/build actions and status roles | Hydration communicates boundary, schema, and sub-field lifecycle state | Actual render + Jest |

The package does not alter geospatial validation, authorization, or queue wiring.
