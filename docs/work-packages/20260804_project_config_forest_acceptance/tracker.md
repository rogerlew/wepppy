# Tracker - Project Config Forest Acceptance (WP11)

## Quick Status

**Status**: Complete with explicit dispositions
**Started**: 2026-08-26
**Starting revision**: `930881c31`
**Completed revision**: WP11 closure commit

## Task Board

- [x] Confirm all WP00R-WP10 dependencies and Forest-only authority.
- [x] Record deployment, compatibility, security, and rollback plan.
- [x] Add/test default-off production Compose flag passthrough.
- [x] Push and deploy exact candidate twice on forest1.
- [x] Execute defaults, mixed-version, and four-combination matrix.
- [x] Execute named preset, builder, update, restart, and lifecycle flows.
- [x] Prove historical-reader compatibility and record the full-stack rollback
  blocking disposition.
- [x] Complete security review and operator evidence.

## Decisions

- Forest uses the canonical full production deploy command; targeted deploys do
  not satisfy this gate.
- Host-only flag values belong in Forest's gitignored `docker/.env`; tracked
  Compose defaults remain false.
- `master` at `6af9ecdd6` is not rollback-compatible; `cb7698b28` is the
  supported reader-level rollback revision.
