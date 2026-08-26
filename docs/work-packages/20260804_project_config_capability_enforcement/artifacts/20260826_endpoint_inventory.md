# WP05 Capability Endpoint Inventory

| Domain | Presentation authority | Submission authority | Stable ID/runtime mapping |
| --- | --- | --- | --- |
| Climate | run-page `climate_catalog` and `/query/climate_catalog`, both through `ClimateStationCatalogService` | Flask `set_climate_mode` and rq-engine `build-climate`, both resolve catalog IDs through the same service | existing `ClimateDataset.catalog_id` |
| Soil | `controls/soil_pure.htm`, filtered by `soil_capability_modes` | Flask `set_soil_mode` before controller mutation | `gridded` -> 0; `single_mukey` -> 1; `single_database` -> 2 |
| Land use | `Landuse.landcover_datasets`, consumed by the run-page select | rq-engine `set-landuse-db` before controller mutation | existing land-cover catalog key |

Existing persisted climate/soil/land-use state remains the controller's current
state even if absent from newly offered options. Legacy projects have no
`[capabilities]` authority and bypass every new filter/validator.
