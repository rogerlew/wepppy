# Correctness and user-experience review

Independent scaffold review, 2026-11-22 UTC. Baseline `94ad6360266a`. The contract reviewer examined current behavior and the proposed contract. The test guardian checked coverage, test names, the ExecPlan and the live protocol. The operations/security reviewer examined the actual-project design. Implementation sign-off is open.

| Finding | Disposition and regression obligation |
| --- | --- |
| Duplicate IDs or conflicting keys could survive a set-only comparison; lookup may select the last entry. | Added explicit failure semantics, valid shared references and listing/lookup assertions to the contract and M1. |
| Layer metadata, geometry and dependency IDs contribute to export identity. SWAT and carrier paths inspect raw locator values. | Pin catalog signature, both hash modes, dependency entries, cache key and legacy locator representation. Include geometry, multi-table and dependency-only controls. |
| Export can retain a legitimate parent-relative spelling forbidden as untrusted query input. | Compare outward spelling and authorized physical identity independently. Include positive inheritance and denied sibling cases. |
| Generic expansion could introduce Omni × Roads paths or substitute baseline data when Roads is unavailable. | Keep existing scope-specific expansion. Check that explicit unavailable Roads requests retain the unavailable outcome. |
| Simple row counts can pass with incorrect source selection. Producer fixtures can miss watershed migration. | Require distinguishable Parquet values, independent writer and consumer references, and Peridot tests for both existing Parquets and legacy CSV migration. |

The evidence chain runs from producer destination and receipt through published catalog, selected Parquet, query and exported layer. Actual-project readback and isolated full publishing workflows remain pending.

Scaffold verdict: pass. The contract reviewer rechecked duplicate-key disposition against the staged contract, scoped tests and production protocol. Reviewed contract SHA-256: `95be492c8439a68b238347cae28b0e9ed8ac6bfed3666df01074b9f8e3f8962a`.
