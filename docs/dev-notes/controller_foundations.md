# Controller Modernization Foundations
> Long-term guidelines for reducing surface area across WEPPcloud controllers, routes, and NoDb singletons.

This note captures the shared architectural goals that sit behind the per-module refactor workflow. Treat it as a living document—update it whenever a controller migration uncovers new patterns or helper needs.

## 1. Shared UI primitives
- Promote repeatable view behavior into helper-friendly building blocks:
  - `data-*` conventions for buttons, toggles, and expanding rows (e.g., `data-action="run-job"`, `data-toggle-target`).
  - Lightweight utility functions that bridge `WCDom` with common control patterns (`bindRadioGroup`, `bindFormSubmit`, `toggleDetails`).
- Encourage controllers to surface domain signals through a scoped emitter (`WCEvents.createEmitter` + `useEventMap`) so other modules subscribe without reaching inside implementation details (for example, `landuse:build:completed`).
- Aim for each controller to focus on domain logic (payload preparation, NoDb syncing) while the primitives handle DOM wiring.
- Document these primitives alongside usage examples in `controllers_js/README.md` as new pieces are added.
- The ash controller refactor (2024) pairs delegated `data-ash-*` hooks with a scoped `WCEvents` emitter and serves as the reference implementation for helper-first run controls; link to it when introducing similar patterns.

## 2. Unified payload schemas
- Whenever a controller sends structured data, define the schema once and reuse it:
  - Route-level parsing should rely on `parse_request_payload`.
  - Follow up by co-locating dataclasses or validators (Pydantic, marshalled dicts) that describe expected fields and types.
  - Keep downstream NoDb helpers (`parse_inputs`, `set_*` methods) typed to native booleans/ints/floats—no `"on"` or `"1"` checks scattered around the codebase.
- Record schema notes in the domain-specific dev doc (e.g., landuse, wepp) so future migrations stay aligned.

## 3. Control base evolution
- Grow `controlBase` into a declarative job runner:
  - Provide APIs like `submitJob({ url, method, payload, status })` so controllers stop duplicating fetch + status + WebSocket wiring.
  - Offer convenience methods (`setStatus`, `appendStatus`, `clearStacktrace`) that write through to StatusStream or plain DOM automatically.
  - Emit lifecycle events via `WCEvents` (`job:started`, `job:completed`, `job:error`) so controllers attach behavior without monkey-patching `triggerEvent`.
- Ensure new helpers work with both legacy adapters (jQuery-like objects) and native elements/components.

## 4. Documentation alignment
- For every major controller domain, maintain a short “contract” doc:
  - Enumerate endpoints, payload schemas, emitted events, and unitizer hooks.
  - Reference the controller primitives used and any shared utilities.
- Project-specific requests/events live in `docs/dev-notes/project-controller-migration-plan.md`; keep it in sync whenever payloads or data hooks change.
- Update `controllers_js/AGENTS.md`, `controllers_js/README.md`, and the per-domain plan whenever new primitives or patterns ship.
- Tie these contracts back into the refactor workflow so contributors see the broader picture before coding.

## 5. Tooling expectations
- Lint and test quickly: `wctl run-npm lint`, `wctl run-npm test`, `wctl run-pytest …`.
- Keep helper modules thin and well-tested; add Jest suites whenever a primitive or controlBase feature is introduced.
- When introducing new patterns, stage them in one controller, document the contract here, then schedule follow-up work to roll them out broadly.

---

Use this note to guide architectural discussions and helper development. The module refactor checklist should reference this document so every migration reinforces the same controller baseline.
