# Preflight Behavior Documentation

> **Last Updated:** October 27, 2025  
> **Related Files:**
> - `/workdir/wepppy/wepppy/weppcloud/static/js/preflight.js`
> - `/workdir/wepppy/wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
> - `/workdir/wepppy/wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
> - `/workdir/wepppy/wepppy/weppcloud/static/css/ui-foundation.css`
> - `/workdir/wepppy/wepppy/nodb/redis_prep.py`
> - `/workdir/wepppy/wepppy/weppcloud/routes/run_0/run_0_bp.py`
> - `/workdir/wepppy/services/preflight2/` (Go WebSocket service)

## Overview

The preflight system is a real-time task completion tracker that:
1. Shows emoji indicators in the TOC navigation when tasks are complete
2. Enables/disables map layer controls based on data availability
3. Streams progress updates via WebSocket from a Go microservice
4. Uses Redis-backed state from `RedisPrep` and `TaskEnum`

---

## Architecture

### Data Flow

```
Go Service (preflight2)
  ↓ WebSocket (ws://host/preflight2/ws/{runid})
  ↓ JSON payload: {"type":"preflight", "checklist":{...}, "lock_statuses":{...}}
  ↓
preflight.js
  ↓ window.lastPreflightChecklist (global state)
  ↓ updateUI(checklist) → setTocEmojiState()
  ↓ CustomEvent('preflight:update')
  ↓
Controllers (e.g., subcatchment_delineation.js)
  ↓ updateLayerAvailability() → enable/disable radios
```

### Components

1. **Backend Service** (`services/preflight2/`) - Go WebSocket server
2. **Frontend Client** (`preflight.js`) - WebSocket consumer, UI updater
3. **State Source** (`redis_prep.py`) - Task definitions and emojis
4. **Route Handler** (`run_0_bp.py`) - Emoji mapping to TOC anchors
5. **Bootstrap Script** (`run_page_bootstrap.js.j2`) - Initialization orchestration

---

## Preflight Payload Structure

### Example WebSocket Message

```json
{
  "type": "preflight",
  "checklist": {
    "channels": true,
    "climate": false,
    "debris": false,
    "dss_export": false,
    "landuse": false,
    "observed": false,
    "outlet": true,
    "rap_ts": false,
    "sbs_map": true,
    "soils": false,
    "subcatchments": true,
    "watar": false,
    "wepp": false
  },
  "lock_statuses": {
    "ash.nodb": false,
    "climate.nodb": true,
    "landuse.nodb": false,
    "soils.nodb": false,
    "topaz.nodb": false,
    "watershed.nodb": false,
    "wepp.nodb": false
  }
}
```

### Checklist Keys

| Key | Description | Maps To Task |
|-----|-------------|--------------|
| `channels` | Channel delineation complete | `TaskEnum.build_channels` |
| `climate` | Climate data built | `TaskEnum.build_climate` |
| `debris` | Debris flow analysis run | `TaskEnum.run_debris` |
| `dss_export` | DSS export complete | `TaskEnum.dss_export` |
| `landuse` | Landuse data built | `TaskEnum.build_landuse` |
| `observed` | Observed data processed | `TaskEnum.run_observed` |
| `outlet` | Outlet set | `TaskEnum.set_outlet` |
| `rap_ts` | RAP time series fetched | `TaskEnum.fetch_rap_ts` |
| `sbs_map` | Soil burn severity map initialized | `TaskEnum.init_sbs_map` |
| `soils` | Soil data built | `TaskEnum.build_soils` |
| `subcatchments` | Subcatchments delineated | `TaskEnum.build_subcatchments` |
| `watar` | WATAR (ash transport) run | `TaskEnum.run_watar` |
| `wepp` | WEPP model run | `TaskEnum.run_wepp_watershed` |
| `omni_scenarios` | Omni scenario runner completed after the latest WEPP run | `TaskEnum.run_omni_scenarios` |

---

## Mods Selection Dropdown

The Pure header exposes a **Mods** dropdown so operators can toggle optional controllers
without reloading the page. Each checkbox wires through the project controller and
re-renders the associated control panel alongside its TOC entry.

### Backend pieces

- `header/_run_header_fixed.htm` renders the checkbox list and tags each option with
  `data-project-mod="<mod>"`.
