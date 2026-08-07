# Hill 106 Windows Replication: Highlights for Bill

Hi Bill, 

Thanks for the report. 


This details the 9002 soils and the additional parameters.
https://wepp.cloud/weppcloud/usersum/doc/usersum.input_file_specifications.soil_file_spec

The 14 parameters are read but aren’t used by the model, They were added for 
Anurag to support development. We'd need to create yet another soil version to 
remove them so I opted to leave them.

We (codex and Roger) ballpark replicated to your Hill 106 Windows results. The 
main takeaway is that weppcloud runs with `wepp_ui.txt` nor `pmetpara.txt`.

For the unburned hillslope, our ordinary Windows run gave `226 mm` runoff,
`365 mm` ET, and `21 mm` lateral flow. You reported `220`, `368`, and `22 mm`.
That is the closest match we found.

Adding `wepp_ui.txt` changed the answer dramatically. Lateral flow increased
from `21` to `120 mm/year`, while runoff and ET both decreased. With PMET also
enabled, lateral flow reached `145 mm/year`. This sidecar turns on the hourly
lateral-flow update used by WEPPcloud. Its effect is large enough that we are
confident it was not present for your Windows runs.

Adding `pmetpara.txt` by itself switched the run from legacy Penman ET to
Penman-Monteith ET. ET decreased from `365` to `336 mm/year`; runoff increased
from `226` to `250 mm/year`; and lateral flow increased slightly from `21` to
`25 mm/year`. This also moved the result away from your reported values, so
`pmetpara.txt` was probably absent too.

The two files interact. With both present, lower ET leaves more water available
for the hourly lateral-flow routine. We should therefore treat them as two
parts of the water balance, not as independent adjustments.

Earlier this week we investigated an anomoly identified by Scoot on the Stevens 
Canyon fire with peak-flow that traced down the pmetpara ET partitioning.

The largest reversal occurred in simulation year 34 on day 203, with
`58.7 mm` of rain. The undisturbed scenario produced the higher peak at all
three reaches we examined, even though the burned scenario would normally be
expected to respond more strongly.

The 30 days before that storm show what happened. These are area-weighted soil
evaporation totals:

| Reach | Burned (mm) | Undisturbed (mm) | Burned/undisturbed |
| ---: | ---: | ---: | ---: |
| 169 | 33.12 | 1.32 | 25.1× |
| 172 | 27.74 | 1.88 | 14.8× |
| 173 | 28.20 | 2.31 | 12.2× |

At reach 169, for example, the model removed `77.4 mm` as total ET from the
burned hillslopes during those 30 days, versus `38.0 mm` undisturbed. On the
storm day itself, burned-soil evaporation was another `4.50 mm`, compared with
only `0.05 mm` undisturbed. The burned profile entered the storm drier and
produced only `0.31 mm` of surface runoff, while the undisturbed profile
produced `22.17 mm`. The same pattern, though less extreme, appeared at reaches
172 and 173.

The concern is how the FAO-56 partition is constructed. In this implementation,
LAI divides nearly the same potential ET demand between plants and soil:

`plant share = 1 - exp(-0.45 × LAI)`

`soil share = exp(-0.45 × LAI)`

When fire reduces LAI, the plant share falls but the soil share rises by almost
the same amount. In other words, loss of living canopy mostly transfers demand
from transpiration to soil evaporation instead of reducing total ET. Lower
residue after fire exposes still more soil. For recently burned forest, this
can sustain implausibly large soil-water losses before a storm, dry the burned
profile relative to the forested profile, and reverse the expected runoff and
peak-flow response. Changing the PMET crop coefficient scales demand, but does
not independently fix this plant-versus-soil partition.

We also matched your burned result after adjusting the management file. Our
best 40-year ballpark gave:

|  | Our replay | Your result |
| --- | ---: | ---: |
| Runoff (mm/year) | 245 | 246 |
| ET (mm/year) | 345 | 346 |
| Lateral flow (mm/year) | 18.2 | 18 |
| Maximum lateral flow (mm/day) | 0.80 | 0.8 |

That match used a `0.5 m` root depth, initial canopy/interrill cover of
`0.70/0.90`, and maximum LAI of `2.25`. It is a fitted approximation, not proof
of your original settings.

One other useful finding: the `0.8 mm/day` burned maximum is not a fixed cap in
the code. It comes from the soil-water conditions in this run. With
`wepp_ui.txt` active, the same hillslope reached more than `10 mm/day`.
