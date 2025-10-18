# WEPPcloud UI Style Guide & Site Assessment

## 1. Design philosophy
- **Calm utility.** Prioritize legible data and workflows over decorative treatments. Pages should feel like professional tools: uncluttered backgrounds, strong hierarchy, and no ornamental gradients or corner rounding.
- **Pure.css first.** Load the Pure.css core and grid on every page and layer site-specific tokens from `static/css/ui-foundation.css`. Reach for Bootstrap only when Pure lacks a ready-made solution (e.g., modal scaffolding, large tabular navigation, or complex ToCs).
- **Zero-maintenance defaults.** Consolidate colors, type, spacing, and component rules inside the shared foundation stylesheet so individual pages do not need inline CSS. Prefer semantic HTML and Pure utility classes before hand-written overrides.
- **Consistent framing.** Every screen should share a header, generous breathing room, and predictable spacing rhythm so tool-to-tool navigation feels seamless.
- **Accessibility as baseline.** Follow WCAG AA contrast, ensure focus outlines remain visible, and keep interactive controls keyboard reachable without JavaScript dependencies.
- **Consistent, unstyled, unpretentious, simple, maintenable** Keep things simple and use patterns known to render in predictable manner.

## 2. Technology stack
| Layer | Purpose | Notes |
| --- | --- | --- |
| Pure.css `pure-min.css`, `grids-responsive-min.css` | Baseline grid, buttons, and form styling | Vendor locally under `static/vendor/purecss/` using `static-src/build-static-assets.sh`—do **not** link to the CDN in templates.【F:wepppy/wepppy/weppcloud/static-src/scripts/build.mjs†L17-L129】|
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

## 3. Tokens, colors, and typography

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

## 4. Component guidance

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

### Modal/dialogue content
- When Bootstrap modals are required, apply `.pure-modal` on the dialogue content to keep typography, spacing, and squared edges in sync, benefiting from the shared medium elevation shadow.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L846-L850】

### Tooltip primitives
- Use `.wc-tooltip` and `.wc-tooltip__bubble` to create accessible hover/focus descriptions without importing additional libraries. Anchor the bubble with `aria-describedby` IDs and toggle via CSS/JS as needed.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L617-L637】

### Logs & consoles
- Wrap console pages in `.wc-console` grids and use `.wc-panel` to frame tools, tables, and status messages.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L639-L663】
- `.wc-log` provides a reusable monospace log surface with built-in overflow handling.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L645-L663】
- Use `.wc-code-input` and `.wc-code-block` for JSON editors or stack traces so typography and spacing stay consistent.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L735-L760】

## 5. Content display patterns
- **Reading views (Markdown, documentation):** wrap in `.wc-reading` to constrain width and rely on the markdown overrides already in the foundation file.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L146-L147】【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L876-L883】
- **README editor:** use `.wc-editor-grid` with `.wc-editor-textarea` and `.wc-editor-preview` to keep the split view responsive; overlay locks reuse `.wc-overlay` helpers.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L672-L722】
- **Data consoles (logs, monitors):** use `.wc-panel` with monospace text and `.wc-status` for live status chips; pair with `.wc-table` for job lists.
- **Dashboards:** structure as stacked `.wc-panel` elements with `.wc-toolbar` headings, each focusing on a single job/action set.
- **Paginated datasets:** combine `.wc-table` with `.wc-pagination` and ensure the current page link uses `aria-current="page"` so screen readers announce context.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L426-L443】【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L530-L557】
- **Contextual tips:** surface brief guidance using `.wc-tooltip` tied to icons or labels; ensure the tooltip content is duplicated inline for screen readers when the information is critical.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L617-L637】
- **Logs & metrics:** use `.wc-log` alongside `.wc-status-chip` to stream job output; wrap supporting metadata in `.wc-meta-list`.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L573-L663】
- **Static assets:** whenever you add or update third-party CSS/JS, update `static-src/scripts/build.mjs` and rerun `build-static-assets.sh` so production pulls from local files rather than CDNs.【F:wepppy/wepppy/weppcloud/static-src/build-static-assets.sh†L1-L64】【F:wepppy/wepppy/weppcloud/static-src/scripts/build.mjs†L17-L129】

