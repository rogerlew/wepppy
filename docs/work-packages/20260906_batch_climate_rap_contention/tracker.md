# Tracker - Batch Climate and RAP NoDb Contention

## Quick Status

**Timezone**: UTC
**Started**: 2026-09-07 05:34 UTC
**Current phase**: Scaffold complete; ready for forest dispatch
**Last updated**: 2026-09-07 05:34 UTC
**Next milestone**: Reproduce and attribute Climate and RAP_TS writes
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/2026-09-07_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Capture sanitized source logs and a current queue/run-state snapshot.
- [ ] Add deterministic real-file Climate and RAP_TS contention regressions.
- [ ] Inventory all persistence, cache, lock, and timestamp writes in both paths.
- [ ] Decide whether current canonical contracts already authorize the fix.
- [ ] Implement explicit collection and fresh-state finalization per controller.
- [ ] Verify batch metadata, retry selection, summary, and triggers on failure.
- [ ] Run focused, persistence, stub, quality, and full-suite validation.
- [ ] Complete independent correctness, code, QA, and security reviews.
- [ ] Run the operator-authorized forest replay and record before/after signals.

### In Progress

- None. This package is intentionally scaffold-only and ready for dispatch.

### Blocked

- None. Any RQ completion/trigger behavior change is gated on a standalone
  canonical contract checkpoint and must pause at that boundary if needed.

### Done

- [x] Pulled WEPPpy master through `3443b07a7` (2026-09-07 05:34 UTC).
- [x] Correlated post-rollout job IDs, runtime logs, and exact stale-write
  signatures (2026-09-07 05:34 UTC).
- [x] Located and linked prior Climate finalization and batch/culvert
  rehydration packages (2026-09-07 05:34 UTC).
- [x] Scaffolded package, tracker, ExecPlan, and review gates
  (2026-09-07 05:34 UTC).

## Timeline

- **2026-09-07 03:49 UTC** - openWEPP began promotion of WEPPpy `87cfe4047`.
- **2026-09-07 04:31-04:47 UTC** - new batch jobs emitted Climate and RAP_TS
  same-size `NoDbStaleWriteError` failures.
- **2026-09-07 05:34 UTC** - recurrence package scaffolded from production
  evidence.

## Decisions Log

### 2026-09-07 05:34 UTC: Treat this as nested persistence contention

**Context**: The deployed outer cache clear and rehydrate occurs immediately
before `Climate.build()`, yet the same controller file changes during the
long-running operation. RAP_TS shows the same signature outside that patch.

**Decision**: Attribute internal writers and use controller-specific
collect-then-finalize ownership. Preserve strict stale rejection and prohibit
blind stale-object retries or generic merging.

**Impact**: Tests must exercise real NoDb signatures and interleavings rather
than mock away `dump()`.

### 2026-09-07 05:34 UTC: Separate persistence correctness from RQ semantics

**Context**: `run_batch_watershed_rq()` catches domain exceptions, publishes
`EXCEPTION_JSON`, returns `(False, elapsed)`, and therefore appears as `Job OK`
to RQ. Its completion trigger is emitted on both paths.

**Decision**: Require consistent failure metadata and operator evidence in this
package, but do not change established RQ result/trigger semantics without the
required contract-decision checkpoint.

**Impact**: The executor must document whether this is conformance or a behavior
change before editing the boundary.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Finalizer loses unrelated durable fields | High | Medium | Fresh hydrate plus explicit derived-field allowlist | Open |
| Relevant input changes during collection | High | Medium | Snapshot and explicit superseded/conflict outcome | Open |
| Long locks block run/UI writers | High | Medium | Keep remote and parallel work outside lock | Open |
| RAP parquet and NoDb diverge on failure | High | Medium | Define publication order and direct partial-failure tests | Open |
| RQ `Job OK` obscures domain failure | Medium | High | Verify metadata/summary/retry semantics; contract-gate changes | Open |
| Copied controller retains wrong identity | Medium | Medium | Trace runid, wd, logger, cache key, and lock key independently | Open |

## Hardening Signal Log

- **Baseline**: at least twelve Climate/RAP_TS stale-write messages in one
  openWEPP batch excerpt after the cache-boundary rollout.
- **Post-change**: not yet measured.
- **Danger signals observed**: whole-controller mutation bases span expensive
  threaded work; domain failures are reported as successful RQ execution.
- **Temporary callus register**: none.

## Verification Checklist

- [ ] Exact pre-fix regressions fail for the intended reason.
- [ ] Exact post-fix regressions pass without weakening stale detection.
- [ ] `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1`
- [ ] Focused Climate, RAP_TS, BatchRunner, and batch RQ suites pass.
- [ ] `wctl run-pytest tests --maxfail=1`
- [ ] Stub and broad-exception gates pass where applicable.
- [ ] `wctl doc-lint` passes for touched documentation.
- [ ] `git diff --check` passes.
- [ ] Correctness, code, QA, and security findings are dispositioned.
- [ ] Forest replay produces zero new target signatures.

## Handoff

Execute `prompts/active/batch_climate_rap_contention_execplan.md` from the
repository root. Begin with writer attribution and failing tests. Do not begin
with a generic retry, cache clear, or lock-duration increase.
