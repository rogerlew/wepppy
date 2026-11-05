# Deliver the notification inbox through forest acceptance


This is a living ExecPlan maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep Progress, Surprises & Discoveries, Decision Log and Outcomes & Retrospective
current, and update the package tracker at every handoff. The operator requested execution on 2026-11-05. Execute each
milestone without routine permission pauses; stop only at a real authority,
dependency or acceptance blocker and record exact evidence.

## Purpose / Big Picture


Users will see a bell with their active unread count across WEPPcloud headers.
Clicking it opens a 100-row paginated inbox where they can sort unread/read/newest,
select individual or all current-page rows, and explicitly mark them read or
unread. A nightly RQ task supplies notices for recorded automatic deletion dates
within 14 days. No popup or repeat reminder appears. PostgreSQL persists read
state across sessions. Delivery is informational, not a new deletion grace policy.
The completed package includes a verified test deployment on forest, not forest1
or any production host.

## Progress


- [x] (2026-11-05 19:58 UTC) Repository discovery and initial contract/scaffold authored.
- [x] (2026-11-05 UTC) Two independent design reviews and post-fix confirmations; no open medium/high findings.
- [x] (2026-11-05 UTC) Operator execution ratification, ADR-0137 and ancestor `ceeaa5960`.
- [x] (2026-11-05 UTC) M1: schema/repository real-PG tests and restored-database migration validated.
- [x] (2026-11-05 UTC) M2: producer retry/reconciliation/source-boundary tests passed; live schedule pending M5.
- [ ] M3: Flask API, listing, headers and user workflow validated.
- [x] (2026-11-05 21:38 UTC) M4: regression gates/reviews retained; stale collected migration assertion disposition below.
- [ ] M5: forest activation, browser/job evidence, nightly observation and rollback complete.
- [ ] Package closure and prompt archival.

## Surprises & Discoveries


`docker/scheduled-tasks.yml` configures daily access-log compilation on batch and
GC on default; no ordering between them is guaranteed. `run_ttl.py` has helpers
that write/repair TTL as well as a non-mutating reader; choose the latter.
The catalog projection exists but its scheduler is opt-in; this plan does not
depend on its rollout. Pure and legacy headers coexist and reports/dashboard
override the Pure header. Forest is the dev Compose host; forest1 is separate.

## Decision Log


2026-11-05, operator conversation/Codex: retain the smallest inbox workflow:
nightly task, two account tables, Flask routes, static unread badge, page selection
and read state. No real-time delivery, maintenance editor or project lifecycle
redesign. The 14-day window and 100-row bounds come from the operator. Use
ordinary catalog membership for recipients and direct bounded background TTL
reads initially, so no catalog rollout is silently introduced. Contract edge-case
clarifications require review/ratification before implementation.

2026-11-05, independent rollout review/Codex: exercise application activation
rollback after candidate browser acceptance while notification scheduling remains
disabled, then restore candidate and enable the schedule. This proves removal
and restoration of live wiring while avoiding real-user notification creation
solely for rollback testing. The actual scheduled sweep remains a separate gate.

## Outcomes & Retrospective


Implementation is committed at `4cf1432d5` after contract ancestor `ceeaa5960`.
Independent correctness, security and QA implementation reviews have no open
medium/high findings. Forest backup restoration, additive live migration and
fixture-scoped real-worker retry passed, including unchanged TTL bytes and
preserved read state. WEPPcloud (2,325), RQ (1,329) and frontend (1,051) tests
passed. Full repository pytest finished with 12,877 passed and 423 skipped before the
old migration-head assertion, collected before correction, failed. Its fresh
rerun passes (1 test), and the corrected full WEPPcloud suite passed. This is not
claimed as a single all-green full run. Browser acceptance, application
rollback and actual scheduled execution remain open.

## Context and Orientation


The authoritative behavior is `docs/schemas/user-notifications-contract.md`.
It defines the schema, recipient scope, warning episodes (one continuous period
of deletion eligibility), read-state persistence, API and UI. PostgreSQL is the
existing account database; SQLAlchemy models live in `wepppy/weppcloud/app.py`,
Alembic revisions in `wepppy/weppcloud/migrations/versions/`. Existing user scope
selection is in `wepppy/weppcloud/routes/user.py` using `runs_users`. Do not infer
recipient permissions solely from the string `Run.owner_id`.

TTL authority is the run's `TTL` file and protection flags, accessed through
`wepppy/weppcloud/utils/run_ttl.py` and existing root-resolution helpers. The
worker must not initialize/touch TTL or read NoDb in a way that updates access.
GC lives in `wepppy/rq/project_rq_delete.py`; no change to its eligibility or
execution is planned. `docker/scheduled-tasks.yml` registers recurring tasks.

