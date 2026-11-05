# Correctness and User-Experience Review — User notifications

## Metadata

- **Package**: `docs/work-packages/20261105_user_notifications/`.
- **Reviewer**: independent `notification_impl_correctness` agent, reviewer role.
- **Date**: 2026-11-05 UTC.
- **Scope**: notification schema/migration, PostgreSQL repository, TTL producer,
  RQ schedule, Flask routes, header integration, inbox JS/CSS, regression tests,
  retained forest browser/worker/rollback evidence.
- **Revision context**: contract ancestor `ceeaa5960`; notification implementation
  `4cf1432d5`; separately approved forest CAPTCHA repair `f9610c8a1`; mobile
  notification header correction `0bc7cc576`. Final candidate restoration,
  restored-browser acceptance, actual scheduled execution and post-cleanup
  acceptance subsequently passed.
- **Canonical authority**: [notification contract](../../../schemas/user-notifications-contract.md),
  particularly Recipients and authorization, Nightly producer and reconciliation,
  Bell and listing, Flask transport, and Compatibility, regression and rationale.
  Session/CSRF and existing project TTL contracts remain unchanged constraints.
- **Related reviews**: [implementation reviews](20261105_implementation_reviews.md),
  [forest rollback review](20261105_forest_rollout_review.md), and
  [design disposition](20261105_review_disposition.md). Dedicated final security
  and QA reviews remain distinct from this correctness verdict.

## User outcome

Users receive a quiet bell/count and a paginated inbox for recorded upcoming
automatic deletion. They can sort by read state or newest date, select individual
or current-page rows, and explicitly mark read or unread. Opening the list does
not change read state. Read state persists across worker retries and login sessions.

Expected absence produces an empty inbox. Missing/unreadable project metadata
produces an unavailable episode, not a false protection claim. Invalid selections,
foreign IDs, expired authentication, failed CSRF and unavailable database access
have explicit outcomes. A partially completed sweep retains committed batches;
retry preserves existing recipient read state and finishes later work.

## Failure-class coverage

This is a new feature, not an incident repair. Review found and closed malformed
TTL container values aborting the sweep and low-contrast legacy bell rendering.
The malformed-first/healthy-second test covers the affected producer boundary;
the legacy Bootstrap rendering was checked directly in Chromium. Mobile acceptance
also found header overflow; scoped CSS and bounds checks cover the inbox and all
five retained route variants. These are bounded claims, not an exhaustive audit
of every theme, browser or legacy page.

## Valid-state matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Account with no recipient rows | Yes | Empty list, zero badge, no error | Real PostgreSQL tests; ordinary-account empty/isolation check in `forest-browser.json` |
| Empty or beyond-last page | Yes | Empty page and first-page navigation | Repository/list template tests and page-bound rendering |
| Active unread/read inbox | Yes | Count only active unread, stable sort ties, 100 rows maximum, explicit mutations | 1,001-row PostgreSQL pagination/sort test; 101-row forest browser workflow |
| Future publication or ended generic notice | Yes | Publication gate; ended notices excluded from active count | Repository code inspection; no separate live maintenance-publishing workflow claimed |
| Protected, extended or non-active deletion state | Yes | Resolve the current episode without changing read state | Real TTL producer tests for policy/READONLY/date/deletion states |
| Missing, malformed or unreadable TTL | Supported uncertainty | Unavailable, no false protection, no starvation of later healthy projects | Malformed-file/type tests and healthy second registration; unavailable history browser check |
| Later eligibility after a resolved episode | Yes | New episode, new unread recipient state | Real PostgreSQL/TTL episode lifecycle test |
| Revoked project membership | Yes | Hide content/count and reject selection | Real database membership removal and selection rejection test |
| Deleted registration | Yes | Generic resolved history; redact name, subject data and link | Real database deletion/readback test |
| Interrupted or overlapping sweep | Yes | No duplicate episode, lock released, committed read state retained on retry | Overlap and failed-batch tests; live fixture retry with retained `read_at` |
| Malformed/hostile request | No | Bounded rejection before mutation | Real Flask/CSRF and PostgreSQL tests for mixed IDs, duplicates, booleans, size, invalid sort/page and escaped content |

## User-reachable error policy

| Condition | Classification | User-visible result | Evidence / authority |
| --- | --- | --- | --- |
| Missing/invalid CSRF | Expected rejection | Existing JSON 400 `csrf_failed`, before route authentication | Real global handler tests; unchanged CSRF contract |
| Authentication boundary reached without login | Expected rejection | JSON 401 for API; normal login behavior for HTML | Real Flask route checks; notification Flask transport |
| Invalid page/sort or malformed bulk payload | Expected rejection | 400 with no mutation | Validation tests and scoped repository validation |
| Any absent, foreign or no-longer-visible selected ID | Expected rejection | Generic 404, whole selection unchanged | Mixed-owner/missing selection transaction tests |
| Database/count failure | Exceptional | 503/unavailable; no fabricated zero | Real route 503 test; rollback-on-count-failure transaction test; browser count-failure check |
| Uncertain browser mutation response | Exceptional | Selection retained; inline request to refresh/check saved state | Jest and `forest-browser.json` failure-path evidence |
| Stale project observation | Supported uncertainty | Historical wording and unavailable status, excluded from active unread count | Template inspection and `forest-history-browser.json` |

