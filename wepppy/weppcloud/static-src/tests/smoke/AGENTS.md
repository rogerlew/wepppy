# Playwright Smoke AGENTS Guide
> Local playbook for UI smoke tests, CAP-gate bypass accounts, and credential handling.

## Scope
- Applies to files under `wepppy/weppcloud/static-src/tests/smoke/`.
- Use this guide when maintaining smoke tests that need authenticated sessions (notably axe runs against CAP-gated pages).

## Canonical Agent Account
- Primary account label: `ally-agent`
- Preferred email: `ally-agent@example.com` (local/dev convention)
- Required capabilities:
  - active user account
  - `User` role assigned
  - valid password-based login

## Credential Storage (Gitignored)
- Default credentials file used by axe suite:
  - `docker/secrets/ally-agent-smoke.env`
- Expected keys:
  - `ALLY_AGENT_EMAIL`
  - `ALLY_AGENT_PASSWORD`
- File hygiene:
  - `chmod 600 docker/secrets/ally-agent-smoke.env`
  - never commit credential values
  - keep secrets in `docker/secrets/*` or runtime env only

## Account Provisioning (Local Dev, Idempotent)
1. Generate a password and store credentials locally:
```bash
AGENT_PASSWORD="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
cat > docker/secrets/ally-agent-smoke.env <<EOF
ALLY_AGENT_EMAIL=ally-agent@example.com
ALLY_AGENT_PASSWORD=${AGENT_PASSWORD}
EOF
chmod 600 docker/secrets/ally-agent-smoke.env
```

2. Create/update the user in the local WEPPcloud DB:
```bash
AGENT_EMAIL=ally-agent@example.com \
AGENT_PASSWORD="${AGENT_PASSWORD}" \
wctl exec weppcloud python - <<'PY'
from datetime import datetime
import os

from flask_security.utils import hash_password
from wepppy.weppcloud.app import app, db, Role, user_datastore

email = os.environ["AGENT_EMAIL"].strip().lower()
password = os.environ["AGENT_PASSWORD"]

with app.app_context():
    user = user_datastore.find_user(email=email)
    if user is None:
        user = user_datastore.create_user(
            email=email,
            first_name="Ally",
            last_name="Agent",
            active=True,
            confirmed_at=datetime.utcnow(),
            password=hash_password(password),
        )
        print(f"created user {email}")
    else:
        user.password = hash_password(password)
        user.active = True
        print(f"updated user {email}")

    role = Role.query.filter_by(name="User").first()
    if role is None:
        role = Role(name="User", description="Default authenticated user role")
        db.session.add(role)
        db.session.commit()
        print("created role User")

    if role not in user.roles:
        user.roles.append(role)

    db.session.commit()
    print("agent account ready")
PY
```

## Using Stored Credentials in Smoke/Axe
- The axe suite auto-loads `docker/secrets/ally-agent-smoke.env`.
- Override location when needed:
  - `SMOKE_AGENT_CREDENTIALS_FILE=/path/to/agent.env`
- Enforce auth presence in CI/manual runs:
  - `SMOKE_AGENT_REQUIRED=true`

Example:
```bash
SMOKE_BASE_URL=https://wc.bearhive.duckdns.org \
SMOKE_SITE_PREFIX=/weppcloud \
SMOKE_AGENT_REQUIRED=true \
wctl run-playwright --suite full --grep "axe accessibility" --workers 1
```

## Shared/CI Environments
- Do not rely on local `docker/secrets/*` on GitHub Actions runners.
- Provide credentials via secret manager / CI secrets:
  - `ALLY_AGENT_EMAIL`
  - `ALLY_AGENT_PASSWORD`
- Keep account names stable so smoke suites and docs do not drift.

