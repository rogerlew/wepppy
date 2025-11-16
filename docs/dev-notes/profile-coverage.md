# Profile Coverage Quick-Start

> How to execute a profile playback run with coverage tracing enabled and capture the resulting artifact.

## 1. Prepare the stack

1. Copy `docker/.env` to a throwaway overlay (this keeps secrets in one place) and enable coverage:

   ```bash
   cp docker/.env docker/.env.coverage
   printf 'ENABLE_PROFILE_COVERAGE=1\n' >> docker/.env.coverage
   ```

2. Restart `weppcloud` with the overlay so the container reads the flag (note that the compose file lives under `docker/`, so the env file path is relative to that directory):

   ```bash
   WEPPPY_ENV_FILE=.env.coverage \
     docker compose -f docker/docker-compose.dev.yml up -d weppcloud
   ```

3. Verify the container picked up the toggle:

   ```bash
   docker exec weppcloud env | grep ENABLE_PROFILE_COVERAGE
   # ENABLE_PROFILE_COVERAGE=1
   ```

Leave the playback service (`profile-playback`) running as-is; it will inject the `X-Profile-Trace` header and reuse whatever base URL and credentials you already configured in `docker/.env`.

> **Cleanup:** After you finish collecting coverage runs, restart `weppcloud` with `WEPPPY_ENV_FILE=.env` (the default) and delete the overlay file so local changes do not linger.

## 2. Run a traced profile

Execute the playback via `wctl` from the repository root. **Default artifact path:** `/workdir/wepppy-test-engine-data/coverage/<slug>.coverage` (shared bind mount used by weppcloud + workers). `--coverage-dir` is optional and only needed when you want a second copy inside the playback container. Sample command for the `legacy-palouse` profile:

```bash
cd /home/workdir/wepppy
wctl run-test-profile legacy-palouse \
    --trace-code \
    --coverage-dir /tmp/profile-coverage \
    --service-url http://127.0.0.1:8070 \
    --base-url https://wc.bearhive.duckdns.org/weppcloud
```

Key expectations:

- The playback stream shows normal HTTP activity followed by `Profile coverage saved to /tmp/profile-coverage/legacy-palouse.coverage`.
- `/home/workdir/wepppy-test-engine-data/profiles/_runs/<token>.json` contains the run summary (run id, sandbox id, request log).
- `/home/workdir/wepppy-test-engine-data/coverage` fills with `legacy-palouse.coverage.*` shards emitted by the Flask workers/RQ tasks, and the merged `/home/workdir/wepppy-test-engine-data/coverage/legacy-palouse.coverage` file.

If you need to run every profile back-to-back, the helper command does the globbing, header injection, and shard consolidation for you:

```bash
wctl run-profile-coverage-batch \
    --include legacy-palouse us-small-wbt-daymet-rap-wepp \
    --service-url http://127.0.0.1:8070 \
    --base-url https://wc.bearhive.duckdns.org/weppcloud \
    --dry-run  # drop this flag to execute for real
```

The batch runner skips directories without `capture/events.jsonl`, cleans existing shards, runs playback for each slug, and writes merged artifacts to `docs/work-packages/20251109_profile_playback_coverage/artifacts/<slug>.coverage`.

If playback dies early (502/500), check:

- `profile-playback` logs for authentication failures or permission errors when creating the requested `--coverage-dir`.
- `weppcloud` logs for coverage init errors (for example, forgetting to restart with `ENABLE_PROFILE_COVERAGE=1`).

## 3. Combine and archive the coverage data

1. Combine the shards inside the `weppcloud` container—the CLI needs to see the generated files, so run the command from that container:

   ```bash
   docker exec -u 1000 weppcloud \
     sh -c "cd /workdir/wepppy-test-engine-data/coverage && \
            /opt/venv/bin/coverage combine legacy-palouse.coverage.*"
   ```

   This produces `/workdir/wepppy-test-engine-data/coverage/.coverage`.

2. Copy the merged file into the work-package artifacts directory (rename it with the profile slug as a reminder):

   ```bash
   cp /home/workdir/wepppy-test-engine-data/coverage/.coverage \
      docs/work-packages/20251109_profile_playback_coverage/artifacts/legacy-palouse.coverage
   ```

3. (Optional) Remove the intermediate shards from the shared data volume once you have confirmed the `.coverage` file exists.

## Current instrumentation notes (2025-11-15)

- Coverage 7.11.3 is required; `coverage.py` is imported directly in weppcloud, rq-worker, and profile-playback. Import will fail fast if missing.
- `X-Profile-Trace: <slug>` header activates tracing per request. Logs now show header detection, coverage start (slug/data_file/context), job tagging, and worker coverage startup to make debugging loss of the slug straightforward.
- Default data root: `/workdir/wepppy-test-engine-data/coverage` (set via `PROFILE_COVERAGE_DIR` / `ENABLE_PROFILE_COVERAGE=1`).
- `--coverage-dir` simply mirrors the merged artifact into a path inside the playback container; it no longer affects where shards are written.
- `coverage.profile-playback.ini` intentionally omits the `source` setting to avoid filtering out traced files; `relative_files=True` plus the omit list is sufficient for profile runs.

## 4. Notes & troubleshooting

- The playback service runs as a different user inside its container. Any `--coverage-dir` outside `/tmp` typically fails with `Permission denied: '/home/workdir'`. Always target `/tmp` (or another writable path inside the container) and let the real coverage artifacts live under `/workdir/wepppy-test-engine-data/coverage` on the WEPPcloud side.
- Coverage requires `coverage.py >= 7.0`. The project currently pins 7.11.3; older versions reject the `data_suffix` argument.
- RQ worker coverage uses the same slug: if you see orphaned `.coverage.<pid>` shards, make sure the worker restarted after you set `ENABLE_PROFILE_COVERAGE=1`.
- For repeatability, record the exact `wctl` command, timestamp, run token, and the path to the combined `.coverage` file in the work-package tracker (`docs/work-packages/20251109_profile_playback_coverage/tracker.md`).
