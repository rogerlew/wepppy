# Automatic deletion help execution plan

## Purpose / Big Picture

Let ordinary users understand whether their project may be automatically deleted,
disable deletion, confirm the result, and find help without knowing “TTL”. Execute
only this plan; unrelated active work packages are outside scope.

## Progress

- [x] Inspected controls, catalog readers, docs and existing tests.
- [x] Recorded operator wording and compatibility plan.
- [x] Review and commit contract checkpoint before implementation (`c62567f1c`).
- [x] Implement and test catalog state, controls, messages and documentation.
- [x] Rebuild bundle and close independent correctness/security reviews.
- [x] Prepare final implementation commit; authorized push verified in handoff.

## Surprises & Discoveries

The catalog currently uses null expiration for both disabled and unknown state.
The controller reads the already-clicked checkbox as its previous value, so a
failed save can leave the checkbox misleadingly checked.

## Decision Log

2026-11-04, operator: use the three exact labels in the checkpoint. Add a nullable
JSON field from existing policy instead of changing disk or database schemas.
Keep technical TTL identifiers for compatibility. Use readable UTC dates to avoid
ambiguous timezone changes. Only scoped tests; no full-suite run.

## Outcomes & Retrospective

Implementation and scoped validation complete. Operator wording and discoverable
help are implemented; confirmed status survives failure/readonly/batch cases.
Desktop render inspected. Existing mobile fixture overflow is unchanged.
No production deployment claim.

## Context and Orientation

`wepppy/weppcloud/routes/user.py` builds legacy catalog JSON; `run_catalog/reader.py`
builds SQL-backed JSON. `templates/user/runs2.html` renders the table. The two
headers are `templates/header/_run_header_fixed.htm` and
`templates/reports/_base_report.htm`. `controllers_js/project.js` saves the toggle.
Usersum manifest/nav/template files publish help and its searchable content.

## Plan of Work

Commit the reviewed contracts first. Add `ttl_disabled` to both readers with the
same freshness boundary as expiration; retain existing APIs. Update the table
and headers with approved wording and contextual links. Restore confirmed checkbox
state after errors and update visible status only after successful saves. Rewrite
the existing guide, move its existing nav leaf into Managing projects, and rename
user-facing Usersum chrome to WEPPcloud Help. Preserve all URLs and role rules.

## Concrete Steps

From repository root run focused pytest for user metadata/catalog readers,
project routes, header rendering and Usersum publication. Run Jest only for project,
Runs lifecycle/catalog and relevant help tests. Run `wctl run-npm lint`, rebuild
with `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`, validate
Usersum with its CLI and lint changed Markdown. Do not run the full suite.

## Validation and Acceptance

Active rows show the approved enabled wording with readable UTC dates; disabled
and excluded rows show disabled; missing/invalid/stale rows show unknown. Help is
available in every state and next to both header controls. All signed-in roles
retain access; missing data never claims protection. Successful toggles update
status; errors restore confirmed checkbox state without claiming server success.
Natural search phrases locate the guide. Test actual template DOM and JSON rather
than only source strings; retain scoped command results in tracker.

## Idempotence and Recovery

No data migration. Reverting implementation commits restores presentation; the
additive JSON field may be ignored by old clients. Do not alter stored TTL files
except in disposable tests. Build the controller artifact from current source.

## Artifacts and Notes

Checkpoint and reviews live in this package's artifacts directory. No production
user run or production service is mutated by this task.

## Interfaces and Dependencies

Catalog `ttl_disabled`: true for known disabled/excluded policy, false for known
active valid expiration, null otherwise. SQL path requires current/fresh data.
Use existing Flask/Jinja/Jest/pytest/Usersum tooling and browser date formatting.

Revision 2026-11-04: recorded scoped validation, final reviews and existing mobile
fixture limitation; implementation is ready for the final authorized commit/push handoff.
