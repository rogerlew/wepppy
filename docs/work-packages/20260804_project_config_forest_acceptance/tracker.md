# Tracker - Project Config Forest Acceptance (WP11)

## Quick Status

**Status**: In progress
**Started**: 2026-08-26
**Starting revision**: `930881c31`
**Next milestone**: Add Compose flag passthrough and deploy candidate

## Task Board

- [x] Confirm all WP00R-WP10 dependencies and Forest-only authority.
- [x] Record deployment, compatibility, security, and rollback plan.
- [ ] Add/test default-off production Compose flag passthrough.
- [ ] Push and deploy exact candidate twice on forest1.
- [ ] Execute defaults, mixed-version, and four-combination matrix.
- [ ] Execute named preset, builder, update, restart, and lifecycle flows.
- [ ] Rehearse rollback, restore candidate, review, archive, and close.

## Decisions

- Forest uses the canonical full production deploy command; targeted deploys do
  not satisfy this gate.
- Host-only flag values belong in Forest's gitignored `docker/.env`; tracked
  Compose defaults remain false.
