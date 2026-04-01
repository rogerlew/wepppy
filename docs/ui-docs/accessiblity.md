# Accessibility and Section 508 Strategy

This document is the single entry point for accessibility guidance, tests, and compliance strategy across the WEPPcloud UI stack.

## Scope

- Unify the current accessibility-related standards and tests across `docs/`, `tests/`, UI templates, controller JS, and CI workflow specs.
- Define a practical Section 508 strategy for this repo.
- Keep accessibility checks manual-gate driven, not PR-blocking.

## Canonical Repo Map

| Area | Canonical source | Purpose |
| --- | --- | --- |
| UI accessibility patterns | `docs/ui-docs/ui-style-guide.md` | Core WCAG-aligned patterns (labels, focus visibility, keyboard behavior, status announcements). |
| Controller accessibility contract | `docs/ui-docs/controller-contract.md` | Required `aria-live` usage, modal/focus expectations, and resilient controller behavior. |
| Theme accessibility | `docs/ui-docs/theme-system.md` | Theme token model plus contrast guidance and operational workflow. |
| Contrast harness spec | `docs/ui-docs/theme-metrics.spec.md` | Rendered contrast measurement scope, reporting, and CI artifact model. |
| Findings 1-6 remediation package | `docs/work-packages/20260331_wcag21aa_frontend_accessibility/package.md` | Scope and acceptance criteria for recent WCAG remediation. |
| Findings 1-6 execution evidence | `docs/work-packages/20260331_wcag21aa_frontend_accessibility/tracker.md` | Validation history, risks, and current caveats. |
| Template-level accessibility assertions | `tests/weppcloud/routes/test_pure_controls_render.py` | Semantic copy controls, map role changes, placeholder labels, standalone metadata checks. |
| Route-level map semantics assertion | `tests/weppcloud/routes/test_user_runs_admin_scope.py` | Guards map canvas semantics in runs template rendering. |
| Controller accessibility assertions | `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js` | Modal accessible-name and keyboard behavior coverage in map surfaces. |
| Copy control accessibility regression | `wepppy/weppcloud/controllers_js/__tests__/copytext.test.js` | Ensures semantic copy button behavior remains compatible. |
| Rendered contrast smoke test | `wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js` | Theme-level WCAG AA contrast metrics from real DOM rendering. |
| Workflow spec (generated source) | `.github/forest_workflows/theme-metrics-nightly.yml` | Nightly contrast artifact run. |
| Workflow spec (generated source) | `.github/forest_workflows/playwright-controllers-nightly.yml` | Nightly controller-level UI regression coverage. |
| Workflow spec (generated source) | `.github/forest_workflows/npm-tests.yml` | PR/push frontend unit test baseline. |
| Playwright command wiring | `tools/wctl2/commands/playwright.py` | Source of truth for `wctl run-playwright --suite ...` behavior. |

## Standards Baseline

- Product quality target: WCAG 2.1 AA for core user journeys.
- Section 508 legal baseline for federal conformance references Revised 508 standards (which incorporate WCAG 2.0 A/AA via referenced accessibility standards).
- Practical policy for this repo:
  - Treat WCAG 2.1 AA as the engineering bar.
  - Produce 508-friendly evidence packs from automated and manual checks.

External references:
- https://www.section508.gov/develop/applicability-conformance/
- https://www.section508.gov/test/testing-overview/
- https://www.section508.gov/test/trusted-tester/
- https://www.access-board.gov/ict/

## Current Coverage (Already in Repo)

### 1) Template and route semantics (pytest)

Use targeted route tests as first-line structural checks:

```bash
wctl run-pytest \
  tests/weppcloud/routes/test_pure_controls_render.py \
  tests/weppcloud/routes/test_user_runs_admin_scope.py \
  --maxfail=1
```

These currently validate:
- semantic copy controls in report templates
- map canvas semantics (`role="application"` removal and `aria-label` presence)
- placeholder-independent accessible naming
- standalone HTML metadata (`lang`, iframe/title requirements)

### 2) Controller behavior and JS regressions (Jest)

```bash
wctl run-npm test -- copytext map_gl
```

These currently validate:
- modal accessible names in map feature UI behavior
- copy-to-table behavior compatibility with semantic button controls
- selected map keyboard interaction paths

### 3) Rendered contrast evidence (Playwright)

```bash
wctl run-playwright --suite theme-metrics
```

This produces contrast artifacts in:
- `wepppy/weppcloud/static-src/test-results/theme-metrics/theme-contrast.json`
- `wepppy/weppcloud/static-src/test-results/theme-metrics/theme-contrast.md`

AA enforcement policy in `theme-metrics.spec.js`:
- Enforced themes: `default`, `light-high-contrast`, `ayu-mirage`, `ayu-mirage-bordered`, `cursor-dark-midnight`.
- Other themes are still measured/reported for user-preference visibility but do not fail the suite.
- Optional override: `THEME_METRICS_ENFORCED_THEMES=theme1,theme2,...`.

### Universal Design Theme Policy

WEPPcloud supports a mixed theme catalog for universal design and user preference:
- **Compliance-enforced themes** (must remain WCAG AA in the metrics gate):
  - `default`
  - `light-high-contrast`
  - `ayu-mirage`
  - `ayu-mirage-bordered`
  - `cursor-dark-midnight`
- **Preference themes** (still measured/reported, intentionally allowed to be lower contrast):
  - `ayu-light`, `ayu-light-bordered`
  - `ayu-dark`, `ayu-dark-bordered`
  - `onedark`
  - `dark-modern`
  - `cursor-dark-anysphere`
  - `cursor-dark-high-contrast`

