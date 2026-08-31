# Correctness and User-Experience Review - WP02 Reader Foundation

## Metadata

- **Package**: `docs/work-packages/20260804_project_config_reader_foundation/`
- **Reviewer**: Codex, dedicated post-implementation evidence pass
- **Date**: 2026-08-26
- **Scope reviewed**: reader collaborator, NoDb facade/status, nested authority,
  parser and manifest fixtures
- **Commit/branch context**: uncommitted WP02 tree on
  `feature/project-owned-config` after `ceb10fc96`
- **Canonical contract**: `docs/schemas/project-owned-config-contract.md`
  sections 5, 6.1, 6.4, 10, and 15
- **Related security artifact**: `artifacts/2026-08-26_security_review.md`

## User Outcome

- **User goal**: reopen a project against the configuration captured when it
  was created, without mutable shared sources changing runtime values.
- **Success presented to the user as**: ordinary controller/model behavior uses
  the complete local flattened file; legacy projects behave as before.
- **Failures that may reach the user**: explicit `ProjectConfigError`,
  `ProjectConfigSchemaError`, or `ProjectConfigAuthorityError` for an unusable
  flattened file or unsafe nested authority.
- **Partial-state behavior**: a valid config with damaged provenance still
  loads, reports immutable warning status, and disables updates where required;
  reads never repair or partially write artifacts.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Reader flag absent / artifacts never created | yes | legacy reader unchanged | `test_facade_flag_off_preserves_legacy_reader` |
| Manifest absent | degraded-valid | flattened config loads; updates disabled | invalid-manifest matrix |
| Valid flattened config + manifest | yes | file loads alone; updates enabled | flattened and manifest-v1 fixtures |
| Supported legacy local/shared config | yes | defaults, preset, overrides retain layering | legacy layering fixture + WP01 suite |
| Malformed/hostile config or authority | no | explicit failure without fallback | schema, prefix, and symlink fixtures |
| Malformed/hostile manifest | degraded-valid | no fallback/write; safe warning; updates disabled | invalid/secret/symlink manifest fixtures |

## User-Reachable Error Policy

| Condition | Expected? | User-visible result | Justification |
| --- | --- | --- | --- |
| Malformed/unsupported flattened schema | expected invalid state | explicit reader error | contract 6.1 forbids fallback |
| Nested flattened child or escaping parent/config | expected hostile state | explicit authority error | contract 6.4 requires one contained root |
| Missing/invalid/newer manifest | expected degraded state | project remains usable; updates disabled | contract 6.1 |
| Digest mismatch | expected degraded provenance | project and registered amendment remain usable; warning exposed | contract 10 |

## Review Checks

- [x] Canonical intent is named and treated as authority.
- [x] Absent, populated, legacy, malformed, and hostile states are separated.
- [x] Flag/input and stored filesystem states are tested independently.
- [x] Direct temporary-file tests exercise parser, digest, and containment boundaries.
- [x] Security controls preserve valid legacy, flattened, nested, and degraded states.
- [x] No partial success writes exist; all paths are reader-only.
- [x] Existing workflows remain compatible while the flag is off.
- [x] Coverage claims name their dimensions; deployed/lifecycle proof is not claimed.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High | Digest mismatch | Initial design risked treating every inconsistency as update-disabled, contrary to amendment-safe warning policy. | contract 10 + digest test | Keep `updates_enabled=True` for digest mismatch alone. | Resolved |
| COR-02 | Medium | Runtime state | Reader status/deduplication fields could enter persisted NoDb JSON. | `NoDbBase.__getstate__` | Remove both transient fields from serialization. | Resolved |
| COR-03 | Medium | UI handoff | WP02 cannot claim authenticated header presentation. | roadmap WP09 | Expose immutable status and explicitly retain UI acceptance in WP09. | Resolved by scoped handoff |

## Verdict

- **Gate status**: pass for WP02 reader scope
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: ship dormant on the initiative branch; hold
  deployment activation for WP11
- **Reviewer sign-off**: Codex, 2026-08-26
