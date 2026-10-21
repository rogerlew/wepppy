# Validation

Evidence root: `/workdir/wepp-gregorian-repair-20261021`.

- `calendar-tests.log`: 62 passing tests, actual stmget plus shared header helper.
- `fpm-reader.log`: PS05 passes both schemas, years 100/200/300/400,
  1900/2000, runtime legacy rejection, explicit offline access, invalid-date cursor.
- `fpm-bridge.log`: historical bridge fixtures pass explicit offline policy.
- `fortitude.log`: eight touched free-form sources/tests pass.
- `ascii400/execution.json`, `hbp400-final/execution.json`: complete paired 400-year
  single-hillslope/channel simulations; generated daily audit finds 146,097
  climate-aligned water and watershed event dates, ending year 400 day 366.
- `ascii-final/calendar-audit.json`: completed watershed and all 104 hillslopes have
  73,048 water and PASS days matching the climate and daily precipitation. The
  master PASS has the same sequence; all 73,048 watershed event rows align.
- Both candidate host smoke tests pass after supplying an explicit HBP sidecar.
  Without that sidecar the smoke tool assumes ASCII cards (retained initial failure).
- Watchlist blocked by missing `/wc1/runs/ca/carved-letter/wepp/runs/p136.run`.
- Full fpm initially reported WBK08 SIGSEGV and nine hourly-adapter assertions,
  plus outdated fixture expectations. Bridge and router targets now pass. The
  unrelated WBK08/hourly cached failures were already isolated against pre-fix
  source in `20261021_hbp_schema2_calendar_selection/artifacts/validation.md`.
- Native full pytest: 253 passed, two failures. One missing external watchlist
  fixture; one old leap assertion collected before the edit. The final 62-test
  targeted rerun includes and passes its replacement. No full-green claim.
- Freshly rebuilt pre-calendar source baseline: all nine 44-year common text
  outputs byte-identical. HBP binary changes only metadata: all 16,104 decoded
  PASS rows/columns are equal (`hbp-payload-parity.log`). Initial snapshot-binary
  watershed differences reflected the prior schema-2 fix not yet compiled there.
- Observability: all ten 400-year common model outputs byte-identical with
  diagnostics off/on (`observability-comparison.json`).
- ASCII downstream conversion completes: 7,596,992 hillslope PASS records and
  valid Gregorian dates in every dated Parquet output. Rust converter correction
  for new-policy schema-2 padding passes 14 HBP tests and all 109 crate tests.

Both full 200-year watershed runs complete. The HBP raw audit confirms all 104
hillslopes and 73,048 watershed days match climate dates and precipitation. Its
full downstream conversion also passes: 7,596,992 unique daily PASS keys, day
indexes 1–73,048 and zero invalid dates in every dated Parquet table. No live project
outputs or deployed binaries were changed.

Additional retained evidence: `ascii-matched-predivergence.json` compares the
released hillslope binary against the corrected ASCII candidate under the same
inputs/environment. All 36,524 daily rows before the first phantom century day
are identical. Comparison against the originally persisted live H1 output differs
earlier (day 342/year 2), so the matched replay is the controlled regression
baseline; original-output identity is not claimed. The predecessor investigation
already recorded an unresolved original/replay numerical-environment gap.

The 400-year HBP downstream audit passes with the isolated Rust candidate:
146,097 unique daily PASS keys and 146,097 watershed event rows. All dated outputs
have valid Gregorian dates. The deployed shared object and native tracked binary
contents remain unchanged; candidate binaries are retained under the evidence root.

Rust API validation: all 163 Python `tests/wepp_interchange` tests pass against the
isolated candidate package; all 109 Rust crate tests and targeted rustfmt pass.
No installed/shared release library was replaced. The additional padding repair
is retained as `interchange-padding.patch`, with its candidate shared-object path
and SHA-256 in `interchange-binary.json`.
