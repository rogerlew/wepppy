# Browse Tree Theme Integration ExecPlan

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current as work proceeds.

## Purpose

Apply WEPPcloud theming to browse directory tree views while preserving the Default theme's existing odd/even/hover row backgrounds and adding Theme Lab metrics coverage for every catalog theme.

## Progress

- [x] Reviewed browse tree template and listing row markup.
- [x] Scaffolded work package and tracker.
- [x] Implement themed tree view templates and shared CSS.
- [x] Add Theme Lab specimen and contrast targets.
- [x] Update focused tests and docs.
- [x] Run validation and record results.

## Surprises & Discoveries

- The directory tree row colors live entirely in inline `directory.htm` CSS, while row markup comes from `listing.py` as `span.odd-row`/`span.even-row`.
- The preserved Default row colors require a browse-specific link color strategy because the global WEPPcloud link token does not meet AA on the exact Default even/hover backgrounds.
- The first Theme Lab run confirmed selector precedence mattered: the global
  link rule overrode the browse-tree link token until the browse-tree selector
  matched the global exclusions with a `.wc-browse-tree` prefix.
- Some catalog themes have identical or near-identical surface and
  alternate-surface values, so named-theme row differentiation needs a generic
  border-token mix rather than surface-token mixing alone.
- The Parquet Data Filter builder also lived on the themed directory page but
  still used inline hard-coded colors from JavaScript.

## Decision Log

- **2026-06-30 17:32 UTC** – Preserve Default odd/even/hover row colors exactly through browse-tree CSS variables.
- **2026-06-30 17:32 UTC** – Add Theme Lab browse tree specimen rather than adding a second contrast harness.
- **2026-06-30 17:43 UTC** – Keep the global link token unchanged and make
  browse-tree link selectors explicitly win inside `.wc-browse-tree`.
- **2026-06-30 17:43 UTC** – Use generic alternate-surface/border mixes for
  named-theme even and hover rows so every catalog theme renders distinct row
  states without per-theme browse CSS.
- **2026-06-30 19:20 UTC** – Move Parquet Data Filter builder presentation out
  of JS inline styles and into theme-token CSS with a Theme Lab target.

## Plan

1. Move browse tree row/header/schema styles from `directory.htm` into `ui-foundation.css`.
2. Define Default browse-tree variables with exact legacy row colors, then generic `:root[data-theme]` overrides for non-default odd/even/hover backgrounds.
3. Load theme assets and pre-paint `wc-theme` bootstrap in `directory.htm` and `not_found.htm`.
4. Add a Theme Lab browse tree specimen using `odd-row`, `even-row`, and fixture hover row classes.
5. Register contrast targets for odd/even/hover row text and links in `ui_showcase_bp.py`.
6. Update focused browse and UI showcase tests.
7. Update browse/theme docs and close the package after validation.

## Validation

Minimum required:
- `wctl run-pytest tests/microservices/test_browse_routes.py --maxfail=1` - 18 passed.
- `wctl run-pytest tests/weppcloud/routes/test_ui_showcase_bp.py --maxfail=1` - 6 passed.
- `wctl doc-lint --path docs/work-packages/20260630_browse_tree_theme/package.md` - passed.
- `wctl doc-lint --path docs/work-packages/20260630_browse_tree_theme/tracker.md` - passed.
- `wctl doc-lint --path docs/work-packages/20260630_browse_tree_theme/prompts/completed/browse_tree_theme_execplan.md` - passed.
- `wctl doc-lint --path wepppy/microservices/browse/README.md` - passed.
- `wctl doc-lint --path docs/ui-docs/theme-system.md` - passed.
- `wctl doc-lint --path docs/ui-docs/theme-metrics.spec.md` - passed.
- `wctl run-playwright --suite theme-metrics` - 1 passed, 1,430 measurements, 13 themes.
- `theme-contrast.json` browse-tree target - 78 measurements, 0 failures, 13/13 themes with distinct odd/even/hover row backgrounds.
- `theme-contrast.json` Parquet Data Filter builder target - 91 measurements, 0 failures.

## Outcomes & Retrospective

The package applied the WEPPcloud theme system to browse tree pages without
changing browse route behavior. Default keeps exact legacy row colors, named
themes get theme-derived and visually distinct odd/even/hover row colors, and
the Theme Lab metrics suite now measures the rendered browse-tree and Parquet
Data Filter builder states for every catalog theme.
