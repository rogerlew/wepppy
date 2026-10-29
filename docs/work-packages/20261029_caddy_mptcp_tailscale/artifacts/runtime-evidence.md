# Runtime evidence — 2026-10-29 UTC

## Source and boundary checks

All five active Caddy Compose variants parse with net.mptcp.enabled=0. Independent
correctness review compared dev/prod/wepp1 rendered ports to HEAD with new prefix
variables unset: default ports are identical. Caddy adaptation passed generic HTTP
and exact-host HTTPS modes. Homelab runtime caddy+weppcloud were recreated without
build/pull; other published services were recreated using their existing image IDs.
Queues were inspected first; all registered workers in RQ DB9 were idle.

Both Serve endpoints have trusted certificates and target 127.0.0.1:8080.
All WEPPcloud published ports on both hosts now bind 127.0.0.1, except forest Redis
100.99.21.102:6379. A forest1 TCP PING to that address returned NOAUTH, confirming
reachability and required authentication. A later authenticated probe using the
saved forest1 companion env failed: its URL/password agree with each other but
Redis rejects them. No forest1-batch companion container is currently running;
credentials were not changed. This is an open worker-configuration mismatch, not
a proven successful companion workflow. Unrelated host applications were untouched.

Both Caddy namespaces report net.mptcp.enabled=0 and zero allocated MPTCP/MPTCPv6
sockets in /proc/net/protocols. Both host sysctls are zero, persisted by the operator;
Serve443 no longer appears in ss -lnM after tailscaled restart. Other old listeners
remain: forest loopback11434 and forest1 Tailscale18080. Kernel fixes remain required.

## Authentication and application probes

Forest Playwright used existing saved test-account credentials without resetting
passwords or bypassing CAPTCHA. Results after service stabilization:

- Login GET200; zero OAuth links; CAPTCHA endpoint uses the new same origin.
- Password login redirects to the ts.net welcome page; authenticated profile200.
- Existing addicted-reservist/config project200, WEPP run-summary report200,
  browse200 and ron.nodb download200.
- Status WebSocket returned ping; preflight WebSocket returned preflight payload.
- Foreign-origin profile mutation without CSRF returned400.
- Forged Host attacker.invalid returned Caddy empty200, no body or cookies.
- Valid Host with :1234, forged X-Forwarded-Host and X-Forwarded-Port did not
  change the protected-route login redirect away from canonical HTTPS443.

Forest1: trusted TLS, no OAuth links, local form and same-origin CAPTCHA confirmed.
Real configuration reports ENABLE_LOCAL_LOGIN=True and all OAuth enabled flags False.
Authenticated local login awaits the operator's existing account verification;
forest test-account credentials do not match forest1's separate database.
Do not claim end-to-end forest1 acceptance until that verification completes.

## Incident during cutover

Redis/PostgreSQL port rebinding required recreation. Open login forms experienced
missing CSRF sessions, and web workers retained closed PostgreSQL connections,
causing intermittent POST/login500 after databases recovered. Operator reported
both symptoms. Restarted weppcloud on both hosts after database health recovered;
forest's full login/run/report/download/stream probes then passed. No credentials
or CSRF policy were changed. Operator confirmed login is now working.

## Review and validation status

Correctness review identified direct docker/.env reads in deploy-production.sh;
aligned host URLs there and in root .env. Correctness source checks pass. Security
and QA source reviews pass with no additional source changes required. Package
closeout remains open for forest1 authenticated acceptance and the separately
identified companion credential mismatch. All scoped docs lint and diff checks pass.
The operator also confirmed actual mail delivery from forest.


## Targeted wepp1 rollout — 2026-10-29 20:29 UTC

Operator explicitly authorized Caddy-only deployment while production jobs run.
Verified host wepp1 at /workdir/wepppy, baseline commit 0da9c9071. Applied only the
three-line Caddy sysctl addition in prod.yml and prod.wepp1.yml; did not pull
unrelated application changes or switch to homelab configuration. Host copies
before editing are in /tmp/docker-compose.*.yml.pre-mptcp-20261029.

Caddy has no build definition; reused the existing image
sha256:2ad4f81b9a44d531eff80b8d8c65c495c8a867648dc9a3e3720224d7418b3f90.
Caddy configuration and Compose parser passed before recreation. Executed:
`wctl docker compose up -d --no-deps --no-build --pull never --force-recreate caddy`.
The full deployment script has no Caddy-only mode; this bounded operation follows
the operator's explicit targeted-deployment instruction. No queue flush or prune.

New Caddy container 671b1a644caa started at 2026-10-29T20:29:00.206126789Z.
All 24 other container IDs, start timestamps and images match the saved baseline
(/tmp/wepppy-caddy-before-20261029.json on wepp1). Effective MPTCP sysctl 0 and
MPTCP/MPTCPv6 allocated sockets 0. Trusted HTTPS /health returned OK, login 200,
and active-job API 200. Five batch jobs were started and nine queued at cutover;
default and fork-archive had no started jobs. No worker restart occurred. All five previously started jobs remained started
with fresh heartbeats between 20:29:27 and 20:29:42 UTC after the cutover.

Tooling friction: installed wctl rq-info --detailed invokes an unsupported RQ flag
and also refreshes worker-registration indexes. Used direct Redis registry reads
for subsequent observation, avoiding registry cleanup or job mutations. A follow-up
should make this diagnostic genuinely read-only and support the installed RQ CLI.
