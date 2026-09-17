# Validation

Validation completed on 2026-09-17 against contract checkpoint `714693a00`.

## Automated checks

- `wctl run-npm test -- --runInBand postfire_report`: 25 tests passed.
- `wctl run-npm test -- --runInBand`: 112 suites and 904 tests passed before
  the final report-scoped event-link contrast adjustment. The focused suite and
  lint passed again after that adjustment.
- `wctl run-npm lint`: passed after the final source changes.
- `wctl run-pytest tests/weppcloud/routes/test_postfire_report_bp.py
  --maxfail=1`: 26 tests passed after the final source changes.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref
  origin/master`: passed; no changed Python production files.
- `wctl doc-lint` passed for the work package, report contract, accessibility
  strategy and end-user guide.
- `wctl run-playwright --suite theme-metrics`: passed, collecting 1,568
  measurements across 14 themes. The suite retained 59 known, non-enforced
  failures in optional themes; the enforced suite passed.

An exploratory repository-wide `wctl run-pytest tests --maxfail=1` run reached
7% of 9,081 collected tests without a failure. It was stopped because the broad
suite would have delayed the required stack restart and report-specific browser
acceptance; it is not counted as a completed gate.

## Restart and authenticated browser acceptance

The complete Compose stack was restarted with `wctl restart`; `wctl ps`
confirmed the application, data services, RQ services and workers returned.
The read-only acceptance script then opened the saved M3 report at
`thespian-cleanness` through the normal authenticated HTTPS route.

Final acceptance passed with:

- one four-row `wc-summary-pane` definition list and a populated Notices value;
- a final SVG label layer using the computed text and surface theme tokens, a
  3-pixel rounded halo, stroke-first paint order and pointer transparency;
- a real-browser overlap hit-test whose topmost pointer target remained the
  scenario circle, followed by successful Tab/Enter/Space marker selection;
- four canonical filter fields, 16–18 pixel theme-token gaps, 120-pixel numeric
  inputs, no horizontal form overflow at 390 pixels, and preserved Apply/Reset
  query encoding;
- a delayed filter request showing event-date controls disabled at opacity 1
  with their computed color equal to `--wc-button-disabled-text`, followed by a
  reload and successful real Apply/Reset requests;
- zero axe violations in default, light high-contrast and Cursor Dark Midnight
  themes; and
- no browser page errors.

The first live probe before restart correctly observed the prior cached
template. Subsequent acceptance exposed two real presentation defects and kept
them in the repair loop: Pure form specificity stretched the numeric inputs to
232 and 200 pixels, and event-date links on striped rows had 4.08:1 contrast.
The final scoped CSS restores 120-pixel inputs and uses the existing theme hover
token for those event links. Axe then reported zero violations in each required
theme.

Retained evidence:

- `browser/evidence.json`: computed geometry, theme colors and interaction
  outcomes;
- `browser/axe.json`: final default-theme axe result;
- `browser/*-desktop.png` and `browser/*-narrow.png`: visual evidence for the
  three validated themes; and
- `browser_acceptance.cjs`: repeatable authenticated acceptance script.
