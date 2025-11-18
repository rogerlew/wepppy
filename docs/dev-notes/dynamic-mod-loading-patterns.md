# Dynamic Mod Loading Patterns and Pitfalls

**Last Updated:** November 17, 2025  
**Context:** Lessons learned from DSS Export mod integration issues

## The Problem

When mods are dynamically enabled via the Mods dialog (Project controller), controllers face a **DOM availability paradox**:

1. **Singleton Pattern Requirement**: Controllers use `getInstance()` to ensure only one instance exists
2. **Early Instance Creation**: `getInstance()` is called to initialize the controller
3. **Late DOM Insertion**: The HTML is inserted into the DOM *after* instance creation
4. **Stale References**: The controller holds `null` references to DOM elements that don't exist yet
5. **No Re-Query**: Since the instance already exists, subsequent calls to `getInstance()` don't re-query the DOM

### Why This Doesn't Happen on Page Load

When a mod is present on initial page load:
- The HTML is rendered server-side in the template
- DOM elements exist *before* any JavaScript runs
- Controller's `createInstance()` finds all elements immediately
- Everything works perfectly

### Why Dynamic Loading Breaks

When a mod is enabled via checkbox:
```javascript
// project.js set_mod() flow:
1. Backend: /tasks/set_mod persists state
2. Backend: /view/mod/<mod_name> returns HTML
3. Frontend: toggleModSection() → container.innerHTML = html
4. Frontend: bootstrapModController() → DssExport.getInstance()
5. DssExport: createInstance() runs, queries DOM → finds NOTHING (elements just inserted)
6. DssExport: Stores null references in controller.modePanels, controller.form, etc.
7. DssExport: bootstrap() is called, but can't undo the null references
```

## The Two Fixes Applied to DSS Export

### Fix #1: Defer Controller Bootstrap

**Problem:** Controller initialization was happening synchronously with DOM insertion, before the browser could update the rendering tree.

**Solution:** Add `setTimeout(..., 0)` in `project.js` to defer to next event loop tick:

```javascript
// In project.js set_mod()
applyUI(html);
// Allow DOM to settle before bootstrapping controller
return new Promise(function (resolve) {
    setTimeout(function () {
        bootstrapModController(normalized);
        // ... rest of logic
        resolve(response);
    }, 0);
});
```

**Why This Helps:** The browser processes the `innerHTML` assignment and updates the DOM tree before the controller queries for elements.

### Fix #2: Re-Query Elements in Bootstrap

**Problem:** Even with the setTimeout, elements queried during `createInstance()` were stored as `null` and never updated.

**Solution:** Add re-query logic in the `bootstrap()` method:

```javascript
// In dss_export.js bootstrap()
controller.bootstrap = function bootstrap(context) {
    // Re-query mode panels if they weren't found during initial creation
    if ((!controller.modePanels[1] || !controller.modePanels[1].element) && controller.form) {
        var mode1El = dom.qs(SELECTORS.mode1, controller.form);
        if (mode1El) {
            controller.modePanels[1] = createLegacyAdapter(mode1El);
        }
    }
    // ... repeat for mode2, other critical elements
    
    // ... rest of bootstrap logic
};
```

**Why This Works:** `bootstrap()` runs *after* DOM insertion and can fix null references from `createInstance()`.

### Fix #3: Re-Attach Event Delegates in Bootstrap

**Problem:** Event listeners were only attached in `createInstance()` when `formElement` existed. When dynamically loaded, `formElement` is null, so delegates never get attached.

**Solution:** Add conditional delegate setup in `bootstrap()` method:

```javascript
// In dss_export.js bootstrap()
controller.bootstrap = function bootstrap(context) {
    // Track whether we need to set up delegates
    var needsDelegates = false;
    
    // Re-query form if it wasn't found during createInstance
    if (!controller.form) {
        var formElement = dom.qs(SELECTORS.form);
        if (formElement) {
            controller.form = formElement;
            needsDelegates = true;  // Form is fresh, need to wire up events
        }
    }
    
    // Set up event delegates if this is the first time we have a valid form
    if (needsDelegates && controller.form) {
        controller._delegates.push(
            dom.delegate(controller.form, "change", ACTIONS.modeToggle, function(event) {
                // ... mode toggle handler
            })
        );
        controller._delegates.push(
            dom.delegate(controller.form, "click", ACTIONS.runExport, function(event) {
                // ... export button handler
            })
        );
        controller.form.addEventListener("DSS_EXPORT_TASK_COMPLETED", function(event) {
            // ... completion handler
        });
    }
    
    // ... rest of bootstrap logic
};
```

