# Diagnostic smoke specs (manual only)
These Playwright specs are deep-dive diagnostics for deck.gl map debugging.
They are skipped by default.

Run a single spec:
```bash
SMOKE_DIAGNOSTICS=1 MAP_GL_URL="https://wc.bearhive.duckdns.org/weppcloud/runs/<runid>/<config>/" \
  wctl run-npm smoke -- diagnostics/check-layer-identity.spec.js
```

Notes:
- Set `SMOKE_DIAGNOSTICS=1` to enable.
- Prefer `MAP_GL_URL` or `SMOKE_RUN_PATH` to target a specific run.
