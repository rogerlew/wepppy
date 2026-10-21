# M1 regression preflight review

Date: 2026-10-21. Reviewer: independent regression QA agent.
Scope: read-only review of the initial native probes, existing harnesses,
the repair ExecPlan and acceptance matrix. This is a test-design checkpoint,
not final correctness or scientific approval of a repair.

## Evidence and disposition

Native baseline: `6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb` in
`/workdir/wepp-forest-release-20261009`. Reviewed uncommitted
`tests/test_physical_water.py` SHA256:
`184e7fbba9088227953c202a813f2cf44b43794dfbc565c16a571b3b4f3ae497`.

The retained `/tmp/water-baseline-tests.log` reports 15 failures and six passes.
Independent rerun from the native checkout reproduced exactly that outcome in
1.76 seconds:

```bash
PATH=/usr/bin:/bin /workdir/wepppy/.venv/bin/python -m pytest -q tests/test_physical_water.py --tb=no
```

| Boundary | Observed baseline | Positive control |
| --- | --- | --- |
| WPA-04 initial groundwater | 60/40 returns 16 m³ and 20/30/50 returns 20 m³, expected 40 m³ | Single OFE returns 40 m³ |
| WPA-03 infiltration allocation | 0.000001, 0.00001 and 0.000011 m inputs leave unallocated water | 0.001 m input completes allocation |
| WPA-02 flat source | 900 m³ returns 600 m³; 1,000 m³ returns 600 or zero, for both start paths | Aligned 1,200 m³ returns 1,200 m³ for both paths |
| WPA-01 channel source assembly | Declared 100 or 120 m³ produces zero integrated input, with absent or zero-flow side hill | Zero local input produces zero rates in both layouts |

The four causal reproductions are credible: they execute production Fortran
blocks or routines, and failures have the expected signs and magnitudes.
The module correctly states that these are separate from full executable replay.
During this review, a self-contained complete-deck generator and proposed
scientific contract were added; see the follow-up below. Its short baseline
execution evidence remains pending here. The probes alone cannot satisfy M2/M3
acceptance.

## Findings requiring disposition

1. **Medium — contradictory substep expectations.**
   `tests/test_component_reconstruction.py:155` requires a 1,000 m³, 300-second
   flat source to produce zero rates. `tests/test_physical_water.py:87` requires
   the same source to conserve volume. Replace the old limitation assertion
   when WPA-02 is implemented, retaining a precise support/endpoint assertion
   from the reviewed contract. Do not skip either test to hide the conflict.

2. **Medium — complete execution coverage remains separate from the probes.**
   `tests/test_physical_water.py:33` and `:65` extract blocks from CONTIN and
   WATBAL_HOURLY; the channel fixture at `:101` returns before solver execution.
   These tests can pass while call ordering, daily reset, COMMON state, the
   hourly PURK/ET interaction, serialization or channel storage remains wrong.
   The new retained fixture and generator resolve the missing-input concern;
   complete paired hill/PASS/watershed receipts are still required. Keep the
   causal probes as fast, localized diagnostics.

3. **Medium — signed allocation and recurrence are not exercised.**
   At `tests/test_physical_water.py:63`, all infiltration inputs are positive,
   the soil is initially empty, and the profile always has three layers.
   An implementation that removes the positive cutoff but overdraws dry layers
   would pass. Add zero and signed values around the cutoff, one/multiple
   layers, available-water limits, and assertions on each layer as well as the
   total. Follow with saturated/frozen full-path cases. Groundwater tests at
   `:31` exercise only the first day, zero recharge and zero deep seepage:
   add nonzero recharge/deep seepage, zero initial storage, varying areas,
   successive hills, and year transitions with the retained withdrawal timing.

4. **Medium — channel and source totals do not constrain the repaired shape.**
   The channel cases at `:138` have neither top inflow nor side surface flow,
   and all local net exchanges are nonnegative. They cannot detect rescaling
   an unrelated hill hydrograph, duplicate baseflow, or an unavailable-water
   sink. Add separate source identities and positive/negative local exchange
   with known pulse timing, followed by actual solver/storage/downstream
   integration. The flat-source tests at `:87` use only inactive component
   metadata and the harness's hard-coded `mofapp=1`. Assert finite nonnegative
   rates, time-zero behavior, supported intervals, fractional terminal cells
   and the reviewed peak policy, including cell-average mode and mixed/return
   controls. A correct daily sum alone is insufficient.