## 6. Accessibility checklist
- Maintain the default focus outline supplied by the foundation CSS (solid 2px accent) to keep keyboard navigation visible, including `:focus-visible` states.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L342-L355】
- Ensure icon-only buttons include `aria-label` attributes and at least the `.wc-inline` spacing utility so hit targets remain comfortable.
- Keep content inside 70–80 character line lengths (`.wc-reading`) for long-form copy and docs.
- Honor user preferences: do not reintroduce animations or transitions beyond the shared defaults so the global reduced-motion override can do its job.【F:wepppy/wepppy/weppcloud/static/css/ui-foundation.css†L102-L111】

## 7. Implementation playbook
1. **Create/extend a Pure base template.** Migrate templates to extend a common layout that loads Pure + the foundation stylesheet. Replace Bootstrap header includes (`header/_layout_fixed.htm`) with the new header block.
2. **Extract inline CSS.** Move inline styles from templates (home page banners, security forms, Deval loading state) into component-specific partials or reuse `.wc-panel`, `.wc-status`, and `.wc-toolbar` primitives.
3. **Refactor page clusters.** Update one feature cluster at a time (browse, archive dashboard, authentication, run controls) to use Pure grids and the foundation tokens, verifying there are no rounded corners or drop shadows beyond the shared defaults.
4. **Audit Bootstrap usage.** If a page only uses Bootstrap utilities (e.g., `.row`, `.btn`), replace them with Pure equivalents; keep Bootstrap loaded only where widgets like modals remain. When Bootstrap (or any vendor asset) is still needed, ensure the reference comes from `static/vendor/` with the build script instead of a CDN URL.【F:wepppy/wepppy/weppcloud/static-src/build-static-assets.sh†L1-L64】
5. **Document patterns.** As layouts are migrated, note reusable snippets in this guide so new routes stay aligned.
6. **Capture references.** Update the shared visual reference folder with new screenshots whenever you land a significant template refactor so future contributors can see expected results.

## 8. Site-wide assessment & unification plan

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

## 9. Next steps & tracking
- Stand up an “interface audit” checklist in issue tracking using the sections above as milestones (browse, archive, auth, home, controls, reports).
- After each cluster migration, remove unused Bootstrap imports and inline styles to keep the codebase lean.
- Refresh this guide as new shared components emerge (e.g., pagination, diff viewers) so future contributions stay aligned with the cohesive visual language, and capture any updates to the static asset pipeline as libraries change versions.
- Integrate the shared Stylelint ruleset (`.stylelintrc.json`) into CI so linting enforces the “no rounded corners” + token usage expectations automatically.【F:.stylelintrc.json†L1-L21】
- Run a lightweight accessibility audit (Lighthouse or ax) after major migrations to confirm the light palette, focus outlines, and reduced-motion defaults behave as intended.

## 10. Visual references & demos
- Store screenshots or short GIFs that demonstrate core layouts under `docs/ui-reference/`. Capture at least: base layout shell, Pure form, table + pagination, status banner, tooltip example, and a dark-mode rendering.
- Regenerate assets after significant CSS updates to keep the visuals synchronized with the written guidelines.
- Use descriptive filenames (e.g., `header-light.png`, `table-dark.png`) and embed them in this guide or related documentation as needed.

## 11. JavaScript interaction principles
- Favor progressive enhancement: ensure modals, tooltips, and accordions render helpful content even when JavaScript is unavailable.
- Keep interactions framework-agnostic. Lightweight Alpine.js sprinkles are acceptable, but they should operate on semantic HTML and classes defined here.
- When introducing new JS-driven UI, pair it with CSS hooks inside `ui-foundation.css` (e.g., data attributes) so behavior and presentation remain decoupled.

## 12. Validation & automation
- Use Stylelint with the shared config to block forbidden patterns such as `border-radius` values other than `var(--wc-radius-none)` and to require the `wc-` namespace for shared utilities.【F:.stylelintrc.json†L1-L21】
- Prettier (or an equivalent formatter) can be pointed at template directories to enforce indentation and whitespace consistency; avoid inline styles so linting remains effective.
- During review, spot-check new CSS against the token tables—if a new color is required, add it as a token rather than embedding raw hex codes.

## 13. Guide change log
- **2025-10-17:** Added dark-mode tokens, reduced-motion defaults, pagination/tooltip primitives, contributor quick-start, validation guidance, and a visual reference process.
- **2024-04-05:** Initial publication covering Pure.css-first philosophy, tokens, assessment, and migration plan.
