# Contract Checkpoint Correctness Review

Reviewer: independent `reviewer` agent `/root/checkpoint_correctness`.
Review date: 2026-09-07 UTC; initial review and amendment recheck completed before implementation.
Starting implementation revision: `a64c39f8523ba7efab0e13c4973026700f1d780d`.
Scope: read-only review of proposed contracts, current creation/authentication code, interfaces, and test strategy. This artifact is the reviewer's only edit.

## Findings and Disposition

| ID | Severity | Finding and evidence | Disposition |
| --- | --- | --- | --- |
| CK-C01 | Medium | The initial policy converted a session token carrying `user_id` into a user identity for global project creation. `docs/dev-notes/auth-token.spec.md:78-82` limits session authority to an existing run; `session_routes.py:1077-1085` includes account identity without removing that run scope. The conversion could let a holder of a deliberately shared run token create projects owned by its account. | Resolved in the reviewed amendment. Restricted mode rejects every session token, including those carrying a current active `user_id`, and requires a user token or authenticated cookie. Default-mode behavior remains unchanged as required by the operator. |
| CK-C02 | Medium | `docs/schemas/rq-engine-agent-api-contract.md:558` unconditionally described CAPTCHA creation and was missing from the contract matrix. Its `/api/create/` alias is implemented by `wepppy/microservices/rq_engine/__init__.py:158-159` and also needs policy/test coverage. | Resolved. The agent API contract links the conditional policy, the matrix includes that contract, and the policy plus decision record explicitly cover the alias. |
| CK-C03 | Low | The initial policy explicitly assigned `403 anonymous_creation_disabled` to missing/invalid cookie identity, but did not state the exact error envelope for a cryptographically valid session or unknown-class token denied by the new gate. | Resolved in the final recheck. Those classes use the same policy denial envelope; existing invalid-signature, scope, expiry, and revocation errors remain unchanged. |

## Correctness Assessment

The amended contract matches the operator's anonymous-only opt-in restriction and preserves the absent/true default. Explicit empty and malformed environment values fail closed rather than silently restoring anonymous access. The requirement to preserve empty Compose values matters because unset-or-empty interpolation would defeat that parser rule.

Restricted browser authentication resolves the cookie even when a stale CAPTCHA field is present. Explicit credentials retain precedence, and existing expired `rq_token` cookie recovery remains available. Current account resolution in `wepppy/weppcloud/user_preferences.py:262-295` rejects missing/inactive users and conflicting email claims before allocation. Keeping that boundary avoids accepting claims without a current account or losing ownership on creation. Service/MCP behavior is intentionally preserved; no new token grant or issuance change is required.

The interfaces policy omits creation controls and CAPTCHA assets in server-rendered HTML while preserving role-based visibility and information. Fork, builder, restore, batch, test routes, and location-page controls are explicitly excluded; documentation must retain the warning that this setting does not disable every anonymous allocation path. This is consistent with the requested endpoint/page scope.

## Required Implementation Evidence and Residual Risk

- Exercise both `/create/` and `/api/create/`, JSON and form transport, unset/true/false settings, and empty/malformed configuration.
- Assert restricted CAPTCHA requests never verify/consume CAPTCHA, reserve idempotency state, allocate files, or register ownership. Exercise both preset-writer modes.
- Cover valid cookie plus stale CAPTCHA; valid user token; service/MCP; expired `rq_token` recovery; invalid explicit credentials with valid cookie/CAPTCHA; session tokens with and without `user_id`; unknown token class; inactive/deleted/conflicting account; and cross-origin/missing-origin cookie rejection.
- Include direct unmocked authorization/account-resolution and creation-boundary evidence. Existing `test_rq_engine_project_routes.py` fixtures replace allocation, NoDb, and README functions; passing those alone cannot establish real ownership/filesystem safety.
- Render the actual interfaces template for anonymous/authenticated states and regional/legacy role variants, then exercise absent-control JavaScript in a browser.
- Verify both real Compose service environments receive the same value and capture default anonymous success, restricted anonymous denial without artifacts, and restricted authenticated creation with normal ownership.

No checkpoint finding remains open after amendment recheck. Recommend accepting the contract checkpoint. Implementation conformance, test results, and production-equivalent workflow evidence remain pending; this review is not final implementation or deployment approval. The default mode intentionally retains historical session-token behavior under the user's compatibility requirement.
