# Tracker – Browse Tree Theme Integration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-30 17:32 UTC
**Current phase**: Closed
**Last updated**: 2026-06-30 17:43 UTC
**Next milestone**: Package complete
**Security impact**: low
**Dedicated security review**: no
**Security artifact**: N/A

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package, tracker, and active ExecPlan scaffolded. (2026-06-30 17:32 UTC)
- [x] Browse tree template and listing row classes reviewed. (2026-06-30 17:32 UTC)
- [x] Implemented theme-aware browse tree templates and shared CSS. (2026-06-30 17:43 UTC)
- [x] Added Theme Lab browse tree specimen and contrast target metadata. (2026-06-30 17:43 UTC)
- [x] Updated focused tests and browse/theme documentation. (2026-06-30 17:43 UTC)
- [x] Ran focused pytest, docs lint, and theme metrics validation. (2026-06-30 17:43 UTC)
- [x] Recorded validation outcome and closed package. (2026-06-30 17:43 UTC)
- [x] Follow-up: themed the directory-page Parquet Data Filter builder and added Theme Lab coverage. (2026-06-30 19:20 UTC)

## Timeline
- **2026-06-30 17:32 UTC** – Package created for browse tree theming and metrics coverage.
- **2026-06-30 17:43 UTC** – Implementation validated and package closed.
- **2026-06-30 19:20 UTC** – Follow-up Parquet Data Filter builder theming completed.

## Decisions Log

### 2026-06-30 17:32 UTC: Preserve Default row colors as explicit variables
**Context**: The existing tree view uses hard-coded row colors: odd `#ffffff`, even `#f6f6f6`, hover `#d0ebff`.

**Options considered**:
1. Replace all row colors with generic theme tokens.
2. Preserve only visual intent, not exact values.
3. Preserve the Default colors exactly and override row variables for non-default themes.

**Decision**: Preserve exact Default colors in root browse-tree variables and use generic `:root[data-theme]` overrides for non-default themes.

**Impact**: Default behavior remains stable, while every named theme gets odd/even/hover styling.

### 2026-06-30 17:32 UTC: Use Theme Lab rendered DOM as the proof point
**Context**: The theme metrics suite validates rendered elements from Theme Lab, not raw token assumptions.

**Options considered**:
1. Rely on existing surface/text tests.
2. Add a browse-specific Playwright fixture.
3. Add a Theme Lab browse tree specimen.

**Decision**: Add a Theme Lab browse tree specimen with odd/even/hover rows and contrast target metadata.

**Impact**: The existing theme metrics suite samples browse-tree row states across all catalog themes.

### 2026-06-30 17:43 UTC: Outrank global link rules inside browse trees
**Context**: The first theme metrics run showed Default browse-tree link
measurements inheriting the global WEPPcloud link token instead of the preserved
legacy browse-tree link token, causing failures on the exact Default even and
hover row backgrounds.

**Options considered**:
1. Change the global link token.
2. Change the preserved Default row colors.
3. Give browse-tree link selectors the same exclusions as the global link rule,
   prefixed by `.wc-browse-tree`.

**Decision**: Prefix the matching global link selector shape with
`.wc-browse-tree` so browse-tree link variables control rendered tree links.

**Impact**: Default keeps the legacy row backgrounds and legacy-compatible link
contrast, while named themes continue using theme text on theme-derived row
backgrounds.

### 2026-06-30 17:43 UTC: Make named-theme row states visibly distinct through shared tokens
**Context**: Theme metrics showed that some catalog themes have identical or
near-identical `--wc-color-surface` and `--wc-color-surface-alt` values. A
simple surface/alternate-surface mix can therefore collapse odd/even/hover rows
to the same rendered color.

**Options considered**:
1. Add per-theme browse-tree overrides.
2. Accept the CSS states even when some rendered colors match.
3. Use generic alternate-surface/border mixes for even and hover rows.

**Decision**: Use theme surface for odd rows, then two generic
alternate-surface/border mixes for even and hover rows.

**Impact**: All catalog themes render distinct odd/even/hover row backgrounds
while still using measured theme tokens and avoiding hand-maintained per-theme
CSS.

