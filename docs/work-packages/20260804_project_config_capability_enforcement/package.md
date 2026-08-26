# Project Config Capability Enforcement (WP05)

**Status**: Complete (2026-08-26)
**Timezone**: UTC
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate

## Overview

WP05 makes stable capability IDs in a flattened project config the common
authority for newly presented and newly submitted climate, soil, and land-use
choices. Legacy projects and already persisted selections retain their current
behavior. The project-owned writer remains default-off.

## Objectives

- Populate stable climate, soil-builder, and land-use capability IDs during
  flattened named-preset resolution.
- Read capability IDs from the authoritative top-level flattened config.
- Filter affected option lists and validate their paired mutation/build routes
  against the same resolved IDs.
- Preserve current persisted-selection display/routing and every legacy project.
- Retain canonical authorization, errors, NoDb persistence, and route tokens.

## Scope

### Included

- An explicit endpoint/UI inventory for climate, soil, and land-use choices.
- Capability resolution and strict schema validation for flattened configs.
- Paired presentation/submission enforcement for inventoried endpoints.
- Direct generated-config, valid/hidden submission, legacy, nested, and hostile
  regression evidence.

### Explicitly Out of Scope

- Builder description/creation routes (WP06) and builder UI (WP07).
- Reinterpreting or rejecting a selection persisted before this contract.
- Adding new datasets, modes, locale rules, defaults, or fallback heuristics.
- Writer activation, Forest validation, and production cutover (WP11/WP12).

## Owned Requirements

- PC-11: N-004, N-068 through N-072, and R-049.
- Contribution to WP04's generated preset capability-completeness gate.

## Compatibility and Regression Plan

This package additively writes `[capabilities]` lists only into new flattened
project configs. It does not rename/remove NoDb fields, numeric enum values,
catalog IDs, template field names, route payload aliases, or legacy config
keys. Stable IDs map explicitly to existing accepted runtime values; there is
no inference from labels or enum ordering.

At request time, capability authority activates only when the WP02 reader
recognizes a top-level flattened config containing a valid capability section.
Legacy projects without that section continue locale/mod/catalog behavior.
Current persisted controller state is always renderable and routable under the
contract carve-out, even when it is not among choices offered for a new
selection. A newly submitted hidden/unsupported choice fails before mutation
or enqueue. Nested/PUP runs consume their top-level authority through WP02.

Generated-output evidence will resolve and materialize real preset snapshots,
reopen them through WP02, and prove stable IDs reach the project artifact and
both UI/server decisions. Regression evidence separately covers absent,
populated, malformed, legacy, and already-persisted states.

## Success Criteria

- [x] Every affected presentation and mutation endpoint is inventoried.
- [x] Flattened configs contain complete stable semantic capability IDs.
- [x] UI visibility and server validation consume the same authority.
- [x] Hidden capabilities cannot be newly invoked.
- [x] Persisted-selection and legacy-project behavior is unchanged.
- [x] Focused, subsystem, full-suite, stub, docs, correctness, and security gates pass.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Rationale**: WP05 records and enforces existing supported choices; it does
  not change a default, formula, threshold, conversion, or fallback heuristic.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Primary assets**: project capability integrity, authorized mutation,
  run-scoped config authority, and NoDb/RQ state consistency.

## Dependencies and Handoff

- **Depends on**: WP02, WP03, and WP04; all closed on this branch.
- **Blocks**: WP06 and contributes to WP11 acceptance.
- **Rollback**: revert dormant enforcement code or leave project-owned reader
  and writer flags disabled; no existing project is migrated.

## References

- `docs/schemas/project-owned-config-contract.md` sections 4, 7.2.1, and 9.
- `docs/schemas/project-owned-config-implementation-roadmap.md` WP05.
- `docs/work-packages/20260804_project_config_contract_ratification/artifacts/normative_requirement_checklist.md` PC-11.
