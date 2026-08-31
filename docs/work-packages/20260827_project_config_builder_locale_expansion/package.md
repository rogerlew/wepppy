# Project Config Builder Locale Expansion (WP12C)

**Status**: Complete; handed to WP12 (2026-08-29)
**Timezone**: UTC
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Verified starting revisions**: initiative/origin `e1ef3b8df`; canonical
origin `6af9ecdd6`; canonical is an ancestor of the initiative branch
**Production gate**: WP12 owns production promotion; WP12C may deploy only to
host `forest` for integration acceptance

## Overview

WP12C exposes the canonical Europe, Canada, Australia, and Global Earth locale
profiles in Config Builder alongside Continental United States. Each profile's
typed dataset and climate-station database lists become the sole authority for
the Builder controls, server validation, and flattened run capability graph.

## Scope

Included work covers profile-owned DEM, soil, land-cover, and climate datasets;
per-locale capability graphs; deterministic Builder descriptions; dependent UI
controls; server-side validation; immutable run snapshots; compatibility tests;
and real Forest provider and creation acceptance.

The exposed locale set is exactly `continental-us`, `europe`, `canada`,
`australia`, and `global-earth`. Canada is a new Canada-wide profile with its
own stable/runtime identity and uses Copernicus DEM, ISRIC soil, C3S global
land cover, and observed Daymet climate. Specialized locales and overlays stay
classified but are not Builder-selectable.

Vanilla CLIGEN is available in every exposed locale. Continental US offers
Legacy, 2015, and GHCN climate-station databases; the other four locales offer
only GHCN. Every locale defaults its climate mode to Vanilla CLIGEN.

WP12C does not migrate existing runs, alter Interfaces presets, expose Canada
CDEM/Canada Land Cover 2020, modify scientific algorithms, pursue the unrelated
TerrainProcessor working-directory issue, or deploy to production.

## Success Criteria

- [x] Only the five approved base profiles are Builder-selectable.
- [x] Every exposed profile has complete DEM, soil, land-cover, climate,
  climate-station database, delineation, representation, and WEPP-binary
  capability closure.
- [x] `LocaleProfile.landuse_sources` is the sole Builder authority for the
  Land-cover dataset options and server validation.
- [x] Canada resolves to runtime locale `canada`, uses only global terrain,
  soil, and land-cover providers, offers Vanilla CLIGEN and observed Daymet,
  and defaults to Vanilla CLIGEN with GHCN stations.
- [x] Existing schema-v2 Continental-US projects reopen unchanged and all new
  schema-v3 projects remain Preview, self-contained, and live-registry
  independent.
- [x] Frontend, backend, compatibility, security, and real Forest acceptance
  gates pass before WP12C closes.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR**: `docs/adrs/ADR-0047-project-config-locale-authority.md`
- **Decision provenance captured**: yes
- **Decision owner**: project operator

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: authenticated Builder routes accept new stable IDs that
  select run-scoped data providers and persist executable project authority.
- **Security review artifact**:
  `artifacts/20260827_security_review.md`

## Dependencies and Handoff

- **Depends on**: WP12B, WP07, WP11, and the Builder model-options package.
- **Blocks**: WP12 production cutover.
- **Promotion policy**: WP12C commits and pushes only the initiative branch.
  WP12 owns the reviewed merge to `master` and every production action.
- **Rollback**: every rollback target after any expanded-profile project is
  created must retain the schema-v3 multi-profile reader and fail-closed
  enforcement. No project artifact is rewritten.

## References

- `docs/schemas/project-owned-config-contract.md`
- `docs/schemas/project-owned-config-implementation-roadmap.md`
- `docs/adrs/ADR-0047-project-config-locale-authority.md`
- `docs/standards/contract-first-change-standard.md`
- `wepppy/nodb/locales/`
- `wepppy/nodb/config_builder/`
