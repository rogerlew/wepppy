# Fork Copy Optimization for `wepp/runs` and `wepp/output`

**Status**: Open (2026-05-06)  
**Timezone**: UTC

## Overview

This package adds a new fork-console option to skip copying heavy WEPP run/output trees (`wepp/runs`, `wepp/output`) while still creating those directories in the fork target. The goal is to reduce fork time and I/O cost when operators only need project metadata/state scaffolding or plan to regenerate WEPP artifacts.

It also verifies and codifies the existing undisturbify path behavior so undisturbify forks keep skipping those heavy directories for efficiency.

## Objectives

- Add a fork-console checkbox labeled `Skip wepp/runs and wepp/output`.
- Carry the new option through UI payload -> rq-engine route -> RQ fork worker helper.
- Ensure skipped trees are still created as empty directories in the destination run.
- Keep `undisturbify` behavior efficient and explicit (skip copying those trees).
- Add targeted regressions for route payload handling, rsync exclude behavior, and schema defaults metadata.

## Scope

### Included

- Fork console template and JavaScript payload wiring.
- RQ-engine fork route payload parsing and enqueue argument wiring.
- Fork helper copy command and destination-directory guarantees.
- Schema-defaults metadata updates for the fork endpoint.
- Focused tests in `tests/rq/` and `tests/microservices/`.
- Documentation update in `docs/ui-docs/weppcloud-project-forking.md`.

### Explicitly Out of Scope

- Any change to archive/restore flows.
- Any change to run ownership/auth policy.
- Any change to undisturbify landuse/soils rebuild semantics beyond copy optimization.
- Any large redesign of fork-console UI structure.

## Stakeholders

- **Primary**: WEPPcloud operators and users forking large runs.
- **Reviewers**: RQ-engine maintainers, WEPPcloud route/UI maintainers.
- **Security Reviewer**: Not required for this scoped change (no new auth/secret surface).
- **Informed**: Disturbed/undisturbify workflow maintainers.

## Success Criteria

- [x] Fork console exposes `Skip wepp/runs and wepp/output` as an optional checkbox.
- [x] Fork API accepts and propagates a boolean skip flag without breaking existing clients.
- [x] Normal fork with skip enabled excludes `wepp/runs` and `wepp/output` content copy but creates both directories in the target.
- [x] Undisturbify forks continue skipping those directories and also guarantee they exist in target runs.
- [x] Targeted regression tests pass for helper command generation, route payload contract, and schema defaults.

## Dependencies

### Prerequisites

- Existing fork console control and JavaScript in `wepppy/weppcloud/templates/controls/fork_console_control.htm` and `wepppy/weppcloud/static/js/fork_console.js`.
- Existing fork RQ route and helper paths in:
  - `wepppy/microservices/rq_engine/fork_archive_routes.py`
  - `wepppy/rq/project_rq.py`
  - `wepppy/rq/project_rq_fork.py`

### Blocks

- None expected.

## Related Packages

- **Related**: `docs/work-packages/20260208_rq_engine_agent_usability/`
- **Related**: `docs/work-packages/20260411_rq_operator_experience_hardening/`

## Timeline Estimate

- **Expected duration**: 1 focused session.
- **Complexity**: Medium.
- **Risk level**: Low-Medium (route + worker argument wiring).

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: The change adds an optional fork-copy behavior flag and does not expand auth scope, token handling, or external egress.
- **Security review artifact**: `N/A`

## References

- `docs/ui-docs/weppcloud-project-forking.md`
- `wepppy/weppcloud/routes/fork_console/fork_console.py`
- `wepppy/weppcloud/templates/controls/fork_console_control.htm`
- `wepppy/weppcloud/static/js/fork_console.js`
- `wepppy/microservices/rq_engine/fork_archive_routes.py`
- `wepppy/microservices/rq_engine/schema_defaults_routes.py`
- `wepppy/rq/project_rq.py`
- `wepppy/rq/project_rq_fork.py`

## Deliverables

- Fork UI option + payload wiring.
- Backend route + worker-helper wiring.
- Regression tests and schema-default metadata updates.
- Subagent review findings and disposition artifact.

## Follow-up Work

- Optional future enhancement: expose fork-size estimates and expected speed-up hints in UI before submission.
