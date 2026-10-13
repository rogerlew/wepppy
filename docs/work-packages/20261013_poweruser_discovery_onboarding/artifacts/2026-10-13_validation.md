# PUUX-01 Forest validation

Status: Forest implementation, browser/readback checks and cleanup complete. Independent reviews are retained alongside this receipt.

## Source and boundaries

Contract checkpoint: `2f9f944433147ee497e3c6115c25d96cc9e0b71c` on master.
Reviewed source/test candidate: `3df2ec482` (runtime `ed80608fe`); exact hashes and served-JS parity are in `source-identity.json`. The candidate changes presentation, client completion handling and help content.
No route, grant transaction, statement version, registry permission, queue or
scientific output writer changed. Direct static JavaScript requires no generated
controller bundle. The usersum manifest and navigation register the guide under
Advanced and Operations; protected navigation sections are unchanged.

## Automated checks

- New JS assertions failed against the prior implementation: 6 failed, 7 passed.
- Final focused feature-access JavaScript: 16 passed.
- Final complete frontend tests: 118 suites, 980 tests passed.
- Focused render/presentation tests: 228 passed.
- Usersum contracts, generated-index construction, routes and shell: 64 passed.
- Earlier focused server run: 198 passed before one old report fixture failed;
  that fixture expected a restricted trigger while rendering anonymously. It
  now supplies its intended PowerUser identity; the full render suite passes.
- Changed broad-exception enforcement: pass; no production Python handlers changed.
- Frontend lint remains blocked by the preexisting conditional expectation at
  `controllers_js/__tests__/climate.test.js:300` (`jest/no-conditional-expect`).
  This file is unchanged by PUUX.
- Broad Python coverage: **10,723 distinct passed, 126 skipped**, completed in
  segments. This was not a clean single full-suite run. Two old standalone Runs
  render/browser fixtures required real viewer context and a Profile endpoint;
  both are corrected, including the actual file-to-SQL-to-Chromium catalog chain.
  An unchanged OpenET JWT test returned 401 rather than 403 in reduced
  collection, then all 52 tests in its module passed in isolation. Existing
  `test_auth_tokens.py` replaces the canonical module in `sys.modules` during
  collection; this is a plausible source of order sensitivity, not a proved
  production-auth defect. No auth code changed. An unchanged catalog TTL timing
  test measured a 57.4ms p95 delta against its 50ms limit; all 24 catalog tests
  passed on rerun. The final 183-test segment passed. Exact overlap accounting
  and resume exclusions are retained in `broad-coverage.json`.
- The compact notice and Runs-scope regression set: 36 passed.
- Retained output: `automated-checks.txt` and `red-green-jest.txt`.

## Real Forest evidence

The opt-in `poweruser-onboarding.spec.js` uses real Forest sessions, CSRF,
account database and endpoints. Session fixtures bypass password/CAP login;
login UX is not claimed as tested. All identities are newly created disposable
accounts. The populated identity temporarily joins the preexisting disposable
CBEXEC project `sabbatical-stitcher`; existing accounts and project content are
not modified.

`forest-onboarding-browser.json` records the passed browser journey: empty and
populated Runs, table/map notice, keyboard submission, same-fragment real Profile
reload and focus, Config Builder destination, notice removal, legacy/Admin/Root/
Dev states, missing-CSRF and stale-statement rejection, anonymous rejection and
internal batch denial. `forest-profile-active.png` captures the 390px layout.

`forest-grant-readback.json` independently reads the real database: exactly one
PowerUser acceptance for account 2249 after a duplicate grant, PowerUser/User
roles, no internal memberships or acknowledgment, and legacy access without
fabricated acceptance. This is durable-state evidence in addition to rendered
success. Two earlier browser attempts granted their disposable identities but
failed while retrieving a response body after navigation; the final smoke waits
for actual navigation and validates state independently instead.

Guide integration initially returned 404. Manifest registration then exposed
the catalog's exact manifest/navigation coverage requirement. Both source files
are now updated and all 64 usersum checks pass. Forest's generated catalog was
rebuilt with the existing tool; the generated file is excluded from this change
as required by root instructions. After a bounded Forest web restart,
`forest-presentation-readback.json` confirms guide HTTP 200, reachable voluntary
internal acknowledgment, task headings and working Technical details expansion.
The desktop notice is 136px high instead of the generic panel's 256px minimum.
Desktop and 390px screenshots are retained. Existing narrow-page overflow in
Runs search/table/theme controls is outside this bounded presentation change;
this is not a claim that the whole application is free of mobile layout defects.

Integration QA was performed by the implementation agent, with independent
correctness/UX and security review recorded separately. No third independent QA
review is claimed. The remaining test-isolation follow-up is to remove the
collection-time canonical auth-module replacement in the existing JWT unit tests;
this package does not change that unrelated fixture or loosen its admission check.

## Rollout and recovery

No production deployment has occurred. Production rollout remains a separate
operator action through the installed wctl preset and canonical
`scripts/deploy-production.sh`. The guide requires refreshing the usersum index
with `tools/usersum_docs_tool.py build-index --write --skip-vendor-sync --require-vendor-files`
in the application environment before refreshing web processes. Verify the
linked guide returns 200 after deployment; an old generated index can survive
source-only deployment. No database migration or role backfill is needed.

Rollback restores the paired templates, static JS and documentation catalog;
retain legitimate role grants and acceptance history. Disposable-account cleanup
deactivates only the test identities, rotates authentication uniquifiers, removes
their test-run association and stored sessions, and retains acceptance/audit data.
The cleanup driver and nonsecret receipt are retained with this evidence.

Browser conformance is not an observed-user usability study. No participant
completion rates or user-learning outcomes are claimed.

Cleanup completed: `forest-account-cleanup.json` records all 18 inactive accounts,
removed sessions/associations, rotated authentication uniquifiers and unchanged
acceptance counts (3 before and after). Ignored credential files were removed.
The final served presentation smoke passed in 8.5 seconds. The panel's original
desktop grid leaves unused columns after moving raw resources into Details;
independent review classifies this as a nonblocking layout follow-up.
