# Development runtime acceptance preparation

Status: preparation only; no rebuild, restart or final canary completed.
Current implementation wave:36744f3b3. Final acceptance must use the final code
revision after the remaining confirmed consumers are dispositioned.

## Authority and environment

Owner authorized executing this package, including development-stack acceptance
on disposable projects. Named source projects stay read-only; do not submit a
model job, export or cleanup against them. No production deployment is included.
The installed dev wctl preset and `docker/docker-compose.dev.yml` are canonical.
The shared image is built from `docker/Dockerfile.dev`; shared Python services
run as configured UID/GID, normally1000:993, with `/workdir/wepppy` mounted.
Inspect effective service state, active jobs, mounts, groups and umask immediately
before restart; retain baseline and recovery evidence. Do not restart an active
unrelated job merely to satisfy the acceptance schedule.

Reviewed operator skill `.codex/skills/rq-agent-operator/SKILL.md`, applicable
Docker/WCTL/smoke AGENTS, API auth/job/climate ordering contract sections, frozen
inventory/checklist entries and the controller-state smoke runbook. Runtime
operation discovery remains authoritative for exact request fields/defaults.
Use existing gitignored `docker/secrets/dev-agent.env`; do not print credentials,
cookies, bearer tokens or token-bearing response bodies. Do not reset the agent
account if the existing credentials work.

## Delivery sequence

After final focused/full checks, inspect `wctl --help` and effective Compose
services, rebuild the affected shared image/services and regenerate browser
assets through `wctl build-static-assets` when applicable. Use the installed
wctl orchestration path; retain exact command, revision, service/image IDs and
health results. Restart/recreate affected web, rq-engine, worker, query and
D-Tale consumers as their actual import/image boundary requires. Redis/database
contents are retained. A healthy restart alone is not an acceptance result.

Use a unique disposable run identity and preserve a manifest of its source and
initial hashes. Complete normal UI/API discovery, climate build, post-fire
assessment and WEPP preparation/execution. Record job trees, terminal outcomes,
source links/hashes and accepted output identities. Verify unchanged CLI hard
links leave the assessment current. Replace climate through its supported
workflow; require invalidation, rerun and current new results. Inspect state,
preflight, report, downloads and a browser reload across actual services.

For every changed consumer, exercise its actual owner boundary: NoDb reload in
separate processes; served/rendered bundle IDs; native derived publication;
features primary/companion exports and failed-attempt retention; D-Tale page/map
source changes; report cache rebuild/current/historical behavior; CLI lineage
and private attempt browsing. Add the remaining implemented raster/Omni/profile/
browser paths to this matrix before final acceptance. Isolated helper tests do
not substitute for these owner paths.

Run canonical archive and restore on disposable copies, retaining accepted,
failed and intermediate artifact bytes and permissions. Recheck decisions and
ordinary browsing after restore. Include two interleaved representative post-fire
working sets for the bounded digest cache, recording digest misses/read bytes and
whole-state timings. No mass cache deletion or named-project rerun is a test.

## API evidence contract

Discover `/api/configs`, `/api/endpoints`, operation schema and then run-scoped
pipeline/readiness and operation docs before submission. Resolve current climate
catalog/station/spatial authority; do not invent fields or replay undefined mode.
Log UTC method/path/status with redacted request/result evidence. Poll the returned
job/status URL; only `finished` is terminal success. `failed`, `stopped` and
`canceled` require retained jobinfo/error evidence, and404 is not success. After
each terminal job, reread pipeline/readiness and verify generated artifacts.
Follow operation error catalogs for recovery; preserve the original failure.


Runtime preparation update: the canonical dev image built successfully as
`sha256:00a3e43a88a5c9079a7e58a8423432d69f22b7b09c0a9288078b67abbca1d3f8`.
Sixteen running shared-image service identities/mounts are retained before
restart. The first fullsuite stopped after3881passes/51skips on the unchanged
simulated HTTP timing assertion (1.2377s versus1s) during build/copy work.
The isolated quiet rerun passed; a complete quiet rerun is now running, with
native acceptance still held. No assertion was relaxed. The full independent
canary copy has3916files/6,375,730,842logical bytes and no shared source inodes at
`/wc1/runs/qa/qa-freshness-runtime-7e24c8d1`; original source hashes and versions
are in its retained copy manifest. Browser login/setup and run-scoped discovery
succeeded. An initial config-token0 GET returned404; the stored config stem is
`config`, whose pipeline/readiness/schema calls return200. No model job has yet
been submitted. S02 canonical cookie-only playback has a separately reviewed
pre-existing bearer-auth mismatch; actual per-request failure evidence and an
authorized Session HTTP control will be retained after restart.
