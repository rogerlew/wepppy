# Forest1 deployment run sheet

## Authority

The operator authorized forest1 application deployment and waived fixed 48-hour
nonproduction waits because forest and forest1 have one human operator. This
does not authorize wepp1, the forest companion stack, branch replacement,
discarding commits, or bypassing technical/deployment checks.

## Preflight

- Host: forest1; repository: `/workdir/wepppy`; installed production preset.
- Clean tracked worktree before deploy; current HEAD `253188229` on
  `feature/project-owned-config`, tracking its namesake origin branch.
- Six default, four batch and one fork/archive consumer were idle. Direct
  started-registry checks found no running or queued jobs in those queues.
  No forest companion container was observed running.
- `wctl rq-info --detailed` failed because installed RQ accepts no `--detailed`
  option; direct worker/registry inspection established the same active-job
  gate without mutating jobs. The old registry API also lacks `cleanup=False`;
  raw Redis sorted-set reads were used for the read-only started check.
- Fresh backup `/backups/weppcloud-pre-run-catalog-20261001T031224Z.dump`,
  674 KiB, mode 0600, passed `pg_restore --list`.
- Canonical `--print-plan` passed. Full deployment deliberately excludes the
  profiled fork/archive service; the documented explicit post-deploy startup
  remains necessary for its already-running old consumer. Setting
  `COMPOSE_PROFILES` does not override that deployment-script exclusion.
- Candidate `140dc09d1` and its five preceding run-catalog commits were pushed
  to the existing origin/master for canonical deployment retrieval. Forest's
  uncommitted local scheduler activation was not pushed.

## Safe stop

At 2026-10-01 03:13 UTC, the exact no-argument
`scripts/deploy-production.sh` stopped at its fast-forward guard. Its fetch of
`origin/feature/project-owned-config` returned `2e60d9e64`, which does not
descend from local `253188229`. No application image build, restart, migration,
catalog activation or read cutover occurred on forest1. The script fetched
refs and retained its private pre-pull configuration snapshot only.

Asked the operator for explicit authority to switch forest1 to the existing
master branch and deploy the candidate without resetting or discarding the
feature branch. The operator subsequently approved switching to master. Do not
bypass the canonical pull guard with `--skip-pull` or change tracking silently.

The attempted pre-deploy browser login found no local password login form.
No credentials were submitted and no login configuration was changed. Existing
dev-agent credentials are absent on forest1; OAuth/browser witness remains
unverified, not represented by forest's earlier login evidence.

## Authorized resumption

The operator explicitly approved the switch to existing master. The feature
branch remains intact at `253188229`; no reset, deletion or force update was
used. Repeated idle-job checks passed and the canonical no-argument deployment
was resumed on master and fast-forwarded to `140dc09d1`.

## Runtime gate failure and containment

The first master rollout built the images and passed web/rq-engine health and
CAP challenge/redeem/siteverify. Its final stability check correctly failed:
browse/download restarted repeatedly because importing shared rq-engine auth
ran `initialize_project_commits()` at package import without their having any
PostgreSQL secrets. This is a catalog regression, not an operator-secret issue.
No credentials, login defaults or authorization rules were changed.

The canonical failure handler restored the known-good CAP rescue image and
released its global RQ fence; dequeue is not suspended. Web/rq-engine remain
on the candidate, in legacy-read/timestamp-only staging mode. No catalog schema
migration, sweep activation or SQL read cutover occurred.

At approximately 04:01 UTC, browse/download alone were restored using the
existing production `wctl` Compose preset and exact retained pre-deploy image
`sha256:1debf8406a7ea3c6dc57fdab1a343aca4785d0844ec68567103435f40b30f262`.
This image remained in use by the untouched profiled fork/archive worker.
No new image was built or published for recovery; no project data was rolled
back. This mixed-version containment is not successful deployment acceptance.

Prepared a root fix moving rq-engine initialization to its ASGI lifespan.
Targeted startup/polling tests passed 48 cases; a real browse-container import
with postgres mode and removed SQL credentials passed. Broader microservice
validation passed 1,543 tests in 44.50 seconds. A full-suite sanity run was
started with output at `/tmp/forest1-catalog-startup-full-tests.log`; its result
stopped at a stale fork/archive secret-list assertion: 319 passed, 28 skipped,
one failed. The assertion omitted the catalog's required PostgreSQL secret;
update it without changing runtime permissions. Commit/redeploy approval was
requested explicitly and subsequently granted, including the activation switch.

Post-containment checks: browse/download/web/rq-engine/CAP are running with zero
restarts; download, web and CAP report healthy. The current service recovery
does not waive the failed uniform-candidate deployment gate.

A separate activation gap was found: the disabled schedule is baked into the
production image and its config path is fixed by Compose. Requested approval
for a tested environment-variable activation switch; do not patch running
containers or silently enable sweeps globally as a workaround. Browser/OAuth
verification and the second no-argument deploy remain uncompleted.

## Authorized repair candidate

