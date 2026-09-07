# Contract Checkpoint Security Review

## Findings

| ID | Severity | Evidence and exploit path | Required disposition | Status |
| --- | --- | --- | --- | --- |
| SEC-CP-01 | Low | The initial decision described builder creation as requiring JWT and current actor resolution. `builder_routes.py:247` calls `resolve_creation_actor`, but `user_preferences.py:265` returns `None` for session tokens, and `builder_routes.py:272` permits an ownerless allocation. An anonymous public-run session JWT can therefore remain usable on the explicitly excluded builder surface. | Clarify that builder is JWT-gated, not necessarily account-authenticated, and explicitly retain this excluded allocation path in operator-facing scope notes. No builder behavior change is requested. | Resolved at checkpoint: amended decision, Other Creation Paths; carry into implementation documentation |

No unresolved findings. The low finding was a scope-description correction; the canonical policy also states that this is not a site-wide prohibition on anonymous allocation.

## Metadata and Verdict

- Reviewer: independent security reviewer `/root/checkpoint_security`.
- Reviewed: 2026-09-07 20:50 UTC; final contract recheck 20:52 UTC, implementation baseline `a64c39f8523ba7efab0e13c4973026700f1d780d`.
- Inputs: `20260907_contract_decision.md`, canonical `docs/schemas/project-creation-policy.md`, amended RQ agent API, response and feature-registry links, current CSRF and token-class authorities, package plan, and source/test boundaries below.
- Security impact: **high**; the change governs public HTTP authorization, session claims, and cross-service configuration.
- Checkpoint design gate: **pass**. This is a read-only contract review, not final implementation or release sign-off. No production files were edited and no runtime tests were run by this reviewer. Review artifact documentation lint passed with zero warnings/errors; spelling preview was unchanged.

## Surface Checks

- **Anonymous session JWT bypass:** `session_routes.py:1032,1077-1085` issues public-run session tokens without `user_id`; `project_routes.py:156-183` and `auth.py:370-404` validate JWTs/scopes without proving account login. The final amendment denies every session-token credential in restricted mode, including tokens with a current account `user_id`, and denies unknown token classes. This closes the anonymous-token path without promoting existing-run credentials into new-project authority; `docs/dev-notes/auth-token.spec.md:78-82` explicitly limits session tokens to run-scoped access. Default mode preserves the existing implementation. Authenticated clients use a user token or cookie without explicit session-token credentials.
- **Identity validity and ownership:** `user_preferences.py:262-291` verifies a current active user and rejects conflicting email before creating an actor. Existing user-token and cookie identity resolution must still reach this check before allocation. Missing, boolean, malformed, fractional, zero, or negative account claims must deny; deletion/inactivation/database failure must never become anonymous success. Valid current account identities retain ownership. Service/mcp access is an explicit preserved non-browser exception, not a claim of human login.
- **Credentials, origins, and CAPTCHA:** Explicit rq_token/Bearer errors retain precedence. Expired rq_token recovery keeps `project_routes.py:189-203` and `session_routes.py:422-450` same-origin cookie validation. Restricted cookie resolution before CAPTCHA handles authenticated users with stale CAPTCHA fields. Anonymous denial before CAPTCHA verification prevents solved-token bypass and avoids spending the token. No origin/CSRF relaxation is authorized.
- **Configuration:** Shared parsing with absence-only true default and explicit empty/malformed failure prevents permissive configuration mistakes. The separate Flask startup failure and rq-engine canonical 503 are stated clearly. Compose must preserve an explicitly empty value; rendered environments must agree before operational sign-off.
- **UI and role permissions:** Server-side omission includes forms, ordinary and context-menu Start actions, and creation-only CAPTCHA assets. Existing feature-role visibility is an independent gate. Stale pages and alternate launch pages remain subject to API denial; hiding only `/interfaces/` is consistent with requested UI scope.
- **Scope exclusions:** Fork is an independent anonymous allocation surface (`fork_archive_routes.py:861-864`). Builder has the caveat in SEC-CP-01. Archive restoration retains existing run access. Test support keeps its deployment guard (`routes/test_bp.py:19-21,111-113`). These exclusions must remain visible in operator documentation and must not be presented as a complete site-wide login requirement.
- **Other boundaries:** No new queue edges, worker/subprocess behavior, dependencies, secrets, outbound integrations, path construction, NoDb schema, or scientific parameterization is proposed. Existing CAPTCHA egress is reduced in restricted mode. New denial/configuration errors must not include credentials or policy input dumps.

## Required Implementation Evidence

The checkpoint state matrix covers default/restricted modes, empty/invalid configuration, current/deleted/inactive identities, empty/stale credential state, legacy presets, and omitted UI DOM. Final review must verify the following concrete cases:

1. Signed anonymous session JWT denied via both rq_token and Bearer transports and both create path aliases, including a numeric-looking `sub` that matches a real account; no identity promotion.
2. Signed session JWT with a valid `user_id` remains denied even alongside a cookie/CAPTCHA. Valid user-token and cookie identities resolve a current active owner; malformed IDs and deleted/inactive accounts produce no allocation or idempotency reservation.
3. Cookie-only and cookie-plus-CAPTCHA requests preserve same-origin success and reject cross-origin/missing-evidence requests; revoked/invalid explicit credentials cannot fall through to CAPTCHA.
4. Unset/true anonymous CAPTCHA success, restricted valid-CAPTCHA denial before verification, scoped service/mcp success, and invalid configuration failure in both services.
5. Real template/browser omission, preserved authenticated role gates, and unmocked auth/creation evidence under the configured Compose identities and mounts. The existing mocked creation fixture in `tests/microservices/test_rq_engine_project_routes.py:64-105` alone cannot establish filesystem or identity safety.

## Residual Risk and Closure

The policy deliberately leaves fork, builder, and deployment-enabled test support outside its scope. JWT signing, revocation availability, trusted proxy configuration, current-user lookup, and existing run access remain inherited security boundaries. These are not newly accepted exceptions to those contracts. Final independent security review after correctness/QA must inspect actual implementation and evidence, verify checkpoint ancestry, and close all medium/high findings before package closure.
