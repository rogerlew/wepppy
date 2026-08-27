# WP09 Validation Evidence

## Automated behavior

- Focused NoDb, rq-engine, and rendered-template suite: `171 passed`.
- Frontend lint: passed.
- Full frontend Jest baseline: `107` suites and `791` tests passed.
- Dedicated controller suite: `5` tests passed, covering one page-load GET,
  deferred complete preview, safe text rendering, exact apply/job completion,
  stale-preview recovery, and duplicate-submit prevention.
- Generated `controllers-gl.js` was rebuilt locally from controller sources
  with the repository virtual environment; the generated bundle is ignored by
  source control as designed.

## Structural accessibility check

The rendered shared-header test verifies hidden-by-default state, dialog role,
modal naming/description, merge-only explanatory text, alert/status semantics,
table caption/column headers, and disabled initial apply. Canonical
`shared_ui_contracts.test.js` retains ModalManager focus trap, Escape, and focus
return coverage and passed in the full Jest baseline.

## Contract and isolation gates

- Stubtest, test-stub completeness, endpoint inventory, and route-contract
  checklist: passed.
- Focused randomized and per-file isolation checks: passed.
- Changed-file broad-exception enforcement: passed with net delta `+0`.
- Work-package and affected canonical documentation lint: passed.

## Browser accessibility run

`wctl run-playwright --suite full --grep "axe accessibility" --workers 1`
completed with `7 passed`, `1 skipped`, and `3 failed`. The failures did not
report WP09 accessibility violations: the theme lab fixture lacked
`#themeContrastTargets`, the activated-session setup rejected an invalid target
URL, and the runs0 dashboard fixture lacked `form#setloc_form .wc-map`. The
successful scans reported zero violations for the report probe, root page,
interfaces, profile, and config builder. These environment/page-fixture
failures are retained as transparent non-WP09 validation limitations.

## Repository-wide gate

- `wctl run-pytest tests --maxfail=1`: `6927 passed`, `63 skipped` in
  `678.82s`.
