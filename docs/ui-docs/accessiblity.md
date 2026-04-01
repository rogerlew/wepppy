# Accessibility and Section 508 Strategy

This document is the single entry point for accessibility guidance, tests, and compliance strategy across the WEPPcloud UI stack.

## Scope

- Unify the current accessibility-related standards and tests across `docs/`, `tests/`, UI templates, controller JS, and CI workflow specs.
- Define a practical Section 508 strategy for this repo.
- Distinguish internal engineering evidence, the public accessibility statement, and the separate procurement-facing ACR/VPAT artifact.
- Keep accessibility checks manual-gate driven, not PR-blocking.

## Canonical Repo Map

| Area | Canonical source | Purpose |
| --- | --- | --- |
| UI accessibility patterns | `docs/ui-docs/ui-style-guide.md` | Core WCAG-aligned patterns (labels, focus visibility, keyboard behavior, status announcements). |
| Controller accessibility contract | `docs/ui-docs/controller-contract.md` | Required `aria-live` usage, modal/focus expectations, and resilient controller behavior. |
| Theme accessibility | `docs/ui-docs/theme-system.md` | Theme token model plus contrast guidance and operational workflow. |
| Contrast harness spec | `docs/ui-docs/theme-metrics.spec.md` | Rendered contrast measurement scope, reporting, and CI artifact model. |
| Manual AT pass evidence | `docs/ui-docs/manual-at-pass-20260331.md` | March 31, 2026 keyboard and accessibility-tree pass for core anonymous and authenticated workflows. |
| ACR draft worksheet | `docs/ui-docs/acr-draft-int.md` | Conservative source worksheet for later transfer into the formal `VPAT 2.5Rev INT` template. |
| VPAT workspace | `docs/ui-docs/vpats/README.md` | Runbook, mutable staging package, immutable issue archive, and template provenance for buyer-facing VPAT / ACR work. |
| Findings 1-6 remediation package | `docs/work-packages/20260331_wcag21aa_frontend_accessibility/package.md` | Scope and acceptance criteria for recent WCAG remediation. |
| Findings 1-6 execution evidence | `docs/work-packages/20260331_wcag21aa_frontend_accessibility/tracker.md` | Validation history, risks, and current caveats. |
| Template-level accessibility assertions | `tests/weppcloud/routes/test_pure_controls_render.py` | Semantic copy controls, map role changes, placeholder labels, standalone metadata checks. |
| Route-level map semantics assertion | `tests/weppcloud/routes/test_user_runs_admin_scope.py` | Guards map canvas semantics in runs template rendering. |
| Controller accessibility assertions | `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js` | Modal accessible-name and keyboard behavior coverage in map surfaces. |
| Copy control accessibility regression | `wepppy/weppcloud/controllers_js/__tests__/copytext.test.js` | Ensures semantic copy button behavior remains compatible. |
| Report accessibility probe page | `wepppy/weppcloud/templates/ui_showcase/report_accessibility_probe.htm` | Synthetic-but-representative report structures (tables, chart, filters, status, actions) used by axe smoke. |
| Rendered contrast smoke test | `wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js` | Theme-level WCAG AA contrast metrics from real DOM rendering. |
| Workflow spec (generated source) | `.github/forest_workflows/theme-metrics-nightly.yml` | Nightly contrast artifact run. |
| Workflow spec (generated source) | `.github/forest_workflows/playwright-controllers-nightly.yml` | Nightly controller-level UI regression coverage. |
| Workflow spec (generated source) | `.github/forest_workflows/npm-tests.yml` | PR/push frontend unit test baseline. |
| Playwright command wiring | `tools/wctl2/commands/playwright.py` | Source of truth for `wctl run-playwright --suite ...` behavior. |

## Standards Baseline

- Product quality target: WCAG 2.1 AA for core user journeys.
- Section 508 legal baseline for federal conformance references Revised 508 standards (which incorporate WCAG 2.0 A/AA via referenced accessibility standards).
- Product posture for federal buyers:
  - Section 508 conformance is the procurement baseline.
  - This document is an internal engineering strategy and evidence map, not the formal Accessibility Conformance Report (ACR/VPAT).
  - The public accessibility statement should summarize user-facing commitments and contact paths.
  - The product-specific ACR/VPAT must be maintained separately as the procurement artifact.
