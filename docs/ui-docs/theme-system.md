# VS Code Theme Integration – System Documentation
> **Status:** ✅ Production · **Last Updated:** 2025-10-28  
> **Work Package:** [`docs/work-packages/20251027_vscode_theme_integration/`](/workdir/wepppy/docs/work-packages/20251027_vscode_theme_integration/)  
> **Audience:** UI contributors, operations engineers, stakeholders evaluating theme additions

## Overview
The weppcloud theme system reuses curated VS Code themes to populate CSS custom properties so the interface inherits a complete palette without any bespoke design work. Eleven production themes ship today, the catalog is capped to keep choices intentional, and the entire pipeline—from token mapping to runtime persistence—runs without touching the Flask templates or Pure controls.

### Production Snapshot
| Category | Detail |
|----------|--------|
| Catalog | 11 shipped themes: Default, OneDark, Ayu family (7 variants), Cursor family (3 variants) |
| Mapping | `wepppy/weppcloud/themes/theme-mapping.json` drives token → CSS variable conversion with per-theme overrides |
| Payload | `static/css/themes/all-themes.css` ≈10 KB gzipped, delivered once and cached |
| Persistence | `wc-theme` stored in `localStorage`; inline boot script sets `data-theme` to avoid FOUC |
| Accessibility | Automated WCAG AA checks during conversion; 6/11 themes currently pass in production |

### User Experience
- Theme picker lives in the header; selections apply instantly and persist across sessions.
- FOUC is prevented by setting `data-theme` before paint; print media falls back to the default light palette.
- The runtime never recalculates CSS—switching a theme only swaps CSS variables.

## Architecture

### Mapping Workflow
- VS Code color tokens feed CSS variables through a declarative config (`theme-mapping.json`).
- Each mapping lists multiple tokens in priority order plus a fallback value.
- Per-theme overrides adjust individual variables without rewriting the base mapping file.

```json
{
  "css_var": "--wc-color-surface",
  "vscode_tokens": ["editor.background", "editorWidget.background"],
  "fallback": "#ffffff",
  "description": "Primary panel/card background"
}
```

Example override:
```json
"overrides": {
  "themes": {
    "onedark": {
      "--wc-color-page": {
        "vscode_tokens": ["editorGroupHeader.tabsBackground"],
        "reason": "Default background reads too dark for page chrome"
      }
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
static/css/themes/all-themes.css  (≈10 KB gzipped)
```

Key tooling (`wepppy/weppcloud/static-src/scripts/convert_vscode_theme.py`):
- `--validate-only` confirms required tokens resolve before writing files.
- `--output <path>` emits a dedicated CSS file; `all-themes.css` is rebuilt from the individual outputs.
- `--report` / `--md-report` generate JSON or Markdown contrast summaries for audits.
- `--reset-mapping` restores the default mapping when experimentation goes sideways.

### Runtime Behavior
- `controllers_js/theme.js` reads `wc-theme` from `localStorage`, assigns `data-theme`, then stores updates.
- A small inline script executes before the main bundle to set `data-theme` and prevent FOUC.
- `ui-foundation.css` defines the default (grayscale) palette; themed overrides live in `all-themes.css`.
- Print styles flip back to the default theme to keep dark palettes from burning toner.

```javascript
class ThemeManager {
  static THEMES = {
    default: 'Default Light',
    onedark: 'One Dark',
    'ayu-dark': 'Ayu Dark',
    'ayu-light': 'Ayu Light',
    'ayu-mirage': 'Ayu Mirage',
    'cursor-dark': 'Cursor Dark',
    // … other catalog entries
  };

  static get() {
    return localStorage.getItem('wc-theme') || 'default';
  }

  static set(themeId) {
    document.documentElement.setAttribute('data-theme', themeId);
    localStorage.setItem('wc-theme', themeId);
  }

  static init() {
    ThemeManager.set(ThemeManager.get());
  }
}

document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
```

