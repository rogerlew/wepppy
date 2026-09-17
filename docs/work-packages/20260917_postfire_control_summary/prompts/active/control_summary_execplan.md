# Align post-fire control with shared summary panels

## Purpose / Big Picture

Place the accepted report and its metadata in the standard middle Summary card, visible only after acceptance. Improve help placement and section separation without changing calculations or saved results.

## Progress

- [x] Inspect control, shared macros, reference Features Export summary and contracts.
- [ ] Obtain independent contract reviews and commit ancestor.
- [ ] Implement template/controller and regression tests.
- [ ] Rebuild bundle, run frontend checks and verify browser states.

## Surprises & Discoveries

The control suppresses the shared Summary card and puts report/downloads in the input column. Shared control_shell already places Summary between Status and Details.

## Decision Log

2026-09-17: operator explicitly requested all layout changes. Preserve stale accepted reports in Summary with Previous run labeling; hide Summary only when no accepted result exists. Remove only raw-file links from this control, preserving report downloads and artifacts. Prior commit authority persists for required checkpoint.

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

Template wepppy/weppcloud/templates/controls/postfire_debris_flow_pure.htm supplies inputs and panel markup. Controller wepppy/weppcloud/controllers_js/postfire_debris_flow.js renders server results. Shared _pure_macros.html control_shell orders Status, Summary, Details. Features Export demonstrates summary_panel_override. Canonical changes are listed in artifacts/20260917_contract_decision.md.

## Plan of Work

First review and commit the contract delta. Then move help above the comparison, add shared spacing wrappers, and populate a hidden standard Summary panel with a report link and metadata table when results exists. Replace raw-file rendering with accepted status/model/time/coverage/explanation/warning rows. Preserve dNBR metadata separately. Add state-transition regression coverage and actual template assertions. Update ENDUSER and README.

## Concrete Steps

From repo root run wctl run-npm lint, wctl run-npm test, targeted postfire template pytest, and python3 wepppy/weppcloud/controllers_js/build_controllers_js.py. Use an authenticated development browser on thespian-cleanness to check the rebuilt control, then exercise absent, accepted, stale and failure states with the real controller without running scientific jobs.

## Validation and Acceptance

No report link visible for absent/empty state or first queued/failed attempt. Accepted current, partial, legacy and stale results show the card, with correct labels and coverage. Failed replacement retains previous card. No raw-file links remain in the control. Unitized area bounds and escaped text remain safe. Screenshots cover desktop/mobile and card placement; validate actual template with existing tests. No server mutation boundary changes, so no scientific rerun or stack restart is needed unless template caching requires a web restart.

## Idempotence and Recovery

Reads and browser inspection do not mutate project data. Rebuild the generated bundle after source edits. Revert only package-specific changes if necessary; preserve unrelated working files.

## Artifacts and Notes

Retain review disposition, test logs and browser evidence in artifacts. No new dependencies or scientific artifact schemas.

## Interfaces and Dependencies

Use existing WCDom, state results, Unitizer and ui.control_shell. The accepted result pointer remains the visibility authority; selected model and job completion messages are not acceptance.
