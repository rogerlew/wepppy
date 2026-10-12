# Forest1 deployment — 2026-10-11

## Authorization and release

The operator authorized forest1 deployment after review; wepp1 is excluded.
Deploy WEPPpy `29868fe65b13e3efa4d61cdd89551510706bb519` from clean
forest1 master `2f61fb1e5400a7e2d13891765b00c04a1ac4cf88` using
`scripts/deploy-production.sh --no-flush-rq-db --skip-docker-prune`.
Preserve legacy catalog reads and existing identities/mounts. Local development
management CSV edits are excluded. No feature memberships or onboarding
acceptances are fabricated as part of schema installation.

## Compatibility and regression plan

The account database starts at `d30c91a7b802`, with seven accounts, five roles,
and 201 registered runs. Restore a fresh full database dump into a disposable
database and compare revision/counts before applying `e7a1c9d204bf`.
Stage candidate migration files under a temporary path in the old app container;
the reviewed upgrade creates four tables and six groups without relying on new
application models. Existing consumers remain compatible with the additive schema.
Read back revision, constraints, groups, and unchanged existing counts.

Rebuild through the canonical deploy entry point. Check native interchange hash
`06319303a2337cc75a3c57eb594161565d8a2af1d58cee18c17abcfe6eea8cf8`,
paired with published WEPPpyo3 `bd630941e9f5d45b926291429ccc87c7cc92bae7`.
Preserve existing image IDs with rollback tags. Coordinate the separately profiled
fork/archive worker; prevent mixed-version request admission at activation.
Validate health, CAP functional canary, secret readability, identities, PRISM
cache writes, model-generated artifacts, authorization boundaries, and catalog
consumer compatibility before resuming catalog sweeps. Keep SQL reads disabled.

## Recovery

Retain database backup and previous environment/configuration outside git with
restricted permissions. Application rollback retains the additive schema and
access history: migration downgrade is deliberately unsupported. Preserve Redis
and rollback images. Do not restore a database over newly accepted writes as an
application rollback shortcut. If activation fails, keep admission closed until
the prior coherent service set or repaired candidate passes validation.

## Evidence and outcome

The full backup restored successfully; its SHA-256 is
`308d99bd4a9352fd4767f67d5ede17ffe082b5df007185a72330919bc266fef2`.
The migration passed on the restored copy and then on the live database, with
unchanged account/role/run counts, six active groups, thirteen constraints,
and zero membership/event/acceptance rows. The disposable database was removed.
Evidence and rollback tags are retained under
`/var/tmp/forest1-deploy-20261011` on forest1.

The first canonical build failed before cutover: the mutable Arrow `latest`
package changed, correctly failing the pinned SHA-256 check. The bounded repair
changes only `weppcloudR/Dockerfile`'s URL to Apache's versioned
`apache-arrow-apt-source_25.0.1-1_all.deb`, whose downloaded SHA-256 exactly matches
the existing `9ef1afbcca1705ddd6f358672deb5ba4f858b248144ef6356d4b8f4788ac1fda`.
No dependency version or checksum changes. The deployed release includes this
explicit URL-only patch above the candidate commit; retain the patch until its
normal source integration, then retire host-local drift after direct comparison.

The retry uses `--skip-pull --no-flush-rq-db --skip-docker-prune` with the
URL-only patch. Its existing `WEPPCLOUDR_RUNTIME_VALIDATOR` extension point
runs the canonical renderer validator, the native hash check, a fresh model
artifact probe, and secret-readability checks before stopping old request
consumers and the excluded fork/archive worker. The temporary validator is
outside the checkout; the repository deployment script is unchanged.

At 03:22 UTC the gate passed: renderer owner-only data access as `1000:993`,
the required native-reader hash, the expected WEPP 261010 hash, 1,095 parsed
daily records spanning simulation years 1–3, nonnegative finite water outputs,
and PRISM cache write/read. Fresh evidence is retained at
`/wc1/deployment-validation/20261011/model-hy2zsrj4/verification.json`.
Browse, D-Tale, Query Engine, and batch-worker database/Redis secret reads and
Query Engine JWT-secret access passed under `1000:993`. No started entries
were present in default, batch, or fork-archive immediately before cutover.

## Final outcome — 03:27 UTC