The operator approved committing/redeploying the ASGI startup fix and adding a
host-local activation switch. The baked schedule now resolves
`WEPPCLOUD_RUN_CATALOG_SWEEP_ENABLED`, default false, using strict boolean
validation. Forest's gitignored environment selects true; recreating its
scheduler confirmed the actual loaded task remains enabled. No other host is
enabled by this default. Focused startup/scheduler/topology tests passed 33
cases; all changed Markdown passed lint. The broader sanity suite was rerun
after updating the stale PostgreSQL-secret assertion. Forest1's four batch,
six default and one fork/archive workers were idle with empty started registries
before the repair rollout.

## Repair deployment and shadow activation — 05:47 UTC

Candidate `2f61fb1e5` was committed and pushed with operator approval. Two
successive no-argument `scripts/deploy-production.sh` invocations completed
successfully: the repair staging deployment and the catalog-write deployment.
Both passed CAP challenge/redeem/siteverify, candidate-image checks and service
restart stability; both resumed global RQ dequeue. Logs are retained locally at
`/tmp/forest1-catalog-repair-deploy.log` and
`/tmp/forest1-catalog-shadow-deploy.log`. This replaces the mixed-image containment.

Between deployments, inspected current/head revisions and applied the additive
upgrade from `c91f6b2a4d7e` to `d30c91a7b802`. The existing verified pre-catalog
database backup remains retained. Host-local settings now select postgres
commit integration, catalog writes and **legacy reads**. Sweeps remained off
through both deployments and consumer proof. The full deployment intentionally
excludes the profiled fork/archive worker; explicitly recreated it with
`wctl docker compose --profile fork-archive up -d --no-deps rq-worker-fork-archive`.
The installed wrapper does not accept `wctl --profile`; that initial invocation
failed before any action. No separate forest companion or wepp1 was changed.

Web, rq-engine, default/batch/fork-archive workers and scheduler all run image
`sha256:00abcd7d72126f5d342d4bd5899c91464705adacd31b3344f1b44fdd815d52f2`,
with approved `/wc1` and `/wc1/geodata` to `/geodata` mounts. All four local
batch workers, PIDs 362–365, passed held-nonce false/control-nonce true origin
proof using each actual `/proc/<pid>/environ`, separate adapter connections,
UID 1000/GID 993/groups 993/umask 0022. Both source roots were readable. The
web coordinator retained its transaction throughout and explicitly released it
after all probes. Configuration admission reports four compatible consumers.

Then set `WEPPCLOUD_RUN_CATALOG_SWEEP_ENABLED=true` in forest1's gitignored
environment and recreated only the scheduler. Scheduled bounded backfill covered
all 200 registrations: 41 ready, 159 known unavailable, zero dirty/pending,
transient failures or unreconciled rows. Every individual source comparison
matched. The [shadow manifest](2026-10-01_forest1_shadow.json) retains omission
IDs and source classifications without project paths or credentials.

Direct application-context legacy-versus-SQL table/map comparisons passed for
all seven registered accounts, including the principal scope's 156 registrations,
32 returned and 124 unavailable. See [reader parity](2026-10-01_forest1_reader_parity.json).
These are internal reader checks, **not authenticated HTTPS or browser evidence**.
Technical preflight returned true with no failures and a completed scheduled
sweep (empty batch: 47 ms queue delay, 63 ms execution); operator evidence remains required.
Browse/download/web/rq-engine/CAP have zero restarts; download/web/CAP are healthy.
The public login page returns HTTP 200; login settings and credentials are unchanged.

## Current hold

SQL read cutover is not performed. Requested an operator OAuth login and runs
table/map witness; no usable forest1 automation credentials exist. Real
authenticated mutation-to-browser evidence, browser timing, RQ/DEVAL/rollback
rehearsal and unmeasured recovery behavior remain open. The fixed nonproduction
48-hour wait is waived, not these correctness checks. Production promotion is
neither authorized nor claimed.

Focused repair tests passed 33 cases and the broader microservice suite passed
1,543 cases. RQ dependency graph and changed broad-exception gates pass. The
full sanity rerun stopped after 4,813 passes and 51 skips at
`test_disabled_is_inert`: it removed commit mode but inherited forest's active
write/read settings. An initial targeted isolation fix passed 37 cases,
including this regression. The full suite has not passed end-to-end;
its log remains `/tmp/catalog-activation-full-tests.log`.
The broader RQ/catalog/tools/microservice selection exposed the same leak in
Redis-only cancellation and worker-death tests. Root cause: the shared test
fixture strips SQL secrets but left deployment modes active. Consolidated mode
isolation into that existing root fixture, removing the now-redundant local
microservice fixture and per-test attempts. Tests needing integration explicitly
set their modes. This grants no credentials and preserves worker fail-fast
behavior; it is test isolation, not a second runtime fix.

Final combined NoDb observer, RQ, catalog SQL/file/reader, tools and microservice
validation passed **3,060 tests**, with 29 skips, in 235.71 seconds after the
shared isolation correction. Both exposed worker tests pass. Deployment runtime
remains `2f61fb1e5`; the follow-up commit changes only tests and retained evidence,
so no additional runtime rebuild is needed. Documentation lint and diff checks pass.
