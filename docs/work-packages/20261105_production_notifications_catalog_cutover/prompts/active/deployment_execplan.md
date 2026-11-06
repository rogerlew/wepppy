# Deploy notifications and asynchronous query catalogs to production

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain
Progress, Surprises & Discoveries, Decision Log, Outcomes & Retrospective and the
package tracker at every milestone. Authority is the operator's November 6 UTC
instruction to create this work package and proceed with deployment.

## Purpose / Big Picture

Production users receive a quiet per-account inbox with recorded TTL warnings,
while eligible artifact writers request asynchronous catalog refresh without
blocking request handling on native scans. All production consumers use the
compatible published application/native/RQ release, including five new-project
config defaults selected in user commit 2111d0eb2. Existing projects keep their
persisted binary selections. GC stays paused and the separate PostgreSQL Runs
catalog remains legacy/timestamp-only with its sweep disabled.

## Progress

- [x] (2026-11-06 UTC) Initial three-repository/fleet inspection and wepp1 cleanup.
- [x] (2026-11-06 UTC) Operator ratified combined deployment and new defaults.
- [x] M0: concrete controls, independent review and private baseline checkpoint.
- [x] M1: scheduler repair and candidate validation/publication (8d079b41d).
- [x] M2: backup, schema rehearsal and production migration (2026-11-06 06:34 UTC).
- [x] M3: compatible fleet activation and model/runtime acceptance (2026-11-06 07:24 UTC).
- [x] M4: notification preflight, activation and scheduled/browser readback (2026-11-06 07:44 UTC).
- [ ] M5: default-worker pilot and bounded general catalog observation.
- [ ] M6: final independent review, fixture cleanup and package closure.

## Surprises & Discoveries

The catalog scheduler still passes batch while the October 28 code requires
default. The prior regression passed a handwritten batch task to a stub and
missed the real configuration boundary. Production wctl merges .env inputs into
the existing service env_file; render-only proof showed the notification flag
passes without adding Compose wiring. wepp2 batch registration differs from its
running process count. Root disk cleanup recovered 195.5 GB on wepp1 and preserved
all containers/tagged images. The current fleet still runs RQ 1.16.2 and the
candidate upgrades to 2.12.0; mixed execution/reverse state compatibility is not
supported. The canonical script resumes its own global fence per host.

Final mount preflight found the scheduler alone inherited generic host sources
`/wc1` and `/wc1/geodata`; all active project consumers use `/geodata/wc1` and
`/geodata`. Catalog reconciliation runs directly in the scheduler, unlike the
queued notification producer. It recorded all four namespaces unavailable while
workers validated all seven locators. Keep admission paused until the one-line
wepp1 volume-anchor correction passes runtime parity. Dormant webpush/scale-zero
fork workers are inactive cases; shape-converter's empty mounts preserve isolation.

## Decision Log

2026-11-06 UTC / operator and Codex: permanently remove only wepp1's repository-local forced LFS access=basic setting after controlled tests isolated it; preserve credential helpers, TLS and client selection. Normal uncached filters passed.

2026-11-06 UTC / Codex and independent reviewers: the exact scheduler mount-source
correction fits the authorized deployment prerequisite repair and scheduler-only
recreation. Preserve image, identity, secrets, command, destinations and RW mode;
change only the two host sources to the established wepp1 mappings. Retain old
configuration/container evidence; prove merged-config scope, same-image one-off
root/coordination inode parity, then actual recreated runtime visibility. Keep
owned admission pause throughout; let normal reconciliation clear availability
state. Immediate containment is scheduler stop plus retained pause, never reset
catalog state. This does not expand the unrelated wepp3 archive mount boundary.

2026-11-06 UTC / operator: proceed with the combined production deployment as a
work package, including 2111d0eb2 and ADR-0138. Use the approved readiness sequence,
with scoped worker holds and scheduler recreation where the canonical script
cannot express that bounded operation. Continue without routine confirmation.
2026-11-06 UTC / Codex: repair scheduler queue to the existing default contract;
use actual YAML plus admission-boundary regression. Preserve existing deployment
mechanics and all unrelated work. Independent reviewers own correctness/security
dispositions. Treat whole-cycle observation as required evidence, not a forecast.

## Outcomes & Retrospective

