# DOM-07 Subcatchment Field and Action Matrix

| Rendered identity/action | Controller behavior | Downstream boundary | Evidence |
| --- | --- | --- | --- |
| `pkcsa`, `pkcsa_en` | WBT rendering submits fixed `-1` sentinels | Build route preserves applicable options | Actual render + Subcatchment Jest |
| `mofe_target_length`, `mofe_max_ofes` | Serializes MOFE values unchanged | Route coerces and applies grouped update | Actual render + Jest + route test |
| `mofe_buffer`, `mofe_buffer_length` | Serializes enabled buffer state/value | Route coerces and applies grouped update | Actual render + Jest + route test |
| `btn_build_subcatchments` | Posts form JSON to build endpoint | Build/abstract parent RQ job | Actual render + Subcatchment Jest |
| Parent RQ job | Enqueues subcatchment build before abstraction | `build_subcatchments_and_abstract_watershed_rq` | Worker-chain unit test |
| Completion/reload | Loads built subcatchment data after completion | Existing GL completion tests | Existing Subcatchment Jest |

Excluded: algorithms, map/layer behavior, auth/CSRF, and queue wiring are not
changed. Any production change to those surfaces requires re-triage.
