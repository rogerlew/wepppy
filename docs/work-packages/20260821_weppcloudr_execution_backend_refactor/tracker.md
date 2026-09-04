# WEPPcloudR Execution Backend Refactor Tracker

**Status**: Complete — production-permission remediation and forest Compose proof passed
**Last updated**: 2026-09-04 05:50 UTC
**Completed ExecPlan**: [prompts/completed/weppcloudr_execution_backend_refactor_execplan.md](prompts/completed/weppcloudr_execution_backend_refactor_execplan.md)

## Scope Guardrails

- Preserve the Docker Compose `docker exec` path and every current mount.
- Implement repository-side execution backends and deterministic Kubernetes
  orchestration tests.
- Do not build, publish, or deploy Kubernetes containers or manifests.
- Forest authority is limited to the development Compose stack and the
  designated `branching-hubbub/disturbed9002_wbt` DEVAL report.

## Progress

- [x] Canonical execution contract ratified.
- [x] Work package and active ExecPlan scaffolded.
- [x] Capture baseline Compose source/rendered mounts and focused test behavior.
- [x] Refactor shared request validation and the Compose backend.
- [x] Implement repository-side Kubernetes Job orchestration and one-shot R
  renderer surfaces with deterministic tests.
- [x] Update RQ graph/catalog, stubs, and operator/developer documentation.
- [x] Pass focused/package validation gates and run the broad suite through the
  documented unrelated baseline stops.
- [x] Complete independent correctness, QA, and security reviews.
- [x] Restart the authorized forest development stack and capture successful
  Docker-exec DEVAL evidence for the designated run.
- [x] Remediate the production-discovered cross-container GID/umask contract,
  preserve image-vendored assets under the forest source bind mount, and pass
  the requested `incommensurate-stickball` DEVAL canary.

## Decisions

- Compose retains Docker exec and its existing service/mount topology.
- The Kubernetes implementation is wrapped by the existing RQ task; Kubernetes
  image construction and deployment are separate work.
- The canonical run WD (`run_root`) is the Kubernetes project mount and process
  working directory; `active_root` may resolve through PUP symlinks to its
  parent.
- A 20-minute post-collection Job TTL is the planning default within the
  operator-approved 10–20 minute range. This package may implement/configure
  the field but does not deploy it.
- Implementation fidelity is a faithful extraction of current Compose behavior,
  not a redesign of report semantics.
- Compose filesystem compatibility is accepted only with effective identity,
  group, mount, and umask evidence plus an end-to-end user-facing render.

## Risks and Controls

| Risk | Control | State |
|---|---|---|
| Compose render regression | Characterization tests plus authorized forest proof | Controlled |
| Mount or working-directory drift | Source and rendered-mount snapshots before/after | Controlled |
| Backend fallback crosses trust boundary | Explicit enum and fail-closed selection tests | Controlled |
| Stale completion overwrites newer output | Lock/fencing and receipt-state tests | Controlled |
| Paths escape the run WD through symlinks | Canonical path validation with expected PUP coverage | Controlled |
| Kubernetes code is mistaken for deployed capability | Separate acceptance language and follow-up package | Controlled |
| Forest has overlapping local changes | Read-only preflight; no deployment-file overlap found | Controlled |

## Validation Ledger

| Gate | Evidence | Status |
|---|---|---|
| Focused pytest | 139 focused tests | Pass |
| RQ dependency graph | `wctl check-rq-graph` | Pass |
| Stubs/API | three stubtests and `wctl check-test-stubs` | Pass |
| Broad pytest | Package tests passed; rerun reached 4,593 passed / 61 skipped before unrelated Topanga cwd failure; canonical run stops earlier at nested-Compose canary | Baseline-limited |
| Exception policy | changed-file broad-exception enforcement | Pass |
| Documentation | package and affected docs lint | Pass |
| Correctness review | `artifacts/2026-08-21_correctness_review.md` | Pass |
| QA review | `artifacts/2026-08-21_qa_review.md` | Pass |
| Security review | `artifacts/2026-08-21_security_review.md` | Pass |
| Forest Compose integration | `artifacts/2026-08-21_forest_compose_integration.md` | Pass |
| 2026-09-04 incident remediation | 53 focused tests; canary job `7dd75911-a26c-4690-97e9-32123561802d`; authenticated report HTTP 200 | Pass |

## Deferred Deployment Boundary

Live Kubernetes validation and deployment adapters are intentionally deferred
and were not blockers for this package's defined repository scope.
`kubernetes-job` remains disabled until that separate package completes.
