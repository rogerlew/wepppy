# Controller Modernization Foundations
> Living architectural guide for WEPPcloud run controllers.

**Status:** Modernization complete. All run controllers now use vanilla helpers (`WCDom`, `WCEvents`, `WCHttp`, `WCForms`), emit lifecycle events via scoped emitters, and integrate with the unified `controlBase` + `StatusStream` telemetry pipeline. jQuery has been eliminated from the controller bundle.

This document captures the patterns, conventions, and principles established during the 2024–2025 modernization program. Use it as the reference when maintaining existing controllers or extending the system with new controls.

## 1. Vanilla Helper Infrastructure (Achieved)

**Core helpers** (`dom.js`, `events.js`, `http.js`, `forms.js`):
- All controllers now destructure from global namespaces: `const { qs, delegate, show, hide } = WCDom;`
- jQuery has been completely eliminated from the controller bundle
- Helpers provide unified DOM manipulation, event delegation, HTTP transport, and form serialization
- Every helper fails fast with descriptive errors when misused

**Template conventions**:
- Markup exposes `data-*` attributes for delegated event binding: `data-<controller>-action`, `data-<controller>-role`, `data-<controller>-field`
- Controllers wire behavior through `WCDom.delegate(root, selector, event, handler)` instead of inline event handlers
- Templates ship with semantic structure (`<form>`, proper labels, ARIA attributes) so controllers enhance progressively

**Event-driven architecture**:
- Every controller exposes a scoped emitter: `controller.events = WCEvents.useEventMap([...])` with domain-specific event names
- Controllers emit lifecycle signals (`<domain>:run:started`, `<domain>:run:completed`, `<domain>:config:loaded`, etc.) so downstream consumers subscribe without scraping DOM state
- Legacy `triggerEvent` hooks remain for backward compatibility but new integrations should use the event API

**Controller focus**:
- Controllers concentrate on domain logic: payload assembly, validation, NoDb coordination, and business rules
- DOM wiring, HTTP plumbing, and telemetry orchestration are handled by the helper stack and `controlBase`
- This separation keeps controllers testable and reduces duplication across the 25+ run controls

## 2. Unified Request/Response Contracts (Implemented)

**Payload parsing**:
- All controller routes call `parse_request_payload(request, trim_strings=True)` to normalize JSON and legacy form submissions
- Controllers post native types via `WCForms.serializeForm(form, { format: 'json' })` or `WCHttp.postJson(...)`
- NoDb `parse_inputs` methods now expect native booleans, ints, floats—never stringy truths like `"on"` or `"1"`
- File uploads use `FormData` bodies handled by `WCHttp.request` with automatic CSRF propagation

**Schema documentation**:
- Each controller has a contract document under `docs/work-packages/20251023_controller_modernization/notes/archived-plans/` that enumerates:
  - Request payloads (field names, types, validation rules)
  - Response formats (`success_factory`, `exception_factory`, resource GeoJSON)
  - Emitted events and their payload shapes
  - Integration points with other controllers
- Cross-reference these contracts in `wepppy/weppcloud/routes/nodb_api/README.md` (the NoDb API Blueprint Map)

**Type coercion boundaries**:
- Flask routes coerce request payloads to native types before calling NoDb methods
- NoDb controllers persist native types and serialize them through jsonpickle
- Front-end receives JSON responses with native types (booleans, numbers, nulls)
- This eliminates the `"on"`/`"off"` ambiguity that plagued the legacy codebase

## 3. ControlBase & Telemetry Pipeline (Operational)

**controlBase as orchestrator**:
- `controlBase()` provides declarative job management: status polling, spinner animation, RQ badge updates, error handling
- Controllers call `controlBase.attach_status_stream(form, channel, options)` once per form to wire StatusStream
- Job lifecycle flows through standardized events: `job:started`, `job:progress`, `job:completed`, `job:error`
- `controlBase` manages UI state (disabling buttons, showing spinners, clearing stacktraces) without per-controller duplication

