# Security review — production notifications and catalog cutover

## Findings

| ID | Severity | Surface | Description and evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Fleet execution and partial failure | The initial plan lacked a concrete admission hold. The canonical script resumes its global fence on normal completion and most errors, before package artifact acceptance. A traffic hold alone cannot prevent execution of retained queued/deferred work. `scripts/deploy-production.sh:849`, `:1007`, `:1134`, `:1422`; active plan M0/M3. | Stop old web/RQ producers, scheduler and all five old worker containers, verify child exit and empty started registries, hold remotes, and permit only new-runtime traffic when the canonical script resumes. Never restart old containers after 2.x writes, including on failure. | Resolved at control-design review: revised M3 states concrete services, warm timeout, ordering, outage and failure rules. Actual stop/readback remains a mandatory execution gate. |
| SEC-02 | Medium | Migration target and recovery copy | The initial restored-database rehearsal lacked an executable target guard. Old Flask configuration could select production while rehearsing. Active plan M2; `configuration.py:293`; notification migration. | Override both URI variables before Flask import; validate the owned target, effective app URI and connected database/server before upgrade; preserve backups and verify production unchanged after rehearsal. | Resolved at command review: helper digest and checks below. Successful isolated rehearsal remains required before production migration. |
| SEC-03 | Medium | Old-runtime registry cleanup | The original deployment probe calls `StartedJobRegistry.get_job_ids()`, which cleans the registry. Its pre-build fallback can run old 1.16 against shared 2.x-written state. The first proposed `cleanup=False` correction also fails on actual RQ1.16.2, whose method has no cleanup parameter. | Use raw Redis `ZCARD` of each started-registry key, conservatively treating stale entries as a hold. Regression must forbid `get_job_ids()` and prove the embedded script reads cardinalities without cleanup under both runtime versions. | Resolved: raw ZCARD source, 38 passing execution tests, and independent exact-program execution under installed 1.16.2 and 2.12.0. |

These findings concern execution controls, not requests for new infrastructure or renewed
authorization. No risk acceptance is recorded. Medium/high findings require
closure or explicit owner risk acceptance before their dependent steps.

## Metadata

- **Package**: `docs/work-packages/20261105_production_notifications_catalog_cutover/`.
- **Reviewer**: independent `production_cutover_security`, security reviewer role.
- **Date**: 2026-11-06 UTC; control review updated through 05:19 UTC.
- **Scope reviewed**: active deployment plan, readiness record, canonical deploy
  script, production build inputs, notification migration/auth/worker boundaries,
  RQ migration and query publication/admission contracts.
- **Commit context**: application baseline `2111d0eb2`, with the scheduler repair
  still under implementation. Production baseline is reported as `0da9c9071`.
- **Related artifacts**: [readiness record](../notes/production-deployment-readiness.md),
  [active plan](../prompts/active/deployment_execplan.md),
  [notification implementation/forest security review](../../20261105_user_notifications/artifacts/20261105_final_security_review.md).
  [Current correctness review](20261106_correctness_review.md) retains the
  independent installed-runtime probe. Final deployment evidence is pending.

This reviewer inspected source and retained records without production mutations.
Production values below are attributed to the primary operator's readiness
record; they are not independently refreshed live observations. Historical forest
acceptance supports implementation confidence but does not certify production.

## Security Triage Decision

- **Security impact level**: high; dedicated review required.
- **Rationale**: private account state, shared Redis job state, process identities,
  NFS publication guards and independently rebuilt production images cross trust
  and recovery boundaries during this deployment.
- **Threat assumptions**: account identifiers and project metadata may be hostile;
  tasks can retry and overlap; old workers may remain alive after a host cutover;
  errors can occur after partial recreation; backups contain private account and
  task data; mutable build references can advance between host builds.
- **Authority**: the operator authorized this combined deployment, the selected
  configuration-default commit, bounded remote worker holds and scheduler
  activation. No new service, identity, mount or destructive data repair follows
  from that authority.

