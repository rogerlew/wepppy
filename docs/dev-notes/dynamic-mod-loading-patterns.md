# Dynamic Mod Loading Patterns and Pitfalls

Use this checklist whenever adding a run-page control selectable from **Mods**.
The [shared controller contract](../ui-docs/controller-contract.md#dynamic-mods-handling)
and [feature registry specification](../../wepppy/weppcloud/feature_registry/specification.md)
are authoritative. Registering a feature or rendering its template on page load
alone does not complete its integration.

## Required integration checklist

Paths below are relative to `wepppy/weppcloud/`.

| Surface | Required wiring |
| --- | --- |
| `feature_registry/feature_registry.yaml` | Register the exact mod id, section id/template, eligibility, and declared enable dependencies. |
| `routes/run_0/run_0_bp.py` | Supply full-page and dynamic-fragment context, including the enabled/visible flag. Handle a never-used module without assuming persisted optional state exists. The existing `view/mod/<mod_name>` path renders the fragment. |
| `routes/run_0/templates/runs0_pure.htm` | Keep `data-mod-nav="<mod_id>"` and `data-mod-section="<mod_id>"` placeholders in the initial DOM for selectable mods, even when disabled. Hide the wrappers; conditionally include only their control contents. |
| `routes/run_0/templates/run_page_bootstrap.js.j2` | Register initialization for a control already enabled when the page loads. |
| `controllers_js/project.js` | Add the controller to `MOD_BOOTSTRAP_MAP`; dynamic enabling does not rerun page bootstrap. Use `forceRemount: true` when the controller caches the replaced form. |
| `controllers_js/project.js` state reconciliation | Check `MOD_STICKY_FALSE_FLAGS` for server visibility gates and `MOD_ENABLE_PROPAGATION` for declared dependencies. Only explicitly enabled or server-confirmed dependencies may become visible; preserve unrelated eligibility gates. |
| `controllers_js/<controller>.js` | Export the expected window symbol and idempotent `bootstrap`; re-query the current form or provide `remount` that releases the old instance before binding the new one. |
| Controller bundle | Confirm the source is included by `build_controllers_js.py`, rebuild the served bundle, then verify the browser loads it. |

Keep the mod id consistent across registry, `data-*` attributes, visibility flags,
fragment requests and bootstrap mapping. The section anchor may differ from the
mod id, but its navigation link must match. Put navigation and control sections
in the same agreed workflow order, with prerequisite controls before consumers.
`enable_dependencies` remains server-owned registry policy; client propagation
must reflect that policy rather than inventing extra dependencies.

## Persistent placeholders

Adapt this structure to the feature's agreed layout and eligibility rules:

```jinja
<li data-mod-nav="example" {% if not show_example %}hidden{% endif %}>
  <a href="#example-control" class="nav-link">Example</a>
</li>

<div data-mod-section="example" {% if not show_example %}hidden{% endif %}>
  {% if show_example %}
  <section id="example-control" class="wc-stack">
    {% include 'controls/example_pure.htm' %}
  </section>
  {% endif %}
</div>
```

Do not enclose the entire placeholder in `{% if show_example %}`. A never-enabled
mod would then have no insertion target. The dynamic fragment supplies the inner
section/form; it must not duplicate the outer `data-mod-section` wrapper. Empty
wrappers contain no protected state and do not replace server authorization.

## Bootstrap after insertion and after replacement

The Project controller persists the selection, fetches `view/mod/<mod_id>`,
inserts its HTML, then calls the mapped controller bootstrap. Both placeholders
and the mapping must exist. `DOMContentLoaded` and full-page bootstrap are not
repeated when the checkbox changes.

An `innerHTML` assignment makes its nodes queryable synchronously. Missing
containers, omitted bootstrap hooks, and stale singleton references are wiring
problems; adding timeouts cannot repair them. Preserve the Project controller's
existing scheduling, but do not add delays as a substitute for the checklist.

A cached form can be non-null yet detached after disable/re-enable. Re-query
against the current DOM or remount; a null-only guard is insufficient. For a
controller that owns cached form references, the bootstrap-map entry follows:

```javascript
example: function (ctx) {
    bootstrapControllerSymbol(window.Example, ctx, { forceRemount: true });
}
```

`Example.remount()` must actually exist for this path to recreate the instance.
Release old delegates, document listeners, timers and status streams, and cancel
or invalidate asynchronous callbacks owned by the removed form. Bind actions
once to the replacement form, then refresh authoritative state. Repeated
bootstrap calls against the same form must not duplicate listeners or requests.
Absent forms must not cause eager initialization failures.

## Required validation

Start with an eligible project where the mod is **off and has never been used**.
A browser check that starts with the mod already enabled misses this defect.

1. Render the actual run template with the mod disabled. Assert both hidden
   placeholders exist and the optional form is absent; check section/nav order.
2. Exercise `Project.set_mod` with fragment loading in Jest. Assert the form is
   inserted before the mapped controller bootstraps, the navigation is visible,
   and declared newly enabled dependencies are shown without changing unrelated
   visibility gates. A controller-only fixture with a preinserted form cannot
   prove this integration.
3. Test replacement: disable, re-enable, and interact with the new form. Verify
   readiness/data refresh and handlers use the replacement nodes; old callbacks
   and listeners must not update or submit from the detached form.
4. In an authenticated browser on a disposable eligible project, use the actual
   **Mods checkbox**. Without reloading, verify the visible form, navigation,
   prerequisite order, readiness response and a working action. Then disable,
   re-enable, exercise an action again, and reload to verify persisted selection.
   Calling the API or manually inserting HTML alone is not this smoke test.
5. Check unavailable/unauthorized/readonly states against the feature contract;
   hidden placeholders must not expose content or authorize mutations. Include
   previously populated state where the control hydrates saved results.

Use `controllers_js/__tests__/project.test.js` for Project integration and the
controller's own Jest suite for remount behavior. Use paired route/template tests
for server rendering and eligibility. Run the relevant frontend gates and rebuild
through the [frontend change checklist](frontend-change-checklist.md).

## Diagnostic order

If selecting a mod has no visible effect, inspect the initial placeholder first,
then the `set_mod` response and persisted list, the fragment response, the
bootstrap-map entry, and finally the controller's current form reference.
Reloading successfully proves only the separate full-page path.

The [Post-fire debris-flow repair](20260910_postfire_control_mount.md) records a
concrete recurrence: missing placeholders and mapping prevented first activation;
remounting and dependency propagation completed the dynamic path.
