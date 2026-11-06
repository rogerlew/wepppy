# Production deployment readiness — 2026-11-06

Assessment at approximately 04:40–04:53 UTC (November 5 evening PST).
Scope: verify publication and inspect production; prepare a deployment plan.
No production deployment, repository push, cleanup, migration or service restart
was authorized or performed during this assessment. This is a planning record,
not an active execution authorization.

Execution is now authorized under the parent [work package](../package.md);
the assessment below preserves the earlier inspection context.

## Decision

The committed application/native release is published. Production is not ready
for an unattended deployment command: first resolve disk headroom, preserve and
reconcile the existing Caddy overlay, prepare the additive database migration,
and arrange a coordinated RQ major-version transition across all shared workers.
The current canonical script must remain the activation entry point.

## Publication and candidate identity

| Repository | Candidate | Verified remote state |
| --- | --- | --- |
| wepppy | `master` at `1dc70d26afff262f45105edd411274790f91703f` | Exact GitHub branch match |
| wepppyo3 | `main` at `5e3540f684c8606f4140afcd72ed5a21df5ab85f` | Exact GitHub branch match |
| wepp-forest release checkout | default branch `wepp_260430_negmeltfix_comparator` at `7d4cf4b5ab24bbc825515d54f25a035062b826bb` | Exact GitHub branch match |

The vendored WEPP 261029 revision-7 pair was built from native commit
`e0abe0581f77c6f66917e90daf8f8f429e9315c8`, verified as an ancestor of the
published default branch. Both executable files exactly match their committed
Git blobs and sidecar hashes:

- Watershed: `4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`.
- Hillslope: `210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936`.
- Committed Python 3.12 Rust interchange:
  `7f67d3a8e56066d43b2fdb1ffc5360d357d61f2fcc963190c67fe288373702ad`,
  matching the application startup guard.

Fresh checks passed for all 661 wepppy and 127 wepppyo3 tracked LFS files; both
WEPP executables passed the host interpreter/library provenance gate. The initial
unbounded copied-tree scan was stopped in favor of the tracked-file gate.
These three artifacts are actual Git blobs, not LFS pointer stubs. Production
images copy the vendored WEPP pair from wepppy and fetch wepppyo3; deployment does
not build from the dirty sibling Fortran checkout. The published Rust source
repair is not a newly installed extension release; that distinction is recorded
in the [MOFE installed-reader receipt](../../20261102_mofe_input_producer_audit/artifacts/mipa02_installed_reader.json).
Do not rebuild/promote Rust or change executable defaults as incidental deployment work.

Uncommitted work is not part of the candidate:

- wepppy: controller-input-validation documentation, generated Usersum index,
  and one management JSON change adding `_pmet_plant_names: null`. The last item
  matches the previously observed test-generated change, but is outside docs;
  preserve it rather than silently discarding or including it in a build.
- wepppyo3: module-registry documentation and calendar/HBP Rust source edits.
- Main `/workdir/wepp-forest` is on `kernelized-abandoned`, two documentation
  commits ahead of that remote branch, with substantial unfinished native edits.
  It is not the release checkout. The release checkout has only untracked r5/r6/r7
  build evidence directories; its tracked release source is published.

## Observed production baseline

wepp1, wepp2 and wepp3 host wepppy checkouts are all at
`0da9c9071069c37fdcf3df5a74b28d161b1af458`; the application candidate is 136
commits ahead. wepp2/wepp3 checkouts reported clean. wepp1 has only two tracked
Compose edits adding `net.mptcp.enabled: "0"` to Caddy. Both exact additions are
already in the candidate; preserve the live setting while reconciling the files.

wepp1 effective preset is `docker-compose.prod.yml` plus
`docker-compose.prod.wepp1.yml`. Main runtime image is
`sha256:cdc729021ea9cc6ffbe12a2b15ac8febcbc26ec51d14279e46f88a1a28408864`
(8,036,845,610 bytes). Main services started October 27, Caddy October 29, and
scheduler last started November 5 at 22:08 UTC. All 25 Compose containers were
running; existing healthchecks were healthy, with zero recorded restarts.
Web, rq-engine and CAP health endpoints returned success. The existing
`/rq-dashboard/` endpoint returned 502: Caddy references `rq-dashboard:9181`,
but no such container is running or listed in the production preset. Track this
as a preexisting observer gap, not a new deployment failure or implicit authority
to add a service.

The live worker identity is UID 1002, GID 130, groups `[130]`. Application/native
code is image-resident; no broad application or Rust source bind mount was found.
Host sibling native checkouts are old and dirty but are not the runtime authority.
The live worker has WEPP 261026, no 261029, and Rust interchange hash
`7908a4fa667b149f4eee5a827dfb65c39c0c080369459b659c68cec26f411811`.

