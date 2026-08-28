# Tracker - Project Config Run UI Authority (WP12D)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-27 20:31 UTC
**Current phase**: structural reader-floor implementation review
**Last updated**: 2026-08-28 00:35 UTC
**Next milestone**: commit, push, and validate the writer-absent reader floor on
`forest`
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/20260827_security_review.md`
**Parameterization ADR**: `docs/adrs/ADR-0047-project-config-locale-authority.md`
Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate
**Starting/upstream revision**:
`5e04e0da9a23dd676e171f1857e14fa38cc9dfbe`
**Canonical merge base**: `origin/master` at
`6af9ecdd63921189804c5e292114a97253914cbb`

Affected requirements: PC-09, PC-11, PC-13, PC-22, and PC-23 remain inputs;
PC-24 owns `.cfg` locale normalization and run-UI authority parity.

## Task Board

### In Progress

- [ ] Close independent correctness/security review of the append-only
  structural reader floor, then commit and validate it on `forest` with the
  capability-refresh writer absent.

### Ready / Backlog

- [ ] Write failing full-config inventory and legacy/stored authority tests.
- [ ] Apply exact `.cfg` normalization and bounded resolver/consumer changes.
- [ ] Run focused/full gates and independent correctness/security reviews.
- [ ] Push and validate exact candidate on `forest`; hand off to WP12 without
  production deployment.

### Blocked

- [ ] Capability-refresh writer implementation and exposure are blocked until
  the exact WP12D reader-floor revision is recorded and accepted on `forest`.

### Done

- [x] Committed the ratified canonical documentation-only checkpoint as
  `596ff5758ca83e6077b97f953431c2c881219840` before any WP12D implementation
  edit (2026-08-28 00:16 UTC).
- [x] Implemented the writer-absent structural reader floor with checked-in,
  append-only schema-v2/v3 structure payloads, hashes, and first-reader
  provenance; current and `280cf7e84` schema-v3 structures share identities
  (2026-08-28 00:35 UTC).
- [x] Passed the reader-floor focused and affected suites (65 and 138 tests),
  test-stub, stubtest, Vulture, broad-exception, docs, and diff gates
  (2026-08-28 00:35 UTC).
- [x] Inventoried all 128 named configs and identified 71 that currently omit
  a literal locale declaration (2026-08-27 21:18 UTC).
- [x] Confirmed Builder creation already writes `[general] locales` and legacy
  controllers read effective config locale (2026-08-27 21:18 UTC).
- [x] Superseded the unratified URL/config-registry proposal after the operator
  corrected locale ownership (2026-08-27 21:24 UTC).
- [x] Defined stored Builder, live legacy Builder-profile, and non-Builder
  compatibility modes without migration (2026-08-27 21:24 UTC).
- [x] Simulated the exact normalization across all 128 named configs: 126
  geographic, 2 RHEM-family, and 0 invalid compositions (2026-08-27 21:28 UTC).
- [x] Dispositioned fresh amendment-2 advisory findings with a 128-row closed
  inventory, Turkey identity, project-local/query states, no-capability mode,
  scoped runtime consumers, RQ discovery, exact errors, and rollback
  correction (2026-08-27 21:28 UTC).
- [x] Scoped new locale validation to non-flattened legacy runs and froze
  Turkey's exact classification-only profile record after correctness re-review
  (2026-08-27 21:28 UTC).
- [x] Obtained independent advisory correctness and governance `READY`
  verdicts for the exact amendment-2 proposal (2026-08-27 21:35 UTC).
- [x] Superseded unratified amendment 2 with an explicit acknowledged
  capability-refresh proposal after the operator resolved the on-demand versus
  provenance tradeoff (2026-08-27 22:01 UTC).
- [x] Dispositioned amendment-3 governance findings by making schema-v2
  refresh consistently unavailable, naming the generated RQ graph artifact,
  and adding refresh/reopen plus reader-floor rollback evidence (2026-08-27
  22:18 UTC).
- [x] Corrected capability refresh to preserve project selection defaults,
  mods, and the climate station selector; incompatible removals now make
  refresh explicitly unavailable instead of silently applying current Builder
  defaults (2026-08-27 22:23 UTC).
- [x] Closed refresh provenance, structural-evolution, transaction-commit, and
  locale-congruence gaps with bounded historical identities, exact delta JSON,
  Builder-source-only eligibility, and a WP12D reader floor with the refresh
  writer absent (2026-08-27 22:23 UTC).
- [x] Obtained independent amendment-3 advisory correctness and governance
  `READY` verdicts with no unresolved High or Medium findings (2026-08-27
  22:23 UTC).
- [x] Operator explicitly ratified amendment `PC-24/WP12D-20260827-3` exactly
  as documented and authorized the standalone checkpoint and subsequent
  implementation (2026-08-27 22:23 UTC).
- [x] Promoted the ratified behavior into every affected canonical contract,
  ADR, developer contract, agent API contract, and user-facing update guide
  (2026-08-27 23:57 UTC).
- [x] Closed the binding review findings and obtained independent correctness,
  governance, and security READY verdicts with no unresolved High, Medium, or
  blocking findings; correctness and security also reported no Low findings
  (2026-08-28 00:14 UTC).

## Decisions

### 2026-08-27 21:24 UTC: Effective `.cfg` owns locale

**Decision**: Interfaces navigation remains unchanged. Defaults plus the
selected named/project-local `.cfg` own legacy locale, while flattened Builder
configs carry their selected runtime token.

**Rationale**: Locale is executable configuration, not presentation state. A
URL or feature-registry copy would create a second authority.

### 2026-08-27 21:24 UTC: Dual live/frozen graph behavior is intentional

**Decision**: Recognized legacy single-base profiles use the current Builder
graph. Stored schema-v2/v3 projects use their frozen graph. Non-Builder,
overlay, RHEM, and schema-v1 modes retain current localized behavior.

**Rationale**: Legacy runs have no immutable graph to read, while Builder runs
must remain reproducible. Partial graphs for specialized profiles would hide
valid historical capabilities.

### 2026-08-27 21:24 UTC: Normalize without migration

**Decision**: Add the historical US locale to shared defaults, correct the
exact named specialized configs, and read effective config over stale
persisted locale state. Do not rewrite run files.

**Rationale**: Existing runs reopen against their contracted config chain, and
current selections remain protected by the exact-current carveout.

### 2026-08-27 21:28 UTC: Missing project-local locale has a compatibility value

**Decision**: An absent locale in a legacy project-local defaults/config chain
resolves in memory to `["us"]`; explicit empty/invalid fails and explicit values
remain authoritative. Locale query overrides are prohibited.

**Rationale**: This preserves historical local runs without rewriting them,
while preventing request state from becoming locale authority.

### 2026-08-27 21:28 UTC: Scope runtime locale use by domain

**Decision**: Do not change global `NoDbBase.locales`. The exact landuse, soil,
and climate catalog/provider consumers use effective config locale, and RQ
discovery uses the same resolved graph as mutation.

**Rationale**: This satisfies the requested domains without silently changing
unreviewed locale-sensitive runtime behavior.

### 2026-08-27 21:28 UTC: Classify flattened compatibility before legacy locale

**Decision**: Flattened no-capability and schema-v1 projects retain their
existing behavior without new locale validation or live-registry consultation.
Only non-flattened legacy runs enter the new effective-`.cfg` locale path.

**Rationale**: Historical flattened snapshots can legitimately omit locale,
and schema-v1 present axes already have a versioned compatibility contract.

### 2026-08-27 22:01 UTC: Stored authority may be explicitly refreshed

**Decision**: Stored schema-v2/v3 authority remains frozen by default. For an
eligible complete schema-v3 project only, an authorized end user may review the
complete same-locale graph delta, check an exact provenance/stability
acknowledgment, and atomically replace the graph through the existing
project-config amendment transaction. Schema-v2 refresh is unavailable.

**Rationale**: On-demand modeling requires old projects to adopt new maps and
capabilities. Explicit acknowledgment and reversible manifest deltas preserve
an audit trail while admitting that strict creation-time provenance continuity
and feature stability are diminished.

### 2026-08-27 22:23 UTC: Refresh changes the envelope, not selections

**Decision**: Rebase current axes, relationships, and provider/source revisions
around canonically unchanged project `capability_defaults`, `nodb.mods`, and
`climate.cligen_db`. If any preserved selection is incompatible, make refresh
unavailable with diagnostic stable IDs.

**Rationale**: Adopting new capabilities must not silently convert an existing
project from Daymet to Vanilla, change its model tuple, or otherwise claim a
Builder default as the user's selection.

### 2026-08-27 22:23 UTC: Structural changes require their own reader floor

**Decision**: Validate schema-v3 graphs against append-only structural hashes,
deploy a WP12D reader floor with the refresh writer absent, and roll a writer
deployment back only to a reader that understands every exposed identity. Refresh is
Builder-source-only and requires exact manifest/config locale and selection
congruence.

**Rationale**: A fixed current-profile validator would invalidate frozen old
graphs after a new map is added, while pre-WP12D reader `187a856d4` cannot be
claimed to understand future structural graphs.

## Risks

- A stale `Ron._locales` can defeat config normalization. Directly prove
  effective config precedence without file mutation.
- A live graph can over-narrow a legacy run. Render all authorized recovery
  choices plus the disabled current value and allow exact-current rebuild.
- A registry failure can encourage an unsafe broad fallback. Fail explicitly
  with diagnostic details.
- Shared US defaults can misclassify a specialized config. Parse all 128 files
  and explicitly override known Portland/RHEM/Canada/Tenerife cases.

## Verification Checklist

- [ ] Full named-config effective-locale inventory and malformed-state tests.
- [ ] Five legacy Builder-profile UI/API/build parity suites.
- [ ] Stored schema-v2/v3 drift isolation and schema-v1/non-Builder/overlay
  compatibility suites.
- [ ] Flattened no-capability/schema-v1 absent, empty, unknown, valid-locale,
  and present-axis fixtures with no live-registry consultation.
- [ ] Exact Turkey profile serialization/catalog revision and `yasin` reopen
  behavior.
- [ ] Shared locale-to-graph hotpath across Builder creation, legacy live
  authority, capability-refresh preview, and apply.
- [ ] Accessible acknowledgment UI and direct-API enforcement for
  additive-only, capability-only, and combined update previews.
- [ ] Atomic graph replacement, reversible manifest delta, crash recovery, and
  pre-reservation rejection evidence.
- [ ] Selection-preserving refresh and removed/incompatible-selection refusal
  with no config, manifest, reservation, or queue side effects.
- [ ] Current production identities plus a test-only genuine two-identity
  structural transition; prove `280cf7e84` and current share one identity.
- [ ] Fault evidence on both sides of config replacement plus terminal job/UI
  reconciliation of the recovered pair.
- [ ] Historical last-update inference and exact latest-preview idempotent
  HTTP/RQ retry results without duplicate amendments.
- [ ] Direct exact-current positives and no-mutation rejection negatives.
- [ ] Frontend link/page non-change assertions and standard frontend gates.
- [ ] Full Python, stubs, broad exceptions, vulture, diff, and docs gates.
- [ ] Binding correctness/governance/security checkpoint reviews and final
  correctness/security implementation reviews have no unresolved High or
  Medium.
- [ ] Exact-host `forest` legacy/stored acceptance without image rebuild.
- [ ] Exact-host `forest` acknowledged schema-v3 refresh/reopen acceptance and
  rollback to the recorded WP12D reader floor proving the refreshed config and
  manifest remain readable and unchanged.
- [ ] Scope-vs-changed-files comparison carried into WP12.

## Exact Dirty-Path Exclusions

The following preexisting dirty paths are unrelated and must never be staged:

- `docker/validate-cap-runtime-contract.sh`;
- `docs/infrastructure/incident-2026-08-25-production-compose-partial-build.md`;
- `docs/standards/hardening-lifecycle-standard.md`;
- `docs/ui-docs/cap-js-captcha-auth.md`;
- `docs/work-packages/20260823_session_cookie_namespace_migration/artifacts/rollout_runbook.md`;
- `docs/work-packages/20260823_session_cookie_namespace_migration/prompts/active/session_cookie_namespace_migration_execplan.md`;
- `docs/work-packages/20260823_session_cookie_namespace_migration/tracker.md`;
- `docs/work-packages/20260825_cap_runtime_deploy_hardening/package.md`;
- `docs/work-packages/20260825_cap_runtime_deploy_hardening/prompts/active/cap_runtime_deploy_hardening_execplan.md`;
- `docs/work-packages/20260825_cap_runtime_deploy_hardening/tracker.md`; and
- `services/cap/canary.js`.

Every commit must be path-staged and compared with the ratified boundary.
