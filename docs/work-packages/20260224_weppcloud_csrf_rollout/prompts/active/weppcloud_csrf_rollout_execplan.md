# WEPPcloud CSRF Rollout While Preserving rq-engine Third-Party API Access

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package lands, browser cookie-authenticated mutation routes in WEPPcloud Flask are protected by CSRF checks by default. At the same time, agent and third-party API consumers continue to use rq-engine/browse/files bearer-token endpoints exactly as they do today, without any new CSRF-token coupling.

The observable proof is:

1. Flask mutation endpoints reject missing/invalid CSRF token submissions.
2. The same endpoints accept valid CSRF-protected submissions.
3. rq-engine bearer-token requests still succeed without CSRF headers.

## Progress

- [x] (2026-02-24 00:00Z) Created package scaffold (`package.md`, `tracker.md`, `prompts/active/weppcloud_csrf_rollout_execplan.md`).
- [x] (2026-02-24 00:10Z) Registered package as in-progress in `PROJECT_TRACKER.md`.
- [x] (2026-02-24) Milestone 1 complete: route inventory + exemption register published.
- [x] (2026-02-24) Milestone 2 complete: global CSRF middleware/configuration + template token source implemented.
- [x] (2026-02-24) Milestone 3 complete: boundary route exemptions/hardening implemented and tested.
- [x] (2026-02-24) Milestone 4 complete: targeted validations executed and contract/docs synchronized.
- [x] (2026-02-24) Milestone 5 complete: correctness review findings dispositioned in `artifacts/reviewer_findings.md`.
- [x] (2026-02-24) Milestone 6 complete: code quality review findings dispositioned in `artifacts/code_quality_review.md`.
- [x] (2026-02-24) Milestone 7 complete: final artifacts + tracker synchronization completed.
- [x] (2026-02-24) Post-closeout follow-ups complete: CSRF bootstrap extracted to static JS with Jest coverage and broad-exception changed-file enforcement restored to PASS.
- [x] (2026-02-24) Post-closeout hardening complete: rq-engine forwarded-origin alias handling made opt-in and bearer-path compatibility regression tests expanded.
- [x] (2026-02-24) Post-closeout regression fix complete: `controlBase` polling now upgrades to bearer-auth polling after 401/403 and surfaces `error.detail` inline in job status.
- [x] (2026-02-24) Post-closeout compatibility fix complete: cookie-path same-origin gates now accept browser fetch metadata (`Sec-Fetch-Site: same-origin`) when `Origin`/`Referer` are unavailable.

## Surprises & Discoveries

- Observation: WEPPcloud currently exposes `csrf_token()` in template context but does not globally initialize Flask-WTF `CSRFProtect`.
  Evidence: `wepppy/weppcloud/_context_processors.py` defines `csrf_token_processor`; `wepppy/weppcloud/app.py` has no `CSRFProtect` initialization.
- Observation: Core auth bridge endpoints already enforce same-origin checks independent of CSRF middleware.
  Evidence: `wepppy/weppcloud/routes/weppcloud_site.py` uses `_is_same_origin_post()` for `/api/auth/rq-engine-token`, `/api/auth/session-heartbeat`, and `/api/auth/reset-browser-state`.
- Observation: `rq-engine` session-token issuance supports cookie fallback and bearer flow, but no explicit same-origin gate currently exists in `session_routes.py`.
  Evidence: `wepppy/microservices/rq_engine/session_routes.py` endpoint `/api/runs/{runid}/{config}/session-token` has no origin/referer validation.
- Observation: importing `wepppy.weppcloud.app` after registering `bootstrap_bp` in a test-local app can trigger Flask blueprint setup assertions from run-context preprocessor registration.
  Evidence: bootstrap route test runs raised `AssertionError: The setup method 'url_value_preprocessor' can no longer be called on the blueprint 'bootstrap'`.
- Observation: broad-exception allowlist entries were present for affected route/boundary files, but line-position drift in a dirty branch caused changed-file enforcement to report net-new broad catches.
  Evidence: enforcement output showed +50 deltas that mapped to pre-existing allowlist IDs with stale line numbers; updating allowlist line positions returned enforcement to PASS.
- Observation: run-page job polling still used unauthenticated `/rq-engine/api/jobstatus|jobinfo` reads, so deployments with `RQ_ENGINE_POLL_AUTH_MODE=required` surfaced 401 refresh errors even though tokenized polling helpers already exist.
  Evidence: `wepppy/weppcloud/controllers_js/control_base.js` polled via `http.getJson(...)` only; production logs showed `Authentication required` during polling flows.
