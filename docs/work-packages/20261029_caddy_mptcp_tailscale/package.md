# Caddy MPTCP and homelab Tailscale migration

Status: active. Security impact: high; independent correctness, QA and security review required.

## Scope

Disable MPTCP creation in every active wepppy Compose Caddy service. Move the
homelab forest/forest1 web entry points from DuckDNS/pfSense to their existing
Tailscale names. The operator owns pfSense cleanup. This forest is the homelab
host, not forest.moscowfsl.wsu.edu (fsweppduo).

## Contract and complexity budget

Preserve web authentication, application data, queues, service identities, mounts,
and routes. Reuse existing Tailscale Serve, Caddy and Compose; no added daemon,
package, certificate-renewal cron, or auth bypass. Keep the old path working until
new HTTPS and login are accepted. The operator selected local username/password
login only, with OAuth disabled. Preserve existing accounts and password hashes.
Only homelab cutover is deployment scope; wepp1 Compose receives a source patch.

The broken shared assumption is that disabling MPTCP on the host covers Caddy
containers. It does not: each network namespace has a separate sysctl, and old
listeners survive settings changes. Five active Compose variants are in scope;
immutable work-package snapshots and other repositories are excluded.

## Acceptance and lifecycle

All five Compose Caddy definitions set net.mptcp.enabled=0. Homelab live Caddy
namespaces have zero MPTCP sockets after recreation. Both ts.net domains provide
trusted HTTPS, correct redirects, existing-project access and working login,
with no widened proxy trust or reduced CSRF checks. Retain explicit deployment
holds when required privileges or authenticated validation are unavailable.

Kernel patching remains necessary for CVE-2026-98432. Reassess disabling MPTCP
after a fixed host kernel is booted and an operator requests re-enablement.
Recurrence triggers are MPTCP sockets after deployment or failed TLS/login/streams.

Precedent: forest FSWEPP and Culvert deployments in this incident verified
per-container zero sysctls and sockets. Related repository package:
20261026_culvert_jwt_renewal (existing Tailscale transport); standards:
hardening-lifecycle-standard and dependency-evaluation-standard. No new dependency
is added; Serve uses the installed daemon and replaces pfSense TLS for these hosts.
