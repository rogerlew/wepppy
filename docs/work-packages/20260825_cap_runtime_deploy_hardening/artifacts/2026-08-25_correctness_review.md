# Correctness and User-Experience Review - CAP Runtime and Deployment Hardening

## Metadata

- **Package**: `docs/work-packages/20260825_cap_runtime_deploy_hardening/`
- **Reviewer**: Codex correctness reviewer (`cap_correctness_review`)
- **Date**: 2026-08-25
- **Scope reviewed**: Work-package scaffold, CAP image/runtime, production
  Compose mounts, deployment sequencing and health gates, current CAP tests,
  and prior CAPTCHA package evidence
- **Commit/branch context**: `master` at `075910aff8`; package is uncommitted
  pre-implementation scaffolding
- **Canonical contract(s)**:
  `docs/standards/hardening-lifecycle-standard.md` (Lifecycle sections 1, 3,
  and 4), `docs/infrastructure/secrets.md` (Policy and Docker Compose: Secrets
  As Files), `docs/ui-docs/cap-js-captcha-auth.md` (Cap Service and Local Auth
  Pages), and `docker/AGENTS.md` (Deployment Boundary)
- **Related QA/security artifacts**: Independent QA, operations, and security
  reviews are planned but were not present when this review was written.

## User Outcome

- **User goal**: Use every CAP-protected WEPPcloud workflow after a production
  deployment, especially local login and registration, without losing an
  authenticated session or performing browser-data remediation.
- **Success presented to the user as**: The widget becomes interactive after a
  normal page load or reload, challenge/redeem/siteverify succeeds, local and
  OAuth login remain functional, and already authenticated tabs retain access.
- **Failures that may reach the user**: A noninteractive CAPTCHA, challenge or
  redeem HTTP 5xx/502, an unnecessary repeated CAPTCHA, or loss of access from
  a deployment that removed the working CAP container before detecting a bad
  replacement.
- **Partial-state behavior**: Resource preflight failure must leave the working
  service and ledger untouched. A post-start readiness failure must restore the
  recorded known-good service rather than merely return nonzero with production
  still broken. No failure path may instruct users to log out, clear cookies,
  clear site data, or solve an avoidable second challenge.

## Valid-State Matrix

System state is independent of deploy mode. Full wepp1 mode may initialize or
migrate CAP; targeted web, wepp2 worker, and wepp3 fork/archive modes must not
touch CAP state.

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| CAP data volume absent / fresh host | yes | Create only the CAP-scoped volume with ownership `10001:10001`; read the mounted secret; create and persist a redeemable token | No direct mount-boundary evidence yet; the current auxiliary image test uses `CAP_SECRET` and tmpfs instead of the production mounts (`docker/validate-aux-image-contract.sh:72-85`) |
| CAP volume present but empty; ledger absent | yes | Start without destructive fallback, create a valid ledger as `10001:10001`, and pass challenge/redeem/siteverify | Planned by the ExecPlan, not yet evidenced |
| CAP volume populated and already canonical | yes | Migration is a no-op; preserve the ledger; keep an outstanding token valid across restart | Planned by the ExecPlan, not yet evidenced |
| Supported legacy root-owned volume plus deployment-owned mode-0600 secret | yes | Apply the narrow permission migration idempotently, preserve bytes and semantics, and require no browser/session action | Manual containment restored wepp1 (`tracker.md:38-42`); no automated migration evidence yet |
| Secret replaced or rotated onto a new inode | yes | Reestablish and verify the UID-specific read contract before CAP recreation without broadening group/world access | Not included in the current state matrix or acceptance steps |
| Missing/unreadable secret | no | Fail before stopping the working service; name the path and required identity without exposing contents | Planned, not yet evidenced |
| Empty, invalid-JSON, wrong-schema, symlink, directory, FIFO/device, or otherwise unexpected ledger resource | no | Preserve the resource, fail explicitly before CAP starts, and provide bounded operator recovery guidance | The package says "malformed" but does not enumerate or directly test these distinct states |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Fresh or empty CAP volume | expected | CAPTCHA works on first load; no operator or user repair | Fresh and never-used states are valid product states under the hardening standard |
| Supported legacy ownership | expected | Transparent migration; existing auth session and outstanding CAP verification token remain valid | Migration compatibility must not transfer work to users |
| Secret missing/unreadable before deployment | exceptional | Existing production remains available; deploy reports an actionable operator error | A known bad replacement must not remove the working service |
| Ledger malformed or an unexpected resource type | exceptional | Existing state is preserved for recovery; deployment stops before CAP starts | Silent reset would turn detection into data loss |
| Replacement CAP fails real readiness after recreation | exceptional | Known-good CAP is restored within the rehearsed rollback path; deployment fails | Returning nonzero alone does not restore user access |
| Browser has an existing authenticated session | expected | Session remains logged in through forward deploy and rollback; private access continues | The package explicitly prohibits logout and browser-data remediation |

