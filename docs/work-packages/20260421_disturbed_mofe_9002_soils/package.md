# Disturbed MOFE 9002 Soil Support Parity

**Status**: Complete (2026-04-22)
**Timezone**: UTC

## Overview
This package adds explicit, tested `sol_ver=9002` support for disturbed MOFE soil building by aligning MOFE behavior with the established single-OFE disturbed soil conversion contract. Current code calls `to_over9000(version=sol_ver)` in MOFE paths, but 9002-specific behavior is not explicitly covered by MOFE tests and lookup-miss behavior is inconsistent with single-OFE semantics.

## Objectives
- Establish and document the normative `9002` disturbed-soil contract for MOFE runs.
- Implement MOFE `9002` behavior that is parity-aligned with single-OFE logic where feasible and explicitly documented where MOFE must differ.
- Add regression coverage that directly exercises MOFE `sol_ver=9002` success and fallback paths.
- Validate disturbed MOFE 9002 behavior using both unit tests and a run-level integration target config.

## Scope
This package covers disturbed controller MOFE soil-generation logic and its tests/docs for `sol_ver=9002`.

### Included
- Review-based parity matrix of single-OFE vs MOFE disturbed soil-building behavior for `9002`.
- Disturbed MOFE implementation updates in `wepppy/nodb/mods/disturbed/disturbed.py`.
- Regression tests in `tests/nodb/mods/disturbed/test_modify_soils_mofe.py` (and adjacent modules as needed).
- Disturbed module documentation updates (`README` and package artifacts) to lock the final behavior contract.

### Explicitly Out of Scope
- Non-disturbed soil pipelines.
- New soil format support beyond existing 7778/9001/9002/9003/9005 handling.
- Unrelated MOFE topology or hillslope segmentation behavior.
- Broad lookup-table redesign outside the minimum needed for MOFE 9002 parity.

## Stakeholders
- **Primary**: Disturbed module maintainers and users running `disturbed9002-*-mofe` configs.
- **Reviewers**: NoDb disturbed maintainers, soils utility maintainers, QA reviewers.
- **Security Reviewer**: Not required as a dedicated artifact unless package scope expands.
- **Informed**: RQ engine and WEPPcloud run operators consuming disturbed MOFE outputs.

## Success Criteria
- [x] A documented parity decision table exists for single-OFE vs MOFE `9002` soil building, including intentional differences.
- [x] MOFE `9002` soil generation has explicit contract behavior for lookup-hit and lookup-miss classes.
- [x] MOFE `9002` outputs no longer rely on undocumented fallback behavior.
- [x] Regression tests cover MOFE `9002` lookup-hit, lookup-miss, treatment-suffix, and area/coverage recomputation paths.
- [x] Targeted disturbed and soil utility tests pass.
- [x] At least one config-level MOFE check (`disturbed9002-10-mofe` or `disturbed9002-wbt-mofe`) is executed and recorded with expected `9002` + MOFE flags.

## Dependencies

### Prerequisites
- Existing disturbed lookup contract and data:
  - `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv`
- Existing single-OFE disturbed soil conversion behavior in:
  - `Disturbed.modify_soil`
- Existing soil conversion contract in:
  - `WeppSoilUtil.to_over9000(version=9002)`

### Blocks
- Follow-on MOFE behavior changes that assume stable disturbed 9002 semantics.

## Related Packages
- **Related**: [20260401_disturbed_bd_rosetta_wc_fc](../20260401_disturbed_bd_rosetta_wc_fc/package.md)
- **Related**: [20260325_disturbed_lookup_hardening](../20260325_disturbed_lookup_hardening/package.md)
- **Follow-up**: Optional package for broader single-OFE/MOFE disturbed code-path unification after parity lock.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium (behavioral regression risk in disturbed run outputs)

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Changes are confined to run-scoped soil generation contracts and tests; no auth/session/secrets or new network/file-ingress surface.
- **Security review artifact**: `N/A`

