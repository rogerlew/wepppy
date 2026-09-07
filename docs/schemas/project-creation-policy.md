# Project Creation Access Policy

## Status and Scope

Accepted intent for the anonymous creation work package; implementation conformance pending. This policy governs `POST /rq-engine/create/` (including `/rq-engine/api/create/`) and `/interfaces/` only. Fork, archive restore, builder, batch, and test-only creation retain their existing authorization contracts. This is not a site-wide prohibition on anonymous run allocation.

## Configuration

`WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION` defaults to true when absent. After trimming whitespace and case-folding, `1`, `true`, `yes`, `on` enable anonymous creation; `0`, `false`, `no`, `off` disable it. Empty and other explicit values are configuration errors, never a permissive default. Flask fails configuration loading with ValueError; rq-engine returns canonical HTTP 503 with code `creation_policy_configuration_error` before processing creation. Both consume the same parser. Compose must preserve an explicitly empty value for validation and supply true only for an unset variable. Changing the value requires applying configuration to both services.

## API Authorization

With true, preserve existing authentication precedence and CAPTCHA behavior. With false, explicit rq_token and Authorization credentials retain precedence, signature/scope/revocation validation, and existing errors. Expired rq_token may recover through the existing same-origin authenticated cookie path. Without explicit credentials, resolve the authenticated cookie even if cap_token is supplied. A missing/invalid cookie or origin denial yields canonical HTTP 403 with code `anonymous_creation_disabled` and message `Sign in to create a project.` Existing exceptional auth errors retain their errors; no permissive fallback is allowed.

A CAPTCHA alone cannot authorize creation with false. Deny anonymous requests before CAPTCHA verification, idempotency reservation, run directory allocation, metadata mutation, or jobs. Payload parsing and missing-config validation may precede authorization and retain existing 400 errors.

Validated user tokens and browser identities continue through existing active-user/ownership resolution. Validated service and mcp tokens with existing creation scopes retain their current behavior. Session tokens authorize existing-run access, not new top-level creation: reject all session tokens in restricted mode, even those carrying user_id. Clients must use a user token or authenticated browser cookie without explicit session-token credentials. Unknown token classes are denied. Valid-but-disallowed token classes use the same HTTP 403, `anonymous_creation_disabled`, `Sign in to create a project.` envelope; invalid credential validation errors retain precedence. Existing default-mode session-token behavior remains unchanged. Inactive/deleted/conflicting user identities retain existing run_ownership_failed errors and create no artifacts.

## Interfaces

For anonymous visitors with false, server-rendered `/interfaces/` omits creation forms/buttons, creation context-menu actions, CAPTCHA prompts, and creation-only CAPTCHA scripts. It remains readable and includes a sign-in link. Logged-in visitors retain role-authorized launch actions without CAPTCHA. True retains current UI behavior. Information and feature maturity visibility remain governed by the feature registry; this access policy is an additional launch gate, never a grant of role permission. Stale pages cannot bypass API enforcement.

## Compatibility and Rationale

Default true preserves existing deployments. False changes only the named creation surface; CAPTCHA for login, registration, fork, and run/report viewing is independent. Both UI and API gates are required because hiding controls alone cannot prevent direct HTTP creation. Preserving service/mcp access supports existing non-browser operators; rejecting run-scoped session tokens prevents a scope-bearing token from bypassing the human-account policy. No run schemas, model parameters, or queue dependencies change.

## Error and Safety Contracts

Errors follow [RQ response contract](rq-response-contract.md). Cookie authorization follows [CSRF contract](weppcloud-csrf-contract.md); the policy must not weaken origin, session, or CSRF checks. Creation permission is independent of existing run-access permissions.
