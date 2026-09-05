# Batch and Culvert Climate Rehydration Hardening Tracker

> Living operator/agent handoff for
> `docs/work-packages/20260904_batch_culvert_climate_rehydration_b/`.

**Status**: Backlog - ready for Forest dispatch

**Owner**: Unassigned Forest executor

**Started**: 2026-09-05 00:29 UTC

**Security artifact**: `artifacts/2026-09-05_security_review.md` (required,
pending)

## Backlog

- [ ] Capture a compact Forest pre-change reproduction or equivalent direct
  filesystem interleaving test without modifying production run data.
- [ ] Add failing batch-runner and culvert-runner regressions for late Climate
  hydration, exact cache scope, and lock ordering.
- [ ] Implement the minimal batch and culvert changes.
- [ ] Verify downstream climate consumers use current post-build state.
- [ ] Update affected canonical and subsystem documentation.
- [ ] Run focused and full validation gates.
- [ ] Complete independent correctness, QA, and security reviews and resolve
  every medium/high finding.
- [ ] Deploy the reviewed commit to Forest under the existing deployment
  procedure and capture representative batch and culvert evidence.
- [ ] Close the package, archive the ExecPlan, and synchronize this tracker and
  `PROJECT_TRACKER.md`.

## In Progress

- None.

## Blocked

- None. Production deployment remains out of scope and requires separate
  operator authorization.

## Done

- [x] Captured the openWEPP batch failure signature, job IDs, timing, and
  populated-state classification (2026-09-05 00:29 UTC).
- [x] Confirmed the batch RQ registry had no duplicate `OR-10` job in the
  affected batch (2026-09-05 00:29 UTC).
- [x] Identified the existing `project_rq::build_climate_rq` exact-scope,
  hydrate-inside-lock implementation precedent (2026-09-05 00:29 UTC).
- [x] Scaffolded the package, active ExecPlan, lifecycle signals, review gates,
  Forest boundary, and rollback shape (2026-09-05 00:29 UTC).

## Decisions

- **2026-09-05 00:29 UTC - Treat the NoDb rejection as a safety signal, not the
  defect.** The stale-write guard prevented a lost update. The defect is the
  orchestration retaining a mutable Climate controller across unrelated,
  long-running stages.
- **2026-09-05 00:29 UTC - Use the established project RQ pattern in both
  runners.** Exact cache invalidation and hydration belong inside the accepted
  climate root-lock callback immediately before mutable work.
- **2026-09-05 00:29 UTC - Keep downstream controller freshness explicit.** An
  executor must not fix the build call while leaving RAP/OpenET or WEPP
  interchange on an early stale object.
- **2026-09-05 00:29 UTC - Require high-impact review.** RQ worker persistence
  and lock/cache ordering trigger correctness, QA, and security gates even
  though no public or credential surface changes.
- **2026-09-05 00:29 UTC - Limit live rollout to Forest.** Production repair,
  historical run mutation, and deployment are separate authorization
  boundaries.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Fresh build is followed by downstream use of an early Climate object | High | Medium | Assert controller identity/state ordering in both runner tests | Open |
| Cache clear occurs before root/archive rejection | High | Low | Place guard inside existing root-lock callback and test rejection ordering | Open |
| Retry masks a true concurrent writer | High | Low | Do not add stale-write catch/retry around `build()`; retain lock and guard | Open |
| Scientific artifacts change | High | Low | Preserve inputs/build API and compare representative outputs | Open |
| Culvert fixtures omit realistic long-stage mutation | Medium | Medium | Add direct same-size file-generation advance at persistence boundary | Open |
| Stale serialized runid labels obscure evidence | Medium | Medium | Record as separate follow-up unless persistence identity impact is proven | Open |

## Hardening Signal Log

- **Baseline**: openWEPP leaf `OR-10` retained Climate generation
  `(1788567519.6239834, 1864)` and later observed
  `(1788567558.374864, 1864)`, then returned `(False, approximately 150.5s)`.
- **Current health evidence**: `project_rq::build_climate_rq` already clears
  `climate.nodb` and hydrates inside its climate root-lock callback.
- **Post-change evidence**: pending focused tests and Forest execution.
- **Recurrence trigger**: any batch or culvert leaf reporting
  `NoDbStaleWriteError` for `climate.nodb` after deployment opens a new
  incident package and compares controller-hydration ordering and writer
  attribution with this baseline.

## Verification Checklist

- [ ] `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1`
- [ ] Focused culvert RQ test module(s) pass.
- [ ] Direct, unmocked same-size generation-advance regression passes for each
  changed orchestration boundary.
- [ ] `wctl run-pytest tests --maxfail=1`
- [ ] `wctl check-rq-graph` if inspection finds any queue/dependency edit;
  otherwise record `not applicable` with diff evidence.
- [ ] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- [ ] `python3 tools/code_quality_observability.py --base-ref origin/master`
- [ ] `wctl doc-lint --path docs/work-packages/20260904_batch_culvert_climate_rehydration_b --path PROJECT_TRACKER.md`
- [ ] `git diff --check`
- [ ] Correctness, QA, and security review artifacts pass.
- [ ] Forest batch and culvert evidence plus rollback details are recorded.

## Notes - 2026-09-05 00:29 UTC

- The package was scaffolded from live canary evidence and repository
  precedent; no production implementation or live mutation was performed.
- The executing agent should begin by verifying current `master`, because the
  implementation may have moved after this scaffold commit.
- Test design must distinguish controller-cache staleness from legitimate
  malformed or missing Climate state. Do not make invalid state silently
  buildable.
- Next step: dispatch the active ExecPlan on Forest and move the relevant
  tracker items to In Progress before code edits.