**Why This Is Critical:** Without this fix:
- DOM elements appear in the page ✅
- Controller can query and manipulate them ✅
- But clicking buttons/radios does nothing ❌ (no event handlers attached)

**Symptom:** Mode panels exist but don't swap when radio buttons are clicked; controller.state.mode doesn't match the checked radio value.

## Root Cause Analysis

The real issue is **premature singleton instantiation**. The singleton pattern assumes:
- Instance is created once
- All required resources exist at creation time
- No need to re-initialize

But dynamic mod loading violates these assumptions:
- Instance may be created before DOM exists
- Resources appear *after* instantiation
- We need partial re-initialization without breaking the singleton

## Prevention Checklist for Future Mods

When creating a new mod controller that will be dynamically loaded:

### 1. **Lazy Element Queries**

❌ **Don't** query all elements in `createInstance()`:
```javascript
function createInstance() {
    var form = dom.qs("#my_form");  // May be null!
    var button = dom.qs("#my_button", form);  // Will fail if form is null
    return { form: form, button: button };
}
```

✅ **Do** query elements lazily or in `bootstrap()`:
```javascript
function createInstance() {
    var controller = {
        _formCache: null,
        get form() {
            if (!this._formCache) {
                this._formCache = dom.qs("#my_form");
            }
            return this._formCache;
        }
    };
    return controller;
}
```

Or better yet, use a getter pattern:
```javascript
function createInstance() {
    var controller = {};
    
    function getForm() {
        return dom.qs("#my_form");
    }
    
    controller.doSomething = function() {
        var form = getForm();  // Query fresh each time
        if (!form) {
            console.warn("Form not found");
            return;
        }
        // ... use form
    };
    
    return controller;
}
```

### 2. **Bootstrap Re-Query Pattern**

Always implement re-query logic in `bootstrap()`:

```javascript
controller.bootstrap = function bootstrap(context) {
    // Re-query critical elements if they're missing
    if (!controller.form || !controller.form.element) {
        var formElement = dom.qs(SELECTORS.form);
        if (formElement) {
            controller.form = formElement;
            // Re-query child elements that depend on form
            controller.submitButton = dom.qs(SELECTORS.submit, formElement);
            controller.statusPanel = dom.qs(SELECTORS.status, formElement);
        }
    }
    
    // Now proceed with bootstrap logic knowing elements are fresh
    // ...
};
```

### 3. **Event Delegate Setup in Bootstrap**

If your controller uses event delegates, they must be set up in `bootstrap()` as well as `createInstance()`:

```javascript
function createInstance() {
    var controller = {
        _delegates: [],
        form: null
    };
    
    var formElement = dom.qs(SELECTORS.form);
    if (formElement) {
        controller.form = formElement;
        // Set up delegates for normal page load
        setupDelegates(controller);
    }
    
    return controller;
}

function setupDelegates(controller) {
    if (!controller.form) return;
    
    controller._delegates.push(
        dom.delegate(controller.form, "change", ".mode-toggle", function(e) {
            // ... handler
        })
    );
}

controller.bootstrap = function bootstrap(context) {
    var needsDelegates = false;
    
    // Re-query form if null
    if (!controller.form) {
        var formElement = dom.qs(SELECTORS.form);
        if (formElement) {
            controller.form = formElement;
            needsDelegates = true;
        }
    }
    
    // Set up delegates for dynamic load
    if (needsDelegates) {
        setupDelegates(controller);
    }
};
```

**Critical:** Event handlers are not automatically restored when elements are re-queried. You must explicitly attach them in `bootstrap()`.

### 4. **Defensive Element Access**

Always check for element existence before use:

```javascript
controller.setMode = function(mode) {
    if (!controller.modePanels || !controller.modePanels[mode]) {
        console.warn("[MyController] Mode panel not found:", mode);
        return;
    }
    controller.modePanels[mode].show();
};
```

