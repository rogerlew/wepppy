# User Notifications Contract

Status: ratified by the operator on 2026-11-05 by requesting work-package execution; implementation and deployment pending.
Decision owner: requesting operator. Initial scope agreed 2026-11-05.

## Purpose and scope

Provide a quiet account inbox for upcoming automatic project deletion. A nightly
RQ task populates the next 14-day window. Flask owns the session-authenticated
listing and read-state API; rq-engine gains no notification endpoint. PostgreSQL
stores notification content and per-user read state alongside existing accounts.
The schema supports other kinds, including planned maintenance, without adding
a maintenance administration UI in this release.

The bell and unread count are the only attention cue. There are no toasts,
popups, emails, push messages, dismissal controls, or separate alerted state.
Opening the inbox does not mark anything read. Delivery is informational and
does not guarantee 14 days of notice, extend retention, or gate garbage collection.
Users who do not return to the site will not see an in-app notification.

## Canonical boundaries

This contract adds notification behavior while preserving the
[session](weppcloud-session-contract.md), [CSRF](weppcloud-csrf-contract.md),
[request payload](request-payload-contract.md), [response](rq-response-contract.md),
[shared UI](../ui-docs/controller-contract.md),
[catalog TTL](../ui-docs/contracts/runs-catalog-ttl-deletion-contract.md), and
[project TTL control](../ui-docs/contracts/project-ttl-control-contract.md)
contracts. Notification reads never touch access timestamps, repair TTL files,
change policy, or enqueue deletion. The
[catalog projection](run-catalog-projection-contract.md) remains a separate owner;
this feature does not require its cutover or change its freshness rules.

## Persistence and generic schema

Use additive Alembic migrations in the existing application PostgreSQL database.
Do not store inbox state in Redis, NoDb, or project directories. Use two tables:

| Table | Required fields and constraints |
| --- | --- |
| `notification` | ID; kind; source key unique across producer retries; plain-text title/body; created/updated/published timestamps; optional end timestamp; lifecycle `active`, `unavailable`, or `resolved`; optional subject kind/registration identity; JSON metadata |
| `notification_recipient` | Notification ID; user ID; delivered timestamp; nullable read timestamp; unique notification/user pair; user and notification foreign keys |

All timestamps are timezone-aware UTC. Read means `read_at IS NOT NULL`.
Index recipient user/read/list ordering and producer source/subject lookup; verify
query plans using populated data. A run deletion must not cascade notification
history away: retain an immutable subject identity, not a cascading run FK.
Account deletion may cascade its recipient rows. No automatic history purge is
introduced. A page limit bounds responses, not total database retention; review
growth separately before adding retention policy.

Kinds are application-validated strings; initial TTL kind is `project_ttl`.
Metadata holds the observed expiration and warning episode identifier; future
maintenance can store start/end times without schema redesign. Do not accept
arbitrary HTML or external action URLs. Generate project/help links server-side
from trusted route identities after authorization.

## Recipients and authorization

Use the existing normal user's Runs catalog membership (`runs_users`) to choose
recipients, not every administrator or every visitor to a public project.
Each list/count/mutation query scopes to the authenticated user. For an existing
project, recheck current catalog membership before exposing content or allowing
mutation; revoked membership hides the item and excludes it from the count.
Administrator catalog aliases do not expand this personal inbox.

For a deleted registration, retain a generic resolved history item for the
original recipient but omit the project name, subject metadata, and project
link. A new registration reusing a run ID is a different subject. A transient
database/filesystem failure must not be interpreted as confirmed deletion.
Future non-project kinds must define their audience explicitly; an absent
recipient row never grants access. Browser responses are private/no-store.

## Nightly producer and reconciliation

Register one task with the existing scheduler and an existing worker queue.
For this initial design, nightly means the existing startup-relative daily
schedule: interval 86,400 seconds, initial delay 900 seconds, task-specific jitter
zero. Restart resets the initial delay and can produce an extra sweep; idempotence
must make that harmless. Record expected next execution in UTC, but do not promise
a fixed wall-clock hour. Fixed-clock nighttime execution would require a separate
schedule decision. No new queue/service or dependency on GC completion.
The schedule is gated by `WEPPCLOUD_NOTIFICATIONS_SWEEP_ENABLED`, default false
until migrations and forest preflight pass. Disabling it stops new admissions;
already queued tasks must be inventoried and handled during rollback.
An optional trusted registration-ID scope may be supplied by operator tests;
it constrains both candidates and reconciliation, is absent from normal scheduled
invocations, and is never exposed through browser endpoints.
An explicitly empty scope is a no-op, never an unrestricted sweep.

Start with bounded batches of registered projects and non-mutating reads of
their authoritative TTL/protection state. Use existing run-root resolution.
Never walk arbitrary client-supplied paths or depend on a header request to scan
projects. Verify the runtime cost on forest before introducing a catalog-based
optimization. The catalog projection is not a prerequisite.

Capture one UTC `now` for the sweep. A new normal warning qualifies when
`now < expires_at <= now + 14 days`, rolling deletion is enabled, neither
READONLY nor user protection applies, and deletion state is active. Batch/excluded
projects do not qualify. An active, still-eligible overdue project also qualifies
as catch-up after outages; label it overdue rather than promising future deletion.
Queued/trash/purged projects do not receive new upcoming warnings.

