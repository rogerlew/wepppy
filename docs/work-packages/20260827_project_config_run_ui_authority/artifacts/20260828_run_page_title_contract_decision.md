# Run Page Title Contract Decision

## Amendment identity

`PC-13/WP12D-20260828-7`

This is a bounded cross-owner enhancement carried by active WP12D. It changes
only the established run page's server-rendered and live-mutated document-title
behavior owned by WP07/PC-13. It does not advance or close WP07, PC-13, WP12D,
or WP12, and it does not authorize a merge or production deployment outside the
parent WP12 gate.

## Starting point and authority

- Starting implementation revision:
  `5bb8676bb5b6dca2a71d9bb84f658f9bdf0811e6`.
- Applicable canonical contract:
  `docs/schemas/project-owned-config-contract.md`, new section 7.7, "Run page
  document identity".
- Observed discrepancy: `runs0_pure.htm` currently begins the document title
  with `ron.configname`. Project-owned configs may legitimately have no legacy
  config name, so Jinja renders the visible string `None`.
- Operator approval: on 2026-08-28 the operator directed, "the title for the
  runs page is defaulting to None instead of the config name. Let's change it to
  be the runid," then explicitly granted authority to implement and make the
  necessary contract changes.
- Exact amendment ratification: at 2026-08-28 23:06 UTC the operator explicitly
  ratified `PC-13/WP12D-20260828-7` exactly as documented, authorized WP12D to
  carry the bounded WP07/PC-13 run-page title change without advancing or
  closing WP07, PC-13, WP12D, or WP12, authorized the standalone checkpoint and
  subsequent exact-source implementation, and preserved WP12's exclusive merge
  and production authority.
- Implementation conformance: pending until this reviewed contract checkpoint
  is committed as an ancestor of the template and regression-test change.

## Exact normative delta

The established run page's HTML document title MUST be exactly the
route-resolved `runid` for the complete page lifetime. It MUST NOT derive title
content from `ron.configname`, a config token or filename, project display name,
scenario, locale, current nested/PUP controller identity, or stored capability
metadata. Saving or clearing a project display name or scenario MUST NOT mutate
the title. Missing metadata MUST NOT expose `None`, `Untitled`, or an empty
suffix.

## Rationale

The run ID is required route identity for every established run page and is
stable across named, project-local, and flattened project-owned configuration
modes. Config names, project display names, and scenarios are optional metadata
and are therefore unsuitable as document identity. One exact lifetime rule also
prevents later controller mutations from replacing the stable route identity.

## Valid-state and compatibility matrix

- Named-preset legacy run, populated `ron.configname`: title is exactly the
  `runid`; the config name is not rendered in the title.
- Project-local or flattened run, absent or `None` `ron.configname`: title is
  unaffected by that state and is exactly the `runid`.
- Absent, `None`, or empty project display name: title is exactly the `runid`.
- Populated, saved, or cleared project display name: title remains exactly the
  `runid`; name persistence and feedback remain unchanged.
- Populated, saved, or cleared scenario: title remains exactly the `runid`;
  scenario persistence and feedback remain unchanged.
- Nested/PUP state whose current controller identity differs from the parent
  route: title remains the exact route `runid`.
- Invalid or path-dangerous run IDs remain rejected by the existing route
  boundary. Every title value reaching HTML rendering remains autoescaped;
  HTML-significant title text is never interpreted as executable markup.
- Historical run files, config tokens, browser URLs, bookmarks, and stored
  provenance remain byte-for-byte unchanged.

This intentionally changes the browser title for every established run page
from config-first to run-ID-first identity. No migration or compatibility shim
is required because the title is derived at render time and is not persisted.

## Security and data impact

Security impact is low. The change uses the already-authorized, route-resolved
and autoescaped `runid` and removes optional metadata from the title. It adds no input,
authorization path, request, persistence, filesystem access, queue operation,
dependency, or telemetry field. There is no project data or schema mutation.

## Exact implementation boundary

- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
- `wepppy/weppcloud/controllers_js/project.js`
- `wepppy/weppcloud/controllers_js/__tests__/project.test.js`
- `wepppy/weppcloud/controllers_js/README.md`
- `wepppy/weppcloud/static/js/controllers-gl.js` as the generated bundle
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `docs/schemas/project-owned-config-contract.md`
- this decision artifact
- `artifacts/20260828_run_page_title_correctness_review.md`
- `artifacts/20260828_run_page_title_governance_review.md`
- the active WP12D ExecPlan and tracker

Excluded are routes, context construction, config resolution, NoDb, registry
data, payloads, RQ, authentication, feature flags, project files, deployment,
merge, and production. Project name/scenario persistence, request, event,
notification, and field-update behavior remains unchanged.

## Proposed regression evidence

- Render the actual `runs0_pure.htm` title block with a route `runid`,
  `ron.configname = None`, and no display name; assert the title is exactly the
  run ID and contains neither `None` nor a config token.
- Render the same title block with both a config name and a project display
  name, plus a differing nested/PUP controller identity; assert the title is
  still exactly the route `runid`.
- Render the actual title block under autoescape with HTML-significant title
  text; assert encoded markup and exact decoded browser text.
- Save and clear project names and scenarios through the Project controller;
  assert their existing field/event/notification behavior and an unchanged
  exact run-ID document title.
- Run focused Project Jest and run-control template suites, complete frontend
  lint/tests, the broader WEPPcloud route suite, bundle rebuild/parity, scoped
  documentation lint, and diff checks.
