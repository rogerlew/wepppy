# VS Code Theme Integration – System Documentation
> **Status:** ✅ Production · **Last Updated:** 2025-12-22  
> **Work Package:** [`docs/work-packages/20251027_vscode_theme_integration/`](/workdir/wepppy/docs/work-packages/20251027_vscode_theme_integration/)  
> **Audience:** UI contributors, operations engineers, stakeholders evaluating theme additions

## Overview
The weppcloud theme system reuses curated VS Code themes to populate CSS custom properties so the interface inherits a complete palette without any bespoke design work. Thirteen generated themes ship today (plus the default base palette), the catalog is capped to keep choices intentional, and the pipeline—from token mapping to runtime persistence—does not require template or Pure control changes unless you want to expose new themes in the UI.

### Production Snapshot
| Category | Detail |
|----------|--------|
| Catalog | 13 generated themes (Ayu x6, Cursor x4, OneDark, Dark Modern, Light High Contrast) + default base palette in `ui-foundation.css` |
| Exposure | Header switcher exposes 12 non-default themes; Theme Lab/metrics uses a curated list (excludes `cursor-light`, `light-high-contrast`) |
| Mapping | `wepppy/weppcloud/themes/theme-mapping.json` drives token → CSS variable conversion with per-theme overrides |
| Payload | `static/css/themes/all-themes.css` ≈15.9 KB raw (≈2.2 KB gzipped), delivered once and cached |
| Persistence | `wc-theme` stored in `localStorage`; `controllers_js/theme.js` toggles `data-theme` |
| Accessibility | Token-based WCAG checks emitted by the converter; latest report (2025-10-28) covers 11 themes, 5 passing |

### User Experience
- Theme picker lives in the header; selections apply instantly and persist via `localStorage`.
- Default palette is the no-attribute state in `ui-foundation.css`; themes override variables in `all-themes.css`.
- FOUC prevention is only in `gl_dashboard.htm` today; other pages rely on `theme.js` after DOMContentLoaded.

## Architecture

### Mapping Workflow
- VS Code color tokens feed CSS variables through a declarative config (`theme-mapping.json`).
- Each variable lists tokens in priority order plus a fallback value.
- Per-theme overrides live under `themes.<slug>.overrides` (optional per-variable overrides are also supported).

```json
{
  "--wc-color-surface": {
    "description": "Primary panel/card background",
    "fallback": "#ffffff",
    "tokens": ["editor.background", "editorWidget.background"]
  }
}
```

Example override:
```json
"themes": {
  "onedark": {
    "overrides": {
      "--wc-color-border": "#181A1F",
      "--wc-color-border-strong": "#0F1115"
    }
  }
}
```

### Build Pipeline
```text
VS Code theme JSON
    ↓ parse + validate
convert_vscode_theme.py  (static-src/scripts/)
    ↓ applies theme-mapping.json + overrides
static/css/themes/<theme>.css
    ↓ concatenated
static/css/themes/all-themes.css  (≈2.2 KB gzipped)
```

Key tooling (`wepppy/weppcloud/static-src/scripts/convert_vscode_theme.py`):
- `--theme <slug>` converts only the specified theme(s) (repeatable).
- `--validate-only` confirms required tokens resolve before writing files.
- `--output-dir <path>` overrides the output directory (per-theme files + combined bundle).
- `--combined-file <name>` overrides the combined bundle filename.
- `--report` / `--md-report` generate JSON or Markdown contrast summaries for audits.
- `--reset-mapping` restores the default mapping when experimentation goes sideways.

### Runtime Behavior
- `controllers_js/theme.js` reads/writes `wc-theme`, applies `data-theme`, and dispatches `wc-theme:change`.
- Themes are derived from `<select data-theme-select>` options; selects are kept in sync.
- Default theme removes `data-theme` and clears `localStorage`.
- `gl_dashboard.htm` sets the theme before paint; other templates do not.

