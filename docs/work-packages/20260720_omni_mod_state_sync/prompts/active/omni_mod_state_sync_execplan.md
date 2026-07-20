# Synchronize Omni mod state across the menu, preflight, and runs page

This ExecPlan is a living document maintained under `docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current.

## Purpose / Big Picture

Every user must see Omni Contrasts in the Mods menu. Unauthorized users see a
disabled checkbox with `Not Authorized` directly below the label. Authorized
users see a prerequisite reason until Omni Scenarios is active. After this
work, enabling scenarios alone enables—but does not check—the contrast option
and leaves contrasts absent from the run-page controls and preflight navigation.
Explicitly enabling contrasts makes all four representations—persisted mod
list, checkbox, section, and preflight entry—agree immediately and after refresh.

## Progress

- [x] (2026-07-20 21:08 UTC) Reproduced the contract mismatch in registry visibility and runs-route state derivation.
- [x] (2026-07-20 21:08 UTC) Created the contract decision and amended the feature-registry specification.
- [x] (2026-07-20 21:22 UTC) Obtained and dispositioned two independent contract reviews; both found blocking registered-ownership and contract-conflict issues.
- [x] (2026-07-20 21:23 UTC) Operator authorized GOV-00A expansion, REM-01 registration, and visible-to-all disabled semantics.
- [x] (2026-07-20 21:40 UTC) Obtain and disposition two independent reviews of the governance and contract amendments.
- [x] (2026-07-20 21:42 UTC) Commit ratified contract checkpoint `1afa57fd6d63b93688057143ec5c45daa6f3170f` as the standalone ancestor.
- [x] (2026-07-20 21:51 UTC) Implement registry, backend guard, run-page/bootstrap, and dynamic controller synchronization.
- [x] (2026-07-20 21:51 UTC) Add targeted pytest and Jest regressions.
- [x] (2026-07-20 21:52 UTC) Rebuild the controller bundle and run targeted validation.
- [x] (2026-07-20 22:18 UTC) Dual-review and commit direct-action/report security scope amendment ancestor `57ea1a3e2e71073f65e45c4af1cc607b2323ef37`.
- [x] (2026-07-20 22:25 UTC) Enforce Dev/Root on contrast RQ/report entry points and add role regressions.
- [x] (2026-07-20 22:32 UTC) Dispatch two independent final reviews and disposition every finding; both reviewers approve with no findings.
- [x] (2026-07-20 22:42 UTC) Complete the stable-tree repository-wide Python
  sweep (5,070 passed, 58 skipped) and close the package.

## Surprises & Discoveries

- Observation: The registry already has separate `omni` and `omni_contrasts` ids, but `build_header_mod_options` uses `requires_features` as a visibility filter.
  Evidence: With no active `omni`, the `omni_contrasts` entry is omitted even for a Dev/Root-authorized user.
- Observation: The runs route computes `show_omni_contrasts = show_omni and role`, ignoring the persisted `omni_contrasts` id.
  Evidence: Refreshing an `omni`-only run can render contrasts while its Mods checkbox remains unchecked.
- Observation: The dynamic project controller has an Omni Scenarios bootstrap mapping but no `omni_contrasts` mapping, even though both sections share the Omni controller.
  Evidence: Explicit async loading of a contrasts section cannot remount the controller to bind the newly inserted form.
- Observation: The generated controller bundle is ignored rather than tracked,
  so a successful rebuild updates the local runtime asset without producing a
  Git diff.
  Evidence: The rebuilt `static/js/controllers-gl.js` contains the new
  `omni_contrasts` bootstrap and availability logic while `git status` reports
  only its tracked source module.
- Observation: Direct contrast run/dry-run/delete routes retained JWT scope and
  run access but lacked the embargo role gate; the CAP-gated contrast report
  lacked both run access and the role gate.
  Evidence: The first final security review found no `require_roles` call in
  the three rq-engine entry points and neither `authorize(runid, config)` nor a
  feature-role check on the Flask report.
- Observation: Template fallbacks that infer contrast visibility cannot prove
  authorization or child-run state when route context is omitted.
  Evidence: Final contract review rejected the first implementation until both
  template fallbacks failed closed and the production five-predicate helper had
  direct behavioral matrix coverage.
- Observation: The new contract-first standard assigns this change across
  DOM-02, DOM-25A, and DOM-25B, whose registered dependencies are not complete.
  Evidence: Dual review cited the child-package register rows and independently
  rejected this package as a canonical owner.

## Decision Log

- Superseded decision: The first draft classified the work as conformance
  restoration. Dual review rejected that classification because the prior
  registry specification hid missing-prerequisite features and the embargo ADR
  barred general visibility. REM-01 is an operator-approved intended behavior
  change with both authorities amended in the ancestor.
  Date/Author: 2026-07-20 / Codex, superseded after review.
- Decision: Preserve `requires_features: [omni]` for contrast enablement, but remove prerequisite filtering from menu visibility.
  Rationale: Authorized users can discover the feature without allowing an invalid persisted state.
  Date/Author: 2026-07-20 / Codex.
- Decision: Add `omni_contrasts` as a blocker when disabling `omni`.
  Rationale: The dependency must hold in both enable and disable directions.
  Date/Author: 2026-07-20 / Codex.
- Decision: Stop before implementation and revert the unregistered specification amendment.
  Rationale: Both independent reviewers identified high-severity ownership and contract-classification defects; proceeding would violate the active contract-first standard.
  Date/Author: 2026-07-20 / Codex.
- Decision: Register REM-01 as a bounded pre-GOV-01 borrower of DOM-02,
  DOM-25A, and DOM-25B.
  Rationale: The operator authorized a finite cross-owner production remediation
  without advancing or bypassing the future owner packages for unrelated work.
  Date/Author: 2026-07-20 / User and Codex.
- Decision: Use `menu_min_role: user` for Omni Contrasts while retaining
  `min_role: dev` for enable and dynamic-load authorization.
  Rationale: Every user can discover the feature, but the server authorization
  boundary remains unchanged. Unauthorized users receive `Not Authorized`.
  Date/Author: 2026-07-20 / User.

## Outcomes & Retrospective

The bounded contract was dual-reviewed and sealed at standalone ancestor
`1afa57fd6d63b93688057143ec5c45daa6f3170f`; its direct-action/report security
amendment was dual-reviewed and sealed at
`57ea1a3e2e71073f65e45c4af1cc607b2323ef37`. The registered implementation and
focused regressions are complete. Targeted Python and Jest suites, full frontend
lint/tests, broad-exception enforcement, bundle rebuilding, and the stable-tree
repository-wide Python sweep all pass. The broad sweep closed at 5,070 passed
and 58 skipped. Both final reviewers approve with no findings, so REM-01 is
complete without advancing DOM-02, DOM-25A, or DOM-25B.

## Context and Orientation

WEPPcloud stores active run features in `Ron.mods`, a list of string ids persisted for each run. `wepppy/weppcloud/feature_registry/feature_registry.yaml` defines each feature's role, backend, prerequisites, auto-enabled dependencies, and disable blockers. `wepppy/weppcloud/feature_registry/runtime.py` builds the run-header Mods options. The toggle endpoint in `wepppy/weppcloud/routes/nodb_api/project_bp.py` validates and mutates `Ron.mods`.

The server-rendered runs page is assembled in `wepppy/weppcloud/routes/run_0/run_0_bp.py` and `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`. A navigation item is also the preflight target: `wepppy/weppcloud/static/js/preflight.js` applies status to the existing anchor but does not decide whether that feature should exist. `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2` serializes persisted and authorized state into `window.runContext.mods`. `wepppy/weppcloud/controllers_js/project.js` reconciles that state when a checkbox loads or removes a section without a page refresh.

Omni Scenarios and Omni Contrasts share `wepppy/weppcloud/controllers_js/omni.js`, but use separate forms and status channels. The shared controller must be remounted after either section is dynamically inserted so it discovers the current forms.

## Plan of Work

First complete fresh dual review of the GOV-00A bounded-remediation mechanism,
REM-01 registration, feature-registry contract, authoritative YAML metadata,
security artifact, and test plan. Commit the reviewed checkpoint as a standalone
ancestor. After that gate, extend the feature registry schema/runtime with the
optional `menu_min_role` field. Default behavior remains unchanged for every
other feature. For Omni Contrasts, build a visible menu option for all users,
with authorization and prerequisite availability represented separately.

In `run_0_bp.py`, derive `show_omni_contrasts` from the persisted `omni_contrasts` id, the internal role gate, a usable shared Omni controller, and the non-child-run constraint. Preserve `show_omni` as the scenarios-only state. In `run_page_bootstrap.js.j2`, serialize an explicit `omni_contrasts` flag and include it in the test-only load-all path. The existing `runs0_pure.htm` nav and section wrappers then follow the corrected context.

Before route security edits, dual-review and commit the finite amendment that
adds only Dev/Root authorization gates to the existing contrast run, dry-run,
and delete entry points, plus canonical run access and Dev/Root to the existing
CAP-gated report. Preserve all request payloads, authorized-flow response
shapes, queue wiring, report rendering, and underlying domain behavior; new
denials use the canonical boundary-specific authorization response.

In `_run_header_fixed.htm`, render the disabled reason directly below the label
and serialize authorization plus prerequisite metadata on the checkbox. In
`project.js`, independently recompute checked state, enable availability, and
active nav/section visibility whenever the authoritative mod list changes
and add a bootstrap handler for `omni_contrasts` that force-remounts the shared
Omni controller. Verify the response's authoritative `mods` list controls both
checkbox checked states without using the same predicate for navigation/section
states; do not add enable propagation
between the Omni ids.

Add regressions to `tests/weppcloud/routes/test_feature_registry_runtime.py`, `tests/weppcloud/routes/test_project_bp.py`, `tests/weppcloud/routes/test_run_0_openet_admin_gate.py`, `tests/weppcloud/routes/test_pure_controls_render.py`, and `wepppy/weppcloud/controllers_js/__tests__/project.test.js` as needed. Rebuild `wepppy/weppcloud/static/js/controllers-gl.js` with the canonical builder after the controller source changes.

Add full role-matrix authorization regressions to
`tests/microservices/test_rq_engine_omni_routes.py` and
`tests/weppcloud/routes/test_omni_bp_routes.py`. Denied tests must prove the
domain operation is not entered.
Also prove JWT scope and run access still deny RQ requests carrying Dev/Root,
and that the Flask CAP and run-access gates remain mandatory alongside role.

## Concrete Steps

Work from `/home/workdir/wepppy`.

Review and commit the checkpoint before implementation:

    git diff --check
    wctl doc-lint --path docs/work-packages/20260720_omni_mod_state_sync
    wctl doc-lint --path wepppy/weppcloud/feature_registry/specification.md

Run targeted backend and render tests during implementation:

    wctl run-pytest tests/weppcloud/routes/test_feature_registry_runtime.py tests/weppcloud/routes/test_project_bp.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py tests/weppcloud/routes/test_pure_controls_render.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1

Run frontend checks and rebuild the generated bundle:

    wctl run-npm test -- project
    wctl run-npm lint
    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py

Run changed-file quality checks before review:

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    git diff --check

## Validation and Acceptance

The registry and render tests must prove every user receives the Omni Contrasts
menu option. An ordinary user sees it disabled with `Not Authorized` directly
below the label. A Dev/Root-authorized user without scenarios sees it disabled
and unchecked with `Enable Omni Scenarios first`. Endpoint tests must prove an
ordinary user cannot enable or dynamically load contrasts, enabling `omni`
returns no `omni_contrasts`, enabling contrasts without scenarios fails without
mutation, and disabling scenarios while contrasts is active fails without
mutation. Each rejected action must preserve the persisted list, checkbox,
section, and preflight state immediately and after refresh.

The bootstrap render test must extract distinct `omni` and `omni_contrasts` booleans. With only `omni` persisted, scenarios is true and contrasts is false. With both persisted and authorized, both are true. The controller test must show that an `omni` response leaves the contrasts input, nav, and section false/hidden, while an explicit `omni_contrasts` response loads `view/mod/omni_contrasts`, reveals only that section/nav, and force-remounts `window.Omni`.

Add a full role matrix: User, PowerUser, and Admin see the disabled menu entry
but are denied both the mutation POST and dynamic-section GET with no persisted
or DOM mutation; Dev and Root are allowed when prerequisites are satisfied.
For each contrast run, dry-run, delete, and report entry point, User,
PowerUser, and Admin are denied before any contrast domain operation while Dev
and Root retain authorized flows. RQ Dev/Root requests without the required JWT
scope or run access remain denied. The Flask report retains its CAP gate and
denies Dev/Root without run access; every denial stops before report data is read.
Add legacy contrasts-only cases with and without `omni.nodb`: an authorized
user sees the checkbox checked and enabled for cleanup, section/preflight stay
unavailable, disable succeeds, and refresh shows the id removed. Add parity
coverage proving RUSLE and every feature without `menu_min_role` retains prior
visibility semantics. Schema negatives must reject unknown roles and audience
narrowing/cross-audience combinations such as `min_role: dev` with
`menu_min_role: admin`.

After deployment, first open a run as an unauthorized user and confirm Omni
Contrasts is visible, disabled, and followed by `Not Authorized`. Then open an
authorized run with neither Omni mod; confirm contrasts is disabled with
`Enable Omni Scenarios first`; enable Omni Scenarios; confirm only scenarios
plus its declared Treatments dependency become active and the contrast checkbox
becomes enabled but remains unchecked; refresh and confirm contrasts remains
absent from preflight and the active controls DOM; enable Omni Contrasts
explicitly; confirm its checkbox, section, and preflight entry appear; refresh
and confirm all remain aligned.

## Idempotence and Recovery

The edits and tests are repeatable. Do not mutate production run data. If the generated bundle differs unexpectedly outside the intended project-controller block, stop and inspect the builder inputs rather than hand-editing the bundle. The worktree contains unrelated user changes; stage and commit only paths owned by this package.

## Artifacts and Notes

The accepted checkpoint is `artifacts/2026-07-20_contract_decision.md`. Contract and implementation review artifacts will be added under `artifacts/`, followed by a final disposition that identifies fixed, rejected, and deferred findings with evidence.

## Interfaces and Dependencies

No new dependency is introduced. `build_header_mod_options(active_mods, user, is_wbt, include_all)` keeps its signature. `set_project_mod_state(runid, config, mod_name, enabled)` keeps its response schema. `window.runContext.mods.flags` gains the already-registered key `omni_contrasts`; all values remain booleans. `Project.set_mod` keeps its Promise result and event contracts.

Revision note (2026-07-20): Initial self-contained plan created from the reported production sequence and existing independent-gating ADR.

Revision note (2026-07-20 21:22 UTC): Updated after dual contract review to
record the blocking registered-ownership, UX conflict, security, rejected-action,
and legacy-state findings; implementation is stopped pending operator direction.

Revision note (2026-07-20 21:23 UTC): Updated after operator authorization to
register REM-01, ratify visible-to-all disabled semantics, preserve Dev/Root
server authorization, and require fresh dual review before the ancestor commit.
