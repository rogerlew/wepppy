# M6 master rollout — production evidence

Status: M6 complete, 2026-10-15 04:04 UTC. Operator authorized wepp1, wepp2, and wepp3 on 2026-10-14
Pacific time (execution 2026-10-15 UTC). Candidate: `052019426`; prior production
revision on all three hosts: `84337c967`. No receiving-deployment or recurring
synchronization activation belongs to this milestone.

## Preflight and deployment

All three host identities and clean checkouts verified. Installed canonical plans:
wepp1 full production stack, wepp2 worker stack, wepp3 fork/archive worker only.
The shared started registries for default, batch, and fork/archive were empty.
The skill's `wctl rq-info --detailed` is incompatible with installed RQ;
read-only Redis sorted-set inspection established the queue gate instead.
The canonical deploy script retains its own queue and suspension checks.

Published the previously tested candidate with `git push origin HEAD:master`.
Deploy command on each authorized host is
`scripts/deploy-production.sh --no-flush-rq-db --skip-docker-prune` from
`/workdir/wepppy`. Per-host logs and previous-image evidence are retained in
`/var/tmp/wmesque-m6/`. The prior wepp1 application image is tagged
`wepppy:before-wmesque-m6`.

wepp1's Git LFS 2.3.4 checkout stalled downloading the sole changed LFS object,
WEPP release-notes PDF SHA-256
`9a25dd7e51256ac56c843d2614f2aa49a486190c911a63862339a5e322d37bb0`
(2,747,329 bytes). Copied the identical verified forest object into each host's
LFS object cache. Terminated only wepp1's stalled LFS process; the canonical
script restored the previous revision. Its rollback left 410 new untracked
files from the failed checkout. Every file was verified against the candidate
Git blob before moving it into `/var/tmp/wmesque-m6/failed-checkout-untracked/`.
No preexisting untracked files existed. Retried the canonical script with normal
LFS filters and deployment gates. No services were restarted during this repair.

## Publication selection and baseline

Actual wepp1 WMesque identity: UID 1002, GID 130; host `/geodata` maps directly to
container `/geodata`. The NFS source has about 3.7 TB free. Selected existing
`tenerife/136_MDT25_TF`, a
self-contained 36 MB GeoTIFF/VRT closure. Source hashes are retained at
`/var/tmp/wmesque-m6/source-before.sha256`. Existing operator SSH access with
strict host-key checking can read this source; no account, key, trust, runtime
identity, or mount was changed.

Baseline public/default-client request for bbox `[-16.65, 28.25, -16.60, 28.30]`
at 30 m returned a 187 by 161 Float32 raster in EPSG:32628, range
2043.2005615234375–3704.739990234375. Baseline raster and metadata are retained
under `/wc1/wmesque-m6-20261015/` on forest. Publication, pixel comparison, private transfer, and post-deployment results follow below.

## wepp1 publication and private source validation

Canonical deployment completed successfully at about 03:30 UTC. The new WMesque
image is `sha256:dfd1a26c005251cec8a2855815648164ccbaa2920d68b9a4f9f975d470080d90`.
Public web/RQ/CAP health, CAP functional canary, all recreated services, image
identity/stability, worker registration, and global RQ resume passed.
The public HTTPS route was briefly unavailable during normal Caddy replacement;
it recovered before publication acceptance. No zero-downtime claim is made.

Published through the existing server identity with
`wctl exec -T wmesque2 python -m wepppy.webservices.wmesque_catalog publish /geodata tenerife/136_MDT25_TF`.
Revision: `aa96d31fe8aff11778b84be268798c04295e0d3de758649ec6e666d854fee295`.
Two files total 37,493,165 bytes. Repeat publication produced the identical
manifest. Both original source hashes remain unchanged. Public pinned retrieval
matches the complete baseline pixel array, projection, transform, and nodata.
The deployed worker verified managed and legacy NLCD acquisition, old-style
unpinned requests, and HTTP 409 for a wrong revision. Defaults remain remote-only;
master synchronization remains disabled.

