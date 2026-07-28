# SHR-05 Pure UI Unitizer Preferences Contract

**Status**: Closed
**Package ID**: SHR-05
**Security impact**: `high` because an authenticated run preference is mutated

## Purpose

Verify the shared Unitizer preference path from rendered global/category radios
through browser conversion state, the Project controller request, route
validation, NoDb persistence, and reload. Preserve existing conversion tables,
precision policies, defaults, and compatibility behavior.

## Concise Intent Contract

The modal renders exactly one global `unit_main_selector` group and one
`unitizer_<category>_radio` group for every authoritative precision category.
Checked state reflects persisted preferences. Global SI/English selection
updates all categories, individual radios override one category, and both paths
apply visible units/numeric fields before posting the complete preference map
to the current run.

The route accepts JSON or form input, ignores unknown/invalid preferences
without discarding valid entries, persists accepted values through the Unitizer
NoDb lock/dump contract, and returns the authoritative persisted map. Reloaded
templates select that state. Missing client/run context and failed requests
surface the existing Project failure lifecycle without inventing fallback
persistence.

## Scope

- `wepppy/nodb/unitizer.py` preference state and reload;
- generated `static/js/unitizer_map.js` parity with backend tables;
- `controllers_js/unitizer_client.js` conversion, DOM sync, and events;
- `controllers_js/project.js` Unitizer bridge;
- `templates/controls/{unitizer,unitizer_modal}.htm`;
- `routes/nodb_api/unitizer_bp.py`; and
- focused render, Jest/Node, route, NoDb, and builder evidence.

## Compatibility and Parameterization

SHR-05 does not change category names, unit tokens, formulas, precision,
defaults, endpoint paths, response shapes, or stored keys. Such a change would
require an operator-approved contract checkpoint and, for parameterization, an
ADR before implementation.

## Acceptance

Direct rendering proves identities, values, checked state, labels, modal
lifecycle, and complete category coverage. Browser tests prove global/category
selection, numeric/label updates, complete payloads, events, and failures.
Route/NoDb tests prove filtering, persistence, and reload. Generated-map parity,
focused suites, controller build when applicable, frontend lint/test,
documentation lint, and `git diff --check` pass.

## Outcome

SHR-05 verified the rendered, client, Project, route, generated-map, and NoDb
preference path. It repaired mixed-state global selection, the client global
selector, obsolete bootstrap lookup, and duplicate legacy shell event
ownership. Conversion formulas, precision, defaults, stored keys, endpoint
behavior, and authorization remain unchanged.