Valid states to preserve:

| State | Required outcome |
| --- | --- |
| Absent or empty inbox; missing legacy TTL | Account remains usable; no invented TTL, false warning or source initialization. |
| Populated inbox, read/unread history | Account isolation and durable read state survive retries, migration and feature rollback. |
| Revoked membership or deleted registration | Existing private history follows contract redaction; no project disclosure. |
| Queued/deferred/scheduled/completed/failed RQ state | Preserve IDs, dependencies, metadata and diagnostics; running jobs drain in their original runtime. |
| Empty queue with historical/deferred state | Empty ready queues never authorize Redis flushing or registry cleanup. |
| Writable, readonly, legacy or temporarily unavailable managed roots | Correct shared guard/identity and explicit degraded status; no standalone fallback or permission expansion. |
| Retained catalog receipts, permits or old pilot manifests | Preserve evidence and obligations; old pilot authority cannot become a new default-queue pilot. |
| Malformed/foreign notification selection or stale scope identity | Explicit rejection without partial unauthorized updates or publication. |

## Verdict

- **Gate status**: pass for the revised execution controls and candidate repair;
  this is not final production acceptance or package closeout.
- **Unresolved findings**: high 0; medium 0; low 0.
- **Recommendation**: proceed with guarded rehearsal and the reviewed sequence,
  retaining actual backup/hold/readback evidence before their dependent steps.
  Feature enablement and package closure additionally require the
  execution evidence below; a plan is not a passing production test.
- **Correctness boundary**: this review does not replace correctness, QA or
  operator control review, and does not infer their approval.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- [x] Contract states above distinguish valid absence/legacy cases from hostile
  inputs; deployment preserves existing project executable selections and GC pause.
- [x] Notification forest evidence includes genuine PostgreSQL and browser
  isolation, CSRF, malformed selection, retry and read-state preservation.
- [ ] Current production valid/hostile browser and artifact readback, plus the
  independent correctness review, remain required.

### 1) Auth, Session, and Authorization

- [x] `routes/notifications.py:26` requires the current authenticated account;
  reads/mutations use its identity and private/no-store responses. Global Flask
  CSRF remains active (`app.py:71`); no exemption is introduced here.
- [x] Public catalog job polling must retain the sanitized maintenance shape
  through job retention and rollback, as required by the RQ/query contracts.
- [ ] Production checks must include foreign-ID atomic rejection, anonymous
  behavior, CSRF failure and authenticated project/download visibility.

### 2) Secrets and Credential Handling

- [x] Plan keeps raw backups and credentials outside git in private host evidence
  directories; no new credential or secret mount is proposed.
- [ ] Verify mode 0700 directories and restricted backup/config files. Sanitize
  retained summaries; no rendered Compose environment, process argv, raw Redis
  job payloads, cookies, database URIs or secret-bearing command traces in artifacts.
- [ ] Backup commands must use existing mounted secrets/configuration without
  placing credentials in argv or printing them. Export only allowlisted fields.

### 3) Input Validation and Output Safety

- [x] Notification route limits sorts/pages and validates JSON selection through
  the repository. Prior security review covers escaping and account ownership.
- [x] Trusted fixture registration scope applies to both notification creation and
  reconciliation (`notifications/producer.py:118`); an empty scope is a no-op.
- [ ] Production fixture names/IDs and cleanup manifest must bind only owned
  resources. No request parameter may select an arbitrary task function or queue.

### 4) File System and Run-Tree Boundaries

- [x] Query contract requires all four managed namespaces, external stable guard
  inodes and no managed-to-standalone fallback. Readonly behavior remains intact.
- [ ] Prove actual UID/GID/groups/umask, mounts and cross-host exclusion under the
  final runtime; do not infer access from root diagnostics or process health.
- [ ] Retain source TTL byte comparisons and guard/receipt evidence before owned
  fixture retirement. Never remove a guard inode to resolve contention.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] RQ contract forbids mixed 1.x/2.x execution and reverse compatibility claims.
  Preserve deferred and historical records; no Redis flush or canceled-job purge.
