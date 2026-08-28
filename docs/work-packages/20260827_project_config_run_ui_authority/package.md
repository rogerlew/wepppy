# Project Config Run UI Authority (WP12D)

**Status**: Reader floor accepted on Forest / implementation active (2026-08-28)
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
  compatible without live-registry consultation for flattened compatibility
  modes.
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

### Explicitly Out of Scope

- Locale-bearing Interface links, query filtering, card remapping, or
  config-registry locale metadata.
- Migrating or rewriting any existing run or persisted NoDb file.
- Changing the global `NoDbBase.locales` property or locale-sensitive consumers
  outside the enumerated landuse, soil, and climate modules.
- Changing providers, scientific algorithms, dataset lists, model defaults,
  queue topology, auth, or production.
- Synthesizing Builder graphs for non-Builder bases, overlays, or RHEM.
- Applying new locale validation or live Builder authority to flattened
  no-capability or schema-v1 projects.
- Silent/background graph refresh, locale changes through update, capability
  rollback, or claims of strict creation-time reproducibility after refresh.

## Success Criteria

- [ ] The row-level 128-config inventory matches actual effective config and
  every row resolves to its ratified authority mode.
- [ ] Both Config Builder links and the Interfaces page remain unchanged.
- [ ] Five recognized legacy base locales render and enforce their live Builder
  graph while stored schema-v2/v3 runs remain unaffected by registry drift.
- [ ] Eligible complete schema-v3 projects expose current capabilities only
  after an exact preview-bound acknowledgment and atomic manifest-recorded
  refresh; schema-v2 refresh remains unavailable.
- [ ] Refresh preserves existing project selection defaults and runtime
  selectors exactly, and becomes unavailable rather than substituting a value
  when a preserved selection is incompatible with the current envelope.
- [ ] Only congruent schema-v3 Builder-source projects may refresh; preset
  sources, schema-v2, and locale/selection mismatches remain unavailable.
- [ ] The writer candidate is rollback-safe to a recorded WP12D reader floor
  that understands every structural identity the writer can persist.
- [ ] Stale persisted locale state does not override effective `.cfg` locale
  and no run file is rewritten during reopen.
- [ ] Current outside-authority state remains observable and exactly rebuildable
  while authorized recovery choices remain selectable.
- [ ] Frontend/Python/full-suite, documentation, correctness, security, and
  Forest gates pass.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR**: `docs/adrs/ADR-0047-project-config-locale-authority.md`
- **Decision provenance captured**: yes; the operator corrected the authority
  model, accepted the on-demand/provenance tradeoff, and amendment
  `PC-24/WP12D-20260827-3` records the exact values and warning.

## Dependencies and Handoff

- **Depends on**: accepted WP05, WP07, and WP12B contracts; WP12C ratified
  candidate `b31eeb625`, accepted audit correction `f6784420a`, and deployed
  reader floor `187a856d4`.
- **Overlap rule**: WP12D does not claim or replace WP12C's pending Forest
  writer/provider/create/reopen acceptance.
- **Blocks**: WP12 production cutover.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Rationale**: untrusted config locale and run-scoped control submissions
  select executable providers, even though auth policy remains unchanged.
- **Security artifact**: `artifacts/20260827_security_review.md`

## References

- `artifacts/20260827_contract_decision.md`
- `artifacts/20260827_surface_matrix.md`
- `artifacts/20260827_config_locale_inventory.md`
- `artifacts/20260827_amendment2_advisory_correctness_review.md`
- `artifacts/20260827_amendment2_advisory_governance_review.md`
- `artifacts/20260827_amendment3_advisory_correctness_review.md`
- `artifacts/20260827_amendment3_advisory_governance_review.md`
- `artifacts/20260827_binding_correctness_review.md`
- `artifacts/20260827_binding_governance_review.md`
- `docs/schemas/project-owned-config-contract.md`
- `docs/schemas/project-owned-config-implementation-roadmap.md`
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/schemas/rq-response-contract.md` (unchanged applicable envelope)
- `docs/adrs/ADR-0047-project-config-locale-authority.md`
- `wepppy/weppcloud/routes/usersum/weppcloud/rq-engine.md`
- `docs/standards/contract-first-change-standard.md`