All three shared queues (`default`, `batch`, `fork-archive`) had zero queued and
zero started entries. Seventeen worker hashes reported idle RQ 1.16.2 workers
across local pools, a remote default pool and the dedicated fork/archive pool.
Redis reported neither suspension nor a deployment fence. Recheck at cutover;
this snapshot does not promise that jobs remain absent. Historical registry counts were also inspected without cleanup:

| Queue | Deferred | Scheduled | Failed | Finished | Canceled |
| --- | ---: | ---: | ---: | ---: | ---: |
| default | 544 | 0 | 6,736 | 4,294 | 10,716 |
| batch | 13 | 0 | 477 | 123 | 2,829 |
| fork-archive | 0 | 0 | 29 | 14 | 11 |

These counts do not certify record compatibility. Preserve the 557 deferred
entries and all retained history; inspect representative IDs/dependencies in an
isolated recovery copy before migration. wepp2 has a running batch supervisor
and four child processes, but its batch hostname has no corresponding worker
hashes in the shared snapshot. Diagnose this baseline registration gap before
claiming fleet health; do not infer working consumption from a running container.

The account database is at `e7a1c9d204bf`; the pending notification migration is
`f6b8d27a901c`. Scheduler file readback confirms TTL GC is already paused. Catalog
flags remain `legacy` reads, `timestamp_only` writes and sweep disabled.
Preserve those rollout choices.

Root filesystem: 22 GB available, 98% used. Docker reports 225.5 GB in images,
57.76 GB reclaimable, zero build cache, and 76 volumes (8 active). Reclaimability
is not permission to prune: retain running and rollback images and all volumes.
Measure peak build space and choose exact disposable image IDs before cleanup.
wepp2 has 121 GB free and wepp3 242 GB; their build budgets still require checking.
Host Python imports Jinja2 successfully; the forest host-builder issue is absent.

## Changes that require explicit deployment gates

1. RQ changes from 1.16.2 to 2.12.0. Mixed execution and reverse compatibility with
   2.x-written state are not supported. See [migration/recovery](../../../dev-notes/rq-2-12-migration.md).
2. Production dependency versions differ from the forest baseline. Actual
   production → candidate pins include FastAPI 0.162.0 → 0.143.1, narwhals 2.28.0
   → 2.27.1, pkginfo 1.13.3 → 1.13, python-dateutil 3.0.0 → 2.9.0.post0;
   Redis remains 6.2.0. Validate installed candidate distributions and affected
   API/raster/report workflows; do not claim only RQ changes in production.
3. Notification tables must exist before serving the inbox. The deployment script
   does not invoke Flask/Alembic account migrations. Prepare a separate backed-up,
   restore-rehearsed migration step before candidate readers activate.
4. Correction after effective-config verification: production services inherit
   wctl's merged `WEPPPY_ENV_FILE`. A temporary host-env render on wepp1 proved
   `WEPPCLOUD_NOTIFICATIONS_SWEEP_ENABLED=true` reaches the scheduler without a
   Compose edit. Persist it in the selected host/service environment files and
   verify precedence; a shell-only export is not sufficient when that key is not
   referenced in Compose interpolation. The temporary file was removed, and live
   configuration was unchanged. Initial rollout keeps population disabled until
   worker/browser preflight passes; preserve GC pause throughout.
5. This is a full release: RQ, native binaries/interchange, Roads, soil and NoDb
   changes, Usersum, notifications and Runs bulk TTL controls. A targeted web-only
   deployment cannot update all required consumers.

The latest bulk-TTL package records 13,218 passing Python tests / 423 skipped,
1,067 frontend tests, and independent reviews. Native revision-7 provenance
retains native, runner, specialized and artifact validation. These are retained
release evidence, not freshly executed production acceptance for this assessment.

## Proposed execution sequence

1. Freeze the published candidate revisions above. Inventory exact running image
   IDs and installed distributions on every affected host. Preserve host config,
   Caddy mitigation, static assets, and rollback images. Clear sufficient measured
   build headroom using only reviewed disposable images; do not prune volumes.
   Preserve unfinished local work and build from the clean production checkout.
2. Save the two wepp1 Compose diffs, verify they are subsumed by the candidate,
   then reconcile them without dropping the live mitigation. Fast-forward all
   three application checkouts to the frozen candidate, without switching branches.
   Resolve published sibling build refs and verify the extension guard and both
   vendored executable hashes in each built image. Moving branch refs must be
   rechecked before every build; abort on drift.
3. Back up PostgreSQL and rehearse the additive migration against a disposable
   restored database. A bounded one-shot Flask migration can use the old runtime
   with the candidate migrations directory mounted read-only: the new revision
   imports only Alembic/SQLAlchemy, and old application code ignores its tables.
   Validate this exact invocation in rehearsal before applying it live. This
   avoids starting candidate readers before the schema exists. Keep all new
   notification admissions disabled.
