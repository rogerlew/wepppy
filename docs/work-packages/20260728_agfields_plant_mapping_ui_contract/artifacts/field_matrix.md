# DOM-13B AgFields Plant Mapping Field and Action Matrix

| Rendered identity/action | Downstream behavior | Evidence |
| --- | --- | --- |
| `plant_database` `.zip` input | Archive upload validates and enqueues plant processing | Actual render + Jest + RQ-engine route |
| Open mapping action/modal | Loads persisted crop, management, and plant-file inventory | Actual render + Jest + route |
| Mapping table/save action | Validates and persists crop-to-management rows | Actual render + Jest + route |
| Unused-mapping region | Retains and displays non-current mappings without silent deletion | Actual render + Jest |
