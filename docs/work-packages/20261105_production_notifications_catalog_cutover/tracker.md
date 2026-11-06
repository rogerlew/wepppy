# Production cutover tracker

Status: executing. Last updated: 2026-11-06 UTC.

## Progress

- [x] Operator authorized package and production deployment, including `2111d0eb2`.
- [x] Published candidate/native hashes and current fleet baseline inspected.
- [x] wepp1 cleanup completed: 215 GB free, tagged rollback images preserved.
- [x] Package/checkpoint and independent preflight review.
- [x] Scheduler queue correction, regressions and published candidate 8d079b41d.
- [x] Production state backup/rehearsal and coordinated migration/deployment.
- [x] Notification activation and actual scheduled/browser acceptance.
- [ ] Default-worker pilot and monitored general catalog activation.
- [ ] Final reviews, cleanup and closure.

## Decisions

Keep all earlier safeguards and GC pause. The user's last config-default commit
is release authority, not an invitation to rewrite existing project selections.
Keep notification population on batch and catalog maintenance on default. Use
wctl merged environment files; no new Compose mapping is necessary. Preserve old
catalog ledger/pause/history during queue migration. No Redis flush or image/volume
prune during deployment. No 1.x workers may attach after 2.x writes.

## Current findings

Scheduler YAML corrected to default; actual-config integration failed before
and passed after the correction. Focused tests: 186 passed; deployment tests:
72 passed; full suite: 13,361 passed, 281 skipped; RQ graph current.
All three hosts run compatible RQ 2.12.0; wepp2 batch capacity is restored.
Production schema is f6b8d27a901c. Notifications and the default-worker pilot
passed actual job, database, artifact and browser acceptance. The second canonical
rollout enables general catalog configuration while admission remains paused.
The old dashboard 502 and legacy archive read-only placement are retained existing
limitations, not authority for new services or mount changes.

## Evidence and next action

Readiness assessment is under notes/. Original production inspection and cleanup
logs are retained under /tmp on forest; copy sanitized summaries to artifacts and
private operational backups to mode-0700 host directories. Finish fleet configuration
convergence, then run the reviewed bounded general observation with independent
artifact and age-coverage acceptance before closing the package.

### Reviewed execution preparation (2026-11-06 UTC)

Published checkpoint `b4d9aab1d` includes the operator's defaults. All three hosts
have fetched it; running applications remain at 0da9c9071. Staged environment
readback confirms seven equivalent root locators/four namespaces on 18 wepp1,
two wepp2 and one wepp3 services, with both feature flags false. The isolated
migration passed with counts preserved and its database was removed; live schema
is unchanged. Images and protected backups remain retained.

Two completed October pilot permits outlived their RQ hashes. Both reviewers
verified their exact completed bindings against anchored historical results.
The reviewed one-time helper retires only those two reservations after the
baseline-matched all-old-runtime hold and catalog pause; it preserves ledger
identity and all pilot history. No recovery mutation has run. Fresh full pytest
is still running without a reported failure; focused/deployment/frontend gates
pass. The new scheduler will be held after wepp1 activation through remote fleet
activation to avoid admitting unrelated scheduled work during the transition.

### Live cutover checkpoint (2026-11-06 06:34 UTC)

Full suite: 13,361 passed, 281 skipped. Candidate 8d079b41d verified on all hosts.
Permanent wepp1 LFS repair independently verified through uncached normal filters.
All eight old runtime containers stopped. Quiescent account dump and Redis RDB
retained privately; SHA256 values are in artifacts/20261106_live_checkpoint.md.
Exact two expired completed permits retired, with historical pilot bytes preserved.
Live migration f6b8d27a901c passed unchanged existing counts; both new tables empty.
Canonical wepp1 build running; remote workers held. Both flags false; global
catalog admission pause remains deployment-owned. No 2.x activation claimed yet.

### Fleet activation checkpoint (2026-11-06 06:54 UTC)

Canonical wepp1 and wepp2 deployments completed with no RQ flush. wepp1 scheduler
was stopped before its 900-second initial delay. Twelve default and eight batch
workers are genuinely registered; wepp2's missing batch capacity is restored.
Both hosts use RQ 2.12.0, UID1002/GID130, expected WEPP261029/interchange hashes,
and identical dependency/vendor/runtime manifests. wepp3 canonical build started.
Production CAP login, ordinary token denial, self-service PowerUser onboarding
and token mint passed for two disposable accounts. Inbox pagination/read-state,
isolation/mobile and history browser checks passed. The scoped real notification
job created one TTL warning. Scheduler activation and actual scheduled sweep remain
pending. Initial fixture .invalid emails and an absent test-client Referer were
corrected in acceptance helpers; no production validation was weakened.