- Practical policy for this repo:
  - Treat WCAG 2.1 AA as the engineering bar.
  - Produce 508-friendly evidence packs from automated and manual checks.

External references:
- https://www.section508.gov/develop/applicability-conformance/
- https://www.section508.gov/sell/acr/
- https://www.section508.gov/sell/how-to-create-acr-with-vpat/
- https://www.section508.gov/test/testing-overview/
- https://www.section508.gov/test/elements-of-an-accessibility-test-report/
- https://www.section508.gov/test/trusted-tester/
- https://www.section508.gov/manage/governance/section-508-for-change-control-processes/
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

### 4) Structural page scans (axe / Playwright)

Use the smoke suite to probe representative public and authenticated surfaces:

```bash
wctl run-npm smoke:a11y
```

This currently validates, at a structural level:
- common page-level semantics across root, interfaces, profile, Theme Lab, report probe, and runs dashboard targets
- detectable issues around labels, headings, landmark structure, color-contrast failures surfaced by axe rules, and ARIA misuse
- authenticated runs-page coverage when agent credentials are available

## Coverage-to-Requirement Map

This table is an evidence map for engineering and release review. It is not a substitute for the criterion-by-criterion ACR/VPAT table.

| Evidence source | Primary checks in repo | WCAG 2.1 / 2.0 criteria most directly exercised | Revised 508 / manual-method relation |
| --- | --- | --- | --- |
| `tests/weppcloud/routes/test_pure_controls_render.py` and `tests/weppcloud/routes/test_user_runs_admin_scope.py` | language metadata, iframe/title requirements, accessible names independent of placeholders, map semantics | 3.1.1, 1.1.1, 2.4.1, 3.3.2, 4.1.2 | Web-content conformance evidence under Revised 508's WCAG references; aligns with Trusted Tester / ICT Baseline checks for language, titles, labels, and name/role/value. |
| `wepppy/weppcloud/controllers_js/__tests__/copytext.test.js` and `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js` | semantic buttons, modal accessible names, keyboard behavior for map-related UI | 2.1.1, 2.1.2, 2.4.3, 2.4.7, 4.1.2 | Supports software/web-application behavior checks typically confirmed with manual keyboard and assistive-technology testing. |
| `wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js` | rendered text, control, and non-text contrast across the theme set | 1.4.3, 1.4.11 | Supplies repeatable contrast evidence for the validated theme set; manual review still needed for context-specific exceptions and real-page edge cases. |
| `wepppy/weppcloud/static-src/tests/smoke/a11y/*.spec.js` | axe scans over representative anonymous and authenticated pages | partial structural coverage across 1.1.1, 1.3.1, 2.4.1, 2.4.6, 4.1.2 and related rules | Automated scan coverage only; Section 508 guidance requires manual confirmation for gaps and false positives/negatives. |
| Manual verification checklist in this document | keyboard traversal, screen-reader spot checks, zoom/reflow, live-region behavior | 1.4.4, 1.4.10, 2.1.1, 2.4.7, 4.1.3 | Aligns with Trusted Tester / ICT Baseline style manual validation and must remain part of release evidence. |

### Universal Design Theme Policy

WEPPcloud supports a mixed theme catalog for universal design and user preference:
- **AA-validated themes** (must remain WCAG AA in the metrics gate and are the only themes included in the conformance set):
  - `default`
  - `light-high-contrast`
  - `ayu-mirage`
  - `ayu-mirage-bordered`
  - `cursor-dark-midnight`
- **Sensory-preference themes** (still measured/reported, intentionally excluded from the conformance set):
  - `ayu-light`, `ayu-light-bordered`
  - `ayu-dark`, `ayu-dark-bordered`
  - `onedark`
  - `dark-modern`
  - `cursor-dark-anysphere`
  - `cursor-dark-high-contrast`

Latest captured metrics snapshot (generated at **March 31, 2026**):
- Light themes: `default` and `light-high-contrast` compliant; `ayu-light*` variants non-compliant.
- Dark themes: `ayu-mirage*` and `cursor-dark-midnight` compliant; remaining dark preference themes non-compliant.
- Operationally, this is acceptable only if:
  - the default remains in the AA-validated set
  - the selector clearly labels which themes are AA-validated versus sensory-preference only
  - the non-validated themes are not represented as part of the Section 508 conformance claim
  - federal-buyer deployments may keep the sensory-preference set visible only as supplemental user-choice themes outside the conformance set

