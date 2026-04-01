# Manual AT Pass: Core Workflows

This note records the manual accessibility pass completed on **March 31, 2026** for the core anonymous and authenticated WEPPcloud workflows used as current ACR evidence.

## Scope

In scope:

- anonymous landing page: `/`
- anonymous interfaces page: `/interfaces/`
- anonymous Theme Lab: `/ui/components/`
- anonymous report accessibility probe: `/ui/components/report-a11y`
- authenticated profile page: `/profile`
- authenticated runs page: `/runs/<runid>/disturbed9002_wbt/?playwright_load_all=true`

Out of scope:

- OAuth provider flows
- third-party sites
- full spoken screen-reader output capture on Windows/macOS AT stacks

## Environment Matrix

| Field | Value |
| --- | --- |
| Evaluation date | March 31, 2026 local time (`America/Los_Angeles`) |
| Host | Local docker-backed WEPPcloud stack |
| Base URL | `http://localhost:8000` |
| Browser | Chromium via Playwright |
| Authenticated test user | `dev-agent@example.com` |
| Auth session method | Local server-side session cookie minted from the `weppcloud` container for browser import |
| Contrast handling | `axe` `color-contrast` rule disabled during this pass because contrast is covered separately by the theme-metrics harness |

## Formal Browser / Operating System / Assistive Technology Matrix

| Operating system | Browser / engine | Assistive technology / inspection mode | Status in this pass | In-scope workflows | Notes |
| --- | --- | --- | --- | --- | --- |
| Ubuntu 24.04.4 LTS | Chromium 141.0.7390.37 via Playwright | Keyboard-only traversal plus browser accessibility-tree inspection | Completed | `/`, `/interfaces/`, `/ui/components/`, `/ui/components/report-a11y`, `/profile`, `/runs/<runid>/disturbed9002_wbt/?playwright_load_all=true` | This is the primary formal matrix row for the March 31, 2026 evidence set. |
| Ubuntu 24.04.4 LTS | Google Chrome 146.0.7680.75 | None exercised in this pass | Installed, not exercised | None | Recorded to freeze the local desktop browser inventory for the evaluated workstation. |
| Ubuntu 24.04.4 LTS | Mozilla Firefox 149.0 | None exercised in this pass | Installed, not exercised | None | Recorded to freeze the local desktop browser inventory for the evaluated workstation. |
| Ubuntu 24.04.4 LTS | Firefox / Chromium desktop stack | Orca 46.1 | Installed, not exercised | None | Spoken screen-reader output capture remains a follow-up item outside this recorded pass. |

## Method

This pass combined:

- keyboard-only traversal using sequential `Tab`
- browser accessibility-tree spot checks through Playwright
- targeted `axe` scans for WCAG 2.0/2.1 A/AA structural rules other than color contrast

The pass was intended to close the repo's core-flow manual evidence gap and freeze a formal local browser / operating system / assistive-technology matrix. For the current buyer issue, this documented matrix defines the manual-evidence boundary; a broader named spoken-screen-reader lab matrix is not planned unless scope changes.

## Results

### Anonymous pages

| Page | Result | Notes |
| --- | --- | --- |
| `/` | Pass after remediation | A critical `axe` `select-name` issue was found on the landing-page run-year filter and fixed during this pass. Re-scan after the fix reported `0` violations. |
| `/interfaces/` | Pass | `0` `axe` violations after scan. |
| `/ui/components/` | Pass | `0` `axe` violations after scan. |
| `/ui/components/report-a11y` | Pass | `0` `axe` violations after scan. |

### Authenticated pages

| Page | Result | Notes |
| --- | --- | --- |
| `/profile` | Pass | `0` `axe` violations after scan. |
| `/runs/<runid>/disturbed9002_wbt/?playwright_load_all=true` | Pass | `0` `axe` violations after scan on a provisioned run created through `/tests/api/create-run`. |

## Keyboard / Focus Observations

Anonymous pages:

- Landing page focus order reached the primary navigation links and the map canvas in a predictable sequence.
- Interfaces page focus reached the site link, login link, theme selector, and interface resource links without trapping.
- Theme Lab and report probe pages exposed keyboard-reachable links and controls in the sampled sequence.

Authenticated pages:

- Profile page focus reached `Change Password`, `Logout`, `Reset browser state for this site`, `Mint JWT Token`, and the token textarea in sequence.
- Runs0 focus reached the site link, run link, run name input, scenario input, README/FORK/ARCHIVE actions, the theme selector, and the `Mods` / `More` disclosure summaries in sequence.

Focus styling:

- Inputs and selects consistently exposed a visible focus treatment using either a solid outline or a high-contrast box shadow.
- Several anchor and summary controls rely on browser-default focus outlines (`auto 1px`), which remained visible in the sampled pass.

## Findings Closed During This Pass

- Landing page root: critical `axe` `select-name` failure on the run-year filter.
  - Remediation: explicit `aria-label="Run year filter"` added in the landing app source and the exported landing bundle was rebuilt.
  - Verification: post-fix re-scan reported `0` violations on `/`.

## Residual Limits

- This pass did not capture spoken output from Orca, NVDA, JAWS, or VoiceOver.
- For the current buyer issue, no separate spoken-screen-reader matrix is planned; the manual evidence boundary is the documented local browser / operating system / assistive-technology matrix in this note.
- `wepp.cloud` was not used for the authenticated pass because the current test account did not exist there, and the live password form currently renders `action="/weppcloud/weppcloud/login"` instead of the canonical login path.

## Release Posture

- For the evaluated local build, no critical accessibility defects remained open in the scanned core anonymous and authenticated workflows after the landing-page filter-label fix.
- This note is suitable as release evidence input for the ACR worksheet, but it is still not the final buyer-facing ACR artifact.
