# Narrow repair regression QA

Date: 2026-10-21. Reviewer: independent secondary QA agent.
Scope: updated native tests, retained fixtures, generator and the three narrow
source changes. No production or test source was changed by this reviewer.
This is not full watershed-routing approval.

## Current disposition

The narrow source/test changes pass secondary QA at the final snapshot below.
All medium findings raised here are resolved: management coverage, partially
depleted profiles, withdrawal roundoff and invalid source durations. Independent
scientific review additionally corrected the duration bound to the physical day
instead of the rounded numerical grid endpoint. Full current-binary replay and
actual 400-year model execution remain pending in this review; successful input
generation and focused tests do not satisfy those gates.

Reviewed source is native baseline `6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb`
plus the working changes. Relevant SHA256 snapshots:

| File | SHA256 |
| --- | --- |
| `tools/physical_water_case.py` | `70a2a822e48b6b1994681861cd5aeead93f704b0d7a5f163588e12e789c53b86` |
| `tests/test_physical_water.py`, final tested snapshot | `205bb4ea87ffb9d1908a39a5d058416d4d5323b91033901515f364633c40df0c` |
| `tests/test_component_reconstruction.py` | `7db66a2f833f4f2b070c724b697d2437f99e658dc7b12e20ac50a4b7a4464ed4` |
| `src/watbal_hourly.for`, binary64 withdrawal working state | `c828a9b714347f0aa6f8e62509328a7c4dfe3b629d3c30029e300a7a8514bb32` |
| `src/chrqin.for`, physical-day duration bound | `3e5eba9a74b044943193bdd3f3edee6935cda00a1b27d4ea982598e38a6b65a8` |

## Independent checks

From `/workdir/wepp-forest-release-20261009`:

```bash
PATH=/usr/bin:/bin /workdir/wepppy/.venv/bin/python -m pytest -q tests/test_physical_water.py tests/test_component_reconstruction.py -k 'not channel_local_water' --tb=short
```

The final snapshot passes **106 tests, with six channel cases deselected**.
The initial expanded snapshot passed 92; added profile-wide withdrawal controls
then exposed one failure among 98 tests. Binary64 working stores and five invalid
duration controls passed 103 tests. Three full-day grid controls complete the
final 106-test result. Excluding the channel group is explicit; those unresolved
cases are not passed or waived by this narrow review.

Generator staging independently covered five layouts × requested durations
1, 44, 45 and 400 years. Both management decks have the requested `sim_years`,
44-year rotation length and respectively 1, 1, 2 or 10 repetitions. Management
coverage therefore meets the requested period. Climate row counts match the
Gregorian date range; hill/channel climate bytes agree. Durations 0 and 401
raise before creating a destination. All 32 retained fixture hashes match.
These checks generated inputs under `/tmp/physical-water-narrow-qa-14htrqnf`;
they did not execute the 400-year model.

The ten WAT artifacts referenced by
`/workdir/watershed-physical-water-repair-20261021/hill-lane-results.json`
were read independently. Each OFE has exactly 16,071 ordered, unique dates from
1980-01-01 through 2023-12-31 and finite numeric fields. The six groundwater
receipts report unchanged WAT bytes; the allocation receipts report changed
hourly WAT and unchanged daily control. These artifacts support complete-period
execution and the claimed unaffected path, not complete physical closure.
Their recorded binary hashes must be refreshed or explicitly matched after any
subsequent source correction; they predate the second withdrawal pass reviewed
here.

## Findings and resolutions

1. **Resolved — management coverage capped long runs.**
   `tools/physical_water_case.py:21` now updates both management headers and
   repeats the retained homogeneous 44-year rotation enough times. The change
   is small and fits this bounded fixture. Continue to require actual generated
   output date/count checks so future template drift cannot pass as a full run.

