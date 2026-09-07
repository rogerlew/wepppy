# Tracker - Batch Climate and RAP NoDb Contention

## Quick Status

**Timezone**: UTC
**Started**: 2026-09-07 05:34 UTC
**Current phase**: Closed — authorized implementation and local validation complete
**Last updated**: 2026-09-07 UTC
**Full repository suite**: 7535 passed, 63 skipped
**Security impact**: `high`; independent review passed
**Live replay/deployment**: excluded by operator; Kubernetes recurrence unmeasured
## Task Board

### Ready / Backlog

No remaining authorized implementation work. Future deployment investigation
should attribute the actual Kubernetes writer and repair copied batch group
identity under its own bounded scope.
### In Progress

None.
### Blocked

- No implementation blocker. Live acceptance is excluded, not waiting for
  permission. Source attribution cannot identify the deployment writer from
  the supplied exception excerpt alone.
### Done

- [x] Pulled WEPPpy master through `3443b07a7` (2026-09-07 05:34 UTC).
- [x] Correlated post-rollout job IDs, runtime logs, and exact stale-write
  signatures (2026-09-07 05:34 UTC).
- [x] Located and linked prior Climate finalization and batch/culvert
  rehydration packages (2026-09-07 05:34 UTC).
- [x] Scaffolded package, tracker, ExecPlan, and review gates
  (2026-09-07 05:34 UTC).

- [x] Attributed source writers; recorded exact synthetic writers and unknown
  Kubernetes attribution (2026-09-07).
- [x] Implemented fresh finalization for observed GridMET/PRISM and RAP; preserved
  strict stale-write checks and generated schemas (2026-09-07).
- [x] Added real-file failure/conflict/containment/commit-outcome tests and real
  raster-to-parquet-to-WEPP-cover propagation (2026-09-07).
- [x] Closed all independent correctness/code/QA/security findings (2026-09-07).
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
| Finalizer loses unrelated durable fields | High | Medium | Fresh hydrate plus explicit derived-field allowlist | Verified |
| Relevant input changes during collection | High | Medium | Snapshot and explicit superseded/conflict outcome | Verified |
| Long locks block run/UI writers | High | Medium | Keep remote and parallel work outside lock | Verified |
| RAP parquet and NoDb diverge on failure | High | Medium | Defined publication/rollback; interrupted commits retain evidence | Mitigated; crash limit documented |
| RQ `Job OK` obscures domain failure | Medium | High | Verified existing metadata/summary/retry semantics | Verified |
| Copied controller retains wrong identity | Medium | Medium | Independent source attribution; separate copied-group defect | Deferred follow-up |

## Hardening Signal Log

- **Baseline reproduction**: two real-file tests failed before the patch with
  equal sizes and mtimes one second apart.
- **Post-change local evidence**: unrelated writes survive; relevant changes
  reject publication; pre/post-commit errors, unknown commit, lock takeover,
  symlinks, empty/legacy/malformed RAP state, and real raster-to-cover output
  are covered. 245 focused tests and 49 expanded contention/facade tests passed.
- **Deployment signal**: unmeasured; the operator prohibited live reruns.
- **Temporary calluses**: no retry/cache-clearing workaround. Recovery copies
  remain only when an interrupted publication cannot safely be rolled back.
## Verification Checklist

- [x] Both pre-fix real-file regressions fail for the intended same-size stale signature.
- [x] Post-fix unrelated/relevant interleavings preserve strict stale detection.
- [x] NoDb boundary/base suites pass.
- [x] Focused Climate/RAP and batch RQ suites pass.
- [x] Real raster summaries propagate through parquet to WEPP cover files.
- [x] Climate/RAP public stubtest and test-stub completeness pass.
- [x] Broad exception enforcement and Vulture pass.
- [x] Correctness, code, QA, and security findings are dispositioned.
- [x] Full repository suite: 7535 passed, 63 skipped; documentation/diff checks pass.
- [x] No live replay/deployment; excluded by operator.
## Handoff

Implementation and validation completed 2026-09-07. The completed ExecPlan
records the operator's no-rerun amendment. See
`artifacts/2026-09-07_validation.md` for 7535 passed / 63 skipped in the full
suite and all other gates, and `artifacts/2026-09-07_writer_attribution.md` for
authority, compatibility, and exact pre-fix evidence.

The durable decision is documented in
`docs/dev-notes/batch-climate-rap-finalization.md`, especially "User and operator
behavior" and "Publication and recovery." No branch, commit, deployment, or
live rerun was performed. Kubernetes attribution/recurrence and copied identity
remain documented follow-ups, not claimed production acceptance.