- `run_0/run_0_bp.py` maintains `MOD_UI_DEFINITIONS`, the `/view/mod/<mod>` route that
  re-renders a control, and placeholder wrappers (`data-mod-section="<mod>"`) inside
  `runs0_pure.htm`.
- `project_bp.task_set_mod` updates `Ron.mods`, instantiates controllers, and preserves
  existing `.nodb` snapshots by renaming them to `.bak` when modules are disabled.

### Frontend pieces

1. `project.js` listens for checkbox changes and posts to `tasks/set_mod`.
2. Successful responses fetch `/view/mod/<mod>` and update both the nav entry
   (`data-mod-nav`) and section placeholder (`data-mod-section`).
3. `MOD_BOOTSTRAP_MAP` reinitialises controller JS (Omni remounts its event handlers,
   Ash/Treatments rebuild their forms, etc.) so the new panel behaves as if the page was refreshed.

When adding a new module, update the header list, append metadata in `MOD_UI_DEFINITIONS`,
drop a `data-mod-section` wrapper in `runs0_pure.htm`, and optionally register a bootstrap
handler so the controller self-initialises after dynamic inserts.

---

## TOC Emoji Mapping

### How It Works

1. **Route Handler** (`run_0_bp.py` lines 44-67):
   ```python
   TOC_TASK_ANCHOR_TO_TASK = {
       '#map': TaskEnum.fetch_dem,
       '#disturbed-sbs': TaskEnum.init_sbs_map,
       '#channel-delineation': TaskEnum.build_channels,
       '#rangeland-cover': TaskEnum.build_rangeland_cover,
       # ... etc
   }
   
   TOC_TASK_EMOJI_MAP = {
       anchor: task.emoji() 
       for anchor, task in TOC_TASK_ANCHOR_TO_TASK.items()
   }
   ```

2. **Template** receives `toc_task_emojis` and embeds in `runContext.ui.tocTaskEmojis`

3. **Bootstrap Script** (`run_page_bootstrap.js.j2` line 341):
   ```javascript
   window.tocTaskEmojis = runContext.ui && runContext.ui.tocTaskEmojis 
       ? runContext.ui.tocTaskEmojis : {};
   ```

4. **Preflight.js** (`getSelectorForKey()` lines 166-184):
   ```javascript
   var mapping = {
       "sbs_map": 'a[href="#disturbed-sbs"]',
       "channels": 'a[href="#channel-delineation"]',
       "outlet": 'a[href="#set-outlet"]',
       "rangeland_cover": 'a[href="#rangeland-cover"]',
       // ... etc
   };
   ```

5. **CSS** (`ui-foundation.css` lines 702-724):
   ```css
   .wc-toc-with-emojis .nav-link::before {
       content: attr(data-toc-emoji-value);
       opacity: 0;  /* Hidden by default */
   }
   
   .wc-toc-with-emojis .nav-link[data-toc-emoji]:not([data-toc-emoji=""])::before {
       opacity: 1;  /* Visible when complete */
   }
   ```

### Emoji Source: TaskEnum

All emojis are defined in `wepppy/nodb/redis_prep.py` (`TaskEnum.emoji()` method):

```python
def emoji(self) -> str:
    return {
        TaskEnum.if_exists_rmtree: '🗑️',
        TaskEnum.project_init: '🚀',
        TaskEnum.set_outlet: '📍',
        TaskEnum.abstract_watershed: '💎',
        TaskEnum.build_channels: '🌊',
        TaskEnum.build_subcatchments: '🧩',
        TaskEnum.build_landuse: '🌲',
    TaskEnum.build_rangeland_cover: '🦎',
        TaskEnum.build_soils: '🪱',
        TaskEnum.build_climate: '☁️',
        TaskEnum.fetch_rap_ts: '🗺️',
        TaskEnum.run_wepp_hillslopes: '💧',
        TaskEnum.run_wepp_watershed: '🏃',
        TaskEnum.run_observed: '📊',
        TaskEnum.run_debris: '🪨',
        TaskEnum.run_watar: '🌋',
        TaskEnum.run_rhem: '🌵',
        TaskEnum.fetch_dem: '🌍',
        TaskEnum.landuse_map: '🗺️',
        TaskEnum.init_sbs_map: '🔥',
        TaskEnum.run_omni_scenarios: '🪓',
        TaskEnum.run_omni_contrasts: '⚖️',
        TaskEnum.dss_export: '📤',
        TaskEnum.set_readonly: '🔒',
        TaskEnum.run_path_cost_effective: '🧮',
    }.get(self, self.value)
```