Flask blueprints register in `wepppy/weppcloud/routes/__init__.py` and
`_blueprints_context.py`. A new `routes/notifications.py` can own the three routes.
Put reusable database/producer operations in a focused `wepppy/weppcloud/notifications/`
module and the RQ entry point in `wepppy/rq/notifications_rq.py`. Use the existing
SQLAlchemy transaction and scheduler conventions; no new libraries. A shared
bell include belongs under `templates/header/`, the page under `templates/`,
and a small script under `static/js/`. Inspect comparable templates before naming
selectors or introducing styles. Read nearest AGENTS before editing each area.

## M0: Contract checkpoint and compatibility plan


Read the package contract-decision artifact and its complete contract matrix.
Review the actual current contents of every listed contract, including any
uncommitted concurrent edits; never overwrite unrelated work. Obtain two
independent read-only reviews and post-fix confirmations. Ratify proposed
edge cases with the operator as required by contract-first sequencing. Author a
parameterization ADR using `docs/adrs/AGENTS.md` and the ADR template, recording
conversation provenance and the window/cadence/page/sort defaults. No TTL formula
is changed. Commit contract/checkpoint/ADR/review disposition as a standalone
ancestor and record its revision before editing runtime files.

The compatibility plan is additive account tables only, old code ignores them,
no renamed API keys or run-scoped files, migration before readers/writers activate.
Migration rollback on populated inboxes would discard user state, so operational
rollback keeps tables and disables the feature. Test schema downgrade only on a
disposable database. Run artifact propagation is N/A because no run schema is
mutated; still prove TTL input bytes remain unchanged and inbox output is correct.

## M1: Durable account storage


Implement two tables from the contract with uniqueness, timezone-aware timestamps,
indexes and user deletion semantics. Check current Alembic heads and use the
repository migration workflow; do not guess a down_revision. Implement scoped
listing/count and atomic bulk updates, validating the whole request before
changing rows. Recheck membership and hide revoked subjects. Deleted subjects
render generic resolved history without project identifiers or names. Prevent
project deletion from cascading away private notification history.

Write meaningful real-PostgreSQL tests for migration upgrade, populated-state
readback, upgrade compatibility, uniqueness, transaction rollback, concurrent
updates and absent-user empty state. Disposable migration downgrade/upgrade must
pass without treating it as a production rollback. Verify indexes/query plans
with at least 1,001 seeded notifications for multiple accounts. Record selected
rows and count results, not only SQL execution success.

## M2: Nightly population and reconciliation


Implement `reconcile_ttl_notifications(now=None, registration_ids=None)` behind
the RQ task. The optional registration scope is a trusted operator/test input,
never a browser parameter; it must constrain both candidate scans and existing
episode reconciliation. Default scheduling supplies no scope and covers the
normal registered-project population. An explicitly empty scope must be tested
as a no-op, never interpreted as absent/unrestricted. Capture one
UTC time per sweep, use bounded registration batches, lock against overlapping
sweeps, and upsert unique episodes/recipient rows without modifying `read_at`.
Scan current registrations plus previous live subjects; never resolve an item
only because an incomplete scan omitted it. Observe TTL/protection without writes.
Normal qualifying dates are `(now, now + 14 days]`; active overdue projects get
catch-up notices with overdue wording. Protected/excluded/non-active deletion
states never create new warnings. Unknown TTL preserves episode/read state as
unavailable; recovery restores it or resolves based on confirmed state.

Retain duration/count/partial-failure telemetry and fail explicitly on incomplete
sweeps. Retries must be safe after committed batches. Choose the existing batch
queue unless runtime placement evidence requires another existing queue. Wire a
startup-relative 86,400-second schedule with 900-second initial delay and zero
task-specific jitter; record its expected UTC next execution. Restart resets the
initial delay and can cause an extra idempotent sweep. This initial daily design
does not promise a fixed nighttime hour. Gate admissions with
`WEPPCLOUD_NOTIFICATIONS_SWEEP_ENABLED=false` until forest preflight passes.
Do not add a dependency on access compilation or GC.
Update `wepppy/rq/job-dependencies-catalog.md`, run `wctl check-rq-graph`, regenerate
only if indicated, and later inspect the actual job tree.

Prove exact 14-day boundary, outside window, overdue catch-up, changed dates,
disabled/readonly/batch flags, queued/trash/purged states, corrupt/missing TTL,
deleted registrations, revoked/new membership, partial retries, overlapping
sweeps and restart persistence. Hash/read back TTL before/after the real worker
reader to prove no access refresh or repair. Preserve prior read state after reruns.

