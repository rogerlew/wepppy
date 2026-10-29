# Disable Caddy MPTCP and migrate homelab HTTPS

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

## Purpose / Big Picture

The operator should reach forest and forest1 via private trusted HTTPS on their
Tailscale names, without pfSense proxying. Caddy must stop opening MPTCP sockets
in all supported Compose variants. Ordinary HTTP, login and project workflows
must continue to work.

## Progress

- [x] 2026-10-29 UTC: identified five active Caddy definitions and both Tailscale names.
- [x] Validate net.mptcp.enabled=0 in all five rendered Compose variants.
- [x] Operator enabled Serve on both hosts; trusted HTTPS login GET returns 200.
- [x] Perform homelab domain/auth/port cutover; forest full browser workflow passes.
- [x] Operator confirmed forest login works after stale database pools were cleared.
- [ ] Verify forest1 existing-account password login (operator confirmation pending).
- [x] Complete independent source reviews, runtime evidence and documentation.
- [ ] Resolve or explicitly defer forest1 companion credential mismatch (not running).

## Surprises & Discoveries

The working tree contains unrelated user changes. Preserve them. forest docker/.env
explicitly warns that DuckDNS OAuth callbacks are registered externally. Both
hosts lack passwordless sudo. Existing Caddy listens on HTTP port 8080 and requires
X-Forwarded-Proto=https to avoid redirects; verify Serve supplies it before cutover.

## Decision Log

2026-10-29: select existing Tailscale Serve as the first TLS approach, because it
uses the installed daemon and automatically renews certificates. Do not add a
socket mount or certificate-copy daemon without evidence this approach fails.
Host names are forest.tail305ec9.ts.net and forest1.tail305ec9.ts.net. Keep current
account/password data; operator confirmed local username/password login only,
with all OAuth providers disabled on these two homelab hosts.

## Outcomes & Retrospective

Both homelab deployments now use Tailscale HTTPS, local-password-only login and
restricted backend ports. Forest login/project/report/download/stream probes pass;
operator confirms login works. Forest1 authenticated acceptance remains pending.
All five source variants include the Caddy MPTCP mitigation; no public production
rollout was performed. See artifacts/runtime-evidence.md.

## Context and Orientation

Active Caddy definitions are docker/docker-compose.dev.yml, dev.hpc.yml, prod.yml,
prod.wepp1.yml and canary-smoke.yml (each has the docker-compose. prefix).
docker/caddy/Caddyfile is the HTTP reverse-proxy configuration for homelab.
wctl merges docker/defaults.env, docker/.env and optional host .env; never print
merged secrets. forest is local /workdir/wepppy; forest1 uses the same path over SSH.
A network namespace is the container's separate networking configuration.

Host-local WEPPCLOUD_BIND_PREFIX=127.0.0.1: restricts published ports;
REDIS_BIND_PREFIX supports the forest companion-worker tailnet exception. Empty
default prefixes preserve existing public IPv4/IPv6 publication semantics.
CADDY_UPSTREAM_SCHEME=https is permitted only with Serve and loopback ingress;
the default http preserves the existing HTTP-only Caddyfile behavior.

## Plan of Work

Milestone 1 adds only sysctls.net.mptcp.enabled=0 to each Caddy service, then parses
all five definitions and inspects representative live namespaces after recreation.
Milestone 2 tests Tailscale Serve forwarding existing local Caddy before changing
canonical host settings. Inspect callback generation and provider requirements;
retain old access until new TLS, login, CSRF and existing-run routes pass. Record
host-local configuration separately from committed defaults. Milestone 3 obtains
independent correctness, QA and security reviews and documents exact coverage.

## Concrete Steps

From /workdir/wepppy use wctl docker compose config --quiet and focused rendered
configuration inspection. For each homelab host inspect tailscale serve status;
configure tailscale serve --bg http://127.0.0.1:8080 if permissions/HTTPS allow.
Check trusted HTTPS with curl, not -k. Use wctl for Compose operations; recreate
only necessary services and do not flush queues or rebuild unrelated changes.
Record effective domain settings without printing secrets. Do not alter pfSense.

## Validation and Acceptance

Compose parsers must report zero sysctls for all five Caddy definitions. Confirm
live settings and socket absence independently. For migration, trusted HTTPS must
serve login, existing project/report and streaming endpoints, produce same-domain
redirects and maintain CSRF rejection. Use an existing authorized test account if
available; do not claim completed login from an unauthenticated status check.
Run scoped doc lint and diff checks. Literal sysctl changes require parser/readback,
not new literal-assertion tests. Runtime URL/header logic changes require targeted
regression coverage and applicable broader gates.

## Idempotence and Recovery

Retain host-local configuration backups outside Git with restricted permissions.
Do not expose tokens. Restore prior URLs and Caddy publication if cutover fails;
disable only the newly configured Serve entry. Keep MPTCP disabled where validated.
Never replace dirty source trees. Preserve existing kernel-patch caveat.

## Artifacts and Notes

Retain concise sanitized coverage/runtime evidence in artifacts. Historical packages
are excluded from mutation. PROJECT_TRACKER.md already has unrelated edits; add
only this package's entry.

## Interfaces and Dependencies

Use current wctl/Compose/Caddy/Tailscale interfaces. No new dependencies. Durable
operator procedure belongs in docs/infrastructure outside this execution record.

Revision 2026-10-29: initial plan from live inventory and user-authorized scope.

Revision 2026-10-29: local-password-only confirmed; Serve verified. Host MPTCP
listeners remain; requested operator sysctl persistence and tailscaled restart.

Cutover discovery: restarting PostgreSQL left closed pooled connections in web
workers, causing intermittent login500. Restarted both web services after database
health recovered. Full forest probes then passed and operator confirmed recovery.
The durable runbook now requires this dependency restart ordering.

Final review: all scoped source reviews and docs lint/diff checks pass. Companion
transport is reachable but saved credentials fail Redis authentication; no running
companion container or secret mutation. Retained as an open functional limitation.
Operator confirmed forest email delivery as well as login.

Revision 2026-10-29 20:29 UTC: operator extended scope to Caddy-only production
rollout on wepp1 with active jobs. Applied only sysctl additions on its existing
checkout and recreated Caddy with the existing image/no dependencies. Verified
all other container IDs/start times unchanged, MPTCP zero and HTTPS health/login/
job API success. Source remains otherwise at the existing production baseline.
