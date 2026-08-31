# Project Config Run UI Authority (WP12D)

**Status**: Amendment 5 checkpoint complete; reader floor next (2026-08-28)
**Timezone**: UTC
Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate
**Starting/upstream revision**:
`5e04e0da9a23dd676e171f1857e14fa38cc9dfbe`
**Canonical merge base**: `origin/master` at
`6af9ecdd63921189804c5e292114a97253914cbb`
**Promotion boundary**: WP12D may push the initiative branch and deploy only
to exact host `forest`; WP12 owns merge and production

## Overview

WP12D makes the effective `.cfg` the locale authority. Legacy runs without a
flattened project-owned config use that locale to select the live Builder graph
for recognized Builder profiles. Builder-created schema-v2/v3 runs continue to
use their stored graph. An authorized end user may explicitly review and
acknowledge a same-locale capability refresh only for an eligible complete
schema-v3 project. Interfaces navigation remains unchanged.

## Objectives

- Ensure every shipped named config resolves to a canonical locale composition,
  including corrected Canada, Portland, RHEM, Tenerife, Turkey, and explicit
  established/general cases.
- Make landuse, soil, and climate presentation and submission use one resolved
  authority for both stored Builder projects and recognized legacy profiles.
- Reopen old runs without rewriting them, preserve exact current selections,
  and keep flattened no-capability/schema-v1/non-Builder/overlay behavior
  compatible except for the bounded live climate/land-cover projection of a
  valid schema-v1 named preset.
- Let project owners deliberately adopt current maps and capabilities through
  a preview-bound acknowledgment that records the provenance discontinuity
  and unstable-feature risk without replacing their project selections with
  current Builder defaults.

## Scope

### Included

- Exact `.cfg` locale normalization from amendment
  `PC-24/WP12D-20260827-3`.
- A public server-side Builder graph reader and an explicit stored-or-legacy
  run-authority resolver.
- Append-only schema-v3 structural identities plus a WP12D reader floor with
  the capability-refresh writer absent before any structural refresh is
  exposed.
- Run-page context and paired landuse, soil, and climate discovery/set/build
  conformance.
- RQ endpoint schema/default/error, operation-document, pipeline, and readiness
  parity plus locale-override rejection before creation/load.
- Extension of the existing project-config update modal, API, RQ job, atomic
  transaction, and manifest record for explicit same-locale graph replacement.
- Generated fixtures, direct legacy reopen evidence, correctness/security
  reviews, and exact-host Forest acceptance.
- Ratified audit-only correction `PC-24/WP12D-20260828-4` for the export-only
  locale package surface, append-only capability-structure authority, and
  bounded signed-identity handoff required by Forest execution.
- Ratified amendment `PC-24/WP12D-20260828-5` for the corrected five-locale
  climate matrix, complete locale land-cover envelopes, and valid schema-v1
  named-preset climate/land-cover projection. It requires binding reviews, a
  standalone contract checkpoint, and another reader-first Forest gate.

### Explicitly Out of Scope

- Locale-bearing Interface links, query filtering, card remapping, or
  config-registry locale metadata.
- Migrating or rewriting any existing run or persisted NoDb file.
- Changing the global `NoDbBase.locales` property or locale-sensitive consumers
  outside the enumerated landuse, soil, and climate modules.
- Changing providers, scientific algorithms, model defaults, queue topology,
  authentication/authorization beyond the ratified identity handoff, or
  production. Dataset-list changes are limited to amendment 5's exact climate
  matrix and land-cover envelopes.
- Synthesizing Builder graphs for non-Builder bases, overlays, or RHEM.
- Applying new locale validation or live Builder authority to flattened
  no-capability or schema-v1 projects outside amendment 5's exact valid-preset
  climate/land-cover exception.
- Silent/background graph refresh, locale changes through update, capability
  rollback, or claims of strict creation-time reproducibility after refresh.

## Success Criteria

- [x] The row-level 128-config inventory matches actual effective config and
  every row resolves to its ratified authority mode.
- [x] Both Config Builder links and the Interfaces page remain unchanged.
- [x] Five recognized legacy base locales render and enforce their live Builder
  graph while stored schema-v2/v3 runs remain unaffected by registry drift.
