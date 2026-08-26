# Fork Skip Omni Scenarios/Contrasts and Reset

**Status**: Closed 2026-08-06
**Timezone**: UTC
**Package ID**: SURF-04B

## Overview

Add an opt-in fork-console option labeled **Skip Omni Scenarios/Contrasts and
reset controllers**. When selected, the fork must not copy Omni child projects
from `_pups/omni/scenarios` or `_pups/omni/contrasts`, and the destination must
contain a freshly reset Omni controller and empty Omni artifact directories
rather than copied state that points at missing child projects.

This is an intended UI, API, RQ, NoDb, and run-tree behavior change. The
contract-first checkpoint and its two independent reviews must be committed as
a standalone ancestor before implementation files are edited.

## Objectives

- Add one boolean fork option, `skip_omni_scenarios_contrasts`, defaulting to
  `false`, through template, controller, rq-engine schema/route, and worker.
- Exclude both Omni child-project collections when the option is `true`.
- Reset only the destination Omni controller, its cache/lock state, and Omni
  aggregate/artifact directories; do not reset unrelated project controllers.
- Remove exactly the two inherited Omni RedisPrep completion timestamps and
  invalidate copied query-engine catalog/cache so neither advertises removed
  Omni work; preserve unrelated timestamps and datasets.
- Prove the behavior across the complete boolean option matrix with
  property-style tests and run-tree integration fixtures.
- Preserve current fork behavior byte-for-byte when the option is `false`.

## Scope

### Included

- `wepppy/weppcloud/templates/controls/fork_console_control.htm` and
  `wepppy/weppcloud/static/js/fork_console.js`.
- `wepppy/weppcloud/routes/fork_console/fork_console.py` for initial option
  hydration.
- `wepppy/microservices/rq_engine/fork_archive_routes.py` and
  `schema_defaults_routes.py` for request/default/response contracts.
- `wepppy/rq/project_rq.py` and `project_rq_fork.py` for copy exclusion and
  destination reset orchestration.
- A bounded Omni reset operation in `wepppy/nodb/mods/omni/` that follows NoDb
  locking, persistence, and cache invalidation contracts.
- User, operator, developer, OpenAPI/schema-default, RQ catalog, and test docs
  affected by the new option.

### Explicitly Out of Scope

- Deleting or changing Omni data in the source project.
- Resetting Watershed, Climate, Landuse, Soils, Wepp, Disturbed, or other
  destination controllers.
- Automatically rebuilding or running Omni after the fork.
- Changing `undisturbify` or `skip_wepp_runs_output` semantics.
- Changing authentication, authorization, target-run ownership, queue choice,
  or job dependency topology.
- Adding a property-testing dependency. The finite boolean state space will be
  exhaustively generated with existing pytest/Jest facilities.

## Stakeholders

- **Primary**: WEPPcloud operators and users who fork projects with large Omni
  scenario/contrast trees.
- **Reviewers**: independent contract/correctness reviewer and QA reviewer.
- **Security Reviewer**: required for run-tree deletion/exclusion and RQ input.
- **Informed**: maintainers of fork/archive and Omni NoDb behavior.

## Success Criteria

- [x] The unchecked option is absent from behavior: existing copy and Omni state
  remain unchanged.
- [x] The checked option excludes child content under both Omni collections.
- [x] The checked destination has real, empty
  `_pups/omni/{scenarios,contrasts}` directories and an empty real `omni/`
  aggregate directory.
- [x] The destination `omni.nodb` loads as a fresh controller with no scenarios,
  contrasts, dependency trees, run-state, output references, or inherited job
  markers.
- [x] The destination has neither Omni RedisPrep completion timestamp nor stale
  query-engine Omni entries, while unrelated timestamps/datasets are retained.
- [x] Source model/Omni state, Omni timestamps, query-engine data, and
  quiescent-fixture hashes are unchanged after excluding only the existing
  source `redisprep.dump` fork-job tracking delta; no source reset/cache/lock
  helper is invoked.
- [x] Every combination of the three fork booleans has contract/property
  coverage, including request serialization, route parsing, enqueue arguments,
  rsync exclusions, reset decision, and terminal destination invariants.
- [x] Failure during reset cannot report fork success or leave a destination
  advertised as ready.
