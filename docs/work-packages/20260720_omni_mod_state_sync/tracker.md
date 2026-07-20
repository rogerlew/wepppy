# Tracker – Omni Mod State Synchronization

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-20 21:08 UTC
**Current phase**: Security scope amendment ratification
**Last updated**: 2026-07-20 22:15 UTC
**Next milestone**: Commit the second docs-only ancestor, then implement route gates.
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `docs/work-packages/20260720_omni_mod_state_sync/artifacts/2026-07-20_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Implement and test contrast action/report authorization gates.
- [ ] Dispatch two independent final code reviews and disposition findings.
- [ ] Close documentation and package.

### In Progress

- [ ] Dual-review and commit the security scope amendment as a standalone ancestor.

### Blocked

- None.

### Done

- [x] Created package, active ExecPlan, contract decision, and specification amendment (2026-07-20 21:08 UTC).
- [x] Completed two independent read-only contract reviews and dispositioned all findings (2026-07-20 21:22 UTC).
- [x] Reverted the unregistered specification amendment; no implementation files were changed (2026-07-20 21:22 UTC).
- [x] Operator authorized GOV-00A expansion, REM-01 registration, and the
  discoverable-disabled `Not Authorized` UX (2026-07-20 21:23 UTC).
- [x] Completed two independent ratification reviews, dispositioned every
  finding, and received both post-fix approvals (2026-07-20 21:40 UTC).
- [x] Committed the standalone contract ancestor at
  `1afa57fd6d63b93688057143ec5c45daa6f3170f` (2026-07-20 21:42 UTC).
- [x] Implemented registry, route, template/bootstrap, and controller state
  synchronization (2026-07-20 21:50 UTC).
- [x] Added and passed focused Python/Jest regressions; rebuilt the ignored
  generated controller bundle (2026-07-20 21:52 UTC).
- [x] Accepted the first final-review action/report authorization finding and
  drafted the operator-authorized finite security amendment (2026-07-20 22:15 UTC).

## Timeline

- **2026-07-20 21:08 UTC** – Package created and contract checkpoint prepared at starting revision `a0c21b8727ca6b10c9dc1946087473d793a3554b`.
- **2026-07-20 21:22 UTC** – Dual review found two shared high-severity blockers; implementation stopped and the unregistered specification amendment was reverted.
- **2026-07-20 21:23 UTC** – Operator authorized bounded cross-owner ratification; REM-01 registration and contract amendments drafted.
- **2026-07-20 21:40 UTC** – Both independent reviewers approved the corrected
  GOV-00A-M1A/REM-01 contract ancestor with no unresolved high/medium findings.
- **2026-07-20 21:42 UTC** – Sealed the reviewed authority in standalone commit
  `1afa57fd6d63b93688057143ec5c45daa6f3170f`.
- **2026-07-20 21:52 UTC** – Focused implementation complete; 196 targeted
  Python tests and 27 Project-controller Jest tests pass, followed by full
  frontend lint and 638-test Jest validation.
- **2026-07-20 22:15 UTC** – Corrected the security amendment to add canonical
  run access plus Dev/Root to the CAP-gated report and require additive-boundary tests.

## Decisions Log

### 2026-07-20 21:08 UTC: Treat persisted feature ids as active-state authority

**Context**: Omni Contrasts was rendered from Omni Scenarios state even though both are separate feature ids and the accepted ADR requires independent gating.

**Options considered**:

1. Keep one combined Omni toggle and remove the contrasts checkbox.
2. Auto-enable contrasts with scenarios.
3. Preserve separate toggles and make each feature id control its own UI state.

**Decision**: Preserve separate toggles. Role/backend policy controls menu discoverability, `requires_features` controls enable-time validation, and each persisted id controls its checkbox, section, and preflight entry.

**Impact**: Enabling Omni Scenarios cannot implicitly activate Omni Contrasts; authorized users can still discover the contrasts option before its prerequisite is active.

### 2026-07-20 21:23 UTC: Discoverable-disabled menu contract

**Context**: The first review required a consistent exception to "visible means
usable" and registered ownership for the cross-domain fix.

**Options considered**:

1. Keep Omni Contrasts hidden from unauthorized users.
2. Show an enabled checkbox that rejects unauthorized requests.
3. Show a disabled checkbox with a direct reason.

**Decision**: Register REM-01 through GOV-00A. Show Omni Contrasts to every
user, disable it for unauthorized callers, and render the exact reason
`Not Authorized` directly below the label. Authorized callers missing Omni
Scenarios see a prerequisite reason and an unchecked disabled checkbox.

**Impact**: Discoverability no longer grants enable or dynamic-load authority;
the existing Dev/Root server gates remain mandatory.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Internal role gate accidentally broadened | High | Low | Preserve `min_role: dev`; add role and dynamic-route denial tests | Open |
| Dynamic contrast section loads without controller remount | Medium | Medium | Add Jest coverage for explicit contrast enable | Open |
| Preflight remains visible from stale DOM state | Medium | Medium | Assert own-id route/bootstrap flags and navigation synchronization | Open |
| Cross-domain remediation expands beyond REM-01 | High | Low | Enforce exact register exclusions and dual review | Mitigated by accepted contract |

## Verification Checklist

### Code Quality

- [x] Targeted tests passing.
- [x] Frontend tests passing.
- [x] Frontend lint clean.
- [x] Broad exception changed-file enforcement clean.

### Security

- [x] Security impact triage recorded with rationale.
- [x] Existing internal role gate remains a required acceptance condition.
- [ ] Review confirms no authorization bypass.
- [ ] Formal security gate passes with no unresolved medium/high findings.

### Documentation

- [x] Authoritative behavior accepted by dual review for the registered REM-01 ancestor.
- [ ] Work package closure notes complete.
- [x] No parameterization ADR required.

### Testing

- [x] Registry visibility regression.
- [x] Backend dependency and independence regressions.
- [x] Run-page/bootstrap active-state regressions.
- [x] Dynamic controller regression.
- [ ] RQ contrast action role, JWT scope, and run-access regressions.
- [ ] Flask contrast report CAP, run-access, and role regressions.

## Progress Notes

### 2026-07-20 21:08 UTC: Discovery and contract checkpoint

**Agent/Contributor**: Codex

**Work completed**:

- Confirmed the header hid contrasts through `requires_features`.
- Confirmed the runs route derived contrasts visibility from `show_omni` instead of `omni_contrasts` persisted state.
- Recorded the existing ADR as the unchanged independent-gating authority and amended the registry specification to remove its conflicting visibility rule.

**Blockers encountered**: None.

**Next steps**: Obtain two independent contract reviews, disposition findings, record the ancestor revision, then implement.

**Test results**: Not run; implementation has not started.

### 2026-07-20 21:22 UTC: Dual-review disposition and stop

**Agent/Contributor**: Codex with two independent read-only reviewers

**Work completed**:

- Accepted the shared high findings that the checkpoint lacks registered
  ownership and that the proposed specification amendment is an intended
  behavior change with an unresolved UX-policy conflict.
- Accepted the medium findings covering global `requires_features` fan-out,
  authorization regressions, rejected-toggle synchronization, legacy-invalid
  state behavior, and security triage.
- Reverted the specification amendment and made no production code changes.

**Blockers encountered**: DOM-02 depends on GOV-01 and shared foundations;
DOM-25A depends on DOM-14A and DOM-23; DOM-25B depends on DOM-25A, DOM-04A,
and DOM-04B. Those packages are planned rather than ratified/executed.

**Next steps**: Obtain operator direction to expand scope into the registered
dependency spine or amend governance through GOV-00A to define a bounded,
reviewed cross-owner remediation path.

**Test results**: Documentation lint passed before disposition; code tests were
not run because implementation is blocked.

### 2026-07-20 21:23 UTC: Operator unblocked bounded ratification

**Agent/Contributor**: User/operator and Codex

**Work completed**:

- Registered REM-01 as a defect-scoped borrower of DOM-02, DOM-25A, and DOM-25B.
- Drafted the GOV-00A bounded cross-owner remediation mechanism.
- Ratified the requested menu text and disabled-state semantics in the proposed
  feature-registry contract.

**Blockers encountered**: None; independent review is the next mandatory gate.

**Next steps**: Complete dual review, disposition findings, commit the
standalone ancestor, and begin implementation.

**Test results**: Pending contract lint and review.

## Watch List

- **Dirty worktree**: Unrelated active contract-ratification and PATH-CE files must remain untouched.
- **Scope containment**: REM-01 may add only the ratified authorization gates;
  it cannot alter Omni payload parsing, authorized response shapes, queue/RQ
  execution, outputs, overlays, report content/formatting, deletion semantics,
  model parameters, or non-Omni Project behavior.

## Communication Log

### 2026-07-20 21:08 UTC: Operator behavior decision

**Participants**: User/operator and Codex
**Question/Topic**: Expected visibility and independence of Omni Scenarios and Omni Contrasts.
**Outcome**: Superseded at 21:23 UTC by visible-to-all disabled discoverability.

### 2026-07-20 21:23 UTC: Scope expansion and final menu UX

**Participants**: User/operator and Codex
**Question/Topic**: Governance expansion and unauthorized menu presentation.
**Outcome**: Complete REM-01 through a GOV-00A bounded remediation path. Show
Omni Contrasts to all users and place `Not Authorized` below the disabled
checkbox label for unauthorized callers.