- Observation: some browser/proxy paths can omit or normalize `Origin`/`Referer` on same-origin `fetch` POSTs, causing false-negative same-origin checks on auth/session bridge endpoints.
  Evidence: production polling still failed after controlBase auth retry, with Flask fallback bridge logging `Authentication required`; adding `Sec-Fetch-Site` handling resolved targeted regression tests.

## Decision Log

- Decision: Scope CSRF enforcement to WEPPcloud cookie-auth mutation routes and keep bearer-token API routes CSRF-agnostic.
  Rationale: CSRF risk is browser-cookie driven; forcing CSRF headers on non-browser bearer APIs would be unnecessary breakage for third-party and agent clients.
  Date/Author: 2026-02-24 / Codex
- Decision: Use global CSRF middleware with explicit, documented exemptions.
  Rationale: A default-protect posture is safer than piecemeal per-route decorators for a large route surface.
  Date/Author: 2026-02-24 / Codex
- Decision: Require both correctness review and code quality review as explicit completion gates.
  Rationale: Security changes must be regression-safe and maintainable; both risk and maintainability need independent checks.
  Date/Author: 2026-02-24 / Codex
- Decision: apply CSRF propagation at `base_pure.htm` via template token meta + same-origin form/fetch token attachment.
  Rationale: Many legacy inline fetch/form mutation paths exist; centralized propagation avoids broad piecemeal route/template rewrites while preserving default-protect posture.
  Date/Author: 2026-02-24 / Codex
- Decision: enforce same-origin only on rq-engine cookie-path session-token issuance; keep bearer path unchanged.
  Rationale: Cookie path is CSRF-relevant; bearer-token path must stay third-party/agent compatible.
  Date/Author: 2026-02-24 / Codex
- Decision: synchronize existing broad-exception allowlist IDs to current line positions rather than introducing new suppressions or behavioral code churn.
  Rationale: Existing boundaries were intentional and already allowlisted by ID; refreshing line coordinates restores deterministic enforcement without changing runtime behavior.
  Date/Author: 2026-02-24 / Codex
- Decision: keep polling backward-compatible by attempting unauthenticated job polling first, then upgrading to `requestWithSessionToken` only when 401/403 indicates auth-required mode.
  Rationale: avoids unnecessary token bridge calls in open/token-optional deployments while still fixing authenticated polling in required mode.
  Date/Author: 2026-02-24 / Codex
- Decision: treat `Sec-Fetch-Site: same-origin` as an accepted same-origin signal for cookie-auth POST boundaries in rq-engine session-token issuance and WEPPcloud auth bridge routes.
  Rationale: this preserves CSRF posture (`cross-site` still denied) while reducing false blocks when `Origin`/`Referer` are absent through legitimate browser/proxy flows.
  Date/Author: 2026-02-24 / Codex

## Outcomes & Retrospective

Delivered behavior:

- Global Flask CSRF middleware enabled in WEPPcloud (`CSRFProtect`).
- CSRF config toggles added: `WTF_CSRF_ENABLED`, optional `WTF_CSRF_TIME_LIMIT[_SECONDS]`.
- `base_pure.htm` now exposes CSRF meta token and loads `static/js/csrf_bootstrap.js` for same-origin form/fetch CSRF propagation.
- OAuth disconnect route now relies on global CSRF middleware; disconnect UX for CSRF failures preserved via app-level `CSRFError` handling.
- Bootstrap forward-auth verify endpoint explicitly CSRF-exempt (`register_csrf_exemptions`).
- rq-engine session-token cookie-auth path now enforces same-origin (`Origin`/`Referer`), while bearer path remains CSRF-agnostic.
- rq-engine forwarded-origin alias checks are now default-deny and require explicit opt-in (`RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true`).
- Added CSRF regression tests (`tests/weppcloud/routes/test_csrf_rollout.py`) and rq-engine same-origin tests (`tests/microservices/test_rq_engine_session_routes.py` updates).
- Added dedicated bootstrap JS coverage (`wepppy/weppcloud/controllers_js/__tests__/csrf_bootstrap.test.js`).
- `controlBase` now renders `error.detail` inline for polling failures and upgrades job polling to bearer-auth reads when the polling surface requires auth.
- Added fetch-metadata compatibility handling (`Sec-Fetch-Site`) for same-origin gating in `session_routes.py` and `weppcloud_site.py`, plus route/microservice regression tests.

