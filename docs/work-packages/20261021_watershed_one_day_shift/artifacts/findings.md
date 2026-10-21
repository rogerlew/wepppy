# One-day shift findings

## Confirmed date-label mechanism

The retained `chemotherapeutic-scope` run reproduces a one-day difference between
PASS/Julian-day labels and calendar-dated event output after the first non-leap
century. This is the already repaired calendar defect, not evidence by itself
that the channel holds surface runoff for a day.

A concrete original-output example:

| Output | Reported date | H1 runoff |
| --- | --- | --- |
| H1.pass.dat | Year 102, Julian 121 = May 1 | 39.742 mm |
| H1.ebe.dat | May 2, year 102 | 39.7 mm |
| ebe_pw0.txt | May 2, year 102 | Outlet volume 147,126 m3; not comparable to H1 depth |

The extra day requested in year 100 advances the climate stream one day relative
to subsequent PASS Julian labels. Hillslope and watershed EBE both use the
climate day/month; those two EBE dates agree in this example. Comparing a Julian
series with watershed EBE therefore looks like a one-day routing lag. Comparing
hillslope EBE directly with watershed EBE is a different claim that needs its own
run evidence.

The released-binary H1 replay has 309 surface-runoff events whose runoff values
match calendar-dated H1 EBE to its printed precision: 137 have equal dates and
172 have EBE one day later than the PASS label. No events are unmatched. The
first surface event after the boundary in this hill is the May 2/year-102 example.
The underlying daily-key divergence begins earlier, at the year-100 boundary.

## Actual reader and scheduler evidence

Corrected 400-year generated traces contain 146,097 daily reader loads. Every
loaded surface-runoff depth/volume matches the same date's decoded PASS values
(after conversion to the reader's float32 precision). On all 147 nonzero surface
runoff days, same-day values match; previous-day and next-day values match zero
times. Channel routing BEGIN/END markers share matching dates for all 103,556
invocations; days without that channel call are not asserted to have routed.

Both release source `7471bb5` and current `src/wshdrv` increment the daily index,
read climate, load hillslope PASS, route channels and call `sedout` before the
next daily iteration. Current locations: `wshdrv.f90:616,621,782,1122,1270`;
`sedout.f90:472,479` writes current climate day/month and simulation year.
There is no unconditional extra-day handoff demonstrated by these traces.
Outlet peaks can still differ from hillslope peaks because channel rainfall,
subsurface inflow, storage and losses change the signal; cross-correlation or
sparse row position alone cannot establish a date-selection bug.

## Limits and reproduction

Jackson's exact run and compared output family have been requested and are not
yet available. The confirmed reproduction above applies to the retained run;
it does not establish that his reported comparison used the same series.
No new production changes were made.

Run `./.venv/bin/python docs/work-packages/20261021_watershed_one_day_shift/artifacts/audit_shift.py`
from `/workdir/wepppy`. [Results](audit-results.json) retain counts and examples.
The 400-year trace is from `hbp400-observe`; decoded values are from `hbp400-final`
under `/workdir/wepp-gregorian-repair-20261021`. The corrected pair uses the same
hill input and binary; observability parity was established by the repair work.