### Acceptance checkpoint (2026-11-06 07:25 UTC)

All three canonical deployments completed. Native/code/distribution/vendor parity
passed using manifests that explicitly exclude the mounted bot-token secret.
Owned model fcb15f42-88c9-4eb6-b169-4e1ff8d5ce74: all 18 jobs passed; 25 fresh
Parquet files / 706,190 rows, both execution binary identities, three strict reports,
rendered summary and authenticated CSV verified. Archive/restore preserved every
Parquet hash and report construction. Public source was undone-terminal; earlier
source candidates correctly rejected synthetic-account access and were untouched.
Default pilot qcat-20261106-default01 passed in 105.65 seconds, one inventory and 16 refresh jobs, eight
scopes/two artifact waves, query schemas/counts and unchanged source/sentinel.
Observed actual modeling arrivals waited at most 0.128 seconds. Ten-second samples are
not exhaustive transient concurrency evidence.
Notification scheduler enabled at 07:12:24 UTC, with sweep due approximately 07:27:41 UTC
after runtime initialization. General flag stays false and owned admission pause
is production-cutover-20261106:general-observation. Reviewed collector and
manifest are prepared; concrete configuration/images/deadline still required.
API discovery does not list archive/restore metadata; live OpenAPI and exact
route contract supplied that acceptance call. Outputs API reported an empty
metadata inventory despite verified generated artifacts; no metadata-inventory
completeness claim is made.

### General transition staging (2026-11-06 07:32 UTC)

The real scheduled notification job 8d431619-1510-4a78-80b3-5a4ee6373d32
started at 07:27:41 UTC and remains active with a current heartbeat. The scheduler
was held after enqueue to avoid admitting additional scheduled work during the
next canonical transition; accepted work is not canceled. General enablement is
staged in all three docker/.env files, but running processes remain false and
the owned catalog pause stays set. All 21 queue-specific live worker registrations
verified. The next deployment waits for accepted work to drain and scheduled
notification database/browser acceptance.

### Scheduled notification acceptance (2026-11-06 07:44 UTC)

Actual scheduler job 8d431619-1510-4a78-80b3-5a4ee6373d32 completed in 761.804 seconds:
33,446 examined; 4,992 created; 1 updated; 19,382 unavailable; 9,071 skipped.
Unavailable sources were not assigned inferred dates. Database/read-state/TTL
readback and actual browser acceptance passed; 5,093 total notices include 101
owned test notices. Preserve all 4,992 nonfixture notices during cleanup.
Queues are empty, source remains clean 8d079b41d, and compatible images retained.
Second canonical full deployment started on wepp1 with general flag staged true
and owned catalog admission pause retained. No skip-build bypass is available
or used. Runtime convergence, observation and cleanup remain open.

### Final configuration and cleanup checkpoint (2026-11-06 07:58 UTC)

wepp1 second canonical deployment passed; every participating container matches
the enabled configuration and code/native manifests remain identical. Scheduler
is held while wepp2 builds, with catalog admission still paused. Post-recreation
project, summary, Usersum and authenticated CSV checks passed with unchanged CSV
hash. Reviewed notification fixture cleanup removed only registration 59273, its
directory and 101 notices; all 4,992 production notice IDs remain. The fixture
account now renders an empty inbox and zero unread badge. Accounts/model remain
for general acceptance. SEC-08 optimized-Python guard finding is closed.

### Scheduler storage prerequisite (2026-11-06 08:16 UTC)

wepp2's second canonical deployment passed with matching runtime/native manifests
and twelve compatible default consumers; wepp3 is exporting its final image.
Prelaunch cursor readback found all four namespaces unavailable. Actual Docker
mounts confirm scheduler alone inherited generic `/wc1` and `/wc1/geodata` host
sources; workers validate all seven configured locators. The one-line wepp1 volume
anchor repair has a failing-before/passing-after regression (47 focused checks
pass) and actual merged Compose render confirms correct sources. COR-08/SEC-09
hold general release until actual scheduler root/coordination parity and normal
reconciliation readback pass. Existing scoped recreation authority applies;
identity, image, destinations, RW mode and unrelated containers must remain fixed.
