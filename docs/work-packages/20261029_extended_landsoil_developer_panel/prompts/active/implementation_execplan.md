# Implement the extended landsoil developer-project panel

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain this plan and package tracker together. The operator has requested execution of this package, authorizing implementation and the reviewed contract ancestor commit. Production deployment and role assignment remain outside scope.

## Purpose / Big Picture

Normal Base projects get a simpler Disturbed Panel with Reset Base and Modify Base. Developer projects and projects currently using Extended keep all existing controls. Users can enable project developer mode through a Dev user and reload to obtain extended controls. Model parameter processing and existing authorized APIs remain unchanged.

## Progress

- [x] (2026-10-29 UTC) Inspect current template, getter, controller and routes.
- [x] (2026-10-29 UTC) Record DM-02, Usersum instructions and compatibility matrix.
- [x] (2026-10-29 UTC) Record operator approval for Extended-to-Base/delete loss of full layout after reload.
- [x] (2026-10-29 UTC) Complete independent contract reviews; C1–C3 closed and security approval reconfirmed.
- [ ] After execution is requested, commit reviewed checkpoint as ancestor.
- [ ] Implement conditional template and necessary tests.
- [ ] Validate real base/extended workflows and complete independent implementation review.
- [ ] Update user docs status, package, tracker and final evidence.

## Surprises & Discoveries

`Disturbed.active_lookup_variant` honors explicit Base even when an extended file exists. When stored selection is absent/invalid, it infers Extended from file existence. Explicit Extended with a missing file still resolves Extended; do not hide its recovery controls. `disturbed.js` captures controls at initialization and queries metadata even with only the base modify link; test the sparse layout without rewriting that behavior. The existing header exposes Disturbed for enabled modules independently of PowerUser access.

## Decision Log

2026-10-29 UTC, operator: make full-panel discovery follow project developer mode or current Extended selection, with no backend enforcement. Preserve active legacy projects; do not assign developer mode automatically. Operator accepts switching to Base/deleting Extended results in a simple panel after reload and will manage Dev role assignment.

2026-10-29 UTC, scaffold design: evaluate layout during page rendering; document explicit reload after activation. Keep the currently rendered panel stable during selection/deletion and preserve unsaved inputs. This minimizes changes to controller initialization. Existing DM-01 immediate status/anisotropy updates remain intact.

## Outcomes & Retrospective

Assessment supports a small template change with targeted compatibility tests. No runtime implementation or generated-artifact acceptance has occurred. Both independent contract reviews passed after C1–C3 corrections; no open operator decision remains. Later execution must update this section.

## Context and Orientation

Canonical rules are DM-02 in `docs/schemas/project-developer-mode-contract.md`. The full modal lives in `wepppy/weppcloud/templates/controls/disturbed_modal.htm`, included by `routes/run_0/templates/runs0_pure.htm`. The run route supplies Ron and Disturbed. `templates/reports/_base_report.htm` also includes the modal; common report routes supply Ron but omit Disturbed, and `_context_processors.py:current_ron_processor` does not resolve Disturbed selection. `wepppy/nodb/mods/disturbed/disturbed.py:active_lookup_variant` supplies authoritative resolved selection; do not change it. `wepppy/weppcloud/controllers_js/disturbed.js` binds actions and metadata refresh. `routes/nodb_api/disturbed_bp.py` supplies existing selection/load/delete/sync/editor APIs; they must remain usable without a developer-mode gate. The Usersum reference is `routes/usersum/weppcloud/disturbed-land-soil-lookup.md` under `wepppy/weppcloud`.

Read root and nearest WEPPcloud/controllers/tests AGENTS, DM-02, the package state matrix and checkpoint. Base revision is `981caadf553c12b1199b9d76f5a28c100b6722e3`; do not change branches or modify closed packages. Ignore generated Usersum index churn per root instructions.

## Plan of Work

### Milestone 1: Ratify the checkpoint

Finish two independent read-only contract reviews and disposition all findings. Once implementation is requested and commit authority exists, commit the canonical amendment, Usersum planned guidance and package as a separate ancestor. Record the SHA in the tracker. This checkpoint does not change templates, backend code, tests or run data.

### Milestone 2: Render the appropriate controls

Extend existing template tests before changing markup. In the existing modal derive full-panel eligibility from `ron.developer_mode` or the resolved Extended variant. Inventory all modal consumers, including run and report shells. Add the smallest shared presentation-state read needed for reports that omit a Disturbed template variable; use the active page/run root and normal NoDb read path, never construct a missing controller or infer Base solely from absent Jinja context. Preserve the module-enabled guard. Do not construct or persist missing controllers solely for presentation. Share the existing base actions, dialog/status/help markup; conditionally include advanced groups and avoid blank headings. Simple layout has no extended actions or selection radio group. Preserve selectors, base editor URL, action feedback, modal focus/close behavior and current readonly rules. Prefer no production JS changes.

