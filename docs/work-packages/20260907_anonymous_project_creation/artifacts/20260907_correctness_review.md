# Correctness and User-Experience Review - Anonymous Project Creation

## Metadata

- **Package**: `docs/work-packages/20260907_anonymous_project_creation/`
- **Reviewer**: independent reviewer agent `/root/checkpoint_correctness`
- **Date**: 2026-09-07 UTC
- **Scope reviewed**: shared policy parser; rq-engine create authorization and alias; Flask configuration and interfaces rendering; development/production Compose; affected Docker, developer, and user documentation; changed configuration/API/template tests.
- **Commit context**: implementation `935d96220222adaab065e96980de4d3efeda3e30` and its subsequent OpenAPI description shortening, after standalone checkpoint `fb67f32fccb00410b561e4f331f0b89a815a487e`, verified as an ancestor of HEAD. Checkpoint commit contains contracts and both independent checkpoint reviews, with no production implementation files.
- **Canonical contracts**: `docs/schemas/project-creation-policy.md` (all sections); `docs/schemas/rq-response-contract.md` (error envelope); `docs/schemas/weppcloud-csrf-contract.md` (cookie origin boundary); `docs/dev-notes/auth-token.spec.md` (token classes); `wepppy/weppcloud/feature_registry/specification.md` (interface role visibility).
- **Related reviews**: `artifacts/20260907_checkpoint_correctness.md`, `artifacts/20260907_checkpoint_security.md`, `artifacts/20260907_security_review.md`; final security evidence recheck is separate.

## User Outcome

- **Goal**: operators may require account authentication for the existing create endpoint while retaining the default anonymous CAPTCHA flow.
- **Success**: restricted anonymous interfaces show information and a sign-in link; authenticated visitors retain permitted Start actions; valid authenticated creation returns the existing redirect and ownership behavior.
- **Failures**: anonymous/disallowed-class requests receive `403 anonymous_creation_disabled`; invalid policy returns `503 creation_policy_configuration_error` from rq-engine and fails Flask configuration loading. Existing credential, payload, ownership, and storage errors retain their contracts.
- **Partial state**: policy denials precede CAPTCHA consumption and creation state. Existing creation compensation remains responsible for later failures; this change does not alter it.

## Valid-State Matrix

| State | Valid? | Required behavior | Source/test evidence |
| --- | --- | --- | --- |
| Policy absent / feature never configured | Yes | Default anonymous CAPTCHA creation | Shared parser returns true only for absence; existing alias/default creation tests retained. |
| Policy explicitly empty or malformed | No | Explicit configuration error | Configuration parser cases; API invalid-policy test asserts 503 and no captured allocation. |
| Restricted site; visitor has no authenticated identity | Yes | Readable interfaces and explicit creation denial | JSON/form and primary/alias denial matrix; restricted real HTTP evidence verifies both aliases, unconsumed solved CAPTCHA, and absent idempotency reservation. Chromium shows zero forms, context menu, widgets, or CAPTCHA asset requests. |
| Restricted site; active browser account and stale CAPTCHA field | Yes | Cookie identity authorizes creation without CAPTCHA | Restricted real HTTP login and creation with stale CAPTCHA creates `calcareous-federation`, with the current account's owner ID and NoDb/config artifacts. |
| Restricted site; valid user/service/MCP credential | Yes | Existing creation result/ownership semantics | Both-mode signed user-token test; final restricted real signed service/MCP requests return 303 and preserve their existing unowned-run behavior. Existing verification still runs before class policy. |
| Expired rq_token plus current cookie | Yes | Existing cookie recovery | Existing recovery test now runs in both modes; explicit invalid nonexpired credentials do not recover. |
| Missing/inactive/conflicting account | No | Existing ownership failure before allocation | Both-mode actor-resolution failure tests plus real JWT/Redis/PostgreSQL restricted rejection for nonexistent, inactive, and conflicting account identities in both token transports. |
| Supported legacy presets and writer enabled/disabled | Yes | Existing successful creation, bounded denial before writer access | Existing legacy/idempotency tests and restricted writer-mode denial matrix. No preset/model/queue changes. |
| Valid session token, with or without user_id; unknown class | No in restricted mode | Policy denial without interpreting session sub as account identity | Signed-token matrix covers both rq_token and Bearer transports and disallowed classes. Default mode remains unchanged. |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Restricted anonymous cookie/CAPTCHA request | Expected | 403; `Sign in to create a project.` | Creation policy, API Authorization. |
| Restricted valid session/unknown-class token | Expected | Same policy denial | Run-scoped session authority does not grant global creation. |
| Invalid explicit signature/scope/revocation | Expected | Existing auth error takes precedence | Creation policy preserves explicit credential validation. |
| Empty/malformed deployment value | Exceptional | Flask configuration failure; rq-engine canonical 503 | Creation policy, Configuration; prevents silent permissive fallback. |
| Missing config or malformed payload | Expected | Existing canonical 400 | Creation policy explicitly permits payload validation before authorization. |
| Invalid/deleted/inactive account | Expected | Existing `run_ownership_failed`, no allocation | Existing current-account authority is retained. |

## Review Checks

