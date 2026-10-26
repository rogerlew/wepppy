# ADR-0106: Scheduled Culvert JWT renewal

Status: accepted; implemented and validated on wepp1/wepp2, 2026-10-26 UTC.

## Decision provenance

Venue: operator/Codex conversation, 2026-10-26 UTC. Participants: Roger Lew (decision owner), Codex (implementer). Explicit direction: scaffold and execute a systemd renewal work package, test through systemd and validate the updated token on wepp2.

## Decision

Use a daily persistent systemd timer on wepp1 under the existing lingering operator user. Issue the same 90-day submit-only identity when at most 30 days remain. Deliver with restricted SSH over Tailscale, validate before atomic replacement and read a file per submission. Keep prior credential for recovery. These are operational scheduling bounds, not model parameter changes. Operational limits are 16,384 characters per credential read, 30 seconds per HTTPS verification, 15 seconds for SSH connection setup, 120 seconds per issuer/SSH subprocess, and 5 minutes per systemd invocation. Daily scheduling adds up to 15 minutes of jitter. These bounds reject unreasonable credential input and prevent a stalled dependency from leaving renewal running indefinitely; ordinary JWTs are far smaller and observed renewal completes in seconds.

## Rationale and alternatives

Manual expiry tracking repeatedly failed. A 30-day margin permits daily retries and repair without extending credential authority. Cron was rejected in favor of systemd status/journal/catch-up. mTLS and an issuance API are deferred until the existing mechanisms prove inadequate. Reusing existing user systemd avoids new root privileges.

## Evidence and rollback

See [work package](../work-packages/20261026_culvert_jwt_renewal/package.md) and [contract](../schemas/culvert-jwt-renewal-contract.md). Risks: issuer/SSH/network outage, invalid replacement, stale consumer cache. Mitigations: pre-install validation, atomic file, per-submission read, durable status and explicit failure. Disable timer and restore a valid previous file; legacy env-only clients remain supported. Off-host notification requires an operator-specified destination.
