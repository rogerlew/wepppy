# Creation Policy Contract Decision

Date: 2026-09-07 UTC. Starting revision: `a64c39f8523ba7efab0e13c4973026700f1d780d`.

## Authority and Approval

The operator requested default-preserving opt-in anonymous creation restriction, interface hiding, and Docker documentation, then explicitly instructed: “execute docs/work-packages/20260907_anonymous_project_creation”. This authorizes execution of the scaffolded anonymous-only scope and its necessary local checkpoint commit. No production deployment is authorized or claimed. Classification: intended behavior enhancement; security impact high; no data/model/queue changes.

Current contract matrix: `docs/schemas/rq-engine-agent-api-contract.md` owns create/alias API descriptions (amend); `docs/dev-notes/auth-token.spec.md` describes token classes/scopes (unchanged, session tokens remain run-scoped); `docs/schemas/weppcloud-session-contract.md` owns session lifecycle (unchanged); `docs/schemas/project-creation-policy.md` owns new policy/parser/UI rules; `docs/schemas/rq-response-contract.md` owns error envelope (add policy pointer); `docs/schemas/weppcloud-csrf-contract.md` owns cookie origin/CSRF (unchanged); `docs/ui-docs/controller-contract.md` owns shared UI runtime (unchanged); `wepppy/weppcloud/feature_registry/specification.md` owns interfaces role/config launch visibility (add cross-link for additional access gate). No borrowed domain implementation or closure is asserted.

## Exact Delta and Rationale

See the new canonical policy. Default true preserves behavior. False denies anonymous CAPTCHA and anonymous session-token creation, preserves validated user/service/mcp callers, and hides anonymous launch surfaces. All session tokens are denied in restricted mode because their current authority is existing-run scoped. No token issuance or scope expansion is introduced. Empty/malformed policy is an explicit configuration error, not permissive. This refines the scaffold's unspecified parser behavior and anonymous-token boundary.

## Other Creation Paths

`fork_archive_routes.py:fork` allows anonymous fork with independent access/CAPTCHA gates; unchanged and explicitly excluded. Restore restores existing runs under its current auth/access checks. `builder_routes.py` requires JWT but permits an absent actor for session/service/mcp tokens, so an anonymous session token can remain an alternate allocation path; explicitly excluded and unchanged. Batch creation is Admin gated. `routes/test_bp.py` belongs to test support and must retain its existing deployment enablement guard. `/create` index and `/config-builder/` UI already require login. This setting must not be advertised as disabling every anonymous allocation path.

## State and Regression Matrix

| Runtime state | true / unset | false |
| --- | --- | --- |
| No cookie or credentials; missing/empty CAPTCHA | Existing CAPTCHA-required denial | anonymous_creation_disabled; no side effects |
| No identity; valid or invalid CAPTCHA, including stale solved token | Existing CAPTCHA verification outcome | Denied without consuming CAPTCHA |
| Valid current browser session, with/without CAPTCHA field | Existing branch order | Cookie identity succeeds; existing ownership |
| Valid user rq_token/Bearer | Existing behavior | Existing active-user resolution and ownership |
| Expired rq_token + valid cookie | Existing recovery | Same recovery |
| Invalid explicit token + otherwise valid CAPTCHA/cookie | Existing auth denial | Same denial; no fallback |
| Valid service/mcp scoped token | Existing behavior | Preserved |
| Session token absent/empty/nonpositive/noninteger user_id | Existing behavior | Denied; never use sub |
| Session token signed positive user_id, active account | Existing behavior | Denied; use user JWT or authenticated cookie |
| Deleted/inactive/conflicting account | Existing identity failure | Existing identity failure; no allocation |
| Explicit empty/invalid environment value | New explicit configuration failure | New explicit configuration failure |
| Supported legacy preset; writer on/off; missing idempotency state | Existing creation contracts | Same contracts for authorized callers |
| Anonymous page with omitted creation DOM | Not applicable | Readable, sign-in works, no JS errors |
| Authenticated role-limited page | Existing role gates | Same role gates, Start actions retained |

Expected access failures use the policy contract; exceptional configuration uses 503; existing identity/database/payload errors remain existing contracts. Validate request JSON and form transport and direct unmocked authorization/creation boundaries. Tests and real Compose evidence are required; unit mocks alone do not prove filesystem or identity safety. Review artifacts and disposition must be present in the standalone checkpoint before production edits.

Review refinement: `/api/create/` is a middleware alias and must share denial tests. Locations pages also submit to the gated endpoint; hiding their controls is outside the requested interfaces-page scope.

## Review Disposition and Acceptance

2026-09-07 20:52 UTC: independent correctness and security reviews passed after correction of session authority expansion, omission of the agent API alias contract, error-envelope precision, and builder scope description. See `20260907_checkpoint_correctness.md` and `20260907_checkpoint_security.md`. All findings resolved; parent accepts reviewed checkpoint for implementation. The local standalone commit is necessary to execute the operator-approved package under the contract-first standard.