### 5. **Test Dynamic Loading**

Add this to your controller testing checklist:

- ✅ Test initial page load (mod in template)
- ✅ Test dynamic enable (checkbox in Mods dialog)
- ✅ Test dynamic disable → re-enable
- ✅ Test mode switches after dynamic load
- ✅ Test event handlers (clicks, changes) after dynamic load
- ✅ Verify all UI interactions work identically in both scenarios

### 6. **Document Dynamic Loading Requirements**

In your controller's README or header comment:

```javascript
/**
 * MyController
 * 
 * DYNAMIC LOADING NOTES:
 * - Form elements may be null during createInstance() if mod is dynamically loaded
 * - bootstrap() re-queries form and child elements to handle dynamic loading
 * - All public methods defensively check for element existence
 */
```

## Alternative Architectures to Consider

### Option A: Remount Pattern (Used by Omni)

Instead of singleton, allow full remount:

```javascript
return {
    getInstance: function() {
        if (!instance) {
            instance = createInstance();
        }
        return instance;
    },
    remount: function() {
        if (instance && typeof instance.dispose === "function") {
            instance.dispose();  // Clean up old instance
        }
        instance = createInstance();  // Fresh instance with fresh queries
        return instance;
    }
};
```

Then in `project.js` `MOD_BOOTSTRAP_MAP`:
```javascript
omni: function (ctx) {
    bootstrapControllerSymbol(window.Omni, ctx, { forceRemount: true });
}
```

**Pros:**
- Clean slate for dynamic loading
- No stale references possible
- Simpler controller code

**Cons:**
- Loses in-memory state
- Event listeners must be re-attached
- More complex lifecycle management

### Option B: Factory Functions

Replace singleton with factory that returns new controller per DOM root:

```javascript
function createDssExportController(formElement) {
    if (!formElement) {
        throw new Error("DssExport requires form element");
    }
    
    // All queries scoped to formElement
    var submitButton = dom.qs(SELECTORS.submit, formElement);
    var statusPanel = dom.qs(SELECTORS.status, formElement);
    
    return {
        form: formElement,
        submit: function() { /* ... */ }
    };
}

// Usage:
var form = dom.qs("#dss_export_form");
var controller = createDssExportController(form);
```

**Pros:**
- Explicit dependencies
- Easy to test
- No singleton state

**Cons:**
- Breaks current `getInstance()` API
- Callers must manage instances
- Not compatible with existing bootstrap pattern

### Option C: Two-Phase Initialization (Recommended)

Split creation into instantiation + initialization:

```javascript
function createInstance() {
    var controller = {
        _initialized: false,
        form: null,
        modePanels: {}
    };
    
    controller.initialize = function() {
        if (controller._initialized) {
            return;  // Already initialized
        }
        
        // Query elements
        controller.form = dom.qs(SELECTORS.form);
        if (!controller.form) {
            throw new Error("DssExport form not found in DOM");
        }
        
        var mode1El = dom.qs(SELECTORS.mode1, controller.form);
        var mode2El = dom.qs(SELECTORS.mode2, controller.form);
        controller.modePanels = {
            1: createLegacyAdapter(mode1El),
            2: createLegacyAdapter(mode2El)
        };
        
        // Set up event listeners
        dom.delegate(controller.form, "change", ACTIONS.modeToggle, handleModeChange);
        
        controller._initialized = true;
    };
    
    controller.bootstrap = function(context) {
        controller.initialize();  // Safe to call multiple times
        // ... rest of bootstrap
    };
    
    return controller;
}
```

**Usage in project.js:**
```javascript
function bootstrapModController(modName) {
    var controller = MOD_SYMBOL_MAP[modName].getInstance();
    if (typeof controller.initialize === "function") {
        controller.initialize();  // Ensure DOM elements are queried
    }
    if (typeof controller.bootstrap === "function") {
        controller.bootstrap(window.runContext || {});
    }
}
```

**Pros:**
- Separates concerns (instantiation vs initialization)
- Safe to call `initialize()` multiple times
- Compatible with singleton pattern
- Clear contract for dynamic loading

**Cons:**
- Extra method to maintain
- Must remember to call `initialize()` before use

## When to Use Which Pattern

