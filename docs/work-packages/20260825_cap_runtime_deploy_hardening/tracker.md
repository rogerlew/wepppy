# Tracker – Production Compose Deployment and CAP Runtime Hardening

> Living document tracking the durable repair for the 2026-08-25 partial-build
> production deployment incident.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-25 15:48 UTC
**Current phase**: Forest1 automated gate complete; final manual UX gate
**Last updated**: 2026-08-25 21:38 UTC
**Next milestone**: final-revision browser UX confirmation, then production
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260825_cap_runtime_deploy_hardening/artifacts/2026-08-25_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Add the outstanding-token continuity case to the CAP Docker matrix.
- [ ] Re-confirm final-revision Safari CAPTCHA, local/OAuth login, retained
  session, and multi-tab logout on Forest1.
- [ ] Deploy to wepp1 and begin the 14-day observation window.

### In Progress

- [ ] Complete the operator-controlled browser UX gate.

### Blocked

- Production activation remains held for operator-controlled browser UX
  confirmation and explicit production authorization.

### Done

- [x] Restored production CAP by granting UID `10001` read access to the secret
  and migrating the existing CAP data volume to `10001:10001` (2026-08-25
  15:43 UTC).
- [x] Confirmed public `/cap/health` HTTP 200 and successful cross-browser login
  CAPTCHA after containment (2026-08-25 15:45 UTC).
- [x] Scaffolded durable hardening work package and ExecPlan (2026-08-25 15:48
  UTC).
- [x] Completed independent correctness, operations, QA, and security reviews:
  Critical 0; all High findings accepted as implementation blockers
  (2026-08-25 16:10 UTC).
- [x] Ratified and documented dispositions for every High finding in
  `artifacts/2026-08-25_review_disposition.md` (2026-08-25 16:12 UTC).
- [x] Rebuilt WEPPcloudR on wepp1 and wepp2 without restarting running workers,
  restoring the required renderer entrypoints (2026-08-25 16:38 UTC).
- [x] Captured the combined incident report and expanded this package to cover
  full-mode build/recreate consistency (2026-08-25 16:45 UTC).
- [x] Implemented and directly validated the CAP persistence/migration/canary,
  Compose-derived deployment sets, candidate image identity, and WEPPcloudR
  runtime gates (2026-08-25 17:20 UTC).
- [x] Passed the complete repository suite: 6,706 passed and 63 skipped
  (2026-08-25 17:31 UTC).
- [x] Closed the first expanded-review blockers with a deployment lock,
  quiesced CAP migration, production ACL matrix, bounded rescue state machine,
  RQ cutover fence, stable-service/RQ registration checks, base-first dependent
  builds, protocol marker/request receipt, atomic frontend publication, and
  executable mode/recovery tests (2026-08-25 17:47 UTC).
- [x] Passed renewed correctness, operations, QA, and security code gates with
  Critical 0 and High 0; deployment-mode suite 29 passed (2026-08-25 18:05
  UTC).
- [x] Verified Forest1 ACL support and exact CAP secret ACL; fixed the real
  `wctl` Python/Lua quoting boundary exposed before cutover (2026-08-25 20:40
  UTC).
- [x] Passed two exact no-argument full deployments, targeted CAP/web identity
  isolation, hostile CAP/stale-renderer gates, and automatic CAP rescue on
  Forest1 (2026-08-25 21:20 UTC).
- [x] Completed the real browser CAP gate and RQ-driven DEVAL render; job
  `d872b1f2-cff9-4658-8132-14ebe1bf11a2` finished and published a 12,155,360
  byte report (2026-08-25 21:21 UTC).
- [x] At exact `e11985f02`, stopped the newly recreated targeted CAP candidate;
  deploy returned 1 without success, restored the rescue image and functional
  canary, preserved all non-selected IDs and unsuspended RQ state, then passed
  a clean targeted retry (2026-08-25 21:27 UTC).
