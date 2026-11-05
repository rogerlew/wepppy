# User notifications tracker

Status: closed — implemented and verified on forest, 2026-11-05.
Last updated: 2026-11-05 UTC.

## Task board

- [x] Contract, ADR-0137, independent design review and ancestor `ceeaa5960`.
- [x] Additive PostgreSQL schema, generic inbox, Flask API and shared headers.
- [x] Retry-safe nightly RQ producer and server-side read state.
- [x] Regression checks and independent correctness, security and QA reviews.
- [x] Forest backup/restore rehearsal, live migration and real worker parity.
- [x] Authorized CAPTCHA transport repair and real-token/browser acceptance.
- [x] Browser pagination, sorting, bulk actions, isolation, history and mobile headers.
- [x] Application rollback/restoration with exact notification/read-state preservation.
- [x] Actual scheduled sweep and source/database/browser readback.
- [x] Fixture cleanup, final browser acceptance, documentation closure and archival.

## Decisions and authority

The [canonical contract](../../schemas/user-notifications-contract.md) records
operator decisions and rationale: existing account PostgreSQL, Flask API, nightly
RQ producer, quiet bell, 100 rows per page, current-page selection, explicit
read/unread and three sort modes. No new service or retention-policy change.
The [contract checkpoint](artifacts/20261105_contract_decision.md) and independent
reviews preceded implementation. The operator authorized forest execution and
separately approved the CAPTCHA repair and scheduler-only recreation exception.
Canonical targeted-web deployment handled all web activation and rollback.
Concurrent operator GC pause and unrelated workspace edits were preserved.

## Runtime evidence

The live additive migration is `f6b8d27a901c`. Restored database rehearsal preserved
28 users, 570 runs and 259 memberships; its disposable database was removed.
Restricted backups and raw logs remain in `/var/tmp/notification-rollout-20261105/`.
Four local batch workers match candidate task/producer source and runtime identity.
Real worker retries preserved TTL bytes and recipient read timestamps.

CAPTCHA verification now uses the existing internal CAP service on forest while
browser challenge URLs remain HTTPS. Fresh tokens pass; replayed, invalid and
missing tokens fail. The original deployment stopped before cutover because host
Python lacked Jinja2; canonical deployments succeeded with repository virtualenv
PATH. See [validation](artifacts/20261105_validation.md) for exact commands.

Rollback removed notification routes/bells while ordinary authenticated pages
remained healthy. All 101 fixture notifications and recipient records matched
before rollback, after rollback and after restoration, including the read timestamp.
Candidate browser acceptance then passed again.

Scheduler job `b4cd4984-a290-4596-8587-91cdc374963c` ran at
2026-11-05 23:01:53 UTC: 572 examined, 0 created, 1 updated, 0 resolved,
470 unavailable and 101 skipped in 2.098 seconds. Exact TTL bytes, read timestamp,
active status and browser badge/content passed readback. The availability audit
found 469 missing local project directories and one missing TTL; unknown sources
were not initialized or represented as valid expiration dates.
The next daily enqueue is expected around 2026-11-06 23:01:53 UTC (scheduler polling
applies). Restart resets the 900-second initial delay; interval is 86,400 seconds,
zero jitter. Notifications are enabled; the separate GC pause remains effective.

## Regression disposition

Notification tests: 26 passed; corrected combined suite: 78 passed; complete
WEPPcloud: 2,325 passed; RQ: 1,329 passed, 220 skipped; frontend: 1,051 passed.
Full repository run: 12,877 passed, 423 skipped, one stale collected migration-head
assertion failed. The process collected it before correction; fresh verification
passed and the corrected complete WEPPcloud suite passed. No single all-green full
run is claimed. Exact results and hashes: [regression results](artifacts/regression-results.json).
Graph, stub, JavaScript, exception and documentation checks passed.

## Closure

Fixture registration 2325, disposable user 2831, 101 fixture notices, the exact
fixture directory and disposable credentials are removed. The rehearsal database
is absent. Gunicorn-held NFS fixture log handles were released by a successful
canonical targeted-web recreation. Post-cleanup real browser acceptance passed:
empty inbox, hidden zero badge, anonymous count 401 and missing-CSRF mutation 400.
All other container identities are unchanged; scheduler stayed running through
cleanup and its next daily execution remains scheduled. See
[cleanup](artifacts/forest-cleanup.json), [browser](artifacts/forest-post-cleanup-browser.json)
and [runtime](artifacts/forest-final-runtime.json).

Final correctness and security review artifacts record their independent gate
dispositions. This package activates forest only; no production or forest1 rollout
is implied. History purge and a maintenance publisher remain outside scope.
