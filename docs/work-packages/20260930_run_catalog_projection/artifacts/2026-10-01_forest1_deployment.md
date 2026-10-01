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
