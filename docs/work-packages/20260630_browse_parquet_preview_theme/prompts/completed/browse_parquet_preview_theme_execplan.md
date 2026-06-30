# Browse Parquet Preview Theme Integration ExecPlan

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current as work proceeds.

## Purpose

Turn the production parquet preview hotfix into the durable browse UX: one fixed banner that discloses preview scope, includes any active parquet filter feedback, exposes full-file actions, and follows WEPPcloud themes with contrast coverage in the existing Theme Lab metrics suite.

## Progress

- [x] Reviewed `docs/ui-docs/theme-system.md` and `docs/ui-docs/theme-metrics.spec.md`.
- [x] Inspected the standalone browse `data_table.htm` and Theme Lab target registration.
- [x] Scaffolded the work package and tracker.
- [x] Implement themed consolidated browse banner.
- [x] Add Theme Lab specimen and contrast target metadata.
- [x] Update docs and focused tests.
- [x] Run validation and record results.

## Surprises & Discoveries

- The browse parquet table template is standalone and does not inherit `base_pure.htm`, so it needs its own theme bootstrap and asset includes.
- Theme metrics already discover every theme through the Theme Lab picker and target JSON payload, so adding a Theme Lab specimen is enough to bring the browse banner under the existing suite.
- A warning-tint banner background failed the enforced `cursor-dark-midnight` theme at `3.548:1`; the standard surface/text pairing passed across all sampled themes.

## Decision Log

- **2026-06-30 16:47 UTC** – Use existing theme tokens and Theme Lab target discovery instead of adding browse-specific palettes or a second contrast harness.
- **2026-06-30 16:47 UTC** – Keep route semantics unchanged; only template/CSS/docs/tests are in scope.
- **2026-06-30 16:57 UTC** – Use the standard surface/text pair for the banner instead of warning-tint background because rendered theme metrics caught an enforced-theme AA failure.

## Plan

1. Update `data_table.htm` so parquet previews load `ui-foundation.css`, `all-themes.css`, and `theme.js`, apply the persisted `wc-theme` before paint, and style body/table/banner/action links with WEPPcloud tokens.
2. Consolidate filter feedback into the fixed `parquet-preview-banner` so filtered pages do not render a second notice.
3. Add a Theme Lab browse-preview banner specimen that uses the same class names and token pairings as browse.
4. Register contrast targets for preview title/message, filter title/message/code, and action buttons in `ui_showcase_bp.py`.
5. Update focused tests in `tests/microservices/test_browse_routes.py` and `tests/weppcloud/routes/test_ui_showcase_bp.py`.
6. Update browse documentation and package tracker.
7. Run focused pytest, doc lint, and theme metrics if local services are available.

## Validation

Minimum required:
- `wctl run-pytest tests/microservices/test_browse_routes.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_ui_showcase_bp.py --maxfail=1`
- `wctl doc-lint --path docs/work-packages/20260630_browse_parquet_preview_theme/package.md`
- `wctl doc-lint --path docs/work-packages/20260630_browse_parquet_preview_theme/tracker.md`
- `wctl doc-lint --path docs/work-packages/20260630_browse_parquet_preview_theme/prompts/active/browse_parquet_preview_theme_execplan.md`
- `wctl doc-lint --path wepppy/microservices/browse/README.md`

Theme evidence:
- `wctl run-playwright --suite theme-metrics`

## Outcomes & Retrospective

Completed. The final implementation consolidates preview and filter feedback into one fixed banner, applies WEPPcloud theme assets/bootstrap to standalone browse table previews, and adds Theme Lab coverage for the browse banner. Validation passed:

- `wctl run-pytest tests/microservices/test_browse_routes.py --maxfail=1` - 16 passed.
- `wctl run-pytest tests/weppcloud/routes/test_ui_showcase_bp.py --maxfail=1` - 4 passed.
- `wctl doc-lint` passed for package docs, browse README, `theme-system.md`, and `theme-metrics.spec.md`.
- `wctl run-playwright --suite theme-metrics` - 1 passed, with 91 browse-banner measurements across 13 themes and 0 browse-banner failures.