- [x] Final correctness, operations, QA, and security reassessment passed with
  Critical 0 and High 0 after the Lua transport repair and exact-revision
  rollback rehearsal (2026-08-25 21:30 UTC).

## Timeline

- **2026-08-25 15:39 UTC** – Confirmed CAP restart loop caused by unreadable
  `/run/secrets/cap_secret`.
- **2026-08-25 15:43 UTC** – Restored secret access and migrated persistent
  ledger ownership; CAP returned healthy.
- **2026-08-25 15:45 UTC** – User confirmed login CAPTCHA works.
- **2026-08-25 15:48 UTC** – Durable repair package opened.
- **2026-08-25 16:10 UTC** – Four independent reviews completed with no
  Critical findings and overlapping High design blockers.
- **2026-08-25 16:12 UTC** – High findings dispositioned into the ratified
  repair design; review gates remain hold pending implementation evidence.
- **2026-08-25 16:18 UTC** – RQ-driven DEVAL render failed because the newly
  deployed worker invoked a file missing from the stale WEPPcloudR image.
- **2026-08-25 16:25 UTC** – Rebuilt only WEPPcloudR on wepp1; renderer
  entrypoints restored without worker interruption.
- **2026-08-25 16:38 UTC** – Rebuilt only WEPPcloudR on wepp2 and verified
  healthy state and renderer script parsing.
- **2026-08-25 16:45 UTC** – Expanded the incident and work package around the
  common full-mode partial-build defect and exact Forest1 release gate.
- **2026-08-25 17:20 UTC** – Targeted tests and unmocked CAP/WEPPcloudR image
  contracts passed; implementation advanced to broad validation and re-review.
- **2026-08-25 17:31 UTC** – Full repository gate completed with 6,706 passed
  and 63 skipped.
- **2026-08-25 17:47 UTC** – Executable deployment harness passed 23 focused
  checks; disposable production CAP and WEPPcloudR positive/stale-negative
  image contracts passed; renewed four-discipline review started.

## Decisions Log

### 2026-08-25 15:48 UTC: Treat containment and durable repair separately

**Context**: Production required immediate recovery, but host-local ACL and
volume ownership changes alone do not protect rebuilt hosts or detect future
regressions.

**Options considered**:

1. Close after operational repair — fast but recurrence remains possible.
2. Revert CAP to root — restores compatibility by discarding least privilege.
3. Preserve non-root CAP and formalize migration plus deployment gates.

**Decision**: Preserve UID/GID `10001:10001` and implement option 3.

**Impact**: The package must validate both secrets and persistent state and
must fail a deployment that recreates a broken CAP service.

### 2026-08-25 15:48 UTC: Preserve the canonical production deployment model

**Context**: `wepp.cloud` uses host-built Docker Compose and the existing deploy
script; registry/Kubernetes mechanisms apply to `openwepp.org` only.

**Decision**: Extend `scripts/deploy-production.sh` narrowly. Do not introduce a
registry, Kubernetes, or a replacement deployment orchestrator.

**Impact**: Forest1 and wepp1 exercise the same Compose contract.

### 2026-08-25 16:12 UTC: Use CAP-only failure-atomic activation

**Context**: Review proved that the original full-deploy design stops unrelated
services, shallow health false-greens, and post-start failure can leave login
broken.

**Decision**: Add `--targeted-cap`. Prevalidate against disposable
production-style resources, preserve a host-local rescue image, stop/migrate/
recreate only CAP, require readiness plus a functional canary, and
automatically restore known-good CAP after failure.

**Impact**: Workers, WEPPcloud, rq-engine, Caddy, Redis, and browser/session
state remain untouched. A measured bounded login-only gap is allowed because
CAP is not redundant.

### 2026-08-25 16:12 UTC: Ratify least-privilege migration boundaries

**Context**: Free-form root helpers, recursive ownership changes, inode-local
ACL assumptions, and upstream token-store fallback can corrupt data or disclose
secrets.