2. **Resolved in the ordinary-tillage control — unused available liquid.**
   The initial allocation change could fail with demand -0.025 m, three layers
   containing 0.01 m each, and 0.3 m tillage: it reported -0.00111111 m unmet
   while 0.00611111 m liquid remained in earlier layers. A second bounded pass
   over remaining liquid now satisfies that demand and the -0.03 m exact-total
   control. Demand -0.030001 m correctly fails with zero liquid remaining.
   The six new profile-wide tests retain this causal boundary.

   Independently compiled nonuniform-state probes used `[0,0.01,0]`,
   `[0.01,0,0]`, `[0,0,0.01]` and `[0.001,0.005,0.02]`. Half-total and exact-total
   withdrawals succeeded with nonnegative stores and zero remainder; withdrawals
   exceeding the total by 0.0001 m failed. All 12 controls behaved as expected.

3. **Resolved — exact available-water withdrawal failed on roundoff.**
   With three 0.01 m layers, tillage depth 1.0 m and demand -0.03 m,
   `src/watbal_hourly.for:510` diagnoses an unmet -4.65661287e-10 m after all
   stores reached zero in the earlier single-precision redistribution. The final
   code checks the original represented inventory before mutation, uses binary64
   working stores through both bounded passes, handles exact inventory equality
   directly and casts back once. No residual tolerance was introduced. The
   formerly failing test now passes.

   Additional native probes at tillage depths 0.3 and 1.0 m passed -0.025 m,
   -0.03 m and zero inputs, while -0.030001 m failed. For each of the four
   nonuniform profiles above, the largest binary32 withdrawal at or below the
   binary64 sum of stored binary32 water succeeded; the next binary32 withdrawal
   above inventory failed. This tests the actual represented-water boundary,
   which need not equal a decimal arithmetic sum of input labels.

4. **Resolved — invalid flat-source duration was not diagnosed.**
   Independent calls through the actual CHRQIN harness with requested volume
   100,000 m³, supplied peak 1 m³/s and inactive component metadata produced:

   | Duration | Result |
   | --- | --- |
   | 0 s | Nonfinite rates and NaN integrated volume |
   | -1 s | Zero delivered volume, no diagnostic failure |
   | 90,000 s | About 96,000.004 m³ delivered on the 86,400-second grid |

   The final CHRQIN checks finite duration and `0 < T <= 86400` before division
   or reconstruction for positive rainfall source volume. Native tests reject
   zero, negative, 90,000-second, NaN and infinite durations with the diagnostic
   `CHRQIN_INVALID_DURATION`. The physical-day limit avoids rejecting 86,400
   seconds when a binary32 timestep × step count rounds slightly below a day.
   Full-day controls pass with 144, 161 and 277 steps. Additional valid controls
   at 0.01, 86,399.99 and 86,400 seconds conserve 100,000 m³ within the existing
   2e-6 relative source-summation bound.

## Quality assessment and residual debt

The groundwater fix remains localized, the allocation loops have explicit finite
bounds, and flat-cell reconstruction has readable volume/support semantics.
Separating negative binary64 allocation from positive legacy weighting adds
limited duplication with a clear numerical reason; a new allocation framework
would not improve this bounded repair. The intrinsic finite-value check adds no
external dependency.
Expanded tests now protect previous-day groundwater withdrawal, year boundaries,
new-simulation reset, small signed inputs, dry profiles, both source modes,
prior time-zero values and unchanged negligible-source thresholds. The former
contradictory substep test now asserts the repaired contract.

Non-blocking follow-ups: assert uniqueness of management replacement markers and
the borrowed channel-driver prefix; include year in unmet-water diagnostics for
long runs; retain a small nonuniform-layer regression if the allocation code
changes again. Shared test imports and comment-delimited native probes remain
acceptable for this bounded repair. Avoid expanding them into a general harness
framework. The CHRQIN subprocess helper still lacks the timeout now used by the
new allocation/channel probes; adding that same bound would prevent future test
hangs.

Frozen/saturated full-path behavior, complete groundwater mode/layout coverage,
source-to-solver temporal conversion, channel-local sinks, storage and downstream
transport remain broader acceptance work. Neither the source-cell tests nor the
WAT date audit establishes those claims. Primary correctness review, durable
contract/ADR updates for the represented-inventory and physical-day rules, and
current-binary replay receipts remain necessary for final acceptance.
