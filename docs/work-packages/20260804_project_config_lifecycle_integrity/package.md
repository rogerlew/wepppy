# Project Config Lifecycle Integrity (WP10)

**Status**: Complete (2026-08-26)
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `f86c2b78a`
**Security impact**: high; dedicated review required

## Objective

Make fork, archive, download, and restore preserve one consistent project-owned
configuration authority. Lifecycle copies recover interrupted amendments under
the amendment lock, preserve config and manifest bytes, exclude the pending
journal, and retain legacy and degraded-manifest reader behavior.

## Compatibility and Regression Plan

The change is additive around existing lifecycle copy boundaries. Legacy runs
without project-owned artifacts continue through the current shared-defaults
fallback. Restored malformed or newer manifests remain readable in the
existing degraded mode with updates disabled. No user-visible keys, archive
member names, or project data schemas are renamed or removed.

## Success Criteria

- [x] Fork and archive recover pending amendments under the config lock.
- [x] Fork/archive/restore preserve config and manifest bytes as one state.
- [x] Archives never rely on the pending journal for recovery.
- [x] Nested/PUP lifecycle operations use top-level config authority.
- [x] Legacy, invalid/newer-manifest, read-only, and public behavior regressions pass.
- [x] Security, docs, focused, isolation, and full-suite gates pass.