Residual risks:

1. If forwarded-origin alias trust is explicitly enabled (`RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true`), proxy header sanitization remains required.

Follow-ups:

1. None required for package scope; residual forwarded-header trust assumptions remain deployment-side.

## Context and Orientation

This repository has two relevant auth planes:

1. WEPPcloud Flask routes (`wepppy/weppcloud/**`) that often rely on browser session cookies.
2. Microservice APIs (`rq_engine`, `browse`, `query_engine`) that primarily use `Authorization: Bearer` JWT.

CSRF (Cross-Site Request Forgery) is relevant where browsers auto-send cookies on mutation requests. It is not the same threat model as bearer-token APIs where headers are explicitly set by clients.

Current state relevant to this package:

- Template helper exists for CSRF token generation:
  - `wepppy/weppcloud/_context_processors.py` (`csrf_token_processor`)
- Base page template now exposes a shared CSRF meta token and static bootstrap loader:
  - `wepppy/weppcloud/templates/base_pure.htm`
- Controller JS already knows how to discover/send CSRF token when available:
  - `wepppy/weppcloud/controllers_js/http.js`
  - `wepppy/weppcloud/controllers_js/forms.js`
- OAuth disconnect now relies on global CSRF middleware and app-level CSRF error handling:
  - `wepppy/weppcloud/routes/_security/oauth.py`
- Existing bridge endpoints enforce same-origin checks:
  - `wepppy/weppcloud/routes/weppcloud_site.py`
- rq-engine session-token route supports cookie fallback and bearer tokens:
  - `wepppy/microservices/rq_engine/session_routes.py`

Normative contract and docs that must remain aligned:

- `docs/schemas/weppcloud-csrf-contract.md`
- `docs/schemas/weppcloud-session-contract.md`
- `docs/dev-notes/auth-token.spec.md`
- `docs/dev-notes/rq-engine-agent-api.md`

## Plan of Work

Milestone 1 establishes the implementation baseline and classification artifacts. Inventory all WEPPcloud mutation routes and classify each as:

- cookie-auth browser route (must enforce CSRF),
- non-browser boundary route (candidate `@csrf.exempt`, with rationale),
- safe method/no CSRF needed.

Publish this in `artifacts/route_classification.md` and `artifacts/csrf_exemptions_register.md` before code edits.

Milestone 2 wires global CSRF protection in Flask and exposes token sources for browser JS. Add `CSRFProtect` initialization in WEPPcloud app startup, add explicit config toggles in configuration (`WTF_CSRF_ENABLED`, optional CSRF time limit), and add `<meta name="csrf-token" content="{{ csrf_token() }}">` to base templates used by controller-driven pages.

Milestone 3 aligns boundary endpoints and exemptions. Keep existing same-origin guards on bridge endpoints and apply explicit exemptions only where cross-origin/non-browser semantics are intentional (for example `bootstrap` forward-auth verify route if required by auth proxy behavior). Remove ad hoc per-route CSRF checks that become redundant once global CSRF handles them (for example OAuth disconnect manual validation), but preserve user-facing error behavior.

Milestone 4 adds or updates tests for CSRF failure/success behavior and bearer compatibility. Include both WEPPcloud route tests and rq-engine tests proving third-party bearer paths remain unaffected.

Milestone 5 executes a correctness review focused on behavioral regressions, missing security coverage, and contract mismatches. Record findings and disposition in `artifacts/reviewer_findings.md`.

Milestone 6 executes a code quality review focused on complexity/readability/maintainability. Record findings and disposition in `artifacts/code_quality_review.md`. Include code-quality telemetry command outputs.

Milestone 7 completes closeout synchronization: update package/tracker/ExecPlan sections, update `PROJECT_TRACKER.md` status, and publish `artifacts/final_validation_summary.md`.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Baseline inventory and route classification.

    rg -n "@.*route\\(.*methods=.*(POST|PUT|PATCH|DELETE)" wepppy/weppcloud/routes > docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/route_inventory_raw.txt

    # Curate route_classification.md and csrf_exemptions_register.md from inventory.

