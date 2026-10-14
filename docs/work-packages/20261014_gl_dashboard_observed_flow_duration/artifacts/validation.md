# Observed flow-duration validation

Date: 2026-10-14 UTC. Candidate: master working changes after reviewed checkpoint
`4e02ee2e0`. Environment: dev Compose weppcloud Python 3.12, host Node/Chromium.
Highest claim: locally validated; no production deployment.

## Automated checks

- Existing backend baseline: 10 passed.
- New observed Jest regressions before implementation: 5 failed as expected.
- Focused backend after fixes: 34 passed (real CSV/parquet reads, ownership,
  limits, missing/malformed/legacy data and parent lineage).
- Focused flow-duration frontend after fixes: 24 passed.
- Full frontend after final regression: 986 passed. Lint passes.
- Full Python suite: running; final result pending. The final area/encoding
  regressions also passed in a focused rerun after full-suite collection.
- Broad-exception enforcement versus checkpoint: pass, zero added broad catches.
  The required origin/master comparison fails on preexisting
  wepppy/nodb/core/climate_build_helpers.py (+1), outside this package.
- Code-quality observe-only command completed; radon unavailable in host runtime.
  Generated root reports were restored to avoid unrelated changes.

## Actual artifact readback

Read-only project: `/wc1/runs/ti/tight-orthodontist`. The normalized Observed CSV
contains 731 days (1995-01-01 through 1996-12-31), including 145 zeros. Independent
Python calculation and browser ranked output agree: maximum 6.5015665660666695 m³/s,
minimum 0, first exceedance 0.1366120218579235%. All 731 values remain when model
warm-up is five years. Source hashes before/after agree:

- `observed/observed.csv`: `70d876e255e3f9697c536c4d69ebc8fe913c4ccd3e53e5bf83911650102db0db`
- `wepp/output/interchange/totalwatsed3.parquet`: `021ea68100edd62c4952aaa721ac7281ee8af839bb169225f0a5450d99c4e70b`

Bootstrap read/parse: 0.027 seconds; serialized metadata
76,984 bytes. Synthetic 100-year sample: 36,524
rows, 1,119,688 CSV bytes, 3,567,001
metadata bytes, 0.234 seconds. These measurements
support the bounded reader; they are not production-load benchmarks.

## Browser evidence and reproducibility

`verify_browser.mjs` serves actual graph controller, graph loaders, state and
canvas renderer locally. It injects the real observation bootstrap plus a small
simulated-query fixture. Chromium verifies checkbox on/off, both source choices,
five-year simulation exclusion, log axis, legend, keyboard values and exact
oracle values, with zero page errors. Screenshot: observed-browser.png.

From repository root:

    wctl exec -T weppcloud python docs/work-packages/20261014_gl_dashboard_observed_flow_duration/artifacts/probe_observed.py > /tmp/fdc-real-data.json
    node docs/work-packages/20261014_gl_dashboard_observed_flow_duration/artifacts/verify_browser.mjs /tmp/fdc-real-data.json /tmp/fdc-observed-browser.png

The probe only reads the named project and creates its large synthetic sample in
a temporary directory. No secrets, uploads or model outputs are modified. This
proves local real-artifact consumption and graph wiring, not deployment or full
live-page authorization. Existing authorization paths remain unchanged.