Add sparse-layout coverage to existing Disturbed Jest tests: initialization, metadata refresh, reset feedback and the base editor link must work with no extended controls/radios. Verify the full layout's existing selection/load/delete/sync behavior. If a production JS change proves necessary, retain the failing evidence and keep it limited to absent-DOM handling; do not introduce a second policy/state authority. Update any activation success text needed to make the documented reload requirement clear without introducing automatic reload.

### Milestone 3: Validate compatibility through real boundaries

Cover all package state rows using the real getter and temporary files where relevant. Add report-shell tests with no supplied Disturbed variable and real existing explicit Extended, legacy Extended and explicit Base state; verify the shared resolver does not create missing `disturbed.nodb`. Explicit Base plus an extended file is simple; legacy missing selector plus an extended file is full. Empty/old-schema tables retain current validation; missing file with explicit Extended retains full recovery UI. A non-Dev caller sees full layout on an eligible project; a Dev caller on normal Base sees simple. Backend tests must confirm direct authorized Extended operations still accept normal mode and existing denied/invalid requests remain denied/invalid.

On disposable representative projects, record browser/HTTP evidence of both layouts, actual base edit and reset with CSV content readback, preserved legacy Extended edit/selection, and Extended-to-Base/delete followed by reload. Verify enabling mode and manually reloading reveals full controls without generating/resetting lookup files or changing prepared model inputs. Hash relevant CSV/input files before and after read-only rendering and activation. No model execution or native rebuild is required because this package does not change parameter generation; reassess if implementation expands that scope. Do not mutate source projects or assign user roles.

### Milestone 4: Complete reviews and documentation

Obtain correctness and scoped security/noninterference review of final diff and evidence. Close medium/high findings. Remove the Usersum planned-update notice only when behavior is implemented and locally validated; record deployment separately. Update DM-02 implementation status, package, tracker, PROJECT_TRACKER and this plan. Archive the plan only after accepted implementation and gates complete.

## Concrete Steps

Run from `/home/workdir/wepppy`, using canonical wctl commands. Focused Python targets are `tests/weppcloud/routes/test_pure_controls_render.py`, `tests/weppcloud/routes/test_disturbed_bp.py`, and `tests/nodb/mods/disturbed/test_lookup_contract.py`. Run the Disturbed Jest file via `wctl run-npm test -- --runInBand controllers_js/__tests__/disturbed.test.js`. Run `wctl run-npm lint` and `wctl run-npm test` for template-only implementation too. If controller JS changes, also use the existing controller builder through wctl. Run `wctl run-pytest tests --maxfail=1` for the substantive template implementation per root guidance, retaining unrelated baseline limitations. Run scoped `wctl doc-lint`, manifest validation for Usersum if catalog metadata changes, and `git diff --check`. No queue topology, stub API, native release or schema edits are planned.

## Validation and Acceptance

A normal Base project has exactly the two lookup actions requested; authorized users can still complete both operations. An eligible project retains all existing controls. Reload reflects current Ron/Disturbed state, including the operator-approved loss of legacy full-panel access; no hidden migration or sticky flag exists. Direct authorized extended APIs remain functional in normal projects. Artifact readback proves presentation/activation does not alter data, while requested base edit/reset changes only its intended CSV. Actual browser links and Help still resolve. Existing auth/readonly/CSRF expectations and malformed-state behavior remain unchanged.

## Idempotence and Recovery

Rendering is read-only and repeatable. Reverting the template restores the prior full presentation without changing project data. Clone/restore uses incoming state; no migration rollback is required. Use disposable projects for reset/delete/edit acceptance; preserve source files and do not recover by forcing developer mode. Repeated Dev activation follows existing DM-01 idempotence.

## Artifacts and Notes

Store review findings, dispositions, command outcomes, real-state matrix evidence, browser captures and CSV/input hashes under this package's artifacts directory. Documentation-only review does not establish runtime conformance. Keep implemented, locally validated and deployed status distinct.

## Interfaces and Dependencies

Reuse Ron's existing boolean getter, Disturbed's existing string-valued selection getter, current Jinja macros, selectors, HTTP responses and docs routes. No new public API, dependency, registry entitlement or persistence field. Canonical rule amendments stay outside this work package.

Revision note (2026-10-29 UTC): initial scaffold records the operator-approved presentation policy and transition tradeoff; implementation deliberately pending.

Review revision (2026-10-29 UTC): include report-shell state resolution and real report-context tests (C1), correct loading/selection guidance for legacy fallback (C2), and require frontend lint/tests for template changes (C3). These are conformance corrections; no new operator decision.