## Generated artifact evidence chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| Operator/user intent | Daily two-week notices, quiet inbox and explicit read state | Ratified contract, ADR-0137 and checkpoint `ceeaa5960` | Pass |
| Source persisted state | Active rolling TTL within the warning window; non-mutating read | Reviewer read `/wc1/runs/no/notifications-fixture-6f487fd65e/TTL`: rolling policy, active state, user protection false, expiration `2026-11-12T20:46:08.847222Z`; SHA-256 matches `forest-fixture.json` | Pass |
| Generated intermediate | One fixture TTL episode and authorized recipient; unrelated rows unchanged | `forest-worker-preflight.json`: real RQ job examined one, created one; TTL bytes and non-fixture rows unchanged | Pass |
| Consumed database state | Retry updates same episode without resetting read state | `forest-retry.json`: created zero, updated one; retained read timestamp | Pass |
| API/Jinja/browser output | Badge, 100/1 pagination, sorting/actions, retained state and private scope | `forest-browser.json`, `forest-history-browser.json`, inspected desktop/mobile/dark screenshots | Pass for initial candidate |
| Application rollback | Baseline pages remain usable, new routes/bell absent, recipient state retained | `forest-baseline-browser.json`; reviewer compared `forest-rollback-before.json` and `forest-rollback-after.json` as identical | Pass |
| Final candidate restoration | Restored candidate routes/browser state remain correct after rollback | `forest-restored-state.json` equals the pre-rollback hashes; `forest-restored-browser.json` repeats the primary acceptance and five mobile route checks successfully | Pass |
| Actual recurring scheduler execution | Enabled scheduler admits and worker completes the real daily task | `forest-scheduler-activation.json` log matches `forest-scheduled-job.json`; `forest-scheduled-readback.json` and `forest-scheduled-browser.json` verify preserved source/read state and consumed output | Pass |
| Acceptance-fixture cleanup | Remove temporary account, rows and project files without affecting recurring scheduling | `forest-cleanup.json` records removed registration, ordinary fixture account, 101 notices, project directory, credential and rehearsal database; reviewer independently confirmed directory absence | Pass |
| Post-cleanup deployed output | Empty private inbox and auth/CSRF behavior remain correct; scheduled service stays active | `forest-post-cleanup-browser.json`; `forest-final-runtime.json`; canonical cleanup deployment log completes successfully with health, image identity and stability checks | Pass |

The fixture TTL SHA-256 is
`210ceafaa291df2351d7dd1cbf1075903e3bd5ea1c3b4b2d5cc8344ed298d3e0`.
Rollback snapshots preserve 101 notification/recipient rows, including one read
recipient, with matching content and recipient hashes. The source read and
snapshot comparison above were independently performed by this reviewer.

The reviewer inspected all three retained inbox screenshots. Controls and status
text are visible in desktop/light, mobile/light and desktop/dark captures. The
retained five 390px header checks have maximum right extent 374px. This establishes
the measured layouts; it is not a representative-user comprehension study or a
claim of complete WCAG conformance.

The 1,001-row PostgreSQL query-plan artifact reports 0.976 ms for unread count and
2.072 ms for the listing query on the rehearsal workload. This is a bounded
measurement, not a latency guarantee for all account sizes.

Restored-state hashes were independently compared with the pre-rollback snapshot
and match exactly. The final worker parity artifact records UID:GID 1000:993,
group 993 and four live batch workers; the recorded RQ entry/producer source
hashes also match the checkout in this review. Scheduling was activated at
22:46:39 UTC and loaded at 22:46:53 UTC with the contracted daily interval,
900-second initial delay and zero jitter. The scheduler log records admission at
23:01:53.638 UTC and actual job `b4cd4984-a290-4596-8587-91cdc374963c` was created
at 23:01:53.639 UTC with no arguments. The full sweep examined 572 registrations,
updated the existing fixture episode, created none, classified 470 unavailable
and skipped 101; it completed in 2.098 seconds without an exception. The aggregate
availability audit accounts for 469 absent local directories, one absent TTL and
102 known states. Missing metadata was not initialized and was not used to invent
deletion predictions. This is expected uncertainty on this forest registration
set, not evidence that all registrations have valid local TTL sources.

