# Correctness and User-Experience Review - Project Config Registry and Serializer

## Metadata

- **Package**: `docs/work-packages/20260804_project_config_registry_serializer/`
- **Reviewer**: Codex, separate static-review pass
- **Date**: 2026-08-26
- **Scope reviewed**: registry schema/loader, profiles, resolver, stubs, and focused tests
- **Commit/branch context**: `feature/project-owned-config`, starting at `8ee87a2e6`
- **Canonical contract(s)**: `docs/schemas/project-owned-config-contract.md` sections 7.2, 7.5, 8, and 8.2
- **Related QA/security artifacts**: `artifacts/20260826_registry_serializer_evidence.md`; dedicated security review not required (`low`)

## User Outcome

- **User goal**: later builder code can describe and resolve only registered,
  supported project configurations into deterministic canonical bytes.
- **Success presented to the user as**: a typed description or an in-memory
  result containing canonical bytes, selections, parent provenance, cell-size
  provenance, and effective writers.
- **Failures that may reach the user**: field-addressable
  `BuilderConstraintError` for unknown, incompatible, duplicate, or invalid
  selections; deployment-owned source defects raise `RegistryError`.
- **Partial-state behavior**: none. Loading and resolution are read-only and
  publish no partial registry, project, manifest, or config file.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Registry source absent | no | explicit no-documents failure | loader contract path |
| Registered zero-write climate/mod set empty | yes | resolve without invented runtime writes | local matrix and dormant-mod tests |
| Shipped registry populated | yes | validate all documents before exposure | stable-ID/corpus test |
| Canonical shared defaults supplied | yes | preserve input and resolve from a copy | snapshot-independence test |
| Malformed or hostile TOML | no | bounded explicit failure, no partial registry | invalid-document tests |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Unknown selection ID | expected validation | field plus `unknown_component` | contract forbids substitution |
| Unsupported locale combination | expected validation | field plus `unsupported_combination` | locale allowlist is authoritative |
| Invalid cell size | expected validation | `cellsize_override` plus `invalid_cellsize` | section 7.5 closed set |
| Undeclared component collision | deployment defect | explicit `undeclared_writeover` | section 8 ownership contract |
| Invalid TOML/schema/reference | deployment defect | `RegistryError`, no registry returned | section 8.2 atomic validation |

## Review Checks

- [x] Canonical intent is named; tests are evidence, not behavioral authority.
- [x] Absent, empty, populated, supported base, and hostile states are addressed.
- [x] Selection combinations and registry/default state were reviewed separately.
- [x] Direct tests exercise real `tomllib` and WP00B serialization boundaries.
- [x] Mocks do not replace either changed boundary.
- [x] The WP00A sanitization boundary remains active for every serialized result.
- [x] There is no partial success, readiness, retry, or cleanup state in WP03.
- [x] Selection errors are field-addressable and do not silently substitute.
- [x] Existing creation workflows are not wired to the dormant resolver.
- [x] The four-combination claim is limited to the two ratified DEMs by two ratified backends and explicitly excludes Forest acceptance.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | stable climate IDs | Initial implementation used hyphenated climate IDs instead of the ratified underscore tokens. | contract section 7.2.1 versus initial TOML pass | permit underscore IDs and use exact tokens throughout | Resolved |
| COR-02 | Low | registry validation | Duplicate ownership declarations and missing/non-positive DEM defaults were not rejected at load time. | loader review | add atomic schema checks and regression coverage | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: `ship` as dormant WP03 core; do not claim Forest acceptance
- **Reviewer sign-off**: Codex, 2026-08-26
