# Production verification evidence

Full `wctl run-pytest tests --maxfail=1`: 8,194 passed, 77 skipped in 854.71 seconds.
Focused RQ/backends suite: 52 passed. Both independent reviews accepted the code
and the production permission-boundary evidence. Shell syntax and scoped docs
lint passed. The repair introduces no broad exception handler; an unrelated
concurrent worker edit tripped the shared changed-file exception inventory.

September 10, 2026 UTC. Isolated canary copies use actual production mounts and
worker identities. Original project data was not changed by these checks.

## Owner-only fresh render on wepp1

    CANARY_RESULT {"uid": 1002, "gid": 130, "input_mode": "0600", "input_unchanged": true, "output": "/wc1/runs/de/deval-permissions-canary-20260910/export/WEPPcloudR/deval_deval-permissions-canary-20260910.htm", "output_bytes": 13494027}

## Regenerated input and absent export

    CANARY_RESULT {"regenerated_soils": "passed", "dataframe_unchanged": true, "input_mode": "0644", "absent_export": "created", "output_bytes": 13494033}

## Queued replacement render

    QUEUED_CANARY {"job_id": "deb10627-1fbd-48d7-87e3-55fcc3ab1283", "prior_output_mtime_ns": 1789014055394599000, "input_mode": "0600"}

## Canonical RQ completion

    {"job_id": "deb10627-1fbd-48d7-87e3-55fcc3ab1283", "status": "finished", "result": "/wc1/runs/de/deval-permissions-canary-20260910/export/WEPPcloudR/deval_deval-permissions-canary-20260910.htm", "ended_at_utc": "2026-09-10 04:22:21.694667", "worker": "bc149e8eec534a2b83d57c48a6540295", "input_mode": "0o600"}

## Authenticated Flask route readback

    ROUTE_READBACK {"status": 200, "bytes": 13494023, "sha256": "a2e5361a5ae3c42ffe0796453e42b1a3633f0d7c5a6ebc8e5c61f5dd17aa75f5", "artifact_match": true}

## Owner-only fresh render on wepp2

    CANARY_RESULT {"uid": 1002, "gid": 130, "input_mode": "0600", "input_unchanged": true, "output": "/wc1/runs/de/deval-permissions-canary-20260910/export/WEPPcloudR/deval_deval-permissions-canary-20260910.htm", "output_bytes": 13494036}

## Real image preflight

    weppcloudr-runtime-contract: owner-only data sharing passed as 1002:130
    weppcloudr-runtime-contract: compatible image=sha256:925dd175ef04ae944b141f07a3c7e677ae3690e0b28630d908ef6393d757fbc4

The route check used the deployed Flask application with an existing active Root
identity held only inside the process. It did not export credentials or create an
account, and does not claim a browser/Gunicorn roundtrip. Source-copy NoDb warnings
were expected; assertions verified writes stayed inside the canary copy.

Default and batch worker modules on wepp1 and wepp2 were atomically patched with
timestamped backups. SHA256: `bc315d790ca421f265c0cbcdf26fd3a8b8ac07d812697aa84f989337ca5c9b85`.
Worker container start times remained unchanged: wepp1 September 10 02:27:20 UTC;
wepp2 September 10 03:13:19 UTC. The earlier image remains unchanged; supported
deployment rebuilds the fixed repository source before recreating containers.
