# WEPPcloud web runtime contract

This is the canonical startup and secret inventory for the WEPPcloud web
process. It applies to Docker Compose and Kubernetes. Deployment-specific
documents may add configuration, but they must not silently weaken or replace
this contract.

The Kubernetes deployment is greenfield. Existing production Compose
deployments on `wepp1`, `wepp2`, and `wepp3` remain independent and must keep
their current defaults unless a separate production change explicitly says
otherwise.

## Process contract

The common image has no `ENTRYPOINT`. Its Dockerfile `CMD`, or an explicit
orchestrator command override, starts Gunicorn serving
`wepppy.weppcloud.app:app` on port `8000`. The deployed Kubernetes digest was
inspected to confirm the non-root `roger` user, `/workdir/wepppy` working
directory, Gunicorn executable, and expected vendored compatibility path.

`docker/weppcloud-entrypoint.sh` exists for Compose-specific workflows but is
not wired into the common image and must not be assumed to run in Kubernetes.
Any preflight needed by Kubernetes must be explicit in image build validation,
an init container, or the workload command rather than relying on that script.

The production image default is four workers, two threads, and a 1,800-second
timeout. A resource-bounded canary may override that to one worker, two threads,
and a 120-second timeout without changing the image or Compose defaults:

```text
gunicorn --workers 1 --threads 2 --timeout 120 \
  --bind 0.0.0.0:8000 --log-level info wepppy.weppcloud.app:app
```

Use `GET /health` for container readiness and liveness. A gateway may expose the
application under `SITE_PREFIX`, but it must strip the prefix before proxying and
set `X-Forwarded-Prefix`, matching the current Caddy behavior. Kubernetes will
move proven routes incrementally to Traefik/Gateway API; Caddy is a temporary
compatibility layer, not the target public ingress.

## Minimum web-only configuration

These values are sufficient for a web-only canary with local login and optional
integrations disabled. Example values are non-secret and illustrative.

| Name | Example | Required | Purpose |
| --- | --- | --- | --- |
| `SITE_PREFIX` | `/weppcloud` | Yes for prefixed route | Flask application root and generated URLs |
| `WC1_DIR` | `/wc1` | Yes | Writable WEPPcloud run root |
| `GEODATA_DIR` | `/geodata` | Yes | Read-only shared reference data root |
| `POSTGRES_HOST` | `postgres-01.openwepp.arpa` | Yes | External PostgreSQL host |
| `POSTGRES_PORT` | `5432` | Yes | External PostgreSQL port |
| `POSTGRES_DB` | `wepppy` | Yes | Database name |
| `POSTGRES_USER` | `wepppy` | Yes | Database role |
| `REDIS_HOST` | `redis.weppcloud.svc.cluster.local` | Yes | Redis Service name |
| `REDIS_PORT` | `6379` | Yes | Redis port |
| `SESSION_REDIS_DB` | `11` | Recommended | Flask session database |
| `ENABLE_LOCAL_LOGIN` | `false` | Canary choice | Disable user/password login until intentionally tested |
| `GL_DASHBOARD_BATCH_ENABLED` | `false` | Canary choice | Avoid worker-dependent dashboard jobs |
| `PYTHONUNBUFFERED` | `1` | Recommended | Immediate container logs |
| `MPLCONFIGDIR` | `/tmp/matplotlib` | Recommended | Writable Matplotlib cache |

Do not set `SQLALCHEMY_DATABASE_URI` or `DATABASE_URL` for this deployment.
`wepppy.weppcloud.configuration` composes the URI from the non-secret PostgreSQL
fields and `POSTGRES_PASSWORD_FILE`, preventing the password from appearing in
an environment variable. Likewise, use host/port plus `REDIS_PASSWORD_FILE`
instead of a credential-bearing Redis URL.

## Minimum secret inventory

The application secret loader prefers `<NAME>_FILE`, fails closed for an
unreadable or empty configured file, and falls back to `<NAME>` only for
backward compatibility. New deployments must mount files and expose only file
paths in the environment.

| Secret ID | File variable | Required for web canary | Notes |
| --- | --- | --- | --- |
| `flask_secret_key` | `SECRET_KEY_FILE` | Yes | Flask session signing; generate a canary value |
| `flask_security_password_salt` | `SECURITY_PASSWORD_SALT_FILE` | Yes | Flask-Security hashing; generate a canary value |
| `postgres_password` | `POSTGRES_PASSWORD_FILE` | Yes | Reuse the scoped `wepppy` database credential |
| `redis_password` | `REDIS_PASSWORD_FILE` | Yes | Generate for the canary Redis instance |
| `agent_jwt_secret` | `AGENT_JWT_SECRET_FILE` | Recommended | Keep agent tokens distinct from the Flask key even though code can fall back to it |

