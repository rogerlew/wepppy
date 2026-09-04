# Forest Deployment and Acceptance Evidence

## Candidate and bounded deployment

- Host: `forest`
- Checkout: `/workdir/wepppy`
- Contract checkpoint/rollback SHA: `8434ecb88aeb2f7073cebf03188c78e3e2cf0900`
- Candidate SHA: `f2dc2349810c5eff62c9543ad7a86239991166ca`
- Immediate preflight: default, batch, and fork-archive queues had zero queued
  or executing jobs.
- Recreated services only: `weppcloud`, `rq-engine`, `rq-worker`, and
  `rq-worker-batch` with `--no-build --no-deps --force-recreate`.
- New container IDs: `6fb99e99e576`, `7577854b9e60`, `62b74565db73`, and
  `70960c4d6e82` respectively.
- The worker resolved `wepppy` from `/workdir/wepppy/wepppy/__init__.py` and Git
  HEAD `f2dc2349810c5eff62c9543ad7a86239991166ca`.
- WEPPcloud health returned `OK`. The first public rq-engine probe during
  Uvicorn startup returned 502; subsequent local and public probes returned
  `{"status":"ok","scope":"rq-engine"}` before submission.
- New default and batch workers registered idle before submission.

## rq-engine execution

- Config discovery for `canada-wbt-mofe` returned HTTP 200.
- Request endpoint:
  `/rq-engine/api/runs/dainty-signature/canada-wbt-mofe/run-wepp`
- Payload: `{"clip_hillslopes": true, "hillslope_clip_length": 60}`
- Root job: `f5121308-9c63-4e46-8bae-c41083d53199`
- Started: `2026-09-04 12:30:13 UTC`
- Finished: `2026-09-04 12:33:12 UTC`
- Aggregate: 15 of 15 jobs complete, status `finished`.

## Generated slope acceptance

Every source hillslope was mapped to its generated `p<ID>.slp` through the run's
WEPP/TOPAZ translator and compared.

- Source/generated hillslopes: 167/167
- Source OFEs over 60 m: 220
- Source OFEs over 300 m: 0
- Source maximum OFE: 101.56 m
- Changed generated files: 83
- Generated maximum OFE: 60.0 m
- Maximum relative area error: `2.1856569972509936e-16`
- Header/version/z0, OFE count, point counts, and profile rows: all preserved
- Source/generated file modes: all preserved
- Failed comparisons: 0

The acceptance criteria passed without rollback.