### File Layout
```text
wepppy/weppcloud/
├── themes/
│   ├── theme-mapping.json         # Token mapping + overrides (author-editable)
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
2. **Validate and convert**
   ```bash
   cd /workdir/wepppy/wepppy/weppcloud/static-src/scripts
   python convert_vscode_theme.py ../../themes/Theme.json --validate-only
   python convert_vscode_theme.py ../../themes/Theme.json \
     --output ../../static/css/themes/theme.css
   ```
3. **Adjust mapping if colors miss the mark**  
   Edit `theme-mapping.json` to add overrides, then rerun the converter.
4. **Register the theme in the UI**  
   - Add an `<option>` to `wepppy/weppcloud/templates/header/_theme_switcher.htm`.  
   - Register the human-readable label in `ThemeManager.THEMES`.
5. **Rebuild the combined bundle**  
   Use the existing asset build (`wctl build-static-assets`) or concatenate individual CSS files into `all-themes.css`.
6. **Restart and smoke-test**  
   `wctl restart weppcloud`, then confirm the theme across maps, tables, and forms; run print preview to verify the fallback.
7. **Document and archive**  
   Update the catalog tracker under `docs/work-packages/20251027_vscode_theme_integration/notes/` with accessibility notes.

### Maintenance Checklist
- All catalog themes produce outputs via the converter (no hand-edited CSS).
- `themes-contrast.md` regenerated whenever a theme or mapping changes.
- Header dropdown and `ThemeManager.THEMES` stay in sync.
- `all-themes.css` rebuilt after any addition or removal.
- Print preview keeps usable contrast (dark themes must not override print palette).
- Inventory lists which themes pass WCAG AA; accessible variants are flagged explicitly.

## Accessibility & Quality
- The converter runs WCAG AA checks; failures emit actionable warnings before CSS is written.
- Current production ratio: 6/11 themes pass AA (goal ≥ 75%). Overrides should nudge problem tokens toward compliant colors.
- Guardrails to watch:
  - `--wc-color-text` vs. `--wc-color-surface`
  - `--wc-color-link` vs. `--wc-color-page`
  - `--wc-focus-outline` must hold a 3:1 contrast with both focused control and surrounding surface.
- When overrides cannot rescue a palette, ship an “Accessible” variant rather than diluting the base catalog.

### Theme Lab & Metrics
- `/ui/components/#theme-lab` hosts the canonical specimens (buttons, helper text, radios, checkboxes, Leaflet zoom controls) that the automation harness inspects. Keep this page in sync with macro updates so the rendered sample always matches production markup.
- Run the contrast suite locally with `npm run smoke:theme-metrics` from `wepppy/weppcloud/static-src/` or through the CLI via `wctl2 run-playwright --suite theme-metrics --env local`. The harness simply hits the Theme Lab and does **not** require run provisioning, but the backend must be running so the page renders.
- Results are written to `wepppy/weppcloud/static-src/test-results/theme-metrics/theme-contrast.{json,md}`. Attach the Markdown table to PRs when tweaking `theme-mapping.json` to prove contrast moved in the right direction.
- Implementation details and expansion plan live in `docs/ui-docs/theme-metrics.spec.md`.

### Catalog Health
| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Catalog size | 6 – 12 themes | 11 | Avoid decision fatigue |
| Guaranteed coverage | ≥1 light, ≥1 dark AA-compliant | ✅ | Default + OneDark Accessible backlog item |
| Accessibility pass rate | ≥75% AA compliant | 54% | Prioritize Ayu and Cursor variants for overrides |
| Bundle size | ≤15 KB gzipped | ≈10 KB | Plenty of headroom |

## Troubleshooting
- **Theme renders incorrectly:** Re-run the converter with `--validate-only` to confirm tokens; add per-theme overrides for missing or unsuitable values.
- **Theme missing from dropdown:** Ensure `_theme_switcher.htm` and `ThemeManager.THEMES` include identical keys, then rebuild `all-themes.css`.
- **Contrast warnings:** Check `themes-contrast.md`; patch `theme-mapping.json` with overrides and regenerate the CSS.
- **FOUC on first load:** Verify the inline script that sets `data-theme` ships ahead of the main bundle and that `wc-theme` is present in `localStorage`.
- **Print outputs unreadable:** Confirm print media rules in `ui-foundation.css` override the active theme back to the default palette.

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