### 2026-06-30 19:20 UTC: Theme the Parquet Data Filter builder
**Context**: The directory-page Parquet Data Filter builder still used inline
hard-coded colors and borders from `parquet_filter_builder.js`, so it did not
follow selected themes even after the directory page loaded theme assets.

**Options considered**:
1. Keep inline styles and swap literal colors for `var(...)` strings in JS.
2. Move presentation to CSS class hooks owned by `ui-foundation.css`.
3. Hide the builder until a broader browse shell refactor.

**Decision**: Emit class hooks from JS and move visual treatment to
`ui-foundation.css`, then add a Theme Lab contrast target for the builder.

**Impact**: The builder now inherits theme surface/text/border/button/input
tokens and is sampled by the existing theme metrics suite.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Default odd/even/hover colors drift. | Medium | Low | Encode exact default values as variables and assert them in tests. | Mitigated |
| Link text fails on preserved default hover/even rows. | Medium | Medium | Use a browse-tree link variable with legacy-compatible default link color and theme text color for named themes; validate in Theme Lab. | Mitigated |
| Stale local app process hides Theme Lab target updates. | Low | Medium | Restart local `weppcloud` container before final theme metrics if target rows are missing. | Mitigated |

## Verification Checklist

### Code Quality
- [x] Focused Python tests passing.
- [x] Theme metrics suite passing.

### Security
- [x] Security impact triage recorded with rationale.
- [x] Dedicated security review not required.
- [x] No auth/path/download behavior changed.

### Documentation
- [x] Browse README updated for tree theming.
- [x] Theme docs updated for browse tree target.
- [x] Work package docs linted.

### Testing
- [x] Directory tree theme assets and row variables covered.
- [x] Not-found tree theme assets covered.
- [x] Theme Lab target registration covered.
- [x] Theme metrics run completed.

### Deployment
- [ ] Not deployed.

## Progress Notes

### 2026-06-30 17:32 UTC: Package scaffold and strategy
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed browse tree template and listing-generated row classes.
- Scoped the package around presentation-only template/CSS/docs/tests.
- Chose Theme Lab target registration as the contrast coverage strategy.

**Blockers encountered**:
- None.

**Next steps**:
- Implement shared browse tree CSS and template asset loading.
- Add Theme Lab specimen and target metadata.
- Run focused tests, docs lint, and theme metrics.

**Test results**: Not run yet.

### 2026-06-30 17:43 UTC: Implementation and validation complete
**Agent/Contributor**: Codex

**Work completed**:
- Moved browse tree page styling into theme-aware `ui-foundation.css`
  variables and classes.
- Updated directory and not-found browse templates to load theme assets and
  pre-paint the persisted `wc-theme` value.
- Added a Theme Lab browse-tree row fixture and contrast target covering
  odd/even/hover row text and links.
- Added focused route/UI showcase tests and durable browse/theme docs.
- Fixed browse-tree link selector specificity so the tree-specific link token
  outranks the global link rule.

**Blockers encountered**:
- None. The initial Theme Lab run exposed a Default link contrast failure caused
  by selector precedence, which was fixed and revalidated.

**Next steps**:
- None for this package. A future package can extend the same shell to
  standalone text/data/DSS/arc viewers.

**Test results**:
- `wctl run-pytest tests/microservices/test_browse_routes.py --maxfail=1` - 18 passed.
- `wctl run-pytest tests/weppcloud/routes/test_ui_showcase_bp.py --maxfail=1` - 6 passed.
- `wctl run-playwright --suite theme-metrics` - 1 passed, 1,430 measurements, 13 themes.
- `theme-contrast.json` browse-tree target - 78 measurements, 0 failures, 13/13 themes with distinct odd/even/hover row backgrounds.
- `theme-contrast.json` Parquet Data Filter builder target - 91 measurements, 0 failures.

## Watch List
- **Default row parity**: Preserve `#ffffff`, `#f6f6f6`, and `#d0ebff`.
- **Theme target rows**: Confirm generated `theme-contrast.json` includes the browse tree target.
