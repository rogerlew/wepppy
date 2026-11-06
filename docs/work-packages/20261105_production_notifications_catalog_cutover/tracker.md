# Production cutover tracker

Status: executing. Last updated: 2026-11-06 UTC.

## Progress

- [x] Operator authorized package and production deployment, including `2111d0eb2`.
- [x] Published candidate/native hashes and current fleet baseline inspected.
- [x] wepp1 cleanup completed: 215 GB free, tagged rollback images preserved.
- [x] Package/checkpoint and independent preflight review.
- [x] Scheduler queue correction, regressions and published candidate 8d079b41d.
- [ ] Production state backup/rehearsal and coordinated migration/deployment.
- [ ] Notification activation and actual scheduled/browser acceptance.
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
72 passed; RQ graph current. Broad suite running. wepp2
batch workers retired; only stalled pool processes remain. Canonical recreation
must restore real registrations. Independent review requires all old producers
and five worker containers stopped before first 2.x writes; normal traffic may
reopen on exclusively-2.x wepp1 while remote deployments continue.
Production schema is e7a1c9d204bf, pending additive f6b8d27a901c. Production pins
also change FastAPI/narwhals/pkginfo/dateutil relative to actual installed baseline.
The old dashboard 502 and legacy archive read-only placement are retained existing
limitations, not authority for new services or mount changes.

## Evidence and next action

Readiness assessment is under notes/. Original production inspection and cleanup
logs are retained under /tmp on forest; copy sanitized summaries to artifacts and
private operational backups to mode-0700 host directories. Complete independent
review and exact rollback/control commands before irreversible cutover.

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
