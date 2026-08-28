# Controller Contract

> **See also:** [`controllers_js/README.md`](../../wepppy/weppcloud/controllers_js/README.md) for bundling and architecture.

## What “contract” means
- Controllers are singletons that must stay idempotent across page reloads, mods-menu toggles, and Playwright `playwright_load_all` runs.
- DOM wiring, status streaming, and error surfacing must be resilient when sections are added/removed at runtime.
- Requests must be run-scoped and use the shared helpers so telemetry, CSRF, and error handling stay consistent.

## Required behaviors

### Singleton + bootstrap
- Export `getInstance()`; never allow `new`.
- Implement `bootstrap(context)` and make it safe to call multiple times: re-query DOM nodes, rebind delegates only when missing, and no-op if the section is absent.
- Context contains `run`, `mods`, `jobIds` (RQ job_id map), and `flags.playwrightLoadAll` when Playwright forces all controllers on.

### DOM + panels
- Pure templates must render:
  - form with stable id (e.g., `#landuse_form`)
  - status panel: `data-status-panel` with `data-status-log`
  - stacktrace panel: `data-stacktrace-panel` and inner `data-stacktrace-body`
  - job hint: `data-job-hint` element near the command button
- Controllers must store panel references (`statusPanelEl`, `stacktracePanelEl`, `hint`) and pass them into `attach_status_stream` so status, job info, and stacktraces render correctly.

### Status stream + stacktrace
- Always call `attach_status_stream` with `channel`, `runId`, `spinner`, and `stacktrace: { element, body? }`.
- StatusStream will enrich stacktraces via `/rq-engine/api/jobinfo/<jobid>` when the channel message includes an RQ job id (`rq:<uuid> ...`). Keep the `data-stacktrace-*` hooks intact or enrichment will fail silently.
- Prefer `pushResponseStacktrace`/`pushErrorStacktrace` for synchronous failures; rely on StatusStream for RQ errors.

### Polling completion + failure (redundant trigger path)
- **Required for RQ controllers**: completion must be driven by **both** StatusStream triggers and polling (`set_rq_job_id` fallback). This redundancy is intentional; completion handlers must be idempotent.
- On successful queue:
  - Set `poll_completion_event` before calling `set_rq_job_id`.
  - Reset `_completion_seen = false` to allow the next completion to fire once.
- `controlBase` dispatches:
  - `poll_completion_event` + `job:completed` once on `finished` (guarded by `_job_completion_dispatched`).
  - `job:error` once on `failed`/`stopped`/`canceled`/`not_found` (guarded by `_job_failure_dispatched`), after fetching `/rq-engine/api/jobinfo/<job_id>` to push stacktraces (child `exc_info` preferred).
- Custom `onTrigger` handlers must **not** call `triggerEvent` again; `attach_status_stream` already does this. Use guarded handlers for CustomEvents to avoid recursion.
- **See also:** [trigger-refactor.md](../mini-work-packages/completed/trigger-refactor.md) for the per-controller trigger inventory and completion event names.

### Requests
- Use `WCHttp` and `url_for_run()` for every in-run endpoint (`rq-engine/api/*`, `tasks/*`, `query/*`, `resources/*`). Never hardcode `/weppcloud/...` or bare paths.
- Include `form` when posting FormData so CSRF tokens are attached automatically.

### Project-config run authority and refresh

- Landuse, soil, and climate controls MUST render the resolved run authority
  supplied by the server. Their controller payloads MUST submit the same stable
  IDs; frontend catalogs MUST NOT broaden the server graph.
- A persisted current value outside authority renders once as disabled current
  state while every authorized recovery choice remains operable. An exact-
  current rebuild may proceed; selecting a different unsupported value must
  surface the server's diagnostic refusal.
- The project-config update panel supports additive, capability-refresh, and
  combined previews. It MUST render every delta row and preserved project
  selection supplied by preview; availability alone MUST NOT expose or invent
  the delta.
- Capability refresh MUST show the server-provided exact versioned warning next
  to a programmatically labeled, initially unchecked checkbox. Apply stays
  disabled until checked. The checkbox resets on preview load, stale/error,
  modal close, and success, and MUST NOT persist in local/session storage.
