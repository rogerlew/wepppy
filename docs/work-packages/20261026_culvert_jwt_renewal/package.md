# Culvert JWT automatic renewal

Status: Closed 2026-10-26 UTC (deployed and environment-validated). Owner: Roger Lew. Implementer: Codex.

## Problem and scope

The Culvert integration on wepp2 failed on 2026-10-24 with a TLS EOF while uploading with an expired submit JWT. Manual rotation restored authentication on 2026-10-26. Implement the operator-selected daily systemd renewal on wepp1, restricted SSH delivery, per-submission file consumption on wepp2, and retained real systemd/consumer evidence. No mTLS, new issuer API, new scope, model run repair, Kubernetes deployment, or general error-handling redesign.

## Complexity budget

One Python standard-library operator script, one existing-user systemd service/timer pair, one restricted SSH key, one small client credential helper, regression tests and documentation. Existing wctl issuance, registered identity, HTTPS validation, SSH/Tailscale and user systemd manager are reused. No new dependency, root privilege, queue, database, or daemon. Existing roger user manager has Linger=yes.

## Acceptance and artifact chain

Invoke systemd, mint a fresh 90-day submit-only JWT, deliver and atomically replace the file on wepp2, read the same fingerprint and claims through the actual app loader in its worker container, and obtain authenticated missing-payload validation from wepp1. A second normal service start must retain the token. Invalid candidate/unauthorized SSH commands must fail without replacement. Timer must be enabled with a next trigger. No claim that a full WEPP model analysis was rerun.

## Security impact

High: credential issuance, delivery, filesystem replacement, application consumption. Dedicated independent security and correctness review artifacts required. Never retain bearer tokens or private keys in repository/logs. Use restrictive permissions, fixed receiving actions and TLS verification. Existing service identity/scope remain unchanged.

## Health and recovery

Daily success/no-op receipt, systemd failure/journal and local last-attempt health record; external alert destination pending operator response. Renewal begins with 30 days remaining, leaving retries before expiration. Preserve previous token for recovery; do not revoke during overlap. Monitor first scheduled run and subsequent rotation. Rollback disables timer and restores legacy env consumption/client source if needed.

## References

- [ExecPlan](prompts/completed/implementation_execplan.md)
- [Tracker](tracker.md)
- [Renewal contract](../../schemas/culvert-jwt-renewal-contract.md)

## Outcome

Daily renewal is enabled on wepp1 and consumed without rotation-time restarts on wepp2. Service and timer acceptance passed with real credential replacement and same-process HTTP authentication. Twenty focused tests passed; segmented repository coverage has 11,786 passing cases and 155 skips after correcting the browser path for the tail process. Independent correctness/security gates pass with no unresolved findings. See [validation summary](artifacts/20261026_validation_summary.md) and [live evidence](artifacts/20261026_live_validation.md).

Durable mechanism and recovery rules are promoted to the renewal contract and [operator runbook](../../culvert-at-risk-integration/jwt-renewal.md). External notifications and observation of the first ordinary daily trigger remain documented operational follow-ups, not completed claims. No model-analysis recovery claimed.