**Decision**: Use only a fixed named-volume, networkless, no-free-form-input
migration helper; validate allowed filesystem entries/schema before mutation;
and make atomic secret rotation apply named-UID ACLs for every effective
allowlisted consumer. Reject inline secret/file ambiguity.

**Impact**: Malformed state fails without truncation, and secret replacement is
a supported regression state rather than an operator footnote.

### 2026-08-25 16:45 UTC: Make full deployment internally consistent

**Context**: Plain full mode rebuilt a curated subset and then recreated the
entire Compose topology. CAP exposed an unhandled runtime migration, while
WEPPcloudR restarted from an April image incompatible with the new worker.

**Decision**: Derive full-mode build targets from enabled locally buildable
services, validate every recreated service, and gate worker/renderer protocol
compatibility. Forest1 must run the exact no-argument command twice and complete
a real RQ-driven DEVAL render before production.

**Impact**: Targeted-mode rehearsal cannot substitute for full-mode evidence.
The expanded scope requires renewed correctness, operations, QA, and security
review; existing reviews continue to govern the CAP sub-scope.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Secret becomes too broadly readable | Critical | Low | least-privilege named-UID ACLs for verified consumers; assert no group/other read | Mitigation ratified |
| Legacy token ledger is lost or reset | High | Medium | populated-volume fixture, checksum receipt, idempotent migration, rollback | Mitigated locally |
| Deploy reports success while an auxiliary service loops | High | Medium | persistence readiness, functional canary, exact recreated-service validation, automatic restore | Mitigation ratified |
| Migration requires browser/session remediation | High | Low | preserve CAP ledger and authentication/session stores; explicit UX smoke | Open |
| Health gate checks an untouched service in targeted mode | Medium | Medium | derive gates from the selected/recreated service set | Open |
| Full mode recreates a stale locally buildable image | Critical | Medium | derive build set from effective Compose; assert candidate image identities | Mitigated locally |
| Worker and renderer protocol revisions diverge | High | Medium | version marker, request/receipt fixture, stale negative, and RQ-driven DEVAL canary | Forest evidence pending |
| Rehearsal exercises a different deploy mode | High | Medium | run exact no-argument full command twice on Forest1 | Open |

## Hardening Signal Log

- **Baseline health signals**: CAP restart-looped; `/cap/health` returned 502;
  two EACCES signatures; CAPTCHA unusable in Safari and Chrome.
- **Post-containment health signals**: CAP running as `10001:10001`, secret
  readable, ledger writable, `/cap/health` 200, user login succeeded.
- **Danger signals observed**: full deploy health check covered WEPPcloud but
  omitted recreated CAP and WEPPcloudR; forest targeted-web rehearsal never
  exercised the full path; DEVAL failed with a missing renderer entrypoint.
- **Post-containment renderer signals**: WEPPcloudR rebuilt on wepp1 and wepp2;
  required scripts exist and parse while workers remained running.
- **Temporary callus register**: none.
- **Softening experiments**: not eligible until the 14-day observation window
  and review gates complete.

## Verification Checklist

### Code Quality

- [ ] Targeted tests pass.
- [ ] `wctl run-pytest tests --maxfail=1` passes or a confirmed unrelated
  blocker is recorded.
- [ ] Changed-shell validation passes.
- [ ] Broad-exception enforcement remains clean for changed production code.

### Security

- [x] Security impact triage recorded as `high`.
- [ ] Dedicated security review is complete.
- [ ] No unresolved medium/high security findings remain before closure.
- [ ] Secret access remains least privilege and secret contents never enter
  logs, argv, repository files, or artifacts.

### Documentation

- [x] Canonical runtime/operator docs updated.
- [x] Work package and tracker remain current.
- [x] Changed documentation passes `wctl doc-lint`.

### Testing