```javascript
(function (global) {
  var STORAGE_KEY = "wc-theme";
  var SELECTOR = "[data-theme-select]";
  var root = global.document ? global.document.documentElement : null;

  function applyTheme(theme) {
    if (!root) {
      return;
    }
    if (!theme || theme === "default") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
  }

  function init() {
    if (!root || !global.document) {
      return;
    }
    var selects = global.document.querySelectorAll(SELECTOR);
    if (!selects.length) {
      return;
    }
    var stored = global.localStorage.getItem(STORAGE_KEY);
    var initial = stored || root.getAttribute("data-theme") || "default";
    applyTheme(initial);
    // sync selects + listen for change...
  }

  if (global.document && global.document.readyState === "loading") {
    global.document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
}(typeof globalThis !== "undefined" ? globalThis : window));
```

### File Layout
```text
wepppy/weppcloud/
├── themes/
│   ├── theme-mapping.json         # Token mapping + overrides (author-editable)
│   ├── theme-mapping.defaults.json # Defaults used by --reset-mapping
│   ├── themes-contrast.json/md    # Optional contrast reports
│   ├── OneDark.json               # Source VS Code themes (examples)
│   └── …                          # Additional source JSON
├── static/
│   └── css/
│       ├── ui-foundation.css      # Default palette + base variables
│       └── themes/
│           ├── *.css              # Generated per-theme outputs
│           └── all-themes.css     # Combined bundle loaded on every page
└── controllers_js/
    └── theme.js                   # Runtime manager (bundled automatically)
```

## Operations

### Quick Start: Add a VS Code Theme
1. **Acquire the theme JSON**
   ```bash
   find ~/.vscode/extensions -path "*/themes/*" -name "*<theme-name>*.json"
   cp ~/.vscode/extensions/publisher.theme-1.0.0/themes/Theme.json \
      /workdir/wepppy/wepppy/weppcloud/themes/
   ```
2. **Add a mapping entry**
   - Add a `themes.<slug>` entry in `theme-mapping.json` with `label`, `source`, `variant`, and any overrides.
3. **Validate and convert**
   ```bash
   cd /workdir/wepppy/wepppy/weppcloud/static-src/scripts
   python convert_vscode_theme.py --theme <slug> --validate-only
   python convert_vscode_theme.py --theme <slug>
   ```
4. **Adjust mapping if colors miss the mark**  
   Edit `theme-mapping.json` to add overrides, then rerun the converter.
5. **Register the theme in the UI**  
   - Add an `<option>` to `wepppy/weppcloud/templates/header/_theme_switcher.htm`.  
   - If it should appear in Theme Lab/metrics, add it to `THEME_OPTIONS` in `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` (otherwise add it to the exclusions list below).
6. **Refresh and smoke-test**  
   - CSS changes take effect on reload.  
   - Template changes may require a restart depending on environment caching.  
   Confirm the theme across maps, tables, and forms.
7. **Document and archive**  
   Update the catalog tracker under `docs/work-packages/20251027_vscode_theme_integration/notes/` with accessibility notes.

### Maintenance Checklist
- All catalog themes produce outputs via the converter (no hand-edited CSS).
- `themes-contrast.md` regenerated whenever a theme or mapping changes.
- Header dropdown (`_theme_switcher.htm`) and Theme Lab (`THEME_OPTIONS`) stay in sync with desired exposure.
- Theme Lab exclusions list stays current when intentionally skipping themes.
- `all-themes.css` rebuilt by the converter after any addition or removal.
- If print fallback is required, add `@media print` overrides in `ui-foundation.css`.

## Accessibility & Quality
- The converter runs token-based WCAG AA checks; failures emit actionable warnings before CSS is written.
- Latest stored report (2025-10-28) covers 11 themes with 5 passing (goal ≥ 75%). Rerun after catalog changes.
- Guardrails to watch:
  - `--wc-color-text` vs. `--wc-color-surface`
  - `--wc-color-link` vs. `--wc-color-page`
  - Focus outlines inherit `--wc-color-accent` (or optional `--wc-color-focus`) and should hold ≥3:1 contrast.
- When overrides cannot rescue a palette, ship an “Accessible” variant rather than diluting the base catalog.