**Single Source of Truth:** `TaskEnum.emoji()` is the authoritative emoji source. Never hardcode emojis elsewhere.

---

## TOC HTML Structure

### Template (`runs0_pure.htm` lines 30-75)

```html
<nav id="toc" class="wc-run-layout__toc wc-toc-with-emojis">
  <h4>Preflight and Navigation</h4>
  <ul class="wc-toc-list">
    <li><a href="#map" class="nav-link">Map &amp; Analysis</a></li>
    <li><a href="#disturbed-sbs" class="nav-link">Soil Burn Severity</a></li>
    <li><a href="#channel-delineation" class="nav-link">Channel Delineation</a></li>
    <!-- ... etc -->
  </ul>
</nav>
```

### CSS Grid Layout (`ui-foundation.css` lines 702-724)

```css
.wc-toc-with-emojis .nav-link {
  display: grid;
  grid-template-columns: 1.5rem 1fr;
  gap: var(--wc-space-sm);
  align-items: center;
}
```

**Column 1 (1.5rem):** Emoji indicator  
**Column 2 (1fr):** Control label

### Attributes Set by JavaScript

| Attribute | Purpose | Set By |
|-----------|---------|--------|
| `data-toc-emoji-value` | Stores the TaskEnum emoji | `run_page_bootstrap.js.j2::registerTocEmojiMetadata()` |
| `data-toc-emoji` | Completion flag (empty="" or emoji value) | `preflight.js::setTocEmojiState()` |
| `data-original-text` | Control label without emoji | `run_page_bootstrap.js.j2::registerTocEmojiMetadata()` |

---

## JavaScript Initialization Sequence

### 1. DOMContentLoaded (`run_page_bootstrap.js.j2` line 339)

```javascript
document.addEventListener("DOMContentLoaded", function () {
    initUnitizers();
    bootstrapControllers(runContext);
    window.tocTaskEmojis = runContext.ui && runContext.ui.tocTaskEmojis 
        ? runContext.ui.tocTaskEmojis : {};
    initializeToc(window.tocTaskEmojis);
});
```

### 2. initializeToc() (line 323)

```javascript
function initializeToc(emojiMap) {
    var navElement = document.getElementById("toc");
    if (!navElement) return;
    
    // Register emoji metadata on anchors
    registerTocEmojiMetadata(navElement, emojiMap || {});
    
    // Setup smooth scroll
    setupTocScroll(navElement);
    
    // Apply initial preflight state
    if (typeof window.updateUI === "function" && window.lastPreflightChecklist) {
        window.updateUI(window.lastPreflightChecklist);
    }
}
```

### 3. registerTocEmojiMetadata() (line 275)

```javascript
function registerTocEmojiMetadata(navElement, emojiMap) {
    var anchors = navElement.querySelectorAll("a.nav-link");
    Array.prototype.forEach.call(anchors, function (anchor) {
        var href = anchor.getAttribute("href");
        var emoji = emojiMap[href];
        if (!emoji) return;
        
        // Store original text (strip emoji if present)
        var existingText = (anchor.textContent || "").trim();
        if (emoji && existingText.indexOf(emoji) === 0) {
            existingText = existingText.slice(emoji.length).trim();
        }
        
        // Set attributes
        anchor.setAttribute("data-original-text", existingText);
        anchor.setAttribute("data-toc-emoji-value", emoji);
        anchor.setAttribute("data-toc-emoji", "");  // Empty = not complete
        anchor.textContent = existingText;
    });
}
```

### 4. Window Load → initPreflight() (`run_page_bootstrap.js.j2` line 345)

```javascript
window.addEventListener("load", function () {
    if (typeof initPreflight === "function") {
        initPreflight(runId);
    }
    // ... other initialization
});
```

### 5. initPreflight() → WebSocket Connection (`preflight.js` lines 24-85)

```javascript
function initPreflight(runId) {
    var protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    var host = window.location.host;
    var url = protocol + "//" + host + "/preflight2/ws/" + runId;
    
    ws = new WebSocket(url);
    
    ws.onmessage = function (evt) {
        var msg = JSON.parse(evt.data);
        if (msg.type === "preflight") {
            handlePreflightUpdate(msg.checklist, msg.lock_statuses);
        }
    };
}
```

