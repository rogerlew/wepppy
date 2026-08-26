# Tracker - Project Config Reader Foundation (WP02)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-26 18:15 UTC
**Current phase**: Closed - implemented on feature branch
**Last updated**: 2026-08-26 19:03 UTC
**Next milestone**: WP03/WP04; WP11 later owns deployed reader activation
**Security impact**: `high`
**Dedicated security review**: yes
**Security artifact**: `artifacts/2026-08-26_security_review.md`
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate
**Starting revision**: `ceb10fc9686925f89288d4411c3d36cd9d6ccbaf`
**Implementation revision**: `cb7698b28`
**Upstream**: `origin/feature/project-owned-config`

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Verified branch, upstream, WP00R, and WP01 prerequisites (2026-08-26 18:15 UTC).
- [x] Imported all WP02-owned checklist tasks and wrote the compatibility plan before production edits (2026-08-26 18:15 UTC).
- [x] Inventoried the central NoDb reader, direct consumers, manifest sanitizer, and nested parent state (2026-08-26 18:15 UTC).
- [x] Implemented the default-off reader collaborator, facade status seam, exact legacy branch, and transient-state exclusion (2026-08-26 18:30 UTC).
- [x] Added flattened/schema, manifest, digest, nested, flag, read-only, and symlink-boundary fixtures (2026-08-26 18:38 UTC).
- [x] Passed 1,699 NoDb tests with 26 skips, stub gates, initial full suite (6,823 passed, 63 skipped), and restarted the feature-branch dev services (2026-08-26 18:48 UTC).
- [x] Completed correctness/security reviews with all medium/high findings resolved and preserved exact legacy exception/override behavior (2026-08-26 18:50 UTC).
- [x] Passed the exact final-tree full suite (6,827 passed, 63 skipped), synchronized canonical docs, and closed WP02 (2026-08-26 19:03 UTC).

## Requirement Ledger

| Contract area | Tasks | Planned evidence | Status |
| --- | --- | --- | --- |
| PC-01 | N-001, N-002, N-005, N-013, N-014, N-034, N-035, N-037, R-001, R-015 | marker/schema, filename/token, no-write, no-fallback matrices | verified for reader scope; real writers retained by WP04/WP06 |
| PC-08 | N-015, N-016, N-073 through N-078, R-016, R-017, R-026 | manifest schema/degradation/digest/logging fixtures | reader/status verified; header UI/lifecycle retained by WP09/WP10 |
| PC-16 | N-021, N-022, R-034, A-001 | child precedence, parent containment, UI handoff disposition | reader verified; optional UI deferred to WP09, lifecycle to WP10/WP11 |

## Decisions Log

### 2026-08-26 18:15 UTC: Extend the central reader behind a default-off flag

**Context**: Web routes, RQ jobs, and NoDb controllers converge on
`NoDbBase._configparser`; adding writers or per-call-site readers would create
drift.

**Decision**: Add one focused collaborator and retain `_configparser` as the
facade. Enable project-owned recognition only through an explicit environment
flag whose absent/false value preserves legacy behavior.

**Impact**: WP02 can prove reader compatibility before WP04 creates artifacts,
and WP11 can activate the exact dormant path after fleet validation.

### 2026-08-26 18:15 UTC: Treat manifest validity as status, not config authority

**Context**: The contract makes a valid flattened config authoritative even
when manifest provenance is damaged.

**Decision**: Fail explicitly on malformed/unsupported flattened config, but
return structured update-disabled status for missing/invalid/newer manifests
and warning-only status for digest mismatch. Never synthesize or repair files.

**Impact**: Existing model operations remain available without weakening
future update gates or exposing config contents.

### 2026-08-26 18:15 UTC: Resolve nested authority only from persisted context

**Context**: String-prefix discovery can confuse siblings such as `/run` and
`/run2` and violates the ratified containment rule.

**Decision**: Preserve an existing child-local legacy file; otherwise accept
only explicit/persisted `parent_wd` whose resolved path contains the child via
`Path.relative_to`. Reject child-local flattened files and unsafe parent state.

**Impact**: Nested projects inherit one root authority without path searching.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Flattened file accidentally receives shared values | High | Low | sentinel no-fallback fixtures | Mitigated |
| Invalid parent escapes project authority | High | Low | resolved containment and prefix-collision tests | Mitigated |
| Warning logs expose secrets or flood accessors | High | Low | allowlisted fields and instance dedupe | Mitigated |
| Feature flag alters legacy behavior while off | High | Low | exact parser/result comparison | Mitigated |

## Verification Checklist

- [x] Focused WP02 and existing WP00/WP01 tests pass.
- [x] NoDb and full repository suites pass.
- [x] Stub/API and changed broad-exception checks pass.
- [x] Documentation lint and `git diff --check` pass.
- [x] Restarted dev stack exercises disabled and enabled reader paths.
- [x] Correctness and security artifacts have no unresolved medium/high findings.

## Progress Notes

### 2026-08-26 18:50 UTC: Reader implementation and review gates

**Agent/Contributor**: Codex

**Work completed**:

- Wired flattened/manifest/nested resolution into the common NoDb facade behind
  `WEPPPY_PROJECT_CONFIG_READER_ENABLED`, default off.
- Preserved exact legacy values, exception types, absolute paths, and override
  parsing while the reader is enabled.
- Resolved five security and three correctness findings, including prefix and
  symlink escapes, warning leakage/flooding, and persisted transient status.
- Restarted configuration-reading dev services and verified the front door.

**Blockers encountered**: None. Downstream writer/UI/lifecycle evidence remains
owned by its roadmap packages and does not activate WP02 code.

**Next steps**: Run final-tree full suite, close docs, and commit WP02.

**Test results**: focused 42; NoDb 1,699 passed/26 skipped; initial full suite
6,823 passed/63 skipped; stubs, docs, broad exceptions, and reviews passed.

### 2026-08-26 18:15 UTC: Scaffold, inventory, and compatibility checkpoint

**Agent/Contributor**: Codex

**Work completed**:

- Verified `feature/project-owned-config` at `ceb10fc96`, tracking the matching remote.
- Imported all 25 WP02 checklist tasks and the PC-01/PC-08/PC-16 ledger.
- Traced configuration access to `NoDbBase._configparser` and nested identity to persisted `parent_wd`.
- Recorded the compatibility/regression plan before modifying run-scoped schema authority.

**Blockers encountered**: None.

**Next steps**: Implement collaborator, integrate facade, then build fixtures.

**Test results**: WP01 full-suite baseline is 6,785 passed, 63 skipped.

## Watch List

- WP09 must consume structured status for header UI without moving authority.
- WP11 must prove deployed mixed-version/rollback behavior before flag activation.

## Closure Handoff

- **Feature-branch implementation revision**: `cb7698b28`, based on starting
  revision `ceb10fc96`.
- **Feature flag**: `WEPPPY_PROJECT_CONFIG_READER_ENABLED`, default off.
- **Delivered interfaces**: `load_project_config()`, immutable
  `ProjectConfigStatus`, explicit schema/authority errors, and
  `NoDbBase.project_config_status`.
- **Evidence**: `artifacts/2026-08-26_reader_foundation_evidence.md`.
- **Residual work**: real writers (WP04/WP06), header UI (WP09), lifecycle
  (WP10), and deployed activation/rollback (WP11).