4. Establish a coordinated maintenance window and stop new user/job admissions
   through a reviewed mechanism. Inventory all historical registry states and
   drain every running 1.x job, including fork/archive. Preserve Redis and take
   a protected, consistent recovery snapshot. No queue flush or job deletion.
5. Before wepp1 cutover, warm-stop and hold old shared worker services on wepp2
   (`rq-worker`, `rq-worker-batch`) and wepp3 (`rq-worker-fork-archive`). This is
   a specific operational exception to prepare/approve before execution; the
   canonical per-host script alone does not coordinate the fleet. Preserve all
   unrelated Culvert and watershed-analytics services. Confirm zero old remote
   consumers remain before the first script may resume RQ.
6. Activate wepp1 first, then recheck and activate wepp2, then wepp3 using the
   installed preset and canonical command below. Each script owns its fence and
   resumes it on completion. Holding old remote workers prevents mixed versions
   between those resumptions; do not manually pre-set a global fence that the
   script rejects or assumes ownership of. Recheck zero started jobs before each
   subsequent host, and keep general admissions held until fleet acceptance.
7. Verify all producer/worker/scheduler versions, worker pool counts, UID/GID,
   mounts, umask, native hashes and stable health. Exercise a disposable ordinary
   project through the real API/model graph, inspect consumed inputs and fresh
   outputs, and retrieve a report. Include Roads rendering, login/CAP, Usersum,
   notification read/unread and bulk TTL authorization checks. Submit a bounded
   fork/archive canary once wepp3 is updated. Preserve old project binary choices;
   do not mix old/new hillslope and watershed artifacts.
8. Restore general admissions only after acceptance. Leave notifications disabled
   until effective configuration and worker/migration preflight pass; when enabled,
   retain actual scheduled-job/source/inbox readback, not just a green job.
   Catalog pilot controls and paused GC remain unchanged.

Canonical entry point (proposed, not executed):

```bash
cd /workdir/wepppy
scripts/deploy-production.sh --print-plan --no-flush-rq-db --skip-docker-prune
scripts/deploy-production.sh --skip-pull --no-flush-rq-db --skip-docker-prune
```

`--skip-pull` is appropriate only after verified fast-forward to the frozen
candidate. Do not use it to deploy an unresolved dirty checkout. The script
builds locally without cache and refuses `--skip-build` for locally built
services. It prunes build cache after building even with `--skip-docker-prune`;
that flag preserves runtime images. wepp1's read-only plan reports six build
services and 24 recreated services, including PostgreSQL and Redis; schedule a
service interruption, not a zero-downtime rollout. The existing f-esri orphan
must be preserved. Do not substitute registry/Kubernetes procedures.

## Rollback boundary

Before any 2.x writes, retain exact compatible application/native images and
source plus a consistent recovery point. Keep additive notification tables on
application rollback. Once 2.x has written shared queue state, do not restart
1.x workers against it or restore an old Redis snapshot over newer accepted work.
Hold admissions, retain diagnostics and prefer a bounded forward repair; any
whole-state rollback needs an explicit no-data-loss recovery decision. The
canonical script does not provide generic full-stack exact-image rollback, so
prepare and review concrete image/source recovery commands before activation.
Forest's notification rollback proves that feature's state preservation, not a
production RQ major-version downgrade.

## Inspection/tooling note

The skill's suggested `wctl rq-info --detailed` is invalid for this installed
wrapper/CLI. Its preliminary worker-index synchronization ran before the CLI
rejected the option; no jobs were enqueued, stopped or deleted. Subsequent queue
inspection used direct Redis reads only. Prefer the supported `--detail` spelling
when its wrapper behavior is intended; use direct non-cleaning reads for a strictly
read-only snapshot. A small skill correction would prevent this recurrence.

## Authorized wepp1 cleanup follow-up

The operator approved the recommended cleanup after this assessment. Executed
`docker image prune --force` on wepp1 only, without `--all` or volume pruning.
Docker reported 195.5 GB reclaimed. Final root readback: 735 GB used, 215 GB
available, 78% usage, compared with 928 GB used / 22 GB available / 98% before.
The original reclaimable estimate understated actual recovery.

Before/after inspection confirmed every container ID, image, start time, restart
count and state unchanged; all tagged images, including rollback and CAP rescue
images, were preserved. No volumes or project data were targeted. Web and
rq-engine health checks passed during cleanup. wepp2 and wepp3 were untouched.

The optional `sudo -n journalctl --vacuum-size=500M` step could not run because
sudo requires an interactive password. Journals remain unchanged; no alternative
privilege mechanism was used. Disk headroom is now substantially improved.

## Combined notification and query-catalog production cutover