- Apply payload shape follows preview: always `preview_id`; additive trigger
  only when additions exist; acknowledgment only when a capability delta
  exists. The controller MUST NOT retain an acknowledgment across a new
  preview ID.
- After terminal job failure, the controller rechecks availability and compares
  preview prior/resulting digests with `current_digest` and `last_update`. It
  announces exactly `not applied`, `committed/recovered`, or an explicit
  indeterminate diagnostic instead of hiding a recovered commit behind a
  generic failure.
- An exact latest-preview idempotent HTTP 200 result is terminal success and
  MUST NOT start polling for a nonexistent new job. HTTP 202 continues through
  the normal redundant StatusStream/poll path.

### Field identity and round trip

- DOM `id`, submitted `name`, option token, parser key, persisted attribute, and
  reload value are distinct contract values. Never assume that matching one
  proves the others.
- Tests for template- or macro-defined controls must inspect actual rendered
  HTML. Hand-authored Jest DOM is useful for controller logic but cannot prove
  the production submitted name or selected/default state.
- A field or action is risk-bearing when its rendered value or use can change a
  submitted payload, persisted or reloaded state, queued work, or visible
  workflow state. Record any reviewed field/action excluded from that set and
  the reason in the controller package or field matrix.
- For each risk-bearing field, test only the downstream seams it reaches:
  serialization, route parsing, persistence/reload, and RQ input/lifecycle where
  applicable.
- When a mismatch is found, retain a failing regression before the production
  repair when practical, then make the smallest backward-compatible patch.
- Do not combine mismatch repair with refactoring, redesign, new defaults,
  compatibility changes, or unrelated shared-helper cleanup.

### Events
- Expose `controller.events = WCEvents.useEventMap([...])` for internal listeners and tests.
- Still call `controlBase.triggerEvent(...)` when legacy consumers require it, but keep new logic on the event map.

### Dynamic mods handling
- If a controller can be loaded when its section is hidden, guard eager code paths:
  - Re-query critical elements inside `bootstrap`.
  - Short-circuit actions when `form`/panels are missing.
  - Keep delegates in arrays and avoid re-registering once set.
- Tests (Jest/Playwright) rely on this to toggle mods on the fly without reloading the page.

### Job hints
- `controlBase.set_rq_job_id` will set and render hints if `hint` points at a `data-job-hint` element. Do not clear hints in `reset_panel_state` when `rq_job_id` is set—rely on the control_base guard instead.
- **Hydrate on load:** In `bootstrap(context)` always look up the last job id from (in order) `WCControllerBootstrap.resolveJobId(ctx, "<rq_key>")`, `controllerContext.job_id`, and `ctx.jobIds.<rq_key>`, then pass it to `set_rq_job_id`. This keeps the job link visible after page reloads or mod toggles.
- Route bootstrap payloads should serialize persisted controller job hints into `context.controllers.<name>.job_id` and `context.controllers.<name>.job_key` when available (for example, `controllers.wepp.job_id` / `controllers.wepp.job_key` sourced from NoDb state) so reload hydration still works if Redis job-id hints are absent and completion semantics remain correct.
- **Bootstrap IDs are not active locks:** `context.jobIds` and controller `job_id` hints are last-known metadata only. Do not set domain-specific active-task latches (or disable queue buttons) from bootstrap hints alone.
- **Authority order for "is active":**
  - queue/post response contract (`202 Accepted` + new `job_id`, or conflict status from server),
  - domain status endpoint (for controllers that expose one),
  - `/rq-engine/api/jobstatus/<job_id>` polling state.
- **Stale-lock reconciliation:** if a local active-task latch exists when the user queues work, reconcile once with the authoritative status endpoint before rejecting the action. If status is terminal/non-running (`finished`, `failed`, `stopped`, `canceled`, `not_found`, `idle`), clear the stale local latch and retry queueing once.
- **Deferred is replaceable:** `deferred` must never disable a controller command
  or require the user to find a separate cancellation action. Display the old
  job status/link, stop indefinite polling, and permit an ordinary submission.
  The server owns cancellation and dependency detachment of the superseded
  deferred job before it records the replacement. `queued`, `started`, and
  `scheduled` retain their existing active/disabled behavior.
