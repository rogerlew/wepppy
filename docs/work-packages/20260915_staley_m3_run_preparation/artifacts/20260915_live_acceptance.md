# Real fresh-basin acceptance — 2026-09-15 20:07 UTC

Development URL: https://wc.bearhive.duckdns.org/weppcloud/runs/overpriced-sprawl/config/

Normal authenticated browser Run M3, no manual pre-acquisition. The pointer was
absent before this execution. Existing WEPP interchange was allowed to finish
before taking the baseline; only idle development rq-engine/rq-worker services
were restarted to load the code. No production deployment.

- Job: `43bf711b-dd44-4c18-a2a2-d8f60c9ea857`.
- Attempt: `092439d0c00e458dac57949641a5cbb6`.
- POST 200, job finished, accepted result current, partial false.
- Automatic receipt: `source_preparation/b8e644085a2d4425b2f0bc251fd9b105/receipt.json`.
- Promotion committed with no cleanup warnings.
- Actual worker identity UID 1000 / GID 993; pointer and result parquet owned
  by 1000:993 with mode 0644. No identity/mount/permission workaround was used.
- Valid coverage: 410,121 / 410,121 cells, all original USGS THICK fallback.
  SDA identifies the two spatial keys (658504 and 665730) as STATSGO, not SSURGO;
  their raw cache records are not incorrectly promoted to the primary tier.
- Predictors: T=0.05643304623594102, F=0.4776809770774966,
  S=0.6520827553617857.
- All 27,450 event rows, 12 design rows and 3 inverse rows available.
- Independent literal Table-4 arithmetic passed for every available row;
  exact uint8 mask membership/counts passed.
- Before/after SHA-256 comparison: 2,648 protected files, zero changes to
  soils, RUSLE, or generated WEPP run inputs.
- Result reload, exact-mask download and SI/English area-warning display passed.
  The existing out-of-study-area warning remains: this is a 41.0121 km² basin.

## Retained evidence and reproduction

Run-root evidence:
`/wc1/runs/ov/overpriced-sprawl/postfire_debris_flow/validation/20260915_run_preparation/`.
Read `arithmetic.json`, `protected_before.json`, `protected_after.json` and
`browser_host/{browser,state,jobstatus,jobinfo}.json`; browser completion text,
summary, downloaded mask and screenshot are alongside them. Source requests,
raw responses, native window, snapshots and receipts remain in visible module
`source_preparation/`; attempt `status.json` links its receipt and promotion.

Reused (without editing) the prior package's `live_browser.cjs`,
`audit_protected_inputs.py`, and `verify_live_results.py`. Browser execution must
use host Node/Playwright here; the container attempt failed at browser setup
before project mutation. The first input audit rejected an independently
changing WEPP output; retaken after its job completed. These observations are
not suppressed or counted as model failures.

The prior all-unavailable attempt is retained for comparison. No basin-specific
input path, key, projection, credential, or formula was added to production code.
