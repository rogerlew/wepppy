# Tracker: FORK-READ-01

## Status

2026-09-07 UTC: Local implementation and review complete; production rollout gated. Ancestor: `2ad307aeb`.
Starting revision: `87cfe40473108a93cbbd5733fdc13c99d97707ea`.

## Task Board

- [x] Capture incident and operator burst-of-small-files hypothesis.
- [x] Discover NoDb, fork, deferred retry and serial-queue precedents.
- [x] Two independent contract reviews; standalone contract ancestor `2ad307aeb`.
- [x] Implement bounded reads and diagnostics.
- [x] Implement fork prerequisite failure reporting.
- [x] Validate filesystem/RQ integration, focused/broad suites and graph; broad-suite gap recorded.
- [x] Independent correctness, QA and security reviews: no open findings.
- [x] Complete validation record and documentation handoff.

## Decisions

- 2026-09-07 UTC: ENOENT and ESTALE only; 5-second total read-context budget,
  0.1-second initial exponential delay capped at 1 second. No write/job retries.
- 2026-09-07 UTC: Initial preparation controller reads opt in; ordinary web
  loads retain immediate errors and optional absence retains None semantics.
- 2026-09-07 UTC: Failure callbacks report terminal child failure; they do not
  cancel sibling jobs, release active claims or run blocked model stages.

## Validation and Risks

228 focused tests and the final full suite pass; follow-up results are below. A hard-mounted NFS syscall can block beyond a Python
retry deadline; this package bounds retry scheduling, not kernel I/O duration.

## Handoff

Active plan: [ExecPlan](prompts/active/fork_read_retry_hardening_execplan.md).

## Progress — 2026-09-07 UTC

- Implementation wired after ancestor `2ad307aeb`; 228 focused tests pass.
- Real OS ENOENT recovery and NoDb hydration, real Redis/RQ strict job tree and
  atomic receipt/publication, and real worker subprocess death verified.
- Optional disappearing-file policy and supervisor Redis error isolation fixed
  following independent reviews; all review findings closed.
- Full suite stopped at unrelated unchanged shape-converter Compose assertion:
  5,129 passed, 50 skipped. Baseline revision contains the same contradicting
  service/test assertion. Final full run excludes that single known failure.
- Deployment and recovery of original production jobs remain out of scope.

## Scope Addition — 2026-09-07 UTC

The user explicitly requested resolution of the shape-converter broad-suite
failure. The test-only correction permits the existing shared image/build
service overlay while preserving runtime and environment hardening checks.
Production Compose is unchanged. Shape/rollout validation: 15 passed;
independent QA accepted with no findings. The already-running final broad pass
excludes that test, which passed separately after repair.

## Final Broad Validation

The final run stopped at an unrelated roads authorization/backend test: 6,477
passed, 63 skipped, 1 deselected. The test expected a WBT-backend error but
received the PowerUser restriction first. Both the test and route are unchanged
from the contract checkpoint. The excluded shape-converter test passed in its
separate 15-test run. Full-suite green is not claimed; see the validation artifact.

## Full-Suite Follow-up — 2026-09-07 UTC

The user requested resolution of all test failures. Roads test users now have
the required PowerUser role; the climate same-size rewrite fixture uses a
deterministic atomic payload edit. Affected modules: 48 passed. Final full
suite: 7,489 passed, 63 skipped, 12 subtests passed, no failures or deselections.
This supersedes the broad-suite gap above. No production behavior changed.


## Retry Budget Amendment — 2026-09-07 UTC

Operator-directed correction after production recurrence: supersede the original
5-second/0.1-second-to-1-second policy with a 120-second shared budget and
2-second initial delay doubling to a 10-second cap. Existing production storage
measurements already justified a longer timescale. ADR-0049 and the canonical
NoDb contract carry the amended policy. No broader retry scope or mount changes.
Validation: 93 targeted NoDb/read/preparation tests passed in 17.59 seconds,
including simulated recovery after 60 seconds and permanent-error exhaustion.
Scoped documentation lint and diff checks passed. Production rollout pending.
