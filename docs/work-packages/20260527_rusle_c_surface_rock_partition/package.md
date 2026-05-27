# RUSLE C Surface-Rock Partition Implementation

**Status**: Open (2026-05-27)
**Timezone**: UTC

## Overview

This package implements the new `observed_rap` surface-rock partition feature defined in the RUSLE specification and ADR-0003. The goal is to prevent stony armored surfaces from being treated as fully exposed bare soil by introducing a user-facing `rock_fraction_of_rap_bare` control, a conservative `auto` proxy default from top-horizon `cfvo`, and explicit user guidance to verify rock cover with field/local evidence.

## Objectives

- Implement `observed_rap` C-factor runtime partitioning of RAP bare ground into exposed mineral soil and protective surface rock.
- Add user-facing `rock_fraction_of_rap_bare` control to the RUSLE UI with explicit verification guidance.
- Support `auto` defaulting from top-horizon profile `cfvo` (when available) with explicit proxy semantics.
- Persist manifest provenance for effective value and source (`user` vs `auto`).
- Add targeted regressions for C-factor math, API payload contracts, UI payload behavior, and manifest metadata.
- Run independent review and disposition all high/medium findings before closeout.

## Scope

### Included

- `wepppy/nodb/mods/rusle/c_integration.py` and related C helpers for observed RAP partition logic.
- `wepppy/nodb/mods/rusle/rusle.py` option plumbing and manifest metadata updates.
- `wepppy/microservices/rq_engine/rusle_routes.py` build payload allowlist update.
- `wepppy/microservices/rq_engine/schema_defaults_routes.py` request schema/default metadata updates.
- `wepppy/weppcloud/templates/controls/rusle_pure.htm` UI control + guidance copy.
- `wepppy/weppcloud/controllers_js/rusle.js` payload handling and mode-specific behavior.
- Focused regressions in:
  - `tests/nodb/mods/test_rusle_c_integration.py`
  - `tests/nodb/mods/test_rusle_controller.py`
  - `tests/microservices/test_rq_engine_rusle_routes.py`
  - `tests/microservices/test_rq_engine_schema_defaults_routes.py`
  - `wepppy/weppcloud/controllers_js/__tests__/rusle.test.js`
- Work-package execution artifacts: review notes and findings disposition.

### Explicitly Out of Scope

- New spatial surface-rock raster/proxy generation beyond `cfvo`-based `auto` default.
- Recalibration of `b` parameter or broader C-subfactor model redesign.
- Changes to `scenario_sbs` C mode behavior.
- K-factor `cfvo` class-shift policy changes.

## Stakeholders

- **Primary**: WEPPcloud RUSLE users modeling stony landscapes.
- **Reviewers**: RUSLE module maintainers, WEPPcloud route/UI maintainers.
- **Security Reviewer**: Not required by triage for this package.
- **Informed**: Disturbed/RUSLE documentation maintainers.

## Success Criteria

- [ ] `observed_rap` C computation uses `rock_fraction_of_rap_bare` partition contract from spec.
- [ ] RUSLE UI exposes `rock_fraction_of_rap_bare` with explicit verification guidance text.
- [ ] `auto` default is supported with explicit proxy semantics:
  - use top-horizon `cfvo` proxy when available (`clamp(cfvo_0_5cm_volpct / 100, 0, 1)`)
  - fallback to `0.0` when `cfvo` is unavailable and record fallback reason in manifest metadata
- [ ] Build payload contract includes `rock_fraction_of_rap_bare` end-to-end (UI -> rq-engine -> RUSLE controller), including schema/default discoverability metadata.
- [ ] Input contract is enforced as numeric `[0,1]` or literal `auto`; invalid values (`<0`, `>1`, non-numeric non-`auto`) are rejected with canonical RQ error payload behavior.
- [ ] Manifest captures effective rock fraction and value source provenance (`user` vs `auto`), including explicit `auto` fallback annotation when `cfvo` is missing.
- [ ] Targeted Python/JS tests pass for changed behavior, including boundary/error-path regression coverage.
- [ ] Review artifact and findings disposition artifact are complete with no unresolved high/medium findings.

## Parameterization ADR Gate

- **Parameterization change present**: `yes`
- **ADR required**: `yes`
- **ADR link(s)**: `docs/adrs/ADR-0003-rusle-observed-rap-surface-rock-partition.md`
- **Decision provenance captured**: `yes`

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites

- Specification updates in `wepppy/nodb/mods/rusle/specification.md` for canonical surface-rock handling.
- ADR accepted in `docs/adrs/ADR-0003-rusle-observed-rap-surface-rock-partition.md`.

### Blocks

- Follow-up validation packages that rely on improved stony-surface C behavior.

## Related Packages

- **Related**: [20260321_rusle_c_modes_implementation](../20260321_rusle_c_modes_implementation/package.md)
- **Related**: [20260321_rusle_nodb_ui](../20260321_rusle_nodb_ui/package.md)
- **Related**: [20260507_rusle_k_cfvo_integration](../20260507_rusle_k_cfvo_integration/package.md)

## Timeline Estimate

- **Expected duration**: 2-3 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium (cross-layer contract change across UI/API/controller/factor math).

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: numerical/modeling and UI-input contract updates only; no auth/session/secrets/egress contract expansion.
- **Security review artifact**: `N/A`

## References

- `wepppy/nodb/mods/rusle/specification.md`
- `docs/adrs/ADR-0003-rusle-observed-rap-surface-rock-partition.md`
- `wepppy/nodb/mods/rusle/c_integration.py`
- `wepppy/nodb/mods/rusle/rusle.py`
- `wepppy/microservices/rq_engine/rusle_routes.py`
- `wepppy/microservices/rq_engine/schema_defaults_routes.py`
- `wepppy/weppcloud/templates/controls/rusle_pure.htm`
- `wepppy/weppcloud/controllers_js/rusle.js`

## Deliverables

- Runtime C-factor feature implementation and tests.
- Updated RUSLE UI control behavior and guidance text.
- Package tracker and active ExecPlan updates during implementation.
- Review + disposition artifacts under `artifacts/`.

## Follow-up Work

- Evaluate whether a better surface-rock prior can be integrated in future (for example, run-scoped mapped surface fragments) without violating canonical RUSLE separation of surface vs profile effects.

## Kickoff Prompt

- Active ExecPlan: `docs/work-packages/20260527_rusle_c_surface_rock_partition/prompts/active/rusle_c_surface_rock_partition_execplan.md`