## Review Checks

- [x] Canonical intent is named; implementation and tests are not treated as
  authority for user behavior.
- [ ] Absent, empty, populated, supported legacy, and hostile states are either
  tested or explicitly ruled out by the contract.
- [ ] Input/flag combinations and stored/filesystem state combinations are
  reviewed as separate dimensions.
- [ ] At least one direct, unmocked test exercises each changed safety or
  persistence boundary.
- [x] Mocks do not replace the function or boundary where the production
  failure can occur in the proposed acceptance plan.
- [ ] Security controls prove noninterference with every valid state in
  addition to rejecting hostile states.
- [ ] Partial success, readiness, retry, and cleanup semantics are explicit.
- [ ] Error text and recovery guidance are understandable and actionable.
- [ ] Existing user workflows remain compatible unless an approved contract
  explicitly changes them.
- [x] Claims such as "exhaustive", "complete", or "all combinations" are not
  made without naming covered dimensions.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High | CAP readiness; unwritable or unreadable populated ledger | The proposed public health gate is not a persistence-readiness gate. `GET /cap/health` returns a static success response, while token storage is initialized separately. The pinned `@cap.js/server` 4.0.5 dependency also catches token-file load/write initialization failures and can continue with empty in-memory state. CAP can therefore return health 200 while redeem or siteverify later fails or ignores the ledger. | `services/cap/server.js:58-62`, `services/cap/server.js:99-101`, `services/cap/package-lock.json:14-20`; ExecPlan `Validation and Acceptance` currently relies on public health at lines 175-184 | Define separate liveness and readiness semantics. Before accepting deployment, directly prove the mounted secret is readable, the existing ledger is valid/readable, and the CAP identity can perform a nondestructive persistence write at the real Compose boundary. Add direct tests where health alone would be 200 but ledger access or parsing is broken. | Open |