## M3: Flask and browser workflow


Implement the three contract routes without a `/weppcloud` blueprint prefix.
Use existing session/CSRF utilities and canonical JSON envelopes. Validate sort,
page, ID types/count/uniqueness and strict boolean before mutation. Test a mixed
authorized/foreign selection returns generic 404 with no writes, missing CSRF
returns the existing global JSON 400 before route authentication, expired sessions
with otherwise valid requests return JSON 401 on API routes, and database failure
does not masquerade as a zero count. Use private/no-store responses.

Build a Jinja list with 100 maximum rows, the three contracted sort choices,
checkboxes, current-page select-all and two bulk actions. Keep selection on
failure; clear it on success and navigation. Opening the page never marks read.
Use an asynchronous count fetch for the bell so notification failures do not
break the page shell. Zero hides the badge; unavailable is distinguishable.
Cover base_pure, legacy run/non-run/global dispatch, reports/_base_report and
gl_dashboard overrides explicitly. Anonymous pages do not fetch private counts.

Add browser tests for a 101-row inbox, deterministic sort ties, page transitions,
selected-only updates, all-on-page updates, second-user isolation, reload/login
persistence, count changes, empty history and resolved/unavailable rows. Exercise
keyboard labels, focus, narrow screens and available themes. Read
`static-src/tests/smoke/AGENTS.md` before using the canonical test account flow.
If controllers_js is changed, rebuild its generated bundle with the canonical
builder and validate the emitted asset actually served to the browser.

## M4: Regression, documentation and independent review


Update affected user help with inbox/read-state instructions, recorded-expiration
wording and the existing keep-project help link. Document developer schema/API,
operator schedule/retry/health/rollback, and explicitly state no automatic history
purge. Update the contract only through the same review discipline if intent
changes. Run focused tests first, then the following from `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud --maxfail=1
    wctl run-pytest tests/rq --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl check-rq-graph
    wctl check-test-stubs
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/schemas/user-notifications-contract.md
    wctl doc-lint --path docs/work-packages/20261105_user_notifications

Run stubtest for changed public modules and the repository isolation gates when
test fixtures/stubs change. Record exact commands, exit status and retained output;
do not claim broad success when only focused tests pass. Obtain separate
correctness/UX, security and QA implementation reviews. Use the repository review
templates, preserve valid-state and generated-evidence matrices, close medium/high
findings with independent confirmation before activation.

## M5: Forest test deployment and acceptance


Target `forest.bearhive.internal`, public-to-tailnet URL
`https://forest.tail305ec9.ts.net/weppcloud/`, installed dev Compose preset.
Read `docker/AGENTS.md`, `docs/infrastructure/homelab-tailscale.md`, installed
wctl configuration, `scripts/deploy-production.sh` and relevant deployment docs
in full before acting. Do not substitute forest1, openwepp or wepp1. Verify host,
candidate SHA, worktree, running image/source revision, actual queue worker host,
UID/GID, groups, umask, mounts and database/scheduler configuration. Existing
forest companion workers can consume shared queues; determine which worker will
execute this task and establish matching candidate code before enabling it.
Do not change companion topology or unrelated worker services to make a test pass.

Create a concrete activation record with database backup/restore evidence,
migration command, feature activation order, exact installed-preset deployment
command, affected services, expected next nightly job and rollback command.
Use the canonical deployment entry point and its plan mode where supported;
preserve queues/Redis and avoid cleanup/pruning unrelated resources. A guessed
deployment command is not an executable runbook. If current tooling cannot make
the scoped change, retain the blocker and obtain the smallest necessary operator
decision instead of inventing a workflow.

Back up and apply the additive migration first, with the new schedule disabled,
before loading any new database reader/writer. Install the candidate using the
verified activation record. Before activating the schedule, use disposable forest
accounts/projects and a real worker to run a controlled, explicit registration-ID
scoped sweep under deployed identity/mounts. Verify that both candidate selection
and old-episode reconciliation stay inside that scope, and compare database rows
before/after to prove no non-fixture recipient state changed. Record
source TTL bytes, output rows, API responses, screenshot/browser assertions,
job IDs/tree, runtime cost and failure logs. Use actual catalog-authorized test
accounts; do not alter real-user expiration, permissions or protection settings.
Keep expired/queued cases isolated from real GC: use local disposable filesystem
fixtures outside scanned production roots for those boundary tests. For the live
project use a future date safely within the window and remove fixtures before
expiry. Populate 101 synthetic inbox records for pagination under test accounts.

