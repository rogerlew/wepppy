# Add an Opt-in Login Requirement for Project Creation

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective alongside the package tracker. Execution authorized on 2026-09-07; contract checkpoint in progress, implementation not yet started.

## Purpose / Big Picture

Operators can set `WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION=false` to require authenticated creation at `POST /rq-engine/create/`. The default is true, preserving anonymous CAPTCHA creation. Anonymous visitors can still read `/interfaces/`, but when restricted they see a sign-in explanation instead of creation forms, Start actions, or CAPTCHA. Authenticated users and currently authorized API callers retain creation under existing permissions.

## Progress

- [x] (2026-09-07 20:40 UTC) Inspect code and scaffold behavior, source inventory, and execution plan.
- [ ] Ratify current contracts and commit the required reviewed checkpoint before implementation.
- [ ] Implement shared policy semantics, API enforcement, and interfaces rendering.
- [ ] Wire Compose and update operator/user/developer documentation.
- [ ] Validate both modes, complete independent reviews, and close package.

## Surprises & Discoveries

The public page is `/interfaces/`, plural. `/create` already requires login, but its target rq-engine endpoint permits CAPTCHA-only creation. Within that endpoint a supplied CAPTCHA currently takes precedence over session-cookie fallback. Restricted-mode logic must not reject a valid logged-in user simply because a CAPTCHA field is present. The CAPTCHA guide still describes old `/create/<config>` routes. Evidence and exact source paths are in `artifacts/change_inventory.md` relative to this package.

## Decision Log

2026-09-07 20:40 UTC, Codex: interpret the user's request in the preceding login-requirement context as anonymous-only restriction. Preserve authenticated creation; do not implement an endpoint-wide kill switch. Choose a positive allow flag defaulting true so existing deployments remain unchanged. Server-side UI omission and API denial are both necessary because cached pages and direct HTTP clients can bypass page controls. Scope this delivery to scaffolding as requested.

## Outcomes & Retrospective

The scaffold records the intended behavior and remaining decisions. No runtime feature, deployment wiring, or security validation is complete. The current milestone establishes canonical contracts; this package cannot close on planning artifacts alone.

## Context and Orientation

Start in `/home/workdir/wepppy`. Read root and nearest AGENTS before edits, especially those under `wepppy/weppcloud`, `wepppy/microservices/rq_engine`, `tests`, and `docker`. Follow the docs-maintainer and applicable testing skills. Do not create or switch branches. Baseline revision is `a64c39f8523ba7efab0e13c4973026700f1d780d`; record the actual implementation baseline if it changes.

Flask serves the interfaces template via `interfaces()` in `wepppy/weppcloud/routes/weppcloud_site.py`. `wepppy/weppcloud/configuration.py` loads Flask settings. The separate rq-engine service handles creation in `wepppy/microservices/rq_engine/project_routes.py:create`; it supports signed tokens, browser sessions, and CAPTCHA. Both processes need the same environment policy. CAPTCHA proves a human interaction, not account authentication. The form template is `wepppy/weppcloud/templates/interfaces.htm`, including regional/legacy actions and inline context-menu code. Consult the package inventory for tests and documentation surfaces.

## Milestone 1 — Establish the Contract Checkpoint

Read `docs/standards/contract-first-change-standard.md`, `docs/schemas/rq-response-contract.md`, `docs/schemas/weppcloud-csrf-contract.md`, applicable UI contracts, and the feature-registry specification. Prepare a canonical project-creation policy contract under `docs/schemas/` if no existing current contract owns it, and amend/cross-link the affected authorities. Preserve this package's behavior and rationale in that contract. Resolve boolean accepted values and invalid-value handling using repository precedent; malformed explicit settings must never silently enable anonymous creation. Record whether invalid configuration fails startup or returns an explicit configuration failure consistently across services.

Specify default true, explicit false, API `403` / `anonymous_creation_disabled` / `Sign in to create a project.`, and anonymous-only rendering suppression. Preserve valid browser and authorized API caller behavior and existing origin, CSRF, scope, and role checks. Inventory other run-allocating routes and disposition each without silently extending scope to fork. Define request combinations separately from absent/empty/populated/legacy/hostile runtime states. Obtain the two independent read-only reviews and disposition required by the standard, and record base/contract revisions and timestamps. The standalone reviewed checkpoint must be an ancestor before production code edits; if commit authority is absent, prepare the concrete checkpoint and request that authority at that stage. This scaffold does not constitute checkpoint acceptance.

## Milestone 2 — Enforce and Render the Policy