Latest captured metrics snapshot (generated at **March 31, 2026**):
- Light themes: `default` and `light-high-contrast` compliant; `ayu-light*` variants non-compliant.
- Dark themes: `ayu-mirage*` and `cursor-dark-midnight` compliant; remaining dark preference themes non-compliant.
- Operationally, this is acceptable under the current policy because the enforced compliance set passes.

Nightly artifact workflow source:
- `.github/forest_workflows/theme-metrics-nightly.yml`

## Known Gaps

- Axe coverage currently includes Theme Lab and runs0 dashboard only; expand to additional high-risk flows over time (GL dashboard variants, report-heavy pages, and advanced modals).
- No baseline/triage policy yet for classifying and tracking recurring axe findings across runs.

## Section 508 Strategy (Manual Gate, Non-Blocking)

The repository should keep accessibility as a release-readiness gate that is run manually, not as a required PR check.

### Gate posture

- Do not mark accessibility CI checks as required branch-protection statuses.
- Keep accessibility workflow(s) `workflow_dispatch` (optionally also scheduled) and use pass/fail plus artifacts for reviewer signoff.
- Use the generated workflow system:
  - edit `.github/forest_workflows/*.yml`
  - regenerate `.github/workflows/*.yml` using `scripts/build_forest_workflows.py`

### Manual gate sequence

1. Run existing automated checks and collect artifacts:
   - pytest route semantics
   - Jest `copytext` + `map_gl`
   - Playwright theme metrics
2. Run axe structural scan suite (defined below) and capture violation report.
3. Perform manual assistive-tech and keyboard checks (Trusted Tester/ICT baseline style checks).
4. Record outcome in release notes/work package tracker before release signoff.

## Axe Test Setup (Implemented)

### Dependencies

In `wepppy/weppcloud/static-src/package.json` dev dependencies:
- `@axe-core/playwright`
- `axe-core`

### Test location

Playwright specs are under:
- `wepppy/weppcloud/static-src/tests/smoke/a11y/`

Current spec:
- `wepppy/weppcloud/static-src/tests/smoke/a11y/axe-runs0.spec.js`

### Suggested test targets

- WEPPcloud root (`/weppcloud/`)
- Interfaces landing (`/weppcloud/interfaces/`)
- Runs page (`SMOKE_RUN_PATH` target)
- Map view (`map_gl` surface with modals/overlays)
- UI components showcase (`/ui/components/#theme-lab`)
- Command surfaces with dynamic status updates

### Core axe invocation

```javascript
import AxeBuilder from "@axe-core/playwright";

const results = await new AxeBuilder({ page })
  .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
  .analyze();
```

### Artifact policy

Write artifacts to `test-results/a11y/` (not `playwright-report/`), for example:
- `axe-violations.json`
- `axe-summary.md`
- optional per-page JSON snapshots

### Execution command (manual gate use)

```bash
wctl run-npm smoke:a11y
```

For CAP-gated runs0 scans, use an authenticated agent account:

1. Create `docker/secrets/ally-agent-smoke.env` (gitignored):
   - `ALLY_AGENT_EMAIL=<ally-agent email>`
   - `ALLY_AGENT_PASSWORD=<ally-agent password>`
2. Set file permissions:
   - `chmod 600 docker/secrets/ally-agent-smoke.env`
3. Run the suite (it auto-loads this file by default), or override with:
   - `SMOKE_AGENT_CREDENTIALS_FILE=/path/to/file.env`

Optional strict mode:
- `SMOKE_AGENT_REQUIRED=true` to fail/skip fast when agent credentials are missing.

## Recommended Accessibility Workflow

Implemented workflow spec:
- `.github/forest_workflows/accessibility-manual.yml`

Generated workflow:
- `.github/workflows/accessibility-manual.yml`

Recommended triggers:
- `workflow_dispatch` (required)
- nightly schedule at 11 PM Pacific (`America/Los_Angeles`)

Recommended steps:
1. `wctl run-npm install`
2. `wctl run-pytest ...` targeted a11y tests
3. `wctl run-npm test -- copytext map_gl`
4. `wctl run-playwright --suite theme-metrics`
5. `wctl run-playwright --suite full --grep "axe accessibility" --workers 1`
6. upload `test-results/theme-metrics/*` and `test-results/a11y/*` artifacts

Recommended smoke target configuration for shared dev host:
- `SMOKE_BASE_URL=https://wc.bearhive.duckdns.org`
- `SMOKE_SITE_PREFIX=/weppcloud`
- `SMOKE_RUN_CONFIG=disturbed9002_wbt`

This workflow should be reviewed manually and treated as release evidence, not PR policy.

## Manual Verification Checklist (Non-Automatable)

- Keyboard-only traversal across major flows (Tab, Shift+Tab, Enter, Space, Escape).
- Screen-reader spot checks for key pages/dialogs/status regions.
- Focus visibility on all interactive controls, including dynamic drawers/modals.
- Reflow/zoom checks at 200% for core controls and reports.
- Non-text contrast and meaningful status announcements (`aria-live`) for run feedback.

## Change Management Notes

- When adding or modifying accessibility behavior, update this doc and the most specific canonical source in the map above.
- Prefer small, test-backed updates linked to explicit WCAG criteria.
- Keep generated workflow edits in `.github/forest_workflows/` and rebuild generated workflow outputs.