---

## Preflight Update Flow

### handlePreflightUpdate() (`preflight.js` lines 87-166)

```javascript
function handlePreflightUpdate(checklist, lockStatuses) {
    window.lastPreflightChecklist = checklist;
    window.lastPreflightLockStatuses = lockStatuses;
    
    if (typeof window.updateUI === "function") {
        window.updateUI(checklist);
    }
}
```

### updateUI() (`preflight.js` lines 129-166)

```javascript
function updateUI(checklist) {
    if (!checklist || typeof checklist !== "object") return;
    
    // Update TOC emojis for each checklist key
    Object.keys(checklist).forEach(function (key) {
        var selector = getSelectorForKey(key);
        if (selector) {
            setTocEmojiState(selector, checklist[key]);
        }
    });
    
    // Dispatch event for controllers
    document.dispatchEvent(new CustomEvent('preflight:update', { 
        detail: checklist 
    }));
}
```

### setTocEmojiState() (`preflight.js` lines 187-238)

```javascript
function setTocEmojiState(selector, isComplete) {
    var $targets = $(selector);
    $targets.each(function () {
        var anchor = this;
        var href = anchor.getAttribute('href');
        var emoji = anchor.getAttribute('data-toc-emoji-value');
        
        // Fallback: look up emoji from window.tocTaskEmojis
        if (!emoji && window.tocTaskEmojis && href) {
            emoji = window.tocTaskEmojis[href];
        }
        
        // Set completion state
        anchor.setAttribute('data-toc-emoji-value', emoji || '');
        anchor.setAttribute('data-toc-emoji', (isComplete && emoji) ? emoji : '');
        
        // Ensure text is clean (no emoji inline)
        var originalText = anchor.getAttribute('data-original-text');
        if (anchor.textContent !== originalText) {
            anchor.textContent = originalText;
        }
    });
}
```

---

## CSS Visibility Logic

### Default State (Task Not Complete)

```css
.wc-toc-with-emojis .nav-link::before {
    content: attr(data-toc-emoji-value);
    opacity: 0;  /* Hidden */
}
```

**Result:** Emoji column is empty.

### Complete State (Task Complete)

```css
.wc-toc-with-emojis .nav-link[data-toc-emoji]:not([data-toc-emoji=""])::before {
    opacity: 1;  /* Visible */
}
```

**Condition:** `data-toc-emoji` attribute has a non-empty value  
**Result:** Emoji becomes visible with `opacity: 1` transition.

---

## Controller Integration

### Example: Map Layer Enablement

**File:** `wepppy/weppcloud/controllers_js/subcatchment_delineation.js`

```javascript
function updateLayerAvailability() {
    var checklist = window.lastPreflightChecklist || {};
    
    if (checklist.subcatchments) {
        enableColorMap('slp_asp');
        enableColorMap('chn_slp_asp');
        // ... etc
    }
    
    if (checklist.landuse) {
        enableColorMap('landuse');
    }
    
    if (checklist.soils) {
        enableColorMap('soils');
    }
}

// Listen for preflight updates
document.addEventListener('preflight:update', function(event) {
    updateLayerAvailability();
});
```

**Custom Event:** `preflight:update` is dispatched by `updateUI()` after TOC updates, allowing controllers to react to state changes.

---

## Checklist Key → Anchor ID Mapping

### Complete Mapping Table

| Checklist Key | Anchor ID | TaskEnum | Emoji |
|---------------|-----------|----------|-------|
| `sbs_map` | `#disturbed-sbs` | `init_sbs_map` | 🔥 |
| `channels` | `#channel-delineation` | `build_channels` | 🌊 |
| `outlet` | `#set-outlet` | `set_outlet` | 📍 |
| `subcatchments` | `#subcatchments-delineation` | `build_subcatchments` | 🧩 |
| `landuse` | `#landuse` | `build_landuse` | 🌲 |
| `soils` | `#soils` | `build_soils` | 🪱 |
| `climate` | `#climate` | `build_climate` | ☁️ |
| `rap_ts` | `#rap-ts` | `fetch_rap_ts` | 🗺️ |
| `wepp` | `#wepp` | `run_wepp_watershed` | 🏃 |
| `observed` | `#observed` | `run_observed` | 📊 |
| `debris` | `#debris-flow` | `run_debris` | 🪨 |
| `watar` | `#ash` | `run_watar` | 🌋 |
| `dss_export` | `#dss-export` | `dss_export` | 📤 |

