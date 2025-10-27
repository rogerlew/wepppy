# WEPPcloud UI Style Guide & Site Assessment

> **For AI Agents:** This document is agent training material, not human documentation.  
> **Quick Start:** Scroll to [Pattern Catalog](#pattern-catalog) for copy-paste templates.  
> **Deep Dive:** Scroll to [Design Philosophy](#design-philosophy) for rationale and technical details.

<!-- toc -->
- [Pattern Catalog](#pattern-catalog)
  - [Pattern #1: Basic Control Shell](#pattern-1-basic-control-shell)
  - [Pattern #2: Summary Pane](#pattern-2-summary-pane)
  - [Pattern #3: Advanced Options (Collapsible)](#pattern-3-advanced-options-collapsible)
  - [Pattern #4: Status Panel + WebSocket](#pattern-4-status-panel-websocket)
  - [Pattern #5: Data Table + Pagination](#pattern-5-data-table-pagination)
  - [Pattern #6: Form with Validation](#pattern-6-form-with-validation)
  - [Pattern #7: Status Indicators](#pattern-7-status-indicators)
  - [Pattern #8: Console Layout](#pattern-8-console-layout)
- [Composition Rules](#composition-rules)
- [Pattern Decision Tree](#pattern-decision-tree)
- [Quick Reference Tables](#quick-reference-tables)
  - [Button Style Selection](#button-style-selection)
  - [Container Selection](#container-selection)
  - [Spacing Tokens](#spacing-tokens)
  - [Form Type Selection](#form-type-selection)
  - [WebSocket Status Patterns](#websocket-status-patterns)
- [Troubleshooting](#troubleshooting)
  - [Blue checkboxes appearing](#blue-checkboxes-appearing)
  - [Table overflows on mobile](#table-overflows-on-mobile)
  - [Status panel empty during task](#status-panel-empty-during-task)
  - [Buttons respond when disabled](#buttons-respond-when-disabled)
  - [Form has 11em left margin](#form-has-11em-left-margin)
  - [Summary pane doesn't show](#summary-pane-doesnt-show)
  - [Advanced options don't collapse](#advanced-options-dont-collapse)
- [Testing Checklist for New Controls](#testing-checklist-for-new-controls)
- [Design philosophy](#design-philosophy)
  - [The "Zero-Aesthetic" Reality](#the-zero-aesthetic-reality)
  - [Classic Design Principles (Still Apply)](#classic-design-principles-still-apply)
- [Technology stack](#technology-stack)
  - [Contributor quick-start](#contributor-quick-start)
- [Control components](#control-components)
  - [Base layout snippet](#base-layout-snippet)
- [Tokens, colors, and typography](#tokens-colors-and-typography)
  - [Color palette](#color-palette)
  - [Typography & spacing](#typography-spacing)
  - [Layout primitives](#layout-primitives)
- [Component guidance](#component-guidance)
  - [Buttons](#buttons)
  - [Forms](#forms)
  - [Tables](#tables)
  - [Panels & cards](#panels-cards)
  - [Status & alerts](#status-alerts)
  - [Navigation & toolbars](#navigation-toolbars)
  - [Console layout macros](#console-layout-macros)
  - [Tabular controls inside `control_shell`](#tabular-controls-inside-controlshell)
  - [Modal/dialogue content](#modaldialogue-content)
  - [Tooltip primitives](#tooltip-primitives)
  - [Logs & consoles](#logs-consoles)
- [Content display patterns](#content-display-patterns)
- [Accessibility checklist](#accessibility-checklist)
- [Implementation playbook](#implementation-playbook)
- [Site-wide assessment & unification plan](#site-wide-assessment-unification-plan)
  - [Global observations](#global-observations)
  - [Page-by-page notes](#page-by-page-notes)
- [Next steps & tracking](#next-steps-tracking)
- [Visual references & demos](#visual-references-demos)
- [JavaScript interaction principles](#javascript-interaction-principles)
- [Validation & automation](#validation-automation)
- [Guide change log](#guide-change-log)
<!-- tocstop -->

---

## Pattern Catalog

**Agent workflow:** Match user request → Copy pattern → Fill blanks → Done

**Pattern matching:**
```
User: "Climate control with dropdown and status log"
      ↓
Agent: control_shell + select + status_panel
      ↓
Copy: Pattern #1 (Basic Control Shell)
Fill: title="Climate Data", options=[GridMET, Daymet, PRISM]
      ↓
Done. No aesthetic decisions required.
```

**Pattern matching rules:**

| User Request Contains | Use Pattern | Pattern ID |
|-----------------------|-------------|------------|
| "control", "workflow", "climate", "landuse", "soils" | Basic Control Shell | #1 |
| "summary", "read-only data", "metadata", "current settings" | Summary Pane | #2 |
| "advanced options", "rarely used settings" | Advanced Options (Collapsible) | #3 |
| "status log", "background task", "streaming" | Status Panel + WebSocket | #4 |
| "table", "list", "pagination", "multi-page" | Data Table + Pagination | #5 |
| "form", "input", "validation", "error messages" | Form with Validation | #6 |
| "status", "success", "failed", "queued" | Status Indicators | #7 |
| "dashboard", "console", "admin tool" | Console Layout | #8 |

---

### Pattern #1: Basic Control Shell

**Trigger words:** control, workflow, climate, landuse, soils, wepp  
**Use when:** Building any run workflow control  
**Template variables:** `{{TITLE}}`, `{{ID_PREFIX}}`, `{{FORM_CONTENT}}`

```jinja
{% extends "base_pure.htm" %}
{% from "controls/_pure_macros.html" import control_shell, status_panel %}
{% from "shared/console_macros.htm" import button_row %}

{% block body %}
{% call control_shell(
    form_id="{{ID_PREFIX}}-form",
    title="{{TITLE}}",
    collapsible=True,
    summary_panel_override=summary_html
) %}
  
  <fieldset>
    <legend>{{TITLE}}</legend>
    
    {{FORM_CONTENT}}
    
    {% call button_row() %}
      <button type="submit" class="pure-button pure-button-primary">
        Submit
      </button>
      <button type="button" class="pure-button pure-button-secondary">
        Reset
      </button>
    {% endcall %}
  </fieldset>

  {{ status_panel(id="{{ID_PREFIX}}-status", height="300px") }}

{% endcall %}
{% endblock %}
```

**Example fill:**
- `{{TITLE}}` → `"Climate Data"`
- `{{ID_PREFIX}}` → `"climate"`
- `{{FORM_CONTENT}}` → dropdown + fields (see Pattern #6 for forms)

**What you get automatically:**
- Collapse toggle, summary pane (if provided), status panel, consistent spacing, ARIA attributes
- Summary panel appears only if `summary_panel_override` is passed
- `control_shell` provides the `<form>` wrapper automatically with `id="{{ID_PREFIX}}-form"`

---

### Pattern #2: Summary Pane

**Trigger words:** summary, read-only, metadata, current settings  
**Use when:** Show state information that user cannot edit  
**Template variables:** `{{ITEMS}}` (list of term/definition pairs)

```jinja
{% set summary_html %}
<div class="wc-summary-pane">
  <dl class="wc-summary-pane__list">
    {{ITEMS}}
  </dl>
</div>
{% endset %}
```

**Item template:**
```jinja
<div class="wc-summary-pane__item">
  <dt class="wc-summary-pane__term">{{LABEL}}</dt>
  <dd class="wc-summary-pane__definition">{{VALUE}}</dd>
</div>
```

**Example fill:**
```jinja
<div class="wc-summary-pane__item">
  <dt class="wc-summary-pane__term">Climate Source</dt>
  <dd class="wc-summary-pane__definition">GridMET (2020-2024)</dd>
</div>
<div class="wc-summary-pane__item">
  <dt class="wc-summary-pane__term">Station Count</dt>
  <dd class="wc-summary-pane__definition">42 stations</dd>
</div>
```

**Critical:** Copy wrapper divs exactly—they control grid layout.

---

### Pattern #3: Advanced Options (Collapsible)

**Trigger words:** advanced, rarely used, optional settings  
**Use when:** Hiding settings that would clutter main form  
**Template variables:** `{{CONTENT}}`

```jinja
<details class="wc-advanced-options">
  <summary class="wc-advanced-options__summary">
    Advanced Options
  </summary>
  <div class="wc-advanced-options__content">
    <div class="pure-form pure-form-stacked">
      {{CONTENT}}
    </div>
  </div>
</details>
```

**Example fill:**
```jinja
<label for="buffer">
  Buffer Distance (meters)
  <span class="wc-help-text">Area around watershed to include</span>
</label>
<input type="number" id="buffer" name="buffer" value="1000" min="0" step="100">

<label for="interpolation">Interpolation Method</label>
<select id="interpolation" name="interpolation">
  <option value="idw">Inverse Distance Weighting</option>
  <option value="nearest">Nearest Neighbor</option>
</select>
```

**Zero JavaScript required.** Native browser `<details>` behavior.

---

### Pattern #4: Status Panel + WebSocket

**Trigger words:** status log, background task, streaming, progress  
**Use when:** Long-running operations need live feedback  
**Template variables:** `{{PANEL_ID}}`, `{{CHANNEL}}`

**Template:**
```jinja
{# In template #}
{{ status_panel(id="{{PANEL_ID}}", height="300px") }}
```

**Controller JS:**
```javascript
<script>
document.addEventListener('DOMContentLoaded', function() {
  const controller = {{CONTROLLER}}.getInstance();
  
  controller.attachStatusStream('{{PANEL_ID}}', {
    channel: '{{CHANNEL}}',
    runId: window.runid
  });
});
</script>
```

**Example fill:**
- `{{PANEL_ID}}` → `"climate-status"`
- `{{CHANNEL}}` → `"climate"`
- `{{CONTROLLER}}` → `ClimateController`

**Handles automatically:** WebSocket connection, reconnection, scroll-to-bottom, timestamp formatting

**Note:** The `status_panel()` macro signature:
```python
status_panel(
    id=None,           # Required for WebSocket attachment
    title="Status",
    variant="compact",
    height=None,       # e.g. "300px" for scrollable log
    log_id=None,       # Auto-generated from id if not provided
    aria_live="polite"
)
```

---

### Pattern #5: Data Table + Pagination

**Trigger words:** table, list, pagination, multi-page, dataset  
**Use when:** Displaying tabular data with multiple pages  
**Template variables:** `{{COLUMNS}}`, `{{ROWS}}`, `{{PAGINATION}}`

```jinja
<div class="wc-table-wrapper">
  <table class="wc-table">
    <thead>
      <tr>
        {{COLUMNS}}
      </tr>
    </thead>
    <tbody>
      {{ROWS}}
    </tbody>
  </table>
</div>

<nav class="wc-pagination" aria-label="Pagination">
  <a href="?page=1" class="wc-pagination__link" aria-label="First page">«</a>
  <a href="?page={{ page - 1 }}" class="wc-pagination__link">‹</a>
  
  {% for p in page_range %}
    {% if p == page %}
      <span class="wc-pagination__link wc-pagination__link--current" aria-current="page">
        {{ p }}
      </span>
    {% else %}
      <a href="?page={{ p }}" class="wc-pagination__link">{{ p }}</a>
    {% endif %}
  {% endfor %}
  
  <a href="?page={{ page + 1 }}" class="wc-pagination__link">›</a>
  <a href="?page={{ total_pages }}" class="wc-pagination__link" aria-label="Last page">»</a>
</nav>
```

**Example fill:**
```jinja
{# Column headers #}
<th>Run ID</th>
<th>Configuration</th>
<th>Status</th>
<th>Created</th>

{# Rows #}
{% for run in runs %}
<tr>
  <td><a href="{{ run.url }}">{{ run.id }}</a></td>
  <td>{{ run.config }}</td>
  <td>
    <span class="wc-status-chip" data-state="{{ run.status }}">
      {{ run.status }}
    </span>
  </td>
  <td>{{ run.created | format_date }}</td>
</tr>
{% endfor %}
```

**Features:**
- `.wc-table-wrapper` provides horizontal scroll on narrow screens
- Alternating row backgrounds for scanability
- `aria-current="page"` announces current page to screen readers

---

### Pattern #6: Form with Validation

**Trigger words:** form, input, validation, error messages  
**Use when:** User input that needs validation and clear error messaging  
**Template variables:** `{{FIELDS}}`

```jinja
<form class="pure-form pure-form-stacked" id="{{FORM_ID}}">
  <fieldset>
    <legend>{{FORM_TITLE}}</legend>
    
    {{FIELDS}}
    
    {% call button_row() %}
      <button type="submit" class="pure-button pure-button-primary">
        {{SUBMIT_LABEL}}
      </button>
      <button type="reset" class="pure-button pure-button-secondary">
        Reset
      </button>
    {% endcall %}
  </fieldset>
</form>
```

**Field template with validation:**
```jinja
<div class="wc-field">
  <label for="{{FIELD_ID}}">
    {{LABEL}}
    <span class="wc-field__required">*</span>
  </label>
  <input 
    type="{{TYPE}}" 
    id="{{FIELD_ID}}" 
    name="{{NAME}}"
    required
    aria-describedby="{{FIELD_ID}}-help {{FIELD_ID}}-error"
  >
  <small id="{{FIELD_ID}}-help" class="wc-help-text">
    {{HELP_TEXT}}
  </small>
  <div id="{{FIELD_ID}}-error" class="wc-field__error" role="alert" hidden>
    {{ERROR_MESSAGE}}
  </div>
</div>
```

**Validation JavaScript:**
```javascript
document.getElementById('{{FORM_ID}}').addEventListener('submit', function(e) {
  const input = document.getElementById('{{FIELD_ID}}');
  const errorDiv = document.getElementById('{{FIELD_ID}}-error');
  
  if (!input.checkValidity()) {
    e.preventDefault();
    errorDiv.hidden = false;
    input.setAttribute('aria-invalid', 'true');
    input.focus();
  } else {
    errorDiv.hidden = true;
    input.removeAttribute('aria-invalid');
  }
});
```

**Accessibility features:**
- `aria-describedby` links help text and errors to inputs
- `role="alert"` announces errors to screen readers
- `aria-invalid` marks invalid fields
- Required fields marked visually and semantically

---

### Pattern #7: Status Indicators

**Trigger words:** status, success, failed, queued, progress  
**Use when:** Show job/task state inline or as banner

```jinja
{# Inline chip #}
<span class="wc-status-chip" data-state="{{STATE}}">{{TEXT}}</span>

{# Block-level banner #}
<div class="wc-status" data-state="{{STATE}}" role="alert">
  {{CONTENT}}
</div>

{# With spinner for in-progress tasks #}
<div class="wc-status" data-state="attention">
  <div class="wc-spinner"></div>
  {{PROGRESS_TEXT}}
</div>
```

**States available:**
- `success` – Green, for completed tasks
- `attention` – Yellow/orange, for pending/queued
- `critical` – Red, for errors
- (default) – Neutral gray for informational

**Example fill:**
```jinja
<span class="wc-status-chip" data-state="success">Completed</span>
<span class="wc-status-chip" data-state="attention">Queued</span>
<span class="wc-status-chip" data-state="critical">Failed</span>

<div class="wc-status" data-state="critical" role="alert">
  <strong>Build Failed:</strong> Climate data unavailable for selected date range.
  <a href="/docs/climate-troubleshooting">View troubleshooting guide</a>
</div>
```

---

### Pattern #8: Console Layout

**Trigger words:** dashboard, console, admin tool  
**Use when:** Administrative interfaces (archive dashboard, fork console, query tools)  
**Template variables:** `{{TITLE}}`, `{{SUBTITLE}}`, `{{SECTIONS}}`

```jinja
{% from "shared/console_macros.htm" import console_page, console_header, button_row %}

{% call console_page(data_controller="{{CONTROLLER}}") %}
  
  {% call console_header(
    run_link="{{RUN_URL}}", 
    run_label="{{RUN_ID}}", 
    title="{{TITLE}}",
    subtitle="{{SUBTITLE}}"
  ) %}
    <div class="wc-toolbar">
      {{TOOLBAR_ACTIONS}}
    </div>
  {% endcall %}
  
  {{SECTIONS}}
  
{% endcall %}
```

**Section template:**
```jinja
<section class="wc-panel wc-stack">
  <h2>{{SECTION_TITLE}}</h2>
  {{SECTION_CONTENT}}
</section>
```

**Example fill:**
```jinja
{% call console_page(data_controller="archive-dashboard") %}
  
  {% call console_header(
    run_link=run_url, 
    run_label=runid, 
    title="Archive Dashboard",
    subtitle="Create and manage project archives"
  ) %}
    <div class="wc-toolbar">
      <button class="pure-button" onclick="refreshList()">
        Refresh List
      </button>
      <a href="/docs/archiving" class="pure-button pure-button-link">
        Documentation
      </a>
    </div>
  {% endcall %}
  
  <section class="wc-panel wc-stack">
    <h2>Create New Archive</h2>
    <form class="pure-form pure-form-aligned">
      <!-- form content -->
    </form>
  </section>
  
  <section class="wc-panel">
    <h2>Existing Archives</h2>
    <div class="wc-table-wrapper">
      <table class="wc-table">
        <!-- archive list -->
      </table>
    </div>
  </section>
  
{% endcall %}
```

**What you get:**
- Breadcrumb navigation (run link → title)
- Consistent header styling
- Action toolbar aligned to the right
- Panels stack with proper spacing

---

## Composition Rules

**Valid nesting (what goes inside what):**

```
control_shell
├── form (pure-form pure-form-stacked)
│   ├── fieldset
│   │   ├── label + input/select/textarea
│   │   ├── button_row (for submit/reset buttons)
│   │   └── details (wc-advanced-options)
│   └── status_panel (outside fieldset, using status_panel macro)
├── table (wc-table inside wc-table-wrapper)
└── summary_pane (via summary_panel_override parameter)

console_page
├── console_header
│   └── toolbar (action buttons)
├── wc-panel (can stack multiple)
│   ├── form OR table OR content
│   └── button_row (if form)
└── status_panel (optional)
```

**Composition constraints (must follow):**

| Rule | Constraint | Why |
|------|------------|-----|
| Tables | Must wrap in `.wc-table-wrapper` | Enables horizontal scroll on mobile |
| Forms | Use `.pure-form-stacked` not `.pure-form-aligned` | Aligned creates 11em margin we don't want |
| Buttons | Always inside `button_row` macro | Consistent spacing + alignment |
| Status panel | Use `status_panel()` macro with unique `id` parameter | WebSocket attachment requires ID |
| Summary pane | Pass as `summary_panel_override` to control_shell | Shell handles show/hide logic |
| Advanced options | Wrap in `<details class="wc-advanced-options">` | Native collapse, zero JS |
| Checkboxes | Wrap in `.wc-choice.wc-choice--checkbox` | Sets accent color, prevents blue default |

**Invalid combinations (don't do this):**

| ❌ Wrong | ✅ Correct | Issue |
|---------|----------|-------|
| `<table class="wc-table">` | `<div class="wc-table-wrapper"><table class="wc-table">` | Table overflows on mobile |
| `<input type="checkbox">` | `<div class="wc-choice wc-choice--checkbox"><input>` | Shows blue instead of styled |
| `<button class="pure-button">` outside form | `{% call button_row() %}<button>` | Inconsistent spacing |
| Multiple `control_shell` in one page | One `control_shell` per template | Nesting not supported |
| Inline styles | Use CSS classes + tokens | Breaks global updates |

---

## Pattern Decision Tree

**For agents: Follow this logic to select patterns**

```
START: What does user want to build?

1. Is it a run workflow control (Climate, Landuse, etc.)?
   YES → Use Pattern #1 (Basic Control Shell)
   NO → Go to 2

2. Does it need read-only summary information?
   YES → Use Pattern #2 (Summary Pane) inside control_shell
   NO → Go to 3

3. Does it need rarely-used settings?
   YES → Use Pattern #3 (Advanced Options) inside form
   NO → Go to 4

4. Does it need live progress/log streaming?
   YES → Use Pattern #4 (Status Panel + WebSocket)
   NO → Go to 5

5. Does it display tabular data with pagination?
   YES → Use Pattern #5 (Data Table + Pagination)
   NO → Go to 6

6. Does it need validated user input?
   YES → Use Pattern #6 (Form with Validation)
   NO → Go to 7

7. Does it need to show task status (success/failed/queued)?
   YES → Use Pattern #7 (Status Indicators)
   NO → Go to 8

8. Is it an admin dashboard/console?
   YES → Use Pattern #8 (Console Layout)
   NO → Check if user request is unclear, ask for clarification

9. Multiple patterns needed?
   → Combine patterns following Composition Rules above
   → Example: Control Shell (#1) + Summary Pane (#2) + Status Panel (#4)
```

---

## Quick Reference Tables

### Button Style Selection

| User Intent | Class | When to Use |
|------------|-------|-------------|
| Primary action | `.pure-button` | Main task button (Build, Run, Save) |
| Secondary action | `.pure-button-secondary` | Alternative action (Cancel, Reset) |
| Text link | `.pure-button-link` | Navigation or low-priority action |
| Disabled | `.pure-button[disabled]` | Cannot perform action yet |

**Pattern:** Primary button = 1 per control, secondary = supporting actions, link = navigation

**Note:** Pure.css provides only `.pure-button` base styling. The `-secondary` and `-link` variants are **not** defined in Pure.css core. These classes are defined in `ui-foundation.css` or may require custom CSS to differentiate visual hierarchy. Check `ui-foundation.css` for current implementation or add styles as needed.

### Container Selection

| Content Type | Class | Max Width | Use Case |
|-------------|-------|-----------|----------|
| Control content | `.wc-container` | 1200px | Standard control layout |
| Full-width layout | `.wc-container--fluid` | 100% | Dashboard, console, maps |
| Reading content | `.wc-reading` | 65ch | Documentation, long text |

**Pattern:** Control = wc-container, console/dashboard = wc-container--fluid, docs = wc-reading

### Spacing Tokens

| Token | Value | Use Case |
|-------|-------|----------|
| `--wc-space-xs` | 0.25rem (4px) | Tight spacing (icon-text gap) |
| `--wc-space-sm` | 0.5rem (8px) | Button padding, form field gap |
| `--wc-space-md` | 1rem (16px) | Section spacing (default) |
| `--wc-space-lg` | 1.5rem (24px) | Major section dividers |
| `--wc-space-xl` | 2rem (32px) | Control-to-control spacing |

**Pattern:** Default = md (16px), tighter = sm (8px), sections = lg (24px), controls = xl (32px)

### Form Type Selection

| User Intent | Pure.css Class | Layout |
|------------|----------------|--------|
| Vertical labels | `.pure-form-stacked` | Label above field |
| Inline compact | `.pure-form-aligned` | Label beside field (11em left margin) |
| Single-line | `.pure-form` | No label structure |

**Pattern:** Default = pure-form-stacked (vertical), compact = pure-form-aligned (horizontal)

### WebSocket Status Patterns

| Event | Handler Method | Action |
|-------|----------------|--------|
| Connection opened | `onOpen(event)` | Show "Connected" message |
| Message received | `onMessage(data)` | Append to log panel |
| Connection closed | `onClose(event)` | Show "Disconnected", disable buttons |
| Connection error | `onError(error)` | Show error message, retry |

**Pattern:** Always provide onClose handler to prevent user confusion when WebSocket drops

---

## Troubleshooting

**Format:** Symptom → Cause → Fix (mechanical correction, no explanation)

### Blue checkboxes appearing
**Symptom:** Checkbox renders with browser default blue  
**Cause:** Missing wrapper class  
**Fix:**
```html
<!-- ❌ Before -->
<input type="checkbox" id="my-checkbox">

<!-- ✅ After -->
<div class="wc-choice wc-choice--checkbox">
  <input type="checkbox" id="my-checkbox">
  <label for="my-checkbox" class="wc-choice__label">Enable feature</label>
</div>
```

### Table overflows on mobile
**Symptom:** Wide table breaks layout on narrow screen  
**Cause:** Missing wrapper  
**Fix:**
```html
<!-- ❌ Before -->
<table class="wc-table">...</table>

<!-- ✅ After -->
<div class="wc-table-wrapper">
  <table class="wc-table">...</table>
</div>
```

### Status panel empty during task
**Symptom:** Log panel stays empty, no messages appear  
**Cause:** WebSocket not attached or wrong channel  
**Fix:**
```javascript
// Verify channel matches backend exactly
controller.base.attachStatusStream('panel-id', {
  channel: 'climate:' + runId  // Must match Redis pub/sub key
});
```

### Buttons respond when disabled
**Symptom:** Disabled button still fires click handler  
**Cause:** Event listener doesn't check disabled state  
**Fix:**
```javascript
button.addEventListener('click', function(e) {
  if (this.disabled) {
    e.preventDefault();
    return;
  }
  // Normal handler code
});
```

### Form has 11em left margin
**Symptom:** Form content shifted far right  
**Cause:** Using `.pure-form-aligned` instead of `.pure-form-stacked`  
**Fix:**
```html
<!-- ❌ Before -->
<form class="pure-form pure-form-aligned">

<!-- ✅ After -->
<form class="pure-form pure-form-stacked">
```

### Summary pane doesn't show
**Symptom:** Summary pane missing from control_shell  
**Cause:** Not passing `summary_panel_override` parameter  
**Fix:**
```jinja
{# Define summary first #}
{% set summary_html %}
<div class="wc-summary-pane">...</div>
{% endset %}

{# Then pass to control_shell #}
{% call control_shell(
    form_id="my-form",
    title="...",
    summary_panel_override=summary_html
) %}
```

### Advanced options don't collapse
**Symptom:** `<details>` element doesn't expand/collapse  
**Cause:** Missing required classes  
**Fix:**
```html
<!-- ❌ Before -->
<details>
  <summary>Advanced</summary>
  <div>content</div>
</details>

<!-- ✅ After -->
<details class="wc-advanced-options">
  <summary class="wc-advanced-options__summary">Advanced Options</summary>
  <div class="wc-advanced-options__content">
    <div class="pure-form pure-form-stacked">
      content
    </div>
  </div>
</details>
```

---

## Testing Checklist for New Controls

- [ ] Renders correctly without JavaScript enabled (progressive enhancement)
- [ ] All form fields have associated `<label>` elements
- [ ] Focus outlines visible when tabbing through controls
- [ ] Error messages announced to screen readers (`role="alert"` or `aria-live`)
- [ ] Color not the only indicator of state (use icons/text too)
- [ ] Mobile: Tables scroll horizontally, forms stack properly
- [ ] Mobile: Touch targets at least 44×44px
- [ ] Reduced motion: No unnecessary animations
- [ ] Status panel connects to WebSocket and receives messages
- [ ] Summary pane updates when state changes
- [ ] Advanced options collapse/expand without JavaScript errors

---

## Design philosophy

### The "Zero-Aesthetic" Reality
**UI work is a time sink.** The developer wants to spend zero time on aesthetics and minimal time on layout. The goal: stand up usable, consistent UI functionality fast with minimal human intervention.

**Compositional patterns with zero degrees of freedom:**
- **Grayscale only** - No color coordination bikeshedding. Black, white, grays. Done.
- **Single light theme** - No dual-theme maintenance burden (dark mode deferred to high-contrast inversion)
- **Token-based spacing** - Use `--wc-space-md`, never manual pixels
- **Pure.css grid** - 4KB, predictable, no Bootstrap complexity
- **Macro composition** - Assemble `control_shell` + `status_panel` + `button_row`, get consistent result
- **Pattern catalog** - If user says X, agent uses pattern Y. No interpretation.

**Developer velocity metrics:**
- **Time to new control:** <5 minutes (template copy + variable fill)
- **Styling decisions per control:** 0 (patterns handle everything)
- **Visual QA time:** <30 seconds (does it match other controls? Yes → ship)

**Critical note:** Velocity constraints operate **alongside** accessibility and usability guardrails, not instead of them. The "zero aesthetic decisions" philosophy eliminates subjective styling choices (colors, fonts, spacing values) but preserves WCAG AA compliance, keyboard navigation, semantic HTML, and progressive enhancement. Speed through constraints, quality through standards.

### Classic Design Principles (Still Apply)
- **Calm utility.** Prioritize legible data and workflows over decorative treatments. Pages should feel like professional tools: uncluttered backgrounds, strong hierarchy, and no ornamental gradients or corner rounding.
- **Pure.css first.** Load the Pure.css core and grid on every page and layer site-specific tokens from `static/css/ui-foundation.css`. Reach for Bootstrap only when Pure lacks a ready-made solution (e.g., modal scaffolding, large tabular navigation, or complex ToCs).
- **Zero-maintenance defaults.** Consolidate colors, type, spacing, and component rules inside the shared foundation stylesheet so individual pages do not need inline CSS. Prefer semantic HTML and Pure utility classes before hand-written overrides.
- **Consistent framing.** Every screen should share a header, generous breathing room, and predictable spacing rhythm so tool-to-tool navigation feels seamless.
- **Accessibility as baseline.** Follow WCAG AA contrast, ensure focus outlines remain visible, and keep interactive controls keyboard reachable without JavaScript dependencies.
- **Consistent, unstyled, unpretentious, simple, maintenable** Keep things simple and use patterns known to render in predictable manner.

## Technology stack
| Layer | Purpose | Notes |
| --- | --- | --- |
| Pure.css `pure-min.css`, `grids-responsive-min.css` | Baseline grid, buttons, and form styling | Vendor locally under `static/vendor/purecss/` using `static-src/build-static-assets.sh`—do **not** link to the CDN in templates.【F:wepppy/wepppy/weppcloud/static-src/scripts/build.mjs†L17-L129】|
| Avoid `.pure-form-aligned` control wrappers | They shift `.pure-controls` content 11em to the right; prefer our macros (`button_row`, `wc-stack`) to align buttons and helper text. | Built-in Pure alignment margins conflict with our layout tokens. |
| `static/css/ui-foundation.css` | Tokens & default element rules | Defines fonts, colors, spacing, table, form, status, pagination, tooltip, and accessibility patterns with zero rounded corners.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L10-L637】|
| Optional Bootstrap fragment | Specialized UI (modals, collapse, ToC) | Lazy-load per-page when Pure patterns are insufficient. |
| Minimal Alpine/Vanilla JS | Interactivity | Keep behavior isolated and framework-agnostic. |
| `static-src/build-static-assets.sh` | Vendor asset pipeline | Syncs npm + manual vendor sources into `static/vendor/` so Flask templates serve local copies without CDN dependencies.【F:wepppy/wepppy/weppcloud/static-src/build-static-assets.sh†L1-L64】|

### Contributor quick-start
1. Build vendor assets locally by running `static-src/build-static-assets.sh` (add `--prod` for release builds) so `static/vendor/` contains Pure and other third-party bundles.【F:wepppy/wepppy/weppcloud/static-src/build-static-assets.sh†L1-L64】【F:wepppy/wepppy/weppcloud/static-src/scripts/build.mjs†L17-L129】
2. Extend the shared base template in `templates/base_pure.htm` (or equivalent) so every page loads Pure + `ui-foundation.css`.
3. Replace bespoke wrappers with `.wc-container`, `.wc-page__body`, and `.wc-header` to inherit gutters, header spacing, and typography.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L123-L226】
4. Convert forms to `.pure-form` markup so they gain the shared focus outlines, input sizing, and stacked spacing.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L317-L360】
5. Swap Bootstrap buttons for `.pure-button` + `.pure-button-secondary`/`.pure-button-link` to reuse the accent palette and disabled states.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L362-L421】
6. Wrap data lists with `.wc-table` and `.wc-pagination` for consistent chrome on desktop and mobile without custom CSS.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L426-L443】【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L530-L557】

## Control components
- Use the shared macros in `templates/controls/_pure_macros.html` for any run control, console form, or reusable UI chunk. They ship keyboard/ARIA wiring and consistent spacing so individual templates stay lean.
- Treat `docs/ui-docs/control-ui-styling/control-components.md` as the contract source. Update that document (and the `/ui/components/` showcase) when you add args, adjust markup, or introduce a new pattern.
- Always render long-form controls with `ui.control_shell`. Set `collapsible=False` for console dashboards, add `form_class`/`form_attrs` for Pure form variants, and override panels via `status_panel_override`, `summary_panel_override`, or `stacktrace_panel_override` when needed.
- Prefer `status_panel(height=...)` instead of bespoke `<div>` logs. Use a small height (~`3.25rem`) for single-line run status and taller values (e.g., `300px`) for consoles. Pair every status panel with `StatusStream.attach` rather than duplicating WebSocket code.
- `stacktrace_panel` handles disclosure, focus, and monospace styling for exception payloads—reuse it anywhere you surface tracebacks.
- When you need to hide a side panel, pass "" (empty string) to the relevant override hook so the shell skips rendering it.
- Inputs inside controls should use the field macros (`text_field`, `numeric_field`, `select_field`, `checkbox_field`, `radio_group`, `textarea_field`, `file_upload`) to keep labelling, helper text, and error state semantics aligned.
- When a macro cannot express a layout detail (for example `<select>` elements with dynamic `<optgroup>` blocks), keep the markup minimal but wrap it in `.wc-field`, mirror the macro’s label/help pattern, and preserve IDs so the existing JavaScript bindings still resolve.
- Control summary panes should default to the shared `.wc-summary-pane` pattern unless a control’s documentation specifies a different layout:
  ```jinja
  <div class="wc-summary-pane">
    <dl class="wc-summary-pane__list">
      <div class="wc-summary-pane__item">
        <dt class="wc-summary-pane__term">Extent (xmin, ymax, xmax, ymin)</dt>
        <dd class="wc-summary-pane__definition">-116.427150301252, 45.226315684419845, -116.320333328386, 45.30166873028432</dd>
      </div>
      <div class="wc-summary-pane__item">
        <dt class="wc-summary-pane__term">Center (lon, lat)</dt>
        <dd class="wc-summary-pane__definition">-116.373741814819, 45.264004709690184</dd>
      </div>
      <!-- additional items -->
    </dl>
  </div>
  ```
  The foundation stylesheet already handles spacing, borders, and responsive behavior for this structure. Document any deviations in `docs/ui-docs/control-ui-styling/` so future controls stay consistent.

When adding or updating checkboxes/radio buttons, follow these conventions so spacing, colors, and accessibility stay predictable:

| Pattern | Guidance |
| --- | --- |
| Standalone checkbox | Wrap the `<input>` in `.wc-run-header__toggle` (for header placements) or `.wc-choice--checkbox` (general forms). Both enforce a 1rem square, `accent-color: var(--wc-color-accent)`, and label spacing. |
| Radio/checkbox groups | Use `.wc-choice` wrappers inside `.wc-choice-group`. Horizontal groups set `data-choice-group` or `.wc-choice-group--horizontal` to flip layout without inline CSS. |
| Dropdown/tucked controls | In dropdown menus (e.g., run header “More” menu), keep toggles inside `.wc-run-header__menu-content` so spacing and accent colors match other contexts. |
| Accessibility | Always pair inputs with visible labels (`<label>` or `.wc-choice__label`). Checkbox/radio macros already add `aria-describedby` hooks—mirror that pattern if hand-coding markup. |

Daily reminder: browsers default to blue checkboxes unless the relevant class sets `accent-color`. If you see blue, ensure `.wc-run-header__toggle`, `.wc-choice--checkbox`, or `.wc-choice` is applied.

### Base layout snippet
Embed the shared assets in a Jinja base template that other pages extend:

```html
<!doctype html>
<html lang="en" class="wc-page">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{% block title %}WEPPcloud{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/purecss/pure-min.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/purecss/grids-responsive-min.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/ui-foundation.css') }}">
    {% block head_extras %}{% endblock %}
  </head>
  <body class="wc-page">
    <header class="wc-header">
      <div class="wc-header__inner wc-container">
        <a class="wc-brand" href="{{ url_for('weppcloud_site.index') }}">WEPPcloud</a>
        <div class="wc-header__nav">
          {% block header_nav %}{% endblock %}
        </div>
        <div class="wc-header__tools">
          {% block header_tools %}{% endblock %}
        </div>
      </div>
    </header>
    <main class="wc-page__body">
      <div class="wc-container">
        {% block body %}{% endblock %}
      </div>
    </main>
    {% block footer %}{% endblock %}
    {% block script_extras %}{% endblock %}
  </body>
</html>
```

Run `static-src/build-static-assets.sh --prod` during releases (or `--force-install` when
dependencies change) to refresh the `static/vendor/` copies of Pure.css and other libraries.
If registry access is locked down, drop the official Pure.css builds into
`static-src/vendor-sources/purecss/` before running the script so the pipeline can mirror them
locally.【F:wepppy/wepppy/weppcloud/static-src/build-static-assets.sh†L1-L64】【F:wepppy/wepppy/weppcloud/static-src/scripts/build.mjs†L17-L129】【F:wepppy/wepppy/weppcloud/static-src/vendor-sources/purecss/README.md†L1-L6】

## Tokens, colors, and typography

### Color palette
| Token | Hex | Usage |
| --- | --- | --- |
| `--wc-color-text` | `#1f2328` | Primary text, icon fills.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L23-L34】|
| `--wc-color-text-muted` | `#636c76` | Secondary copy, helper text.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L23-L34】|
| `--wc-color-page` | `#f6f8fa` | App background, diff backdrops.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L17-L34】|
| `--wc-color-surface` | `#ffffff` | Panels, cards, dialogs.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L17-L34】|
| `--wc-color-surface-alt` | `#eef1f4` | Striped table rows, secondary blocks.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L17-L34】|
| `--wc-color-border` | `#d0d7de` | Default borders, inputs.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L21-L34】|
| `--wc-color-border-strong` | `#afb8c1` | Dividers that need extra weight.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L21-L34】|
| `--wc-color-accent` | `#24292f` | Primary actions, focus outlines.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L27-L34】|
| `--wc-color-positive` | `#1a7f37` | Success chips/rows.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L29-L34】|
| `--wc-color-attention` | `#9a6700` | Pending/queued states.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L31-L34】|
| `--wc-color-critical` | `#cf222e` | Error panels, destructive actions.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L33-L34】|

**Theme:** WEPPcloud ships a single light palette; dark mode overrides are intentionally not supported.

### Typography & spacing
- Font stacks: sans-serif UI text uses `Source Sans 3` with system fallbacks; monospace uses `Source Code Pro` family.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L10-L147】
- Base font size is 16px with heading sizes of 32/24/20/18/16/14 px for h1–h6, built into the stylesheet.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L72-L112】
- Spacing tokens (`--wc-space-*`) define consistent padding/margins—use multiples instead of ad-hoc pixel values.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L41-L48】
- Motion-sensitive defaults follow `prefers-reduced-motion` to disable transitions when requested, so interactive components remain comfortable for sensitive users.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L102-L111】

### Layout primitives
- `.wc-page`, `.wc-page__body`, `.wc-container`, and `.wc-reading` provide the basic shell, responsive gutters, and max widths.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L123-L147】
- `.wc-header` and `.wc-header__inner` replace Bootstrap’s navbar with a Pure-compatible header strip, including a mobile breakpoint that stacks controls for narrow screens.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L151-L226】
- `.wc-stack` is a single-column grid with `grid-template-columns: minmax(0, 1fr)` so nested panels, banners, or complex children never overflow the container while preserving consistent vertical rhythm.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L486-L493】
- Use `.wc-container--fluid` when a page needs to span the full viewport (e.g., wide tables). Override both `body_container_class` and `header_container_class` in `base_pure.htm` so the masthead aligns with the content. Document when you do this; fluid layouts should be rare and deliberate.【F:wepppy/wepppy/weppcloud/templates/base_pure.htm†L17-L34】【F:wepppy/wepppy/weppcloud/templates/user/runs2.html†L5-L7】【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L140-L148】
- Report-specific layout, dependencies, and CSV/table guidance live in `docs/report-ui-conventions.md`. Review that note before modifying report templates so they stay aligned with the shared header, unitizer requirements, and download conventions.
- All layout templates should import vendor CSS/JS via `url_for('static', ...)` paths so deployments never depend on external CDNs. If a new library is required, add it to the `static-src` pipeline instead of linking to third-party hosts.【F:wepppy/wepppy/weppcloud/static-src/build-static-assets.sh†L1-L64】【F:wepppy/wepppy/weppcloud/static-src/scripts/build.mjs†L17-L129】

## Component guidance

### Buttons
- Use native buttons or `.pure-button` paired with the shared accent palette. Buttons are flat, squared, and invert to the darker accent on hover.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L362-L407】
- `.pure-button-secondary` yields a neutral border-only alternative without introducing new colors; `.pure-button-link` provides a tertiary textual button without extra padding for inline actions.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L396-L421】
- Respect reduced motion preferences—no component should add custom transitions that bypass the global `prefers-reduced-motion` override.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L102-L111】

### Forms
- Prefer Pure’s stacked form markup (`.pure-form`, `.pure-control-group`). All fields inherit zero-radius borders and accessible focus outlines from the foundation stylesheet.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L317-L360】
- Group supporting text beneath inputs using muted text color (`var(--wc-color-text-muted)`).
- Authentication views use the shared `.wc-auth-card` container and `.pure-form-aligned` layout; reuse the Jinja macros in `security/_macros.html` so labels, inline messages, and controls stay consistent.【F:wepppy/wepppy/weppcloud/templates/security/_layout.html†L5-L20】【F:wepppy/wepppy/weppcloud/templates/security/_macros.html†L1-L46】

### Tables
- Apply `.pure-table` or `.wc-table` for full-width, borderless tables with alternating row backgrounds for scanability.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L521-L545】
- Pair `.wc-pagination` underneath multi-page datasets to keep navigation consistent and accessible (ARIA current markers, hover state).【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L804-L831】
- Wrap wide tables in `.wc-table-wrapper` so they scroll horizontally on narrow viewports instead of overflowing.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L1090-L1094】

### Panels & cards
- Wrap feature areas inside `.wc-panel` or `.wc-card` to keep consistent padding and squared borders.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L357-L364】【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L838-L842】

### Status & alerts
- `.wc-status` blocks provide consistent accenting for queued, success, and failure states without custom CSS per page. Pair them with iconography or concise labels so state isn’t communicated by color alone.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L551-L605】
- Use `.wc-status-chip` and `.wc-status-note` for streaming job feedback; pair with `.wc-spinner` for polling UI and `.wc-log` for live logs.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L573-L663】

### Navigation & toolbars
- Build inline action rows with `.wc-toolbar` and `.wc-inline` utilities to avoid bespoke flex snippets. Toolbars automatically stack on narrow screens for readability.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L772-L787】
- For global navigation, drop Bootstrap’s `.navbar` in favor of the base header snippet to eliminate dependency on Bootstrap classes entirely.
- Use `.wc-nav`, `.wc-nav__list`, and `.wc-nav__link` for primary navigation in the header—links inherit spacing, hover, and focus states tuned to the foundation palette.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L214-L237】
- Accent run headings with `.wc-heading__run` anchors inside `.wc-heading__title` to highlight critical identifiers without custom inline styles.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L214-L247】【F:wepppy/wepppy/weppcloud/routes/readme_md/templates/readme_view.htm†L8-L21】

### Console layout macros
- Centralize console-style scaffolding (archive dashboard, fork console, README tools, query console) with the shared macros in `templates/shared/console_macros.htm`; they keep headers, action rows, and button sizing aligned across routes.【F:wepppy/wepppy/weppcloud/templates/shared/console_macros.htm†L1-L68】
- `console_page` wraps the page body with the standard `.wc-stack` container and optionally injects the command bar, while `console_header` renders the run link/title, optional subtitle, and action buttons inside the `.wc-console-header` flex shell. `button_row` standardizes button spacing inside or outside Pure form controls.
- Typical usage:

  ```jinja
  {% from "shared/console_macros.htm" import console_page, console_header, button_row %}
  {% call console_page(data_controller="archive-dashboard") %}
    {% call console_header(run_link=run_url, run_label=runid, title="Archive Dashboard") %}
      <p class="wc-text-muted">Create and manage project archives.</p>
    {% endcall %}
    <section class="wc-panel wc-stack">
      <form class="pure-form pure-form-aligned">
        {% call button_row(form_controls=True) %}
          <button type="submit" class="pure-button">Create archive</button>
          <button type="button" class="pure-button pure-button-secondary">Refresh list</button>
        {% endcall %}
      </form>
    </section>
  {% endcall %}
  ```

- Starlette surfaces that render these macros (e.g., the query engine) must extend their `Jinja2Templates` loader to include `weppcloud/templates` so the shared partials resolve next to app-local templates.【F:wepppy/wepppy/query_engine/app/server.py†L33-L40】

### Tabular controls inside `control_shell`
- Wrap any tabular data in `<div class="wc-table-wrapper">` + `<table class="wc-table">` to inherit the shared spacing, border, and responsive rules. Avoid Bootstrap’s `.table` classes—Pure + our foundation utilities already deliver the chrome and mobile collapse behavior.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L426-L443】
- Keep the table markup semantic (thead/tbody/th/td). Apply additional layout tokens to cells rather than rows; e.g., `.wc-table__numeric` or custom helpers like `.wc-landuse-report__cell--numeric` ensure the padding survives display differences across browsers.
- For inline form controls inside tables, stick with raw `<select>`/`<input>` elements and add `disable-readonly` (so the global read-only toggle still works) plus small utility classes (`.wc-inline`, `.wc-landuse-report__select`) to control width. Avoid the `select_field` macro inside tight cells—it wraps extra grid markup that can break table layouts.
- Use `<details>` for collapsible rows rather than Bootstrap’s collapse. Pair it with a table row that toggles `is-open` so the detail row stays visually tied to the summary. The landuse report pattern (`.wc-landuse-report__summary`, `.wc-landuse-report__details-row`, `.wc-landuse-report__collapse`) demonstrates this approach: the summary row carries the action button and inline selects, and the detail row contains extended controls with additional spacing tokens.
- When tables appear inside a `control_shell`, keep consistent vertical rhythm by:
  * adding bottom padding on each summary row (`.wc-landuse-report__summary > td { padding-bottom: var(--wc-space-lg); }`), and
  * resetting the padding on the last summary row so the table footer aligns with surrounding panels.
- Always ensure interactive elements within tables have proper aria attributes (`aria-controls`, `aria-expanded`, `aria-describedby`) so keyboard users understand the relationship between the action button and the collapsible content.

### Modal/dialogue content
- When Bootstrap modals are required, apply `.pure-modal` on the dialogue content to keep typography, spacing, and squared edges in sync, benefiting from the shared medium elevation shadow.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L846-L850】
- **Pure modal pattern (`modal.js`):** Use the `data-modal` attribute system for lightweight modals without Bootstrap. Follow the markup conventions in `templates/controls/unitizer_modal.htm`:
  * Wrap the modal in `<div class="wc-modal" id="modalId" data-modal hidden>`
  * Include `data-modal-dismiss` on overlay and close buttons
  * Trigger with `<button data-modal-open="modalId">`
  * The modal manager (`controllers_js/modal.js`) handles focus trapping, Escape key, and accessibility
- **Critical implementation note:** When a modal opens, `modal.js` adds `data-modal-open="true"` to track state. The `handleOpenClick` function checks if the attribute value is "true" (state marker) vs. a modal ID (trigger) to prevent `preventDefault()` from blocking form interactions inside the modal. Do not modify this logic without testing interactive form controls (radios, checkboxes, selects) inside the modal.
- **Testing & validation:** The modal system is relatively new (introduced October 2025). Before migrating Bootstrap modals or creating complex modal content:
  * Start with simple modals (confirmation dialogs, read-only content) to validate the pattern
  * Test with plain text, buttons, and links before adding complex forms
  * Add interactive form controls (radios, checkboxes, selects, inputs) incrementally
  * Verify keyboard navigation (Tab, Shift+Tab, Escape) works correctly
  * Check that form submissions and change events fire as expected
  * The unitizer modal serves as a reference implementation but was a complex first use case - simpler modals are recommended for pattern validation
- Always test interactive form elements (especially radio buttons and checkboxes) inside modals to ensure click events aren't being prevented by modal event handlers. If adding complex forms to modals, consider whether a dedicated page might be simpler until the modal pattern matures.

### Tooltip primitives
- Use `.wc-tooltip` and `.wc-tooltip__bubble` to create accessible hover/focus descriptions without importing additional libraries. Anchor the bubble with `aria-describedby` IDs and toggle via CSS/JS as needed.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L617-L637】

### Logs & consoles
- Wrap console pages in `.wc-console` grids and use `.wc-panel` to frame tools, tables, and status messages.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L639-L663】
- `.wc-log` provides a reusable monospace log surface with built-in overflow handling.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L645-L663】
- Use `.wc-code-input` and `.wc-code-block` for JSON editors or stack traces so typography and spacing stay consistent.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L735-L760】

## Content display patterns
- **Reading views (Markdown, documentation):** wrap in `.wc-reading` to constrain width and rely on the markdown overrides already in the foundation file.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L146-L147】【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L876-L883】
- **README editor:** use `.wc-editor-grid` with `.wc-editor-textarea` and `.wc-editor-preview` to keep the split view responsive; overlay locks reuse `.wc-overlay` helpers.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L672-L722】
- **Data consoles (logs, monitors):** use `.wc-panel` with monospace text and `.wc-status` for live status chips; pair with `.wc-table` for job lists.
- **Dashboards:** structure as stacked `.wc-panel` elements with `.wc-toolbar` headings, each focusing on a single job/action set.
- **Paginated datasets:** combine `.wc-table` with `.wc-pagination` and ensure the current page link uses `aria-current="page"` so screen readers announce context.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L426-L443】【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L530-L557】
- **Contextual tips:** surface brief guidance using `.wc-tooltip` tied to icons or labels; ensure the tooltip content is duplicated inline for screen readers when the information is critical.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L617-L637】
- **Logs & metrics:** use `.wc-log` alongside `.wc-status-chip` to stream job output; wrap supporting metadata in `.wc-meta-list`.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L573-L663】
- **Static assets:** whenever you add or update third-party CSS/JS, update `static-src/scripts/build.mjs` and rerun `build-static-assets.sh` so production pulls from local files rather than CDNs.【F:wepppy/wepppy/weppcloud/static-src/build-static-assets.sh†L1-L64】【F:wepppy/wepppy/weppcloud/static-src/scripts/build.mjs†L17-L129】

## Accessibility checklist
- Maintain the default focus outline supplied by the foundation CSS (solid 2px accent) to keep keyboard navigation visible, including `:focus-visible` states.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L342-L355】
- Ensure icon-only buttons include `aria-label` attributes and at least the `.wc-inline` spacing utility so hit targets remain comfortable.
- Keep content inside 70–80 character line lengths (`.wc-reading`) for long-form copy and docs.
- Honor user preferences: do not reintroduce animations or transitions beyond the shared defaults so the global reduced-motion override can do its job.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L102-L111】

## Implementation playbook
1. **Create/extend a Pure base template.** Migrate templates to extend a common layout that loads Pure + the foundation stylesheet. Replace Bootstrap header includes (`header/_layout_fixed.htm`) with the new header block.
2. **Extract inline CSS.** Move inline styles from templates (home page banners, security forms, Deval loading state) into component-specific partials or reuse `.wc-panel`, `.wc-status`, and `.wc-toolbar` primitives.
3. **Refactor page clusters.** Update one feature cluster at a time (browse, archive dashboard, authentication, run controls) to use Pure grids and the foundation tokens, verifying there are no rounded corners or drop shadows beyond the shared defaults.
4. **Audit Bootstrap usage.** If a page only uses Bootstrap utilities (e.g., `.row`, `.btn`), replace them with Pure equivalents; keep Bootstrap loaded only where widgets like modals remain. When Bootstrap (or any vendor asset) is still needed, ensure the reference comes from `static/vendor/` with the build script instead of a CDN URL.【F:wepppy/wepppy/weppcloud/static-src/build-static-assets.sh†L1-L64】
5. **Document patterns.** As layouts are migrated, note reusable snippets in this guide so new routes stay aligned.
6. **Capture references.** Update the shared visual reference folder with new screenshots whenever you land a significant template refactor so future contributors can see expected results.

## Site-wide assessment & unification plan

### Global observations
- **Split frameworks:** Many templates rely on Bootstrap’s navbar and grid (e.g., `_layout_fixed.htm`), while others are hand-styled or framework-free, causing inconsistent spacing and typography.【F:wepppy/wepppy/weppcloud/templates/header/_layout_fixed.htm†L1-L8】
- **Inline styling:** Landing, archive, Deval, and security pages embed large `<style>` blocks, making maintenance tedious and undermining consistency.【F:wepppy/wepppy/weppcloud/templates/index.htm†L15-L90】【F:wepppy/wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm†L11-L26】【F:wepppy/wepppy/weppcloud/templates/reports/deval_loading.htm†L9-L133】【F:wepppy/wepppy/weppcloud/templates/security/login_user.html†L68-L97】
- **Missing global header:** Browse and several microservice pages omit the site header entirely, so users lose navigation context.【F:wepppy/wepppy/weppcloud/routes/browse/templates/browse/directory.htm†L1-L47】

### Page-by-page notes

1. **Browse interface (`routes/browse/templates/browse/*.htm`)**
   - *Current state:* Lean HTML with minimal monospace styling and no Bootstrap dependencies; aligns with the desired utilitarian feel.【F:wepppy/wepppy/weppcloud/routes/browse/templates/browse/directory.htm†L17-L47】
   - *Action:* Keep the minimalist approach, but wrap output in the shared layout for header consistency and swap inline styles for `.wc-table`/`.wc-inline` utilities.

2. **Archive dashboard (`routes/archive_dashboard/templates/rq-archive-dashboard.htm`)**
   - *Current state:* Pulls full Bootstrap CSS/JS and jQuery for layout and modals; log panel mixes serif fonts and rounded boxes.【F:wepppy/wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm†L5-L26】
   - *Action:* Replace Bootstrap grid/buttons with Pure equivalents, restyle the log with `.wc-panel` + monospace, and limit Bootstrap to the modal markup (or reimplement modals with native `<dialogue>` + `.pure-button`).

3. **Deval loading screen (`templates/reports/deval_loading.htm`)**
   - *Current state:* Custom card UI with rounded corners, pill status chips, drop shadows, and accent colors that differ from the rest of the app.【F:wepppy/wepppy/weppcloud/templates/reports/deval_loading.htm†L21-L133】
   - *Action:* Strip to a `.wc-panel` + `.wc-status` layout, reuse shared accent colors, and remove pill treatment to match the “no rounded corners” directive.

4. **Flask-Security auth templates (`templates/security/*.html`)**
   - *Current state:* Base layout still imports Bootstrap and custom `style.css`, while individual forms define their own CSS (rounded cards, shadows).【F:wepppy/wepppy/weppcloud/templates/security/_layout.html†L5-L18】【F:wepppy/wepppy/weppcloud/templates/security/login_user.html†L6-L97】
   - *Action:* Point `_layout.html` to the Pure base template, drop Bootstrap, and rebuild the forms with `.pure-form` + `.wc-panel`. Use `.wc-status[data-state="critical"]` for error messaging instead of bespoke classes.

5. **Landing page (`templates/index.htm`)**
   - *Current state:* Uses Bootstrap jumbotrons, inline banner styles, and ad-hoc spacing wrappers, leading to inconsistent typography and lots of manual padding adjustments.【F:wepppy/wepppy/weppcloud/templates/index.htm†L10-L188】
   - *Action:* Convert hero sections to Pure grid (`pure-g`) with `.wc-panel` wrappers, move banner styling into a reusable notice pattern, and normalize buttons using `.pure-button`.

6. **Run control panels (`templates/controls/_base.htm` and derivatives)**
   - *Current state:* Bootstrap grid classes (`col-md-*`, `.form-group`) and inline spacing dominate, producing cramped layouts on small screens.【F:wepppy/wepppy/weppcloud/templates/controls/_base.htm†L1-L19】
   - *Action:* Replace the outer grid with Pure’s responsive columns, move status blocks into `.wc-status`, and rely on shared spacing tokens instead of inline `style` attributes.

7. **Usersum Markdown views (`routes/usersum/templates/usersum/layout.j2`)**
   - *Current state:* Imports GitHub’s markdown stylesheet and applies generous padding via inline CSS; visually close to the target but lacks the shared header and palette.【F:wepppy/wepppy/weppcloud/routes/usersum/templates/usersum/layout.j2†L1-L28】
   - *Action:* Drop the GitHub CSS in favor of `.wc-reading` + markdown overrides already present in the foundation file to reduce external dependencies.

## Next steps & tracking
- Stand up an “interface audit” checklist in issue tracking using the sections above as milestones (browse, archive, auth, home, controls, reports).
- After each cluster migration, remove unused Bootstrap imports and inline styles to keep the codebase lean.
- Refresh this guide as new shared components emerge (e.g., pagination, diff viewers) so future contributions stay aligned with the cohesive visual language, and capture any updates to the static asset pipeline as libraries change versions.
- Integrate the shared Stylelint ruleset (`.stylelintrc.json`) into CI so linting enforces the “no rounded corners” + token usage expectations automatically.【F:.stylelintrc.json†L1-L21】
- Run a lightweight accessibility audit (Lighthouse or ax) after major migrations to confirm the light palette, focus outlines, and reduced-motion defaults behave as intended.

## Visual references & demos
- Store screenshots or short GIFs that demonstrate core layouts under `docs/ui-reference/`. Capture at least: base layout shell, Pure form, table + pagination, status banner, tooltip example, and a dark-mode rendering.
- Regenerate assets after significant CSS updates to keep the visuals synchronized with the written guidelines.
- Use descriptive filenames (e.g., `header-light.png`, `table-dark.png`) and embed them in this guide or related documentation as needed.

## JavaScript interaction principles
- Favor progressive enhancement: ensure modals, tooltips, and accordions render helpful content even when JavaScript is unavailable.
- Keep interactions framework-agnostic. Lightweight Alpine.js sprinkles are acceptable, but they should operate on semantic HTML and classes defined here.
- When introducing new JS-driven UI, pair it with CSS hooks inside `ui-foundation.css` (e.g., data attributes) so behavior and presentation remain decoupled.

## Validation & automation
- Use Stylelint with the shared config to block forbidden patterns such as `border-radius` values other than `var(--wc-radius-none)` and to require the `wc-` namespace for shared utilities.【F:.stylelintrc.json†L1-L21】
- Prettier (or an equivalent formatter) can be pointed at template directories to enforce indentation and whitespace consistency; avoid inline styles so linting remains effective.
- During review, spot-check new CSS against the token tables—if a new color is required, add it as a token rather than embedding raw hex codes.

## Guide change log
- **2025-10-17:** Added dark-mode tokens, reduced-motion defaults, pagination/tooltip primitives, contributor quick-start, validation guidance, and a visual reference process.
- **2024-04-05:** Initial publication covering Pure.css-first philosophy, tokens, assessment, and migration plan.
