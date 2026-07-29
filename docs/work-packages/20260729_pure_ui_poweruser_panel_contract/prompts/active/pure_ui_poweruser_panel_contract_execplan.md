# Verify the PowerUser panel contract

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

Privileged operators can inspect exact run resources, recover locks, promote a
profile draft, mint a scoped token, and use optional notifications without
exposing those controls or side effects to ordinary run viewers.

## Progress

- [x] (2026-07-29 UTC) Scaffolded SHR-07 and ratified concise intent.
- [x] (2026-07-29 UTC) Traced launcher/panel, inline clients, Project actions,
  Flask routes, runtime locks, service worker, and existing tests.
- [x] (2026-07-29 UTC) Added actual-render, direct-inline, and route regressions.
- [x] (2026-07-29 UTC) Patched only reproduced contradictions.
- [x] (2026-07-29 UTC) Passed focused/broad validation and security review.
- [x] (2026-07-29 UTC) Reconciled records and closed SHR-07.

## Surprises & Discoveries

- Observation: The PowerUser launcher and included panel are not role-gated.
  Evidence: `_run_header_fixed.htm` and `runs0_pure.htm` render them
  unconditionally.

- Observation: Clear Locks requires run authorization but no privileged role.
  Evidence: `project_bp.clear_locks` lacks `roles_required`.

- Observation: Notification initialization runs before discovering there is no
  `#notificationToggle` producer anywhere in the template tree.
  Evidence: repository search finds only client lookups, while DOMContentLoaded
  calls `initPush()` first.

- Observation: Recorder promotion rendered for Admin while its established
  backend boundary requires PowerUser.
  Evidence: the panel condition and `recorder_bp.recorder_promote` disagreed.

- Observation: The clear-lock method change updates generated RQ route
  inventory despite no queue-edge change.
  Evidence: regeneration retained 144 edges and the graph gate passed.

## Decision Log

- Decision: Ratify PowerUser/Admin/Root as the consistent panel and recovery
  boundary.
  Rationale: The registered package calls this a privileged panel and adjacent
  TTL/token/operator controls already use that role set.
  Date/Author: 2026-07-29 / Codex with operator authority.

- Decision: Keep absent notification UI side-effect free rather than add a new
  toggle.
  Rationale: A new control changes UX and web-push behavior; the bounded
  conformance repair is to no-op when the existing optional consumer is absent.
  Date/Author: 2026-07-29 / Codex.

- Decision: Align recorder rendering to the existing PowerUser backend
  contract instead of broadening route authority.
  Date/Author: 2026-07-29 / Codex.

- Decision: Update the Command Bar clear-lock caller as a finite consumer of
  the shared route so the confirmed destructive-GET defect is fully removed.
  Date/Author: 2026-07-29 / Codex.

## Outcomes & Retrospective

SHR-07 is verified. Ordinary users receive neither launcher, panel, privileged
actions, nor inline clients. Clear-lock is a run-authorized,
PowerUser/Admin/Root-only POST consumed through CSRF-aware clients. Recorder
promotion matches its existing PowerUser authority. Missing notification UI
has no browser/network side effect, and repeated token evaluation retains one
owner.

Evidence passed 187 focused render/route tests, 34 focused Jest tests, 29
retained token/runtime-lock tests, frontend lint, the complete
103-suite/738-test frontend sweep, and the complete 5,565-test Python sweep
with 58 skips and 12 subtests. The regenerated 144-edge RQ inventory and graph
gate passed. Security review has no unresolved high or medium finding.

## Context and Orientation

The run header opens `#puModal`. `runs0_pure.htm` includes
`poweruser_panel.htm`, whose server-rendered links/actions are followed by
inline web-push and token clients. `project.js` consumes clear-lock and recorder
actions. `project_bp.py`, `recorder_bp.py`, and `user.py` enforce backend
behavior. The service worker is served by `run_0_bp.py`.

## Plan of Work

Render ordinary, PowerUser, Admin, Root, feature-enabled, and hostile contexts
through the actual run shell. Execute the real inline clients for absent
notifications and Admin token mint/copy/error/repeat ownership. Add direct route
tests for clear locks and recorder promotion role parity. Retain Project,
runtime-lock, token, CSRF, and service-worker suites. Patch only reproduced role
or lifecycle contradictions.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-npm test -- poweruser
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py \
      tests/weppcloud/routes/test_project_bp.py \
      tests/weppcloud/routes/test_user_profile_token.py \
      tests/runtime_paths/test_mutations_thaw_freeze_contract.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl check-rq-graph
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path \
      docs/work-packages/20260729_pure_ui_poweruser_panel_contract
    wctl doc-lint --path \
      docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

## Validation and Acceptance

Acceptance requires exact role/render evidence, direct execution of the inline
clients, backend role/run authorization, retained lock/token/recorder/CSRF
evidence, and passing focused/broad gates.

## Idempotence and Recovery

Rendering and tests are safe to rerun. Inline tests isolate browser globals,
storage, service workers, notification state, timers, and clipboard behavior.
Role repairs are additive denials and retain authorized paths.

## Interfaces and Dependencies

Preserve `#puModal`, `data-project-action`, resource/browse URLs,
`recorder/promote`, `data-run-token-*`, token class `service`, 24-hour token TTL,
web-push subscription paths, seven-day enable TTL, CSRF discovery, and
same-origin credentials.

## Revision Notes

2026-07-29: Created from explicit operator direction to execute the recommended
PowerUser panel package.