- [x] Canonical intent and checkpoint ancestry verified independently of implementation.
- [x] Absent, empty, populated, legacy, and hostile states reviewed separately from request/flag combinations.
- [x] Default branch order preserved; restricted cookie-plus-CAPTCHA and disallowed-token behavior match the accepted policy.
- [x] All creation forms and context-menu actions are gated; existing JavaScript exits when its context-menu element is absent.
- [x] Existing role visibility remains separate from creation permission; informational content and sign-in navigation remain present.
- [x] Development and production Compose use unset-only interpolation for both web/API services. Docker activation/reversion instructions match the inspected canonical targeted-web deployment path.
- [x] Error and partial-state contracts remain explicit; no new persistence, model, queue, or exception-swallowing behavior introduced.
- [x] Focused, frontend, OpenAPI, stub completeness, and broad-exception validation results reviewed against their retained local logs.
- [x] Direct unmocked cookie/authentication, ownership/filesystem, and browser workflow evidence reviewed against retained scripts and result JSON.
- [x] Final broad pytest rerun complete and reviewed: 7,721 passed, 72 skipped. The first attempt's OpenAPI description length regression is fixed with the original budget retained.
- [x] Disposable run cleanup and restored-default operational handoff complete and recorded: ten canary directories and their ownership records removed; both services use true again.
- [x] No exhaustive-coverage claim made: mocked route/template tests cannot establish service identity, mounts, real CAPTCHA consumption, or browser console behavior.

## Findings

No source-level correctness or UX defect remains in the implementation reviewed. Checkpoint findings are resolved. The overlong OpenAPI description found by the first broad run was shortened; this reviewer inspected the delta and confirmed the focused OpenAPI log reports 12 passes. Final broad-suite completion, cleanup, and restoration evidence close the remaining execution gates.

## Runtime and Validation Recheck

Reviewed `runtime_canary.py`, `browser_canary.cjs`, both `20260907_runtime_*.json` files, both `20260907_browser_*.json` files, and `20260907_validation.md`. The HTTP canary uses the development HTTPS proxy with real login/CAPTCHA, signed token decoding, Redis revocation/idempotency access, PostgreSQL actor/ownership queries, and generated run directories. No production auth/allocation function is replaced. Successful runs explicitly assert HTTP 303, `ron.nodb`, and the expected ownership record. Restricted requests assert the policy response for both aliases, then independently verify the same CAPTCHA remains valid. Account/token rejection cases use both Bearer and rq_token transports.

The browser canary observes real Chromium `pageerror` events, DOM state, and CAPTCHA asset requests. Restricted anonymous loading has zero launch forms/context menu/widgets and requests no CAPTCHA assets; the actual sign-in link reaches login and authenticated loading restores 15 permitted forms. Both modes report zero page exceptions. The browser check validates launch availability rather than submitting every regional preset; HTTP creation exercises `disturbed9002`.

Independent log readback confirms 296 focused pytest passes; 108 frontend suites / 835 tests pass; frontend lint and stub completeness pass; 12 OpenAPI tests pass after the fix; changed-file broad-exception enforcement passes with zero new catches. Final `/tmp/creation-broad-final.log` reports **7,721 passed, 72 skipped**, in 779.85 seconds. Restored-default anonymous and authenticated creation success is retained in `20260907_runtime_restored.json`.

The final `20260907_runtime_denial_snapshots.json` strengthens denial evidence: 16 requests compare the exact before/after sets of root directories, sharded run directories, and Run primary keys, with no changes. The reviewed `allocation_snapshot` and `assert_no_allocation` functions compare sets, not only the summarized counts. Cases include both anonymous aliases, cross-origin and missing-origin requests carrying a valid login cookie, both signed-token transports, disallowed session classes, and unavailable/conflicting accounts. The same final run successfully creates with real signed service and MCP credentials and retains correct cookie-user ownership.

Reviewed `cleanup_canaries.py` and `20260907_cleanup_final.json`: cleanup is limited to the recorded ten run IDs and asserts both directory absence and no remaining Run record after removal. It verifies owned canaries belong to the existing test account before deleting the registration. `20260907_restoration_final.json` records true in both service environments, restored anonymous forms, and the existing CAPTCHA-required response for an anonymous request without CAPTCHA. `20260907_runtime_identity.json` records actual UID/GID/groups, umask 0022, and run/source mounts. Final restricted Chromium evidence in `20260907_browser_final.json` again reports zero anonymous forms, 15 authenticated forms, and zero page exceptions after the canary's failure logger was sanitized.

Coverage remains bounded: the real canary does not exercise every preset, low-privilege role, or optional writer state. Existing/focused tests cover these compatible paths, while the changed cookie, token-policy, browser, and creation/ownership boundaries have direct evidence. No exhaustive state claim is made.

## Verdict

- **Gate status**: `pass`.
- **Unresolved source findings**: High 0; Medium 0; Low 0.
- **Release recommendation**: `ship` for correctness/UX; dedicated security sign-off and normal operator deployment procedures remain separate.
- **Reviewer sign-off**: `/root/checkpoint_correctness`, 2026-09-07; source, direct runtime/UX, full validation, cleanup, and restoration evidence reviewed. No correctness finding remains open.

Residual scope risk: default-mode session-token behavior and alternative allocation routes deliberately remain unchanged. Operators must not interpret the new flag as a site-wide ban on anonymous allocation. Location-specific pages can still expose launch controls whose POST is rejected; the package explicitly excludes changing those pages.
