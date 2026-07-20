# Omni Mod State Synchronization

**Stable ID**: REM-01
**Status**: Complete; implemented, validated, and dual-approved (2026-07-20)
**Timezone**: UTC

## Overview

Privileged users can currently lose the Omni Contrasts toggle until Omni
Scenarios is active, while activating Omni Scenarios can make the contrasts
section and preflight entry appear without an active contrasts checkbox. This
package restores independent gating and makes the persisted mod list the single
authority for the Mods checkbox, run-page section, and preflight navigation.

## Objectives

- Show Omni Contrasts in the Mods menu to every user. Keep it disabled with
  `Not Authorized` for callers below the internal enable role.
- Keep Omni Scenarios and Omni Contrasts independently persisted and rendered.
- Add backend, template/bootstrap, and controller regressions for the reported
  add-and-refresh sequence.
- Obtain two independent reviews and disposition every finding before closure.

## Scope

### Included

- Feature-registry visibility and dependency semantics.
- Run-header, runs-page, preflight-navigation, and dynamic controller state.
- Dev/Root authorization gates only for contrast run, dry-run, and delete;
  canonical run access plus Dev/Root on the CAP-gated report endpoint. Authorized
  payloads, queue behavior, and report formatting remain unchanged.
- Targeted pytest and Jest regression coverage.
- Contract checkpoint, dual-review artifacts, and final disposition.

### Explicitly Out of Scope

- Omni computation, RQ orchestration semantics, output schemas, and maturity promotion.
- Changes to the publication embargo or its role requirement.
- Production deployment or mutation of the reported run.

## Stakeholders

- **Primary**: WEPPcloud internal-feature users and run-page maintainers.
- **Reviewers**: Two independent read-only Codex reviewers.
- **Security Reviewer**: Required before implementation; initial gate recorded in `artifacts/2026-07-20_security_review.md`.
- **Informed**: WEPPcloud operators.

## Success Criteria

- [x] Every user sees Omni Contrasts; unauthorized users see a disabled
  checkbox with `Not Authorized` directly below the label.
- [x] An authorized user missing Omni Scenarios sees a disabled unchecked
  checkbox with a simple prerequisite reason.
- [x] Enabling Omni Scenarios does not enable, check, render, or preflight Omni Contrasts.
- [x] Enabling Omni Contrasts explicitly keeps its checkbox, section, preflight entry, and persisted mod state aligned across refresh.
- [x] Contrast run, dry-run, delete, and report reject User, PowerUser, and
  Admin before domain behavior; Dev and Root pass only with the applicable JWT
  scope/run-access or CAP/run-access boundaries satisfied.
- [x] Targeted pytest and Jest checks pass.
- [x] Both independent reviews are dispositioned with no unresolved high- or medium-severity findings.
- [x] The stable-tree repository-wide Python sweep passes.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes; the user supplied the required behavior on 2026-07-20 and `docs/adrs/ADR-0001-time-limited-publication-embargo-for-omni-contrasts.md` already requires independent gating.

## Dependencies

### Prerequisites

- Accepted Omni Contrasts embargo ADR and existing feature registry.
- Existing project mod toggle endpoint and dynamic section loader.

### Blocks

- Reliable internal use of Omni Contrasts from the runs page.

## Related Packages

- **Related**: `docs/work-packages/20260716_pure_ui_contract_ratification/`
- **Related**: `docs/work-packages/20251023_frontend_integration/`

## Timeline Estimate

- **Expected duration**: One focused session.
- **Complexity**: Medium.
- **Risk level**: High because role-gated state mutation is in scope.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package restores the existing Dev/Root policy at
  direct action/data entry points and adds missing canonical report run access,
  while crossing registered DOM-02 and DOM-25A/B authorization and
  persisted-state mutation boundaries.
- **Security review artifact**: `docs/work-packages/20260720_omni_mod_state_sync/artifacts/2026-07-20_security_review.md`

## Hardening and Callus Softening

- **Failure signature(s)**: Omni Contrasts absent from the Mods menu until Omni Scenarios is enabled; contrasts DOM/preflight visible while its persisted checkbox is false.
- **Related prior hardening efforts**: N/A
- **Health signals**: Checkbox, persisted mod list, section, and preflight entry agree before and after refresh.
- **Danger signals**: Any role-gate bypass or implicit addition of `omni_contrasts`.
- **Observation window**: Targeted automated regression plus operator smoke test after deployment.
- **Temporary calluses introduced**: None.
- **Callus softening hypothesis**: N/A.

## References

- `wepppy/weppcloud/feature_registry/specification.md` - Feature visibility and enablement contract.
- `docs/adrs/ADR-0001-time-limited-publication-embargo-for-omni-contrasts.md` - Independent internal gating decision.
- `wepppy/weppcloud/routes/run_0/run_0_bp.py` - Server-rendered mod visibility.
- `wepppy/weppcloud/controllers_js/project.js` - Dynamic toggle reconciliation.

## Deliverables

- Contract checkpoint and amended feature-registry specification.
- State synchronization implementation and regressions.
- Two review artifacts and one final disposition artifact.

## Follow-up Work

- Feed the REM-01 contract decision and regression evidence into the later
  DOM-02, DOM-25A, and DOM-25B audits without advancing their execution state.
