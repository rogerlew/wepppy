# Tracker - Defaults CFG Compatibility (WP01)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-26 17:12 UTC
**Current phase**: Closed - implemented on feature branch
**Last updated**: 2026-08-26 17:41 UTC
**Next milestone**: WP02 reader foundation; WP11 later consumes Forest evidence
**Security impact**: `low`
**Dedicated security review**: no
**Security artifact**: N/A
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate
**Starting revision**: `c45726072`
**Implementation revision**: `a5d0367d7`
**Upstream**: `origin/feature/project-owned-config`

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Verified the initiative branch, upstream, and WP00R prerequisite
  (2026-08-26 17:12 UTC).
- [x] Imported all twelve WP01 checklist task IDs and wrote the compatibility
  and downstream-regression plan (2026-08-26 17:12 UTC).
- [x] Inventoried the central reader, direct consumers, tools, tests, and docs
  that name the legacy shared file (2026-08-26 17:12 UTC).
- [x] Moved shared defaults, created the relative alias, implemented central
  precedence, and updated direct consumers (2026-08-26 17:18 UTC).
- [x] Added the complete compatibility matrix and resolved canonical seed
  leakage into preset discovery (2026-08-26 17:18 UTC).
- [x] Passed 49 initial focused tests, 56 consumer tests, 62 post-fix focused
  tests, 1,661 NoDb tests with 26 skips, docs lint, and the running-stack probe
  (2026-08-26 17:26 UTC).
- [x] Passed the full repository suite (6,785 passed, 63 skipped), stubtest,
  stub completeness, and changed broad-exception enforcement
  (2026-08-26 17:41 UTC).
- [x] Published correctness and WP11 handoff evidence, closed PC-02/PC-03
  locally, and closed WP01 as implemented on the feature branch
  (2026-08-26 17:41 UTC).

## Requirement Ledger

| Task | Planned evidence | Status |
| --- | --- | --- |
| `WP01-PC02-N017` | four-location precedence tests | verified |
| `WP01-PC02-N018` | project-local legacy alias precedence | verified |
| `WP01-PC02-N019` | canonical shared and alias-only fallback tests | verified |
| `WP01-PC02-N020` | missing/malformed explicit failure tests | verified |
| `WP01-PC03-N099` | Git move plus relative symlink inspection | verified |
| `WP01-PC03-N100` | old hard-coded reader and dev-stack evidence | verified locally; WP11 deploy retained |
| `WP01-PC02-R004` | defaults-plus-local layering fixture | verified |
| `WP01-PC02-R005` | shared fallback fixture | verified |
| `WP01-PC02-R006` | project-local cfg precedence fixture | verified |
| `WP01-PC02-R007` | project-local toml precedence fixture | verified |
| `WP01-PC02-R008` | shared alias fallback fixture | verified |
| `WP01-PC03-R009` | relative symlink plus older-reader fixture | verified |
| `WP01-PC02-R010` | serialized config-token inspection | verified |

## Decisions Log

### 2026-08-26 17:12 UTC: Centralize ordered path selection

**Context**: The deployed reader currently derives one local basename from one
hard-coded shared path.

**Decision**: Keep config parsing unchanged and replace only defaults path
selection with the contract's ordered existing-file candidates. Expose the
canonical shared selection through `get_default_config_path()`.

**Impact**: Legacy layering remains intact, local legacy defaults remain
permanent, and direct consumers stop hard-coding the legacy shared name.

### 2026-08-26 17:12 UTC: Preserve one shared inode through a relative alias

**Context**: Mixed-version readers must observe identical shared content.

**Decision**: Rename the tracked regular file and create `_defaults.toml` as a
relative symlink to `_defaults.cfg`; do not keep two regular copies.

**Impact**: New and old readers cannot drift during the compatibility window.

### 2026-08-26 17:18 UTC: Keep canonical defaults out of preset discovery

**Context**: The canonical `.cfg` suffix caused the defaults seed to match the
named-preset glob.

**Decision**: Exclude only the exact reserved `_defaults` stem in
`get_configs()` and assert the existing 128-preset inventory.

**Impact**: Setup discovery and Interfaces cannot expose the defaults seed as a
project configuration.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Project-local legacy defaults lose precedence | High | Low | Full four-location matrix | Open |
| Old readers fail after rename | High | Low | Relative symlink and hard-coded-reader proof | Open |
| Direct consumers embed a filename | Medium | Low | Consumer inventory and payload test | Open |
| Shared values drift during move | High | Low | Byte, typed, and lexical parity checks | Open |

## Verification Checklist

- [ ] Focused compatibility tests pass.
- [ ] Existing serializer, sanitization, setup-discovery, profile-recorder, and
  migration tests pass.
- [ ] NoDb suite and full repository suite pass.
- [ ] Stub/API checks pass if the public helper surface changes.
- [ ] Documentation lint passes.
- [ ] Development stack starts and reads canonical shared defaults.
- [ ] No unresolved medium/high correctness findings remain.

## Progress Notes

### 2026-08-26 17:12 UTC: Scaffold and inventory

**Agent/Contributor**: Codex

**Work completed**:

- Verified branch `feature/project-owned-config` at `c45726072` tracking the
  matching remote.
- Imported PC-02/PC-03 checklist ownership.
- Located the central reader and direct legacy-name consumers.
- Recorded the compatibility and regression plan before schema-path edits.

**Blockers encountered**: None.

**Next steps**:

- Implement the move, resolver, tests, and consumer updates.

**Test results**: Pre-change WP00A/WP00B focused tests passed during branch
merge validation (39 passed).

## Watch List

- WP11 must consume, not duplicate, the exact compatibility evidence produced
  here.

## Closure Handoff

- **Feature-branch implementation revision**: `a5d0367d7` based on starting
  revision `c45726072`.
- **Feature flags**: none added or enabled.
- **Delivered interfaces**: `resolve_defaults_path()` and canonical
  `get_default_config_path()`.
- **Evidence**:
  `artifacts/2026-08-26_defaults_compatibility_evidence.md`.
- **Residual work**: WP02 flattened-reader foundation and WP11 deployed
  Forest/rollback acceptance.
