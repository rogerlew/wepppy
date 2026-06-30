# Browse Tree Theme Integration

**Status**: Closed (2026-06-30)
**Timezone**: UTC

## Overview
Browse directory tree views still use standalone hard-coded CSS instead of the WEPPcloud theme system. This package applies the theme foundation to browse tree pages while preserving the Default theme's existing odd/even/hover row backgrounds and adding rendered Theme Lab contrast coverage for row states across every catalog theme.

## Objectives
- Move browse directory tree and not-found pages onto WEPPcloud theme assets and persisted `wc-theme` bootstrap.
- Preserve Default theme row backgrounds exactly: odd `#ffffff`, even `#f6f6f6`, hover `#d0ebff`.
- Provide non-default theme odd/even/hover row backgrounds derived from tested theme tokens.
- Add Theme Lab contrast-target coverage for browse tree odd/even/hover rows.
- Update focused tests and documentation for the durable browse tree theming contract.

## Scope

### Included
- `wepppy/weppcloud/routes/browse/templates/browse/directory.htm`
- `wepppy/weppcloud/routes/browse/templates/browse/not_found.htm`
- Shared browse tree CSS in `wepppy/weppcloud/static/css/ui-foundation.css`
- Theme Lab specimen and metrics target registration.
- Focused browse route/UI showcase tests and documentation updates.

### Explicitly Out of Scope
- Changing directory listing, sorting, pagination, authorization, path resolution, download links, filter behavior, or command-bar behavior.
- Re-theming text/data/DSS/arc file viewers unless required by this package's tree-view scope.
- Production deployment.

## Implementation Fidelity and Evidence
- **Fidelity target**: faithful extraction
- **Authoritative source path(s)**: `wepppy/weppcloud/routes/browse/templates/browse/directory.htm`, `wepppy/microservices/browse/listing.py`
- **Cutover proof required**: focused route tests render themed tree pages and preserve row classes/assets; Theme Lab route tests register browse tree contrast targets.
- **Acceptance evidence type**: fixture-only

## Stakeholders
- **Primary**: WEPPcloud operators and users browsing run artifacts.
- **Reviewers**: WEPPcloud maintainers.
- **Security Reviewer**: Not required.
- **Informed**: Accessibility/theme maintainers.

## Success Criteria
- [x] Browse directory tree pages load `ui-foundation.css`, `all-themes.css`, and `theme.js`.
- [x] Browse directory tree pages apply persisted `wc-theme` before paint.
- [x] Default theme preserves odd/even/hover row colors exactly.
- [x] Non-default themes render odd/even/hover row backgrounds through theme-derived variables.
- [x] Theme Lab includes a browse tree specimen and contrast targets for odd/even/hover states.
- [x] Focused tests, docs lint, and theme metrics pass or blockers are recorded.

## Parameterization ADR Gate
- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes

## Dependencies

### Prerequisites
- Completed browse parquet preview theme package: `docs/work-packages/20260630_browse_parquet_preview_theme/`
- Existing WEPPcloud Theme Lab metrics suite.

### Blocks
- Future consolidation of standalone browse file viewers into a shared shell can reuse this strategy.

## Related Packages
- **Related**: `docs/work-packages/20260630_browse_parquet_preview_theme/`
- **Related**: `docs/work-packages/20251027_vscode_theme_integration/`

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: Low

## Security Impact and Review Gate
- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: The package changes tree-view presentation, shared CSS, fixture docs, and tests for an existing public browse surface. It does not change auth, path handling, downloads, filters, queueing, or subprocess behavior.
- **Security review artifact**: N/A

## Hardening and Callus Softening
- **Failure signature(s)**: Browse tree views bypass theme assets and hard-code row/header/schema colors.
- **Related prior hardening efforts**: `20260630_browse_parquet_preview_theme`
- **Health signals**: Theme metrics include browse tree row states with zero browse-tree failures.
- **Danger signals**: Default row color drift; theme row states without contrast coverage; link colors failing on hover rows.
- **Observation window**: Package validation.
- **Temporary calluses introduced**: None.
- **Callus softening hypothesis**: Tree-view CSS can be moved to shared theme tokens while preserving default row behavior.

## References
- `wepppy/weppcloud/routes/browse/templates/browse/directory.htm` - browse tree template.
- `wepppy/weppcloud/routes/browse/templates/browse/not_found.htm` - tree-style error template.
- `wepppy/microservices/browse/listing.py` - generated row markup/classes.
- `docs/ui-docs/theme-system.md` - theme runtime and metrics workflow.
- `docs/ui-docs/theme-metrics.spec.md` - Theme Lab metrics contract.

## Deliverables
- Theme-aware browse tree view templates.
- Shared browse tree row/header/schema styles.
- Theme Lab browse tree target and focused tests.
- Theme-aware Parquet Data Filter builder styles and Theme Lab target.
- Documentation updates.

## Closure Notes
Closed on 2026-06-30 after implementation and validation.

The selected strategy is to keep Default browse-tree row colors as explicit
root variables and switch named themes through `:root[data-theme]` browse-tree
variables derived from already-tested theme surface, alternate-surface, border,
and text tokens. Odd rows use the theme surface; even and hover rows use two
different alternate-surface/border mixes so equal-surface themes still render
distinct row states. The rendered Theme Lab fixture is the enforcement point:
`browse_tree_rows` samples odd, even, and hover row states for both link and
plain text across every catalog theme.

Validation evidence:
- `wctl run-pytest tests/microservices/test_browse_routes.py --maxfail=1` - 18 passed.
- `wctl run-pytest tests/weppcloud/routes/test_ui_showcase_bp.py --maxfail=1` - 6 passed.
- `wctl run-playwright --suite theme-metrics` - 1 passed, 1,430 measurements, 13 themes.
- `theme-contrast.json` browse-tree target: 78 measurements, 0 failures, 13/13 themes with distinct odd/even/hover row backgrounds.
- `theme-contrast.json` Parquet Data Filter builder target: 91 measurements, 0 failures.

Follow-up correction on 2026-06-30: the Parquet Data Filter builder on the
directory page also needed to follow themes. Its JS now emits class hooks
instead of inline hard-coded colors, `ui-foundation.css` owns the themed
presentation, and Theme Lab includes a `browse_parquet_filter_builder` target.

## Follow-up Work
- Evaluate whether `text_file.htm`, `dss_file.htm`, and `arc_file.htm` should adopt the same standalone browse shell.
