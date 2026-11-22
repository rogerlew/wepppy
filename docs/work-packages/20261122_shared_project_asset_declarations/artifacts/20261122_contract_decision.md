# Contract decision — shared project assets

Starting implementation revision: `94ad6360266a`. Intent: a faithful extraction shared by asset writers, Feature Export and the query engine. The operator selected consolidation and retained the layer catalog within Feature Export. This package prepares the checkpoint; it does not attest runtime conformance.

| Authority | Decision for the first slice |
| --- | --- |
| [Shared declarations](../../../schemas/shared-project-asset-declarations-contract.md) | One producer-owned logical rule and explicit scope parameters. Preserve public naming and consumer-specific resolution. |
| [Feature Export specification](../../../../wepppy/nodb/mods/features_export/specification.md) and its layer catalog | Retain joins, IDs, selector validation, missing/optional behavior and dependency/cache identity. |
| [Query catalog](../../../schemas/query-engine-catalog-refresh-contract.md) and [HTTP access](../../../schemas/query-engine-http-access-contract.md) | Preserve root binding, source authorization, publication and freshness for direct and qualified queries. |
| [Output scope](../../../schemas/output-scope-contract.md) | Preserve baseline/Roads mapping and currentness rules, including unavailable outputs. |

The contract-first gate is a committed ancestor of implementing code. Before implementation, verify the independent review disposition against the exact checkpoint, confirm the agreed scope and resolve remaining contract conflicts. Changes to visibility, cache identity, layer catalog semantics or deployment require explicit disposition outside this faithful extraction. [Review record](20261122_correctness_review.md)
