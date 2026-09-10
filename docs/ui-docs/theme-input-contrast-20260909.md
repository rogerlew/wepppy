# Pure form disabled-input contrast validation — 2026-09-09

Validated on Forest at `/weppcloud/ui/components/#theme-lab` with Playwright. All **42 rendered input-state measurements pass across 14 themes**, including the bundled, hidden `cursor-light` theme. Threshold: 4.5; lowest measured ratio: **6.098:1**.

## Defect and correction

Pure CSS supplied `#cad2d3` text on `#eaeded` for typed disabled inputs (1.305:1), overriding the canonical theme rule by selector specificity. The existing specimen lacked the `.pure-form` ancestor. The shared CSS now matches Pure’s selector specificity and wins by stylesheet order. Specimens use the real text-field macro within `.pure-form`, covering disabled-only, read-only-only, and combined disabled/read-only Scale factor map states. Field mutability and configuration authority are unchanged.

Metrics discovers theme IDs from both the selector and loaded `all-themes.css`, so hidden bundled themes cannot be omitted. All three input-state pairs are required to pass in every discovered theme.

## Rendered contrast ratios

| Theme | Scale map before | Disabled after | Read-only after | Scale map after |
| --- | ---: | ---: | ---: | ---: |
| default | 1.305 | 13.935 | 13.935 | 13.935 |
| light-high-contrast | 1.305 | 18.394 | 18.394 | 18.394 |
| onedark | 1.305 | 7.903 | 7.903 | 7.903 |
| dark-modern | 1.305 | 8.101 | 8.101 | 8.101 |
| ayu-dark | 1.305 | 10.121 | 10.121 | 10.121 |
| ayu-mirage | 1.305 | 8.852 | 8.852 | 8.852 |
| ayu-light | 1.305 | 6.098 | 6.098 | 6.098 |
| ayu-dark-bordered | 1.305 | 10.121 | 10.121 | 10.121 |
| ayu-mirage-bordered | 1.305 | 8.852 | 8.852 | 8.852 |
| ayu-light-bordered | 1.305 | 6.098 | 6.098 | 6.098 |
| cursor-dark-anysphere | 1.305 | 14.353 | 14.353 | 14.353 |
| cursor-dark-midnight | 1.305 | 10.365 | 10.365 | 10.365 |
| cursor-dark-high-contrast | 1.305 | 14.353 | 14.353 | 14.353 |
| cursor-light | Not sampled | 13.935 | 13.935 | 13.935 |

## Validation

- Before fix: new browser assertion failed at 1.305:1 using the production Pure form ancestry.
- After fix: full theme metrics passed, **1,568 measurements across 14 themes**, with all 42 input-state pairs passing.
- `wctl run-npm lint`: passed.
- `wctl run-npm test -- --runInBand`: 108 suites / 836 tests passed.
- `wctl run-pytest tests/weppcloud/routes/test_ui_showcase_bp.py tests/weppcloud/test_ui_foundation_css.py --maxfail=1`: 9 passed.
- The broad Python suite was not repeated for this CSS and gallery-metadata correction; actual browser cascade checks and focused route/CSS tests directly exercise the changed surfaces.

The full report retains 59 unrelated contrast failures in optional preference themes, unchanged from the initial 13-theme run; they do not involve these input states. No theme palette or unrelated enforcement policy changed. The initial report did not sample hidden `cursor-light`; the final run does.

Run the canonical browser check with:

    wctl run-playwright --suite theme-metrics --base-url https://wc.bearhive.duckdns.org/weppcloud --no-create-run

Full machine-readable and Markdown reports are generated at `wepppy/weppcloud/static-src/test-results/theme-metrics/theme-contrast.{json,md}`. CSS is served directly; no generated theme or controller bundle needed rebuilding. Forest web was restarted to load updated gallery metadata; production was not deployed. Existing browser sessions may require a hard refresh for cached CSS.