- **Split hint vs. status:** Reserve the job hint element for the RQ dashboard link only. Use a separate `<p>` in the status panel meta (e.g., `#<control>_message`) for human-readable status/errors so the link is never overwritten by `"py/state"` or other payloads.
- **Clear before enqueue:** When handling a run click, immediately clear status text and stacktrace content before posting so stale errors disappear. Do not clear the job hint if a job id is present—`set_rq_job_id` will refresh it.

## Minimal template skeleton
```html
<form id="foo_form">
  <!-- inputs/buttons -->

  <div id="foo_status_panel" data-status-panel>
    <div data-status-log></div>
  </div>

  <div id="foo_stacktrace_panel" data-stacktrace-panel hidden>
    <div data-stacktrace-body></div>
  </div>

  <p id="hint_build_foo" data-job-hint class="wc-job-hint wc-text-muted"></p>
</form>
```

## Testing notes
- Jest: stub `controlBase` with `reset_panel_state`, `set_rq_job_id`, `pushResponseStacktrace`, and `attach_status_stream`.
- Playwright: `controller-regression` assumes stacktrace bodies exist and job hints are populated (or deliberately empty for controllers that don’t surface hints). Ensure selectors in templates match the cases listed in `static-src/tests/smoke/controller-cases.js`.
- Work through one controller at a time. Begin with direct actual-render and
  focused downstream assertions.
- Extract a test helper only after at least two tests repeat the same logic. A
  helper must be stateless, smaller than the tests using it, and make the exact
  field mapping visible in failures.
- Run cheap render, syntax, lint, and focused tests before existing broad
  frontend, Python, or RQ suites.
- Do not create a registry, manifest, change classifier, dependency engine, or
  CI workflow merely because the controller inventory is large.

Keep this contract lean—controllers and templates should stay predictable so status streaming, stacktraces, and job hints behave the same everywhere.

**Status panels MUST use `aria-live="polite"` for screen reader announcements.**

## Migration Checklist

When modernizing a controller:

- [ ] Replace jQuery with `WCDom`, `WCHttp`, `WCForms`
- [ ] Use delegated events on data attributes
- [ ] Implement re-query pattern in `bootstrap()`
- [ ] Treat bootstrap `jobIds` as hints only; do not infer active jobs from them
- [ ] Reconcile custom active-task latches against server status before blocking queue actions
- [ ] Test dynamic loading scenario
- [ ] Add Jest unit tests
- [ ] Add Playwright regression test
- [ ] Document DOM contract in controller README
- [ ] Update `controllers_js/README.md` reference section

## Anti-Patterns

### ❌ Don't

**Query DOM only in createInstance():**
```javascript
function createInstance() {
    var form = dom.qs("#form"); // May be null!
    return { form: form };
}
```

**Use inline event handlers:**
```html
<button onclick="controller.submit()">Submit</button>
```

**Make multiple XMLHttpRequest without WCHttp:**
```javascript
var xhr = new XMLHttpRequest();
xhr.open('POST', '/tasks/something');
```

**Skip bootstrap re-query:**
```javascript
controller.bootstrap = function(context) {
    // Assumes elements exist - fails for dynamic loading!
    controller.form.addEventListener(...);
};
```

### ✅ Do

**Query lazily or re-query in bootstrap:**
```javascript
controller.bootstrap = function(context) {
    if (!controller.form) {
        controller.form = dom.qs("#form");
    }
};
```

**Use delegated events:**
```javascript
dom.delegate(container, "click", "[data-action='submit']", handleSubmit);
```

**Route through WCHttp:**
```javascript
WCHttp.postJson(url_for_run("tasks/something"), payload);
```

**Always check element existence:**
```javascript
if (controller.form) {
    controller.form.reset();
}
```

## Further Reading

- [`controllers_js/README.md`](../../wepppy/weppcloud/controllers_js/README.md) - Architecture and bundling
- [`dynamic-mod-loading-patterns.md`](../dev-notes/dynamic-mod-loading-patterns.md) - Deep dive on dynamic loading
- [`ui-style-guide.md`](ui-style-guide.md) - UI patterns and templates
- [AGENTS.md](../../AGENTS.md#front-end-development) - Front-end development section