After preflight success, enable the nightly schedule for the verified candidate.
Verify the actual scheduled
job (not just a manually called function), counts/content, persistence across web
restart, protected/extended project reconciliation, header pages and bulk actions.
Observe one scheduled daily execution; a manual run is not proof the recurring
schedule works. If this cannot be observed within the session, leave that explicit
gate open with its next scheduled time and a reproducible evidence collection step.

Exercise rollback of application activation on forest without dropping tables or
losing read state, then restore the candidate and repeat smoke acceptance. Disable
the new schedule before reverting code so old workers cannot receive unknown
jobs; handle any queued new-task jobs through existing job tools, never flush
Redis. Retain existing GC unchanged throughout. Close only when acceptance and
review evidence support the deployment claim, then update PROJECT_TRACKER and
archive this prompt with its outcome. No production rollout belongs to closure.

## Validation and Acceptance


Valid states include a never-used account with no rows, an empty inbox, populated
active/read/unread rows, resolved/unavailable history, old projects with no valid
TTL, revoked membership and deleted registration. Hostile input cases are tested
separately: foreign IDs, mixed ownership, malformed JSON, missing CSRF, invalid
sort/page, more than 100 IDs, duplicates, booleans-as-IDs and untrusted titles.
Expected absence yields an empty inbox or unavailable project state; it never
becomes a 500 or a false protection claim. Route failure semantics are fixed in
the contract and must be checked at real Flask/database boundaries.

Acceptance is visible: two task runs produce one warning episode; reading it
survives a third run and logout; marking unread restores the badge; selecting page
one changes at most those 100 rows; the second user's count/content is unaffected;
protection resolves the notice on reconciliation; unknown TTL never falsely says
safe; a later new episode becomes unread. Browser sorting matches the specified
read grouping and newest/ID ties. Headers remain usable during count failure.

## Idempotence and Recovery


Database constraints and a sweep lock prevent duplicate work; bounded commits
make interrupted sweeps retryable. Never reset read timestamps during content
updates. Keep additive tables on application rollback, disable schedule before
reverting workers, and retain evidence of pending new task jobs. Restoring a
database backup is not the routine rollback because it could discard unrelated
account activity. Do not delete real project files as fixture cleanup.

## Artifacts and Notes


Store review/disposition, migration/schema readback, test summaries, query plans,
forest activation/rollback record and browser/job evidence in this package's
artifacts directory, omitting credentials/private user data. Exact fixture TTL
content and recipient-scoped output must establish the semantic evidence chain.
Document any unavailable evidence and keep the corresponding task unchecked.

## Interfaces and Dependencies


The public HTTP interface is the contract's three Flask routes. The internal
producer accepts only trusted operator/scheduler inputs, with an injectable clock
for deterministic testing, and returns aggregate telemetry. PostgreSQL provides
transactions, uniqueness and locking. Existing RQ provides recurring execution;
existing Flask/Jinja/frontend helpers provide rendering and authenticated mutation.
No additional dependency, privilege or deployment topology is permitted.

Revision note: 2026-11-05 initial scaffold captures operator requirements and
explicit forest delivery gates; design review passed after corrections; implementation and forest acceptance are tracked above.
Review revision: preserve global CSRF 400/precedence, migrate before real preflight,
default the new schedule off, constrain fixture scope across reconciliation, and
state actual startup-relative scheduler timing rather than imply a fixed UTC hour.

Execution note: the operator explicitly approved scheduler-only recreation with
`wctl docker compose up -d --no-deps --force-recreate scheduler` for activation
and rollback. Canonical targeted-web remains the web activation mechanism; no
full-stack restart is authorized or needed.

Execution revision: retained completed implementation, migration and focused-suite
evidence; broad tests and live browser/scheduler/rollback gates remain open.

Forest pre-activation browser login exposed an existing CAPTCHA verification
transport failure: public forest HTTPS is refused from web/rq-engine containers,
while internal CAP is healthy. The bounded repair and independent review are in
[forest login blocker](../../artifacts/forest-login-blocker.md). Operator approval for the prepared repair is
pending; notification scheduling remains disabled. Full repository results are recorded in the final regression disposition.

Handoff 2026-11-05 21:38 UTC: independent work completed; forest activation is
blocked on the pending operator approval for the prepared CAPTCHA transport repair.
Scheduler-only recreation is already approved and must not be requested again.
No web/scheduler recreation has occurred. On approval, apply the reviewed patch,
update homelab documentation and source snapshots (preserve the repair in both
notification rollback/candidate Compose snapshots), set the host override, then
follow canonical targeted-web activation and the retained token/browser canaries.
Run the application rollback with admissions disabled, restore candidate, then
enable scheduling and observe the real 900-second delayed scheduled execution.
The restricted prepared patch/canary are under `/var/tmp/notification-rollout-20261105/`.
