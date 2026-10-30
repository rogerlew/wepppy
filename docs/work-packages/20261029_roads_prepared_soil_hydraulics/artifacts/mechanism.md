# Horizon subdivision sensitivity

## Observed native result

All values below are common detailed-report export in kg/year, using the exact
`wepp_261026`, the site climate, sandy-loam specimen, unrutted gravel/high traffic,
and identical management/geometry. No parameter was fitted to these results.

| Soil representation | Export |
| --- | ---: |
| Original 7778 horizons | 109.099 |
| 9002 metadata with original unsplit horizons | 109.099 |
| 7778, redundant 200 mm boundary in all three OFEs | 4473.288 |
| 7778, redundant boundary in road only | 87.504 |
| 7778, redundant boundary in fill only | 11.940 |
| 7778, redundant boundary in buffer only | 2547.390 |

The subdivision copies the existing horizon's physical properties to both pieces.
The original sandy-loam profile has 100.8 mm/h conductivity from 0–150 mm and
9.72 mm/h from 150–400 mm. Splitting the latter at 200 mm does not intentionally
change this piecewise profile. Format conversion alone reproduces the original
result; the subdivision is a material numerical/model-input sensitivity.

## Source explanation

The binary release metadata pins native source commit
`b73e93b19a724d1991d341d38a18d11e742231bd`. At that exact revision,
`src/input.for`, lines 763–770 and 846–853, regrids horizons into 200 mm model
layers and assigns `ssc2(j) = ssc2(1)` while processing the first model layer.
This mutates the source-horizon conductivity array in place. If a source horizon
straddles 200 mm, its changed value persists when its remainder is processed in
deeper model layers. If a boundary is explicitly inserted at 200 mm, the deeper
piece has another array index and retains its original conductivity.

For this specimen, that path can carry 100.8 mm/h below 200 mm in the unsplit
input, while the explicitly split input retains 9.72 mm/h below 200 mm. This
source behavior explains why a nominally equivalent subdivision can change
infiltration/lateral drainage and sediment export. The source is bound to the
release; internal native conductivity arrays were not instrumented in this study.
The native outputs above, rather than source inspection alone, establish that
subdivision changes the executed result.

The owned `to_over9000` preparation inserts a 200 mm boundary even in the
format-only control. The new tests therefore reveal a preparation/native-model
interaction, not evidence that writing 9002 metadata itself causes the excess.
The reference WEPP2010 comparison uses legacy templates and does not establish
whether this native behavior existed in older generated-soil implementations.

## Disposition

Do not tune road erosion coefficients to compensate for this sensitivity, or
remove the 200 mm boundary merely because the unsplit representation exports
less sediment. The explicitly split input preserves the intended lower
conductivity below 200 mm; fixing native invariance need not lower predictions.
Retain it as a focused native input-parameterization issue, with an invariance
test comparing equivalent split/unsplit profiles and a review of the intended
0–200 mm conductivity treatment before changing native code. Repairing it,
rebuilding a binary, and validating downstream consumers are outside this
fixed-`wepp_261026` parameter study. No native source or binary was changed.

Exact source extracts and manifest are retained under the scratch root's
`native-source/`; all native case inputs/outputs and source snapshots are retained
in `subdivision-v1`. This finding does not establish physical field accuracy.

The implicated native reader is shared by non-road hillslopes. A future repair
should include equivalent split/unsplit profiles outside Roads, with contrasting
conductivities in a horizon crossing 200 mm, rather than introduce a Roads-only
compensation. This study establishes the Roads reproducer, not a census of all
affected projects.
