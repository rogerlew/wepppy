# WP01 Defaults Compatibility Evidence

**Date**: 2026-08-26 17:41 UTC
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `c45726072`
**Implementation revision**: `a5d0367d7`
**Feature flags**: no project-owned config writer or update flag added/enabled

## Artifact and Reader Evidence

- `wepppy/nodb/configs/_defaults.cfg` is the regular canonical source.
- `wepppy/nodb/configs/_defaults.toml` is a relative symlink whose exact target
  is `_defaults.cfg`.
- Reading through either path produces identical bytes.
- An old-reader fixture hard-coded to `_defaults.toml` parses
  `[nodb].apply_nodir = false` successfully.
- Current resolution covers, in order, project-local cfg, project-local toml,
  shared cfg, and shared toml.
- Named-preset discovery remains 128 entries and excludes `_defaults`.

## Running Development Stack Probe

Executed inside the restarted `weppcloud` development container:

    wctl run-python -c "... get_default_config_path(); ... get_configs()"

Observed:

    _defaults.cfg True _defaults.cfg False 128

This proves the running branch selects canonical `_defaults.cfg`, sees a
relative legacy symlink, parses the known default value as false, and retains
the 128-preset catalog.

## Automated Results

- Initial serializer/sanitizer/compatibility set: 49 passed.
- Direct migration/profile/setup consumers: 56 passed.
- Final compatibility/serializer/setup set: 62 passed.
- NoDb suite: 1,661 passed, 26 skipped.
- Full repository suite: 6,785 passed, 63 skipped.
- `wepppy.nodb.base` stubtest: success, no issues in one module.
- Test-stub completeness: pass.
- Changed-file broad-exception enforcement: pass, net delta zero.
- Source normalization: 129 files validated, zero drift.
- Project-config secret scan: pass.
- Package, configuration reference, and project tracker Markdown lint: zero
  errors and warnings.

## WP11 Handoff

WP11 must deploy an exact feature-branch commit and repeat the running-stack
probe on Forest with its deployed/rollback revision inventory. It must also
reopen a representative legacy project and exercise local cfg/local toml
fixtures there. WP01 supplies the implementation, local matrix, older-reader
fixture, and exact commands; it does not claim Forest acceptance or production
promotion.
