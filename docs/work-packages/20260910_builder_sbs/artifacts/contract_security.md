# Builder SBS contract security review

## Findings and disposition

| ID | Severity | Finding and evidence | Disposition |
| --- | --- | --- | --- |
| BSC-01 | Medium | Enabling Disturbed also dispatches landuse and soil adjustments without an SBS map. `Disturbed.on()` handles `LANDUSE_DOMLC_COMPLETE` and `SOILS_BUILD_COMPLETE` without a map guard. Describing this as upload-only support would conceal a generated-input behavior change. | Resolved by explicit operator authorization and ADR-0064. The canonical contract now requires normal Disturbed behavior, including the no-map case. No SBS-only guard is authorized. |
| BSC-02 | Low | Relaxing the manifest/config equality check to arbitrary module sets could accept unrelated module differences. The existing boundary is `_assert_builder_congruence()` in `project_config_update.py`. | Resolved in the contract: accept only exact historical selected lists or `['disturbed', *selected_mods_without_disturbed]`; retain ordered equality and all other validation. |
| BSC-03 | Low | Plain landuse mappings omit classes required by Disturbed. A broad mapping fallback or rewriting existing custom mappings would hide source/provenance differences. | Resolved by the amended contract and ADR-0064: select named existing compatible mappings in provider writes/revisions, preserve lookup contents, and limit existing-run mapping repair to fair-division's absent/default state. |

No unresolved medium/high contract findings. No risk acceptance is requested.

## Approval and scope

**Contract security gate: pass.** Independent reviewer: Codex
`contract_security`, 2026-09-10. Starting revision: `595816476`.
Reviewed the amended [canonical contract](../../../schemas/project-owned-config-contract.md#builder-soil-burn-severity-support-2026-09-10),
[ADR-0064](../../../adrs/ADR-0064-builder-disturbed-default.md),
[checkpoint](20260910_contract_decision.md), package and active ExecPlan.
The Builder registry, resolver, snapshot, update validator and Disturbed
implementation had no package runtime changes at this review. This disposition
includes the subsequent compatible-landuse-mapping amendment.

This approves the pre-implementation contract. The independent correctness
review and standalone ancestor checkpoint remain required before implementation.
Final implementation and repair evidence are pending; this review does not claim
those gates passed. No runtime files or live projects were changed by the reviewer.

## Actual boundaries and residual risk

Security impact is **low**: the change composes existing authenticated creation
and SBS operations, with no new endpoint, token scope, upload type, path input,
queue edge, shell command or egress destination. Existing upload validation and
resource limits remain the inherited boundary; this is not a fresh certification
of every legacy SBS transport path.

- `config_builder/resolver.py` currently writes `selections.mods` directly;
  `snapshot.py` separately records source selections and hashes materialized
  config bytes. The new fixed dependency must preserve that distinction,
  capability validation, materialization checks and manifest digest checks.
- `Ron.__init__()` initializes selected modules. `NoDbBase.trigger()` dispatches
  from each controller's persisted module list. A Ron-only repair would leave
  downstream event owners inconsistent.
- `Disturbed.__init__()` creates its directory and resets lookup state. It must
  run only for verified absent state; populated state must be reused. Corrupt
  controller state or orphaned artifacts must not be erased to force creation.
- The explicit repair is restricted to `fair-division`. Apply only the intended
  module-list additions and absent/default Landuse mapping repair under canonical
  lock/refresh/persist transactions;
  preserve unrelated fields, maps, config bytes and manifest digests. Read-only
  or malformed state fails explicitly. No GET repair or fleet migration is
  authorized. Cross-controller completion must be verified before reporting
  repair success; individual NoDb locks do not make the whole repair atomic.
- Normal Disturbed adjustments may change subsequently generated model inputs.
  That effect is now explicit and authorized. Existing inputs are not rebuilt
  by this repair. Numerical routines and lookup contents remain unchanged;
  selecting compatible mapping defaults is an explicit part of the amendment.
- The fixed mappings are `disturbed` for NLCD/EMAPR, `eu-disturbed` for CORINE,
  `au-disturbed` for Australian landuse and existing `c3s-disturbed` for C3S.
  `managements.py` already resolves `eu-disturbed` to
  `eu-corine-disturbed.json`. No arbitrary mapping path is introduced. Provider
  revisions must change with the selected mapping. Existing populated mapping
  values remain preserved; adding a missing config option uses explicit
  preview/apply. Both provider congruence/completeness validators still apply.
- `Landuse._custom_mapping_relpath` can override a `None` `_mapping`. Inspect and
  preserve that reference and its artifacts during repair; an absent base
  mapping alone does not establish the absence of custom state.

## Required implementation evidence

Focused validation must directly exercise real boundaries, including:

1. New Builder creation with absent optional selections, preserved populated
   selections and each exposed locale/backend; real controller initialization
   and rehydration, including event-owner module lists.
2. Exact historical and new manifest/config compatibility, rejection of extra,
   missing, reordered or malformed selections, and preservation of historical
   config values through update preview/apply. Exercise missing and populated
   mappings without relaxing unrelated source-selection validation.
3. Lock-based repair with absent and existing Disturbed state, preservation of
   unrelated values/artifacts, and explicit failure for read-only or malformed
   state. Verify config and manifest digests before and after the named repair.
4. Existing authenticated upload/classification/removal on a disposable Builder
   project. Confirm optional no-map behavior follows normal Disturbed semantics;
   no new guard or numerical default is introduced.
5. Load each exposed source's actual selected mapping, verify required burn
   classes and source-class coverage, and verify provider revision/provenance.
   Preserve custom mapping references even when the persisted base mapping is
   absent. Confirm rehydration of fair-division's explicitly repaired mapping.

The operator explicitly excluded the full suite for this package. Focused and
browser evidence, plus final correctness review, are still required.
