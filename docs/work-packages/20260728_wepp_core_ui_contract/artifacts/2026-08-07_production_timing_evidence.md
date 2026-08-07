# Production Timing Evidence - WEPP Prep Completion

**Captured**: 2026-08-07 UTC
**Host**: `wepp1`
**Run path**: `/geodata/wc1/runs/do/door-to-door-salad`

## Original Failure

RQ job `9636f1fd-3475-4b32-9216-65a7324c9d80` ran
`wepppy.rq.wepp_rq._log_prep_complete_rq` with timeout 180. Redis recorded:

    started_at = 2026-08-07 03:02:09.434231 UTC
    ended_at   = 2026-08-07 03:05:09.661254 UTC
    status     = failed
    exception  = rq.timeouts.JobTimeoutException:
                 Task exceeded maximum timeout value (180 seconds)

## Measurement Method

Codex staged `/tmp/measure_door_bootstrap.py`, copied it into the production
`rq-worker` container, and ran it with the production source and environment.
The script contained no credentials. Its effective operation was:

    lock = acquire_bootstrap_git_lock(
        lock_redis,
        runid="door-to-door-salad",
        operation="auto_commit_timing_recovery",
        actor="codex:operator",
        ttl_seconds=14_400,
    )
    started = time.time()
    sha = Wepp.getInstance(get_wd(runid)).bootstrap_commit_inputs(
        "WEPP prep-only pipeline timing recovery"
    )
    ended = time.time()
    released = release_bootstrap_git_lock(..., token=lock.token)

The container emitted this result:

    {
      "elapsed_seconds": 1234.1167397499084,
      "ended_epoch": 1786078598.659138,
      "lock_released": true,
      "runid": "door-to-door-salad",
      "sha": "1e7fb6b5d031171042f92211b4fdc28c8f6782cf",
      "started_epoch": 1786077364.5423982,
      "status": "complete"
    }

The UTC interval was 2026-08-07 04:36:04.542398 through
04:56:38.659138. The run logger recorded:

    Bootstrap auto-commit created 1e7fb6b for
    WEPP prep-only pipeline timing recovery

## Post-Operation Verification

Independent read-only verification at 2026-08-07 05:05 UTC confirmed:

- commit `1e7fb6b5d031171042f92211b4fdc28c8f6782cf` exists with subject
  `Pipeline: rebuilt WEPP prep-only pipeline timing recovery`;
- the commit time is 2026-08-07 04:50:20 UTC;
- the run-scoped bootstrap lock is absent after token-owned release;
- the original RQ job remains failed at its historical 180-second boundary.

The temporary script and timing-output files were removed after capture.
