# Playwright Smoke AGENTS Guide
> Local playbook for UI smoke tests, CAP-gate bypass accounts, and credential handling.

## Scope
- Applies to files under `wepppy/weppcloud/static-src/tests/smoke/`.
- Use this guide when maintaining smoke tests that need authenticated sessions (notably axe runs against CAP-gated pages).

## Canonical Agent Account
- Primary account label: `dev-agent`
- Preferred email: `dev-agent@example.com` (local/dev convention)
- Required capabilities:
  - active user account
  - roles: `User`, `Admin`, `Root`, `PowerUser`
  - valid password-based login

## Credential Storage (Gitignored)
- Preferred credentials file used by smoke/axe:
  - `docker/secrets/dev-agent.env`
- Expected keys in `dev-agent.env`:
  - `DEV_AGENT_EMAIL`
  - `DEV_AGENT_PASSWORD`
  - `SMOKE_AGENT_EMAIL` (same value as `DEV_AGENT_EMAIL`)
  - `SMOKE_AGENT_PASSWORD` (same value as `DEV_AGENT_PASSWORD`)
- Legacy compatibility file (still supported):
  - `docker/secrets/ally-agent-smoke.env`
- File hygiene:
  - `chmod 600 docker/secrets/dev-agent.env`
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
cat > docker/secrets/dev-agent.env <<EOF
DEV_AGENT_EMAIL=dev-agent@example.com
DEV_AGENT_PASSWORD=${AGENT_PASSWORD}
SMOKE_AGENT_EMAIL=dev-agent@example.com
SMOKE_AGENT_PASSWORD=${AGENT_PASSWORD}
EOF
chmod 600 docker/secrets/dev-agent.env
```

2. Create/update the user in the local WEPPcloud DB:
```bash
wctl exec weppcloud python - <<'PY'
from datetime import datetime
from pathlib import Path

from flask_security.utils import hash_password
from wepppy.weppcloud.app import app, db, Role, user_datastore

secrets_path = Path('/workdir/wepppy/docker/secrets/dev-agent.env')
pairs = {}
for line in secrets_path.read_text(encoding='utf-8').splitlines():
    text = line.strip()
    if not text or text.startswith('#') or '=' not in text:
        continue
    key, value = text.split('=', 1)
    pairs[key.strip()] = value.strip().strip('"').strip("'")

email = (pairs.get("DEV_AGENT_EMAIL") or "").strip().lower()
password = pairs.get("DEV_AGENT_PASSWORD") or ""
required_roles = ("User", "Admin", "Root", "PowerUser")

if not email or not password:
    raise SystemExit("DEV_AGENT_EMAIL/DEV_AGENT_PASSWORD are required in dev-agent.env")

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

    for role_name in required_roles:
        role = Role.query.filter_by(name=role_name).first()
        if role is None:
            role = Role(name=role_name, description=f"Auto-provisioned role {role_name}")
            db.session.add(role)
            db.session.commit()
            print(f"created role {role_name}")
        if role not in user.roles:
            user.roles.append(role)
            print(f"assigned role {role_name}")

    db.session.commit()
    final_roles = sorted({r.name for r in user.roles})
    print(f"dev-agent ready roles={','.join(final_roles)}")
PY
```

## Using Stored Credentials in Smoke/Axe
- The axe suite auto-loads `docker/secrets/dev-agent.env` first.
- If `dev-agent.env` is absent, it falls back to `docker/secrets/ally-agent-smoke.env`.
- Override location when needed:
  - `SMOKE_AGENT_CREDENTIALS_FILE=/path/to/agent.env`
- Enforce auth presence in CI/manual runs:
  - `SMOKE_AGENT_REQUIRED=true`

Example:
```bash
SMOKE_BASE_URL=https://wc.bearhive.duckdns.org \
SMOKE_SITE_PREFIX=/weppcloud \
SMOKE_AGENT_ACCOUNT_LABEL=dev-agent \
SMOKE_AGENT_REQUIRED=true \
wctl run-playwright --suite full --grep "axe accessibility" --workers 1
```

## Using `dev-agent` for CAP-Guarded Endpoints
- CAP gating applies to anonymous sessions on protected routes.
- `dev-agent` is the intended authenticated path for automated smoke work. The
  login form itself may render Cap.js; browser smoke helpers should solve the
  login-page CAP prompt when `input[name="cap_token"]` is present before
  submitting credentials.
- Typical sequence:
  - login to `/weppcloud/login` with stored credentials and a solved Cap.js token
    when the login page requires one
  - request a protected run route (or use `/weppcloud/tests/api/create-run` in smoke flows)
  - verify `#cap-gate` is absent before continuing assertions

## Using `dev-agent` for RQ-Engine API
- For agent/API work, mint a bearer token from the authenticated profile route:
  - `POST /weppcloud/profile/mint-token` (cookie session + CSRF header)
- Use returned token against `/rq-engine/api/*`.
- `dev-agent` includes `Admin`/`Root`, so admin debug routes are available:
  - `GET /rq-engine/api/admin/recently-completed-jobs`
  - `GET /rq-engine/api/admin/jobs-detail`
- Role/scopes baseline from `/profile/mint-token`:
  - scopes include `rq:status`, `rq:enqueue`, `rq:export`
  - audience includes `rq-engine`

Quick verification command (login -> mint token -> rq-engine admin endpoint):
```bash
python3 - <<'PY'
import json
import re
from pathlib import Path
import requests

host = "https://wc.bearhive.duckdns.org"
base = f"{host}/weppcloud"
rq_base = f"{host}/rq-engine"

pairs = {}
for line in Path("docker/secrets/dev-agent.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        key, value = line.split("=", 1)
        pairs[key.strip()] = value.strip()

email = pairs["DEV_AGENT_EMAIL"]
password = pairs["DEV_AGENT_PASSWORD"]
s = requests.Session()

login = s.get(f"{base}/login", timeout=30)
if 'name="cap_token"' in login.text:
    raise SystemExit("Login page requires Cap.js. Use Playwright/browser smoke login so the widget can solve the challenge.")
csrf = re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', login.text, re.I).group(1)
s.post(f"{base}/login", data={"email": email, "password": password, "remember": "y", "csrf_token": csrf}, timeout=30).raise_for_status()

profile = s.get(f"{base}/profile", timeout=30)
profile_csrf = re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', profile.text, re.I).group(1)
mint = s.post(f"{base}/profile/mint-token", headers={"X-CSRFToken": profile_csrf}, timeout=30)
mint.raise_for_status()
payload = mint.json()
token = (payload.get("Content") or payload.get("content") or payload.get("success") or {}).get("token")
if not token:
    raise SystemExit(f"token missing: {json.dumps(payload)[:240]}")

admin = s.get(
    f"{rq_base}/api/admin/recently-completed-jobs",
    params={"lookback_minutes": 5},
    headers={"Authorization": f"Bearer {token}"},
    timeout=30,
)
admin.raise_for_status()
print("rq-engine dev-agent check passed")
PY
```

## Shared/CI Environments
- Do not rely on local `docker/secrets/*` on GitHub Actions runners.
- Provide credentials via secret manager / CI secrets:
  - `DEV_AGENT_EMAIL`
  - `DEV_AGENT_PASSWORD`
  - `ALLY_AGENT_EMAIL`
  - `ALLY_AGENT_PASSWORD`
  - `SMOKE_AGENT_EMAIL`
  - `SMOKE_AGENT_PASSWORD`
- Keep account names stable so smoke suites and docs do not drift.
