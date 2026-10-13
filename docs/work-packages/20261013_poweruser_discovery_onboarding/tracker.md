# PUUX-01 tracker

Status: scaffold complete; M0 contract checkpoint and all implementation remain pending.
Started: 2026-10-13 17:42 UTC. Base: `a8de37a0db1e678e76eefb36a991514036fb9a9c`, branch `master`.

## Task board

- [x] Static review and Runs-page placement decision captured.
- [x] Source paths, role states, report-header discrepancy and acceptance plan documented.
- [x] Package, active ExecPlan and pending review artifacts created.
- [ ] M0 current contract amendments, independent contract reviews and standalone ancestor commit.
- [ ] M1 discovery notice and onboarding completion.
- [ ] M2 internal-access presentation, panel orientation and help updates.
- [ ] M3 regression/browser validation and final independent reviews.
- [ ] Final handoff with deployment status and residual limitations.

## Decisions

2026-10-13 17:42 UTC — Operator selected Runs as the discovery location, visible to non-PowerUsers. Interpret the exclusion as existing panel eligibility (PowerUser/Admin/Root), so administrators are not prompted to acquire access they have. Dev alone is not panel eligibility. Keep the panel restricted; discoverability uses explanation and Profile links instead of exposing gated controls.

2026-10-13 17:42 UTC — Use fixed server-generated completion destinations rather than introducing return URL handling. Keep internal acknowledgment reachable but secondary for users with no memberships. Preserve all permission and acceptance semantics.

## Discoveries and risks

Main run header and panel template both guard PowerUser/Admin/Root. Shared report header renders the button unconditionally while including the guarded panel, creating a potential dead trigger for ordinary viewers. Correct the trigger only; do not expand access. Profile's shared JavaScript also serves membership administration, so onboarding changes must not regress that branch.

## Validation and handoff

This is a documentation scaffold, not implementation or reviewed conformance. Validate Markdown and links now; runtime tests belong to M1–M3. Next executor starts at M0 in the active plan. Record contract-review and final-review identities/revisions independently; pending artifact stubs are not sign-offs. Update this tracker and the active plan at every milestone.

## PUUX-01A amendment

2026-10-13 UTC — Operator requests GL Dashboard in More for regular users. Existing route already uses project authorization, with no PowerUser gate. Execute this bounded link move after its own reviewed checkpoint; broad onboarding stays scaffolded. Review and implementation pending.

PUUX-01A checkpoint `5528224f6` precedes the three-template anchor change. Existing template/dashboard route suite: 229 passed, 6 warnings. Direct Jinja readback: 20 role/page/parent-child cases pass with tab preferences intact; panel duplicate absent. Dashboard route and authorization unchanged. Broader M0–M3 remain pending; no production deployment.
