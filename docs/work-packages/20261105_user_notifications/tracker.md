# User notifications tracker

Status: approved CAPTCHA repair and notification forest activation in progress.
Last updated: 2026-11-05 21:38 UTC.

## Task board

- [x] Inspect TTL, scheduler, database and shared headers.
- [x] Record conversation-derived behavior in the canonical notification contract.
- [x] Scaffold complete implementation/testing/forest deployment ExecPlan.
- [x] Obtain two independent contract reviews, correct findings and obtain post-fix confirmation.
- [x] Record operator decision checkpoint and standalone ancestor commit (`ceeaa5960`).
- [x] Add ADR-0137 and additive migration; restored-database rehearsal passed.
- [x] Implement task, Flask surfaces and header/list UI.
- [x] Complete local regression and independent implementation reviews (broad-run disposition below).
- [ ] Deploy to forest, verify artifacts/browser/job tree, observe nightly execution.
- [ ] Verify rollback, finish documentation and close package.

## Decisions

- 2026-11-05 19:58 UTC — Nightly RQ producer; Flask inbox/API; PostgreSQL read state.
  Reuses existing mechanisms and avoids a second account API or delivery service.
- 2026-11-05 19:58 UTC — Bell with unread count, direct listing, no attention popup.
  Explicit read/unread actions preserve user control and eliminate repeat alerts.
- 2026-11-05 19:58 UTC — 100 rows per page; select-all is current page; unread-first,
  read-first and newest sorts. Page-bound selection limits accidental bulk changes.
- 2026-11-05 19:58 UTC — Start with background non-mutating TTL reads; catalog
  projection deployment is not assumed. Preserve its separate owner and cutover.
- 2026-11-05 19:58 UTC — Test deployment targets forest, not forest1; do not infer
  authorization to deploy production from the work-package scaffold request.

## Contract checkpoint

Starting revision: `5fb446744d1e5d0e193c3d3aa2cf2dc040e22823`.
Checkpoint: [contract decision](artifacts/20261105_contract_decision.md).
Ancestor revision: `ceeaa5960`. Operator requested execution on 2026-11-05;
reviewed intent ratified and forest delivery authorized. Runtime implementation in progress.
Reviews: [correctness/UX](artifacts/20261105_correctness_review.md),
[security](artifacts/20261105_security_review.md), and
[disposition](artifacts/20261105_review_disposition.md). Both reviewers confirmed
closure; no open medium/high design findings. Forest runtime acceptance remains pending.

## Validation and evidence

Documentation lint: contract, seven package documents and PROJECT_TRACKER passed
with zero errors/warnings. Spelling preview is clean for contract/package files.
Implementation and PostgreSQL tests passed; see the execution update below.
Full-suite and forest browser/scheduler/rollback acceptance remain open.

## Surprises and risks

The worktree already has unrelated controller-input-validation documentation
and a modified PROJECT_TRACKER. Preserve those edits; ignore generated docs_index.
Daily access compilation and GC use different queues; do not promise immediate
expiration refresh. Existing header overrides require an explicit coverage map.

## Next action

Finish the full repository test run, activate candidate web code, validate the
browser workflow, rehearse rollback, then observe the enabled scheduled task.

## Execution update — 2026-11-05 UTC

26 real PostgreSQL/TTL/Flask tests pass; 1,051 frontend tests passed, with the four
notification tests rerun after final script changes. Independent correctness,
security and QA code reviews have no open medium/high findings. Full pytest completed; see the final regression disposition below. Rehearsal restored database counts remained 28 users, 570 runs and 259
memberships after migration to f6b8d27a901c. Live backup is restricted under
`/var/tmp/notification-rollout-20261105/`.

Operator explicitly approved scheduler-only recreation for activation and rollback:
`wctl docker compose up -d --no-deps --force-recreate scheduler`. This bounded
exception avoids the canonical full deployment restarting unrelated services.
Web activation uses the canonical targeted-web entry point. Blueprint availability
context prevents mixed-version header links during source-mounted cutover.

Focused regression results: WEPPcloud 2,325 passed; RQ 1,329 passed and 220 skipped;
frontend 1,051 passed. Candidate implementation is `4cf1432d5`. Live migration is
`f6b8d27a901c`; application activation and scheduler remain pending.

Forest pre-activation browser login exposed an existing CAPTCHA verification
transport failure: public forest HTTPS is refused from web/rq-engine containers,
while internal CAP is healthy. The bounded repair and independent review are in
[forest login blocker](artifacts/forest-login-blocker.md). Operator approval for the prepared repair is
pending; notification scheduling remains disabled. Full repository results are recorded in the final regression disposition.

The disposable restored database `notifications_rehearsal_20261105` was removed
after confirming zero connected sessions. Migration/query-plan evidence and the
restricted original backup remain retained. The live account database was not
restored or downgraded.

## Final regression disposition — 2026-11-05 21:38 UTC

Full pytest: 12,877 passed, 423 skipped, one failure in 3,654.63 seconds. The
long-running process had collected the old migration-head assertion before its
correction. Its trace compares old/new migration IDs while displaying the edited
source line. Fresh verification passes (1 test); the corrected focused suite
passed 78 and the complete WEPPcloud suite passed 2,325. No single all-green full
run is claimed. Exact logs/hashes are in `artifacts/regression-results.json`.

Awaiting the already presented approval for the reviewed forest CAPTCHA transport
repair. No web deployment, application rollback or scheduled execution is claimed.
The scheduler-only recreation approval remains valid. Fixture run registration
2325 and ordinary test user 2831 are retained for acceptance; remove them and the
gitignored `docker/secrets/notifications-acceptance.env` after completing acceptance.
The fixture has a future expiry and must be cleaned before 2026-11-12.

Operator approved the CAPTCHA routing repair. Canonical targeted-web activation
is running for `f9610c8a1`; schedule remains disabled. Root/Docker host overrides
are aligned and notification-only rollback snapshots retain the repair.
