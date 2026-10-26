# Browse and Download

Canonical authority: [Browse filesystem contract](../../../docs/schemas/browse-filesystem-contract.md).

- Generic browse, file inspection, previews, downloads and aria2c inventories must reflect actual filesystem contents.
- Only security and PII protections may restrict existing files: preserve authentication, authorization, containment and sensitive-path checks.
- Do not add model-status, publication-receipt, stale-result or lifecycle filtering/locks to generic file access. Do not reintroduce per-entry filesystem resolution for model eligibility.
- Model reports, computations and dashboards own model-result eligibility. Generic file access does not certify results.
- Preserve explicit user-selected search/sort/pagination and ordinary filesystem/read errors. Raw files remain accessible when an optional representation cannot parse them.
- Validate actual listing/manifest/byte delivery for partial and legacy files alongside negative auth, traversal, symlink-escape and PII cases.