### Theme Lab & Metrics
- `/weppcloud/ui/components/#theme-lab` hosts the canonical specimens (buttons, helper text, radios, checkboxes, Leaflet zoom controls) that the automation harness inspects. Keep this page in sync with macro updates so the rendered sample always matches production markup.
- Theme IDs are pulled from the Theme Lab `<select data-theme-select>` list (`THEME_OPTIONS` in `ui_showcase_bp.py`).
- Theme Lab exclusions (intentional): `cursor-light`, `light-high-contrast`.
- Run the contrast suite locally with `npm run smoke:theme-metrics` from `wepppy/weppcloud/static-src/` or through the CLI via `wctl2 run-playwright --suite theme-metrics --env local`. The harness simply hits the Theme Lab and does **not** require run provisioning, but the backend must be running so the page renders.
- Results are written to `wepppy/weppcloud/static-src/test-results/theme-metrics/theme-contrast.{json,md}`. Attach the Markdown table to PRs when tweaking `theme-mapping.json` to prove contrast moved in the right direction.
- Implementation details and expansion plan live in `docs/ui-docs/theme-metrics.spec.md`.

### Catalog Health
| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Catalog size | 6 – 12 themes | 13 generated (12 non-default in header, 11 non-default in Theme Lab) | Above target; avoid decision fatigue |
| Guaranteed coverage | ≥1 light, ≥1 dark AA-compliant | ✅ (2025-10-28 report) | Cursor Light + Ayu dark variants |
| Accessibility pass rate | ≥75% AA compliant | 5/11 (45%) in latest converter report | Prioritize Ayu Light + Cursor variants |
| Bundle size | ≤15 KB gzipped | ≈2.2 KB gzipped (15.9 KB raw) | Plenty of headroom |

## Troubleshooting
- **Theme renders incorrectly:** Re-run the converter with `--validate-only` to confirm tokens; add per-theme overrides for missing or unsuitable values.
- **Theme missing from dropdown:** Ensure `_theme_switcher.htm` (header) and `THEME_OPTIONS` (Theme Lab) include the key as intended, then rebuild `all-themes.css`.
- **Contrast warnings:** Check `themes-contrast.md` (converter) and `static-src/test-results/theme-metrics/` (Playwright); patch `theme-mapping.json` overrides and regenerate the CSS.
- **FOUC on first load:** Only `gl_dashboard.htm` sets `data-theme` before paint. Add a small inline boot script to `base_pure.htm` if you need this everywhere.
- **Print outputs unreadable:** No print-specific overrides exist today; add `@media print` rules in `ui-foundation.css` if needed.

## Zero-Aesthetic Alignment
| Principle | Result | Notes |
|-----------|--------|-------|
| No bespoke palettes | ✅ Themes imported from community JSON | Development workflow stays “copy → fill → ship”. |
| Minimal maintenance | ✅ Declarative mapping + converter CLI | Stakeholders tweak JSON; `--reset-mapping` provides escape hatch. |
| Pattern-first UI | ✅ Pure controls untouched | Only CSS variables change; layout and markup remain stable. |
| User choice, developer neutrality | ✅ Theme picker is user-facing | Default theme remains grayscale to honor original aesthetic. |

## Roadmap
- Optional per-user theme sync via profile settings (falls back to device-local storage).
- Respect `prefers-color-scheme` for first-run defaults.
- Ship accessible variants for popular dark themes (OneDark, Ayu Mirage).
- Add guided preview tooling (e.g., `/themes/preview/<id>`) for catalog reviews.
- Evaluate controlled custom uploads for power users with explicit support boundaries.

## References
- VS Code theme color reference: https://code.visualstudio.com/api/references/theme-color
- WCAG 2.1 contrast guidance: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum
- UI foundation stylesheet: `wepppy/weppcloud/static/css/ui-foundation.css`
- Theme converter: `wepppy/weppcloud/static-src/scripts/convert_vscode_theme.py`
- Catalog tracker: `docs/work-packages/20251027_vscode_theme_integration/notes/themes_inventory.md`

---

**Document owner:** GitHub Copilot (AI Agent)  
**System status:** Production, monitored  
**Next review:** Align with next theme catalog update or accessibility audit
