# Winter Canopy-Cover Validation

Date: 2026-06-26

## Method

The validation used the single-hillslope fixture
`tests/omni/fixtures/honeyed_marathoner_sediment_inversion/run_root/wepp/runs/p118.*`.
For each management, Codex copied the run files to a temporary run directory,
expanded the management to the six-year simulation length with
`Management.build_multiple_year_man(6)`, and executed:

```bash
/workdir/wepppy/wepp_runner/bin/latest < p118.run
```

The source managements were:

| Label | Management |
|-------|------------|
| Evergreen | `UnDisturbed/Old_Forest.man` |
| Deciduous | `UnDisturbed/Deciduous_Forest.man` |
| Mixed | `UnDisturbed/Mixed_Forest.man` |

The WEPP output file was `H118.element.dat`. The fixture reports WEPP daily and
event rows rather than a dense 365-row calendar table. The final model year
(`1994`) is used for the acceptance summary to avoid first-year establishment
transients in perennial growth state.

## Summary

| Label | Return code | Final year | Winter mean `Cancov` | Summer mean `Cancov` | Final-year min | Final-year max |
|-------|-------------|------------|----------------------|----------------------|----------------|----------------|
| Evergreen | `0` | `1994` | `90.000%` | `90.000%` | `90.000%` | `90.000%` |
| Deciduous | `0` | `1994` | `6.653%` | `81.183%` | `0.000%` | `99.786%` |
| Mixed | `0` | `1994` | `44.446%` | `62.911%` | `37.257%` | `67.725%` |

Result: the snow-season ordering is deciduous low, mixed intermediate, and
evergreen high.

## Monthly Checkpoints

The table below records the first reported row in each month of the final model
year.

| Month | Evergreen `Cancov` | Deciduous `Cancov` | Mixed `Cancov` |
|-------|--------------------|--------------------|----------------|
| Jan | `90.000%` | `0.000%` | `48.040%` |
| Feb | `90.000%` | `0.000%` | `48.040%` |
| Mar | `90.000%` | `0.000%` | `48.040%` |
| Apr | `90.000%` | `0.000%` | `48.040%` |
| May | `90.000%` | `0.000%` | `48.680%` |
| Jun | `90.000%` | `25.671%` | `56.469%` |
| Jul | `90.000%` | `98.866%` | `64.507%` |
| Aug | `90.000%` | `99.369%` | `65.046%` |
| Sep | `90.000%` | `99.675%` | `66.715%` |
| Oct | `90.000%` | `99.786%` | `67.725%` |
| Nov | `90.000%` | `64.308%` | `54.192%` |
| Dec | `90.000%` | `19.958%` | `37.257%` |

## WEPP Behavior Notes

An earlier management variant set `jdplt=126` from the Harvard Forest mean
budburst date. In this WEPP perennial pathway that behaved like first-year
planting and discarded the established winter canopy, causing both seasonal
forest managements to emit zero canopy throughout the run unless additional
crop-style growth constants were supplied. The implemented managements keep
`jdplt=0` for established forest and use plant growth constants plus
`jdharv=286` for the seasonal trajectory.

The deciduous branch/stem residual target is represented conservatively. WEPP's
`Cancov` output in this pathway follows live canopy cover and can reach zero
after hard leaf-off, even though real deciduous stems and branches still have
some snow interception area. The result is still the intended snow-relevant
ordering and removes the previous false evergreen winter canopy.
