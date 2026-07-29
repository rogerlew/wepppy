# SURF-09 Pure UI README Editor Contract

**Status**: Verified
**Package ID**: SURF-09
**Security impact**: `high`
**Dedicated security review**: required if a production patch changes the
authenticated mutation, path, concurrency, or rendered-Markdown surface

## Purpose

Verify the run-scoped README viewer and editor from authorized Flask hosts
through rendered content, preview, automatic and explicit save, multi-tab lock
invalidation, filesystem persistence, and reload.

## Concise Intent Contract

An authorized viewer can read the current run's `README.md`. Only a confirmed
owner or administrator can enter the editor or save. Readonly projects remain
view-only. The editor renders exact run-scoped endpoints and JSON-safe initial
state, previews Markdown without executable HTML, saves one string payload
inside the active run root, detects a stale tab before mutation, and reflects
saved content after reload. Mutation requests preserve the canonical browser
CSRF boundary.

The server retains run authorization, active-root selection, fixed
`README.md` confinement, editor-session TTL behavior, explicit validation,
safe Markdown/Jinja rendering, and clear error responses. Redis unavailability
fails editor coordination closed with HTTP 503 and never widens authorization
or path scope. Jinja support is deliberately limited to non-amplifying variable
interpolation.

## Scope

- `routes/readme_md/readme_md.py`;
- `readme_editor.htm`, `readme_view.htm`, and the default Markdown template;
- shared browser CSRF behavior as an exercised consumer;
- Redis editor lock/session state;
- fixed run-root README persistence and reload; and
- direct render, executable inline-client, route, filesystem, and security
  tests.

## Exclusions

No general file editor, arbitrary path input, Markdown feature redesign,
shared transport redesign, Redis topology change, run ownership policy change,
or generated controller-bundle change is authorized.

## Acceptance

Actual rendering proves editor/view actions, initial values, fixed URLs,
readonly behavior, lock targets, and safe bootstrap. Executing the real inline
script proves debounce, preview, Ctrl+S, CSRF-compatible fetch, lock
invalidation, server response handling, and reload. Route tests prove
authorization, ownership, readonly mutation denial, fixed-path persistence,
safe rendering, concurrency, and reload.
