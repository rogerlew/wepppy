# ADR-0061: Persistent GridMET queue waiting and transport recovery

Status: accepted, 2026-09-09 PDT. Supersedes ADR-0050's admission deadline and terminal transient Redis failure decisions.

## Context

Marta's production climate jobs failed on two-second Redis poll/release timeouts. The original implementation also imposed a 900-second queue wait deadline, contrary to the requested queue semantics. A healthy waiter or a completed response should not fail merely because capacity is busy or one Redis response is delayed.

## Decision and rationale

Remove elapsed admission deadlines. Requests wait until admitted or explicitly canceled; heartbeat expiry reclaims abandoned tickets. Keep the legacy positive `wait_timeout_seconds` configuration/fingerprint field accepted but ineffective for compatibility with running clients. No HTTP retry/backoff shares a queue-age deadline.

Keep bounded two-second individual Redis socket operations, with redis-py automatic retries disabled, and recover transport errors at the admission operation boundary. Replay enqueue/poll with the same ticket/token; matching active state must renew before providing a fresh local lease bound. Never retry authentication, policy, ownership, or malformed-state errors as transient outages. Renewal retries only while the last confirmed lease remains locally valid and stops promptly on release. Release retries idempotent matching-token cleanup. Cancellation and exceptional exit perform bounded cleanup; abandoned leases/tickets expire normally.

Increasing the wait timeout was rejected because it still discards healthy queued work. Blind Redis retries were rejected because command execution may precede a lost reply and lease validity needs explicit reconciliation. Disabling admission was rejected because it removes the shared concurrency bound.

## Decision provenance

Venue: user/Codex incident conversation, 2026-09-09, America/Los_Angeles. Participants: requesting operator and Codex. Decision owner: requesting operator, who explicitly specified a queue without the 15-minute wait cutoff and requested the fix. Implementer: Codex. Original two-second and 900-second values were implementation choices, not a requirement from the operator.

## Evidence, risk and rollback

Evidence: [queue recovery package](../work-packages/20260909_gridmet_queue_recovery/package.md). Prior policy: [ADR-0050](ADR-0050-gridmet-redis-admission.md). Durable semantics: [admission contract](../schemas/gridmet-redis-admission-contract.md).

A prolonged Redis outage may keep waiting/releasing clients blocked until cancellation or recovery; an active request still loses authorization at confirmed lease expiry. Live FIFO order survives retries while ticket heartbeat state exists; a ticket reclaimed after a prolonged outage rejoins at the tail. Old workers retain old failure behavior until recreated. Rollback via coordinated worker code rollback; preserve namespace and concurrency configuration and never delete live ownership state. Activation requires production-equivalent boundary validation.
