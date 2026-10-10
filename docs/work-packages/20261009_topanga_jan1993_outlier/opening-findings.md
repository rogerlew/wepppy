# Opening Findings: January 18, 1993

2026-10-10 UTC. Classification: **unexplained event outlier**, not an established
defect. This is a read-only first pass; no simulations, source edits or input
changes were made.

## Evidence Captured

Both live watershed EBE hashes match the frozen pre-investigation snapshots.
The new `artifacts/opening-window/` retains January 10-24, 1993 extracts for
both scenarios: hillslope PASS, watershed-consumed PASS, hillslope water state
and erosion, watershed timing, channel water outputs, totalwatsed and outlet
event/peak outputs. Hillslope metadata is retained in full. Each extract is
read back, compared with its selected source records, and recorded with source
and extract hashes and schema units.

There are 284 hillslopes in each daily PASS population. Over the captured
window, the two PASS products agree exactly on hillslope ID, date, surface
volume, published peak, duration, time of concentration, alpha and lateral
volume. This reduces concern about a mismatch between those products; it does
not independently establish the correctness of their common source calculation.

## January 18 Comparison

| Quantity | Burned | Undisturbed |
| --- | ---: | ---: |
| Hillslope surface volume, m3 | 68,202.43 | 44,548.56 |
| Hillslope lateral volume, m3 | 143,040.24 | 173,633.11 |
| Sum of individual published hillslope peaks, m3/s | 36.4968 | 10.6785 |
| Largest individual hillslope peak, m3/s | 1.06710 (WEPP 106) | 0.80955 (WEPP 105) |
| Hillslopes with PASS EVENT records | 231 | 136 |
| Published source duration for those EVENT records, s | 1,440 | 1,440 |
| Outlet daily volume, m3 | 213,282.16 | 218,608.19 |
| Outlet peak, m3/s | 76.03957 | 707.63910 |
| Channel-output peak time, s | 1,800 | 1,200 |

The outlier is not accompanied by a larger sum or maximum of the published
undisturbed hillslope peak scalars. The undisturbed case instead has less
surface volume and more lateral volume. This makes channel-source reconstruction
and routing timing useful next boundaries to inspect, rather than immediately
targeting a single hillslope's reported peak as the explanation.

These sums are not simultaneous inlet discharges or a proven upper bound on
the implemented routed response. They exclude channel-generated contributions
and do not describe antecedent storage release or source reconstruction.
The PASS summary columns also do not expose the separate component operands
used by the revised source handling. Do not infer a numerical failure from the
outlet-to-source-scalar ratio alone.

## Antecedent Context

The preceding two days are wet in both scenarios. Reported outlet precipitation
is 47.2 and 59.7 mm on January 16 and 17, followed by 15.7 mm on January 18.
The totalwatsed area-weighted precipitation values differ slightly from those
outlet report values; these are different spatial summaries, not substituted
forcing series. Both scenarios use the same precipitation sequence.

Totalwatsed reports zero aggregate snow water and equal precipitation and
rain-plus-melt for January 16-20. There is no substantial aggregate snowmelt
signal in these outputs. Reported aggregate soil water on January 18 is
254.74 mm burned and 258.62 mm undisturbed, following wet preceding states.
The undisturbed lateral-flow depth is 17.86 mm versus 14.72 mm burned.
These support considering antecedent state and pathway differences, but do
not by themselves explain the outlet peak magnitude or its timing.

The undisturbed scalar source-peak sum falls from 94.7081 m3/s on January 17
to 10.6785 m3/s on January 18, while outlet peaks rise from 71.88370 to
707.63910 m3/s. On January 19 the reported hillslope surface volume is zero
and outlet peak falls to 3.54204 m3/s. This temporal contrast is retained
without assuming either a hydrological explanation or a model defect.

## What the Existing Output Does Not Show

Both `chan.inp` files select mode 1 (peak-only output), a configured 600-second
routing interval and outlet Topaz 412. Therefore the retained `chan.out`
product is one daily maximum and its time, not the full outlet hydrograph.
Daily ledgers and scalar maxima cannot determine peak width, intra-day source
coincidence, or the sequence of upstream contributions.

Static source read at clean Forest revision
`692c225e672844c71114bbdda851625616ebbba9` shows:

- `src/wshchr.for:621`: `qchpk` is selected from the routed `q1` array.
- `src/wshchr.for:675`: mode 1 prints `dtchr * itpk` and `qchpk`.
- `src/wshchr.for:684`: modes 3 and above print the routed time-step series.
- `src/wshchr.for:711`: the same `qchpk` is assigned to `peakot`.
- `src/chrqin.for:91`: component-aware source handling separates rainfall and
  returned-water contributions before reconstructing time-step source rates.

Consequently, matching EBE and channel peak outputs is not two independent
physical estimates. The time field locates a routing-array sample in the
daily routing frame, not a calculated absolute mixed-flow storm onset. Neither
that scalar time nor volume/peak alone establishes a physical hydrograph.

## Competing Explanations

| Possibility | What supports considering it | What is missing |
| --- | --- | --- |
| Antecedent water and source timing concentrate flow | Wet preceding days; more undisturbed lateral volume | Time-resolved sources, storage changes and outlet shape |
| Source reconstruction produces a concentrated inlet | Outlet response differs markedly from published source peak scalars; component handling exists | Actual reconstructed component/inlet arrays on this date |
| Channel routing or discretization amplifies a short pulse | Large routed maximum at an early routing sample | Full routed series and upstream progression; no failure established |
| Reporting or input identity mismatch | Always worth checking in forked scenarios | Current EBE identities and PASS product agreement do not support a simple stale-table/PASS-copy mismatch; fuller operand provenance remains relevant |

These possibilities may interact. None has been adjudicated as the cause.
The purpose is not to force burned flow above undisturbed on every day, nor
to eliminate all legacy accounting differences before understanding this event.

## Next Bounded Decision

The smallest useful additional observation is the existing full time-step
channel output for the outlet, with the burned counterpart as a control.
An isolated same-build replay could change only the existing output selector
from peak-only to full-series, keeping the 600-second interval, physical
parameters and antecedent simulation history unchanged. It would test whether
the reported maximum is a narrow isolated sample, a sustained pulse, or part
of a coherent rising/receding sequence. It would not alone prove the cause.

Before such a replay, stage a complete immutable same-build input/PASS set,
verify the output-selector path is observer-neutral, and state the run/storage
cost. Do not replay January 18 from a cold initial state or swap PASS files
between binaries. If the full input set is unavailable, report that limitation.
No replay is launched in this opening phase. Source instrumentation, upstream
channel expansion, timestep perturbation and behavior changes remain separate
decisions justified only by what the first observation shows.
