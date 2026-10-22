# Channel-plane initialization: secondary QA

Date: 2026-10-21. This reviewer inspected the two-field WSHDRV repair without
editing production source, then authored the portable integration tests below.
The scientific reviewer independently reviewed the final test files and found
no blocking findings. The source review follows
[channel-plane-initialization-scientific-review.md](channel-plane-initialization-scientific-review.md).

## Disposition

The two resets are a small, coherent correction to scratch-field ownership.
They belong immediately after WSHCQI and before optional WSHIRS: upstream
volumes have already been admitted through separate fields, while neither
scratch field contains a valid result for the current channel. This leaves the
event decision and all native soil and routing calculations in place.

**The narrow source correction and its portable integration coverage pass this
review.** The targeted run passed all seven tests in 115.93 seconds. The parent
reports the full native gate passed with 520 tests and two existing warnings in
618.33 seconds, reaching year 100/day 365/channel 31; all 29 representative
replays, 12 watchlist tests and both smoke/loader profiles also passed. These
broader gates were run by the parent, not repeated by this reviewer.

This review covers the narrow initialization defect. Signed MC acceptance and
clipping remain open, and the full physical-water package is not complete.

## Portable causal coverage

Native files:

- `tests/test_channel_plane_initialization.py`
- `tests/native/channel_plane_trace.for`

The tests generate a full 1980–1981 hillslope and three-channel cascade from
committed synthetic fixtures and `tools/physical_water_case.py`. They require
no private run directory or retained external executable. One fresh native
watershed build is followed by three WSHDRV-only relinks: both resets, neither
reset, runoff reset only and local-runoff reset only. Checked source anchors
make the bounded observation and ablation changes explicit; the actual
WSHCQI, WSHIRS, daily/hourly WATBAL and WSHCHR routines execute.

Four variants run for each of two soil modes and two receiving-soil inputs,
giving sixteen full two-year cases. The second soil input changes only C2's
conductivity to exercise wet WSHIRS with no local rainfall excess. A single
100 m³ upstream boundary is consistent between the q1 integral and tmpvol,
preserves the inherited q0 endpoint, and is restored before subsequent channel
processing. No runoff, branch flag, infiltration result or loss is prescribed.

The seven assertions cover distinct causal consequences:

- On the hourly dry witness day, the upstream element write exactly equals the
  next channel's inherited plane depth. The daily dry witness is correctly
  treated as an unaffected zero-depth control. Corrected channels have zero
  pre-soil runoff whenever the observed optional WSHIRS call is absent.
- The actual 24 requested hourly FIN values sum to runon depth minus pre-soil
  runoff plus subsurface runon. The runoff reset restores approximately
  1.548 m³ of requested infiltration on this witness; the independent local
  reset leaves that consequence unchanged. This tests the local request, not
  an assumed final soil-storage gain or complete soil budget.
- Wet, high-conductivity C2 executes WSHIRS with intensity below conductivity,
  produces no local rainfall excess, and then produces genuine surface return
  in WATBAL. Only the local-runoff reset removes the falsely published
  approximately 26.91/26.99 m³ in actual chnvol.
- Standard-soil C2 retains native positive local runoff and publishes its
  volume. Every variant preserves the entire upstream C1 daily balance for
  both soil inputs, and all three channels complete the full period.

## Artifact and harness checks

Success messages alone do not establish completion. Each case must contain
exactly 731 finite hillslope water-balance rows and 731 finite, ordered daily
rows for each of all three channels in both channel output files. The keys
cover the leap year and end at 1981/day 365.

Read-only observations are restricted to watershed soil calculations. Their
five-day window must have exact ordered year/day/element/plane/hour keys: 15
daily records or 360 hourly records. Stage observations reject duplicate keys,
unexpected stages, malformed records, wrong channel identities and nonfinite
values. The pulse quadrature is checked independently of the prescribed scalar
volume. The scientific review's observer-off siblings supply the separate
native-output parity evidence for these diagnostic hooks.

Retained evidence is under
`/workdir/watershed-physical-water-repair-20261021/channel-plane-initialization-qa-v1/`:
`pytest.log`, build logs, reviewed source snapshots, the three complete daily
output files and diagnostic records for all sixteen cases, `receipt.json` and
`manifest.json`. The manifest pins 172 files. Receipt SHA256:
`5e6bef3729f37b9a8b6858fbcb26e027ca3720b15ee3505b53027631341c9aee`.
Python compilation, fixed-form line widths and scoped whitespace checks passed.

## Quality risk and residual debt

No production abstraction or parameter was introduced. The test's deck edits
and source anchors intentionally target a small known fixture shape and fail
explicitly if it changes. The module caches a single full build and isolates
all later relinks and runs in temporary directories. This integration coverage
has a higher runtime than routine-level controls, justified by the defect's
dependence on real upstream writes, optional WSHIRS and actual soil behavior.

The portable controls use MC4, lateral interpretation mode 1, a single cascade
topology and two selected soil inputs. They do not independently cover MC5,
impoundments or every legacy routing mode. Broader gates supply regression
coverage, not proof of every scientific coupling contract. Existing signed
exchange clipping remains a separate acceptance item; the corrected scientific
hourly dry control still reports 11.423601 m³ of clipping.