**StatusStream integration**:
- `StatusStream` (`status_stream.js`) consumes the Redis Pub/Sub WebSocket feed via the `status2` Go service
- Controllers attach streams to `[data-status-panel]` markup; fabricated panels are created when templates only expose legacy shells
- Log messages appear in `[data-status-log]`, spinner animations in `[data-status-spinner]`, stacktraces in designated error areas
- WebSocket reconnection, backoff, and heartbeat monitoring are handled transparently
- The legacy `WSClient` has been removed; **do not reintroduce direct WebSocket wiring**

**Backward compatibility**:
- `controlBase.triggerEvent` still dispatches legacy DOM events (`BUILD_CLIMATE_TASK_COMPLETED`, etc.) for historical listeners
- Controllers continue to accept jQuery-wrapped elements via adapter shims, but new code should pass native elements
- The RQ job badge, status area, and stacktrace panels remain in their canonical locations for template compatibility

**Best practices**:
- Attach streams early (during controller initialization or bootstrap)
- Use the scoped event emitter for domain events; use `controlBase` events for cross-controller telemetry
- Let `controlBase` manage polling—don't implement custom interval loops
- Enrich errors with `controlBase.pushResponseStacktrace` or `appendStatus` for user-facing diagnostics

## 4. Controller Bootstrap Contract (Established)

**Bootstrap protocol**:
- Every controller now exposes an idempotent `bootstrap(context, meta)` method
- Page templates build a context object once (`run`, `user`, `mods`, `flags`, `map`, `jobIds`, `data`) and pass it to all controllers via `WCControllerBootstrap.bootstrapMany([...])`
- Controllers extract only the slices they need: `const climateData = (context.data && context.data.climate) || {};`
- Templates no longer poke controller internals directly—all initialization flows through the bootstrap interface

**Context structure**:
```javascript
{
  run: { runid, config, name, scenario, ... },
  user: { id, email, roles },
  mods: { hasDisturbed, hasBaer, hasRangeland, ... },
  flags: { readonly, isPublic, ... },
  map: { center, zoom, bounds },
  jobIds: { climate: 'uuid', wepp: 'uuid', ... },  // RQ job IDs
  data: {
    climate: { hasObserved, precipScalingMode, ... },
    watershed: { hasChannels, outletSet, ... },
    // per-controller hints
  },
  controllers: {
    climate: { defaultColorMap: 'viridis', ... },
    // per-controller overrides
  }
}
```

**Helper utilities**:
- `WCControllerBootstrap.setContext(context)` caches the context once per page load
- `WCControllerBootstrap.bootstrapMany(entries, context)` resolves controller singletons and invokes `bootstrap`
- `WCControllerBootstrap.resolveJobId(context, key)` extracts RQ IDs with fallback to null
- `WCControllerBootstrap.getControllerContext(context, name)` retrieves controller-specific overrides

**Testing considerations**:
- Jest tests stub `WCControllerBootstrap` or omit it entirely
- Controllers guard against missing helpers: `if (typeof WCControllerBootstrap !== 'undefined') { ... }`
- Always provide sensible defaults when context data is absent

## 5. Documentation & Maintenance Standards

**Per-controller contracts**:
- Every controller has a plan document under `docs/work-packages/20251023_controller_modernization/notes/archived-plans/<controller>-controller-plan.md`
- Each contract enumerates: endpoints, payload schemas, emitted events, DOM hooks, testing coverage, and integration points
- Cross-reference these plans in `wepppy/weppcloud/routes/nodb_api/README.md` (the NoDb API Blueprint Map)

**Comprehensive guides**:
- `wepppy/weppcloud/controllers_js/README.md` — architecture overview, bundling, migration patterns, controller references
- `wepppy/weppcloud/controllers_js/AGENTS.md` — AI agent playbook with workflow, testing, and per-controller quick references
- `docs/dev-notes/module_refactor_workflow.md` — step-by-step modernization checklist (scope → plan → implement → document → validate)

**When to update documentation**:
1. Adding a new controller or helper module
2. Changing payload schemas or event signatures
3. Introducing new `data-*` conventions
4. Modifying `controlBase` or StatusStream behavior
5. Discovering bugs or anti-patterns that need warning notes

**Maintenance workflow**:
- Update the contract doc alongside code changes (same commit)
- Refresh `README.md` and `AGENTS.md` when patterns evolve
- Add inline comments for non-obvious workarounds or legacy compatibility shims
- Keep `__all__` exports synchronized when refactoring module structure

