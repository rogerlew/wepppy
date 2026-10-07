# Experiment methods

## Intervention and comparison

Source: forest:/wc1/runs/wa/warming-championship/wepp/runs, titled Cedar Creek.
Each case uses the same corrected surface-return executable pair. Recompute all
864 hillslopes for 1980–2003 and then route all 371 channels. The 10 cm case is a
fresh corrected-build baseline, not the source run's previously saved output.

Only the fourth token of each eligible initial-condition roughness record changes:
0.10 m to 0.17 m or 0.60 m. Eligibility is determined from the source value, not
land-cover labels: 1,885 eligible records, 19 preserved exceptions. The existing
WEPPpy parser independently reads every case before execution. Other parameters,
including ridge height, ground cover, soils, climate, channel geometry, and
routing coefficients remain unchanged. Dynamic roughness and rill-width feedback
are not disabled. This is an initial-condition intervention, not a fixed roughness
throughout every timestep and not a burned/unburned comparison.

## Hydrograph observer and checks

All cases use chan.inp output mode 3 instead of 1, retaining the existing
600-second routing timestep and outlet element 1235 (channel 371). This requests
the complete modeled outlet series. A separate 10 cm watershed replay with the
original mode 1 tests byte parity of canonical watershed outputs. It reuses the
fresh baseline hillslope pass files, not source-run pass files.

Fresh outputs are mandatory; every process needs exit code zero and the WEPP
success marker. Logs, terminal records, input/output hashes, and mutation records
are retained. All 14 hillslopes without eligible records are negative controls:
their output hashes must match the baseline. Original source inputs and consumed
case inputs must retain their expected hashes after execution.

## Statistics and figures

Daily outlet volumes and peaks come from ebe_pw0.txt; its years are simulation
indices 1–24, corresponding to calendar years 1980–2003. Channel output already
uses calendar years. Validate dates, finite/nonnegative discharges, outlet IDs,
and the expected 144 samples per full-output day. The model permits one end-day
sample for negligible-flow days. Missing EBE rows are not silently filled with
zero: that report excludes volumes at or below 0.005 m³. Cross-check EBE volumes
against chanwb.out and peaks against chan.out within printed precision.

Figure 1 shows all daily peaks and cumulative reported runoff. Figure 2 selects
the three largest baseline peak days separated by more than seven days and shows
two days before through three days after each selected midnight. Selection uses
baseline only, avoiding treatment-driven selection. Figure 3 shows paired daily
peaks, empirical peak-ratio distributions for baseline peaks above 0.01 m³/s,
and annual runoff-volume departures. Ratio thresholds only affect that summary,
not any simulation or full-period volume total.

chan.out prints three significant digits, so peak timing can be ambiguous on
rounded plateaus. Report tied samples and first/last printed maximum rather than
claiming unwarranted precision. Discharge-weighted centroids and integrated flow
over the common five-day windows are comparative shape statistics, not inferred
travel times. They use printed 10-minute samples; authoritative daily volume
totals remain the EBE/channel water-balance values.

Also retain the full-period discrepancy between the right-rectangle integral of
the printed 600-second hydrograph samples and reported ledger volume. WEPP's
channel routine calculates chvol from inflow and storage, not by summing q1.
Do not normalize plotted flows to force agreement or describe agreement between
two ledger reports as proof of hydrograph volume conservation.

For a printed discharge q, bound its rounding error by half a unit in the third
significant digit. A conservative centroid rounding bound is
sum(error × abs(time − printed centroid)) / (sum(q) − sum(error)). Add the two
case bounds when judging a centroid difference. This addresses discharge printing
only, not the uncertainty between 10-minute routing samples. Figure 2 includes
discharge-difference panels; their small steps can reflect output quantization.

## Limits

This experiment does not validate physical plausibility of 17 or 60 cm roughness,
separate every feedback mechanism, estimate observed discharge accuracy, or
authorize changing defaults. It includes the complete supplied 24-year history,
including model initialization; no separate warm-up period is discarded. It
does not compare corrected versus unpatched executables. Production and the
original user run remain unchanged.
