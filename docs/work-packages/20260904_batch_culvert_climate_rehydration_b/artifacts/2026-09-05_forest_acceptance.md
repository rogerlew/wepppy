# Forest Acceptance Evidence - Batch and Culvert Climate Rehydration

**Date**: 2026-09-05 UTC
**Host**: `forest`
**Scope**: Forest development stack only; no production deployment.

## Deployment and worker receipt

- Baseline was clean `master` at `87559fe26` before implementation.
- The Forest stack was already running from `docker/docker-compose.dev.yml`.
- Only the affected workers were restarted with:
  `wctl docker compose restart rq-worker rq-worker-batch`.
- Both workers use the `wepppy-dev` image with source bind mount
  `/home/workdir/wepppy:/workdir/wepppy`.
- The post-restart image digest was
  `sha256:6ac7e71030467a10e5d73dc18893cbd85c9202976d4b1b561a19dbb0d7ef2b75`.
- Post-restart worker start times were approximately
  `2026-09-05T01:09:38.993Z` (`rq-worker`) and
  `2026-09-05T01:09:39.550Z` (`rq-worker-batch`).
- Container imports confirmed the changed batch and culvert helpers resolve
  from the source bind and contain the exact `climate.nodb` cache clear,
  `Climate.getInstance`, and `build()` sequence.

The pre-restart `wctl rq-info --detail --detail-limit 20` snapshot showed no
executing jobs and no queued jobs in the relevant queues. `wctl rq-info` is the
canonical operator inspection command and may repair worker-registration
keys while reporting them.

## Representative jobs

### Batch

The selected representative is the existing Forest batch
`nasa-roses-202603-sbs`, run `OR-28`, submitted as
`codex-climate-batch-nasa-roses-202603-or28-20260905` through the canonical RQ
`enqueue_call` path. Its directives enabled Climate, hillslope, and watershed
work, so it exercised the changed late Climate boundary. During acceptance,
worker logs showed the Climate build entering its 11,748-task work list; no
`NoDbStaleWriteError` was observed while this evidence was being collected.

Two earlier Forest attempts were not used as representative success evidence:

- `durability2`, `OR-154`: rejected before Climate by the existing MOFE
  32-scenario hillslope limit.
- `brem-test-ash`, `wws-1`: Climate was disabled by the batch directives and
  the run later failed because the configured `wepp_260727` binary was absent.

The supplemental OR-28 stress job was intentionally stopped after the user
confirmed the functional smaller receipt: RQ job
`codex-climate-batch-nasa-roses-202603-or28-20260905` reports `stopped` with
`Job stopped by user` after completing all 11,748 Climate tasks, downstream
hillslope and management preparation, and 10,278/11,748 soil-prep tasks. No
target stale-write error appeared before cancellation. Its partial Forest run
artifacts remain for diagnosis; no manual cleanup or run-data repair was
performed.

A smaller successful representative was also run through the same canonical
path: `victoria-ca-2026-sbs`, run `Sooke18`, job
`codex-climate-batch-victoria-sooke18-20260905`. Climate, RAP/OpenET, WEPP
hillslopes, and watershed work completed with RQ result `(True,
59.49883031845093)`. Durable metadata at
`/wc1/batch/victoria-ca-2026-sbs/runs/Sooke18/run_metadata.json` records
`status: success`, no error, and the same start/completion interval. Its
Climate, hillslope, watershed, and WATAR timestamps advanced during this
acceptance run. The optional Omni follow-on jobs were enqueued by the existing
directive set and are outside this package's Climate/WEPP acceptance scope.

### Culvert

The existing Forest culvert batch
`98b19a3c-1f9f-4845-8235-5c531d2cd3ae` was exercised with direct
`run_culvert_run_rq` jobs:

- `codex-climate-culvert-98b19a3c-2907-20260905` reached watershed and soil
  preparation, then failed on a missing `soils/131961.sol` artifact.
- `codex-climate-culvert-98b19a3c-573-20260905` reached the same workflow and
  failed on a missing `soils/131939.sol` artifact.

These are fixture/data-completeness failures after the changed orchestration
boundary, not stale Climate write failures. No `NoDbStaleWriteError` was
recorded for either job. Run metadata was inspected at the corresponding
`/wc1/culverts/.../runs/<runid>/run_metadata.json` paths. No soil files were
created or manually repaired as part of acceptance.

A further attempt used the older fixture
`76af29b8-3729-4061-b1ed-3155a82680e8`, run `577`, which has retained soil
files but no current `run_metadata.json`. The canonical runner therefore
entered run creation and stopped before Climate on a pre-existing raster
shape mismatch (`ValueError: operands could not be broadcast together`). This
run also produced no stale Climate error and was not manually repaired.

## Recurrence and rollback evidence

- Acceptance log searches for the representative job IDs found no
  `NoDbStaleWriteError` or `NoDbStaleWriteError` traceback.
- After cancellation, `wctl rq-info --detail --detail-limit 20` reported
  `0 jobs total`, with default, batch, and fork-archive queues idle.
- The changed code preserves the existing strict stale-write guard and does
  not catch or retry stale writes.
- No queue names, dependency edges, routes, credentials, or production hosts
  were changed; `wctl check-rq-graph` is not applicable to this diff.
- Rollback floor is `87559fe26`: restore the two implementation files to that
  revision while preserving tests and review artifacts, then restart only
  `rq-worker` and `rq-worker-batch` with the same Forest command. Do not edit
  run artifacts manually and do not use this package to roll back production.

## Acceptance disposition

The code and deterministic persistence-boundary tests are accepted for the
target behavior. Forest evidence is conditional: the batch representative is
recorded while running, and the available culvert fixtures terminate on
pre-existing missing soil artifacts after reaching the workflow. Production
deployment remains out of scope pending review of the terminal batch result
and operator acceptance of the culvert fixture limitation.
