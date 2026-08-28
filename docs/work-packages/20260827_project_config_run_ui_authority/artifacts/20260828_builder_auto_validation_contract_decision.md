# Builder Automatic Validation Contract Decision

## Amendment identity

`PC-13/WP12D-20260828-6`

This is a bounded cross-owner enhancement carried by active WP12D after its
Forest handoff. It changes only the Config Builder validation interaction owned
by WP07/PC-13. WP12D is only the active carrier. This amendment does not advance
or close WP07, PC-13, WP12D, or WP12; merge and production remain reserved to
WP12. It does not change any registry, validation, creation, authentication,
configuration, or stored-graph contract.

## Starting point and authority

- Starting implementation revision:
  `b772877c443ae21697a4eed5d51827cc806afc52`.
- Applicable canonical contract:
  `docs/schemas/project-owned-config-contract.md`, section 7.4,
  "Validation and review".
- Operator approval: on 2026-08-28 the operator asked whether the redundant
  Review Selections action could be removed in favor of the existing form-change
  validation plus one validation after options load. After the current behavior
  and edge cases were explained, the operator replied, "okay. please implement
  the removal and initial validation behavior."
- Bounded cross-owner ratification: at 2026-08-28 19:59 UTC the operator
  explicitly ratified this amendment exactly as documented, authorized WP12D to
  carry the WP07/PC-13 interaction change without advancing or closing WP07,
  PC-13, WP12D, or WP12, authorized the standalone checkpoint commit and
  subsequent implementation, and preserved WP12's exclusive merge and
  production authority.
- Implementation conformance: pending until the checkpoint is committed as an
  ancestor and the controller/template/test change passes review and validation.

## Exact normative delta

After a successful Builder-description response, the browser MUST finish
populating every select, applying the selected locale's registered defaults,
and resolving dependent options before it automatically validates the complete
proposal. Each subsequent user-originated `change` event MUST continue to
invalidate the prior review and automatically validate the resulting complete
proposal after dependent options have settled.

The Config Builder MUST NOT present a general-purpose Review Selections button.
The server-resolved Review configuration summary remains mandatory and Create
remains disabled until the latest complete proposal validates successfully.

A stale-registry reload MUST follow the same hydration-and-automatic-validation
path. Initial and change-triggered validation, whether successful or failed,
MUST not move focus. Validation errors retain the existing linked page summary,
field associations, live announcement, and selection preservation.
A user can retry a failed unchanged initial proposal by reloading the page; any
subsequent form change also starts a new validation. This amendment does not add
a new retry control.

Only the validation response for the latest proposal under the latest completed
Builder-description load may render a review or errors or enable Create. Starting
a description load invalidates every earlier validation response and temporarily
disables the selection controls. A stale reload preserves each still-registered
selection. When a prior selection is no longer registered or compatible, the
browser applies that field's current registered default, visibly explains the
replacement, and validates only after every replacement has settled. A failed
description reload retains its diagnostic and starts no validation; a failed
post-reload validation retains its own diagnostic and disabled Create state.

## Rationale

The Review Selections button invokes the same server validation already invoked
by every form change. Its only unique normal-path role is compensating for the
fact that programmatic option and default assignment does not emit a browser
`change` event. Running validation once after hydration removes that artificial
extra step while preserving the actual review: the exact server-resolved
summary that gates Create.

## Valid-state and compatibility matrix

- Before the Builder description exists, controls and Create remain unavailable.
- While options are loading or validation is pending, Create remains disabled.
- A successfully hydrated complete proposal automatically validates once.
- A successful latest validation renders the server review and enables Create.
- A user change clears the prior review, resolves dependencies, and validates
  the new complete proposal.
- An invalid proposal preserves selections and exposes linked field/page errors;
  Create stays disabled.
- A transport or server failure remains diagnostic and non-mutating; a form
  change or page reload retries validation.
- A stale registry response reloads options and validates the refreshed complete
  proposal before Create can become available.
- A description rejected by the existing hydration boundary starts no validation
  or creation. That boundary is unsupported description schema version, absent
  locale-keyed component or graph maps, a locale population missing its matching
  locale component/graph, or a dependency-rendering failure. Other graph and
  combination validity remains owned by the authenticated server validator; this
  amendment does not add a second browser schema validator.
- Overlapping validation is valid browser state. A later proposal invalidates
  every earlier response, so only the latest response may render or enable
  Create. Starting any description reload invalidates all validation responses
  from the prior registry revision and disables selection changes until the load
  succeeds or fails.

Existing named Interfaces, existing run projects, Builder payload schemas,
server routes, tokens, registry identities, stored graph identities, and project
creation semantics are unchanged. The only additional normal request is one
read-only validation immediately after a successful Builder-description load.

## Security and data impact

Security impact is low. The change reuses the authenticated validation endpoint,
token bridge, complete payload, and stale-response sequence guard. It adds no
input, authorization path, persistence, filesystem access, queue operation, or
dependency. Validation remains read-only and Create remains fail-closed.

There is no project data or schema mutation and no migration or compatibility
burden.

## Exact implementation boundary

- `wepppy/weppcloud/controllers_js/config_builder.js`
- `wepppy/weppcloud/templates/config_builder.htm`
- `wepppy/weppcloud/controllers_js/__tests__/config_builder.test.js`
- `wepppy/weppcloud/controllers_js/README.md`
- `wepppy/weppcloud/static/js/controllers-gl.js` as the generated bundle
- `tests/weppcloud/routes/test_config_builder_ui.py`
- `docs/schemas/project-owned-config-contract.md`
- this decision artifact
- `artifacts/20260828_builder_auto_validation_correctness_review.md`
- `artifacts/20260828_builder_auto_validation_governance_review.md`
- the active WP12D ExecPlan and tracker

Excluded are backend routes, payloads, registry data, NoDb, RQ, feature flags,
deployment, merge, production, and every project configuration or manifest.

## Proposed regression evidence

- A focused controller test proves initialization performs exactly one describe
  request followed by one validation request, renders the returned review, and
  enables Create without a click.
- Existing change-event coverage proves a changed value still validates after
  dependent options settle.
- A stale-registry test proves refreshed options automatically revalidate and do
  not leave the user waiting for a removed action.
- A controlled overlapping-request test proves a user change made while initial
  validation is pending supersedes the initial response: only the latest review
  can render or enable Create.
- A change-during-stale-reload test proves controls are disabled, every old-
  revision validation result is ignored, still-valid choices are preserved,
  invalidated choices use current registered defaults, and validation uses only
  the refreshed revision.
- Initial validation success and failure tests prove focus remains on the
  previously focused element while the alert/live regions expose the result.
- Unsupported-version, absent-map, missing-locale-authority, and dependency-
  rendering failures prove zero validation requests; an initial validation
  failure proves a later form change retries it. Stale description-load and
  refreshed-validation failures retain their exact diagnostic and disabled
  Create state.
- Template/controller assertions prove no Review Selections control or dead
  selector remains.
- Focused Jest, frontend lint, bundle rebuild, relevant template pytest, and
  scoped documentation lint pass.
