# Contract decision — 2026-09-21

Base: `f97dab846`. Classification: intended menu behavior change.
Operator explicitly approved removal and a local checkpoint commit; no push.

Authorities: feature registry `specification.md` and `feature_registry.yaml`;
shared `docs/ui-docs/controller-contract.md` invariants remain unchanged.
Exact delta: `build_header_mod_options` excludes `culvert_runner` and
`batch_runner` even for Dev/Root, active legacy ids and `include_all`.
Rationale: these standalone workflows have no run-level UI controls.
Compatibility: registry entries, standalone routes, authorization, stored mods,
section rendering and unrelated menu entries remain unchanged.
Security impact: low; no server access or mutation boundary changes.

State matrix: absent/empty active set, populated other mods, either/both legacy
runner ids, unknown ids; exclusions are independent of state. Malformed input
retains existing validation/error behavior. No new user-reachable exceptions.
No artifact-producing boundary changes; archive/restore is not applicable.

Evidence: targeted real-registry menu-builder tests across roles, backends,
active states and `include_all`; registry entries remain available and normal
Omni remains selectable. Existing registry/header-render suites must pass.
Full numerical suite is disproportionate to a two-id menu filter; no model,
NoDb, queue, controller JS or filesystem logic changes.

Independent prereviews: `/root/runner_menu_contract1` and
`/root/runner_menu_contract2` both PASS before implementation, no findings.
Both confirm menu-only scope, preserved registry/authorization/state and require
privileged/legacy/include-all coverage plus ordinary Omni availability. Retain
existing option order. Those checks are included in the regression plan.
