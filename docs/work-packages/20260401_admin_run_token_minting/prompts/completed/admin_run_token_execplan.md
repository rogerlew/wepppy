# Admin Run-Scoped Token Minting in PowerUser Panel

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference standard: `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, Admin/Root users can mint a 24-hour run-scoped JWT directly from the PowerUser panel and copy it for sync/debug workflows. Non-admin users will not see the control and cannot call the endpoint. This enables credentialed run syncing and run-targeted agent/API debugging without relying on long-lived profile tokens.

## Progress

- [x] (2026-04-01 18:00Z) Created work package scaffold and active ExecPlan.
- [x] (2026-04-01 18:05Z) Verified existing profile token UI pattern and PowerUser panel action layout.
- [x] (2026-04-01 18:35Z) Implemented backend endpoint and route tests.
- [x] (2026-04-01 18:45Z) Implemented PowerUser admin-only UI and template tests.
- [x] (2026-04-01 19:25Z) Updated docs and ran QA/review gates.
- [x] (2026-04-01 19:30Z) Completed closeout artifacts and moved ExecPlan to `prompts/completed/`.

## Surprises & Discoveries

- Observation: Private `aria2c.spec` intentionally returns `401` without auth; sync failures are expected if worker requests are anonymous.
  Evidence: `tests/microservices/test_browse_auth_routes.py::test_aria2c_private_run_returns_401_without_redirect` and live curl verification.
- Observation: `mint_run_token` initially had a broad catch that could mask `authorize` access denials.
  Evidence: route structure review and explicit `Forbidden` regression test in `tests/weppcloud/routes/test_user_profile_token.py`.

## Decision Log

- Decision: Issue a `service`-class run token (not `user`) so token authorization is claim-based (`runs`) and portable for cross-server sync.
  Rationale: `user` tokens depend on ownership checks and are less portable between deployments.
  Date/Author: 2026-04-01 / Codex

- Decision: Keep a fixed TTL of 24 hours (`86400` seconds) per request.
  Rationale: User requirement; limits exposure while supporting operational sync windows.
  Date/Author: 2026-04-01 / Codex

## Outcomes & Retrospective

- Delivered:
  - Admin-only endpoint `POST /runs/<runid>/<config>/mint-run-token` issuing 24-hour run-scoped service tokens.
  - Admin-only PowerUser panel Mint Run Token card (mint, copy, status, expiry).
  - Token contract and usersum docs updates.
  - Review artifacts:
    - `docs/work-packages/20260401_admin_run_token_minting/artifacts/code_review_findings.md`
    - `docs/work-packages/20260401_admin_run_token_minting/artifacts/qa_review_findings.md`
- Resolved medium finding:
  - Preserved `HTTPException` in route auth flow and removed newly introduced broad catch in `mint_run_token`.
- Validation summary:
  - `wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` (`49 passed`)
  - `wctl run-pytest tests/weppcloud/routes --maxfail=1` (`432 passed`)
  - `wctl doc-lint --path docs/dev-notes/auth-token.spec.md --path wepppy/weppcloud/routes/usersum/weppcloud/getting-started.md --path docs/work-packages/20260401_admin_run_token_minting` (`5 files validated, 0 errors, 0 warnings`)
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (`PASS`)

## Context and Orientation

Relevant code paths:
- `wepppy/weppcloud/routes/user.py` currently mints 90-day profile user tokens.
- `wepppy/weppcloud/templates/user/profile.html` contains canonical mint/copy/status UI behavior for token issuance.
- `wepppy/weppcloud/templates/controls/poweruser_panel.htm` contains the PowerUser “Actions” column.
- `wepppy/weppcloud/utils/auth_tokens.py` defines token issuance (`issue_token`) and claims assembly.
- `tests/weppcloud/routes/test_user_profile_token.py` and `tests/weppcloud/routes/test_pure_controls_render.py` provide existing test patterns.
- `docs/dev-notes/auth-token.spec.md` is the normative JWT contract doc.

## Plan of Work

Implement a new admin-only run-scoped mint endpoint in Flask routes, returning canonical `success_factory`/`error_factory` payloads with `Cache-Control: no-store`. Token should be `token_class=service`, include `runs=[runid]`, include broad run-debug scopes/audiences, and set a fixed 24-hour TTL.

Extend PowerUser panel actions with an admin-only token card using existing profile token classes/styles (`wc-profile-token`, `wc-alert`, `wc-button-row`, `wc-field__input-row`) and the same interaction model: mint button, readonly token textarea, copy button, status alert, and expiry text.

Add tests for endpoint authorization/claims/TTL and template visibility contract. Update token contract docs and user-facing docs for the new admin run token behavior.

## Concrete Steps

From `/workdir/wepppy`:

1. Add endpoint constants and route implementation in `wepppy/weppcloud/routes/user.py`.
2. Add endpoint tests in `tests/weppcloud/routes/test_user_profile_token.py`.
3. Add admin-only token card + JS handlers in `wepppy/weppcloud/templates/controls/poweruser_panel.htm`.
4. Add/extend template assertions in `tests/weppcloud/routes/test_pure_controls_render.py`.
5. Update docs:
   - `docs/dev-notes/auth-token.spec.md`
   - `wepppy/weppcloud/routes/usersum/weppcloud/getting-started.md`
6. Run validation commands:
   - `wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
   - `wctl doc-lint --path docs/dev-notes/auth-token.spec.md --path wepppy/weppcloud/routes/usersum/weppcloud/getting-started.md --path docs/work-packages/20260401_admin_run_token_minting`

## Validation and Acceptance

Acceptance checks:
- Admin/Root caller to run token endpoint gets `200` with token payload including 24-hour expiry and run-scoped claims.
- Non-admin caller gets `403` with canonical error payload.
- PowerUser panel renders mint controls only when admin/root condition is true.
- UI JS supports mint + copy flows and status updates using profile-style alert behavior.
- Targeted route/template tests pass.

## Idempotence and Recovery

- Re-running endpoint mints a fresh token; no persisted mutable state is required.
- UI changes are additive and guarded by role checks.
- If JWT config is missing, endpoint fails with explicit `500` configuration error, matching existing token patterns.

## Artifacts and Notes

- Validation outputs and review findings are captured in:
  - `docs/work-packages/20260401_admin_run_token_minting/tracker.md`
  - `docs/work-packages/20260401_admin_run_token_minting/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_admin_run_token_minting/artifacts/qa_review_findings.md`

## Interfaces and Dependencies

Expected endpoint response payload content shape:

    {
      "token": "<jwt>",
      "token_class": "service",
      "audience": ["rq-engine", "query-engine"],
      "runs": ["<runid>"],
      "scopes": ["..."],
      "expires_at": <unix-seconds>,
      "issued_at": <unix-seconds>,
      "expires_in": 86400
    }

Token claims must include:
- `token_class=service`
- `runs=[runid]`
- `scope` covering run debugging + sync operations
- `aud` containing `rq-engine` and `query-engine`
- role/group context from current user for downstream role-gated checks.