- [x] Fresh/absent CAP state tested.
- [x] Empty CAP state tested.
- [x] Populated supported legacy state tested without data loss.
- [x] Malformed/hostile permission state fails explicitly.
- [x] Direct unmocked Compose boundary exercised (Forest1 gate).
- [x] Full-mode build targets cover every enabled locally buildable service it
  recreates.
- [x] A deliberately stale renderer image fails before deploy success.
- [x] WEPPcloudR entrypoints parse and the worker/renderer protocol fixture
  passes.

### Deployment

- [x] Forest1 baseline inventory captured before deployment.
- [x] Exact no-argument full deployment passes twice on Forest1.
- [ ] Forest1 local login, OAuth, retained-session, Safari/Chrome CAPTCHA, and
  multi-tab logout checks pass.
- [x] A real RQ-driven DEVAL job publishes output and its render receipt.
- [x] Forest1 stale-renderer and CAP failure injections fail closed and recover.
- [x] Targeted modes preserve every non-selected container identity.
- [x] Forest1 rollback and independent disposable-resource cleanup pass.
- [ ] Full deploy that recreates CAP applies the same preflight/rescue contract,
  fails when CAP readiness is deliberately broken, and restores and revalidates
  known-good CAP before returning nonzero.
- [x] Targeted web deploy does not unnecessarily touch CAP.
- [ ] wepp1 rollout preserves login/session UX and begins observation window.

## Progress Notes

### 2026-08-25 15:48 UTC: Incident containment and package creation

**Agent/Contributor**: Codex and production operator

**Work completed**:

- Diagnosed runtime secret and volume ownership mismatch.
- Restored production without changing browser/session state.
- Captured the durable repair scope, risks, validation matrix, and review gates.

**Blockers encountered**: none.

**Next steps**:

- Complete independent reviews and disposition critical/high findings.
- Update the ExecPlan before implementation when findings alter scope.

**Test results**: public CAP health 200; user confirmed CAPTCHA login works in
the previously failing production environment.

### 2026-08-25 16:12 UTC: Independent review and disposition

**Agent/Contributor**: independent correctness, operations, QA, and security
reviewers; Codex disposition owner

**Work completed**:

- Four review artifacts created with direct implementation and Docker-boundary
  evidence.
- No Critical findings; nineteen overlapping High findings mapped into the
  ratified repair design.
- Added CAP-only activation, persistence readiness, secret rotation, fixed-
  scope migration, rescue-image, executable-test, and honest availability
  requirements.

**Blockers encountered**: review gates intentionally remain `fail/hold` until
implementation and re-review evidence exists.

**Next steps**: write failing production-mount and deploy-mode tests, then
implement the ratified design.

**Test results**: all review artifacts and package documents pass doc lint.

### 2026-08-25 16:45 UTC: Expand scope after renderer failure

**Agent/Contributor**: Codex and production operator

**Work completed**:

- Connected CAP and WEPPcloudR failures to the same full-mode partial-build and
  incomplete-acceptance defect.
- Captured the production incident report with evidence and containment.
- Amended the ExecPlan with build/recreate parity, renderer compatibility, and
  exact Forest1 integrated-test requirements.

**Blockers encountered**: the existing independent reviews cover CAP only; the
expanded deployment and renderer implementation must be re-reviewed.

**Next steps**: write the failing deploy-set and stale-renderer tests, implement
the shared contracts, then execute the exact Forest1 matrix.

**Test results**: incident report, all eight package Markdown files, and
`PROJECT_TRACKER.md` pass `wctl doc-lint`; `git diff --check` passes.

## Watch List

- **CAP EACCES recurrence**: query both confirmed signatures during observation.
- **CAP restart count**: any nonzero increase after rollout is a rollback/review
  trigger.
- **Login UX**: no workflow may require logout, cookie clearing, or site-data
  clearing as part of this repair.
- **Renderer contract**: alert on missing `render-compose-request.R`, render
  protocol failures, and DEVAL publication failures.
- **Deploy consistency**: record effective build/recreate sets and candidate
  image identity; any locally buildable stale image is a release blocker.
