# OAuth verification-failure contract checkpoint proposal

**Status**: Proposed; independent review and owner ratification pending.
No OAuth route edit is authorized by this proposal alone.

## Boundary and evidence

Starting checkpoint: `d4b175436`. The first Authlib upgrade candidate moves
OpenID verification to joserfc. A confined actual-library trial accepts a valid
signed token and rejects 15 invalid cases; each rejection is outside the current
callback exception tuple. A direct Flask callback probe confirms an invalid
nonce escapes the callback through `LoggedBlueprint` instead of returning the
existing login-failure response.

Applicable current authorities are `docs/schemas/weppcloud-session-contract.md`
(session identity, remember behavior, authentication logging) and
`docs/schemas/weppcloud-csrf-contract.md` (browser/OAuth route classification).
Neither currently specifies the callback response to failed OpenID verification.
Existing implementation and tests demonstrate handling of other OAuth failures,
but do not independently create normative authority under
`docs/standards/contract-first-change-standard.md`.

The user authorized execution of the dependency-security plan and approved its
M0 policy. That covers compatible remediation and preservation of authentication
behavior; this checkpoint makes the previously undocumented error outcome
concrete before editing the route. No new provider, login mechanism, scope,
cookie default, token lifetime or acceptance rule is proposed.

## Proposed normative text

Add an "OAuth callback verification failures" subsection to the session
contract:

> When the configured OAuth/OpenID client rejects a callback token's signature,
> required claims, issuer, audience, nonce or time validity, the callback MUST
> stop before fetching profile data, creating/linking an account or establishing
> authentication. It MUST return HTTP 302 to the configured
> `SECURITY_LOGIN_ERROR_VIEW` endpoint (default `security_ui.login`) and flash
> `Login failed while contacting the identity provider.` with category `error`.
> It MUST NOT expose token, header or claim values in logs or the
> response. Valid OAuth login and existing session/remember-cookie behavior MUST
> remain unchanged. The callback consumes the existing PKCE verifier before
> token exchange and retains Authlib's state validation and state consumption;
> verification failure MUST NOT restore consumed state or permit replay.

Cross-link a bounded OAuth callback classification from both the session
contract and the CSRF contract's matrix/Flask Route Requirements:

> `GET /oauth/<provider>/callback` and the existing
> `GET /<provider>-auth-callback` alias are identity-provider return boundaries.
> They MAY receive a cross-site top-level return without a same-origin header
> or Flask CSRF token. Authorization MUST instead require the existing
> session-bound OAuth state and PKCE verification, and OpenID nonce/signature/
> claim checks when that protocol is configured. Missing, mismatched or consumed
> state MUST NOT establish authentication. This exception does not apply to
> provider disconnect, token minting, ordinary session mutations, or another
> endpoint.

This resolves the existing conflict between the CSRF matrix's safe-GET rule and
the general same-origin requirement for cookie-backed session mutations. It
documents the existing cross-site OAuth return mechanism, not a new generic
same-origin bypass. The owner must ratify this bounded clarification alongside
the error outcome before implementation.

The implementation delta is a narrow catch for joserfc's documented `JoseError`
at the existing `authorize_access_token` boundary. Do not add `except Exception`,
retry invalid verification, accept a partial token, or change success-path
account/linking decisions. Handle `JoseError` separately from the existing
exception-text logging branch: log only a static message, configured provider,
and exception class/category, with no `str(exc)`, `repr(exc)`, `exc_info` or
token/header/claim values, regardless of today's sample error messages.

## State and regression matrix

| State | Required observation |
| --- | --- |
| Provider disabled/absent | Existing unavailable-provider behavior unchanged |
| Callback has no PKCE state | Existing expired-session redirect; no client exchange |
| OAuth state absent, mismatched or replayed with PKCE present | Real Authlib rejects; no profile/account/login side effect |
| Provider reports cancellation | Existing cancellation redirect; no token exchange |
| Valid token and populated expected state | Real verification succeeds; existing login/linking suite remains green |
| Valid token with optional OpenID claims absent | Login remains possible; optional claims do not become required |
| Existing-account login and supported linking state | Existing account selection/link behavior and remember-cookie outcome unchanged |
| Anonymous/new-account valid login | Actual callback reaches existing account creation/login after real signed-token verification |
| Preexisting authenticated identity on verification rejection | Existing authenticated identity/authentication state remains unchanged; flow state is consumed and the error flash may update the session; no account/link/login side effect |
| Optional next destination absent, empty or populated | Existing success destination selection and failure redirect remain unchanged |
| Remember/session state absent, empty or populated | Required protocol state still controls admission; existing valid login/session/remember behavior remains unchanged |
| Missing/empty required claim | Generic login-failure redirect; no profile/account/login side effect |
| Wrong issuer/audience/nonce/signature | Same failure contract; validation remains enabled |
| Expired, boolean or non-finite time claim | Same failure contract; no acceptance workaround |
| Malformed serialized token | Same failure contract; no raw token in diagnostics |
| Supported providers without OpenID | Valid OAuth login and existing OAuth/transport exception handling preserved |
| Legacy callback alias | Same valid and rejected outcomes as the primary callback |

Use real Authlib/joserfc signing and verification for the changed boundary,
with fixture keys and offline provider metadata. Exercise the actual Flask
callback with both a valid signed token and those verification failures; the
library-only success probe is not sufficient callback conformance evidence.
For rejection cases, assert redirect, generic message,
and absence of profile/database/login calls. Existing OAuth, session, remember,
CSRF and authentication logging suites remain regression gates. The final
candidate still requires the exact full Python and npm commands.

## Compatibility, security and sequencing

This preserves the existing user-facing failure pattern for an additional
expected authentication rejection. Security impact is high because it touches
the authentication boundary, although it must not expand admission. Authentication
diagnostics require value-free logging. Some joserfc errors interpolate attacker
header fields, so their text must never reach the existing exception-text log.

After two independent contract reviews and explicit owner ratification, amend
the canonical contract and commit this checkpoint plus review disposition as a
standalone ancestor. Only then implement the route/test change and Authlib batch.
Crypto/TLS-only upgrades can be evaluated independently while this is pending.
