# CLIGEN Seed UI-to-Execution Pipeline Tracker

Timezone: UTC. Started: 2026-10-05 18:40 UTC.

Current phase: complete and locally validated.

## Progress

- [x] (2026-10-05 18:40 UTC) Traced the advanced climate form, rq-engine input
  route, NoDb parser, build snapshots, and CLIGEN adapter families.
- [x] (2026-10-05 18:40 UTC) Recorded the additive compatibility and project
  mutation plan before implementation.
- [x] (2026-10-05 18:40 UTC) Scaffolded package, tracker, contract decision,
  correctness gate, canonical contract, and active ExecPlan.
- [x] (2026-10-05 19:01 UTC) Completed two independent read-only contract
  reviews and dispositioned all design findings.
- [x] (2026-10-05 19:43 UTC) Obtained exact operator approval after both
  reviewers confirmed the corrected contract.
- [x] (2026-10-05 19:47 UTC) Committed the required standalone contract
  checkpoint as `514a7da28`.
- [x] (2026-10-05 20:00 UTC) Implemented UI and NoDb persistence behavior.
- [x] (2026-10-05 20:00 UTC) Wired explicit seeds through all applicable CLIGEN
  call sites and retained path-specific automatic defaults.
- [x] (2026-10-05 20:01 UTC) Added focused frontend, route, NoDb, snapshot, and
  process-command tests; 464 focused Python tests passed.
- [x] (2026-10-05 20:10 UTC) Completed actual-project `canine-liar`
  generated-output validation through the authenticated fork and build queues.
- [x] (2026-10-05 22:21 UTC) Completed broad gates: 10,317 Python tests passed,
  126 skipped; 923 Jest tests passed across 113 suites; frontend lint, stubs,
  focused test isolation, docs lint, usersum validation, RQ graph validation,
  and patch hygiene passed. Closed the package and archived the plan.

## Decisions

- **2026-10-05 19:01 UTC** - Use `cligen_seed` as the request/form name and
  `_cligen_seed_override` as additive explicit configuration; preserve existing
  `_cligen_seed` as generated runtime state.
- **2026-10-05 18:40 UTC** - Accept integers from `0` through `99999`; reject
  booleans, fractions, non-numeric text, and values outside WEPPpy's
  five-digit application-policy range.
- **2026-10-05 18:40 UTC** - Omitted payload keys preserve stored state. A
  present empty value requests automatic/default behavior (`None`).
- **2026-10-05 18:40 UTC** - Explicit seeds must reach every applicable native
  command; `None` preserves each path's current automatic/default behavior.
- **2026-10-05 19:01 UTC** - Validate only on a complete disposable fork made
  through `fork_rq` from `canine-liar`, and require exact source-project
  before/after manifests.
- **2026-10-05 19:43 UTC** - Omit Omni scenario and contrast data from the
  disposable test fork with `skip_omni_scenarios_contrasts=True`.
- **2026-10-05 19:43 UTC** - Operator approved the exact corrected matrix.
- **2026-10-05 20:10 UTC** - Treat `redisprep.dump` and `rq.log` updates as the
  supported fork route's expected source bookkeeping boundary. A control fork
  proved the aggregate hash of every other source file was unchanged.

## Risks

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Blank option changes historical output | High | Explicit absent/empty/default regression cases | Closed |
| One nested worker drops the seed | High | Adapter matrix and argv assertions | Closed |
| Concurrent seed edit publishes stale observed climate | High | Include override in the observed immutable build snapshot and reject stale finalization | Closed |
| Actual-project validation damages unrelated state | Medium | Mutate only verified normalized `fork_rq` destinations; compare source model-content manifests | Closed |
| UI suggests publisher/security semantics | Low | Label strictly as random seed/reproducibility | Closed |

## Verification Checklist

- [x] Canonical contract and checkpoint ancestry.
- [x] Pure template render and Jest payload serialization.
- [x] NoDb parse/reload and transactional rejection.
- [x] rq-engine payload/meta replay coverage.
- [x] Vanilla, modified, observed, future, interpolated, and dormant
      single-storm-helper argv.
- [x] Multiple-build seed supersession.
- [x] Real vendored-binary deterministic comparison.
- [x] `canine-liar` source manifest and normalized-fork artifact evidence.
- [x] Focused and full Python suites (464 focused; 10,317 full-suite tests
      passed, 126 skipped).
- [x] Frontend lint and full Jest suite (113 suites, 923 tests).
- [x] Test stubs/isolation, docs lint, usersum validation, and
      `git diff --check`.
- [x] Correctness review with no unresolved High/Medium findings.

## Blocked

None.
