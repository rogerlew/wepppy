# WEPPcloudR Execution Backend Refactor Tracker

**Status**: In Progress — scaffolded; implementation not started
**Last updated**: 2026-08-21 18:04 UTC
**Active ExecPlan**: [prompts/active/weppcloudr_execution_backend_refactor_execplan.md](prompts/active/weppcloudr_execution_backend_refactor_execplan.md)

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
- [ ] Capture baseline Compose source/rendered mounts and focused test behavior.
- [ ] Refactor shared request validation and the Compose backend.
- [ ] Implement repository-side Kubernetes Job orchestration and one-shot R
  renderer surfaces with deterministic tests.
- [ ] Update RQ graph/catalog, stubs, and operator/developer documentation.
- [ ] Pass focused and broad validation gates.
- [ ] Complete independent correctness, QA, and security reviews.
- [ ] Restart the authorized forest development stack and capture successful
  Docker-exec DEVAL evidence for the designated run.

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

## Risks and Controls

| Risk | Control | State |
|---|---|---|
| Compose render regression | Characterization tests plus authorized forest proof | Open |
| Mount or working-directory drift | Source and rendered-mount snapshots before/after | Open |
| Backend fallback crosses trust boundary | Explicit enum and fail-closed selection tests | Open |
| Stale completion overwrites newer output | Lock/fencing and receipt-state tests | Open |
| Paths escape the run WD through symlinks | Canonical path validation with expected PUP coverage | Open |
| Kubernetes code is mistaken for deployed capability | Separate acceptance language and follow-up package | Controlled |
| Forest has overlapping local changes | Read-only preflight; stop on overlap | Open |

## Validation Ledger

| Gate | Evidence | Status |
|---|---|---|
| Focused pytest | `tests/rq/test_weppcloudr_rq.py`, route coverage | Pending |
| RQ dependency graph | `wctl check-rq-graph` | Pending |
| Stubs/API | targeted stub checks and `wctl check-test-stubs` | Pending |
| Broad pytest | `wctl run-pytest tests --maxfail=1` | Pending |
| Exception policy | changed-file broad-exception enforcement | Pending |
| Documentation | package and affected docs lint | Pending |
| Correctness review | `artifacts/2026-08-21_correctness_review.md` | Pending |
| QA review | `artifacts/2026-08-21_qa_review.md` | Pending |
| Security review | `artifacts/2026-08-21_security_review.md` | Pending |
| Forest Compose integration | job, logs, artifact, backend, and mount evidence | Pending |

## Blockers

None at scaffold time. Live Kubernetes validation is intentionally deferred and
is not a blocker for this package's defined scope.