5. **Medium — termination and execution identity need explicit gates.**
   New probe executions at `tests/test_physical_water.py:26` and `:141` have
   no timeout. A loop regression can hang the required test run indefinitely;
   use a bounded timeout as existing `test_channel_state.py:77` does. The reused
   compiler helper selects `gfortran` from PATH and skips when absent. Required
   acceptance must record `/usr/bin/gfortran`, reject unexpected skipped native
   probes, and record the full executable pair's hashes; a passing suite that
   silently omitted those probes is not repair evidence.

## Portable complete-deck generator follow-up

Reviewed `tools/physical_water_case.py` at SHA256
`fa19063a624d6f598753a613b963f0636d16de03e839d606d7b29f56bb41acf1`
and the new `tests/fixtures/physical_water/` parameter decks. All 32 manifest
entries match their files. The fixtures retain the five controlled layouts and
shared input bytes, and the generator uses only the standard library. No private
runtime donor or copied model outputs remain. This is an acceptable alternative
to deriving new templates from older committed fixtures.

I staged daily/hourly, two-year/400-year cases under
`/tmp/physical-water-review-hfnbg_w8` without running model executables there.
Both modes have the correct marker presence. Climate contains 731 dates for
1980–1981 and 146,097 dates for 1980–2379. The destination cannot overwrite an
existing directory. The native proposed scientific contract explicitly retains
the unresolved point/cell quadrature and storage boundary; QA agrees that source
cell sums cannot close that boundary.

**Medium — long requested periods silently exceed management coverage.**
`tools/physical_water_case.py:21` changes run-card duration, and `:26` changes
the climate header and generated rows, but neither `p1.man` nor `pw0.man` is
extended. Both retain one 44-year rotation. `src/contin.for:521` and
`src/wshdrv.for:463` calculate management coverage from rotation count × rotation
years, then cap the requested simulation to that coverage. A generated
`--years 400` deck therefore runs at most 44 years and can still report success.
Generate matching management coverage for both paths, or explicitly reject
unsupported durations until that capability exists. The replay gate must assert
the exact configured final year and all expected daily records. This finding
does not invalidate the proposed two-year M1 fixture.

The current helper is intentionally a staging tool. Remaining case/runner work
should provide the following, without turning it into a general deck framework:

1. Preserve its five homogeneous 100 m × 100 m layouts and add explicit unequal
   total areas for groundwater and tributaries. Assert template version/count
   markers before transforming them, including run-card offsets.
2. A Gregorian climate schedule generated with `datetime.date`, including
   dry spells, moderate/storm rain, cold snow accumulation and subsequent melt.
   The current two-year climate crosses a leap year; add the distinct complete
   400-year calendar lane after management coverage is repaired. Record daily
   input totals and date counts. Do not merely truncate a longer configured
   simulation.
3. Preserve explicit daily/hourly marker selection and ASCII PASS prompts.
   Extend the current top-only case to single-channel side placement, unequal
   tributaries, and a
   two-channel cascade with matching management/soil/channel counts.
4. Fresh hillslope execution followed by watershed execution using the same
   candidate pair. Record binary, template and generated-input hashes, compiler
   identity, case dimensions, prompts, environment, configured period, output
   inventory and subprocess logs. Fail on missing outputs, incomplete or
   duplicate dates, nonfinite values, missing success markers and timeouts.
5. Assert activation: each designated snow/recharge/lateral/surface case must
   actually produce that phenomenon. Validate first-day zero recharge before
   applying the exact 40 m³ initial-baseflow oracle. A dry or inactive case
   cannot substitute for a physically active acceptance row.
6. Independently parse local WAT and selected PASS volumes, then observe native
   channel input/output rates and initial/final state with candidate-off/on
   noninterference controls. Establish precision bounds before candidate
   comparison. Include deliberate duplicate/missing transfer, area, storage-sign
   and date corruptions in the ledger validation. Preserve unknown stores as
   unresolved, not zero.

## Non-blocking maintainability debt

Comment-delimited source extraction and the tab-sensitive WSHCHR insertion
anchor fail explicitly if their anchors disappear; this is preferable to silently
testing the wrong code. Still, trailing-space anchors and borrowing the prefix
of `tests/native/midnight_driver.for` via `split('      integer pcarry', 1)`
couple unrelated fixture maintenance. Assert that split marker is unique, and
consider a dedicated small channel-input driver if coverage expands. Avoid a
general harness framework solely for these four repairs.

The source test's single-precision tolerances are appropriately distinct from
watershed closure, but add their derivation to the test comments and distinguish
arithmetic-zero residual expectations from floating-point comparisons. No
production or test source was changed by this review. Final QA remains pending
implementation, complete replay evidence and primary correctness review.
