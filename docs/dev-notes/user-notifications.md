# Operating and developing the notification inbox

The [contract](../schemas/user-notifications-contract.md) defines account scope,
read state, pagination and warning episodes. PostgreSQL tables `notification` and
`notification_recipient` are private account data, independent of project files.
Migration `f6b8d27a901c` adds them without scanning projects. Apply it before new
web readers or the population task run. Runtime rollback retains these tables.

## Background population

`wepppy.rq.notifications_rq.populate_notifications` runs on the existing batch
queue. `docker/scheduled-tasks.yml` enables it only when
`WEPPCLOUD_NOTIFICATIONS_SWEEP_ENABLED=true` reaches the scheduler container.
The forest dev Compose setting defaults false. Other deployments remain disabled
until separately configured and validated; this package does not deploy them.
Cadence is startup-relative: 900-second initial delay, 86,400-second interval,
zero jitter. Restart can cause an extra sweep; rows/read state remain idempotent.

The producer takes an optional trusted `registration_ids` list for operator tests.
Omission scans registered subjects and existing live episodes; an empty list is
a no-op. Scope covers both creation and reconciliation. Never expose it through a
browser route. The task returns aggregate examined/created/updated/resolved/
unavailable/skipped counts and elapsed time. An overlapping sweep returns
`already_running`. Fatal failures raise to RQ; prior committed batches remain and
retry safely. Check RQ failure state as well as the structured progress log.

Unknown metadata produces an unavailable notice rather than a claim of protection.
Access-log compilation can lag visits; the inbox reports recorded expiration.
The task uses descriptor-bound TTL/protection reads and never touches retention.

## Flask and frontend

`routes/notifications.py` owns the listing, count and read-state endpoints. Reuse
normal session/CSRF middleware, canonical JSON envelopes and `url_for` prefixes.
Bulk selection is atomic and limited to 100 IDs; read state is per recipient.
Database outage is explicit, never converted to an empty inbox or zero badge.
The asynchronous bell is shared across Pure, legacy, run, report and dashboard
headers. Below 540px, bell/theme groups wrap and constrain the theme selector
to available width in both standard and run/report headers. `static/js/notifications.js` is standalone; no controller bundle rebuild
is required for changes limited to this script.

No history pruning or maintenance authoring interface is included. Future kinds
must define their recipient audience and write plain text; do not make arbitrary
HTML/URLs or metadata a rendering escape hatch.

## Validation and rollout

Run `wctl run-pytest tests/weppcloud/test_notifications.py`, `wctl run-npm test`,
`wctl run-npm lint` and `wctl check-rq-graph`. PostgreSQL tests create disposable
schemas and use unique advisory lock keys so they cannot suppress a live sweep.
The test suite exercises middleware, real transactions and source files; the
work-package forest evidence covers the actual worker and browser path.

Before activation preserve exact touched source files as well as image identity:
forest serves bind-mounted source, so restoring an image alone is insufficient.
Back up PostgreSQL and rehearse restore/migration against an explicitly isolated
database URI. Migrate with the new schedule disabled, activate candidate web code,
and run fixture-scoped preflight. Verify every eligible worker sees the candidate
code and expected database before enabling unrestricted scheduled execution.

Use the installed deployment entry point for web activation. Scheduler environment
changes require recreation, not restart; record the bounded mechanism before use.
On rollback stop admissions first, inventory queued/started notification jobs,
restore only feature-touched source and activate web rollback. Keep tables/read
state, unrelated edits/services and GC unchanged. Never flush Redis. The execution
package records exact commands, revisions, browser artifacts and remaining gates.

Forest activation is recorded in the 2026-11-05 notification work package. Its
gitignored root and Docker environment files enable the notification sweep;
production/forest1 are not activated by that work. The separately paused GC
schedule is independent of notification population. On forest, canonical web
deployment needs the repository virtualenv on host PATH for the Jinja controller
builder. Scheduler-only recreation was explicitly authorized for this rollout.

## Production smoke evidence

The notification Playwright suite accepts `SMOKE_NOTIFICATION_EVIDENCE_DIR`,
`SMOKE_AGENT_CREDENTIALS_FILE` and `SMOKE_NOTIFICATION_SECONDARY_CREDENTIALS_FILE`
so each deployment can retain separate evidence and disposable accounts without
changing historical forest artifacts. Paths may be absolute or repository-relative.
Use a fresh primary account with the fixture's 101 notices and an empty secondary
account. The historical cleanup smoke assumes zero unrelated notifications;
production cleanup instead verifies the fixture account and preserves every
unrelated notification. Never remove production rows to satisfy that assertion.
