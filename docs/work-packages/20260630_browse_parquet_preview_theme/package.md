# Browse Parquet Preview Theme Integration

**Status**: Closed (2026-06-30)
**Timezone**: UTC

## Overview
The production hotfix correctly made parquet browse pages disclose that HTML tables are previews, not complete parquet files. This package turns that hotfix into the durable UI contract: consolidate parquet filter status into the fixed preview banner, make the standalone browse table template theme-aware, and prove the banner's color pairings through the existing Theme Lab metrics workflow.

## Objectives
- Replace the separate parquet filter feedback block with a single fixed preview banner that contains preview scope, filter state, and file actions.
- Make standalone browse table previews load the WEPPcloud theme foundation, generated theme bundle, and persisted theme bootstrap.
- Add a Theme Lab browse-preview specimen and contrast target so the existing theme metrics suite samples the banner across every catalog theme.
- Update browse documentation and focused tests for the new UX contract.

## Scope

### Included
- `wepppy/weppcloud/routes/browse/templates/browse/data_table.htm` presentation and theme integration.
- Theme Lab fixture and contrast-target registration for the browse preview banner.
- Focused microservice/template tests and UI showcase route tests.
- Documentation updates for the browse preview/filter banner contract and theme metrics strategy.

### Explicitly Out of Scope
- Changing parquet filter semantics, preview row limits, CSV/parquet export behavior, D-Tale launch behavior, authorization, or path resolution.
- Changing theme token generation, adding new themes, or relaxing AA enforcement.
- Production deployment; the existing hotfix is sufficient until this package is reviewed and promoted.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction
- **Authoritative source path(s)**: `wepppy/microservices/browse/flow.py`, `wepppy/weppcloud/routes/browse/templates/browse/data_table.htm`, `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py`
- **Cutover proof required**: focused browse route tests render the consolidated banner for filtered and unfiltered parquet previews; Theme Lab route tests register the browse banner target.
- **Acceptance evidence type**: fixture-only

## Stakeholders
- **Primary**: WEPPcloud operators and users browsing parquet outputs.
- **Reviewers**: WEPPcloud maintainers.
- **Security Reviewer**: Not required for this package.
- **Informed**: Accessibility/theme maintainers.

## Success Criteria
- [x] Filtered parquet preview pages show one fixed `parquet-preview-banner` containing both preview and filter feedback.
- [x] The old standalone `filter-feedback` banner is removed from parquet preview pages.
- [x] Browse table previews use WEPPcloud theme variables and persisted `wc-theme` selection.
- [x] Theme Lab includes a browse parquet preview banner specimen and `themeContrastTargets` entries for preview text, filter text, and action controls.
- [x] Focused tests and docs lint pass, and the theme metrics suite is run or a blocker is recorded with exact reason.

## Parameterization ADR Gate
- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites
- Production hotfix `ab5c68e5a Clarify parquet browse previews` is already shipped and sufficient.
- Existing WEPPcloud theme foundation and Theme Lab metrics suite.

### Blocks
- Future broad theme rollout for standalone microservice templates should reuse the findings from this package.

## Related Packages
- **Related**: `docs/work-packages/20251027_vscode_theme_integration/`
- **Related**: `docs/work-packages/20260304_browse_parquet_quicklook_filters/`
- **Related**: `docs/work-packages/20260616_browse_arrow_pandas_elimination/`

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: Low

## Security Impact and Review Gate
- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: The package changes only rendered HTML/CSS/fixture coverage for an existing public browse preview. It does not modify auth, access checks, path resolution, file reads, downloads, filter parsing, queueing, or subprocess behavior.
- **Security review artifact**: N/A

## Hardening and Callus Softening
- **Failure signature(s)**: Stacked preview and filter notices on parquet browse pages; hard-coded warning colors outside the theme system.
- **Related prior hardening efforts**: Production preview disclosure hotfix `ab5c68e5a`.
- **Health signals**: One prominent banner, no duplicate filter notice, theme metrics include browse banner pairs.
- **Danger signals**: Bespoke colors bypass theme metrics; preview disclosure becomes visually subtle; theme bootstrap causes standalone browse FOUC.
- **Observation window**: Review during package validation; production promotion handled separately.
- **Temporary calluses introduced**: None.
- **Callus softening hypothesis**: The garish hotfix palette can be replaced by theme tokens once the banner is represented in Theme Lab metrics.

## References
- `wepppy/weppcloud/routes/browse/templates/browse/data_table.htm` - standalone parquet preview table template.
- `wepppy/microservices/browse/flow.py` - preview/filter response context.
- `wepppy/weppcloud/templates/ui_showcase/component_gallery.htm` - Theme Lab rendered specimens.
- `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py` - Theme Lab contrast target registry.
- `docs/ui-docs/theme-system.md` - theme runtime and metrics workflow.
- `docs/ui-docs/theme-metrics.spec.md` - theme metrics target contract.

## Deliverables
- Consolidated, theme-aware browse preview banner in `wepppy/weppcloud/routes/browse/templates/browse/data_table.htm`.
- Shared tokenized browse/banner styles in `wepppy/weppcloud/static/css/ui-foundation.css`.
- Theme Lab browse preview target for contrast sampling in `wepppy/weppcloud/templates/ui_showcase/component_gallery.htm` and `wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py`.
- Focused regression tests in `tests/microservices/test_browse_routes.py` and `tests/weppcloud/routes/test_ui_showcase_bp.py`.
- Documentation updates in `wepppy/microservices/browse/README.md`, `docs/ui-docs/theme-system.md`, and `docs/ui-docs/theme-metrics.spec.md`.

## Follow-up Work
- Evaluate whether other standalone browse templates should be moved to `base_pure.htm` or a shared microservice theme shell.

## Closure Notes

**Closed**: 2026-06-30

**Summary**: The parquet browse preview now renders a single fixed, theme-aware banner that combines preview disclosure, active filter state, filter code, and file actions. The standalone browse table template loads the WEPPcloud theme foundation and generated theme bundle, applies the persisted `wc-theme` before paint, and keeps body padding synchronized with the fixed banner height.

Theme coverage is now explicit: the Theme Lab includes a browse parquet preview banner fixture, and `themeContrastTargets` samples preview text, filter text, filter code, action text, and action borders. `wctl run-playwright --suite theme-metrics` passed after the banner was changed from a warning-tint background to the standard `surface`/`text` pairing; the generated report recorded `91` browse-banner measurements across `13` themes with `0` browse-banner failures.

**Lessons Learned**: The initial warning-token background failed the enforced `cursor-dark-midnight` theme at `3.548:1`, which confirmed that new themed surfaces need rendered Theme Lab evidence instead of token intuition. Standalone templates should either inherit the theme shell or carry the same pre-paint `wc-theme` bootstrap.

**Archive Status**: Package docs and completed ExecPlan are retained under `docs/work-packages/20260630_browse_parquet_preview_theme/`.
