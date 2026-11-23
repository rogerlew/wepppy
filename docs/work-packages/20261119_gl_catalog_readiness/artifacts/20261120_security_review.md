# GL catalog readiness security review

Independent reviewer `contract_security` accepted the reviewed source on
2026-11-20 UTC. The scope is GL-CATALOG-01 on `task/gl-catalog-readiness`
after contract checkpoint `fdba3295c`.

Impact is high because authorized browser operations can register durable
project maintenance. Ready reads for public, private and legacy projects must
continue through the existing authorization boundary.

| Finding | Severity | Resolution and evidence |
| --- | --- | --- |
| Background refresh could lose the HTTP source boundary | High | Derive the exact managed parent and bind the worker's source policy. Real workers published a valid inherited watershed source and refused a private sibling location. |
| Old workers could accept browser-preparation jobs | High | Advertise browser containment capability through the existing worker and admission checks. Real Redis rejects incompatible registration. Operator guidance requires old schedulers and workers to retire before browser activation. |
| Observation and receipt creation could straddle project replacement | Medium | Pass the checked identity and incarnation into the guarded mutation and recheck the canonical path and authorization there. The replacement regression verifies no refresh metadata is written into the new directory. |
| Public prepare could amplify work or admit on cross-site requests | Medium | Require same-origin proof for browser writes, bound guarded receipt writes and Redis operations, and use existing scheduler admission. Tests cover missing origin proof, out-of-scope selectors, held lifecycle guard, and durable receipt after dispatch failure. |
| Malformed project metadata could cause a disclosure or status-side write | Medium | Validate retained metadata and return fixed safe status responses. The corrupt-marker test verifies no exception log, receipt or worker side effect. |

The scoped source gate passed with no unresolved high or medium findings.
Production activation requires verified scheduler, Query Engine, and worker
configuration parity, capability fencing, and drain evidence. Rollback must
drain browser-generated receipts before older unscoped workers can consume
them. [Operator procedure](../../../dev-notes/query-catalog-refresh-operations.md#gl-dashboard-readiness)
