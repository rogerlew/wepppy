# Production deployment - MOFE accepted revision

**Status**: PASS on wepp1, wepp2, and wepp3
**Accepted revision**: `f22ac0d549c141c8784dc1b5e2364e2ffd889421`
**Authority**: Roger explicitly requested deployment to wepp1, wepp2, and wepp3,
then approved preserving wepp1's untracked files in a timestamped Git stash.
This record covers deployment, not the subsequent scientific run repairs.

## Preflight and checkout

All three hosts identified themselves correctly at `/workdir/wepppy`, on master
at `97800607c30c0979d422f99b1e2c65f1b8a89ab5`. wepp2/wepp3 were clean.
wepp1 had 2,023 untracked files, all content-identical to accepted target files;
Git refused the initial fast-forward without changing HEAD. No service restart
occurred during that attempt. Roger approved a recoverable stash.

wepp1 retains `mofe-predeploy-untracked-20260918` for the original files and
`mofe-failed-lfs-checkout-20260918` for an interrupted checkout. The interruption
was an LFS credential failure for two documentation PDFs. Both exact objects
were copied from the local LFS cache and SHA-256 verified; the normal Git
fast-forward then succeeded and the worktree was clean. No credentials or Git
authentication settings were changed.

Recovery stash object IDs on wepp1: original untracked files
`3d7bd93f725a341d9d4e0063fa256f04f0f54e79`; interrupted checkout
`a2ad7f486c25295e4d0f5de236cdb61b7e2a43c6`. Retain both; do not pop them over the
accepted checkout, where their files are now tracked.

Credential diagnosis: `gh auth status` confirms rogerlew authenticated on wepp1,
but Git selects `/usr/local/bin/git-credential-manager` with its `gpg` store,
not the GitHub CLI helper. The separate `gh auth setup-git --hostname github.com`
command links Git to that login. Roger subsequently reported running it on wepp1.

The installed RQ version rejects `rq-info --detailed`; plain `wctl rq-info`
confirmed zero queued or executing default, batch, and fork/archive jobs before
deployment. The canonical script also enforces its own active-job checks.

## Ordered rollout

Use the installed preset and canonical entry point on each host:

    scripts/deploy-production.sh --skip-pull --no-flush-rq-db --skip-docker-prune

`--skip-pull` pins the already-fast-forwarded accepted revision. Do not flush
queue history or prune recovery images. Deploy and validate wepp1 first, repeat
preflight for wepp2, then deploy the dedicated wepp3 fork/archive topology.

| Host | Start (UTC) | Result | Log |
| --- | --- | --- | --- |
| wepp1 | 2026-09-18 09:21 | PASS; complete by 09:34 | `/tmp/mofe-wepp1-deploy.log` |
| wepp2 | 2026-09-18 09:35 | PASS; complete by 10:10 | `/tmp/mofe-wepp2-deploy.log` |
| wepp3 | 2026-09-18 10:11 | PASS; complete by 10:44 | `/tmp/mofe-wepp3-deploy.log` |

## Acceptance

wepp1's canonical deployment passed image/runtime checks, CAPTCHA functional
checks, service health, image identity, restart stability, and worker registration;
the global dequeue fence resumed. Public `/rq-engine/health` returned `ok` and
`/weppcloud/` returned HTTP 200. Four application/worker services retain identity
1002:130 and match Forest's source hashes:

- `landuse.py`: `86be20117e7958a0dd23ded739e111984a5c0d470f2824d456057304ae176070`
- `project_rq.py`: `f72c5f74c045dba5342a590042c5eafaba0992d91a1762cb9115dbc911f9fe35`

Fresh wepp2 preflight at 09:34 UTC found all three queues empty with zero
executing jobs. Host identity and clean checkout were verified before update.

At 09:43:14 UTC the wepp2 deployment requested graceful shutdown of both worker
pools after its zero-active-job gate passed. At 09:52 UTC both still report
waiting for workers to shut down, beyond the normal 405-second queue-read
timeout. The deployment was left running pending operator direction.

Read-only Redis checks at 09:51 UTC found two active maintenance jobs on wepp1,
not wepp2: `ddf17b14-f0be-4398-aed5-afe1f46ad00b` (`gc_runs_rq`) and
`2e1c73d2-a845-4b59-b4b6-97465309f922` (`compile_dot_logs_rq`). Both started after
the fence was established; suspension is therefore not proof that no work can
start. Root cause is unconfirmed.

Roger then reported stopping the batch job and instructed continuation. At
10:08 UTC fresh checks showed zero started default/batch jobs and no registered
wepp2 workers. The two old containers still waited for shutdown. Under that
approval, `wctl docker compose kill -s SIGKILL rq-worker rq-worker-batch` stopped
only those wepp2 containers. The existing canonical deployment continued;
health, candidate-image identity, stability and worker registration passed by
10:10 UTC. It resumed the global queue fence normally and exited zero. Both
worker services run as 1002:130 and match the source hashes above. Evidence:
`/tmp/mofe-wepp2-runtime-identity.log`. No run files or queue history were removed.

wepp3's fresh preflight found all queues idle. Its clean checkout fast-forwarded
to the exact accepted revision; the two verified LFS objects were primed from
the local cache. The canonical plan selected only `rq-worker-fork-archive`, and
its required mounted-secret readability checks passed before deployment.
The image build completed, including vendored LFS verification. At 10:26:25 UTC
the canonical deployment requested warm shutdown. The worker stopped its
scheduler and unregistered, but the container still waited at 10:30 UTC. Fresh
Redis evidence showed zero started fork/archive jobs and no registered consumer.
The deployment was left running pending operator direction.
At 10:33 UTC the normal queue-read timeout elapsed without exit. Fresh checks
still showed zero started fork/archive jobs and zero registered fork/archive
workers; global dequeue suspension was false. Requested approval to force-stop
only this idle container. General queues remained available during this wait.

Roger explicitly approved the bounded force-stop. At 10:42 UTC fresh checks
again found zero active fork/archive jobs and zero registered consumers;
`wctl docker compose kill -s SIGKILL rq-worker-fork-archive` stopped only the
lingering wepp3 container. The existing deployment replaced it and exited zero.
Its identity (1002:130), exactly one registered fork/archive consumer, candidate
image identity, service state, and 15-second restart stability gates all passed.
Live source hashes match the accepted values above; retained in
`/tmp/mofe-wepp3-runtime-identity.log`. No run files or queue history were removed.

All three hosts now run the accepted revision. Public web/API checks remain
healthy. Deployment is complete; the eight scientific run repairs are unstarted.
The repeated idle worker-pool shutdown hang merits a separate bounded diagnosis;
no RQ implementation or deployment timeout policy was changed in this rollout.

Canonical health/image/stability/worker-registration checks and live hashes are
recorded above. Production scenario repair remains unstarted.