No real Discord token is required for the web canary. A vendored module still
opens `/workdir/weppcloud2/weppcloud2/discord_bot/.bot_token` during import.
Mount an empty non-secret file at that path until the import-time coupling is
removed. Never substitute a production Discord credential merely to satisfy
startup.

The following secrets are intentionally absent until their corresponding
feature is enabled and tested: OAuth provider secrets, Zoho SMTP password, CAP
secret, WEPP auth JWT set, MCP JWT secret, D-Tale token, administrator password,
OpenTopography key, Climate Engine key, OpenET key, and `WC_TOKEN`. The complete
cross-service inventory remains in [secrets.md](secrets.md).

## Kubernetes example

The example shows the interface, not deployable secret values. The real Secret
must be SOPS-encrypted in Git, and the names must match the rendered manifests.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: weppcloud-web-runtime
  namespace: weppcloud
type: Opaque
stringData:
  flask_secret_key: REPLACE_THROUGH_SOPS
  flask_security_password_salt: REPLACE_THROUGH_SOPS
  postgres_password: REUSE_THROUGH_SOPS
  redis_password: REPLACE_THROUGH_SOPS
  agent_jwt_secret: REPLACE_THROUGH_SOPS
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: weppcloud-web
  namespace: weppcloud
spec:
  template:
    spec:
      automountServiceAccountToken: false
      containers:
        - name: web
          image: ghcr.io/rogerlew/wepppy@sha256:REPLACE_WITH_REVIEWED_DIGEST
          args:
            - gunicorn
            - --workers
            - "1"
            - --threads
            - "2"
            - --timeout
            - "120"
            - --bind
            - 0.0.0.0:8000
            - --log-level
            - info
            - wepppy.weppcloud.app:app
          env:
            - {name: SITE_PREFIX, value: /weppcloud}
            - {name: POSTGRES_HOST, value: postgres-01.openwepp.arpa}
            - {name: POSTGRES_DB, value: wepppy}
            - {name: POSTGRES_USER, value: wepppy}
            - {name: REDIS_HOST, value: redis.weppcloud.svc.cluster.local}
            - {name: SECRET_KEY_FILE, value: /run/secrets/weppcloud/flask_secret_key}
            - {name: SECURITY_PASSWORD_SALT_FILE, value: /run/secrets/weppcloud/flask_security_password_salt}
            - {name: POSTGRES_PASSWORD_FILE, value: /run/secrets/weppcloud/postgres_password}
            - {name: REDIS_PASSWORD_FILE, value: /run/secrets/weppcloud/redis_password}
            - {name: AGENT_JWT_SECRET_FILE, value: /run/secrets/weppcloud/agent_jwt_secret}
          volumeMounts:
            - name: runtime-secrets
              mountPath: /run/secrets/weppcloud
              readOnly: true
      volumes:
        - name: runtime-secrets
          secret:
            secretName: weppcloud-web-runtime
            defaultMode: 0400
```

The final deployment must also mount `/wc1`, `/geodata`, and the empty Discord
compatibility file; define startup/readiness/liveness probes; run as the image's
non-root UID/GID; and apply resource limits and NetworkPolicies. Those concerns
belong in the environment manifests, not in the secret object.

## Startup acceptance checklist

1. Pin the image by immutable digest and verify anonymous GHCR pull.
2. Confirm each required secret file exists, is non-empty, and is not printed by
   rendered YAML, process arguments, logs, or pod environment output.
3. Confirm PostgreSQL is reachable only from the observed canary source and a
   transaction can be rolled back.
4. Confirm authenticated Redis connectivity and session DB isolation.
5. Confirm `/wc1` is writable, `/geodata` is readable and not writable, and the
   Discord compatibility path contains no credential.
6. Confirm direct `/health` and the private prefixed route succeed.
7. Confirm no RQ worker, Docker socket, public route, or production Compose
   mutation is present.

## Implementation references

- `wepppy/weppcloud/configuration.py` — Flask, PostgreSQL, and session startup
- `wepppy/config/secrets.py` — canonical `*_FILE` resolution behavior
- `wepppy/config/redis_settings.py` — Redis URL construction and password injection
- `docker/Dockerfile` — common image startup contract
- `docker/weppcloud-entrypoint.sh` — optional Compose workflow helper, not the
  common image entrypoint
- `docker/docker-compose.canary-smoke.yml` — isolated compatibility evidence
- `docs/infrastructure/secrets.md` — full multi-service secret catalog