| COR-02 | High | Failed replacement after the production stack is stopped | The package promises failure before users are exposed, but the current deploy script runs `down`, starts the replacement, and only then checks health. The ExecPlan specifies rollback rehearsal but does not require restoration after every post-start CAP state/readiness failure. A nonzero exit can still leave login broken. | `package.md:14-16`; `scripts/deploy-production.sh:447-471`, `scripts/deploy-production.sh:560-574`, `scripts/deploy-production.sh:577-651`; ExecPlan `Idempotence and Recovery` lines 186-197 covers migration failure but not general post-start failure | Split pre-stop validation from post-start readiness. Record a recoverable known-good CAP image/config before destructive steps and require a bounded, rehearsed restore path for any replacement startup/readiness failure. Acceptance must show the script returns nonzero with known-good CAP serving, not merely with a broken replacement detected. | Open |
| COR-03 | High | CAP secret rotation/replacement | The production repair grants numeric UID `10001` access through host-file metadata, but an ACL is inode-specific. Replacing or atomically rotating `docker/secrets/cap_secret` can discard that access and reproduce the original EACCES. The current planned state matrix covers fresh, unreadable, and rerun states but not a valid secret replacement. | `docker/docker-compose.prod.yml:720-726`, `docker/docker-compose.prod.yml:978-979`; `docker/secrets/README.md:9-11`; ExecPlan lines 104-118 and 165-173 | Treat secret replacement/rotation as a supported valid state. Make the canonical rotation/deploy path reapply and verify the least-privilege access contract before CAP recreation, and directly test a newly replaced mode-0600 secret inode. Preserve the host mode and prove no group/world read access. | Open |
| COR-04 | High | Full-deploy recreated-service acceptance | `configure_deploy_topology` currently selects image build targets, not the complete set recreated by full `down` plus `up -d`. The ExecPlan says validation must consume the set selected by that function, which risks conflating `BUILD_SERVICES` with every started/recreated service and repeating the same incomplete-acceptance class for another service. | `scripts/deploy-production.sh:315-371`, `scripts/deploy-production.sh:433-445`, `scripts/deploy-production.sh:447-471`, `scripts/deploy-production.sh:560-574`; ExecPlan lines 120-127 and 207-214 | Define build targets, explicitly recreated targets, and expected-running services as separate contracts. Account for scaled-zero/profiled services. Add executable deploy-script tests for full wepp1, targeted web, wepp2 worker, and wepp3 topologies that prove only selected services are checked or mutated and every expected replacement is stable. | Open |
| COR-05 | Medium | Populated legacy ledger and in-flight user verification | A before/after checksum plus a new post-migration challenge/redeem does not prove that CAP loaded and honored the preserved ledger. The same evidence can pass if the old bytes remain on disk while CAP falls back to empty memory. | ExecPlan lines 112-118 and 165-173; CAP verification tokens are stored at `services/cap/server.js:60-62` and consumed through `/siteverify` at `services/cap/server.js:154-173` | Mint and redeem a challenge before migration, retain its unconsumed verification token in the root-owned legacy ledger, migrate/restart, and prove siteverify accepts that exact pre-migration token once. Record integrity before consuming it and prove the subsequent ledger mutation is writable. | Open |
| COR-06 | Medium | Malformed populated state and data preservation | "Malformed" is not precise enough for a boundary whose dependency can treat parse/access failure like missing state and initialize `{}`. Zero-byte or invalid-JSON files, wrong JSON shape, symlinks, directories, and special files require distinct disposition; otherwise a malformed populated ledger can be silently reset. | `package.md:38-40`; ExecPlan lines 107-118 and 167-173; `services/cap/server.js:58-62` delegates ledger handling to the pinned dependency | Enumerate valid JSON shape and allowed filesystem types. Require pre-start validation to preserve and fail on malformed populated state, with direct tests for at least empty file, invalid JSON, wrong schema, symlink, directory, and one special-file case. No migration or CAP start may truncate/reinitialize these states. | Open |
| COR-07 | Medium | Durable operator/developer contract | The package says canonical docs will be updated but does not name the authoritative destination, while the current CAP guide still describes `CAP_SECRET` as required and a production `/workdir/cap` asset mount that current production Compose no longer uses. Ambiguous authority helped allow image and runtime contracts to drift. | `docs/ui-docs/cap-js-captcha-auth.md:24-48`; `docker/docker-compose.prod.yml:720-733`; ExecPlan lines 129-132 | Name and update exact durable authorities: CAP runtime/readiness in `docs/ui-docs/cap-js-captcha-auth.md`, secret UID/rotation in `docs/infrastructure/secrets.md` and `docker/secrets/README.md`, and production deploy/rollback in `docker/README.md`. Remove the stale asset-mount statement and make the work package reference those promoted sections. | Open |

## Verdict

- **Gate status**: `fail`
- **Unresolved findings**: Critical 0; High 4; Medium 3; Low 0
- **Release recommendation**: `hold`
- **Reviewer sign-off**: Codex correctness reviewer, 2026-08-25

The current wepp1 containment is independently confirmed healthy, but that does
not constitute durable repair evidence. Disposition COR-01 through COR-04 in
the package, ExecPlan, and tracker before implementation. Close all medium
findings with direct evidence before package closure.
