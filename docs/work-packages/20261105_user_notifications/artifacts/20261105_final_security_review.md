# Final implementation and runtime security review — user notifications

## Metadata

- **Package**: `docs/work-packages/20261105_user_notifications/`.
- **Reviewer**: independent `notification_impl_security` agent, security_reviewer role.
- **Date**: 2026-11-05; evidence reviewed through 23:20 UTC.
- **Scope reviewed**: notification schema/migration, SQL repository, TTL producer,
  Flask routes, RQ task/schedule, header/list templates, browser script, tests,
  forest runtime evidence and the separately authorized CAPTCHA transport repair.
- **Revision context**: contract ancestor `ceeaa5960`; candidate working tree at
  `0bc7cc576b3ed7190c59e40f9d828e62722c182a`; rollback manifest identifies baseline
  `ceeaa5960`, candidate wiring `4cf1432d5`, and preserved repair `f9610c8a1`.
- **Canonical authority**: [notification contract](../../../schemas/user-notifications-contract.md),
  [CSRF contract](../../../schemas/weppcloud-csrf-contract.md),
  [session contract](../../../schemas/weppcloud-session-contract.md).
- **Related reviews**: [implementation correctness/UX and QA dispositions](20261105_implementation_reviews.md),
  [design correctness review](20261105_correctness_review.md),
  [forest rollback review](20261105_forest_rollout_review.md).

This review inspects code and retained evidence. The reviewer independently
exercised malformed TTL files during the earlier implementation review. Other
runtime tests below were executed by the primary agent and checked here through
their retained artifacts and test assertions. This is not a claim that the
reviewer independently repeated the entire deployment.

## Security Triage Decision

- **Security impact level**: high.
- **Dedicated security review required**: yes.
- **Rationale**: new authenticated account reads/mutations, project metadata
  exposure, scheduled worker writes and a separately authorized authentication
  transport repair cross security boundaries.
- **Threat assumptions**: browser parameters and stored project metadata may be
  malformed or hostile; users may select another account's notification IDs;
  membership can be revoked; tasks may overlap or retry after partial commits;
  forest source mounts can expose new templates to old application processes.
- **Valid states preserved**: never-used/empty account, populated read/unread
  inbox, unavailable/resolved history, old or missing TTL, protected projects,
  revoked membership and deleted registrations. Hostile inputs are assessed
  separately from those valid states.

## Findings

| ID | Severity | Surface | Description and evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-IMPL-01 | Medium | TTL producer | Array/object `policy` or `delete_state` previously raised `TypeError` in set membership and could abort the shared sweep. | Validate field types and preserve unavailable handling; prove later healthy projects still run. | Resolved: explicit checks in `notifications/producer.py`, direct file-boundary verification and malformed-first/healthy-second PostgreSQL tests. |

No unresolved high, medium or low security finding was identified in the reviewed
candidate. Earlier design findings (CSRF precedence and preflight ordering/scope)
remain closed; see [design disposition](20261105_review_disposition.md).
The blueprint availability context, episode metadata, diagnostic run identifier
and subsequent header integration were re-reviewed without new medium/high findings.

No risk acceptance is recorded or implied. All security acceptance gates described
below have retained passing evidence.

## Verdict

- **Security gate status**: pass for the implementation and forest runtime
  boundaries described below, including scheduled execution and final cleanup.
- **Unresolved findings**: high 0; medium 0; low 0.
- **Release recommendation**: security gate satisfied for package closure within
  the authorized forest test-deployment scope.
- **Scope limit**: no production or forest1 deployment approval. At this review,
  baseline rollback and final candidate restoration/browser acceptance passed.
  The notification schedule was enabled at 22:46:39 UTC. Its actual first enqueue
  occurred at 23:01:53.639 UTC and completed successfully; source/database/browser
  evidence confirms preserved read state and unchanged source TTL. Final fixture
  cleanup and post-cleanup browser/runtime acceptance passed after canonical
  targeted-web recreation released the existing NFS log handles. The scheduler
  identity remained unchanged during that final recreation.

The security pass does not replace correctness/UX or QA review. It certifies the
first actual scheduled execution, not an unobserved future recurrence.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- [x] The contract and linked reviews enumerate valid absent, empty, populated,
  legacy, unavailable, resolved and hostile states separately.