- [ ] Valid schema-v1 named presets project current climate and land-cover
  authority only; Europe exposes exactly Vanilla, E-OBS Modified, and User-
  Defined Climate without rewriting the run.
- [ ] Every locale graph exposes amendment 5's exact climate matrix and
  complete land-cover envelope; Builder selection changes the land-cover
  default without restricting the run control.
- [x] Eligible complete schema-v3 projects expose current capabilities only
  after an exact preview-bound acknowledgment and atomic manifest-recorded
  refresh; schema-v2 refresh remains unavailable.
- [x] Refresh preserves existing project selection defaults and runtime
  selectors exactly, and becomes unavailable rather than substituting a value
  when a preserved selection is incompatible with the current envelope.
- [x] Only congruent schema-v3 Builder-source projects may refresh; preset
  sources, schema-v2, and locale/selection mismatches remain unavailable.
- [x] The amendment-3 writer candidate is rollback-safe to its recorded WP12D
  reader floor.
- [ ] The amendment-5 writer candidate is rollback-safe to a new reader floor
  that understands all five resulting structural identities.
- [x] Stale persisted locale state does not override effective `.cfg` locale
  and no run file is rewritten during reopen.
- [x] Current outside-authority state remains observable and exactly rebuildable
  while authorized recovery choices remain selectable.
- [x] Amendment-3 frontend/Python/full-suite, documentation, correctness,
  security, and Forest gates passed.
- [ ] Fresh amendment-5 frontend/Python/full-suite, documentation, correctness,
  security, and Forest gates pass.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR**: `docs/adrs/ADR-0047-project-config-locale-authority.md`
- **Decision provenance captured**: yes; amendment
  `PC-24/WP12D-20260828-5` records the exact climate/land-cover correction and
  was ratified exactly on 2026-08-28 16:29 UTC.

## Dependencies and Handoff

- **Depends on**: accepted WP05, WP07, and WP12B contracts; WP12C ratified
  candidate `b31eeb625`, accepted audit correction `f6784420a`, and deployed
  reader floor `187a856d4`.
- **Overlap rule**: WP12D does not claim or replace WP12C's pending Forest
  writer/provider/create/reopen acceptance.
- **Blocks**: WP12 production cutover.
- **Handoff gate**: WP12 must retain
  `artifacts/20260828_scope_audit_correction.md` plus amendment 5's final
  scope-versus-changed-files comparison and repeat both before canonical merge
  or production promotion.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Rationale**: untrusted config locale and run-scoped control submissions
  select executable providers, even though auth policy remains unchanged.
- **Security artifact**: `artifacts/20260827_security_review.md`
- **Amendment-5 security artifact**:
  `artifacts/20260828_amendment5_security_contract_review.md` (binding READY)

## References

- `artifacts/20260827_contract_decision.md`
- `artifacts/20260828_climate_landcover_contract_decision.md`
- `artifacts/20260828_amendment5_contract_correctness_review.md`
- `artifacts/20260828_amendment5_contract_governance_review.md`
- `artifacts/20260828_amendment5_security_contract_review.md`
- `artifacts/20260827_surface_matrix.md`
- `artifacts/20260827_config_locale_inventory.md`
- `artifacts/20260827_amendment2_advisory_correctness_review.md`
- `artifacts/20260827_amendment2_advisory_governance_review.md`
- `artifacts/20260827_amendment3_advisory_correctness_review.md`
- `artifacts/20260827_amendment3_advisory_governance_review.md`
- `artifacts/20260827_binding_correctness_review.md`
- `artifacts/20260827_binding_governance_review.md`
- `artifacts/20260828_scope_audit_correction.md`
- `artifacts/20260828_writer_forest_acceptance.md`
- `docs/schemas/project-owned-config-contract.md`
- `docs/schemas/project-owned-config-implementation-roadmap.md`
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/schemas/rq-response-contract.md` (unchanged applicable envelope)
- `docs/adrs/ADR-0047-project-config-locale-authority.md`
- `wepppy/weppcloud/routes/usersum/weppcloud/rq-engine.md`
- `docs/standards/contract-first-change-standard.md`