Published candidate 8d079b41d is clean on all three hosts. Full pytest passed:
13,361 passed, 281 skipped; focused, deployment, frontend and documentation gates
passed. The permanent wepp1 LFS configuration repair passed uncached fetch and
normal checkout-filter verification; see docs/infrastructure/wepp1-git-lfs.md.
All eight old runtime containers are stopped, with exact-ID receipts retained.
Quiescent PostgreSQL and Redis recovery snapshots exist privately on wepp1.
The two independently proven completed permits were retired with pilot bytes
unchanged. Production migration reached f6b8d27a901c with existing counts unchanged
(5,416 users; 33,444 runs; 9,444 ownership rows; 11 feature memberships).
Canonical deployments completed on all three hosts; code/native manifests match.
Twelve default/eight batch registrations and matching native/runtime manifests
are verified. Scoped notification population and inbox/history browser checks passed.
All 18 owned-model jobs passed; 25 fresh Parquet files (706,190 rows), native execution hashes, strict reports, browser CSV and archive/restore byte parity passed.
The fresh default-worker pilot completed both waves on eight scopes with actual
query readback, unchanged source/sentinel and observed model waits below 0.13 seconds.
Notification scheduling enabled at 07:12 UTC; the actual scheduled sweep created
4,992 production notices and preserved the fixture warning's read state and TTL.
Scheduled browser acceptance passed. At 07:56 UTC the owned fixture and its 101
notices were removed, retaining all production notices. General configuration is
true and converged on all three hosts after their second canonical rollouts.
Scheduler mount correction 51e1f2345 passed same-image preflight and actual runtime
root/inode checks, with all 24 other container identities preserved. Scheduler
restarted at 08:28:43 UTC; normal ticks cleared namespace unavailability under
the retained admission pause. General observation remains open.

## Context and Orientation

The canonical deploy script is `scripts/deploy-production.sh`, selected by each
host's installed wctl preset. wepp1 uses docker-compose.prod.yml plus prod.wepp1;
wepp2 is the worker stack; wepp3 owns only rq-worker-fork-archive. Actual run storage
is /geodata/wc1 on hosts and /wc1 in containers. Runtime identity is 1002:130.
Candidate baseline is 2111d0eb2; published Rust source is 5e3540f and installed
interchange hash must match docker/wepppyo3-interchange-preflight.py. Native
WEPP 261029 revision 7 is vendored with matching sidecars. Host native checkouts
are not build sources. Production initial application baseline is 0da9c9071.

Notification migration f6b8d27a901c follows e7a1c9d204bf and is additive. Population
uses batch and explicit trusted registration scopes for preflight. Catalog code
uses default, twelve expected consumers, a seven-job global maintenance cap and
ordinary waiting-work deferral. Its historically named batch ledger and receipts
must survive migration. Four namespaces include legacy projects; guard storage
is outside replaceable project trees. Readiness notes retain exact baseline.

## M0 — Freeze scope and concrete controls

Move the assessment with wctl doc-mv, establish package/tracker and root board
entry, and obtain independent correctness/security review. Inspect and retain
canonical script, effective presets, host/container identity, image IDs, process
UID/GID/groups/umask and mounts without exposing secrets. Use direct non-cleaning
Redis reads; the skill's old --detailed wrapper option is unsuitable. Refresh
started-job checks on default, batch and fork-archive before mutation.

Diagnose missing wepp2 batch registration from filtered logs/metadata without
printing process command lines containing Redis URLs. Preserve working jobs and
held locks. Do not fabricate registrations. Prepare bounded remote warm-stop,
owned maintenance admission controls, per-host canonical commands and exact
recovery controls before activation. User approval covers the described scope;
if a necessary operation expands topology/identity or destroys accepted work,
retain the evidence and ask only for that new decision.

## M1 — Repair and publish the deployment candidate

Change query_catalog_refresh.queue in docker/scheduled-tasks.yml to default.
Make the canonical pre-build active-job probe read-only using Redis ZCARD on
registry.key: RQ 1.16 get_job_ids always cleans and rejects cleanup=False.
Verify the final probe against the actual old runtime and an executable regression.
Add a test reading actual YAML and exercising scheduler handoff and real queue
validation. It must fail on the old YAML and pass on the corrected configuration.
Preserve notifications=batch and paused GC. Update queue catalog/graph if needed.
Run focused scheduler/catalog/notification/deployment tests through wctl, then
required broad pytest. Latest completed suite evidence is 13,218 passed/423 skips;
retain any fresh-run differences honestly. No new tests merely pin the user's
literal executable-default values; verify their committed values/ADR and native
artifact/runtime behavior. Run docs and graph gates, reviews, commit only owned
changes, push and verify exact remote HEAD. Do not stage controller-validation
work, management JSON test residue or Usersum generated index.

## M2 — Protect state and migrate before readers

Create private mode-0700 evidence directories on each host and retain image tags,
config hashes and original source revision. Preserve current Caddy mitigation;
its two local edits are already in the candidate. Back them up and reconcile only
those exact edits before verified fast-forward, preserving unrelated changes.
Take protected PostgreSQL and Redis recovery snapshots, including deferred and
historical state. Rehearse notification migration on an isolated restored database
with explicit URI override, verify counts/tables and remove only rehearsal data.

