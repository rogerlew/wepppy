# ADR-0141: Bound WebSocket stream credentials to five minutes

Status: Accepted  
Date: 2026-11-11

## Context

Status and preflight currently accept sockets without run authorization. The
F4/SEC-04 repair needs a bounded credential and connection lifetime, without
reusing the four-day general RQ token or shortening its Redis run marker.

## Decision

Use service-specific stream credentials with 300-second lifetime, zero
clock leeway, and browser refresh 30 seconds early. Close sockets at expiry
(code 4001), bounding stale authorization to at most five minutes after mint.
Check revocation at handshake; do not claim instantaneous connected-session
revocation. Cache only in memory by exact run/config/service. Allow one fresh
credential retry after an unexplained upgrade failure, then stop visibly.
Protocol credential input is bounded to 8192 bytes before parsing.

## Decision Provenance

Decision Venue: Codex execution session, 2026-11-11 UTC.  
Participants Present: operator and Codex; independent read-only agent reviews.  
Decision Owner: WEPPpy maintainer/forest operator; approved 2026-11-11 in the execution conversation.  
Implementer: Codex; implementation not started.

## Change Summary

Replace unlimited unauthenticated stream admission with a short-lived credential
and bounded authenticated connection. Do not change general RQ token lifetime,
existing marker TTL, scientific parameters, or production deployment state.

## Rationale

Five minutes limits replay and post-mint access changes while the 30-second
refresh margin tolerates normal network latency. Zero leeway makes expiry
closure and both language validators agree. These are security/UX tradeoffs,
not measured throughput claims; forest browser acceptance must test reconnect
continuity and expose a failed refresh without retry storms.

## Alternatives Considered

Four-day RQ tokens are unnecessarily broad. Handshake-only expiry would leave
an established connection authorized indefinitely. Continuous revocation polling
would add load and complexity; this proposal instead states the bounded delay.
No clock-skew bypass is introduced; deployments must have synchronized clocks.

## Consequences

Long-running pages periodically reconnect. Disconnect/refresh tests must prove
that stopped clients cannot be resurrected by late mint responses. Expiry and
revocation-store outages deny access. Public no-cookie and lifecycle policy
are governed by the ratified stream contract.

## Evidence

- [Proposed stream contract](../schemas/weppcloud-websocket-auth-contract.md).
- [Execution plan](../work-packages/20261111_status_preflight_websocket_authorization/prompts/active/implementation_execplan.md).

## Risk and Rollback Notes

Periodic reconnect could miss ephemeral Pub/Sub messages. Validate existing job
polling recovery and preflight snapshots. Forest rollback restores the recorded
image/config mapping; it does not close SEC-04. Production remains unauthorized.
