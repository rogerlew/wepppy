# Native output semantics for the Roads OFE experiment

Audited source: WEPP commit `b73e93b19a724d1991d341d38a18d11e742231bd`,
matching the provenance of `wepp_261026`. Extracted source and SHA-256 identities
are retained under `/wc1/runs/ro/roads-ofe-budget-20261029-v2/native-source/`
and `declaration.json`. These interpretations apply to this binary and the
three noncontoured Roads management files; each declares zero contour scenarios.
They are not a new universal WEPP output contract.

## Sediment

`sedout.for:482–493` writes ELEMENT `SedLeave = ofelod(iplane)` in kg/m width.
`sloss.for:165–224` calculates that load at the last spatial point of each OFE.
Multiply by profile width, sum observed days, divide by 16 years. Successive
boundary differences give signed net exchange. Sum positive and negative daily
differences separately to expose reversals. Neither quantity is gross detachment
or gross deposition, and neither tracks the origin of individual particles.

ELEMENT is sparse event/checkpoint output. `contin.for:1344–1398` also emits
checkpoint records on days 1 and 15. Require one record per OFE on each observed
date, valid climate dates, finite loads, and all three OFEs. Do not demand a full
daily ELEMENT calendar. The Rust reader receives the explicit climate start year.

`sedout.for:532` and `contin.for:1841` print loads to 0.001 kg/m. The independent
annual report prints annual export to 0.001 kg/m. The conservative reconciliation
bound in kg/year is `(event_dates * 0.0005 / 16 + 0.0005) * width`, plus 1e-6
relative native accumulation allowance. Record whether each run meets the bound;
never silently force the terminal load to equal the annual report.

EBE `Sed.Del` prints to 0.1 kg/m (`sedout.for:534–535`). Compare event values with
a 0.0505 kg/m combined rounding bound plus 1e-6 relative allowance. Require unique
EBE dates present in ELEMENT and coverage of every nonzero terminal ELEMENT day.
Retain every beyond-precision difference, including date and both values.

**The native quantities are not unconditionally identical.**
`sloss.for:268–270` only assigns the terminal load to `avsole` when `qout > 0`
(and there are no contours); otherwise it uses side export. Annual accumulators
receive `avsole` at lines 275–277. `sedout.for:349` can subsequently zero `avsole`
when `iroute == 0`; EBE writes that variable at lines 440–443, while ELEMENT
writes `ofelod` independently. Thus an EBE discrepancy is an observable diagnostic,
not permission to relax precision or rewrite native values. These branches show
possible mechanisms; no internal trace was added to prove which branch fired on
each discrepant event. Report unresolved mismatches and bound the interpretation.

PASS gross detachment/deposition and discharge-times-concentration export remain
separate diagnostics. Cross-binary similarity always uses the same annual report
metric, not PASS export substituted for one side of the comparison.

## Water

Use WAT, not ELEMENT Runoff: the two ELEMENT writer branches use different runoff
normalizations. The canonical context is
[the hillslope water aggregation contract](../../../schemas/hillslope-water-aggregation-contract.md).

For this exact release, `watbal.for:1092–1105` writes cumulative runoff depth
`Q = runoff * efflen / totlen * 1000`, upstream local depth, local lateral depth,
and local `Area = slplen * fwidth`. For constant profile width:

- Surface boundary volume is `Q * cumulative_area / 1000` m³/day.
- Upstream surface inflow is `UpStrmQ * local_area / 1000`.
- Lateral outflow is `latqcc * local_area / 1000`.
- Upstream lateral inflow is `SubRIn * local_area / 1000`.

`watbal.for:359–367` converts upstream flows into downstream local depth. Validate
surface and lateral transfers independently at each boundary. Use actual emitted
slope lengths and width, checking WAT's rounded areas within 0.0051 m².
Surface transfer tolerance is 5e-6 relative plus 1e-7 m³ for native single-precision
length/flux arithmetic and e15.7 printing. Lateral terms print to 0.01 mm: tolerance
is `0.005 * (upstream_area + local_area) / 1000 + 1e-7` m³. Keep actual maximum
residuals. All three OFEs must cover the complete 5,844-day climate calendar.

Aggregate rain/melt, precipitation, ET, deep percolation and boundary fluxes by
local area as appropriate. The apparent soil balance uses RM plus surface/lateral
inflow, less surface/lateral outflow, ET, deep percolation, tile drainage and change
in `SoilWaterTotal`. Exclude the first day because its initial stock is not reported.
This diagnostic is **not complete physical water closure**: canopy/interception
storage and all model accounting terms have not been established. Do not declare
mass conservation from a small residual alone. `QOFE` is not used.

## Treatment controls

Hydraulic factors toggle road, fill and buffer independently. Only `ksatadj`,
`ksatfac`, `ksatrec` and horizon `ksat` may differ. Verify all other parsed soil
fields equal, the 200 mm break present, and every horizon below 200 mm unchanged.
Each OFE must match its corresponding all-off/all-on endpoint, preventing treatment
leakage into another OFE. All eight cases retain bare/bare/forest erosion parameters
and soil landuse identities. `000` is not the full format-only anchor.
