# Current Environment Matrix

This file freezes the environment assumptions for the next VPAT / ACR issue.

## Current Matrix

| Field | Current value |
| --- | --- |
| Evaluation date | March 31, 2026 |
| Time zone | `America/Los_Angeles` |
| Host | Local docker-backed WEPPcloud stack |
| Base URL | `http://localhost:8000` |
| Operating system | Ubuntu 24.04.4 LTS |
| Primary evaluated browser / engine | Chromium 141.0.7390.37 via Playwright |
| Additional installed browsers recorded | Google Chrome 146.0.7680.75, Mozilla Firefox 149.0 |
| Installed assistive technology recorded | Orca 46.1 |
| Authenticated test user | `dev-agent@example.com` |
| Auth method for authenticated browser checks | Local server-side session cookie minted from the `weppcloud` container for browser import |
| Contrast handling | `axe` `color-contrast` disabled in the manual pass because rendered contrast is covered separately by the theme-metrics harness |

## Refresh Triggers

Refresh this file when:

- the evaluated OS changes
- the primary browser / engine changes
- the assistive-technology matrix changes
- the authenticated test method changes
- the production-bound issue uses a different deployment environment than the current staging package