Use existing environment parsing patterns, with a small shared helper only if needed to keep Flask and rq-engine semantics identical. No new dependencies are needed. Add the setting to Flask configuration and enforce it in rq-engine after determining valid identity but before CAPTCHA verification or creation side effects. An anonymous valid CAPTCHA must not authorize restricted creation. Maintain explicit invalid-token errors and expired-token session recovery; do not introduce broad permissive fallbacks. Preserve authenticated ownership assignment and authorized service callers.

Pass a server-derived availability value to the interfaces template. Omit all anonymous creation forms, variant/context-menu actions, prompts, and creation-only CAPTCHA assets when restricted; retain informational sections and a working sign-in link. Keep authenticated actions under existing role visibility. Ensure inline JavaScript handles absent forms without errors. Prefer page-local conditions over changing shared CAPTCHA macros used by other workflows. Extend existing API, configuration, create-index, and real template-render tests; prove the new denial test fails before enforcement and passes afterward.

## Milestone 3 — Wire Configuration and Documentation

Inspect `docker/AGENTS.md`, `scripts/deploy-production.sh`, and current Docker README before documenting activation or rollback. Add the flag with default true to both web/API environments in development and production Compose. Audit HPC and host overrides for applicable propagation; do not add the flag to unrelated workers without a consumer. Document it in `docker/defaults.env` and `docker/README.md`, including affected services, consistent values, activation, verification, and reversion. Do not edit local `.env` or secret files. Update CAPTCHA guide route descriptions, rq-engine API documentation, and getting-started guidance for restricted deployments. Leave `wepppy/weppcloud/routes/usersum/generated/docs_index.json` untouched.

## Milestone 4 — Verify and Review

Run focused tests, then required broad gates once focused coverage passes. Verify unmocked creation through the configured Compose web/API services under their real identities, mounts, and orchestration. Capture restricted anonymous rejection with a previously obtained valid CAPTCHA and no new run files/records, restricted authenticated success with normal ownership/artifacts, restricted interface HTML and browser behavior, and default-mode anonymous success. Use disposable runs and record their identifiers and cleanup disposition. Capture only the nonsecret policy value from both service environments. Do not claim rollout readiness without production-equivalent boundary evidence.

Create independent correctness/UX and security review artifacts using `docs/prompt_templates/correctness_review_template.md` and `docs/prompt_templates/security_review_template.md`. Close all medium/high findings and retain post-fix evidence. Update package, tracker, and project board, then archive this prompt with outcomes after implementation closure. Production deployment is a separate operator action unless authorized during execution.

## Concrete Steps and Validation

From `/home/workdir/wepppy`, run the following after implementation:

    wctl run-pytest tests/microservices/test_rq_engine_project_routes.py tests/weppcloud/test_configuration.py tests/weppcloud/routes/test_weppcloud_site_interfaces_route.py tests/weppcloud/routes/test_run_0_create_token.py
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260907_anonymous_project_creation
    wctl doc-lint --path docker/README.md

Expect focused/broad tests and blocking lint gates to pass; record actual counts, not predicted counts. Lint each additional amended contract/guide. Run stub gates only if API/stub surfaces change. Queue topology is excluded, so graph checks are required only if an explicitly authorized scope change touches wiring. Test API combinations and valid states described in the inventory, including authenticated session plus CAPTCHA and expired token recovery. A green mocked test suite cannot replace the real boundary evidence above.

## Idempotence and Recovery

Changing the flag must not migrate or rewrite existing runs. Reverting to true restores default anonymous creation once both services use that configuration. Follow the inspected canonical deployment entry point for service recreation; avoid inventing parallel deployment commands. A partially updated deployment is not accepted: verify both services agree before signoff. Keep real-workflow artifacts free of tokens, cookies, and secrets.

## Interfaces and Dependencies

Public configuration is `WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION`; default true. Proposed denial contract is a canonical error payload with HTTP 403 and code `anonymous_creation_disabled`. API and template must consume equivalent policy semantics. Existing auth utilities, Flask/Jinja, rq-engine request handling, and Compose are sufficient. No persistence-schema, scientific parameterization, or queue dependency changes are planned.

## Artifacts and Notes

Store checkpoint reviews/disposition, a valid-state matrix, focused/broad test results, sanitized Compose/browser workflow evidence, and final correctness/security reviews in this package's `artifacts/`. Keep evidence concise and identify any uncovered state or remaining boundary limitation.

Revision note: 2026-09-07 20:40 UTC — created the implementation scaffold and recorded anonymous-only scope, backward-compatible default, and additional review surfaces from source discovery.

Revision note: 2026-09-07 20:51 UTC — execution authorized; canonical policy now fixes strict boolean parsing, rejects all existing-run session tokens in restricted mode, and covers the API alias. Session-scope preservation supersedes the initial suggestion to resolve session user_id for creation.