2. Implement global CSRF middleware and config defaults.

    Edit:
    - `wepppy/weppcloud/app.py` (initialize `CSRFProtect`)
    - `wepppy/weppcloud/configuration.py` (CSRF config toggles)
    - `wepppy/weppcloud/templates/base_pure.htm` (meta token source)
    - `wepppy/weppcloud/routes/_security/oauth.py` (remove redundant manual validation if global CSRF fully covers route)

3. Apply exemption and boundary updates from classification.

    Edit only routes with explicit rationale in exemption register, and annotate each exemption with a short comment referencing why it is boundary-safe.

4. Add/update tests for CSRF behavior and bearer compatibility.

    Candidate test files:
    - `tests/weppcloud/routes/test_rq_engine_token_api.py`
    - `tests/weppcloud/routes/test_bootstrap_bp.py`
    - `tests/weppcloud/routes/test_bootstrap_auth_integration.py`
    - `tests/weppcloud/routes/test_user_profile_token.py`
    - `tests/microservices/test_rq_engine_session_routes.py`
    - new focused CSRF regression tests as needed under `tests/weppcloud/routes/`

5. Execute validation gates.

    wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py

    wctl run-pytest tests/weppcloud/routes/test_bootstrap_bp.py tests/weppcloud/routes/test_bootstrap_auth_integration.py

    wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py

    wctl run-pytest tests/microservices/test_rq_engine_session_routes.py

    wctl run-npm test -- http

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

    python3 tools/code_quality_observability.py --base-ref origin/master

    wctl doc-lint --path docs/work-packages/20260224_weppcloud_csrf_rollout

6. Execute required review gates.

    Correctness review:
    - Run reviewer pass over changed files, focusing on security regressions and contract drift.
    - Record finding severity, disposition, and any required patch links in `artifacts/reviewer_findings.md`.

    Code quality review:
    - Run qa/code-quality review over changed files, focusing on complexity, readability, and long-term maintainability.
    - Record findings, accepted tradeoffs, and follow-up actions in `artifacts/code_quality_review.md`.

7. Closeout synchronization.

    Update:
    - `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective` in this ExecPlan.
    - `docs/work-packages/20260224_weppcloud_csrf_rollout/tracker.md`.
    - `docs/work-packages/20260224_weppcloud_csrf_rollout/package.md` closure notes if complete.
    - `PROJECT_TRACKER.md` when moving package status.

## Validation and Acceptance

The package is complete when all criteria below are true:

- WEPPcloud cookie-auth mutation routes are CSRF-protected by default.
- Browser mutation calls can obtain CSRF token from template-exposed token source and pass CSRF validation.
- Explicit exemptions are minimal, documented, and tested.
- No regressions for rq-engine third-party bearer clients (no CSRF header requirement introduced).
- Required tests, correctness review, and code quality review all pass with findings dispositioned.
- Contract docs and package artifacts are synchronized.

## Idempotence and Recovery

This plan is designed for repeatable execution:

- Route inventory generation is idempotent.
- CSRF configuration should be controlled by explicit config flags so rollback is possible without code reverts (for example temporary `WTF_CSRF_ENABLED=false` in controlled environments).
- If a route fails after CSRF enablement, first classify whether it is browser-cookie mutation or non-browser boundary; do not add exemptions before classification and test evidence.
- If review gates find regressions, fix findings and re-run only affected test slices before running full required gate set again.

## Artifacts and Notes

Required artifacts:

- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/route_classification.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/csrf_exemptions_register.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/final_validation_summary.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/reviewer_findings.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/code_quality_review.md`

Optional helper artifact:

- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/route_inventory_raw.txt`

## Interfaces and Dependencies

Required interfaces and components:

- Flask CSRF extension:
  - `flask_wtf.csrf.CSRFProtect`
  - accepted tokens via `X-CSRFToken`, `X-CSRF-Token`, or form `csrf_token`
- Template token exposure via `csrf_token()` helper
- JS CSRF propagation via:
  - `wepppy/weppcloud/controllers_js/http.js`
  - `wepppy/weppcloud/controllers_js/forms.js`
- rq-engine bearer auth contract:
  - `wepppy/microservices/rq_engine/auth.py`
  - `wepppy/microservices/rq_engine/session_routes.py`

No speculative fallback wrappers are allowed. Missing CSRF token failures must remain explicit and actionable.

Revision note (2026-02-24 00:10Z): Initial ExecPlan authored for end-to-end implementation, including mandatory correctness review and code quality review gates.
