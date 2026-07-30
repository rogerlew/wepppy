# SHR-06 Pure UI Command Bar Contract

**Status**: Verified 2026-07-29 UTC
**Package ID**: SHR-06
**Security impact**: `high`

## Purpose

Verify the shared keyboard Command Bar from actual host rendering through
command parsing, navigation, privileged recovery, diagnostics, Query Engine MCP
token minting, Wojak agent chat, StatusStream delivery, and backend
authorization.

## Concise Intent Contract

Every host renders at most one initialized Command Bar. Pressing `:` outside an
editable control opens it, Escape closes it, Enter executes exactly one parsed
command, and history navigation remains page-local. Missing optional run
context or controller dependencies must produce a visible, truthful result
without a request or exception.

Safe navigation and diagnostic commands may be available to an authorized run
viewer. State-changing commands independently preserve their owning route's
authorization, use the canonical HTTP method, same-origin credentials, and
CSRF header, and expose canonical failures. Lock and cache recovery are
PowerUser/Admin/Root-only, run-confined POST operations.

Query Engine MCP token minting requires an authenticated user authorized for
the exact run. The token remains run-scoped, `token_class=mcp`, restricted to
the documented query scopes and audience, visible only in the response, and
absent from the generated instructions file. Repeated initialization retains
one command owner and one mint request.

Wojak session start, message, and termination require the authenticated,
run-authorized session boundary, use CSRF-protected same-origin requests, encode
session identifiers, and disconnect StatusStream on termination or teardown.
Remote Markdown is sanitized before insertion: active content, event handlers,
and unsafe URL schemes must not survive.

## Scope

- `command-bar.htm`, `command-bar.js`, and every actual host include;
- keyboard activation, parsing, help, history, navigation, and result lifecycle;
- lock/cache/log-level routes and their finite project-route consumers;
- Query Engine MCP token rendering, route, claims, and redacted instructions;
- Wojak agent session client/route/StatusStream integration;
- direct jsdom, Flask route, render, auth, CSRF, error, and retained shared-helper
  evidence.

## Exclusions

SHR-01 owns generic DOM/form primitives. SHR-02 owns the general HTTP, session,
and recorder implementations. SHR-03A/03B own generic StatusStream,
controlBase, bootstrap, and observability internals. This package verifies
their Command Bar consumption but does not claim those packages complete.
Project field semantics remain DOM-02. SHR-07 owns the PowerUser panel.

## Acceptance

Actual host renders and direct client execution prove one owner, keyboard and
history behavior, exact URLs/methods/payloads, absent-dependency handling,
visible canonical failures, token secrecy, StatusStream teardown, and hostile
Markdown confinement. Route tests prove exact-run authorization, privileged
recovery roles, CSRF-compatible mutation methods, MCP claims/redaction, and
agent session boundaries. Existing shared helper, route, frontend, graph, and
full Python evidence remains green. A dedicated security review has no
unresolved high or medium finding.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; the operator directed execution of
  SHR-06 and this contract preserves existing token scopes/TTL, chat TTL,
  command vocabulary, and lock/cache semantics.

## Related Packages

- **Consumes without completing**: SHR-01, SHR-02, SHR-03A, and SHR-03B.
- **Depends on verified UI context**: SHR-04A, SHR-04B, DOM-02, and SHR-07.

## Security Review Gate

The Command Bar crosses ambient-session mutations, privileged recovery,
run-scoped bearer-token minting, filesystem instructions, remote agent content,
Redis messaging, and live StatusStream data. A dedicated review is required at
`artifacts/2026-07-29_security_review.md`.