**Note:** Controls without direct TaskEnum mapping (e.g., `#map`, `#team`, `#treatments`) use placeholder emojis defined in `run_0_bp.py`.

### DSS Export Dependency Rules

`services/preflight2/internal/checklist/checklist.go` now guards the DSS export status with the latest hydrology/transport job timestamps:

```go
latestTransport := maxTimestamp(prep, "timestamps:run_watar", "timestamps:run_wepp_watershed", "timestamps:run_wepp")
check["dss_export"] = safeGT(prep["timestamps:dss_export"], latestTransport)
```

**Practical implications**
- Running DSS export flips only the `dss_export` checklist entry; it should never invalidate WEPP (`run_wepp_watershed`) or Ash Transport (`run_watar`).
- Re-running WEPP or Ash creates newer timestamps, immediately invalidating the prior DSS export so the UI prompts operators to regenerate the archive.
- Manual timestamp edits or scripting against `RedisPrep.timestamp(TaskEnum.dss_export)` must happen after the latest WEPP/WATAR runs, otherwise the checklist will remain false.

---

## Debugging

### Check WebSocket Connection

```javascript
// Browser console
console.log(window.lastPreflightChecklist);
// Should show object like: {channels: true, outlet: true, ...}
```

### Verify Emoji Mapping

```javascript
// Browser console
console.log(window.tocTaskEmojis);
// Should show object like: {"#map": "🌍", "#channel-delineation": "🌊", ...}
```

### Inspect TOC Anchor Attributes

```javascript
// Browser console
document.querySelectorAll('#toc .nav-link').forEach(a => {
    console.log(a.href, {
        emoji: a.getAttribute('data-toc-emoji-value'),
        complete: a.getAttribute('data-toc-emoji'),
        text: a.textContent
    });
});
```

### Check Preflight WebSocket Messages

```bash
# Watch Redis pub/sub (if preflight2 publishes there)
redis-cli -n 2 SUBSCRIBE preflight:*

# Or check Go service logs
docker logs -f preflight2
```

---

## Common Issues

### Emoji Not Appearing

1. **Check anchor ID matches mapping** in `preflight.js::getSelectorForKey()`
2. **Verify TaskEnum mapping exists** in `run_0_bp.py::TOC_TASK_ANCHOR_TO_TASK`
3. **Confirm WebSocket is connected** - check browser DevTools Network tab
4. **Ensure checklist key is `true`** - inspect `window.lastPreflightChecklist`

### Wrong Emoji Displayed

1. **Check TaskEnum.emoji() return value** in `redis_prep.py`
2. **Verify run_0_bp.py maps correct TaskEnum** to anchor
3. **Clear browser cache** - CSS/JS may be stale

### Emoji Always Visible / Never Visible

1. **Check CSS specificity** - ensure `.wc-toc-with-emojis` class is on nav element
2. **Verify `data-toc-emoji` attribute logic** in `setTocEmojiState()`
3. **Confirm preflight.js is loaded** - check for syntax errors in console

---

## Future Enhancements

### Potential Improvements

1. **Hover tooltips** showing task completion timestamp
2. **Progress bars** for long-running tasks
3. **Error indicators** when tasks fail
4. **Emoji animations** on completion (fade-in, bounce)
5. **Persistent state** across page reloads (localStorage cache)

### Adding New Preflight Tasks

1. **Add TaskEnum member** in `redis_prep.py` with emoji
2. **Update TOC template** in `runs0_pure.htm` with new anchor
3. **Map anchor in run_0_bp.py** `TOC_TASK_ANCHOR_TO_TASK`
4. **Map checklist key in preflight.js** `getSelectorForKey()`
5. **Update Go service** to emit new checklist key

---

## Related Documentation

- [UI Style Guide](../ui-style-guide.md) - General UI patterns and conventions
- [Control UI Styling Patterns](control-components.md) - Control-specific styling patterns
- [README: preflight2 service](../../../services/preflight2/README.md) - Go WebSocket service details
- [AGENTS.md](../../../AGENTS.md) - Development guidelines and architecture

---

**Maintained by AI agents per authorship policy. Human reviewers: ensure technical accuracy when modifying.**
