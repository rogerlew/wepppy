# Wepp1 deployment — 2026-10-12 UTC

Completed across wepp1, wepp2 and wepp3 at 2026-10-12 07:14 UTC
(00:14 America/Los_Angeles). All three clean checkouts select `84337c967`.
Database revision is `e7a1c9d204bf`; runtime modes and 21 workers are verified.

## Authorization and plan

The operator authorized production deployment after forest1 validation. Deploy
`84337c967136c6bc50f357fb600c0a44534edf2f` on wepp1, starting from clean
`50495bfeebf5ccf3c8cf50753100803e35bb5382`. Use the installed production preset
and `scripts/deploy-production.sh --no-flush-rq-db --skip-docker-prune`.
The operator subsequently explicitly authorized wepp2 and wepp3's WEPPcloud
worker. Activate in order wepp1, wepp2, wepp3; preserve unrelated services.

## Compatibility and recovery

Initial account revision is `c91f6b2a4d7e`: 5,140 users, six roles, 33,704 runs.
Back up the full database and restore to a disposable database before applying
the additive run-catalog and feature-access migrations through `e7a1c9d204bf`.
Verify the restored migration and existing row counts before live installation.
Retain backups, original environment, and image rollback tags on wepp1 under
`/var/tmp/wepp1-deploy-20261012`, with restricted permissions. Application
rollback retains additive tables; feature-access downgrade is unsupported.

Explicitly stage `WEPPPY_PROJECT_COMMIT_MODE=postgres`, catalog writes
`timestamp_only`, reads `legacy`, and sweeps `false`. Catalog scheduling/read
cutover is not admitted by this application deployment. Set
`PRISM_CACHE_DIR=/wc1/cache/prism` on the existing mount. Preserve
enabled Project Config flags, identities, credentials, and mounts.

Before cutover validate renderer behavior, the pinned native interchange library,
model-generated PASS/parquet artifacts and cache access under runtime identities,
and new database/JWT secret mounts. Preserve global RQ fencing and reject active
jobs; do not flush Redis. After activation verify service images/health, public
and private access boundaries, schema, configuration, and a real queued model
artifact. Retain exact evidence and report unobserved browser acceptance openly.

## Progress and discoveries

- Host identity and clean checkout verified; default, batch, fork-archive queues
  initially have zero queued and started jobs.
- Installed `wctl rq-info --detailed` uses an unsupported RQ option. Direct
  read-only Redis queue/registry checks provide the gate evidence.
- Backup completed before migration. Rehearsal error: the first migration command
  set `POSTGRES_DB`, but the container's explicit `SQLALCHEMY_DATABASE_URI`
  retained the live target. Both additive revisions therefore ran on production
  before restore validation. No destructive recovery or downgrade was attempted;
  the old application remained running. Operator informed immediately upon
  confirmation. Restore validation now explicitly rewrites the URL and asserts
  both engine database and `current_database()` before running migration.
- Restore and target-asserted rehearsal passed; restored and live counts both
  remain 5,140 users, six roles, 33,704 runs, six groups, zero memberships and
  acceptances, and zero catalog rows. Login HTTP 200; old web container healthy.
  Backup SHA-256: `83e3fd18c33f5ffab03e51ecff36818a8a293423e2600d6bb0c78103d916e985`.
  Retained 25 image rollback tags. Disposable restored database removed after
  validation. Evidence: `backup-verify.log`, `restore-migration-verified.log`.
- Environment staging and canonical candidate build initiated; activation pending.
- Two pulls stalled in LFS before build (clients 2.3.4 and 3.4.1). Stopped only
  the stuck filter process; the deploy script restored the original tracked
  checkout. Archived and removed only candidate-owned untracked files left by
  the interrupted checkout. Copied four changed LFS paths (three unique objects)
  from the local cache, verifying bytes against each committed SHA-256. Retried
  the canonical script with the already-installed system LFS client selected
  through a temporary PATH shim. Evidence: `deploy.log`, `deploy-retry.log`,
  `deploy-retry2.log`, `wepp1-lfs-manifest.json`, interrupted-checkout archives.
- Read-only worker inventory confirms wepp2 and wepp3 still run `50495bfee`.
  Asked the operator about matching wepp2 deployment as required by the operator
  runbook; scope decision pending. The temporary cutover validator explicitly
  holds activation until worker scope is resolved.

## Initial preflight outcome (before fleet authorization)