The scheduled before/after evidence preserves the fixture TTL SHA-256 and recipient
read timestamp `2026-11-05T22:47:23.916225+00:00`; recorded expiration matches the
source. Browser evidence confirms the retained read state, active warning and
database unread count. The preserved GC pause is independent of this feature.
Cleanup evidence records removal of registration 2325, temporary ordinary user
2831, all 101 fixture notices, the fixture credential and the rehearsal database.
The reviewer independently confirmed that the exact fixture directory is absent.
Canonical targeted-web recreation released the open NFS log handles; the retained
cleanup deployment log confirms successful health, candidate-image identity,
stability and worker-registration checks. Post-cleanup browser evidence confirms
an empty inbox, hidden zero badge, anonymous API 401 and missing-CSRF 400.
Final runtime evidence records only the authorized web, RQ-engine and scheduler
container identity changes overall, with the scheduler unchanged during this last
web recreation and notification scheduling still enabled.

**Highest supported completion claim:** implemented and environment validated on
the restored forest candidate, with application rollback and reactivation
demonstrated, including actual scheduler admission, consumed output, completed
fixture cleanup and post-cleanup acceptance. Correctness acceptance is complete
for the authorized forest test deployment. No production deployment or
incident-wide resolution is certified here.

## Regression evidence and limits

[Regression results](regression-results.json) retain log locations and hashes:
WEPPcloud 2,325 passed; RQ 1,329 passed / 220 skipped; frontend 1,051 passed;
corrected focused set 78 passed; RQ graph, stubtest, stub completeness and changed
broad-exception checks passed. The normal frontend lint passed; targeted script
lint is recorded in implementation review because its files sit outside that
normal controller glob.

The broad Python run reports 12,877 passed / 423 skipped / one failed. The failure
is the old migration-head assertion collected before its correction; fresh
verification passed that test, the corrected focused set, and the entire
WEPPcloud suite. This review accepts the documented diagnosis and fresh scoped
evidence but does not recast the broad run as all-green or waive its recorded
failure. No additional broad run was performed by this reviewer.

## Review checks

- [x] Canonical intent and ancestor checkpoint are named.
- [x] Absent, empty, populated, legacy/uncertain and hostile states are separated.
- [x] Input validation and stored-state combinations are reviewed independently.
- [x] Real PostgreSQL, filesystem, global CSRF and browser boundaries are exercised.
- [x] Mocks are limited to injected failures; real persistence/read boundaries remain.
- [x] Worker result is supported by source/recipient/browser readback, not job success alone.
- [x] Partial success, retry, private scope and error recovery behavior are explicit.
- [x] Implementation, environment validation and the authorized deployment scope are distinguished.
- [x] No claim of exhaustive combinations, all-browser coverage or user comprehension is made.
- [x] Final restored-candidate browser acceptance and unchanged state are evidenced.
- [x] Actual scheduled-run evidence includes source, read-state and browser readback.
- [x] Acceptance-fixture cleanup and post-cleanup web acceptance are complete.

## Findings

| ID | Severity | Surface | Description / action | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| COR-I01 | Medium | TTL producer | Malformed policy/state containers could abort a whole sweep; add strict types and healthy-peer regression | `producer.py`; `test_malformed_ttl_types_mark_unavailable` | Resolved; independently confirmed |
| COR-I02 | Medium | Legacy header | Dark bell text on dark Bootstrap header; require explicit contrasting normal/hover/focus color | Chromium computed-style recheck: white foreground, dark background, solid focus outline | Resolved; independently confirmed |
| COR-I03 | Low | History wording | Historical/unavailable content looked current; label earlier notice | `notifications.htm`; history browser evidence | Resolved |
| QA mobile follow-up | Medium | Narrow headers | Bell/theme groups overflowed; wrap scoped groups and verify all variants | `forest-header-bounds.json`; `0bc7cc576`; independent QA confirmation | Resolved |

No new medium/high correctness finding was identified in this final source and
evidence review. All correctness acceptance gates for the forest test scope have
supporting evidence. Residual limits remain: one actual daily admission has been
observed, the scheduler resets its initial delay on restart, missing local source
metadata remains unavailable, and the broad Python run retains the separately
diagnosed stale assertion described above. These limits are not converted into
claims of production validation, indefinite scheduler reliability or all-green
broad-suite execution.

## Verdict

- **Implementation correctness gate:** pass for the reviewed source and evidence.
- **Unresolved code findings:** high 0; medium 0; low 0.
- **Final correctness acceptance gate:** pass for the authorized forest test
  deployment, including scheduled execution, rollback/restoration and cleanup.
- **Release recommendation:** accept the completed forest test scope; no production
  recommendation is made. Security and QA sign-offs remain independently owned.
- **Reviewer sign-off:** `notification_impl_correctness`, 2026-11-05 UTC.

## Artifact observability gate

The comparable account surfaces are the existing Runs catalog and account
preferences. Notification source is the ordinary project TTL/protection state;
new content/read state is account-owned PostgreSQL data observable through the
authorized inbox and operator job telemetry. Retained worker/browser/rollback
artifacts make this feature's evidence inspectable without disclosing credentials.

No new model/project file or archive member is produced, so project archive/restore
member tests are N/A. This is the contract's account-record boundary, not a new
hidden project artifact exclusion. Real writer/failure/rollback checks demonstrate
notification state retention. Existing project deletion/protection semantics and
GC remain outside the change.
