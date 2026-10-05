# CLIGEN Seed UI-to-Execution Pipeline Tracker

Timezone: UTC. Started: 2026-10-05 18:40 UTC.

Current phase: contract checkpoint preparation. Implementation has not begun.

## Progress

- [x] (2026-10-05 18:40 UTC) Traced the advanced climate form, rq-engine input
  route, NoDb parser, build snapshots, and CLIGEN adapter families.
- [x] (2026-10-05 18:40 UTC) Recorded the additive compatibility and project
  mutation plan before implementation.
- [x] (2026-10-05 18:40 UTC) Scaffolded package, tracker, contract decision,
  correctness gate, canonical contract, and active ExecPlan.
- [ ] Complete and commit the required contract checkpoint.
- [ ] Implement UI and NoDb persistence behavior.
- [ ] Wire explicit seeds through all applicable CLIGEN call sites.
- [ ] Add focused frontend, route, NoDb, snapshot, and process-command tests.
- [ ] Run actual-project `canine-liar` generated-output validation.
- [ ] Run broad gates, close reviews, and archive the plan.

## Decisions

- **2026-10-05 18:40 UTC** - Use `cligen_seed` as the request/form name and
  `_cligen_seed` as the existing persisted NoDb attribute.
- **2026-10-05 18:40 UTC** - Accept integers from `0` through `99999`; reject
  booleans, fractions, non-numeric text, and values outside the native
  five-digit range.
- **2026-10-05 18:40 UTC** - Omitted payload keys preserve stored state. A
  present empty value requests automatic/default behavior (`None`).
- **2026-10-05 18:40 UTC** - Explicit seeds must reach every applicable native
  command; `None` preserves each path's current automatic/default behavior.
- **2026-10-05 18:40 UTC** - Use `canine-liar` only within a recorded
  snapshot/restore validation procedure so unrelated project state is not lost.

## Risks

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Blank option changes historical output | High | Explicit absent/empty/default regression cases | Open |
| One nested worker drops the seed | High | Adapter matrix and argv assertions | Open |
| Concurrent seed edit publishes stale climate | High | Include seed in immutable build snapshot | Open |
| Actual-project validation damages unrelated state | Medium | Byte backup, bounded mutation, restore verification | Open |
| UI suggests publisher/security semantics | Low | Label strictly as random seed/reproducibility | Open |

## Verification Checklist

- [ ] Canonical contract and checkpoint ancestry.
- [ ] Pure template render and Jest payload serialization.
- [ ] NoDb parse/reload and transactional rejection.
- [ ] rq-engine payload/meta replay coverage.
- [ ] Vanilla, modified, observed, future, interpolated, and single-storm argv.
- [ ] Multiple-build seed supersession.
- [ ] Real vendored-binary deterministic comparison.
- [ ] `canine-liar` state backup/restore and artifact evidence.
- [ ] Focused and full Python suites.
- [ ] Frontend lint and full Jest suite.
- [ ] Test stubs/isolation, docs lint, and `git diff --check`.
- [ ] Correctness review with no unresolved High/Medium findings.

## Blocked

Implementation is gated on the repository-required independent contract reviews
and standalone checkpoint commit.
