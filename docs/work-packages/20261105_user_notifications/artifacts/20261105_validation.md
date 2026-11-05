# Notification implementation and forest validation

## Automated checks

| Check | Result |
| --- | --- |
| PostgreSQL/Flask/TTL notification tests | 26 passed |
| Corrected notification + feature-access suite | 78 passed |
| Complete WEPPcloud suite | 2,325 passed |
| Complete RQ suite | 1,329 passed; 220 skipped |
| Complete frontend suite | 1,051 passed; 123 suites |
| Broad repository run | 12,877 passed; 423 skipped; one stale collected assertion failed |
| Fresh corrected assertion after broad run | 1 passed |
| Standard and targeted JavaScript lint | Passed |
| Task stubtest, test-stub guard, RQ graph | Passed |
| Changed broad-exception enforcement | Passed; no increase |
| Documentation lint | Passed |

The broad process collected the old feature-access migration-head assertion
before it was corrected. Its trace compares the old/new revision IDs while
showing the updated source line. Fresh corrected focused and whole-web suites
pass; this is not represented as a single all-green repository run. Exact log
locations and hashes are in `regression-results.json`.

## Actual boundaries exercised

The live account database was backed up, restored to an explicitly isolated
rehearsal database, and migrated with original user/run/membership counts
preserved. The live additive migration was applied before notification readers
or writers activated. The rehearsal database was removed after evidence capture;
the restricted backup remains under `/var/tmp/notification-rollout-20261105/`.

A real batch worker consumed the scoped disposable project and created exactly
one TTL warning. A second job preserved its read timestamp and episode identity.
TTL bytes and non-fixture notification rows were unchanged. Exact repository SQL
plans were captured over 1,001 seeded notices.

Actual authenticated browser acceptance covers 100/1 pagination, all three sort
modes, individual/page selection, explicit read/unread, logout/login persistence,
keyboard bell activation, anonymous no-fetch behavior, ordinary-account empty
state and cross-account rejection, failure handling, resolved/unavailable history,
light/dark screenshots, and five header routes with 390px bounds. The test account
fixture email was corrected from a rejected reserved domain; authentication
validation was preserved.

The existing forest CAPTCHA routing defect was separately authorized and repaired.
Fresh tokens pass and replayed/invalid/missing tokens fail in Flask and both
rq-engine verification helpers. Browser challenge URLs remain public-to-tailnet
HTTPS; verification uses the existing internal CAP service. Only web/rq-engine
were recreated by canonical targeted-web activation.

Application rollback removed the bell and routes while ordinary authenticated
pages stayed usable. All 101 notifications and their recipient records, including a read
timestamp, matched exact hashes before rollback, after rollback and after candidate
restoration. The restored candidate passed the browser acceptance again.
The independent CAPTCHA repair and concurrent operator GC pause were preserved.

## Canonical operation

The first build stopped before cutover because host Python lacked Jinja2. The
repository virtualenv passed the controller-build preflight. Successful web
activation, rollback and restoration used:

    PATH="/home/workdir/wepppy/.venv/bin:$PATH" scripts/deploy-production.sh --targeted-web --skip-pull --no-flush-rq-db --skip-docker-prune

The operator explicitly approved scheduler-only recreation:

    wctl docker compose up -d --no-deps --force-recreate scheduler

Four live local batch workers match the task/producer source hashes and runtime
identity. Notifications are enabled at a startup-relative 900-second delay and
86,400-second interval with zero jitter. `ttl_gc.enabled` remains false.
Actual scheduled job `b4cd4984-a290-4596-8587-91cdc374963c` completed at
23:01:55 UTC: 572 examined, 0 created, 1 updated, 0 resolved, 470 unavailable,
101 skipped in 2.098 seconds. Source bytes and read timestamp were unchanged;
database and browser readback passed. The availability audit explains 469 missing
local project directories and one missing TTL. Fixture cleanup completed: registration 2325, user 2831, 101 notices, exact project
directory and disposable credentials are absent. Open NFS logs held by Gunicorn
were released through a final canonical targeted-web recreation. Post-cleanup
browser acceptance passed (1 test): empty inbox, hidden zero badge, anonymous
count 401, missing-CSRF mutation 400. Final runtime comparison confirms only
web/rq-engine/scheduler changed across the rollout; scheduler remained unchanged
during cleanup. See `forest-cleanup.json`, `forest-post-cleanup-browser.json` and
`forest-final-runtime.json`.

## Practical limits

This is a forest deployment only. There is no fixed nighttime execution hour,
email/push delivery, history purge, maintenance authoring UI, or changed project
retention policy. Access-log compilation and notification population remain
independent; notices describe recorded expiration. The generic schema supports
future kinds without introducing a second service or account database.