Canonical deployment completed successfully and released its RQ suspension.
The application image is
`sha256:07443fff2d0efc76267d9c7c8f1ea2b8be8ac26089ea4f803b63651bdb6382a8`.
All 24 active default-profile services passed candidate image/state checks with
zero restarts; the separately recreated fork/archive worker also uses this image,
has zero restarts, and registered idle on its queue. Existing unrelated host
containers were preserved. Source checkout has only the recorded Dockerfile URL
patch above the release commit.

The queued job `forest1_deploy_20261011_model_smoke` finished successfully.
Its model output at `/wc1/deployment-validation/20261011/model-kkyd_krw` has the
same PASS bytes and equivalent parsed daily values as the pre-cutover probe.
The result includes 1,095 records for years 1–3, UID/GID `1000:993`, and successful
PRISM cache write/read. This is a bounded RQ/model fixture, not a claim that every
user project, climate source, dashboard, or archive workflow was rerun.

Live HTTPS login, RQ, CAP, Query Engine, and Browse returned HTTP 200. Public
download, D-Tale launch, and declared dataset query passed; the query returned
the expected record `{id: 1, value: 1.25}`. Private anonymous download and D-Tale
launch returned 401 without exposing canary contents. The two synthetic batch
fixture directories were removed after validation; model evidence remains.

Four batch consumers passed held-lock/control-lock database-origin probes from
their actual process environments, with approved source roots readable. Restored
`WEPPCLOUD_RUN_CATALOG_SWEEP_ENABLED=true` in host configuration and recreated
only the scheduler after proof. A new scheduled sweep completed at
`2026-10-11T03:27:42.783568+00:00`, without failures. Catalog status: 201 registered
and projected, 42 ready, 159 previously known unavailable, zero dirty/pending/
transient-error/unreconciled rows, four eligible and zero incompatible consumers.
Reads remain `legacy`; writes remain `catalog`; commit integration is `postgres`.
`PRISM_CACHE_DIR=/wc1/cache/prism` is active in web and all workers. The sweep
flag is consumed by the scheduler; other containers retain its false snapshot
from cutover without controlling dispatch.

The real account evaluator confirms empty OpenET/Batch groups deny actions,
Root's existing Omni Contrasts role path remains allowed, and ordinary retained
result inspection remains allowed. At the initial deployment handoff, maintainer
membership initialization and an operator OAuth/Runs browser witness were pending;
the follow-up below records their disposition. No catalog SQL read cutover was
performed. Wepp1 is unchanged.

Initial and final observed queue snapshots had zero queued/started entries in
default, batch, and fork-archive. The installed `rq-info --detailed` command is
incompatible with RQ; use direct Redis reads for queue evidence. Flask CLI also
emits a preexisting optional profile-coverage path permission warning and a
missing `.git` notice in baked images; neither prevented the migration or checks.

Retained host evidence includes `deploy.log`, `deploy-retry.log`,
`migration-readback.txt`, `services-after.json`, `catalog-origin-proof.json`,
`catalog-status-after-resume.json`, `public-boundaries.json`,
`feature-decisions.json`, and `rq-model-proof.json`. Backup/configuration artifacts
remain restricted under the same evidence directory. Before a subsequent pull,
integrate the URL-only source repair and retire the identical host-local patch;
do not discard unrelated worktree changes.

## Operator acceptance and authorized memberships — 2026-10-12 05:20 UTC

On October 11 Pacific time, the operator confirmed OAuth and the Runs table
functional, and explicitly authorized OpenET/Batch access for
`rogerlew@gmail.com` on forest1. This confirms those browser surfaces; a separate
Runs map witness or SQL read-cutover acceptance is not inferred.

Executed the documented `flask --app wepppy.weppcloud.app admin
initialize-feature-access --email rogerlew@gmail.com --reason ...` command through
`wctl exec -T weppcloud`, after checking host identity and the retained verified
backup. The command resolved forest1 account 1 and created only `batch_runner`
and `openet_ts` memberships. Audit events 1 and 2 retain the explicit operator
authorization and continuing resource-stewardship rationale. Both memberships
have no review/expiration date, matching the documented continuing-maintainer
initialization; roles and other groups were unchanged.

Readback confirms both memberships effective. The current internal onboarding
statement has not been acknowledged, so both action decisions correctly return
`internal_acknowledgment_required`. The account holder must accept the statement
in Profile; operator authorization of memberships does not fabricate that personal
acceptance. Retained evidence: `maintainer-initialization.log` and
`maintainer-readback.json` in the forest1 deployment evidence directory.