- [x] Real PostgreSQL/Flask tests cover empty results, preservation of read state,
  malformed selection rejection, transaction rollback, revoked membership and
  deleted-subject redaction.
- [x] Browser evidence covers ordinary-account empty/isolation behavior, history,
  explicit errors, read/unread persistence and selection preservation on failure.
- [x] Existing global CSRF `400 csrf_failed` precedence is preserved; JSON 401
  occurs when authentication is reached.
- [x] This approval does not substitute for correctness/UX approval or claim
  exhaustive combinations beyond the named tests.

### 1) Auth, Session, and Authorization

- [x] Routes require authenticated account identity; recipient queries scope to
  that account and recheck current project membership.
- [x] Administrator roles do not expand a personal inbox. The live ordinary
  account saw no fixture content and a foreign-ID mutation returned 404.
- [x] Mixed authorized/foreign selection rejects atomically in real database tests.
- [x] Mutation retains global CSRF enforcement without exemption. Missing/invalid
  CSRF and authentication ordering are covered by the real handler tests.
- [x] Responses are private/no-store; deleted-project history is redacted and has
  no project link. Existing JWT/session contracts are unchanged.

### 2) Secrets and Credential Handling

- [x] The reviewed additions introduce no plaintext credentials or new secret mount.
- [x] Existing `CAP_SECRET_FILE` supplies the CAPTCHA secret; the repair changes
  only internal verification routing, not secret or token semantics.
- [x] Retained JSON artifacts contain test identifiers, results and digests, not
  passwords, session cookies, CAPTCHA tokens or CAPTCHA secrets.
- [x] No authentication bypass or missing-secret recovery path was added.

### 3) Input Validation and Output Safety

- [x] Selection validates positive integer IDs, excludes booleans and duplicates,
  requires a strict boolean state and enforces the 100-ID bound.
- [x] Page/sort validation precedes database work; SQL parameters remain bound.
- [x] Jinja escapes title/body; tested script-like content renders as text.
- [x] Project/help URLs are server-generated; no arbitrary external action URL
  or user-controlled fetch target is introduced.
- [x] Expected database failure returns explicit 503 rather than fabricated zero;
  failed count within mutation rolls back the read-state update.

### 4) File System and Run-Tree Boundaries

- [x] Producer reuses non-mutating descriptor-bound project/source readers.
  Request endpoints perform no project filesystem scan or repair.
- [x] Trusted fixture scope constrains both new candidates and prior episodes;
  an explicitly empty scope is a no-op and cannot expand to all projects.
- [x] Forest worker preflight confirms unchanged fixture TTL bytes and unchanged
  non-fixture notification rows.
- [x] Notification persistence is account PostgreSQL data, not a new project file.
- [x] Final cleanup assertions confirm removal of the fixture registration,
  disposable user, 101 fixture notifications, rehearsal database and credential.
  The reviewer directly confirmed the exact fixture directory and credential
  path are absent; no non-fixture notification rows required removal.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Task uses the existing batch queue and no subprocess or shell execution.
- [x] Source schedule defaults disabled and task inputs are operator-only;
  no browser enqueue or scope parameter was introduced.
- [x] Retained RQ graph check reports artifacts up to date.
- [x] Live scoped job tree completed; a second job preserved the user's read state.
- [x] Rollback admission evidence shows scheduling disabled, no pending
  notification jobs and four eligible local batch consumers at that checkpoint.
- [x] Final worker parity evidence identifies four local batch consumers with
  UID/GID 1000:993 and matching candidate task/producer source hashes.
- [x] The separately authorized scheduler-only recreation enabled notifications
  with interval 86,400 seconds, initial delay 900 seconds and zero jitter; the
  concurrent operator GC pause remains disabled.
- [x] Actual scheduler-originated job `b4cd4984-a290-4596-8587-91cdc374963c`
  followed the scheduler log at 23:01:53 UTC with no fixture scope arguments.
  It examined 572 registrations in 2.098 seconds, updated the existing fixture
  episode and did not reset its read timestamp.

### 6) Agentic Tooling and MCP Surfaces

- [x] No new agent, MCP, token-minting or external publication surface is added.
- [x] Work remains bounded to the requested inbox and forest test deployment.
  The CAPTCHA repair and scheduler-only recreation have separate recorded
  operator authorization; unrelated GC pause is preserved by the rollback manifest.
