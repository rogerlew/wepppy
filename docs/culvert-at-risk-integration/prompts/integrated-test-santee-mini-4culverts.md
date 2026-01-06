## Integrated Culvert Batch Test (santee_mini_4culverts)

Goal: Run a full culvert batch submission using the real payload at
`tests/culverts/test_payloads/santee_mini_4culverts/payload.zip`, then
work through any errors to move the culvert runner toward production readiness.
Use HTTPS and a 20-minute timeout.

### Environment
- Repo: `/workdir/wepppy`
- Host: `wc.bearhive.duckdns.org` (HTTPS required)
- Script: `docs/culvert-at-risk-integration/dev-package/scripts/submit_payload.py`
- Payload: `tests/culverts/test_payloads/santee_mini_4culverts/payload.zip`
- Timeout: 1200 seconds (20 minutes)

### Steps
1) Sanity checks
```
ls -lh tests/culverts/test_payloads/santee_mini_4culverts/payload.zip
wctl ps
```

2) Submit payload (inside weppcloud container + venv)
```
wctl exec weppcloud bash -lc "source /opt/venv/bin/activate && \
  WEPPCLOUD_HOST=wc.bearhive.duckdns.org \
  python docs/culvert-at-risk-integration/dev-package/scripts/submit_payload.py \
  --payload tests/culverts/test_payloads/santee_mini_4culverts/payload.zip \
  --timeout-seconds 1200 --poll-seconds 5"
```

3) Capture key outputs
- job_id, culvert_batch_uuid, status_url, final status, browse URL.

4) If it fails or stalls, collect logs
```
wctl logs -f rq-worker-batch
wctl logs -f rq-engine
wctl logs -f weppcloud
```

5) Inspect batch results on disk
```
ls -la /wc1/culverts/<culvert_batch_uuid>/
rg -n "status|error" /wc1/culverts/<culvert_batch_uuid>/runs/*/run_metadata.json
```

6) If errors occur, diagnose and fix
- Trace the failing phase from `run_metadata.json` + logs.
- Patch code as needed, rerun the same payload, and report deltas.

### Deliverable
- Summary of the run (success/failure, durations, counts).
- Any fixes applied (files + rationale).
- Confirmation that results are browseable or reasons why not.