The operator requested including `20261023_query_catalog_async_refresh` in the
production plan. This adds feature activation/acceptance scope, not a claim that
production has been changed. Use its active ExecPlan and tracker for execution.
The PostgreSQL Runs listing catalog is a different subsystem: leave its current
`legacy`/`timestamp_only` modes and sweep setting unchanged.

### Confirmed preparation defect

`docker/scheduled-tasks.yml` still selects `batch` for `query_catalog_refresh`.
The scheduler passes that Queue explicitly into `reconcile_query_catalogs`, while
October 28 admission/worker code requires `default`. An installed-code probe read
the real YAML, captured the queue at the scheduler dispatch boundary and called
the queue guard without Redis access: `batch`, rejected with
`Catalog admission requires shared default`. The existing scheduler test uses a
handwritten batch task and replaces reconciliation with a permissive stub, so it
misses this mismatch. No production job was admitted by the probe.

Before deployment, change only that scheduled task's queue to default, retain
notifications on batch, add a regression exercising the actual YAML/dispatch and
queue admission contract, update the RQ graph/catalog, and obtain review. This
repairs conformance to the existing October 28 contract; no new queue or policy
is needed. Publish the correction and freeze the resulting candidate revision.

### Activation stages

1. Complete the common fleet/RQ/schema rollout above with both feature flags
   false. Fix the wepp2 batch registration gap and confirm twelve genuine default
   consumers (six per host), plus expected notification batch consumers. Match
   catalog protocol, queue, native scanner and roots across all participants.
2. Notifications: use a disposable authorized account/project and explicit
   registration scope for actual worker retry/read-state/TTL-byte checks. Verify
   bell count, inbox pagination/sorting and CSRF/account isolation. Then persist
   `WEPPCLOUD_NOTIFICATIONS_SWEEP_ENABLED=true` on wepp1 and recreate the scheduler
   through an explicitly authorized bounded production operation or canonical
   full deployment. The earlier scheduler-only exception covered forest only.
   Observe the actual startup-relative 900-second admission and its consumed
   inbox output; subsequent interval is 86,400 seconds. This does not enable GC.
3. Catalog default-worker pilot: general `QUERY_CATALOG_REFRESH_ENABLED=false`.
   Verify old batch catalog work is drained and preserve the existing historically
   named admission ledger, pause key, receipts and old pilot manifests. Run the
   existing owned-eight-scope pilot with a fresh ID on the twelve default workers.
   Retain inventory and receipt waves, actual catalog/schema/query readback,
   ordinary default-job arrival delay, pause/resume and guarded cleanup. Prior
   batch-pilot success does not establish this new scheduler/worker path.
4. Configure identical `QUERY_CATALOG_ROOTS_JSON` for all producers, query services,
   workers, scheduler and synchronous publishers on wepp1–3. Include primary runs,
   batch, culverts and active legacy runs, with the existing shared external
   coordination namespace. Do not omit legacy roots to make readiness pass or
   turn the separate Runs catalog on. Verify actual path access and locks under
   UID1002/GID130. The prior legacy archive mount limitation remains excluded;
   no mount/routing repair is added here.
5. Before general activation, retain a concrete monitored rollout manifest with
   the full root configuration, observation deadline, observers, capacity metrics,
   pause/resume procedure and acceptance thresholds. Proposed observation budget
   is up to 48 hours, requiring at least one complete reconciliation cycle and
   representative ordinary arrivals; no arrivals or incomplete cycling means the
   gate stays open. Review the window/stop criteria before executing it. Keep the
   existing cap of seven outstanding maintenance jobs and ordinary-backlog
   admission deferral; do not invent a partial-root cohort that breaks managed
   scope resolution. Use the finite owned pilot as the bounded first stage.
6. Persist `QUERY_CATALOG_REFRESH_ENABLED=true` consistently in the existing
   merged service environment and activate all participants through the canonical
   fleet lifecycle, with catalog admission paused across configuration transition.
   Verify capability convergence before resuming catalog admission. Retain actual
   scheduled default-queue jobs, complete-cycle progress, oldest unreconciled and
   pending ages, ordinary-job delay, HTTP responsiveness, catalog digests/schema,
   receipt acknowledgment and report/query correctness. Adopt a permanent enabled
   state only after capacity/consumer acceptance; a green job alone is insufficient.

Keep stages independent so a catalog capacity failure does not require disabling
notifications. Pause catalog admission on failure and preserve receipts/guards;
coordinate any return to synchronous producer mode while draining outstanding
maintenance. Pause the notification schedule independently and retain inbox/read
state. Neither feature rollback permits an RQ 2.x → 1.x state downgrade.

The 48-hour proposal is an execution observation budget, not a new scheduling
parameter or a 24-hour freshness guarantee. Historical inventory counted 30,891
scopes; current counts and complete reconciliation cost must be measured again.