- [x] This reviewer changed only this designated security artifact.

### 7) Network and External Integrations

- [x] Notifications introduce no outbound integration, email, push or streaming service.
- [x] The forest CAPTCHA repair sends server-side verification over the existing
  Docker network to the existing CAP service. Browser challenge/assets retain
  `https://forest.tail305ec9.ts.net/cap`.
- [x] All three actual verification helpers (web, rq-engine project and fork)
  accepted fresh tokens and rejected replayed, invalid and missing tokens.
- [x] No published port, public route, CORS relaxation or authorization expansion
  accompanies the transport change. Existing verification timeout/error behavior remains.

### 8) CI/CD and Supply Chain

- [x] No third-party dependency, runner privilege or workflow token change.
- [x] Canonical targeted-web activation was used for web/rq-engine; recorded
  container comparison shows only those two services changed during CAP repair.
- [x] Source-mounted rollback preserves restricted baseline/candidate snapshots,
  not merely image identifiers, and does not flush Redis or recreate the full stack.
- [x] Final candidate restore browser acceptance passed; reloaded notification
  and recipient-state hashes match the pre-rollback state exactly.
- [x] Final canonical targeted-web recreation completed its image, stability and
  worker-registration checks. Final identity comparison records only the
  authorized web/rq-engine/scheduler changes across the deployment; the scheduler
  and all other container identities were preserved during final cleanup.

### 9) Data Integrity, Locking, and Concurrency

- [x] Database uniqueness and a sweep advisory lock prevent duplicate live episodes;
  per-recipient upsert does not reset read timestamps.
- [x] Stable recipient-row locking and one transaction enforce atomic bulk changes.
- [x] Tests cover overlapping sweeps, partial committed-batch retry and rollback of
  failed read-state mutation. QA fixed test lock keys so isolated test schemas do
  not contend with the production sweep lock.
- [x] No NoDb lock or TTL mutation contract changes. Additive migration preserves
  old-code compatibility and operational rollback retains the new tables.
- [x] Rollback before/after artifacts match both content and recipient-state
  digests: 101 notification rows, one read row, exact hashes unchanged.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Producer logs aggregate progress/failure and escaped run identity on unreadable
  observations; exceptions are not silently swallowed.
- [x] UI failures provide retry/check guidance without disclosing database internals.
- [x] Rollback preserves separately authorized CAPTCHA routing and concurrent GC
  pause, with disabled notification admissions and retained read state.
- [x] Candidate restoration and actual scheduler activation timing are recorded.
- [x] Actual scheduled result, source/database readback and browser output are
  recorded. With no scheduler restart, the next daily enqueue is expected near
  2026-11-06 23:01:53 UTC, subject to polling; future execution is not claimed.

## Validation Evidence

The retained [regression results](regression-results.json) identify commands/logs
and hashes. Relevant results are 2,325 WEPPcloud tests passed; 1,329 RQ tests
passed/220 skipped; 1,051 frontend tests passed; scoped corrected tests 78 passed;
RQ graph, stub checks and broad-exception gate passed. Normal frontend lint passed,
and QA separately required standalone notification script/test lint because the
normal glob covers controller files.

The broad run reported 12,877 passed, 423 skipped and one migration-head failure
from a pre-correction assertion loaded by the long-running process. Fresh focused
and full WEPPcloud runs passed after correction, including a fresh rerun of the
failed test. This is documented evidence, not an assertion that the original
broad command passed.