- [x] SEC-03 closed: raw cardinality avoids both old-runtime registry cleanup and
  incompatible keyword calls. A stale entry conservatively blocks deployment.
- [x] The current scheduler batch/default mismatch is identified and under repair;
  notification population remains on batch. No queue topology expansion is needed.
- [x] Revised M3 closes the SEC-01 design gap without new infrastructure.
- [ ] Prove actual holds, diagnose the wepp2 batch registration discrepancy, and require
  exact expected fleet registrations/version/capability counts. The canonical
  script only checks positive per-host default/batch counts, not full fleet parity.
- [ ] Retain scheduler handoff regression, RQ graph gate, live job trees and actual
  scheduled execution. Correct configuration alone does not prove queue execution.

### 6) Agentic Tooling and MCP Surfaces

- [x] Reviewer authority is source/record inspection and this artifact only;
  production changes remain with the authorized operator.
- [x] No additional agent privilege, public publication or external messaging is
  required. Existing service identity must not be widened to make tests pass.

### 7) Network and External Integrations

- [x] The package adds no external notification delivery channel, fetch endpoint
  or public maintenance endpoint. Existing dashboard 502 remains a baseline issue.
- [ ] Retain normal authentication/CAP/API acceptance through the real proxy;
  successful internal requests alone do not establish production routing.

### 8) CI/CD and Supply Chain

- [x] Host-local builds use the existing canonical script and installed presets;
  registry workflows and bypassing required builds are out of scope.
- [ ] Record actual candidate revision, image IDs, installed distribution delta
  and allowlisted vendor/native artifact digests on every participating image.
  `docker/Dockerfile:25` selects mutable vendor refs and `:148` removes their git
  metadata; one application SHA or the interchange digest alone cannot prove all
  vendor contents match across independently built hosts. Verify tree/file
  manifests or equivalent actual-content evidence before accepting parity.
- [ ] Preserve exact old images with retained tags and verified IDs. Do not
  rebuild an old mutable reference and call that the original rollback image.

### 9) Data Integrity, Locking, and Concurrency

- [x] Migration is additive: two notification tables and indexes; old account
  tables are not rewritten. Operational rollback retains the new tables.
- [x] SEC-02 target guard reviewed; isolated rehearsal execution remains pending.
- [ ] Retain a quiescent pre-2.x recovery checkpoint with all
  producers/schedulers/consumers accounted for. A live backup is useful but is
  not a promise of no-data-loss rollback after later accepted work.
- [ ] Preserve historical catalog ledger/pause/receipts; fresh pilot identity,
  genuine default capabilities, cap seven and ordinary-work deferral are required.
- [ ] General activation requires converged roots/settings across publishers and
  workers, actual complete-cycle evidence and ordinary-arrival measurements.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Recovery policy correctly separates disabling notification scheduling,
  pausing catalog admission and runtime rollback. No live Redis restore or 1.x
  reattachment after 2.x writes is presumed safe.
- [ ] Record stop/recovery ownership and exact failure responses before cutover;
  preserve meaningful partial outcomes instead of erasing histories to get green.
- [ ] Retain storage headroom and monitor queue delay, worker counts, fence
  ownership, publication failures and unresolved scope ages during observation.

## Validation Evidence

- Source inspection: deployment fence acquisition/renewal/resume and error trap;
  runtime build references; additive migration; notification account/CSRF/scope
  boundaries; canonical RQ and query recovery rules.
- Prior evidence inspected: notification final security review and current
  production readiness record. Their scope and dates remain explicit above.
- Reviewer read-only check on wepp1 imported installed RQ1.16.2 and inspected the
  method signature: `(self, start: int = 0, end: int = -1)`. Local RQ2.12.0 includes
  `cleanup=True`. No Redis client/registry was instantiated by this check.
