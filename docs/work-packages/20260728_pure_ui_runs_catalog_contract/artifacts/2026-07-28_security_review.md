# SURF-06 Security Review

**Date**: 2026-07-28
**Scope**: authenticated Runs catalog, privileged scoping, and deletion
**Result**: passed; no unresolved high- or medium-severity finding

## Boundaries Reviewed

- Ordinary `alias` input cannot widen the ownership query.
- Admin/Root scoping resolves an exact protected user ID or
  case-insensitive email.
- Catalog text uses DOM text nodes; run and configuration path segments are
  encoded before navigation or mutation.
- Deletion posts the exact stored run/config identity with CSRF and explicit
  same-origin credentials.
- The route reauthorizes the run, rejects readonly state with HTTP 400, and
  uses the existing default-queue worker.
- The browser accepts only the returned job identifier, encodes it for
  polling, removes a row only on `finished`, and leaves terminal failures
  visible.

## Threat Assessment

The focused route/database suite covers ownership and privileged scope
widening. Actual-template and inline-client tests cover hostile metadata,
path-component injection, wrong-configuration deletion, CSRF transport,
readonly selection, and false-success UI state. Project route and RQ tests
cover authorization, queued metadata, exact worker arguments, confined
cleanup, and terminal behavior. Existing authenticated job-status ownership
remains owned and verified by SURF-07; SURF-06 introduces no status endpoint.

No secret, new privilege, cross-origin transport, queue, or destructive
worker behavior was added. The repairs narrow existing behavior and preserve
the canonical authentication, CSRF, ownership, and RQ response contracts.