| Boundary | Retained evidence | Assessment |
| --- | --- | --- |
| Actual scoped worker and non-mutating TTL | [worker preflight](forest-worker-preflight.json), [fixture provenance](forest-fixture.json) | Passed; unchanged non-fixture rows and TTL bytes |
| Retry/read-state preservation | [retry job/readback](forest-retry.json) | Passed |
| Browser auth/isolation, read/unread, failure behavior | [browser result](forest-browser.json), smoke test assertions | Passed for named scenarios |
| Resolved/unavailable history and active count | [history result](forest-history-browser.json) | Passed |
| Five header routes, narrow viewport and dark theme | [header bounds](forest-header-bounds.json), browser screenshots | Passed for named routes |
| CAPTCHA restoration without bypass | [CAP canaries](forest-cap-repair.json), [authorization/outcome](forest-login-blocker.md) | All three helpers and actual login passed |
| Baseline application rollback | [baseline browser](forest-baseline-browser.json), [admission state](forest-rollback-admission.json), [source manifest](forest-source-rollback-manifest.json) | Passed; inbox absent and existing pages available |
| Durable state across rollback | [before](forest-rollback-before.json), [after](forest-rollback-after.json) | Exact recorded hashes/counts match |
| Final candidate restoration | [restored browser](forest-restored-browser.json), [restored state](forest-restored-state.json) | Passed; full named browser scenarios and exact state hashes preserved |
| Scheduler activation and worker parity | [activation](forest-scheduler-activation.json), [worker parity](forest-final-worker-parity.json), [pre-sweep read state](forest-scheduled-before.json) | Activated; four local consumers match candidate hashes; GC pause preserved |
| Actual scheduled population | [scheduled job](forest-scheduled-job.json), [readback](forest-scheduled-readback.json), [browser](forest-scheduled-browser.json) | Passed; scheduler log timestamp matches, source TTL and read timestamp preserved |
| Unavailable source audit | [aggregate availability](forest-source-availability.json) | 469 missing local project directories and one missing TTL explain all 470 unavailable observations; no source initialization or false protection claim |
| Final fixture cleanup | [cleanup](forest-cleanup.json), guarded cleanup assertions and direct path-absence checks | Passed; fixture database records, directory, credential and rehearsal database removed |
| Final post-cleanup acceptance | [browser](forest-post-cleanup-browser.json), [runtime](forest-final-runtime.json), canonical deployment log | Passed; empty inbox/hidden zero badge, anonymous 401, missing-CSRF 400, services running and scheduler unchanged |

For the final cleanup boundary, the reviewer inspected the guarded assertions in
`/var/tmp/notification-rollout-20261105/finish-cleanup.py`, the actual browser
assertions in `notifications.spec.js`, its retained `post-cleanup-browser.log`
(one passed), the identity/environment assertions in `final-runtime.py`, and
`deploy-cleanup-release.log` showing completed canonical deployment checks.
The earlier cleanup failure caused by open NFS log handles remains documented;
the final evidence supersedes that incomplete attempt.

## Residual Risk

No unresolved medium/high finding is accepted as residual risk. Actual scheduled
execution, its state/recipient evidence, rollback/restoration, fixture cleanup and
final browser/runtime checks are complete. The read-only availability audit
explains the high unavailable count without concealing it or changing
TTL/deletion policy.
Daily observation can lag visits, in-app notices cannot reach absent users, and
history retention is unbounded by the 100-row page size; these are explicitly
contracted limitations, not new exceptions approved by this review.

## Sign-off

- **Security reviewer**: `notification_impl_security`, updated 2026-11-05 23:20 UTC;
  pass for implementation and all named forest acceptance boundaries. No open
  security gate or unresolved finding remains.
- **Package owner**: primary agent records package completion alongside the
  independent correctness/UX and QA dispositions. No operator risk acceptance
  is inferred.

## Artifact Observability Gate

Follow [artifact observability](../../../standards/artifact-observability-standard.md)
and [generated-artifact validation](../../../standards/generated-artifact-validation-standard.md).
The comparable existing account surface is the Runs catalog; authoritative TTL
files are consumed without modification. Notification content/read state is
account data exposed through the authorized inbox, not project archive content.

- [x] Source TTL provenance, actual worker result, database readback, API/browser
  assertions and rollback digests establish the retained evidence chain.
- [x] Missing/invalid source evidence produces unavailable state rather than
  fabricated safety; the direct malformed-file check and real retry tests cover
  the changed boundary.
- [x] New project archive members are N/A because this feature creates no project
  artifacts. No archive visibility exception is introduced.
- [x] Final restored browser output and durable-state hashes are retained.
- [x] Actual scheduled consumer output and resulting browser state are retained.
- [x] Final fixture filesystem/database/credential disposition and post-cleanup
  browser/runtime output are retained and reviewed.

Highest supported claim at review: implementation locally validated and named
forest browser/worker/rollback/restoration boundaries validated; scheduler
activation and first actual scheduled execution verified; final cleanup and
post-cleanup acceptance verified. The dedicated security gate is satisfied for
the authorized forest test deployment and package closure.