At 2026-10-12 06:07 UTC, canonical candidate builds and the extended renderer
preflight passed. Runtime identity remained `1002:130`; owner-only renderer data,
native reader SHA-256 `06319303a2337cc75a3c57eb594161565d8a2af1d58cee18c17abcfe6eea8cf8`,
WEPP 261010 SHA-256 `1dd1ca75cf53f9a0606cf5a598312d4e680e161df631156360d4a20dbcb6f17e`,
and 1,095 parsed daily rows for years 1–3 passed. Model evidence:
`/wc1/deployment-validation/20261012/model-qo60jkb3/verification.json`.
PRISM cache write/read, database/Redis secret reads by Browse, D-Tale, Query
Engine and batch workers, and Query Engine JWT-secret readability passed.

All started registries remained empty. The explicit worker-scope hold stopped
the script before old request consumers were stopped or any production service
was recreated. Wepp1 source and built image tags now select the candidate, while
running containers retain their previous images. Schema installation and staged
environment settings are complete. New UI/defaults are **not live**. Wepp2 and
wepp3 were inspected read-only; their deployment authorization remains pending.
Do not manually run Compose up to bypass the hold: resolve worker scope, rerun
the canonical entry point and its checks, then complete live HTTP/RQ/artifact
acceptance. No production browser acceptance is claimed.

CAP's canonical candidate validator also passed ACL, rotation, fresh-state,
outstanding-token continuity, idempotent legacy migration and hostile-state
checks (`cap-preflight.log`). Final readback verified all 25 original containers
retain their image IDs and start times, the candidate checkout is clean, and
production login still returns HTTP 200. No deployment process remains running.

## Authorized fleet continuation

The operator answered yes to deploying wepp2 and wepp3's WEPPcloud worker.
Both checkouts are clean at `50495bfee`; installed presets select only the two
workers and renderer on wepp2, and only the fork/archive worker on wepp3.
Fresh queue checks show zero queued/started entries on all three queues.
Restart the canonical wepp1 build, prepare the worker hosts, and warm-stop the
old remote consumers before wepp1 activation so new jobs cannot use old readers.
Then deploy worker hosts in order through the same canonical entry point.
Their unrelated Culvert and analytics/PostGIS services must retain identity.
Keep fleet snapshots, environment backups, image rollback tags and logs in each
host's `/var/tmp/weppN-deploy-20261012` directory. No additional database migration
is needed on consumers; verify their actual SQL connection reaches wepp1.

Worker host preparation completed. Wepp2 retains its existing SQL origin
`192.168.100.237`; wepp3 now explicitly uses the same origin and a restricted
copy of the existing production PostgreSQL secret. A read-only probe under
`1002:130` reached database `wepppy` at `e7a1c9d204bf`. Both hosts preserve their
four enabled Project Config flags and stage legacy catalog reads, timestamp-only
writes, disabled sweeps, and the persistent PRISM cache. LFS objects were seeded
with committed-hash verification before pull. After another empty started-job
check, the two wepp2 workers and the wepp3 worker completed warm shutdown;
wepp1 activation is now released. No unrelated containers were stopped.

## Wepp1 activation completed

The authorized run (`deploy-approved.log`) completed at approximately 06:41 UTC.
All canonical health, CAPTCHA challenge/redeem/siteverify, image identity,
service stability and worker-registration checks passed; global RQ dequeue
resumed without flushing. Public login/RQ/CAP/Query Engine/Browse returned 200.
Synthetic public download, D-Tale and declared parquet query passed (record
`{id: 1, value: 1.25}`); private anonymous download/D-Tale returned 401 without
disclosing fixture contents. Both synthetic fixture directories were removed.
The following empty-registry check passed and wepp2's canonical deployment began.

All 24 active services have zero restarts and the intended runtime modes;
`wepppy-f-esri` retained its original image/start time. The public acceptance
JavaScript SHA-256 matches the release (`f0d936df...`). RQ job
`wepp1_deploy_20261012_model_smoke` finished on the new workers; its output in
`/wc1/deployment-validation/20261012/model-jpuv73as` has the same PASS bytes and
identical parsed parquet data as the preflight (1,095 records, three years,
`1002:130`, successful PRISM cache write/read). Parquet file hashes differ;
equivalence was checked on parsed data rather than hashes.
Evidence: `services-after.json`, `public-boundaries.json`, and shared
`/wc1/deployment-validation/20261012/rq-model-proof.json`.