| Scenario | Recommended Pattern | Rationale |
|----------|-------------------|-----------|
| Simple, stateless mod | Factory Functions | Clean, testable, no lifecycle issues |
| Complex state, dynamic loading | Two-Phase Initialization | Best balance of safety and simplicity |
| Heavy UI widgets | Remount Pattern | Clean slate prevents stale DOM refs |
| Existing controllers | Re-Query in Bootstrap | Minimal code changes, backwards compatible |

## Testing Dynamic Loading

Add this smoke test to your mod:

```javascript
// In tests/weppcloud/routes/test_dynamic_mod_loading.js
describe('Dynamic Mod Loading', () => {
    it('should fully initialize DSS Export when enabled via checkbox', async () => {
        // 1. Load page without mod
        const response = await client.get(`/runs/${runid}/${config}/`);
        expect(response.text).not.toContain('id="dss_export_form"');
        
        // 2. Enable mod via API
        await client.post(`/runs/${runid}/${config}/tasks/set_mod`, {
            mod: 'dss_export',
            enabled: true
        });
        
        // 3. Fetch mod HTML
        const modResponse = await client.get(`/runs/${runid}/${config}/view/mod/dss_export`);
        expect(modResponse.body.Success).toBe(true);
        
        // 4. Simulate frontend: insert HTML and bootstrap
        const html = modResponse.body.Content.html;
        // ... insert into test DOM
        
        // 5. Verify controller functionality
        const controller = DssExport.getInstance();
        controller.bootstrap(mockContext);
        
        // 6. Test mode switching
        controller.setMode(2);
        expect(mode2Panel.hidden).toBe(false);
        expect(mode1Panel.hidden).toBe(true);
        
        controller.setMode(1);
        expect(mode1Panel.hidden).toBe(false);
        expect(mode2Panel.hidden).toBe(true);
    });
});
```

## Documentation Updates Needed

1. **README.md** for each mod controller should include:
   - "Dynamic Loading Behavior" section
   - List of elements that may be null initially
   - How `bootstrap()` handles re-initialization

2. **wepppy/weppcloud/controllers_js/README.md** should document:
   - The dynamic loading lifecycle
   - Recommended patterns for new controllers
   - Common pitfalls (this document)

3. **Code comments** in `project.js` `set_mod()`:
   ```javascript
   // Apply UI changes, then defer controller bootstrap to next tick.
   // This ensures innerHTML assignment completes and DOM is queryable
   // before controllers try to find their elements.
   applyUI(html);
   return new Promise(function (resolve) {
       setTimeout(function () {
           bootstrapModController(normalized);  // Controllers can now find DOM
           // ...
       }, 0);
   });
   ```

4. **Template pattern** in `MOD_UI_DEFINITIONS` (run_0_bp.py):
   ```python
   MOD_UI_DEFINITIONS = {
       'dss_export': {
           'template': 'controls/dss_export_pure.htm',
           'section_id': 'dss-export',
           # IMPORTANT: Ensure all critical elements have stable IDs
           # that controllers can query. Avoid dynamic IDs or classes.
           'critical_selectors': [
               '#dss_export_form',
               '#dss_export_mode1_controls',
               '#dss_export_mode2_controls'
           ]
       }
   }
   ```

## Summary

**Why DSS Export was stubborn:**
1. Singleton pattern + dynamic DOM insertion = null references
2. No re-query mechanism in `bootstrap()`
3. Synchronous bootstrap immediately after `innerHTML`

**How to prevent in future:**
1. Use lazy getters or re-query in `bootstrap()`
2. Add `setTimeout(..., 0)` in `project.js` for all dynamic mods (already done)
3. Test dynamic loading explicitly, not just initial page load
4. Document dynamic loading behavior in controller README
5. Consider two-phase initialization pattern for new controllers

**Quick Reference for New Mods:**

```javascript
// Template for dynamic-loading-safe controller
function createInstance() {
    var controller = {};
    
    // Lazy element access
    function getForm() {
        return dom.qs("#my_form");
    }
    
    controller.doSomething = function() {
        var form = getForm();
        if (!form) return;  // Defensive check
        // ... use form
    };
    
    controller.bootstrap = function(context) {
        // Re-query if needed
        var form = getForm();
        if (form) {
            // Bootstrap logic
        }
    };
    
    return controller;
}
```
