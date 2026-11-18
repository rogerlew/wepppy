# CI runner migration tracker

Updated: 2026-11-18 UTC. Branch: task/ci-runner-migration.

## Progress

- [x] Audit live runner labels, workflow state and retained runs.
- [x] Operator approved migrating nightly checks and retiring 21 profile schedules.
- [ ] Migrate active checks, nightly checks and telemetry; regenerate workflows.
- [ ] Validate generated workflows and real isolated executions; review boundaries.
- [ ] Integrate through PR and retain receipt; clean obsolete queued runs.

## Decisions

Preserve coverage; remove dependence on Forest host setup. Profile schedule retirement
is explicit operator authorization, not inferred from lack of recent successful runs.

## Evidence

[Runner audit](artifacts/runner-audit.json) records 33 enabled homelab workflows;
32 latest executions were queued and Cloc's latest was canceled. There is no
registered homelab runner. Both supported runners are online; only runner-02
is eligible for general remote-ci workloads.
