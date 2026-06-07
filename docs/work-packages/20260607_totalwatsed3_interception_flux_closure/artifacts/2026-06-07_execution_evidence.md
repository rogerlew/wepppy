# Execution Evidence — totalwatsed3 Interception Flux Closure

Date: 2026-06-07 UTC
Status: complete

## Scope Executed

- Added optional `Interception` handling in `wepppy/wepp/interchange/totalwatsed3.py`.
- Added interception outflow to closure identities in `tools/totalwatsed3_daily_closure_audit.py`.
- Updated `docs/dev-notes/totalwatsed-interchange.spec.md` for interception semantics.
- Added focused regression coverage in:
  - `tests/wepp/interchange/test_totalwatsed3.py`
  - `tests/tools/test_totalwatsed3_daily_closure_audit.py`

## Validation — Targeted Tests

Ran:

```bash
wctl run-pytest tests/wepp/interchange/test_totalwatsed3.py tests/tools/test_totalwatsed3_daily_closure_audit.py
```

Result:

- `8 passed, 2 warnings`

## Acceptance Evidence (openWEPP post-WBVAL06 output)

### Input source

openWEPP WBVAL06 post-fix hillslope WAT outputs:

- `/tmp/wbval06_interception_after_20260607T000000Z/outputs/p*/H*.wat.parquet`

### Acceptance dataset construction

Because this WBVAL06 artifact set publishes per-prefix `H*.wat.parquet` and does
not include a prebuilt watershed `H.pass.parquet`, a consolidated daily
`totalwatsed3`-like acceptance parquet was built by aggregating the published WAT
terms across prefixes by `(year, sim_day_index, julian, month, day_of_month,
water_year)`, preserving producer-published interception (`Interception`) and
storage terms.

Generated artifact:

- `/workdir/wepppy/tmp/totalwatsed3_interception_flux_closure/openwepp_post_wbval06_totalwatsed3_like.parquet`

Audit outputs:

- `/workdir/wepppy/tmp/totalwatsed3_interception_flux_closure/audit_openwepp_post_wbval06/daily_closure_audit_summary.json`
- `/workdir/wepppy/tmp/totalwatsed3_interception_flux_closure/audit_openwepp_post_wbval06/daily_closure_audit_top_days.csv`

Annual residual exports:

- `/workdir/wepppy/tmp/totalwatsed3_interception_flux_closure/openwepp_post_wbval06_annual_residuals.csv`
- `/workdir/wepppy/tmp/totalwatsed3_interception_flux_closure/openwepp_post_wbval06_annual_residuals_with_without_interception.csv`

### Key measured results

From `openwepp_post_wbval06_annual_residuals_with_without_interception.csv`:

- Year index 2: with interception `1.8705267890162247e-07`, without interception `14.711778848233783`
- Year index 3: with interception `1.9046265731237355e-07`, without interception `14.881591907752764`
- Year index 4: with interception `1.9491789188252895e-07`, without interception `18.939260615671138`
- Year index 5: with interception `2.0654474019998759e-07`, without interception `16.73963270592777`
- Year index 6: with interception `2.086576434412457e-07`, without interception `16.158012640926525`

Acceptance interpretation:

- Years `2..6` close within tolerance after including interception.
- The same rows show large positive annual residuals when interception is omitted,
  matching the expected failure mode this package closes.
- `ET` inputs remain unchanged; interception is consumed as a separate outflow.
