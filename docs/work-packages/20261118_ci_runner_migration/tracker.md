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

## Implementation observations

Status2 isolated smoke built the actual service/client and delivered all five
samples successfully; cleanup removed its own project. Browser image construction
and direct browser validation are in progress. Existing already-relabeled docs,
quality and broad-exception jobs also inherited unused Forest bootstrap; their
explicit standalone setup removes that same host dependency. Cloc retains optional
repository behavior but now explicitly anchors its base directory to the checkout.
The CI Samurai SSH/restart schedule is a separate discovered consumer; the operator explicitly approved retiring it as well. It is disabled on GitHub,
and the source is archived alongside the profile catalog.
