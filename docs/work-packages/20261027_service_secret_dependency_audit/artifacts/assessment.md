# Shared service secret assessment

Assessment date: 2026-10-27 UTC. Baseline: `917fa52cf`; candidate is the scoped working-tree changes in this package. Production deployment is held. This assesses repository-owned configuration for the missing Flask/database secret failure class; it does not claim all authentication failures are eliminated.

## Broken assumption and search boundary

Every process reaching the shared Flask app, including lazy imports during ownership and legacy identity resolution, must receive Flask key, password salt, Redis and database configuration. Database-only consumers need their own database credentials, not necessarily Flask secrets.

Searched all Python sources for direct `wepppy.weppcloud.app` imports, `get_run_owners_lazy`, `get_user_models`, shared RQ/browse authorization, feature identity callbacks and task consumers. Followed indirect paths into download, D-Tale and query-engine. Parsed all ten `docker/docker-compose*.yml` files, including overrides; inspected entrypoints and restricted worker queues. No repository Kubernetes/Helm deployment YAML was found; the web-runtime contract contains a Kubernetes example with explicit Flask bindings, not a deployable browse topology. External openwepp manifests and host-local overrides are outside this checkout and remain rollout verification responsibilities.

Historical evidence: `46d97c8ec` made Flask secrets required; `796f680ac` replaced shared `.env` with per-service secret files; `9710b762d` repaired worker imports but omitted peer consumers. The reported wepp1 error at 2026-10-26 16:31:10 PDT occurred on `/weppcloud/runs/mdobre-shattering-jockey/cfg/aria2c.spec`. `917fa52cf` repaired dev/prod browse alone.

## Consumer matrix

| Consumer / variants | Dependency and original state | Disposition / repair | Evidence boundary |
| --- | --- | --- | --- |
| browse: dev, prod | `authorize_run_request` → RQ `_authorize_user_claims` → `get_run_owners_lazy` → Flask; bindings added in `917fa52cf` | Previously confirmed defect, patched | Candidate private owner HTTP spec plus unrelated-user denial; no privileged role claims |
| browse: dev.hpc | Same code; both Flask bindings absent | Confirmed defect; add both existing mounts and file variables | Source configuration check; legacy HPC is not a supported deployment target |
| download: dev, prod | `archive_download` → browse auth → same ownership path; Flask and Postgres bindings absent | Confirmed defect; add key, salt and Postgres bindings | Candidate private archive range request validates actual bytes and unrelated-user denial |
| D-Tale: dev, prod, dev.hpc | `_reauthorize_private_scope` → RQ user auth → Flask; key/salt absent, Postgres present | Confirmed defect; add both Flask bindings | Real capability reauthorization with owner allowed and unrelated user rejected; not full browser UI proof |
| query-engine: dev, prod, dev.hpc | `feature_access.require_root` → `require_feature_access` → `verified_principal` → legacy MCP `_resolve_user_id_from_fs_uniquifier` → `get_user_models` → Flask; key/salt absent | Confirmed defect; add both Flask bindings | Real legacy MCP identity lookup, known identity resolved and unknown rejected; not full MCP transport proof |
| weppcloud, rq-engine: dev, prod, dev.hpc | Direct Flask or session/ownership imports; key/salt/Postgres already mounted | Verified unaffected for missing binding class | Source topology validation; existing consumers unchanged |
| rq-worker, rq-worker-batch: dev, prod, dev.hpc, prod.worker | Run-sync/delete/bootstrap tasks import Flask; required bindings already mounted | Verified unaffected for missing binding class | Source validation, including worker base anchors; March repair retained |
| rq-worker-fork-archive: dev, prod, prod.wepp3 | Restricted fork/archive tasks; imports project module but used preference helpers do not import Flask; ownership registration happens in rq-engine | Verified unaffected in inspected queue paths; no new Flask mounts | Trace `fork_rq`, `_finish_fork_rq`, archive/restore delegation; Postgres/Redis already mounted for persistence |
| scheduler: dev, prod, dev.hpc | Imports/enqueues task functions and invokes database catalog scheduling; does not execute Flask-dependent task bodies | Verified unaffected in inspected schedule | `docker/scheduled-tasks.yml`, `wepppy/tools/scheduler.py`; Postgres/Redis bindings present |
| profile-playback: dev, prod, dev.hpc | HTTP client/workflow orchestration, no reachable Flask app import found | Verified unaffected for this class | Source search and entrypoint review; no Flask mounts added |
| Other services: fcgiwrap, caddy, cap, redis, postgres, postgres-backup, rq-dashboard, weppcloudr, elevationquery, metquery, wmesque, wmesque2, shape-converter, status, preflight, status-build, preflight-build, webpush | Separate entrypoints; no reachable shared Flask consumer found | Verified unaffected within searched entrypoints | Broad import/caller search; do not grant Flask secrets to the shared image globally |
| prod.wepp1, prod.worker.override, prod.worker.forest.override | Override hosts/mounts/runtime settings; do not remove Flask secret bindings | Verified unaffected at source | Effective rendered configuration must still pass deploy gate |
| test, canary-smoke | Explicit disposable inline Flask key/salt/database configuration | Verified unaffected | Source configuration test preserves these intentional isolated harness contracts |
| Maintenance scripts: WEPPcloud `_scripts`, `tools/rotate_user_fs_uniquifier.py`, `tools/surf14a_local_acceptance.py` | Direct Flask app imports; no separate Compose service | Existing web-container bindings cover configured execution; standalone operator environments unresolved | Same web runtime requirements apply; a host virtualenv alone is not configuration evidence |
| Host-local overrides and external deployment manifests | Not all are available in checkout | Unresolved outside repository scope | Deploy checks effective rendered Compose; exact-host acceptance still required before rollout |

