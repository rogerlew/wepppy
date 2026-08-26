# Correctness Review - Project Config Capability Enforcement

## Outcome and States

The canonical authority is section 9 of
`docs/schemas/project-owned-config-contract.md`. A legacy project with no
capability section retains all existing behavior. A populated flattened config
filters new choices and rejects a direct unsupported submission. A malformed
populated list fails explicitly. An already persisted selection remains
controller state and is not rewritten or rejected merely because it is not
offered for a new selection.

## Findings

| ID | Severity | Finding | Resolution | Status |
| --- | --- | --- | --- | --- |
| COR-01 | High | WP03's continental-US profile cannot describe all legacy named presets. | Resolve catalog IDs from each preset's effective locale/runtime sources instead of assigning that profile. | Resolved |
| COR-02 | Medium | `config_get_list` converts missing values to an empty list, losing legacy absence. | Check raw presence first, then validate the populated list. | Resolved |

## Verdict

- Gate: pass
- Unresolved findings: High 0; Medium 0; Low 0
- Recommendation: ship dormant; Forest activation remains WP11.
- Reviewer: Codex, 2026-08-26