- [x] Focused backend/frontend tests, RQ graph check if needed, full pytest,
  frontend lint/tests, docs lint, correctness/QA/security reviews all pass.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **Decision provenance captured**: yes; operator direction on 2026-08-06 and
  the contract decision artifact in this package.

## Dependencies

### Prerequisites

- Canonical SURF-04B registration composing SURF-04, SURF-04A, DOM-25A, and
  DOM-25B without reopening, advancing, or closing those owners.
- Ratify `artifacts/2026-08-06_contract_decision.md` with two independent
  reviews and explicit finding dispositions.
- Commit the accepted checkpoint as a standalone ancestor.
- Confirm the canonical fresh Omni state against `Omni.__init__`,
  `clear_contrasts`, scenario deletion/cleanup, and NoDb cache/lock rules.

### Blocks

- Implementation of the new fork option.

## Related Packages

- **Related**:
  [Omni fork symlink retarget hardening](../20260802_omni_fork_symlink_retarget_hardening/package.md)

## Timeline Estimate

- **Expected duration**: 3-5 focused sessions.
- **Complexity**: Medium.
- **Risk level**: High because the worker conditionally omits and resets run
  data across an RQ boundary.

## Security Impact and Review Gate

- **Security impact triage**: `high`.
- **Dedicated security review required**: yes.
- **Triage rationale**: the feature accepts a new public route boolean and
  changes which run-tree paths are copied/deleted/reset by an RQ worker.
- **Security review artifact**:
  `artifacts/2026-08-06_security_review.md`.

## References

- `docs/standards/contract-first-change-standard.md`
- `docs/schemas/rq-response-contract.md`
- `docs/schemas/nodb-persistence-concurrency-contract.md`
- `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`
- `wepppy/rq/job-dependencies-catalog.md`
- `docs/ui-docs/weppcloud-project-forking.md`
- `wepppy/nodb/mods/omni/README.md`
- `prompts/completed/fork_skip_omni_reset_execplan.md`

## Deliverables

- Accepted contract checkpoint and review/disposition artifacts.
- UI/API/RQ/NoDb implementation and generated/static bundle update if required.
- Exhaustive boolean-matrix property tests and run-tree integration tests.
- Updated fork, Omni, operator, and schema documentation.

## Independent Scaffold Review

The 2026-08-06 independent review placed the checkpoint on hold and identified
ten accepted amendments covering canonical SURF-04B registration, reset
ordering, full fresh-state equivalence, exclusion of collection nodes, precise
partial-destination failure semantics, checked readiness, mixed-version worker
rollout, exact NoDb cache/lock handling, boundary/accessibility properties, and
quiescent source evidence. See
`artifacts/2026-08-06_scaffold_review.md`. Implementation remains blocked until
the contract incorporates these findings and passes re-review.

The amended contract now specifies the exact post-identity-rewrite reset order,
full persisted fresh-state equivalence, node-level rsync exclusions, unready
partial-destination semantics, checked-job readiness, worker-first deployment,
profile-target cache/lock evidence, expanded boundary/accessibility properties,
and quiescent source evidence.

## Follow-up Work

- Real Redis/RQ recovery integration remains useful residual coverage but does
  not block the accepted fork/reset contract or package closure.

## Closure Summary

Closed on 2026-08-06. Contract checkpoint `82e47916f` precedes implementation
commit `3269f7e97`. The delivered UI/API/RQ/NoDb flow, exhaustive boolean
matrix, destination/source invariants, focused and full validation, and final
correctness, QA, and security reviews all passed.

## Post-Closure Production Incident - 2026-08-10

Three wepp1 jobs exposed a release-blocking coverage gap: a valid source with
no materialized `_pups` Omni child workspace failed with
`FileNotFoundError('_pups')`. The implementation verified existing ancestors
but did not establish missing optional ancestors, contradicting this package's
required final-state and idempotence contract.

The prior phrase "exhaustive boolean matrix" described only request flags and
must not be read as exhaustive runtime-state coverage. Populated and hostile
fixtures omitted the ordinary never-used-feature state, and higher-level tests
mocked the failing directory helper. Remediation and review-governance changes
are tracked in
`docs/work-packages/20260810_fork_omni_empty_state_fix/` (SURF-04B-C1).