## Validation and limitations

The new `validate-runtime-config` command in `scripts/compose_deploy_contract.py` checks known consumers, binding presence and matching declared mounts in effective Compose JSON. `scripts/deploy-production.sh` invokes it before build/cutover for the selected recreate set; targeted CAP/web retains its narrow scope. It never prints secret values. It is a configuration gate, not a replacement for file-readability or end-user acceptance.

Regression coverage removes required bindings, removes mount targets, supplies undefined secrets and empty values, verifies nonconsumers/database-only services remain valid, checks seven base topologies, and proves deploy planning rejects an invalid browse definition. Targeted tests: 62 passed before final review.

Local probes use `wctl docker compose run --rm --no-deps -T SERVICE python .../consumer_probe.py SERVICE qcat-archive-20261023` on Forest with an existing private run and real database/Redis. The script does not create accounts, mutate project data or print credentials. It uses user-class claims with no admin/root roles. Response contents, not status alone, are checked for spec and range-download artifacts. Probe results and remaining limitations are recorded below as execution completes.

A production rollout must validate the exact candidate revision, service identities, secret readability and real normal-user request paths on each changed host. No source test or disposable Forest container establishes production resolution. No production restart or deploy is authorized by this package.

## Review-discovered second boundary

The independent review reproduced D-Tale's real request context failing after
secrets were supplied: `RuntimeError: The current Flask app is not registered
with this SQLAlchemy instance`. `has_app_context()` did not establish that the
current app owned WEPPcloud's ORM. Repair `get_run_owners_lazy` and both shared
session identity/role lookup helpers to reuse only WEPPcloud's actual app context,
otherwise enter it temporarily. This restores existing ordinary-owner and
current-identity behavior under `docs/schemas/weppcloud-browse-auth-contract.md`
and `docs/schemas/weppcloud-session-contract.md`; no token or authorization rule
is amended.

The same-assumption search covered every `has_app_context` branch. Preferences
run in WEPPcloud or ASGI rq-engine; admin submitter hydration runs in ASGI;
delete/GC runs in workers. No current foreign-Flask consumer was found for those
branches, so they are verified unaffected within these entrypoints and unchanged.
D-Tale can reach both ownership and legacy identity resolution, so both are
patched. Regression tests use real Flask apps and SQLite ORM queries across no
context, own context and a foreign request context, and check caller restoration.

## Candidate evidence

Forest disposable containers use UID 1000/GID 993 and candidate bind-mounted
source. Browse: private spec HTTP 200, nonempty download URLs, unrelated user 403.
Download: private archive range HTTP 206, exact first 16 bytes match the on-disk
ZIP, unrelated user 403. Query-engine: legacy MCP identity resolves an existing
account and rejects an unknown identity. Initial D-Tale probe passed outside its
request context but was insufficient; the corrected request-context probe is the
acceptance evidence. This distinction is retained rather than treating the early
passing probe as proof.

Final local request-context probe: D-Tale owner capability accepted, unrelated
capability rejected, legacy identity lookup passed inside D-Tale's request context.
Independent cold probe imported D-Tale before WEPPcloud and confirmed the same
boundary plus caller-context restoration (see independent review artifacts).
Final focused aggregate: **218 passed**, covering deployment execution/planning,
configuration inventory, foreign app contexts, session routes and browse auth.
`wctl check-test-stubs`, broad-exception delta enforcement, docs lint and root
160-line limit passed. Baseline configurations at `917fa52cf` fail the new gate
for every newly repaired service group. Candidate source hashes are retained in
`candidate_sources.json`; tests use the same bind-mounted sources. Broad sanity
suite disposition is recorded below.

Final probes were repeated using an existing active unrelated account (not merely an unknown subject); owner success and nonowner rejection remain green. No privileged roles were placed in either credential.

## Broad-suite browser prerequisite and peer repair

The broad run reached `test_real_file_sql_http_browser_chain` after 11,645 passes
and 181 skips, then failed before launching Chromium: development Compose set
`PLAYWRIGHT_BROWSERS_PATH` to `/workdir/wepppy/weppcloud/static-src/.playwright-browsers`,
missing the second `wepppy` path component. The installed executable exists under
`/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers`.

Applied the failure-class rule immediately: searched every browser path definition,
found the identical typo in dev.hpc, and corrected both. `tools/wctl2` uses the
correct relative cache under static-src; `docker/Dockerfile.test` installs its
browsers into its separately configured `/opt/wepppy-ci/browsers` path. Production
Compose does not set this test-cache override. No browser installation, service
restart, or test assertion relaxation was needed. The 176-node suffix, including the failed test, passed when rerun in a disposable web container using the candidate
Compose environment; node IDs are retained in `broad_tail_nodes.txt`.

Broad validation totals across the passing prefix and rerun suffix: **11,821 passed,
181 skipped**. This is segmented coverage, not a single uninterrupted green run.
The strengthened persisted-role/context-restoration fixture also passed its
61-test focused rerun. Security, correctness and separate QA reviews all pass.
