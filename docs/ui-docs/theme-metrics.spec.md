# Theme Metrics Specification
> Tracks the end-to-end plan for automated theme contrast capture (fixture page, Playwright harness, and CI reporting).  
> **See also:** `docs/ui-docs/theme-system.md` for mapping guidance, `docs/ui-docs/control-ui-styling/control-components.md` for macro contracts.

## 1. Goals & Non-Goals
- **Goals**
  - Produce rendered color contrast metrics for every catalog theme using real DOM output (no token guessing).
  - Make the data agent-friendly so new themes/overrides can be tuned without human visual QA.
  - Surface regressions through scheduled CI artifacts rather than flaky pass/fail thresholds.
- **Non-Goals (initially)**
  - Full WCAG coverage for every element in the app.
  - Map legend gradients or topology overlays (Leaflet zoom controls only for now).
  - Blocking deployments based on contrast numbers.

## 2. Fixture Page (`/ui/components/theme-lab`)
### 2.1 Foundation
- Extend the existing showcase at `/ui/components/` (same blueprint) with a dedicated “Theme Lab” tab/section so navigation stays centralized. The lab renders:
  - Primary/secondary/link buttons (`pure-button` variants).
  - Representative form fields with `.wc-field__help`, `.wc-text-muted`, `.wc-field__message`, hint text, and error state.
  - Radio/checkbox groups (including the `sub_cmap_radio_*` set) wired through the same macros as production.
  - Leaflet zoom controls rendered via a lightweight stub container (no map tiles) so `.leaflet-control-zoom-in/out` exist.
- Each specimen uses Pure macros so markup stays in sync with `control-components.md`.

### 2.2 Target Metadata
- Assign `data-contrast-id="<component-key>"` on the outer wrapper for every specimen.
- Embed a `<script type="application/json" id="themeContrastTargets">` payload describing:
  ```json
  {
    "pure-button-primary": {
      "selector": ".wc-demo__primary .pure-button",
      "pairs": [
        { "name": "fg/bg", "foreground": ".pure-button", "background": ".pure-button" }
      ],
      "threshold": 3.0
    },
    "wc-field-help": {
      "selector": "#project_name_help",
      "pairs": [
        { "name": "text vs field", "foreground": "#project_name_help", "background": "#project_name" }
      ],
      "threshold": 4.5
    }
  }
  ```
- Include notes for special sampling (e.g., “radio checked vs unchecked”, “Leaflet zoom idle vs hover”).

### 2.3 Map Controls
- Mount a bare `<div class="wc-map">` with Leaflet CSS + JS enough to render the zoom control (Leaflet supports `L.control.zoom({ position: 'topright' }).addTo(map)` even on a blank map).
- Tag `a.leaflet-control-zoom-in` / `-out` with `data-contrast-id` entries so Playwright can sample them just like buttons.

## 3. Playwright Harness (`theme-metrics.spec.js`)
### 3.1 Execution Flow
1. Read theme IDs from `_theme_switcher.htm` or a shared JSON list so tests stay synced with header options.
2. For each theme:
   - Inject `localStorage.wc-theme` + `documentElement.dataset.theme` before navigation.
   - Visit `/weppcloud/ui/components/theme-lab` (or the enhanced gallery) and wait for network idle.
   - Evaluate the JSON payload (`themeContrastTargets`) to know which selectors/pairs to measure.
3. For each target:
   - Locate the element(s); skip gracefully if missing (feature flagged off).
   - Use `getComputedStyle` to capture `color`, `backgroundColor`, `borderColor`, and (when transparent) walk ancestors until a solid background is found.
   - For radio/checkbox `accent-color`, read via `getComputedStyle(input).accentColor` with a fallback to CSS variables when browsers do not expose it.
   - Compute WCAG contrast ratio `ratio = (Lmax + 0.05) / (Lmin + 0.05)` using sRGB → linear conversions.
   - Store `{ theme, targetId, pairName, ratio, threshold }`.
4. After all themes, write `playwright-report/theme-contrast.json` plus a Markdown table summary.

### 3.2 Helper Modules
- `theme-contrast.utils.js`
  - `applyTheme(page, themeId)` – wraps the pre-navigation injection.
  - `sampleColors(page, descriptor)` – shared logic for computed styles, ancestor fallback, accent-color handling.
  - `computeContrast(fg, bg)` – returns ratio + luminance values.
