# SURF-07 Pure UI RQ Job Dashboard Contract

**Status**: Verified
**Package ID**: SURF-07
**Security impact**: `high`
**Dedicated security review**: required only if an actual production patch
changes token, polling, cancellation, or metadata exposure behavior

## Purpose

Verify the RQ job dashboard from its CAP-gated Flask host through job-info
polling, nested job-tree rendering, terminal/error/rate-limit behavior,
session-token and fallback-token acquisition, authorized cancellation, and QR
navigation.

## Concise Intent Contract

The dashboard safely renders an exact job identifier, polls the canonical
rq-engine job-info endpoint, preserves expanded tree state, escapes server
metadata, shows aggregate and child progress, stops at terminal/not-found/error
states, and backs off boundedly on rate limiting. Polling remains compatible
with the configured rq-engine poll-auth mode.

Cancellation requires confirmation, disables the action while pending, obtains
an `rq:status` token through the run-scoped session bridge when possible or the
authenticated rq-engine token bridge otherwise, posts once to the canonical
cancel endpoint, surfaces canonical errors, and refreshes authoritative job
state. Server-side cancellation retains scope, revocation, session-marker,
run-ownership, and Culvert compatibility checks.

## Scope

- `routes/rq/job_dashboard/routes.py` host and job-id normalization;
- `routes/rq/job_dashboard/templates/dashboard_pure.htm`;
- rq-engine `jobstatus`, `jobinfo`, batch jobinfo, and `canceljob`;
- session and rq-engine token bridges used by the dashboard;
- nested job payload and terminal-state normalization; and
- direct render, real inline Jest, Flask route, and rq-engine tests.

## Exclusions

This package does not change RQ job creation, queue topology, worker execution,
retention, token claims/scopes, polling-mode policy, cancellation authority,
StatusStream, the Admin RQ Info Details surface, or DEVAL behavior. SURF-17 and
SURF-18 remain separate consumers.

## Acceptance

Actual rendering proves job identity, action/state/summary/tree/QR targets,
safe Jinja embedding, and script assets. Inline execution proves polling,
tree/error escaping, terminal stop, rate-limit backoff, token acquisition, and
cancel refresh. Existing Flask/rq-engine/session tests prove authorization and
payload contracts. Confirmed mismatches receive only the smallest compatible
repair and proportional independent review.

## Outcome

Direct rendering and real inline execution now cover the host targets, safe
metadata presentation, terminal stop, rate-limit backoff, required poll-auth
recovery, token choice, and cancellation refresh. The audit repaired one
confirmed mismatch: after an unauthenticated job-info request receives 401 or
403, the dashboard obtains its existing authenticated `rq:status` fallback
token and retries exactly once. Server policy, claims, routes, cancellation
authority, and queue wiring are unchanged.

## SURF-03A Fork/Archive Serial Queue Amendment

The operator-approved bounded enhancement at
`../20260803_fork_archive_serial_queue/` retains the dashboard cancellation
button and all behavior for jobs outside `fork-archive`. For a job whose RQ
origin is `fork-archive`, an authorized project user may cancel while it is
queued; after it starts, rq-engine requires Admin or Root. This is a server-side
authorization rule and the dashboard continues to display canonical forbidden
responses. SURF-07 stays closed; SURF-03A implementation conformance is pending
its GOV-00A-M1G checkpoint ancestor.
