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
- StatusStream will enrich stacktraces via `/rq/api/jobinfo/<jobid>` when the channel message includes an RQ job id (`rq:<uuid> ...`). Keep the `data-stacktrace-*` hooks intact or enrichment will fail silently.
- Prefer `pushResponseStacktrace`/`pushErrorStacktrace` for synchronous failures; rely on StatusStream for RQ errors.

### Polling completion + failure (redundant trigger path)
- **Required for RQ controllers**: completion must be driven by **both** StatusStream triggers and polling (`set_rq_job_id` fallback). This redundancy is intentional; completion handlers must be idempotent.
- On successful queue:
  - Set `poll_completion_event` before calling `set_rq_job_id`.
  - Reset `_completion_seen = false` to allow the next completion to fire once.
- `controlBase` dispatches:
  - `poll_completion_event` + `job:completed` once on `finished` (guarded by `_job_completion_dispatched`).
  - `job:error` once on `failed`/`stopped`/`canceled`/`not_found` (guarded by `_job_failure_dispatched`), after fetching `/rq/api/jobinfo/<job_id>` to push stacktraces (child `exc_info` preferred).
- Custom `onTrigger` handlers must **not** call `triggerEvent` again; `attach_status_stream` already does this. Use guarded handlers for CustomEvents to avoid recursion.
- **See also:** [trigger-refactor.md](../mini-work-packages/completed/trigger-refactor.md) for the per-controller trigger inventory and completion event names.

### Requests
- Use `WCHttp` and `url_for_run()` for every in-run endpoint (`rq/api/*`, `tasks/*`, `query/*`, `resources/*`). Never hardcode `/weppcloud/...` or bare paths.
- Include `form` when posting FormData so CSRF tokens are attached automatically.

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
- **Hydrate on load:** In `bootstrap(context)` always look up the last job id from (in order) `WCControllerBootstrap.resolveJobId(ctx, "<rq_key>")`, `controllerContext.jobId`, and `ctx.jobIds.<rq_key>`, then pass it to `set_rq_job_id`. This keeps the job link visible after page reloads or mod toggles.
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

Keep this contract lean—controllers and templates should stay predictable so status streaming, stacktraces, and job hints behave the same everywhere.

**Status panels MUST use `aria-live="polite"` for screen reader announcements.**

## Migration Checklist

When modernizing a controller:

- [ ] Replace jQuery with `WCDom`, `WCHttp`, `WCForms`
- [ ] Use delegated events on data attributes
- [ ] Implement re-query pattern in `bootstrap()`
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