---

## Achieved Patterns & Best Practices

### Helper Usage Patterns

**DOM manipulation**:
```javascript
const { qs, qsa, delegate, show, hide, toggle, toggleClass } = WCDom;

// Query
const form = qs('#climate_form');
const buttons = qsa('[data-action="run"]', form);

// Delegate events
delegate(form, '[data-climate-action]', 'click', handleAction);

// Visibility
show(panel);
hide(errorBox);
toggle(detailsSection, shouldExpand);
```

**HTTP transport**:
```javascript
const { request, getJson, postJson, postForm, HttpError } = WCHttp;

// JSON requests
const data = await getJson(url_for_run('query/status'));
await postJson(url_for_run('tasks/set_mode'), { mode: 2 });

// Form submissions
const payload = WCForms.serializeForm(form, { format: 'json' });
await postJson(url_for_run('rq/api/build'), payload, { form });

// File uploads
const formData = new FormData();
formData.append('file', fileInput.files[0]);
await request(url_for_run('tasks/upload'), { 
  method: 'POST', 
  body: formData,
  form: formElement 
});

// Error handling
try {
  await postJson(url, payload);
} catch (err) {
  if (err instanceof HttpError) {
    controller.pushResponseStacktrace(err.response);
  }
}
```

**Event coordination**:
```javascript
const { createEmitter, useEventMap, emitDom } = WCEvents;

// Define event surface
controller.events = useEventMap([
  'climate:build:started',
  'climate:build:completed',
  'climate:build:failed'
]);

// Emit domain events
controller.events.emit('climate:build:started', { mode: 'station' });

// Subscribe
controller.events.on('climate:build:completed', (payload) => {
  console.log('Build finished:', payload);
});

// Bridge to DOM
emitDom(document, 'BUILD_CLIMATE_TASK_COMPLETED', { jobId });
```

**Form serialization**:
```javascript
const { serializeForm, applyValues, findCsrfToken } = WCForms;

// Native types (JSON)
const payload = serializeForm(form, { format: 'json' });
// { mode: 2, enabled: true, threshold: 5.5 }

// URL encoding
const queryString = serializeForm(form, { format: 'query' });
// 'mode=2&enabled=true&threshold=5.5'

// Object with arrays
const data = serializeForm(form, { format: 'object' });
// { ids: [1, 2, 3], name: 'test' }

// Hydrate form
applyValues(form, { mode: 2, name: 'Updated' });
```

### Run-Scoped URL Construction

**Critical convention**: All run-context endpoints MUST use `url_for_run()` from `utils.js`:

```javascript
// ✅ Correct
http.postJson(url_for_run('rq/api/build_climate'), payload);
http.get(url_for_run('resources/subcatchments.json'));

// ❌ Wrong - breaks in multi-config deployments
http.postJson('rq/api/build_climate', payload);
```

The helper reads `window.runId` and `window.config` to construct `/runs/<runid>/<config>/...` paths automatically.

**Scope**: Applies to `rq/api/*`, `tasks/*`, `query/*`, `resources/*`  
**Exceptions**: `/batch/`, `/api/`, `/auth/`, root routes

### Template Data Hooks

**Naming convention**: `data-<controller>-<category>=<value>`

```html
<!-- Actions (clicks, submits) -->
<button data-climate-action="build">Build Climate</button>
<button data-wepp-action="run">Run WEPP</button>

<!-- Roles (grouped behavior) -->
<input type="radio" data-climate-role="mode" data-climate-mode="station">
<select data-landuse-role="db-selector">...</select>

<!-- Fields (value sources) -->
<input data-climate-field="station-id">
<textarea data-landuse-modify-field="topaz-ids"></textarea>

<!-- Sections (conditional panels) -->
<div data-climate-section="station-controls">...</div>
<div data-precip-section="scaling-options" hidden>...</div>
```

**Wiring pattern**:
```javascript
delegate(root, '[data-climate-action]', 'click', (event) => {
  const action = event.target.dataset.climateAction;
  switch (action) {
    case 'build': handleBuild(); break;
    case 'reset': handleReset(); break;
  }
});
```