A real sync from `roger@wepp1:/geodata` into an isolated forest directory completed
03:30:11–03:30:14 UTC with standard rsync/SSH and strict host verification.
Transferred manifests/hashes and GDAL readability passed; full source readback
was 2747 by 3255 in EPSG:32628. A second dry run reported no updates. The initial
operator invocation correctly failed because its isolated destination directory
had not yet been created; after creating it, transfer succeeded. No code workaround
or permission change was needed.
This establishes the master export under existing authorized operator access.
Receiver task credentials, home/trust configuration, and Kubernetes writer
permissions still belong to M7; no operator credential was copied into a worker.

Rollback-layout acceptance used the prior production image in an isolated
`docker run --rm -i --network none --user 1002:130` with only a read-only
`/geodata` bind. Its original FastAPI request handler returned the expected
187 by 161 raster and baseline values while the managed catalog was present.
No production service was rolled back. SSH connection endpoints were confirmed
as forest `100.99.21.102` to wepp1 `100.127.248.45:22` on the tailnet.

## wepp2 shutdown recovery

The canonical worker-stack cutover acquired its global fence and checked zero
started jobs, but both old RQ pools remained waiting after warm shutdown.
Workers logged unregister/unsubscribe and their remaining processes waited on
futexes; shared registry inspection showed no current jobs and zero default,
batch, or fork/archive started entries. The fence remained owned by
`wepp2-49960-1792035480`. Inspection of installed RQ confirmed that a repeated
SIGTERM forwards the workers' second-stage shutdown signal.
Sent `docker kill --signal=SIGTERM docker-rq-worker-1 docker-rq-worker-batch-1`
on the verified wepp2 host. Both containers stopped immediately and the same
canonical deployment resumed. No queue state, fence, timeout, or code was changed;
no running job was interrupted. This is retained operational recovery evidence,
not a new deployment workflow or an untested shutdown patch.

wepp2 canonical deployment completed at about 03:41 UTC with stable candidate containers, registered default/batch workers, and global dequeue resumed. Its actual batch runtime passed `master_runtime_acceptance.py`; managed/legacy rasters, default routing, disabled sync, unpinned compatibility, and revision mismatch all passed. wepp3 preflight confirmed all three started registries empty and no lingering suspension/fence before its deployment began.

## wepp3 and final acceptance

wepp3 canonical deployment completed successfully at 04:04 UTC. Its large image
export finished without errors. The old one-worker pool displayed the same warm
shutdown hang as wepp2 after unregistering and stopping its scheduler. The
fork/archive started registry was empty and no fork worker remained registered;
only the pool and its exiting worker remained. A batch job was executing on
wepp2 and was left untouched. A second SIGTERM to only
`docker-rq-worker-fork-archive-1` allowed the canonical deployment to finish.
The replacement registered with RQ as UID/GID 1002:130, passed image/stability
checks, and passed `master_runtime_acceptance.py` from its actual runtime.
The analytics Caddy/server and PostGIS containers retained their original IDs.

All three hosts deployed `052019426` in wepp1, wepp2, wepp3 order. Retained
`master-<host>-deployment.json` records image identities, runtime state, and
WMesque configuration; `master-<host>-runtime.json` records actual raster checks.
Final shared Redis inspection found no deployment fence and no suspension;
the existing batch job continued. All deployment scripts returned exit 0.
M6 is complete. M7 receiving task access/local-first canary and M8 recurrence
remain pending. No local-first or recurring sync was enabled on any deployment.

A separate post-deployment batch job, `a24fd9ed-176c-4050-a2b9-632afe207af4`,
failed at 03:44:36 UTC in `index_usersum_docs_rq` because its documentation
contract references missing `tests/disturbed/analysis_results_current.md`.
This is a documentation-indexing failure, not a WMesque acquisition/transfer
failure. It is recorded for separate repair; no generated docs index was edited
and no job was retried or canceled as part of M6.

## Checks and limits

The exact deployed candidate retains the M1–M5 independent correctness/security
approvals and regression evidence (10,846 passed, 126 skipped; final focused
and rebuilt-image checks in the forest acceptance artifact). No production code
changed during M6. This milestone adds actual production identity, mount,
publication, public retrieval, tailnet transfer, rollback-layout, and per-host
runtime evidence. Documentation lint and whitespace checks cover the final
rollout record. Only the Tenerife resource is managed; NED remote source
materialization and broader catalog publication are not claimed.