Before migration, assert the effective application database URI names the owned
rehearsal database and verify SELECT current_database() and server identity.
Check production revision and table absence before and after rehearsal.
Apply the additive migration after the M3 old-producer/worker holds and before
candidate readers. This makes exact count-preservation readback meaningful.
If a post-upgrade assertion fails, inspect committed revision/tables before retry;
Alembic may already have committed. Prefer the existing old
runtime with only the candidate Alembic directory mounted read-only in a one-shot
process, after the exact command passes rehearsal. This avoids a premature full
application activation. Never replace live Redis with a prior snapshot or drop
notification tables on rollback. Raw backups/credentials stay outside git. Retire only the two proven completed
expired October pilot permits using artifacts/retire_completed_catalog_permits.py
after fresh all-old-runtime holds and a deployment-owned catalog pause. Preserve
all pilot bytes and every other ledger field; the independently anchored evidence,
WATCH guards and exclusive snapshots are mandatory. Do not retry blindly after
an uncertain commit/readback. This is not an RQ flush or ledger reset.

## M3 — Coordinated production activation

Keep both feature flags false initially and preserve existing catalog modes/GC.
Stage the exact seven default root locators for four namespaces; all aliases and
shared coordination identities are preserved. Measure duplicate traversal cost
in the general cycle; do not count aliases as unique project coverage.
Gracefully stop old wepp1 weppcloud, rq-engine and scheduler, including in-flight
requests through direct port 8000. Warm-stop all five old worker containers:
wepp1/wepp2 rq-worker and rq-worker-batch, and wepp3 rq-worker-fork-archive.
Use installed wctl compose stop with the canonical 216000-second worker timeout;
never SIGKILL active work. Verify every old process stopped and all three started
registries empty before any 2.x process starts. Preserve retired wepp2 batch logs.
If the already-retired wepp2 batch pool fails warm shutdown, use the exact-ID
conditional disposition in the correctness review: after a 30-second observation,
refresh zero registrations/started jobs and absence of project FDs, mappings or
job descendants, then terminate only that unchanged retired container. This is
not an automatic short timeout for healthy pools. Any contrary evidence blocks
escalation. Preserve its logs and verify process exit before continuing.
Remote pools remain manually stopped until their own canonical deployment.
The script owns its suspension; do not create an external rq:suspended key.

This deliberately permits normal exclusively-2.x traffic as wepp1's new services
become reachable, before post-start health gates finish. Those gates and actual
post-deployment acceptance remain required while remote builds continue. The
application outage includes the no-cache wepp1 build; do not claim zero downtime.
No proxy/firewall changes are needed. Even on script error and fence release,
old stopped producers/workers must remain stopped; inspect partial new services
and forward-repair. Never restart an old container after first 2.x writes.
Preserve unrelated Culvert/analytics services.

Run from /workdir/wepppy on each verified host, in order wepp1, wepp2, wepp3:

    scripts/deploy-production.sh --print-plan --no-flush-rq-db --skip-docker-prune
    scripts/deploy-production.sh --skip-pull --no-flush-rq-db --skip-docker-prune

Use --skip-pull only after the verified candidate fast-forward. Do not bypass
local builds with --skip-build. Capture output privately and retain sanitized
service/image/distribution summaries. Each script's fence must remain owned and
renewed through its cutover. Preserve tagged rollback images and all volumes.
After wepp1's canonical completion, stop only its new scheduler until wepp2/3
finish, then recreate scheduler through the scoped approved operation. Verify it
has not reached the 900-second initial task delay; if it has, inspect/drain any
admitted jobs instead of deleting them or claiming scheduling was prevented.
Require expected worker registrations, actual RQ 2.12.0 imports, unchanged
identities/mounts and correct native hashes across all consumers.

After canonical traffic reopening, submit an owned representative project via the
real API and inspect model inputs, fresh matched native outputs, a strict report
and authenticated download. Check real login/CAP, APIs, Usersum and Roads rendering.
Include bounded fork/archive acceptance after wepp3 updates. Distinguish baseline
failures from regressions; retain incomplete states rather than force green.

## M4 — Notification activation

Create only disposable registered fixture data/accounts, with future expiry and
explicit producer registration scope. Real batch jobs must preserve TTL bytes,
warning identity and read state on retry. Browser tests cover badge/list/sorts,
pagination, selected/current-page read changes, auth and CSRF. After success set
WEPPCLOUD_NOTIFICATIONS_SWEEP_ENABLED=true in wepp1's selected merged host env;
read back effective configuration and recreate only scheduler using the scoped
operation ratified in this deployment plan. Retain other container identities.
Observe the actual first scheduled job after the 900-second initial delay and
its source/database/browser output. Subsequent interval is 86,400 seconds.
No TTL deletion is enabled. Remove only owned fixtures after acceptance.

