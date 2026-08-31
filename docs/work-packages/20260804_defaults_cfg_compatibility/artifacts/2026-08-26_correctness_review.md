# Correctness and User-Experience Review - Defaults CFG Compatibility (WP01)

## Metadata

- **Package**: `docs/work-packages/20260804_defaults_cfg_compatibility/`
- **Reviewer**: Codex (dedicated correctness pass)
- **Date**: 2026-08-26
- **Scope reviewed**: shared defaults rename/symlink, ordered resolver, named
  preset discovery, setup/profile/migration consumers, and NoDb config tokens
- **Commit/branch context**: uncommitted WP01 change on
  `feature/project-owned-config`, starting at `c45726072`
- **Canonical contract**:
  `docs/schemas/project-owned-config-contract.md` sections 6.2, 6.3,
  14.1-14.3, and 15
- **Related QA/security artifacts**: security review N/A (`low` triage)

## User Outcome

- **User goal**: reopen or create a legacy project with the same effective
  configuration while new code uses the canonical shared defaults filename.
- **Success presented to the user as**: projects load normally; no defaults
  filename appears in UI or persisted config tokens.
- **Failures that may reach the user**: existing `FileNotFoundError` for absent
  shared defaults and `configparser` parse errors for malformed selected files.
- **Partial-state behavior**: resolution is read-only and writes no project
  state, so failure leaves no partial artifact or cleanup obligation.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Both shared names absent | no | open canonical path and fail explicitly | `test_missing_defaults_retains_explicit_file_not_found` |
| Canonical shared regular file plus legacy relative symlink | yes | current and old readers load identical bytes | `test_repository_legacy_name_is_relative_symlink_for_older_reader` and running-stack probe |
| Shared legacy name only | yes during compatibility | select legacy fallback | `test_defaults_resolution_uses_contract_precedence[shared_toml]` |
| Project-local `_defaults.cfg` populated | yes | win over local legacy and both shared names | four-name precedence matrix |
| Project-local `_defaults.toml` populated | yes, permanently | win over both shared names | four-name precedence matrix and layering test |
| Selected defaults syntactically malformed | no | retain parser failure; do not try lower-priority paths | `test_malformed_selected_defaults_retains_parser_failure` |
| Shared alias broken because canonical target is absent | no | canonical open fails explicitly | same absent-state boundary; no exception masking |

The input dimension is unchanged: named preset tokens and supported query
overrides are still parsed after defaults selection. The state matrix above is
independent of those inputs; the layering test covers a named preset and the
serialized-token test covers a token with a query override.

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Neither shared defaults name exists | exceptional | existing file-not-found failure naming canonical path | Contract section 6.3 prohibits masking missing shared files |
| Highest-precedence existing file is malformed | exceptional | existing parser exception | Contract section 6.3 prohibits fallback around malformed files |
| Lower-priority file is malformed but shadowed | expected | selected higher-priority file loads | Contract section 6.2 defines authority by ordered presence |
| Older reader opens `_defaults.toml` | expected | transparently reads canonical bytes | Contract section 14.1 requires the relative compatibility symlink |

## Review Checks

- [x] Canonical intent is named; implementation/tests are not behavioral
  authority.
- [x] Absent, populated, supported legacy, symlink, and malformed states are
  reviewed independently.
- [x] Input/token and filesystem-state dimensions are reviewed separately.
- [x] Direct tests open real temporary files and the repository symlink without
  mocking the parser/open boundary.
- [x] No security control or new rejection path was introduced.
- [x] Resolution has no partial success, persistence, retry, or cleanup state.
- [x] Existing missing/malformed error classes remain explicit.
- [x] Legacy local and mixed-version reader workflows remain compatible.
- [x] The claimed precedence matrix names all four ordered locations.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High | Setup discovery / Interfaces | Canonical `_defaults.cfg` initially matched the named-preset glob and would have exposed `_defaults` as a selectable preset. | Source inspection plus 128-preset assertion | Exclude only reserved `_defaults` stem and add regression | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: ship to the WP11 Forest acceptance gate after
  WP01 broad tests pass
- **Reviewer sign-off**: Codex, 2026-08-26