### Controller Lifecycle Pattern

**Standard structure**:
```javascript
var Climate = (function () {
  var instance = null;

  function Controller() {
    // Cache helpers
    const dom = window.WCDom;
    const http = window.WCHttp;
    const forms = window.WCForms;
    const events = window.WCEvents;

    // Validate dependencies
    if (!dom || !http || !forms || !events) {
      throw new Error('Climate requires helper stack');
    }

    // State
    const that = {};
    that.form = null;
    that.base = controlBase();

    // Event surface
    that.events = events.useEventMap([
      'climate:build:started',
      'climate:build:completed',
      'climate:build:failed'
    ]);

    // Bootstrap
    that.bootstrap = function (context, meta) {
      const climateData = (context.data && context.data.climate) || {};
      const jobId = resolveJobId(context, 'climate');
      if (jobId) that.base.set_rq_job_id(jobId);
      // Wire events, hydrate UI
      wireEvents();
    };

    // Private methods
    function wireEvents() {
      that.form = dom.qs('#climate_form');
      dom.delegate(that.form, '[data-climate-action]', 'click', handleAction);
      that.base.attach_status_stream(that.form, 'climate');
    }

    function handleAction(event) {
      const action = event.target.dataset.climateAction;
      // Dispatch based on action
    }

    // Public API
    that.build = async function () {
      that.events.emit('climate:build:started');
      const payload = forms.serializeForm(that.form, { format: 'json' });
      try {
        const response = await http.postJson(
          url_for_run('rq/api/build_climate'), 
          payload,
          { form: that.form }
        );
        that.base.set_rq_job_id(response.job_id);
        that.events.emit('climate:build:completed', response);
      } catch (err) {
        that.events.emit('climate:build:failed', err);
        throw err;
      }
    };

    return that;
  }

  return {
    getInstance: function () {
      if (!instance) instance = Controller();
      return instance;
    }
  };
}());
```

### Testing Patterns

**Jest structure** (jsdom environment):
```javascript
import { describe, test, expect, beforeEach } from '@jest/globals';

// Mock helpers
global.WCDom = {
  qs: jest.fn(),
  delegate: jest.fn(),
  show: jest.fn(),
  hide: jest.fn()
};

global.WCHttp = {
  postJson: jest.fn(),
  getJson: jest.fn()
};

global.WCForms = {
  serializeForm: jest.fn(() => ({ mode: 1 }))
};

global.WCEvents = {
  createEmitter: jest.fn(() => ({
    emit: jest.fn(),
    on: jest.fn()
  })),
  useEventMap: jest.fn((events) => ({
    emit: jest.fn(),
    on: jest.fn()
  }))
};

describe('Climate Controller', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset controller singleton if needed
  });

  test('bootstrap wires events', () => {
    const Climate = require('../climate.js');
    const instance = Climate.getInstance();
    
    const context = {
      data: { climate: { mode: 'station' } },
      jobIds: { climate: 'test-job-id' }
    };

    instance.bootstrap(context);

    expect(global.WCDom.delegate).toHaveBeenCalled();
  });

  test('build emits lifecycle events', async () => {
    const Climate = require('../climate.js');
    const instance = Climate.getInstance();

    global.WCHttp.postJson.mockResolvedValue({ job_id: 'new-id' });

    await instance.build();

    expect(instance.events.emit).toHaveBeenCalledWith(
      'climate:build:started'
    );
    expect(instance.events.emit).toHaveBeenCalledWith(
      'climate:build:completed',
      expect.any(Object)
    );
  });
});
```

**Pytest integration** (backend routes):
```python
from tests.factories import singleton_factory, rq_environment

def test_build_climate_route(tmp_path, rq_environment):
    """Verify climate build route parses JSON and queues job."""
    from wepppy.weppcloud.routes.nodb_api.climate_bp import build_climate
    from wepppy.nodb.core.climate import Climate

    # Arrange
    wd = str(tmp_path)
    climate = singleton_factory(Climate, wd)
    
    with app.test_request_context(
        json={'mode': 'station', 'station_id': 'ABC123'}
    ):
        # Act
        response = build_climate('test-run', 'default')
        
        # Assert
        assert response['Success'] is True
        assert 'job_id' in response
        assert climate.mode == 'station'
```

