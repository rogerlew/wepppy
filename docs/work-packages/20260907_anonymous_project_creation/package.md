# Opt-in Login Requirement for Project Creation

**Status**: Closed (2026-09-07)
**Timezone**: UTC

## Overview

Allow operators to disable anonymous project creation while preserving the current default. The rq-engine API must enforce the policy, and the public interfaces page must reflect it without offering unusable creation controls.

## Behavior and Decision Provenance

The user requested this package on 2026-09-07 after asking whether project creation could require login. Codex interprets “disable project creation through /rq-engine/create/” as disabling **anonymous** creation, preserving logged-in creation and existing authorized API clients. This is a recorded scope assumption, not a global creation shutdown.

Environment variable: `WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION`, default `true`. Setting it to `false` opts into the restriction. Use the same setting and boolean interpretation in Flask and rq-engine. Accepted values and invalid-value behavior are ratified in `docs/schemas/project-creation-policy.md`; empty or malformed explicit settings fail configuration.

When the flag is false, anonymous requests to `POST /rq-engine/create/` receive a canonical `403` error with code `anonymous_creation_disabled` and message `Sign in to create a project.` A valid CAPTCHA cannot override the restriction. Denial occurs before CAPTCHA verification, run allocation, filesystem writes, ownership records, or job submission. Authenticated requests retain existing authorization, scope, configuration-role, session, and CSRF checks.

For anonymous visitors with the flag false, `/interfaces/` remains readable but omits creation forms, Start buttons, associated context-menu creation actions, CAPTCHA prompts, and creation-only CAPTCHA assets. Render a concise sign-in link explaining how to create a project. Logged-in visitors retain their authorized Start actions without CAPTCHA. With the flag absent or true, preserve current behavior. The actual route is plural `/interfaces/`; do not introduce a singular alias solely from the request wording.

Rationale: API enforcement prevents direct-request bypass; server-side omission avoids misleading or script-reenabled controls. A global shutdown and CSS-only hiding were rejected because they do not meet the login requirement.

## Scope

- Shared policy semantics, Flask configuration, rq-engine enforcement, and interface rendering.
- Development and production Compose propagation to both web and API services; audit other Compose variants for applicability.
- Docker operator documentation, affected user/developer docs, current API/UI contracts, focused regression tests, and real workflow evidence.
- Inventory fork, archive restore, builder, batch, test-only creation, and alternate legacy routes. Record each as already authenticated, covered, or explicitly excluded before claiming the setting requires login for all project creation.

Global anonymous browsing, login/registration CAPTCHA, run/report CAPTCHA, existing-run authorization, model parameters, data schemas, queue topology, and blanket shutdown of authenticated creation are out of scope. Fork policy changes require an explicit scope decision; do not silently extend this setting to fork.

## Stakeholders and Review Gates

Operators configure the policy; anonymous and authenticated users experience it; Flask/rq-engine maintainers own implementation. **Security impact: high**, because public creation authorization and cross-service configuration change. A dedicated security review artifact and an independent correctness/UX review are required before closure, using the templates under `docs/prompt_templates/`. No medium/high findings may remain open. Scaffold creation does not constitute either review.

Follow `docs/standards/contract-first-change-standard.md`: prepare current canonical contract amendments, a starting revision and valid-state matrix, two independent read-only checkpoint reviews and disposition, and the required standalone checkpoint ancestor before implementation. The subsequent execute instruction authorized the required local commits; checkpoint ancestor is `fb67f32fc`.

**Parameterization change present: no. ADR required: no.** This is access policy with an unchanged default, not model parameterization.

## Success Criteria

- [x] Unset/true preserves anonymous CAPTCHA creation and existing authenticated behavior.
- [x] False rejects anonymous direct POSTs, including valid CAPTCHA, without creation side effects.
- [x] False permits valid authenticated browser and API creation under existing permissions.
- [x] Restricted anonymous interfaces HTML omits all creation controls and CAPTCHA assets; sign-in and informational content remain usable.
- [x] Both service containers receive the same explicit value; operator enable/disable instructions and rollback are verified.
- [x] Canonical contracts, Docker README/defaults documentation, and affected user/developer guides agree.
- [x] Focused and required broad gates, real workflow evidence, and independent reviews are complete.

## Deliverables and References

- [Implementation plan](prompts/completed/anonymous_project_creation_execplan.md)
- [Tracker](tracker.md)
- [Change inventory](artifacts/change_inventory.md)
- Current authority to examine: `docs/schemas/rq-response-contract.md`, `docs/schemas/weppcloud-csrf-contract.md`, `docs/ui-docs/controller-contract.md`, and feature-registry specification where menu visibility is affected.
- Related history: `docs/work-packages/20260729_pure_ui_public_creation_cap_contract/`; do not amend closed history.

## Closure

Closed 2026-09-07 21:27 UTC. Implemented in `935d96220` with the OpenAPI metadata fix in `43be30d31`, after reviewed checkpoint `fb67f32fc`. Focused tests passed (296); the full suite passed (7,721 passed, 72 skipped); frontend lint and 835 tests passed. Independent correctness/UX and security reviews passed with no unresolved findings.

Real HTTP/Chromium checks verified both modes, including 16 unchanged directory/database snapshots for denials and successful authenticated/service/MCP creation. All ten disposable runs were cleaned up, and both development services were restored to true. Production was not deployed. See [validation evidence](artifacts/20260907_validation.md).

Durable behavior and rationale are promoted in `docs/schemas/project-creation-policy.md`, especially Configuration, API Authorization, Interfaces, and Compatibility and Rationale. Docker activation/rollback and scope exclusions are documented in `docker/README.md#anonymous-project-creation`.

Optional future scope: unify fork/builder policy or hide location-page launch controls on restricted deployments. This package does not change those surfaces. The implementation outcome is complete within its named endpoint/page scope.
