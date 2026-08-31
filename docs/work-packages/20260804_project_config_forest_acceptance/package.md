# Project Config Forest Acceptance (WP11)

**Status**: Complete with explicit dispositions (2026-08-26)
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `930881c31`
**Environment**: Forest test production (`forest1`), never production
**Security impact**: high; deployed reader/writer and rollback evidence required

## Objective

Deploy the complete default-off project-owned-config stack to Forest and prove
the supported compatibility, creation, update, lifecycle, restart, and rollback
matrix on the actual production Compose topology. Record exact revisions,
commands, non-secret identifiers, worker compatibility, and any blocking
dispositions needed before WP12 production cutover.

## Safety and Rollback Plan

Use only `scripts/deploy-production.sh` with the Forest production preset for
full deployments. Preserve the shared `_defaults.toml` compatibility symlink.
Enable feature flags only in Forest host configuration and only after the
default-off deployment passes. Evaluate the prior `master` revision and select
a reader-compatible rollback revision before writer activation. Do not deploy
or mutate `wepp1`, `wepp2`, or `wepp3`.

## Success Criteria

- [x] Production Compose passes all four project-config flags default-off.
- [x] Exact candidate revision deploys twice through the canonical full command.
- [x] Mixed reader/worker and shared defaults compatibility evidence passes.
- [x] All four initial DEM/backend combinations and named/builder flows pass.
- [x] Climate, soil, land-use, update, restart, fork/archive/restore have
  deployed-environment tests or persistent artifact evidence.
- [x] Historical-reader rollback compatibility is proven; full-stack rehearsal
  has an explicit blocking disposition.
- [x] Security, operator, validation, and closure evidence is complete.
