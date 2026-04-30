# WEPP Gregorian Leap-Year Contract and Centurial Tolerance

**Status**: Open (2026-04-30)
**Timezone**: UTC

## Overview

WEPP currently classifies leap years using `year % 4 == 0`, which treats year `100` as leap and emits incorrect warnings when February has 28 days. This package updates WEPP calendar logic to Gregorian rules while preserving operational tolerance for legacy climate inputs that still include day 366 in non-400 centurial years.

## Objectives

- Replace simple modulo-4 leap checks with Gregorian leap logic at all active runtime call sites.
- Preserve compatibility for legacy centurial climate files that include 366 days even when Gregorian says common year.
- Remove false-positive leap warnings for year `100` with 28-day February.
- Keep existing behavior for true Gregorian leap years (for example, 2000).
- Ship with regression coverage and binary validation evidence for vendoring.

## Scope

### Included

- WEPP source updates in `/workdir/wepp-forest/src` for leap-year classification and day-count handling.
- Warning/compatibility messaging updates where leap assumptions are surfaced (`stmget.for`).
- Regression coverage in `/workdir/wepp-forest/tests` for centurial-year edge cases.
- Build, smoke, watchlist, and pytest evidence in `wepp-forest`, followed by vendoring/update evidence in `wepppy`.

### Explicitly Out of Scope

- Reformatting or broad refactors unrelated to leap-year contract behavior.
- Changes to non-calendar hydrology/erosion equations.
- UI/route changes in WEPPcloud outside binary vendoring and changelog sync.

## Stakeholders

- **Primary**: WEPP binary maintainers and WEPPcloud operators.
- **Reviewers**: WEPP-forest maintainers and wepp_runner maintainers.
- **Security Reviewer**: Not required; no new auth/public surface.
- **Informed**: Incident responders monitoring hillslope/watershed runtime regressions.

## Success Criteria

- [ ] Year `100` with 28-day February no longer triggers the leap-year warning block.
- [ ] Non-400 centurial inputs that still contain day 366 remain runnable (tolerated, no fatal stop).
- [ ] Gregorian leap years retain expected handling (for example, year `2000` still treated as leap).
- [ ] `wepp-forest` required validation gates pass for the candidate binaries.
- [ ] Patched binaries are vendored into `wepppy` with provenance + smoke checks and changelog updates.

## Dependencies

### Prerequisites

- `/workdir/wepp-forest` checkout is available and buildable with pinned `gfortran` workflow.
- Existing runner and fixture validation tooling remains available (`tools/smoke_wepp_binary_host.sh`, watchlist, pytest).

### Blocks

- Final production rollout of the next `wepp_2604xx` refresh that includes this contract patch.

## Related Packages

- **Related**: [20260429_totalwatsed3_storage_optional_terms](../20260429_totalwatsed3_storage_optional_terms/package.md)
- **Related**: [20260427_rq_subwta_precondition_contract](../20260427_rq_subwta_precondition_contract/package.md)
- **Follow-up**: Optional CLIGEN/calendar documentation harmonization package if external producers need explicit centurial-day guidance.

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium (calendar edge logic affects runtime loops and annual aggregation).

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Numerical/calendar contract correction in WEPP runtime; no new network/auth/input attack surface.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)

- **Failure signature(s)**:
  - `*Leap year detected with 28 days in February*`
  - `*to February in year  100.  Leap year annual values*`
- **Related prior hardening efforts**: `wepp_260429` hotfix cycle and hillslope timeout incident triage.
- **Health signals**:
  - Centurial-year climate replay no longer emits false leap warning for 28-day February.
  - Legacy 366-day centurial climate replay completes without fatal stop.
- **Danger signals**:
  - New off-by-one day routing regressions in annual loops.
  - Output drift on non-centurial baseline fixtures.
- **Observation window**: 14 days after vendor rollout.
- **Temporary calluses introduced**: None planned.
- **Callus softening hypothesis (if applicable)**: N/A.

## References

- `/workdir/wepp-forest/src/stmget.for` - leap warning trigger and warning text.
- `/workdir/wepp-forest/src/contin.for` - yearly loop leap flag.
- `/workdir/wepp-forest/src/wshdrv.for` - watershed yearly loop leap flag.
- `/workdir/wepp-forest/src/wshpas.for` - watershed pass-file year day-count logic.
- `/workdir/wepp-forest/tests/fixtures/reconciled_condenser_pw0/logs/pw0.stdout` - existing year-100 warning evidence.
- `wepp_runner/AGENTS.md` - vendoring/provenance gate requirements.

## Deliverables

- Package docs (`package.md`, `tracker.md`, active ExecPlan).
- WEPP source patch and regression tests in `wepp-forest`.
- Updated `wepp-forest/change-log.md` and synced vendored changelog copy in `wepppy`.
- Updated vendored binaries in `wepppy/wepp_runner/bin` with validation evidence.

## Follow-up Work

- Confirm whether external climate generators should emit explicit compatibility metadata for non-Gregorian centurial day-366 inputs.
- Optional spec note in WEPP user docs describing tolerant centurial handling policy.