The operator's explicit OpenET/Batch authorization for `rogerlew@gmail.com`
was applied to production with `flask admin initialize-feature-access`.
The command resolved production account 12, verified its active Root status,
and created only `batch_runner` and `openet_ts` memberships with audit reasons.
No acknowledgment was fabricated; personal acceptance remains a browser action.

## Wepp2 activation completed

Canonical `deploy.log` ended successfully, resumed global dequeue, and retained
Redis data. All three selected services are running with zero restarts; the
four unrelated Culvert containers retain their original IDs/start times.
The renderer sharing contract passed under `1002:130`, both worker database
probes reached `wepppy` at `e7a1c9d204bf`, and model artifacts in
`/wc1/deployment-validation/20261012/model-tmr9rim8` contain 1,095 daily records
with the expected PASS hash and successful persistent cache write/read.
Fresh fleet checks found 20 idle workers, no queued/started jobs, and no global
suspension before launching wepp3's canonical deployment.

## Wepp3 activation and final outcome

Canonical `deploy.log` completed successfully after a slow local image export.
The dedicated fork/archive worker runs the candidate image as `1002:130`, has
zero restarts and exactly one current RQ registration. All three unrelated
analytics/PostGIS containers retain their original IDs/start times. Its isolated
model smoke artifact at `/wc1/deployment-validation/20261012/model-qq_2dd6_`
contains the expected 1,095 records and PASS hash; native interchange and
persistent PRISM cache write/read passed.

All 21 actual worker process environments (10 wepp1, 10 wepp2, one wepp3)
passed the shared PostgreSQL advisory-lock origin probe against the web process:
held nonce unavailable, control nonce available, source mounts readable and
runtime identity `1002:130`. Evidence is retained on wepp1 in
`fleet-origin-proof.json`. Every host checkout is clean at the release commit.
Final login/RQ/CAP/Query Engine/Browse HTTP checks returned 200. Final RQ snapshot
has 21 registered workers, no queued backlog, one started default job and one
started batch job, with dequeue enabled (`final-queues.json`). These jobs arrived
after the deployment gates; they were not interrupted by final verification.

The release UI and `wepp_261010` defaults are live. Authorized OpenET/Batch
memberships are present, with two audit events and zero acceptances at readback.
Legacy catalog reads, timestamp-only writes and disabled sweeps remain the
intended rollout state. Full interactive OAuth/Runs/onboarding acceptance on
production remains a human browser check; endpoint and artifact checks do not
claim that witness. Backup, restore rehearsal, rollback tags and operational
logs remain retained outside git at the paths above. The migration target error
and subsequent successful restore validation remain recorded in Progress.

## Authorized one-time seed/backfill

The operator subsequently requested seed/backfill on wepp1. Populate only the
additive catalog from existing registrations and authoritative source files,
using the existing seed/sweep services with at most 50 rows and two readers per
batch. Preserve legacy reads and current producer/scheduler configuration:
this request populates the snapshot but does not authorize read cutover or
claim ongoing notification freshness. No project files or registrations change.
Validate the initial 50, then continue bounded batches, retain source omission
and transient-failure manifests, compare source values to SQL, and report final
coverage. Existing fleet origin/mount evidence applies while identities remain
unchanged; no worker restart or queue clearing is needed. Stop on unexpected
SQL failures or stalled progress; retain committed batches for resumability.

Completed 2026-10-12 07:44:02 UTC (00:44:02 America/Los_Angeles). The pilot
seed/reconcile classified 50 rows and all 50 source comparisons matched.
The continuation used 673 bounded sweeps through the same maintenance service,
under the existing web runtime identity `1002:130`, without restarting services.
All 33,699 registrations now have classified catalog rows: 14,767 ready,
18,930 missing Ron sources and two invalid Ron sources. Pending, dirty,
unreconciled and transient-failure counts are zero. Missing/invalid entries were
classified, not repaired or deleted. Fifty comparisons sampled across the ready
rows also matched, giving 100 successful comparison observations overall.

Restricted host evidence in `/var/tmp/wepp1-deploy-20261012` includes
`catalog-backfill.py`, `catalog-backfill.log`, `catalog-backfill.exit` (zero),
`catalog-backfill-summary.json`, `catalog-omissions.json`, and
`catalog-comparisons.json`. The manifest retains registration IDs, source states
and bounded diagnostics, rather than raw source contents. Continuous catalog
notifications/sweeps and read cutover remain unactivated; this backfill is a
point-in-time snapshot, not proof of ongoing freshness or read-promotion readiness.
