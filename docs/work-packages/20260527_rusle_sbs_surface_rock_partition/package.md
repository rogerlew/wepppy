# RUSLE `scenario_sbs` Surface-Rock Partition Integration

**Status**: Open (2026-05-27)
**Timezone**: UTC

## Overview

This package scopes and implements surface-rock partitioning for `scenario_sbs` RUSLE `C` calculations so stony bare fractions are not treated as fully exposed erodible soil. The contract is intentionally RAP-independent: `scenario_sbs` should not require RAP raster retrieval or RAP-year selection.

## Objectives

- Implement `scenario_sbs` `C`-factor bare partitioning with a user-facing `rock_fraction_of_sbs_bare` control.
- Ensure the SBS rock control is RAP-independent and uses only SBS lookup bare context.
- Support `auto` defaults from SSURGO `cosurffrags` first, with top-horizon `cfvo` fallback.
- Persist manifest provenance for effective value and source (`user` vs `auto`).
- Add focused regressions across UI, rq-engine API contract, and RUSLE controller/C integration.

## Scope

### Included

- `wepppy/nodb/mods/rusle/specification.md` updates for SBS rock-partition formula and controls.
- Runtime and controller updates in:
  - `wepppy/nodb/mods/rusle/c_integration.py`
  - `wepppy/nodb/mods/rusle/rusle.py`
- RQ API/default metadata updates in:
  - `wepppy/microservices/rq_engine/rusle_routes.py`
  - `wepppy/microservices/rq_engine/schema_defaults_routes.py`
- UI wiring updates in:
  - `wepppy/weppcloud/templates/controls/rusle_pure.htm`
  - `wepppy/weppcloud/controllers_js/rusle.js`
- Focused test coverage for mode-specific payload and factor behavior.

### Explicitly Out of Scope

- Replacing `scenario_sbs` static severity lookup policy.
- Building a new spatial surface-rock raster product.
- Recalibrating `K` profile-rock class-shift thresholds.
- Refactoring `observed_rap` rock partition behavior beyond shared helper reuse.

## Stakeholders

- **Primary**: WEPPcloud RUSLE users evaluating SBS scenarios in rocky landscapes.
- **Reviewers**: RUSLE module maintainers; WEPPcloud UI and rq-engine maintainers.
- **Security Reviewer**: Not required by triage.
- **Informed**: Disturbed/RUSLE documentation maintainers.

## Success Criteria

- [ ] `scenario_sbs` supports `rock_fraction_of_sbs_bare` (`[0,1]` or `auto`) end-to-end.
- [ ] SBS `C` math applies `bare_lookup` partition (`bare_exposed = bare_lookup * (1 - r_sbs_bare)`) before `C = exp(-0.04 * fg_effective_pct)`.
- [ ] `scenario_sbs` rock path is RAP-independent (no RAP-year or RAP-raster dependency).
- [ ] `auto` default uses `cosurffrags` first and `cfvo` fallback with SBS-bare normalization.
- [ ] UI explicitly instructs users to verify field/local surface rock cover and set fraction accordingly.
- [ ] Manifest metadata records effective value and source for SBS rock control.
- [ ] Focused Python + JS regressions pass for SBS control and payload contracts.

## Parameterization ADR Gate

- **Parameterization change present**: `yes`
- **ADR required**: `yes`
- **ADR link(s)**: `docs/adrs/ADR-0004-rusle-scenario-sbs-surface-rock-partition.md`
- **Decision provenance captured**: `yes`

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites

- Baseline RUSLE `scenario_sbs` static lookup pathway in place.
- Existing surface-rock proxy conventions from `observed_rap` package available for reuse.

### Blocks

- Scenario-based calibration and comparison packages that depend on stony-surface SBS realism.

## Related Packages

- **Related**: [20260527_rusle_c_surface_rock_partition](../20260527_rusle_c_surface_rock_partition/package.md)
- **Related**: [20260321_rusle_c_modes_implementation](../20260321_rusle_c_modes_implementation/package.md)
- **Related**: [20260507_rusle_k_cfvo_integration](../20260507_rusle_k_cfvo_integration/package.md)

## Timeline Estimate

- **Expected duration**: 1-2 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium (cross-layer contract touches UI/API/runtime).

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Parameterization and input-contract updates only; no auth/session/secrets boundary expansion.
- **Security review artifact**: `N/A`

## References

- `wepppy/nodb/mods/rusle/specification.md`
- `docs/adrs/ADR-0004-rusle-scenario-sbs-surface-rock-partition.md`
- `docs/work-packages/20260527_rusle_c_surface_rock_partition/package.md`
- `docs/work-packages/20260527_rusle_c_surface_rock_partition/tracker.md`

## Deliverables

- SBS rock-partition implementation across UI/API/controller/runtime.
- Focused regression coverage and validation evidence.
- Updated package tracker and active ExecPlan history.

## Follow-up Work

- Evaluate whether run-scoped mapped surface-fragment products can replace coarse AOI-level proxy defaults in future.

## Kickoff Prompt

- Active ExecPlan: `docs/work-packages/20260527_rusle_sbs_surface_rock_partition/prompts/active/rusle_sbs_surface_rock_partition_execplan.md`