Rationale for retaining a sensory-preference set:
- Research with autistic web users found that a low-contrast theme and multiple user-selectable color themes can improve access for some users, while also acknowledging that low-contrast palettes are a barrier for others and therefore cannot stand alone as the compliance baseline.
- Research with autistic adults also reports frequent hypersensitivity to bright lights, bright colors, clutter, and busy environments, with adaptation and control over the sensory environment acting as important coping strategies.

External references:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC6485264/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC8217662/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9213348/

### Literature Review: Neurodivergent Sensory-Preference Themes

This subsection records the current research basis for keeping optional sensory-preference themes in WEPPcloud while limiting the Section 508 conformance claim to the AA-validated theme set.

#### Working conclusion

- Current evidence supports optional, user-selectable sensory-preference themes as a supplemental accommodation for some neurodivergent users.
- Current evidence does not support treating low contrast itself as a generally superior accessibility baseline, or counting non-AA themes as part of the conformance claim.
- The strongest defensible claim is about user control over visual intensity, glare, saturation, clutter, and predictability, not about low contrast in isolation.

#### Strongest direct web/UI evidence

- The most directly relevant study is the participatory AASPIRE web-guidelines paper for autistic web users. It recommends:
  - at least one low-contrast neutral palette option for sensitive vision
  - multiple palette choices, including dark and light options
  - a visually simple and clutter-free interface
  - predictable navigation and layout
- The same paper also records the limiting caveat that low-contrast palettes can be an accessibility barrier for users with low vision. Its design response was not "use low contrast by default," but "offer multiple themes, including WCAG-conformant high-contrast options."

#### Broader sensory-environment evidence

- Qualitative research on autistic adults' visual experiences reports frequent difficulty with bright, flickering, fluorescent, and spot lighting; bright reds and yellows; cluttered or visually busy environments; and combinations of color, contrast, and pattern that become hard to tolerate or read.
- That work also found substantial person-to-person variation. Participants reported that the effect of color could not be predicted from hue alone because surrounding contrast, patterns, and color combinations changed the experience.
- Research on autistic adults in public spaces extends the same theme beyond color selection alone: disabling sensory environments were associated with sensory burden, busy/crowded spaces, lack of predictability, limited adjustments, and difficulty recovering from overload.
- Mixed-methods and systematic-review work on autistic sensory experience also points in the same direction: sensory hyperreactivity is common, but triggers and helpful adaptations are highly individual, which argues for personalization rather than a single palette strategy.

#### Evidence outside autism

- Evidence for other neurodivergent groups is weaker but still relevant. A 2014 ADHD study reported substantially higher self-reported photophobia among adults with ADHD symptoms than controls.
- That finding is useful as supporting plausibility for lower-intensity or glare-reducing options, but it is not enough to justify a broad claim that low-contrast themes are generally preferable across neurodivergent users.

#### Design implications for WEPPcloud

- Keep AA-validated themes as the default and the conformance baseline.
- Keep sensory-preference themes available as optional user settings for users who benefit from calmer or lower-intensity presentation.
- Describe the benefit in terms of sensory accommodation and user control, not as an alternative compliance path.
- Prefer a broader sensory-control posture where feasible: reduced motion, lower saturation, calmer layout density, predictable placement, and dark/light AA-compliant variants.
- Federal-buyer deployments for the current product posture keep sensory-preference themes user-visible, but only as supplemental user-choice themes outside the AA-validated conformance set.

#### Limits and follow-up

- Most cited evidence is strongest for autistic adults; evidence for ADHD and other neurodivergent groups is thinner.
- Much of the evidence is qualitative or mixed-methods rather than controlled product-UI trials.
- The literature supports personalization and sensory-load reduction, but it does not provide a basis to weaken WCAG AA contrast requirements for the conformance set.
- If WEPPcloud wants to make a stronger product-specific claim later, the next step is a small usability study comparing AA-validated themes and sensory-preference themes for comfort, readability, task completion, and error rate.

Additional references:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC10726197/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9201716/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC4261727/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12715023/

