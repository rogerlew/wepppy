# Security review: Runs bulk TTL control

## Metadata and triage

Independent reviewer: `ttl_contract_security`; date: 2026-11-05.
Contract ancestor: `6cbd4404b`. Security tier high due to public route-handler/UI
surface. Scope: user.py sort key, runs2.html bulk handler, changed route/handler
tests and user guide. Existing server auth/CSRF/persistence boundaries unchanged.

## Findings

No unresolved high, medium or low findings. The checkpoint's medium response
integrity finding is resolved in implementation: actual returned active,
protected TTL metadata is required; null/malformed/deleting states are rejected
as confirmation. The reviewer checked this in the actual handler and tests.

## Surface checks and noninterference

Authentication and catalog scope precede sorting. Each mutation independently
uses the existing authorized setter and CSRF header; catalog visibility grants
no new access. Same-origin credentials and encoded run/config preserve routing.
Identifiers/errors are text, including tested hostile markup. Requests are
sequential; repeated bulk invocation and new delete actions are blocked while
protection is in progress. Partial failures are retryable; valid batch exclusion
succeeds. Empty and readonly selections issue no request. Old-scope responses
cannot alter newly loaded rows. No new secret, dependency, external destination,
filesystem operation, queue edge, subprocess or deployment boundary.

## Evidence and disposition

Existing real authorization/CSRF/TTL persistence tests and actual inline-script
regressions provide boundary evidence. Parent recorded 104 focused Python passes,
frontend lint and full-suite passes; final totals are in validation.md. The
Chromium smoke uses mocked transport and is not deployment proof.
Security gate: PASS. Correctness and whole-suite gates remain separate.

The reviewer rechecked final catalog-cache/generation guards and selection reset
after correctness fixes; security sign-off remains PASS.
