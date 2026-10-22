# Channel-plane initialization: scientific causal review

Independent review, 2026-10-21. **Support the two-field initialization immediately
after WSHCQI and before optional WSHIRS, conditional on portable regressions,
native gates and representative replay acceptance.** No canonical production
source was edited by this reviewer. This approval covers scratch-field ownership,
not the unresolved signed MC acceptance/clipping contract.

## Confirmed defects and bounded correction

`runoff` and `chnrun` serve both channel-plane and watershed-element indexes.
After C1 uses plane 1/element 2, WSHDRV copies its values into slot 2. C2 then
uses that same slot as plane 2. The once-daily reset does not protect C2 against
this later upstream write.

WSHCQI consumes upstream `tmpvol`/`tmpsbv` and supplies separate runon fields.
Neither scratch field contains a legitimate current-channel result immediately
after WSHCQI. Initialize both there:

```fortran
                runoff(iplane) = 0.0
                chnrun(iplane) = 0.0
```

This preserves the existing WSHIRS/WATBAL event decision. WSHIRS already clears
runoff when called, but dry days can bypass it. WSHIRS assigns `chnrun` only
when local rainfall excess is positive; even a wet day can otherwise retain an
upstream value. WATBAL may then produce genuine surface return and enable the
existing routing gate, which exposes the false local input.

The source chain and first read-only writer/read proof are recorded in
[actual-soil-coupling-control-review.md](actual-soil-coupling-control-review.md).
Relevant pre-repair native lines are `wshdrv.for:926` (boundary), `:1004`
(element copy), `wshirs.for:172`/`:266` (conditional producers), and
`watbal_hourly.for:352`/`:359` (infiltration consumes the inherited depth).
Upstream element runoff reports are restored from `tmprof` at
`wshdrv.for:1201`; downstream admission uses the retained volume fields.

## Causal experiment

External evidence root:
`/workdir/watershed-physical-water-repair-20261021/channel-plane-init-review-v1/`.

Four isolated variants use the same source, inputs and observation hooks:
baseline, runoff reset only, `chnrun` reset only, and both resets. Each variant
runs twelve full two-year cases: the eight existing two-channel early/late,
wet/dry, daily/hourly soil controls, plus four three-channel wet cases. The
three-channel cases use standard soil or change only C2's soil7778 layer
conductivity input from 0.5 to 100 mm/h. This deliberate test input causes the
native wet/no-local-excess branch; it is not a production parameter change.

Each observed run has a corresponding observer-off run retaining the exact
100 m³ receiving-boundary hook. All **96 runs completed** and all **1,800 native
file pairs match byte for byte**. Every channel has 731 exact finite daily rows.
Across variants, all twelve scenarios retain the entire upstream C1 hydrograph
and channel-balance rows exactly. The eight baseline two-channel cases reproduce
the prior control's native outputs exactly. The common hillslope pass artifacts
are reused unchanged from those completed controls.

MC4, 600-second steps, lateral interpretation mode 1, soil formulas, the event
gate and recurrence remain unchanged. Complete routing arrays retain MCFAST
copied intervals. The receipts keep source quadrature, raw/accepted export,
clipping, MC increments, start/end coordinates and transition terms alongside
pre/post soil, Dp, ET, lateral flow, surface return and the transmission request.

## Independent effects of the two resets

The hourly dry-day 100 m³ control isolates the runoff defect. Its receiving
pre-soil depth is 0.00135309249 m in baseline and `chnrun`-only runs, and zero
with the runoff reset. WSHIRS remains skipped. Because the repair operates
throughout the two-year run, corrected earlier soil history also affects the
selected event; its changes must not be attributed solely to the current-day
1.548344 m³ inherited depth.

| Hourly dry control | Baseline / `chnrun` only | Runoff only / both |
| --- | ---: | ---: |
| Pre-soil liquid inventory depth, m | 0.162981350 | 0.189017838 |
| Fin allocation request, m³ | 98.453385 | 100.001726 |
| Forwarded soil runoff, m³ | 61.158100 | 90.951569 |
| Transmission request, m³ | 38.841900 | 9.048431 |
| Raw-to-export clipping, m³ | 39.231588 | 11.423601 |

The standard daily control has no inherited dry depth in the observed window
and remains unchanged. The repair is not justified by assuming every day or
every soil mode triggers the defect.

The high-conductivity wet control isolates `chnrun`. Native C2 conductivity is
1.19209953e−5 m/s, above rainfall intensity 5.20833328e−6 m/s. Actual WSHIRS runs,
produces no local rainfall excess and leaves runoff zero. Actual WATBAL produces
surface return and sets `norun=1`. Without the `chnrun` reset, WSHDRV then
publishes upstream rainfall runoff as if C2 generated it.

| C2 wet/no-local-excess case | False local input without `chnrun` reset, m³ | Local input with reset, m³ | Baseline → `chnrun`-only transmission request, m³ |
| --- | ---: | ---: | ---: |
| Daily soil | 26.909861 | 0 | 35.569366 → 8.659508 |
| Hourly soil | 26.986202 | 0 | 37.891640 → 10.905434 |

For each runoff-reset setting, changing only `chnrun` leaves C2's measured soil
inventories, fin request, Dp, evaporation, surface return and forwarded runoff
exactly unchanged. Its false local input and inflated transmission request
cancel algebraically in net lateral forcing, so raw routing changes only by
floating-point rounding. This is a real producer/reporting defect even where
its two incorrect gross terms cancel. Both resets are needed for the complete
scratch-field correction.

The standard three-channel wet controls retain positive genuine C2 local
runoff in every variant. In the hourly repaired run it is 26.986202 m³, versus
23.198629 m³ in the baseline because previous soil history is corrected;
initialization does not erase the native WSHIRS-produced value.

## Acceptance boundary and remaining risk

The causal controls support this bounded implementation fix without introducing
a hydrologic parameter or changing MC storage authority. Portable regressions
must distinguish the unaffected daily dry control from the positive hourly
witness, preserve actual soil production, and cover wet zero/local excess and
three-channel propagation. Native gates and representative replays remain the
promotion gate owned by the parent execution.

Independent review of `tests/test_channel_plane_initialization.py` and
`tests/native/channel_plane_trace.for` found no blocking issue in the final
seven-test design. It builds all four native variants from repository sources,
generates three-channel decks without external paths, verifies complete
731-day outputs, and records strictly ordered watershed-only fin observations.
The hourly test proves the upstream writer/receiving reader equality and the
corresponding infiltration consequence. The daily dry test is correctly an
unaffected control. Wet tests observe the actual local-volume publication and
preserve genuine local runoff. The boundary hook preserves time zero and
restores C1 before the next channel. Test execution evidence is retained by the
QA reviewer; this source review does not substitute for its passing result.

Reviewed test/helper SHA-256 values respectively:
`10644f6ee1105e14db3a6524fe90962ac2d2434105b15a2b3604113d4a5181d9` and
`f96e2607c6e85945c1124cc186753a6d8364b71f6c684732a703bc50a87881c8`.

Signed MC acceptance is still open: the corrected hourly dry control retains
11.423601 m³ clipping, while the daily control still retains 38.351856 m³. No
loss cancellation, acceptance cap, residual storage or hydrograph rescheduling
was introduced. Complete geometric or physical budget closure is not claimed.
The isolated matrix does not directly cover MC5, lateral mode 2, impoundments
or every legacy routing mode; existing broader gates and separate coupling work
remain necessary.