## References
- `wepppy/nodb/mods/disturbed/disturbed.py` - single-OFE and MOFE disturbed soil build paths.
- `tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py` - single-OFE behavior reference.
- `tests/nodb/mods/disturbed/test_modify_soils_mofe.py` - MOFE behavior coverage target.
- `wepppy/wepp/soils/utils/wepp_soil_util.py` - 9002 conversion contract (`to_over9000`).
- `wepppy/wepp/soils/utils/multi_ofe.py` - MOFE synthesis requirement (same-version soil stack).
- `wepppy/nodb/configs/disturbed9002-10-mofe.cfg` - run-level MOFE 9002 config.

## Deliverables
- Updated disturbed MOFE implementation with explicit 9002 contract semantics.
- Added/updated regression tests covering MOFE 9002 paths.
- Package artifacts documenting parity decisions and validation evidence.
- Updated module docs if behavior contract changes.

## Initial Review Findings (2026-04-21)
- Single-OFE reference path (`modify_soil`) uses normalized disturbed-class lookup and returns base `mukey` on lookup miss, even for `sol_ver=9002`.
- MOFE path (`modify_mofe_soils`) currently injects a special replacement dict when lookup misses and `sol_ver == 9002.0` (`luse`, `stext`, `ksatfac=0.0`, `ksatrec=0.0`), but this behavior is not covered by dedicated `9002` MOFE tests.
- MOFE lookup-miss keying currently collapses to `f"{mukey}-{texid}"` instead of class-specific keying, which can merge distinct disturbed classes into one generated soil in miss scenarios.
- Existing MOFE tests validate general over-9000/7778 routing and suffix normalization, but do not assert `sol_ver=9002`-specific fallback semantics.

## Parity Decision Table (Locked 2026-04-22)

| Scenario | Single-OFE (`modify_soil`) reference | MOFE `9002` contract | Rationale |
|----------|--------------------------------------|----------------------|-----------|
| Lookup hit | Normalize treatment suffix for lookup key (`lookup_disturbed_class`), apply lookup replacements, key generated soil with full disturbed class. | Same parity behavior: normalized lookup key + full disturbed-class soil key + lookup replacements forwarded to `to_over9000(version=9002)`. | Single-OFE is normative reference; no MOFE-specific deviation required. |
| Lookup miss | Return base `mukey` (no disturbed lookup replacements applied). | Intentional MOFE-specific deviation: generate class-specific migrated `9002` soil with explicit neutral fallback replacements (`luse`, `stext`, `ksatfac=0.0`, `ksatrec=0.0`) and no lookup erodibility overrides (`ki`, `kr`, `shcrit`, `avke`, `bd`, etc.). | `SoilMultipleOfeSynth` requires same-version soil stack inputs; a direct base `mukey` passthrough can violate stack version homogeneity when other OFEs are migrated to `9002`. |
| Treatment suffix handling | Lookup uses normalized base class while generated key keeps full treatment-modified class suffix. | Same parity behavior for lookup key normalization and output key naming. | Prevent lookup misses for treatment variants while preserving output provenance per OFE class. |
| Class keying on lookup miss | Collapses naturally to base `mukey` in single-OFE path. | No class collapsing for MOFE `9002`; key includes full disturbed class (`mukey-texid-disturbed_class`). | Avoid unintentional merging of distinct disturbed classes into one fallback artifact in MOFE stacks. |

## Validation Evidence (2026-04-22)

- `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py --maxfail=1` -> `17 passed`
- `wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py --maxfail=1` -> `30 passed`
- `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1` -> `49 passed`
- `wctl run-python -- - <<'PY' ... Disturbed(temp_wd, disturbed9002-10-mofe.cfg) ... PY` -> printed `disturbed.sol_ver=9002.0` and `config.wepp.multi_ofe=true (text-level check)`

## Follow-up Work
- Consider extracting shared disturbed soil-conversion helper logic across single-OFE and MOFE paths after parity behavior is locked and tested.