---

## Tooling & Validation

### Pre-commit Workflow

```bash
# Lint JavaScript
wctl run-npm lint

# Run Jest tests
wctl run-npm test                    # All tests
wctl run-npm test -- climate         # Specific controller

# Run full check (lint + test)
wctl run-npm check

# Rebuild bundle
python wepppy/weppcloud/controllers_js/build_controllers_js.py

# Run backend tests
wctl run-pytest tests/weppcloud/routes/test_climate_bp.py
wctl run-pytest tests --maxfail=1    # Full suite
```

### Continuous Integration

- ESLint enforces helper usage (flags remaining `$` references)
- Jest runs in CI with full coverage reporting
- Pytest exercises Flask routes with singleton + RQ factories
- Bundle build verified during Docker image creation
- Smoke tests exercise critical user flows via Playwright

---

## Migration Checklist (For New Controllers)

When adding a new run controller or modernizing a legacy one:

1. **Scope**
   - [ ] Identify jQuery dependencies (`git grep '\$' controller.js`)
   - [ ] Map inline event handlers in templates
   - [ ] List backend routes and NoDb methods
   - [ ] Document current payload formats

2. **Plan**
   - [ ] Choose helper modules (typically all four: DOM, HTTP, Forms, Events)
   - [ ] Design event surface (lifecycle + domain events)
   - [ ] Define `data-*` attribute schema
   - [ ] Sketch bootstrap context requirements

3. **Implement**
   - [ ] Replace jQuery with helper calls
   - [ ] Convert inline handlers to `delegate` listeners
   - [ ] Add `bootstrap(context, meta)` method
   - [ ] Expose scoped event emitter via `useEventMap`
   - [ ] Update Flask routes to use `parse_request_payload`
   - [ ] Adjust NoDb methods to accept native types
   - [ ] Integrate `controlBase.attach_status_stream`

4. **Document**
   - [ ] Create/update controller plan in `archived-plans/`
   - [ ] Add controller reference to `README.md`
   - [ ] Update `AGENTS.md` with quick reference
   - [ ] Document payload schemas and event contracts

5. **Validate**
   - [ ] Add Jest test suite under `__tests__/`
   - [ ] Extend pytest coverage for routes
   - [ ] Run `wctl run-npm check` and fix lint errors
   - [ ] Rebuild bundle and verify in browser
   - [ ] Execute smoke tests if applicable
   - [ ] Update this foundations doc if new patterns emerge

---

## Anti-Patterns to Avoid

❌ **Don't reintroduce jQuery**
```javascript
// Wrong
$('#form').find('input').val('test');

// Right
const form = WCDom.qs('#form');
const input = WCDom.qs('input', form);
input.value = 'test';
```

❌ **Don't bypass url_for_run for run-scoped endpoints**
```javascript
// Wrong
http.post('tasks/set_mode', { mode: 2 });

// Right
http.postJson(url_for_run('tasks/set_mode'), { mode: 2 });
```

❌ **Don't implement custom WebSocket clients**
```javascript
// Wrong
const ws = new WebSocket('ws://...');

// Right
controlBase.attach_status_stream(form, 'channel_name');
```

❌ **Don't use inline event handlers**
```html
<!-- Wrong -->
<button onclick="controller.run()">Run</button>

<!-- Right -->
<button data-climate-action="run">Run</button>
```

❌ **Don't mutate controller state without emitting events**
```javascript
// Wrong
controller.mode = 2;

// Right
controller.setMode = function(mode) {
  controller.mode = mode;
  controller.events.emit('climate:mode:changed', { mode });
};
```

❌ **Don't scrape DOM for state in other controllers**
```javascript
// Wrong
const mode = parseInt($('#climate_mode').val());

// Right
Climate.getInstance().events.on('climate:mode:changed', ({ mode }) => {
  // React to mode change
});
```

---

Use this document as the definitive guide when maintaining or extending the controller infrastructure. When you discover new patterns or encounter edge cases, update this foundations doc so future work inherits the learning automatically.
