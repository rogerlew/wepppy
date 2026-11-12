# OAuth dependency compatibility checkpoint

Status: independently reviewed canonical checkpoint; no Authlib/joserfc
production code or requirements change in this checkpoint. Correctness and
security reviews approved the bounded contract before its standalone commit.

Canonical authority: `docs/schemas/weppcloud-session-contract.md`,
"OAuth Dependency Compatibility". This preserves the existing login failure
redirect and verified-profile/linking policy while supporting the independently
observed new verifier exception family. The prior actual Authlib 1.9.1/joserfc
1.8.0 trial rejected 15 invalid-token cases, but its errors escaped the callback's
current OAuthError/RequestException/TypeError/ValueError boundary. A broad catch
or weakened verification is not an acceptable repair.

Starting revision: `f86084dea91e6d7c2d55234022bd8b44f2c0eedb`.
Authority: Roger explicitly requested completion of F6 through M4 on 2026-11-12;
this bounded compatibility repair is within its applicable-authentication batch.
It does not authorize production rollout or new authentication policy.

Finite implementation surface after checkpoint:
`wepppy/weppcloud/routes/_security/oauth.py`, `docker/requirements-uv.txt`,
`tests/weppcloud/routes/test_security_oauth_callback.py`, and
`tests/weppcloud/routes/test_security_oauth_verifier.py`. Update the canonical session
contract, dependency evaluation registry and active F6 evidence in the same batch.

## Runtime state matrix

| State | Required outcome |
| --- | --- |
| Provider absent/disabled | Existing 404 behavior |
| Enabled provider with unavailable registered client | Existing 404 after the existing provider-error/cancellation handling |
| Configured OAuth-only provider with valid exchange/profile | Existing linking/login, remember=True, safe redirect |
| Configured OIDC provider with valid signed token and expected claims/nonce | Real verification and existing successful profile/link/login behavior |
| Missing local PKCE/session state | Existing "OAuth session expired. Please try again." warning and failure redirect |
| Malformed provider-client state or failed exchange | Existing provider-client rejection and established exchange failure redirect |
| Present OIDC token with bad signature, issuer, audience, nonce, claims or encoding | Specific JOSE rejection translated; no userinfo/link/login side effects |
| Provider cancellation | Existing distinct cancellation message |
| Existing authenticated browser whose new attempt fails | Preserve prior identity; do not authenticate/link from rejected exchange |
| Unexpected application/programming exception | Existing error boundary; no new blanket catch |

No provider, cookie, audience, identity-link, account-creation or session lifetime
policy changes are proposed. Existing OAuth-only flows do not acquire a new
ID-token requirement. Verification is performed by the actual upgraded library;
tests may replace transport but not the verifier.

## Required implementation and validation

After the reviewed contract commit, add the specific JOSE exception boundary with
value-free diagnostics and pin the evaluated Authlib/joserfc batch. Retain the
new dependency evaluation and exact transitive delta. Test real keys/signatures
and hostile claims through the actual callback, including a missing nonce claim
when the client expects one and a `nonce_supported=false` bypass attempt. Check
redirect/flash and
absence of profile/link/login side effects. Retain valid OAuth-only and OIDC
controls, cancellation, safe-next behavior and remembered login. Complete clean
image build, fresh scan, full candidate gates and final independent reviews.
This checkpoint is not dependency acceptance, M4, or rollout authorization.

## Independent checkpoint reviews

Correctness approved the substantive contract with no Medium/High finding and
requested explicit source/authority/path metadata plus preservation of the local
session-expiry warning; both are recorded above. Security approved with no
Medium/High finding and requested precise cancellation-before-client-lookup
ordering in the state matrix; that wording is corrected. Both approvals are
contract-only. Real client verification, focused/full candidate acceptance and
final security review remain implementation obligations.