- The initial cleanup-keyword probe passed 38 deployment execution tests and the
  related 72-test gate, but the stub signature masked old-runtime incompatibility.
  Those initial passes did not close SEC-03. The corrected raw-read probe passed
  all 38 execution tests (`/tmp/production-cutover-probe-raw-green.log`, 33.18 s).
- Independent correctness reviewer extracted the exact corrected probe and ran
  it at approximately 05:19 UTC in wepp2's installed RQ1.16.2 and forest's
  installed RQ2.12.0; both returned count 0 and exited successfully without queue
  cleanup. The [correctness follow-up](20261106_correctness_review.md) records
  identities and provenance. This is compatibility evidence, not a later drain
  certificate.
- No production mutation was performed by this reviewer.
- `wctl doc-lint --path <this artifact>` passed: one file, zero errors/warnings.
  The `uk2us` preview produced no spelling changes.

### Concrete-control design response

The operator proposed stopping old weppcloud/rq-engine producers, scheduler and
all old worker pools before the canonical wepp1 invocation, holding remote pools
until their own canonical deployment, and accepting a build-duration application
outage. This is a viable bounded SEC-01 remedy without a firewall or parallel
deployment mechanism, provided the retained service inventory proves all old
producers/consumers and their children are gone. Once wepp1 passes its canonical
checks, ordinary traffic can resume exclusively on 2.x with both features false;
final model/feature acceptance remains a separate claim. A script error may leave
candidate services running but must never restart an old producer/consumer after
2.x writes. Record concrete commands, readbacks and failure disposition in the
active plan; revised M3 now records that control. SEC-03 is needed for the later host's old-image
control helper even when every old worker process has been stopped.

### Migration helper command review

Reviewed `/tmp/production-notification-migrate.py`, SHA256
`1af2a1dce20e6412049f024493a4d04548ee2ec97330e7e68bcd9771cda6e614`.
It requires original database `wepppy` on host `postgres`, selects the explicit
rehearsal database `cutover_rehearsal_20261106`, and rewrites both
`SQLALCHEMY_DATABASE_URI` and `DATABASE_URL` before importing Flask. It then checks
the effective app URI, connected database/server equality, original Alembic head,
notification table absence and existing-table counts before applying only the
named additive revision. Postchecks require preserved counts and empty new tables.
The helper prints only safe identities/counts/revision, not the rendered URI.

Run this reviewed helper with normal, non-optimized Python in the verified wepp1
Compose network. Its assertions are disabled by Python optimization, and its
server equality binds the two connections rather than independently attesting
Docker network identity. Retain that identity separately. Successful rehearsal,
unchanged live revision and protected backup evidence are still required before
production execution; this review does not claim they have occurred.

## Residual Risk

- Historical forest tests are bounded evidence, not complete certification of
  the full production release or every retained job shape.
- Mutable external build references remain existing supply-chain exposure.
  Actual per-host content manifests can detect drift for this rollout without
  inventing a parallel build workflow; future reproducible-build work is separate.
- Baseline dashboard routing and legacy archive mount placement are outside this
  release. Neither may be silently repaired by broadening services or permissions.
- No medium/high risk acceptance is recommended or implied at this stage.

## Sign-off

- **Security reviewer**: `production_cutover_security`, 2026-11-06 UTC; initial
  findings closed at control/source review; final execution review pending.
- **Package owner**: pending concrete-control disposition and execution evidence.

## Artifact Observability Gate (Required)

Authority: [artifact observability](../../../standards/artifact-observability-standard.md)
and [generated artifact validation](../../../standards/generated-artifact-validation-standard.md).

- [x] Catalog, status, receipts, attempt diagnostics, model inputs/outputs and
  authorized reports/downloads are the named acceptance artifacts.
- [ ] Final production evidence must trace actual source → writer → persisted
  artifact → authorized consumer; job success alone cannot satisfy this gate.
- [ ] Preserve project-visible failure/provenance records through ordinary
  browse/download/archive paths and retain scoped cleanup readback.
- [x] No hidden-only project record or new observability exclusion is authorized.
