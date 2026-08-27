# Project Config Locale and View Authority (WP12B)

**Status**: Active (2026-08-27)
**Timezone**: UTC
**Initiative branch**: `feature/project-owned-config`
**Production gate**: WP12 remains blocked until this package closes

## Overview

WP12B replaces duplicated locale conditionals with a comprehensive, typed
locale dependency authority. The current `continental-us` definition is
normalized into the canonical profile schema without renaming its durable ID.
Builder controls consume the live registry; created-run views and paired
mutation endpoints consume the capabilities flattened into that run.

## Scope

Included work covers the canonical locale inventory, stable capability axes,
typed dataset/method dependencies, registry resolution, generated capability
provenance, climate/landuse/soil/watershed presentation and submission parity,
legacy compatibility, generated matrix evidence, and Forest validation.

WP12B does not migrate existing runs, make run pages depend on the current
registry, rename durable component IDs, or promote the branch to production.

## Success Criteria

- [ ] Every runtime locale token in shipped configs and domain catalogs maps to
  exactly one canonical base, overlay, or explicit non-Builder family/support
  disposition.
- [ ] `continental-us` conforms to the same canonical schema as every profile.
- [ ] Locale/component dependency closure is deterministic and rejects unknown,
  contradictory, or empty required capability sets.
- [ ] Flattened configs distinguish climate datasets/methods, landuse
  datasets/methods, soil datasets/builders, and watershed choices.
- [ ] Climate radios, landuse options, soil modes, and watershed controls are
  rendered from the resolved run authority.
- [ ] Paired server endpoints reject newly submitted hidden choices.
- [ ] Legacy and already-persisted selections preserve their contracted behavior.
- [ ] Forest proves every advertised provider and every Builder-exposed base
  and overlay, with representative execution for each provider/method family.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR**: `docs/adrs/ADR-0047-project-config-locale-authority.md`
- **Decision owner**: project operator

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Primary assets**: run-scoped capability integrity, hidden-option mutation
  prevention, dataset/backend selection, and immutable project provenance.

## Dependencies and Handoff

- **Depends on**: WP05, WP07, WP11, and the Builder model-options package.
- **Blocks**: WP12 production cutover.
- **Rollback**: before the first schema-v2 project exists, a full revert to the
  prior one-locale registry is allowed. After the first v2 project exists, every
  rollback target must retain or redeploy the v2-aware, fail-closed reader and
  enforcement path; writers and new views may be disabled, but pre-v2 readers
  are no longer a supported rollback target. No project artifact is rewritten.

## References

- `docs/schemas/project-owned-config-contract.md`
- `docs/schemas/project-owned-config-implementation-roadmap.md`
- `docs/standards/contract-first-change-standard.md`
- `docs/standards/parameterization-adr-standard.md`
- `wepppy/nodb/config_builder/`
- `wepppy/nodb/locales/`