- `theme-targets.js` (optional) – utility to fetch/render the JSON schema so tests remain self-describing.

### 3.3 CLI Integration
- Add `npm run smoke:theme-metrics` pointing to the new spec.
- Expose through `wctl2 run-playwright --suite theme-metrics` (suite preset maps to `--grep @theme-metrics` or direct spec path).

## 4. Reporting & CI
- **Workflow:** Add a GitHub Actions cron (e.g., Monday 07:00 UTC) that runs inside the dev container via `wctl2 run-playwright --suite theme-metrics`.
- **Artifacts:**
  - **Output location:** `static-src/test-results/theme-metrics/` (**CRITICAL:** Must NOT use `playwright-report/` - Playwright's HTML reporter recreates/cleans that directory on each run, deleting custom artifacts. See Implementation Notes below.)
  - Raw JSON metrics (`theme-contrast.json`).
  - Markdown table summarizing ratios (<threshold flagged).
  - Optional trend CSV appended to `docs/ui-docs/theme-metrics-history.csv`; also embed the latest snapshot back into the gallery tab so humans can review within `/ui/components/`.
- **Pass/Fail:** Job always succeeds; it only fails when Playwright errors. Contrast thresholds are informational (use `status-warning` annotations when ratios < 1.0 or < target to draw attention without blocking).
- **Alerting:** If any ratio < 1.0, open/update an issue tagged `theme-contrast` so agents can adjust `theme-mapping.json` overrides.

## 5. Agent Workflow
1. Run `npm run smoke:theme-metrics -- --project runs0 --reporter=list` locally after editing `theme-mapping.json`.
2. Inspect the generated JSON/Markdown to see which tokens need overrides; patch `wepppy/weppcloud/themes/theme-mapping.json` or per-theme overrides accordingly.
3. Update `theme-system.md` (Accessibility section) with new pass/fail counts derived from the report.
4. When adding new macros/controls, register specimens + contrast targets in the Theme Lab to keep coverage in sync.

## 6. Implementation Plan
1. **Spec groundwork**
   - Approve this document’s scope + location (`docs/ui-docs/theme-metrics.spec.md`).
   - Align with control docs so showcase updates serve both documentation and testing.
2. **Fixture build-out**
   - Refactor `component_gallery.htm` into modular sections, add `theme-lab` route or tab.
   - Seed metadata JSON + IDs for the initial component list (buttons, helper text, job hint, field hint vs field background, `sub_cmap_radio_default`, `.wc-text-muted`, `.leaflet-control-zoom-*`).
3. **Playwright harness**
   - Implement spec + helpers, wire to package scripts + `wctl2`.
   - Validate color sampling accuracy across Chromium/WebKit; note Firefox gaps if any.
4. **CI + reporting**
   - Author GitHub Actions workflow (cron), ensure artifacts upload, add docs on how to read them.
   - Optional: script to convert latest JSON into a Markdown table appended to `docs/ui-docs/theme-system.md`.
5. **Expansion**
   - Add remaining macros (table blocks, tabs, banners) as needed.
   - Integrate automated issue creation for severe regressions (<1.0).

## 7. Open Questions
- Do we eventually codify minimum ratios (e.g., reject if primary buttons <3:1) once the catalog stabilizes?

## 8. Implementation Notes

### Output Directory Conflict (Resolved 2025-11-07)
**Problem:** Initial implementation wrote reports to `playwright-report/theme-metrics/`, but files were never visible on disk despite `fs.writeFile()` succeeding and `fs.access()` confirming their existence.

**Root Cause:** Playwright's HTML reporter (configured in `playwright.config.mjs` with `outputFolder: 'playwright-report'`) recreates/cleans the entire `playwright-report/` directory after test completion. This happens asynchronously after test success, so:
1. Test writes files to `playwright-report/theme-metrics/`
2. Files are created and verified successfully
3. Test completes and passes
4. Playwright HTML reporter cleans `playwright-report/` directory
5. Custom artifacts are deleted

**Solution:** Changed output directory to `test-results/theme-metrics/` in `theme-metrics.helpers.js`. Playwright only manages test-specific subdirectories within `test-results/`, leaving custom subdirectories intact.

**Key Lesson:** Never write custom artifacts to directories managed by Playwright reporters. Safe locations:
- `test-results/<custom-subdir>/` ✅ (used by this suite)
- Project root or separate output directories ✅
- `playwright-report/` or its subdirectories ❌ (cleaned by HTML reporter)

