# Project Config Registry and Serializer (WP03)

**Status**: Closed (2026-08-26)
**Timezone**: UTC
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate

## Overview

WP03 supplies the declarative component registry and deterministic resolver
that later project-config writers consume. It registers the conservative
continental-US builder family, validates stable IDs/references/constraints and
declared writeover, and feeds WP00B's canonical `.cfg` serializer. It does not
create projects or enable a writer.

## Objectives

- Parse real TOML component documents with a typed schema and stable IDs.
- Reject unknown references, invalid constraints, undeclared writes, and
  unregistered collisions explicitly.
- Resolve the initial two-DEM/two-backend family deterministically.
- Produce canonical bytes, immutable provenance, effective-writer records, and
  stable server-facing builder descriptions.
- Prove new mods remain disabled unless explicitly selected and registered.

## Scope

### Included

- `wepppy/nodb/config_builder/` schema, registry, resolver, and TOML profiles.
- The `continental-us` locale; two DEMs; TOPAZ/WBT; single-OFE; one soil,
  land-use, and four climate IDs; no optional mods.
- WP00B serializer integration and registry/constraint regression fixtures.

### Explicitly Out of Scope

- Project/config/manifest writes and named-preset snapshotting (WP04).
- Runtime capability endpoint enforcement (WP05) and builder routes/UI
  (WP06/WP07).
- Authenticated cell-size override authorization (WP06); WP03 validates only
  the fixed values and resolution semantics.
- Forest dataset/service acceptance (WP11).

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful declarative implementation of the ratified
  composition model, not a surrogate registry.
- **Authoritative source paths**: the contract sections 7.2, 7.5, 8, and 8.2;
  current normalized defaults and named-presets at revision `8ee87a2e6`.
- **Cutover proof required**: all four local initial combinations resolve
  through the typed registry into canonical parseable bytes; no creation path
  is wired.
- **Acceptance evidence type**: fixture-only by design; deployed generated-run
  evidence belongs to WP04/WP06/WP11.

## Owned Requirements

- PC-06 and PC-07; PC-05 registry integration.
- N-011, N-028, N-030 through N-033, N-049, N-058, N-059, and N-064 through
  N-067.
- R-003, R-029, R-030, R-032, R-033, R-037, and A-003.

## Compatibility and Regression Plan

This package introduces source definitions but does not mutate project data,
NoDb payloads, shared defaults/presets, route schemas, or generated run
artifacts. Registry IDs and builder descriptions are additive future API
material. Resolution begins from a deep copy of the canonical shared-defaults
typed map and then applies only declared TOML writes in the contract order.
Tests compare the input defaults map before/after, prove result independence
from later registry mutation, round-trip every result through WP00B's parser,
exercise all four DEM/backend combinations, and reject excluded IDs, invalid
cell sizes, unknown references, contradictory constraints, malformed TOML,
case collisions, undeclared writes, and unregistered writeover. No generated
`wepp/runs/*` artifact is expected because WP03 exposes only an in-memory
resolver; WP04 owns propagation into a new run.

## Success Criteria

- [x] Every shipped TOML document validates before registry exposure.
- [x] All four local DEM/backend combinations produce stable canonical bytes.
- [x] Unsupported combinations and invalid registry evolution fail explicitly.
- [x] Contributor order and effective write ownership are deterministic.
- [x] No optional mod can appear without explicit registered selection.
- [x] Focused, NoDb, full-suite, stub, docs, and correctness gates pass.

## Outcome

WP03 shipped the dormant typed registry/resolver, 13 real-TOML definitions,
exact ratified stable IDs, canonical WP00B byte generation, ordered provenance,
and effective-writer tracking. The exact final suite passed with 6,864 tests
and 63 skips. WP04 retains the first project writer; WP05/WP06 retain runtime
description and authorization surfaces; WP11 retains deployed Forest
acceptance for each of the four locally eligible DEM/backend combinations.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes
- **Rationale**: WP03 registers already-ratified identifiers/default cell sizes
  and existing runtime values; it changes no deployed default or heuristic.

## Dependencies

- **Depends on**: WP00R and WP00B; both are closed on the initiative branch.
- **Parallel prerequisite state**: WP02 is closed at `8ee87a2e6`.
- **Blocks**: WP04, WP05, WP06, WP08, and WP11.

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: local deployment-owned TOML is parsed without dynamic
  imports, network, paths, auth, queues, subprocesses, or writes; sanitization
  is retained by the canonical serializer.

## References

- `docs/schemas/project-owned-config-contract.md` sections 7.2, 7.5, 8, 8.2,
  and 15.
- `docs/schemas/project-owned-config-implementation-roadmap.md` WP03.
- `docs/work-packages/20260804_project_config_contract_ratification/artifacts/normative_requirement_checklist.md`.

## Deliverables

- Typed registry/schema/resolver and declarative profile corpus.
- Focused contract matrix and correctness evidence.
- Downstream WP04/WP05/WP06/WP11 handoff.
