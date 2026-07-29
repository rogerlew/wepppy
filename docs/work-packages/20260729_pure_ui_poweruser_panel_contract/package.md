# SHR-07 Pure UI PowerUser Panel Contract

**Status**: Open 2026-07-29 UTC
**Package ID**: SHR-07
**Security impact**: `high`

## Purpose

Verify the privileged run-page panel from role-gated rendering through confined
resource links, lock recovery, recorder promotion, run-token mint/copy, and
optional web-push behavior.

## Concise Intent Contract

Only authenticated PowerUser, Admin, or Root users may see or use the
PowerUser launcher and panel. Ordinary viewers must receive neither privileged
action controls nor the panel's inline clients. Backend mutations independently
enforce the same role boundary and exact run authorization.

All resource and dashboard links are server-owned, run/config confined, safely
escaped, and use `noopener` when opened in another tab. Clear Locks targets only
the authorized run, requires privileged role, and reports success/failure
visibly. Recorder promotion renders only when its assembler is enabled and the
caller can invoke the route; it submits the exact run/config and preserves
canonical errors.

Admin and Root may mint a run-scoped 24-hour service token using the rendered
same-origin endpoint and CSRF header. The token is shown only in a readonly
field, is never persisted, and copy failures remain visible. Repeated script
execution retains one action owner.

Web-push code must not register a service worker, request notification
permission, access subscription storage, or call the web-push service when its
toggle is absent. When a toggle exists, subscription/run identifiers are
encoded, mutations include same-origin credentials and CSRF, failures restore a
truthful visible toggle state, and no secret is logged or persisted.

## Scope

- privileged launcher and `controls/poweruser_panel.htm` rendering;
- resource, dashboard, lock, recorder, token, and optional notification UI;
- Project clear-lock and recorder-promotion client consumers;
- clear-lock, recorder-promotion, token-mint, and service-worker routes;
- actual-render, direct-inline-client, route, runtime-lock, and security
  evidence.

## Exclusions

SHR-06 owns the broader Command Bar contract; this package updates only its
clear-lock call to preserve the shared route contract. SHR-05 owns Unitizer.
DOM-02 owns general Project state. This package does not redesign profile recording, web-push
service APIs, token TTL/class, lock implementation, or add a notification
control that is not currently rendered.

## Acceptance

Actual ordinary and privileged renders prove role exclusion, exact URLs,
conditional controls, hostile escaping, and script ownership. Direct inline
execution proves absent-toggle no-op, token mint/copy/error/duplicate behavior,
and notification failure recovery if a toggle is present. Route tests prove
privileged role plus exact run authorization for destructive/recovery actions.
Existing Project, recorder, token, runtime-lock, CSRF, and service-worker
evidence remains green. A dedicated security review passes with no unresolved
high or medium finding.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; the operator directed execution of the
  recommended PowerUser package and this contract preserves token TTL, web-push
  TTL, route payloads, and lock semantics.

## Related Packages

- **Depends on**: verified DOM-02 and SHR-04A/04B; consumer evidence for
  deferred SHR-02.
- **Related**: planned SHR-06 Command Bar and verified SURF-14 profile/session.

## Security Review Gate

The panel crosses role authorization, run access, destructive lock recovery,
profile promotion, secret token mint/copy, CSRF, browser subscription state,
service-worker registration, and third-party web-push calls. A dedicated review
is required at `artifacts/2026-07-29_security_review.md`.
