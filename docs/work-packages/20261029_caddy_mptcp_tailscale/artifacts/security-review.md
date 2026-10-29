# Independent security review

Reviewer: caddy_security_review. Date: 2026-10-29. Security impact: high.

## Disposition

Source review passes. No additional source changes required. Package closeout is
on hold for forest1 successful existing-account password login and authenticated
profile/project access. Preserve credentials and authentication policy; do not
reset passwords or bypass checks to obtain test acceptance.

## Resolved findings

Direct backend exposure is removed through loopback publication, with forest's
Redis tailnet exception. HTTPS upstream metadata is fixed for Serve, site Host
matching prevents arbitrary-host application routing, and forwarded-port headers
are removed. Public default port parity was checked. Forest authenticated login,
project/report/download, WebSockets and CSRF rejection pass; operator confirms
Firefox login and email delivery.

## Remaining limitations

A TCP Redis NOAUTH result establishes transport/authentication enforcement only.
Follow-up authenticated probe discovered saved forest1 companion credentials are
rejected. No companion container is currently running and no credentials changed;
recorded separately in runtime-evidence.md. Forest1 authenticated acceptance is
still pending. No public-host live Caddy rollout was performed in this package.
Kernel updates remain necessary; unrelated older host MPTCP listeners remain.

See [runtime evidence](runtime-evidence.md) and the durable
[homelab runbook](../../../infrastructure/homelab-tailscale.md).
