# SURF-11 Geneva Summary Contract Matrix

| Boundary | Risk-bearing contract | Verified evidence |
| --- | --- | --- |
| Report shell | title, run context, no-store response | render + route |
| Payload seed | one JSON node with validated summary payload | direct render |
| Filters | datasource/ARI/measure identities and selected values | render + Jest |
| Selection | chart marker/table row/selected storm synchronization | Jest |
| Unitizer | chart/table/map labels and values refresh on preference event | Jest |
| HRU map | embedded run URLs, schema version, storm/measure request | render + Jest + route |
| Availability | NOAA, empty, legacy unavailable, and error targets | render + Jest + route |
| Security | authorization/run scoping, validation, no-store, safe rendering | route + review |
| Initialization | exactly one production init when report root exists | controller lifecycle Jest |

No RQ or persisted-state mutation is owned by SURF-11.
