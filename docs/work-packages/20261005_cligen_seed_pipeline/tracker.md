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
- [x] (2026-10-05 19:01 UTC) Completed two independent read-only contract
  reviews and dispositioned all design findings.
- [x] (2026-10-05 19:43 UTC) Obtained exact operator approval after both
  reviewers confirmed the corrected contract.
- [ ] Commit the required standalone contract checkpoint.
- [ ] Implement UI and NoDb persistence behavior.
- [ ] Wire explicit seeds through all applicable CLIGEN call sites.
- [ ] Add focused frontend, route, NoDb, snapshot, and process-command tests.
- [ ] Run actual-project `canine-liar` generated-output validation.
- [ ] Run broad gates, close reviews, and archive the plan.

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

## Risks

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Blank option changes historical output | High | Explicit absent/empty/default regression cases | Open |
| One nested worker drops the seed | High | Adapter matrix and argv assertions | Open |
| Concurrent seed edit publishes stale observed climate | High | Include override in the observed immutable build snapshot and reject stale finalization | Open |
| Actual-project validation damages unrelated state | Medium | Mutate only a verified normalized `fork_rq` destination; compare exact source manifests | Open |
| UI suggests publisher/security semantics | Low | Label strictly as random seed/reproducibility | Open |

## Verification Checklist

- [ ] Canonical contract and checkpoint ancestry.
- [ ] Pure template render and Jest payload serialization.
- [ ] NoDb parse/reload and transactional rejection.
- [ ] rq-engine payload/meta replay coverage.
- [ ] Vanilla, modified, observed, future, interpolated, and dormant
      single-storm-helper argv.
- [ ] Multiple-build seed supersession.
- [ ] Real vendored-binary deterministic comparison.
- [ ] `canine-liar` source manifest and normalized-fork artifact evidence.
- [ ] Focused and full Python suites.
- [ ] Frontend lint and full Jest suite.
- [ ] Test stubs/isolation, docs lint, and `git diff --check`.
- [ ] Correctness review with no unresolved High/Medium findings.

## Blocked

Independent review and exact operator approval are complete. Implementation is
gated only on the standalone checkpoint commit.