Upsert one notification per subject warning episode and one recipient row per
eligible user. Repeated or concurrent sweeps must neither duplicate rows nor
reset `read_at`. Serialize overlapping sweeps with a database-backed lock and
enforce uniqueness in the database; a retry after partial completion is safe.
Commit bounded batches and report partial failures explicitly.

A warning episode continues while a project remains eligible within the window
or overdue. Date changes inside that episode update content without resetting
read state. Confirmed protection, expiration beyond the window, or non-active
deletion state resolves the episode. Later reentry creates a new episode and
unread recipient rows. Unknown/malformed/unreadable TTL marks an existing episode
unavailable, suppresses its active unread count, and retains its read state; it
does not resolve the episode. Recovery restores that episode if still eligible.
Never infer resolution from absence in an incomplete scan. Reconcile previously
active subjects as well as newly eligible ones, including deleted registrations.

Access-log compilation currently runs daily on a separate queue; observed TTL can
lag visits. Notices describe the recorded expiration, not a guaranteed deletion
time or instantaneous access refresh. Record sweep completion/failure, examined,
created, updated, resolved, unavailable and skipped counts and duration. A failed
task is visible to operators; do not report successful completion for a partial
sweep. Notification failures never modify or block existing GC behavior.

## Bell and listing

Authenticated headers show a bell link to the inbox and the number of active,
currently authorized unread notifications. Hide the numeric badge at zero.
Use an accessible name such as `Notifications, 3 unread`; count failure displays
an unavailable state, never a fabricated zero, without breaking the surrounding
page. Anonymous headers make no authenticated count request.

Cover Pure UI, legacy headers, and report/dashboard overrides. Fetch the count
asynchronously on page load; no polling service or WebSocket is needed. Updating
read state refreshes the local badge. Other open tabs update on their next page
load. Keyboard, screen-reader, narrow-screen and theme behavior must work.

The inbox shows status, title/body, created date, applicable expiration and safe
actions. Include resolved/unavailable history with clear status. Exactly 100
items maximum per page; the server owns this bound. Use numbered pages with
deterministic ordering and an ID tie-breaker:

- `unread_first` (default): unread before read, then created descending, ID descending.
- `read_first`: read before unread, then created descending, ID descending.
- `newest`: created descending, ID descending.

Sorting uses stored read state, independently of lifecycle. The badge counts
active unread items only. Offset pagination is acceptable: concurrent inserts or
read changes may move items between pages; no snapshot guarantee is promised.
Preserve sort on pagination; clear selection after navigation or successful
mutation. If the current page becomes empty after reconciliation, offer a return
to page one. Empty accounts render an empty inbox, not an error.

Each row has a checkbox; `Select all on this page` selects only rendered rows.
Provide `Mark read` and `Mark unread`; disable actions for empty selection.
Success reloads the selected sort/page so grouping reflects the change. Failures
retain selection and state and show an actionable inline message.

## Flask transport

Routes are registered without the proxy's `/weppcloud` prefix; generate browser
URLs through `url_for` so deployed prefixes work.

| Route | Contract |
| --- | --- |
| `GET /notifications?page=1&sort=unread_first` | Session-authenticated Jinja listing; page is a positive integer; sort uses the enum above; no read-state mutation |
| `GET /api/notifications/unread-count` | Session-authenticated JSON; canonical success envelope with `unread_count` |
| `POST /api/notifications/read-state` | Session authentication and CSRF; JSON `{notification_ids: [integer IDs], read: boolean}`; 1–100 unique IDs; canonical success envelope with `updated_count` and `unread_count` |

Reject malformed payloads, booleans used as IDs, duplicate IDs, unsupported sort,
invalid pages, missing fields, and oversize selections with 400 and no mutation.
If any requested ID is absent, unauthorized or no longer visible, return a generic
404 for the entire selection and change nothing. Do not reveal which IDs exist.
Repeated valid state updates succeed as no-ops; `updated_count` counts rows whose
state actually changed. Concurrent valid updates serialize; last committed state
wins. Return the count from the committed database state.

Unauthenticated HTML requests follow the normal login redirect; JSON endpoints
return canonical JSON 401 when authentication is the failing boundary, not login
HTML. Preserve global Flask CSRF validation precedence: invalid/missing CSRF on
POST returns the existing JSON 400 with `csrf_failed` even if the session is also absent. Do not
change the global handler for this feature. Expected
database unavailability returns 503 without exposing internals or partially
committing read changes. Preserve shared error envelope conventions.

## Compatibility, regression and rationale

Existing projects, TTL files, model outputs, run APIs, permissions, and deletion
timing remain unchanged. Old application code can ignore the additive tables.
No run-scoped schema/artifact mutation is authorized. The nightly task's only
writes are notification database rows and normal job telemetry.

Validate real PostgreSQL transactions, concurrent upserts, authorization and
CSRF, TTL file read-only behavior, boundary times, missing state, partial sweeps,
read-state persistence, 100/101 row pagination, every sort and header family.
Trace an actual disposable forest project's TTL bytes through the worker's
observations, database rows, API count, Jinja listing and browser bulk actions.
Checking job success alone is insufficient.

The operator chose nightly RQ, server-side read state, badge-only attention,
100-item pages and explicit bulk read/unread controls to avoid repeated alerts
and keep the workflow simple. Flask reuses account sessions; a separate service,
rq-engine endpoint, real-time transport, reminder escalation and alert preference
are unnecessary for that outcome.
