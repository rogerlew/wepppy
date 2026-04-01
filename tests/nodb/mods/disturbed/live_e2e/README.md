# Disturbed Lookup Live E2E Runbook

## One-Command Live Execution

Run from `/workdir/wepppy`:

```bash
DISTURBED_LOOKUP_LIVE_E2E=1 \
wctl run-pytest tests/nodb/mods/disturbed/test_disturbed_lookup_live_e2e.py \
  -m "requires_network and integration" \
  --live-disturbed-lookup-e2e \
  --maxfail=1 -s
```

Evidence artifacts are written inside the container to:

- `/tmp/wepppy-disturbed-lookup-live-e2e/<run_label>_<timestamp>/evidence.json`
- `/tmp/wepppy-disturbed-lookup-live-e2e/<run_label>_<timestamp>/evidence.md`

## Auth Contract

The live harness uses runtime `dev-agent` authentication and does not rely on
`/home/roger/weppcloud-dev-token.txt`.

Credential source:

- `docker/secrets/dev-agent.env` with `DEV_AGENT_EMAIL` and `DEV_AGENT_PASSWORD`
- Override path with `DISTURBED_LOOKUP_LIVE_E2E_DEV_AGENT_CREDENTIALS_FILE`

Runtime flow:

1. `GET /weppcloud/login` and extract CSRF token.
2. `POST /weppcloud/login` with `DEV_AGENT_EMAIL` and `DEV_AGENT_PASSWORD`.
3. `GET /weppcloud/profile` and extract CSRF token.
4. `POST /weppcloud/profile/mint-token` with `X-CSRFToken`.
5. Use minted bearer token for `/rq-engine/api/runs/{runid}/{config}/session-token` calls.

The endpoint transcript in evidence redacts login form fields and never stores
credential values or minted token strings.
