# Deliver the optional one-page project config builder

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

An authenticated user can choose the registered project components on one
accessible page, review the exact combination resolved by the server, and
create a project that opens at its fixed `/config/` location. Existing named
Interfaces remain an independent project-creation path.

## Progress

- [x] (2026-08-26 22:40 UTC) Verify the ratified PC-13 contract, WP05/WP06 APIs, Interfaces route, browser token bridge, and frontend conventions.
- [x] (2026-08-26 22:40 UTC) Scaffold the package and record compatibility, security, and accessibility plans.
- [x] (2026-08-26 23:08 UTC) Publish registered component constraints in the authenticated builder description.
- [x] (2026-08-26 23:08 UTC) Implement the route, one-page semantic template, and helper-based controller.
- [x] (2026-08-26 23:08 UTC) Add server, DOM, dependency, error, duplicate-submit, and accessibility regression tests.
- [x] (2026-08-26 23:08 UTC) Run gates and complete correctness, security, accessibility, and documentation review.

## Surprises & Discoveries

- WP06 returns stable component IDs and labels but not their constraint sets;
  authoritative dependent filtering requires an additive description field.
- `WCHttp.getRqEngineToken()` already mints a short-lived user JWT through a
  same-origin POST, so the builder needs no new credential or CSRF mechanism.
- The documented host-side bundle command lacked Jinja in the host interpreter;
  running the same builder inside the WEPPcloud container succeeded.
- The smoke suite forced an HTTPS proxy header even for an explicit HTTP target,
  causing a CSRF referrer mismatch. Deriving the header from the target URL made
  local and HTTPS targets consistent.
- At 640 pixels, the shared theme selector overflowed before the existing
  540-pixel header breakpoint. Page-scoped responsive constraints resolved it.

## Decision Log

- Decision: add `/config-builder/` to the existing site blueprint and link it
  from Interfaces while leaving all Interfaces forms untouched.
  Rationale: the contract requires a distinct optional path and explicitly
  prohibits replacing or reinterpreting Interfaces.
  Date/Author: 2026-08-26, Codex.
- Decision: extend each builder component description with its registered
  constraints rather than hard-code the current continental-US matrix in JS.
  Rationale: dependent choices must remain server-described as the registry
  grows.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

WP07 delivered the optional authenticated one-page Config Builder without
changing named Interfaces. The browser consumes registered constraints, uses
the canonical token bridge, renders only server validation review data, and
guards stale and duplicate creation. All required reviews and complete test
gates passed. A small tooling improvement remains desirable: document the
container-safe controller bundle command and make the Playwright target printed
by `wctl` more prominent before execution.

## Context and Orientation

`wepppy/microservices/rq_engine/builder_routes.py` owns authenticated builder
description, validation, and creation. `wepppy/nodb/config_builder/schema.py`
defines its immutable vocabulary. `wepppy/weppcloud/routes/weppcloud_site.py`
renders `/interfaces/` and will render the new page. The browser helper
`wepppy/weppcloud/controllers_js/http.js` mints and caches an rq-engine JWT;
the new `config_builder.js` controller will use it without composing config.
The generated `controllers-gl.js` bundle is rebuilt from controller sources.

## Plan of Work

First add serialized constraint metadata to component summaries and prove the
description remains deterministic. Add an authenticated Flask page with one
semantic form: locale, DEM, derived cell size, backend, representation, soil,
land use, climate, optional mods, review, error summary, and live status.
Implement a controller that loads the schema, filters from locale constraints,
visibly clears invalidated selections, validates the complete proposal, renders
only server review data, and submits once with a cryptographically generated
idempotency key. On stale schema it reloads and requires review; on success it
navigates to the returned location.

Add Jest tests for stable values, dependencies, ordinary/privileged cell size,
review parity, focus/announcements, stale refresh, retained selection, and
duplicate submission. Add Flask/template tests for authentication, the distinct
entry point, programmatic labels, error relationships, and unchanged Interfaces
forms. Rebuild the controller bundle and capture correctness, accessibility,
and high-security reviews.

## Concrete Steps

Work from `/home/workdir/wepppy`. Iterate with `wctl run-npm lint`, focused Jest,
and focused pytest. Rebuild using
`python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`. Finish with
the complete npm suite, relevant WEPPcloud tests, stub gates when surfaces
change, documentation lint, broad-exception enforcement, and
`wctl run-pytest tests --maxfail=1`.

## Validation and Acceptance

The rendered page must remain one-column and usable at narrow widths and 200
percent zoom. Every control has a visible label, help, and error association;
dynamic changes use live regions without surprise focus movement. A failed
validation focuses a linked summary, while submission focuses status and
disables Create. The review matches the validation JSON exactly. A successful
response identifies the run and navigates to its server location ending in
`/config/`. Interfaces tests continue asserting established config tokens.

## Idempotence and Recovery

Schema and validation requests are read-only. The creation key is stable for
one reviewed attempt and changes only after the proposal changes or the schema
is refreshed. Repeated active clicks are ignored. The WP06 writer remains
default-off and owns all allocation cleanup. Removing the new link, route,
template, controller, and additive constraint field restores the prior UI.

## Artifacts and Notes

Record focused and full validation counts, keyboard/focus assertions,
responsive inspection, and review dispositions under this package's
`artifacts/` directory.

## Interfaces and Dependencies

No external dependency is added. Use existing Flask-Login, Jinja, Pure CSS,
`WCDom`, `WCEvents`, and `WCHttp`. Browser payloads contain exactly
`registry_revision`, `selections`, and, for creation,
`creation_idempotency_key`. The fixed token and filename remain response-only.

Plan revision note (2026-08-26): initial executable plan.
