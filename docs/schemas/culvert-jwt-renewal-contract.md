# Culvert JWT renewal contract

Status: implemented and environment-validated on wepp1/wepp2 (2026-10-26 UTC); off-host notification destination remains unconfigured.

## Authority and purpose

The operator authorized scheduled issuer-side renewal on wepp1 and installation on wepp2 through systemd, including live end-to-end validation. This contract governs that credential lifecycle; existing JWT validation, service registration and operation scopes remain authoritative. Manual renewal repeatedly allowed the 90-day credential to expire. Automatic renewal must preserve the same authorization and avoid application restarts on each rotation.

## Issuance and scheduling

The existing wepp1 operator user runs a daily persistent systemd timer, using the deployed issuer through wctl. Renew when remaining lifetime is at most 30 days; issue for 90 days. Explicit force is permitted for acceptance or recovery. Preserve subject `culvert-batch-submit-90d`, audience `rq-engine`, token_class `service`, service_groups `culverts`, scope exactly `culvert:batch:submit`, and no run claims. Each token has a fresh jti. Signing secrets never leave the issuer. No general token issuance privilege is delegated to the Culvert app.

## Delivery and installation

A dedicated SSH key uses the Tailscale route and pinned host verification. The receiving authorized_keys entry restricts commands to fixed status/install actions and disables forwarding and PTY. Receiver rejects oversized/malformed/incorrect-principal candidates, verifies acceptance by the live HTTPS API before replacement, and atomically installs a 0600 token beneath a 0700 directory in the existing instance mount. No bearer/private key appears in argv, logs, receipts, repository or error text. Retain the previous token for bounded rollback overlap; do not revoke it during installation.

Absent installed file is an initial provisioning state: report absence and allow a validated candidate to create it. Empty, malformed or wrong-identity installed files fail explicitly and require operator repair; no silent fallback. Status returns only safe identity/expiry/fingerprint metadata. Verification uses an empty POST that must reach authenticated missing-payload validation; it must enqueue no model job. Network/validation failure leaves the prior token unchanged. A failed readback after replacement is a failed attempt, never a success claim.

## Client consumption and compatibility

When WEPPCLOUD_TOKEN_FILE is configured, the client reads that file for every new submission. Missing, unreadable, empty or malformed file content fails explicitly; never fall back to the environment token. Without the file setting, existing WEPPCLOUD_TOKEN behavior is preserved. Rotation does not change active submissions or require restarting containers. One deployment reload may establish the new file setting. Browser-facing 401 handling and upload preflight changes are outside this package.

## Observation and recovery

Persist a sanitized last-attempt status and emit service journal success/no-op/failure records. Renewal failures produce nonzero systemd status. An external notification destination must be explicitly configured before claiming off-host alert delivery. Timer checks recur daily, including catch-up after downtime; overlapping invocations are serialized. Operators may disable the timer and install a previously valid credential through the verified receiver. End-to-end acceptance requires a systemd-triggered JWT change read by the live worker plus successful API authentication; systemd success alone is insufficient.

## Rationale and bounds

Reuse existing systemd, wctl, SSH, HTTPS, principal and mount. No new identity provider, mTLS service, root runtime privilege, Kubernetes dependency or scope expansion. Daily cadence and 30-day margin provide repeated repair opportunities; retained 90-day TTL preserves existing issuance policy. See ADR-0106 for decision provenance and the integration renewal runbook for operations.
