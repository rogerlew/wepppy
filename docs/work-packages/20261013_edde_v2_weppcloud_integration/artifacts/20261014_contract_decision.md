# EDDE-WEPP-01 contract checkpoint

Starting revision6acfb3d23. Operator explicitly requested execution of this package after approving raw future EDDE, no additional bias/elevation correction, and the precedented CLIGEN hybrid. This checkpoint specifies implementation choices within that authorized scope; no deployment or unrelated owner initiative is advanced.

Canonical set: edde-v2-weppcloud-contract.md, edde-v2-experimental-client-contract.md, ADR-0091/0092, prism-spatialization-temperature-contract.md, project-owned-config-contract.md, rq-engine-agent-api-contract.md, rq-response-contract.md, nodb-persistence-concurrency-contract.md, climate-parquet-lineage-contract.md, climate-precipitation-scaling-contract.md, docs/ui-docs/controller-contract.md and climate-cligen-seed-contract.md. Existing feature-menu metadata is unchanged (dataset within Climate, not a new feature gate). Existing archive/browser/auth contracts apply unchanged.

Normative delta: additive mode17/catalog future_edde_v2 in US/Canada and eligible legacy locales; one required projection choice, future-year bounds with live inventory checks; Single/Multiple only; per-location grid and PRISM checks; isolated yearly acquisition and retained project attempts; source/auxiliary-field attribution and all-or-nothing staged build finalization. No new queue, auth policy, automatic station substitution, quality bypass, source correction or persisted graph migration.

Compatibility plan: old NoDb lacks optional projection/provenance and continues existing methods; selecting EDDE creates fields only when needed. Parse failures rollback; no existing keys renamed. Register additive ordinary/single-input capability shapes in reader floor before current graph writers. Existing graphs preserve exact identities/choices until explicit refresh. Generated CLI schema and WEPP preparation remain unchanged; tests and actual prepared-file readback verify propagation.

State matrix: absent/empty selection can render but cannot submit EDDE without explicit projection/years; populated valid selection builds; legacy methods/graphs remain readable and rebuildable; stale/malformed/hostile input rejects without partial state. Invalid grid/land, unavailable months, invalid normals, partial acquisition, CLIGEN failures and superseded inputs retain failed evidence and previous publication. Completed attempts and failed attempts remain browser/archive accessible under existing authorization.

Security impact high: existing authenticated build endpoint now triggers bounded public acquisition and model execution. Dedicated final security review required. Regression evidence spans exact source/CLI/WEPP boundaries, state rollback/supersession, malicious input, auth, browser/archive, stored graph compatibility, source/seed attribution and configured runtime identity. No mock can stand in for the changed filesystem/publication boundary.

Two independent read-only reviews and their dispositions are required before this checkpoint is committed. Implementation conformance pending.

Disposition: both independent reviews pass after clarifying scaling modes/staged publication, PRISM normal checks and automatic seed invocation in ADR-0091. No unresolved medium/high contract findings. Runtime acceptance remains pending.