Nightly artifact workflow source:
- `.github/forest_workflows/theme-metrics-nightly.yml`

## Known Gaps

- Axe coverage includes Theme Lab, report accessibility probe, WEPPcloud root, interfaces, profile, and runs0 dashboard.
- A formal ACR/VPAT has not yet been published for federal procurement.
- Theme-selector labeling should stay synchronized with the AA-validated set in the theme metrics gate; dynamic artifact-driven labeling is still a follow-up improvement.
- The March 31, 2026 core-flow manual pass now includes a formal local browser / operating system / assistive-technology matrix, and no separate spoken-screen-reader matrix is currently planned for the buyer issue unless scope changes.

## VPAT Lifecycle

- Maintain one mutable staging package in `docs/ui-docs/vpats/current/`.
- Archive only buyer-facing issues in `docs/ui-docs/vpats/issued/`.
- Refresh the staging package when conformance-impacting UI behavior, authentication UX, theme baseline, support docs/channels, scope, environment matrix, major remediation, or the official template version changes.
- Stack related pre-production changes into the same staging package.
- Before production deployment, if any tracked conformance trigger changed since the last issued package, refresh `current/` and cut a new issue package for the frozen deployment snapshot.

## Section 508 Strategy (Manual Gate, Non-Blocking)

The repository should keep accessibility as a release-readiness gate that is run manually, not as a required PR check. Non-blocking at PR time does not mean non-blocking at release time.

### Gate posture

- Do not mark accessibility CI checks as required branch-protection statuses.
- Keep accessibility workflow(s) `workflow_dispatch` (optionally also scheduled) and use pass/fail plus artifacts for reviewer signoff.
- Treat accessibility review as a release gate:
  - Critical accessibility defects block release until remediated, or
  - if release proceeds under exception, the issue must be formally risk-tracked with owner, severity, affected workflow, buyer/user impact, and target remediation date.
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
4. Classify defects by severity and determine release disposition:
   - Critical: block release
   - High/Moderate/Low: remediate before release when feasible, otherwise document risk and owner
5. Record outcome in release notes/work package tracker before release signoff.

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
- Profile page (`/weppcloud/profile/`)
- Report accessibility probe (`/weppcloud/ui/components/report-a11y`)
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

1. Create `docker/secrets/dev-agent.env` (gitignored):
   - `DEV_AGENT_EMAIL=<dev-agent email>`
   - `DEV_AGENT_PASSWORD=<dev-agent password>`
   - `SMOKE_AGENT_EMAIL=<dev-agent email>`
   - `SMOKE_AGENT_PASSWORD=<dev-agent password>`
2. Set file permissions:
   - `chmod 600 docker/secrets/dev-agent.env`
3. Run the suite (it auto-loads this file by default), or override with:
   - `SMOKE_AGENT_CREDENTIALS_FILE=/path/to/file.env`

Legacy compatibility:
- `docker/secrets/ally-agent-smoke.env` with `ALLY_AGENT_EMAIL` / `ALLY_AGENT_PASSWORD` is still supported.

Optional strict mode:
- `SMOKE_AGENT_REQUIRED=true` to fail/skip fast when agent credentials are missing.
- In OAuth-only deployments where local password login is disabled, the `/weppcloud/profile/` axe target is kept in the suite but will be marked skipped with an explicit auth reason unless a pre-authenticated browser session is supplied.

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

Latest recorded evidence:

- `docs/ui-docs/manual-at-pass-20260331.md`

## Public-Facing Artifacts

- Landing-page accessibility statement:
  - publish a public statement linked from the landing page/footer
  - include standards target, support/feedback contact, known limitations, alternate-format path, and last-updated date
  - state explicitly that the statement does not replace the ACR/VPAT
- ACR/VPAT:
  - maintain separately using the current ITI VPAT template applicable to federal procurement
  - update when material accessibility-impacting releases ship
  - align evaluation methods, environments, and limitations with the release evidence described in this document

## Change Management Notes

- When adding or modifying accessibility behavior, update this doc and the most specific canonical source in the map above.
- Prefer small, test-backed updates linked to explicit WCAG criteria.
- Keep generated workflow edits in `.github/forest_workflows/` and rebuild generated workflow outputs.