## M5 — Default-worker pilot and general observation

With general async false, verify all twelve genuine default workers advertise
matching protocol/roots/queue identity. Preserve/drain old catalog maintenance
and the historical ledger/pause/manifest records. Run tools/query_catalog_pilot.py
prepare/register/run using a fresh pilot ID and private evidence path in an
existing default worker under UID1002/GID130. The eight fixtures, excluded
sentinel, two artifact waves, receipt acknowledgment and query checks must pass.
Measure ordinary default arrivals and preserve any wait-failure outcome. Do not
reuse old batch-pilot authority or fake worker capability.

Configure identical four-namespace QUERY_CATALOG_ROOTS_JSON and existing limits
on all participants. Retain an executable observation manifest before enabling:
up to 48 hours, at least one complete reconciliation cycle, oldest pending and
unreconciled ages, ordinary-arrival delay, stable seven-job cap and actual
catalog/schema/report readback. Missing arrivals or incomplete cycle leaves the
gate open. Use existing pilot 300-second ordinary-wait failure as a conservative
stop trigger for the observed rollout; record it as an observation criterion,
not a new queue configuration/default. Pause new catalog admission on failure,
retain receipts and allow admitted work to drain.

Set QUERY_CATALOG_REFRESH_ENABLED=true consistently and activate participants
through canonical lifecycle with catalog admission paused during transition.
Verify configuration convergence before unpausing. Actual scheduler jobs must
execute on default and preserve inventory/receipt progress. Keep the separate
Runs catalog untouched. No general acceptance based only on the owned pilot.

## M6 — Review, cleanup and closure

Retain source/native/distribution, backup/migration, deployment, job/tree,
notification, catalog and generated-model evidence. Independent correctness and
security reviews must close medium/high findings. Clean only owned disposable
resources using lifecycle guards, snapshot status/receipt evidence before
retirement, preserve external guard inodes and avoid NFS open-log deletion races.
Update this package and the active query-catalog package, archive only completed
plans, and record remaining limits if any gate cannot be evidenced.

## Idempotence and Recovery

Do not flush queues, erase receipts or remove coordination lock inodes. Before
2.x writes, retain compatible old images/source and a consistent original recovery
point. After writes, no in-place downgrade; pause admissions and use bounded
forward repair unless a separately reviewed no-data-loss restoration is possible.
Feature rollback is independent: disable notification scheduling and keep tables;
pause catalog admission, drain and coordinate synchronous producer mode while
retaining guards/disclosure. Repeated fixture checks use exact owned identities.
No force-reset/stash of unrelated source, no branch creation/switching.

## Observation supervision recovery (2026-11-06 UTC)

Observation 01 remains failed: manual parent probes were 121.782 seconds apart,
exceeding the 60-second attendance bound. Its collector retained 48 samples with
a maximum 10.146-second gap and no cycle errors, but that does not restore the
failed control result. Admission was paused with NX; admitted inventory and all
state remain intact. No completion or acceptance marker exists.

The smallest justified control escalation is a bounded foreground operator
supervisor with 15-second machine cadence and bounded SSH probes. It journals
checks and pauses admission on probe/child failure, stale heartbeat, attendance
gap, interruption or the original deadline. A nonce/PID-bound parent heartbeat
lets the collector detect loss of its supervisor and pause independently. Pausing
uses NX and preserves other owners; only the operator collector is supervised,
never admitted RQ work. No daemon, service, queue or deployment identity changes.
Redis/host loss can prevent confirmed containment and must be reported honestly.

Fresh observation 02 uses new markers/arrivals and the same absolute deadline,
1794127194.157908 (November 8, 08:39:54 UTC). Baseline is the existing failed-run
cycle. It may finish under controlled continuation but cannot satisfy acceptance.
Only a different naturally scheduled cycle starting after activation is eligible;
final ordinary-arrival proof must include arrivals during that target cycle.
Do not reset cursor/generation/scopes/receipts, shorten the 86400-second spacing,
reuse prior success evidence or silently extend time. Insufficient remaining
time leaves the gate incomplete. Failure-injection tests and independent reviews
are required before the new supervisor releases admission.

Empirical prelaunch readback found that 4,641 pending-scope status reads cannot fit
the 45-second sample budget: only 1,272 completed in 45.011 seconds. The supervised
collector therefore checks every admitted scope plus a deterministic rotating
sample of at most 25 pending scopes. It records population, sample counts and
offset; these ages are explicitly nonexhaustive. The independent retained-union
census remains mandatory for global-age acceptance. Deadline and containment
bounds are unchanged. This bounded instrumentation change follows a measured
failure of the simpler whole-pending-list observation.
