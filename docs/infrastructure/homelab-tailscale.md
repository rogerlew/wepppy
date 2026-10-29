# Homelab Tailscale access

## Access and authentication contract

The homelab WEPPcloud deployments use private Tailscale Serve HTTPS:

- forest: https://forest.tail305ec9.ts.net/weppcloud/
- forest1: https://forest1.tail305ec9.ts.net/weppcloud/

The operator selected local username/password login only on 2026-10-29. Disable
all OAuth providers while preserving accounts and password hashes. This avoids
external OAuth callback registration for private deployments. These are homelab
hosts; forest.moscowfsl.wsu.edu is a separate FSWEPP deployment.

Serve uses the existing tailscaled daemon and manages TLS certificates. Do not
enable Funnel. The operator owns removal of the old pfSense/DuckDNS proxy routes.
Unrelated applications on these machines are outside this WEPPcloud boundary.

## Host configuration

Keep these nonsecret settings in gitignored `docker/.env`. If root `.env` also
contains them, keep the values aligned: wctl gives root overrides precedence,
but `scripts/deploy-production.sh` reads some health/CAP URLs from `docker/.env`.

```dotenv
EXTERNAL_HOST=forest.tail305ec9.ts.net
OAUTH_REDIRECT_HOST=forest.tail305ec9.ts.net
ENABLE_LOCAL_LOGIN=true
CADDY_SITE_HOST=forest.tail305ec9.ts.net
CADDY_UPSTREAM_SCHEME=https
WEPPCLOUD_BIND_PREFIX=127.0.0.1:
REDIS_BIND_PREFIX=100.99.21.102:
CAP_BASE_URL=https://forest.tail305ec9.ts.net/cap
```

For forest1 substitute its hostname and use `REDIS_BIND_PREFIX=127.0.0.1:`.
Forest Redis retains authenticated access over its Tailscale address for companion
workers. Other published WEPPcloud ports bind to loopback. A bind prefix includes
the trailing colon; an unset prefix preserves existing IPv4/IPv6 publication.
Public deployment defaults are not switched to private access.

Set each recognized OAuth client-ID variable to an empty value:
`OAUTH_GITHUB_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENTID`,
`OAUTH_GOOGLE_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_ID`, `OAUTH_ORCID_CLIENT_ID`,
`ORCID_OAUTH_CLIENT_ID`, and `ORCID_OAUTH_CLIENTID`. Existing secret files can stay.
Update explicit public CAP asset/CORS, profile-playback and health URLs to the
same host; preserve internal service URLs.

The shared HTTP Caddyfile defaults to HTTP upstream scheme and no host matcher.
Homelab sets HTTPS metadata and an exact hostname only alongside loopback port
publication and Serve. It clears incoming forwarded-port metadata. No broad
trusted-proxy range or authentication bypass is introduced.

## Deploy and validate

Use the installed wctl dev preset on forest and prod preset on forest1. Existing
canonical deployment tooling remains authoritative; no alternative registry or
image workflow is needed. For initial privileged Serve setup:

```bash
sudo tailscale serve --bg http://127.0.0.1:8080
tailscale serve status
```

Validate rendered Compose configuration before applying changes. Inspect actual
container port bindings afterward: a Compose change alone does not alter an
existing container. Preserve images, identities, mounts, queues and unrelated
services. Check active jobs before restarting database dependencies.

If PostgreSQL is restarted, restart dependent web processes after it is healthy:
old connection pools can cause intermittent login HTTP 500 responses. Redis
restarts can invalidate open login forms; reload the login page for fresh CSRF
state. Never disable CSRF to repair this symptom.

Use the actual hostname and validate the health body:

```bash
curl -fsS https://forest.tail305ec9.ts.net/health
curl -fsS -H 'Host: forest.tail305ec9.ts.net' http://127.0.0.1:8080/health
```

Expected body is `OK`. An unmatched Host can receive Caddy's empty HTTP 200;
status alone does not prove application health. Check password login, authenticated
profile and existing runs, reports/downloads, stream connections, same-origin
redirects, missing/foreign-origin CSRF rejection, and absence of OAuth buttons.
Do not treat a login-page GET as successful authentication. Test forged Host and
forwarded headers; wrong host must not return application content or cookies.

## MPTCP mitigation and recovery

All five active Caddy Compose variants set `net.mptcp.enabled=0`. Recreate Caddy
to remove preexisting MPTCP sockets; host sysctls do not configure container network
namespaces. Independently inspect effective sysctls and socket counts.

On each host, `/etc/sysctl.d/90-disable-mptcp.conf` sets `net.mptcp.enabled = 0`.
Restart tailscaled after changing this setting to replace existing Serve sockets.
Other old MPTCP listeners can remain until their owning services restart. Kernel
patching is still required for CVE-2026-98432; this reduces the demonstrated attack
path and is not a complete kernel fix.

Initial host environment backups are under
`~/.local/state/wepppy-homelab-20261029/` with restricted permissions. Restore
only relevant host settings and recreate affected services if rollback is needed;
keep the MPTCP mitigation. Never overwrite unrelated source changes or flush RQ.

References: [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve),
[Caddy environment substitution](https://caddyserver.com/docs/caddyfile/concepts#environment-variables).
