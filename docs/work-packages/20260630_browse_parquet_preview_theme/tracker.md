# Tracker – Browse Parquet Preview Theme Integration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-30 16:47 UTC
**Current phase**: Closed
**Last updated**: 2026-06-30 16:57 UTC
**Next milestone**: N/A
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
- [x] Package, tracker, and active ExecPlan scaffolded. (2026-06-30 16:47 UTC)
- [x] Theme system and metrics strategy reviewed. (2026-06-30 16:47 UTC)
- [x] Consolidated themed browse preview banner implemented. (2026-06-30 16:57 UTC)
- [x] Theme Lab browse banner specimen and contrast target added. (2026-06-30 16:57 UTC)
- [x] Focused tests and browse/theme documentation updated. (2026-06-30 16:57 UTC)
- [x] Focused validation and doc lint completed. (2026-06-30 16:57 UTC)
- [x] Theme metrics suite passed with browse target included. (2026-06-30 16:57 UTC)

## Timeline

- **2026-06-30 16:47 UTC** – Package created; scoped around consolidating preview/filter notice and bringing browse previews under the theme metrics strategy.
- **2026-06-30 16:57 UTC** – Implementation, focused tests, docs lint, and theme metrics completed; package closed.

## Decisions Log

### 2026-06-30 16:47 UTC: Use Theme Lab as the contrast proof point
**Context**: The browse parquet table is rendered by a standalone template that does not inherit `base_pure.htm`, while the theme metrics harness samples targets from `/weppcloud/ui/components/#theme-lab`.

**Options considered**:
1. Rely only on existing token pair coverage - low code churn, but the specific banner composition would not be sampled.
2. Add a new Playwright route fixture for browse - direct, but duplicates the existing Theme Lab target-discovery pattern.
3. Add a Theme Lab browse-banner specimen - keeps the existing metrics suite authoritative and uses real DOM output.

**Decision**: Add a Theme Lab browse-banner specimen and target metadata for the preview text, filter text, and action controls.

**Impact**: Every theme already enumerated by the theme picker is sampled by the existing theme metrics suite without changing the suite's discovery model.

### 2026-06-30 16:47 UTC: Keep the scope presentation-only
**Context**: The production hotfix is sufficient, and the requested change is visual consolidation plus theme alignment.

**Options considered**:
1. Touch browse route/filter/export code while refactoring the banner.
2. Limit changes to template context consumption, CSS, docs, and tests.

**Decision**: Keep parquet filtering, preview limits, downloads, and authorization unchanged.

**Impact**: Lower regression risk and no dedicated security review requirement.

---

### 2026-06-30 16:57 UTC: Use surface/text instead of warning-tint background
**Context**: The first refreshed theme metrics run included the new browse target and failed enforced `cursor-dark-midnight` pairs for preview/filter text on `--wc-warning-bg` at `3.548:1`.

**Options considered**:
1. Override `cursor-dark-midnight` warning tokens - broader theme mapping change for one component.
2. Lower the browse target threshold - violates the AA theme baseline.
3. Use the standard `--wc-color-surface`/`--wc-color-text` pair and keep prominence through fixed placement, title, actions, and strong borders.

**Decision**: Use the standard surface/text pair.

**Impact**: The final theme metrics run passed, and the browse banner target has zero failures across all 13 sampled themes.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| The fixed banner becomes too subtle and users miss that browse is a preview. | Medium | Low | Keep fixed placement, explicit "Preview only" title, and prominent full-file actions while moving to theme tokens. | Mitigated |
| Theme contrast for the new banner fails in an enforced theme. | Medium | Medium | Register Theme Lab targets and run `wctl run-playwright --suite theme-metrics`; adjust token usage, not theme-specific colors. | Closed |
| Standalone browse theme bootstrap diverges from `base_pure.htm`. | Low | Medium | Use the same `wc-theme` localStorage bootstrap and shared `ui-foundation.css`/`all-themes.css`/`theme.js` assets. | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: Production page includes fixed preview disclosure but uses hard-coded warning colors and duplicates filter feedback below the banner.
- **Post-change health signals**: One fixed banner includes preview/filter state and actions; Theme Lab metrics include browse banner pairs with zero failures across 13 themes.
- **Danger signals observed**: Initial warning-tint background failed `cursor-dark-midnight`; resolved by using the standard surface/text pair.
- **Temporary callus register**: None.
- **Softening experiments**: Replace hotfix palette with theme tokens after metrics coverage is in place.

## Verification Checklist

### Code Quality
- [x] Focused Python tests passing.
- [x] Theme metrics suite passing or blocker recorded.

### Security
- [x] Security impact triage recorded with rationale.
- [x] Dedicated security review not required.
- [x] No auth/path/download behavior changed.

### Documentation
- [x] Browse README updated for consolidated theme-aware banner.
- [x] Work package docs linted.

### Testing
- [x] Unfiltered parquet preview banner covered.
- [x] Filtered parquet preview banner consolidation covered.
- [x] Theme Lab target registration covered.
- [x] Theme metrics run attempted.

### Deployment
- [x] Not deployed; production hotfix remains sufficient until this package is promoted.

## Progress Notes

### 2026-06-30 16:47 UTC: Package scaffold and strategy
**Agent/Contributor**: Codex

**Work completed**:
- Read theme system and theme metrics documentation.
- Inspected Theme Lab route/template and browse parquet preview template.
- Scoped the implementation to standalone browse theme bootstrap, consolidated banner markup, and Theme Lab contrast-target coverage.

**Blockers encountered**:
- None.

**Next steps**:
- Implement template and Theme Lab changes.
- Update focused tests.
- Run focused pytest, docs lint, and theme metrics if local stack permits.

**Test results**: Not run yet.

### 2026-06-30 16:57 UTC: Implementation and validation complete
**Agent/Contributor**: Codex

**Work completed**:
- Consolidated active filter feedback into the fixed parquet preview banner.
- Added standalone browse theme asset loading and pre-paint `wc-theme` bootstrap.
- Added shared browse/banner styles to `ui-foundation.css`.
- Added Theme Lab browse banner specimen and contrast-target metadata.
- Updated browse, theme-system, and theme-metrics docs.
- Closed package after validation.

**Blockers encountered**:
- The first theme metrics run after code changes hit a stale app process and did not include the new target. Restarted the local `weppcloud` container and reran.
- The first refreshed metrics run failed `cursor-dark-midnight` for warning-tint banner text at `3.548:1`. Switched to the standard surface/text pair and reran successfully.

**Next steps**:
- Commit/review when requested.
- Consider a follow-up for a shared shell across other standalone browse templates.

**Test results**:
- `wctl run-pytest tests/microservices/test_browse_routes.py --maxfail=1` - 16 passed.
- `wctl run-pytest tests/weppcloud/routes/test_ui_showcase_bp.py --maxfail=1` - 4 passed.
- `wctl doc-lint` passed for package docs, browse README, theme-system, and theme-metrics docs.
- `wctl run-playwright --suite theme-metrics` - 1 passed; 1261 measurements, 13 themes, 91 browse-banner measurements, 0 browse-banner failures.

## Watch List

- **Theme metrics runtime**: The suite needs a running backend; record exact blocker if local services are unavailable.
- **Standalone templates**: Other browse templates may still bypass the theme shell; defer unless directly needed.
