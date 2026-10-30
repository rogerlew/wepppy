# Roads drainage validation results

Completed native execution: 1,920 paired-matrix runs plus 192 runtime-bridge runs.
**The proposed conductivity change does not generalize well enough to adopt.**
In the simplified matrix it fixes 17 factor-ten failures but introduces 13, changing
coverage from 820/905 to 824/905. The conservative policy falls to 814/905. In the
UI-mode bridge, current and source treatments both pass 61/71 positive references;
with the site's shared settings both pass 14/16. No production candidate is accepted.

## Principal finding: runtime mode is part of parameterization

The earlier simplified studies and this frozen broad matrix omit `wepp_ui.txt`.
The actual Roads workspace copies it from baseline projects; both source projects
and the canonical Roads fixture contain it. Its presence activates a different
water-balance path. Therefore improvements in the simplified matrix cannot be
presented as production-mode validation. The bridge explicitly activates and audits
that mode, then tests the site shared-file bundle. See
[physical justification](physical-justification.md) for equations, source audit,
soil classes and primary literature.

## Frozen design and acceptance

Eight labels (seven distinct material profiles), five climates, four designs,
two surfaces and three traffic levels give 960 paired profiles. Each uses 16 complete
years, exact `wepp_261026`, bare/bare/forest role preparation and normalized 200 mm
boundaries. Only buffer lower-boundary conductivity changes. The source alternative
uses source restriction conductivity without /1000 scaling, or deepest emitted Ksat
where no restriction was identified. The policy view retains current lithic values
and selects the source alternative otherwise. Policy rows reuse runs.

Three newly tested profiles are lithic 1856573, mineral-horizon 53949 and unrestricted
1718494. Old loam/holdout have identical horizon/restriction properties and are not
independent validation samples. All specimens come from two existing projects;
climate swaps are stress tests, not geographic field validation.

A positive-reference export passes at 0.1–10× WEPP2010. Every failure and exact-zero
reference is retained; no epsilon denominator or fitted acceptance threshold.
Physical acceptance requires evidence beyond compatibility. Neither source nor
policy satisfies the complete acceptance contract.

## Broad matrix: common-report sediment export

| Treatment | Within factor ten | Above 10× | Below 0.1× | Zero matches/references | Median ratio |
| --- | --- | --- | --- | --- | --- |
| current | 820/905 | 46 | 39 | 24/55 | 1.13 |
| source | 824/905 | 29 | 52 | 24/55 | 0.985 |
| policy | 814/905 | 39 | 52 | 24/55 | 1.05 |

Reference denominators are positive common native report exports. Reused legacy
references are rehashed and matched by climate, texture, design, surface and traffic.
Modern-binary legacy-soil reference: 898/905 positive comparisons within factor ten.

| Soil label | Current | Source | Policy | Source ratio range |
| --- | --- | --- | --- | --- |
| sand | 99/113 | 107/113 | 99/113 | 0.384–336 |
| loam | 98/114 | 92/114 | 92/114 | 0–1.17 |
| silt | 101/108 | 100/108 | 100/108 | 0–2.14 |
| clay | 107/114 | 111/114 | 111/114 | 0.47–25.4 |
| holdout | 98/114 | 92/114 | 92/114 | 0–1.17 |
| new_lithic | 102/114 | 104/114 | 102/114 | 0.553–53.1 |
| new_lowk | 104/114 | 107/114 | 107/114 | 0.433–37.2 |
| new_open | 111/114 | 111/114 | 111/114 | 0.339–17.3 |

| Climate | Current | Source | Policy |
| --- | --- | --- | --- |
| birmingham | 189/192 | 189/192 | 189/192 |
| denver | 142/144 | 142/144 | 142/144 |
| flagstaff | 149/185 | 149/185 | 149/185 |
| charleston | 168/192 | 168/192 | 167/192 |
| site | 172/192 | 176/192 | 167/192 |

Removing the duplicate `holdout` leaves 840 profile comparisons:
current 722/791,
source 732/791,
policy 722/791 within factor ten.

Transitions from current to source: `{'True->True': 807, 'False->False': 68, 'None->None': 55, 'False->True': 17, 'True->False': 13}`.
Transitions from current to policy: `{'True->True': 807, 'False->False': 78, 'None->None': 55, 'True->False': 13, 'False->True': 7}`.
`True` denotes within factor ten, `False` a positive-reference failure, and `None`
an exact-zero reference. Complete strata and all failures are retained in
[summary](artifacts/summary.json) and [comparison CSV](artifacts/comparisons.csv).

### Largest source-scenario departures

| Profile | Source kg/yr | WEPP2010 kg/yr | Ratio |
| --- | --- | --- | --- |
| flagstaff-loam-outunrut-gravel-high | 0.000 | 0.560 | 0 |
| flagstaff-loam-outunrut-gravel-low | 0.000 | 0.560 | 0 |
| flagstaff-loam-outunrut-gravel-none | 0.000 | 0.517 | 0 |
| flagstaff-loam-outunrut-paved-high | 0.000 | 1.121 | 0 |
| flagstaff-loam-outunrut-paved-low | 0.000 | 1.121 | 0 |
| flagstaff-loam-outunrut-paved-none | 0.000 | 0.517 | 0 |
| flagstaff-holdout-outunrut-gravel-high | 0.000 | 0.560 | 0 |
| flagstaff-holdout-outunrut-gravel-low | 0.000 | 0.560 | 0 |
| flagstaff-holdout-outunrut-gravel-none | 0.000 | 0.517 | 0 |
| flagstaff-holdout-outunrut-paved-high | 0.000 | 1.121 | 0 |
| flagstaff-holdout-outunrut-paved-low | 0.000 | 1.121 | 0 |
| flagstaff-holdout-outunrut-paved-none | 0.000 | 0.517 | 0 |

## Runtime bridge

Before any bridge outcomes, freeze gravel/high traffic and both rutted/unrutted
geometries for all eight soil labels and five climates: 160 runs adding only
`wepp_ui.txt`. Another 32 site-climate runs copy all seven canonical Roads shared
files unchanged. Actual input hashes, mode banners and matching baseline soils are
verified. This is a controlled runtime bridge, not a full-project replay or a
revalidation of every paved/traffic combination under production settings.

| Runtime | Treatment | Within factor ten | Above 10× | Below 0.1× | Report/ELEMENT reconciled |
| --- | --- | --- | --- | --- | --- |
| ui-only | current | 61/71 | 4 | 6 | 77/80 |
| ui-only | source | 61/71 | 4 | 6 | 79/80 |
| ui-only | policy | 61/71 | 4 | 6 | 79/80 |
| site-shared | current | 14/16 | 0 | 2 | 13/16 |
| site-shared | source | 14/16 | 0 | 2 | 15/16 |
| site-shared | policy | 14/16 | 0 | 2 | 15/16 |

For site sand, unrutted gravel/high, current-drainage export changes from
897.41 kg/year without UI to 147.98 kg/year with UI alone, and 165.27 kg/year with
the shared site settings. Under the shared settings, source drainage gives
53.02 kg/year. Current-drainage buffer lateral outflow rises from approximately
607 m³/year without UI to 2,736 m³/year with UI alone; its deep percolation actually
falls from 30.5 to 15.1 m³/year. The mode effect therefore cannot be described as
simply increasing deep drainage. Source drainage then shifts much of the UI-mode
lateral flow to deep percolation.

The site bundle includes snow, evaporation and groundwater settings, so its contrast
with UI-only is not attributable solely to deep percolation. Other climates do not
receive transplanted site-specific settings. Complete rows:
[runtime comparisons](artifacts/runtime-comparisons.csv). Exact matches of all
common consumed-input hashes also permit comparing these outputs to the remaining
paved/gravel and high/low labels that share those bytes. These derived comparisons
are retained in [runtime input aliases](artifacts/runtime-exact-input-alias-comparisons.csv);
they are not additional simulations or independently differentiated surface responses.

### Site unrutted gravel/high diagnostic panel

| Soil | Runtime | Drainage | Export kg/yr | Ratio to legacy | Buffer Dp m³/yr | Near-capacity days |
| --- | --- | --- | --- | --- | --- | --- |
| sand | no UI | current | 897.41 | 44.4 | 30.5 | 2669 |
| sand | no UI | source | 47.33 | 2.34 | 3170.1 | 46 |
| sand | ui-only | current | 147.98 | 7.32 | 15.1 | 552 |
| sand | ui-only | source | 47.63 | 2.36 | 2850.3 | 0 |
| sand | site-shared | current | 165.27 | 8.17 | 16.1 | 634 |
| sand | site-shared | source | 53.02 | 2.62 | 3128.4 | 0 |
| clay | no UI | current | 1463.47 | 6.08 | 61.4 | 2883 |
| clay | no UI | source | 450.97 | 1.87 | 2729.4 | 294 |
| clay | ui-only | current | 591.88 | 2.46 | 30.5 | 1198 |
| clay | ui-only | source | 377.95 | 1.57 | 2198.2 | 0 |
| clay | site-shared | current | 655.54 | 2.72 | 33.2 | 1383 |
| clay | site-shared | source | 414.80 | 1.72 | 2495.4 | 0 |
| new_lithic | no UI | current | 1147.12 | 9.96 | 2.6 | 2927 |
| new_lithic | no UI | source | 736.63 | 6.39 | 1706.4 | 1504 |
| new_lithic | ui-only | current | 472.61 | 4.1 | 1.3 | 2280 |
| new_lithic | ui-only | source | 392.77 | 3.41 | 1046.8 | 1460 |
| new_lithic | site-shared | current | 515.28 | 4.47 | 1.4 | 2507 |
| new_lithic | site-shared | source | 431.70 | 3.75 | 1123.7 | 1682 |
| new_lowk | no UI | current | 740.29 | 6.42 | 63.6 | 2701 |
| new_lowk | no UI | source | 126.47 | 1.1 | 3020.7 | 91 |
| new_lowk | ui-only | current | 115.82 | 1.01 | 30.6 | 263 |
| new_lowk | ui-only | source | 136.90 | 1.19 | 2465.5 | 0 |
| new_lowk | site-shared | current | 122.63 | 1.06 | 32.8 | 299 |
| new_lowk | site-shared | source | 145.74 | 1.26 | 2733.3 | 0 |
| new_open | no UI | current | 101.17 | 0.878 | 245.4 | 2618 |
| new_open | no UI | source | 92.12 | 0.799 | 2611.5 | 0 |
| new_open | ui-only | current | 163.84 | 1.42 | 94.3 | 34 |
| new_open | ui-only | source | 175.87 | 1.53 | 1853.1 | 0 |
| new_open | site-shared | current | 171.90 | 1.49 | 99.8 | 46 |
| new_open | site-shared | source | 184.79 | 1.6 | 2011.3 | 0 |

Near-capacity means reported soil water at least 90% of reported porosity capacity;
the denominator is 5,844 days. Dp is deep percolation from the buffer only. Runoff
boundaries use cumulative contributing area, while lateral transfers use local OFE
area. Apparent storage residuals are not claimed as full water closure. Year-one
sensitivity is retained as years 2–16 export and water summaries in the raw analysis.

## Artifact and accounting validation

All 1920 broad cases have successful native completion and complete finite daily
water calendars. 600/600 prior role controls reproduce all seven native outputs exactly.
There are 480 distinct consumed byte signatures and
420 semantic signatures after excluding soil labels/header metadata.
Paved/gravel, high/low traffic and some inbare/inveg modern inputs alias; these
scenarios are compatibility labels, not independent physically differentiated tests.

The broad matrix contains **6 cases with 12 negative native sediment-flux records**.
These are invalid physical budgets even if their signed sums happen to match report
precision. They are neither clipped to zero nor accepted as reconciled. One
Flagstaff/new_lithic/no-traffic source case emits −8.436 kg/m at the fill boundary
and −8.420 kg/m at the buffer boundary on year 7, day 251. Its annual report export
for that year is zero; report agreement alone would miss the invalid boundary flux.
The runtime bridge uses high traffic, so it does not establish whether this failure
persists in UI-mode no-traffic cases. All 12 flagged records are retained in
[negative sediment events](artifacts/negative-sediment-events.csv).

ELEMENT/report reconciliation passes 1698/1920 broad cases;
238 cases have 1390 EBE/ELEMENT event mismatches.
These are retained with original source-precision bounds in
[native audits](artifacts/native-audits.csv). No tolerances were widened. Net OFE
sediment exchange is not gross detachment or attribution of particles to their origin.
Upstream input equality does not guarantee output equality; the native coupled
runoff/erosion behavior is retained in [pair effects](artifacts/pair-effects.csv).

Raw artifacts: `/wc1/runs/ro/roads-drainage-validation-20261029-v2`. Frozen declarations, binary/source hashes, reader provenance
and portable comparisons are in `artifacts/`; large retained tables and prior control
hashes are indexed by [manifest](artifacts/large-artifact-manifest.json).
Failed staging attempts contained no new model outcomes and remain retained.

## Recommendation and limits

Do not change production `kslast` from this study. First use actual project runtime
settings for any subsequent Roads parameterization comparison, and preserve those
settings in the input manifest. The next bounded experiment should also reproduce
the Flagstaff/new_lithic/no-traffic negative flux with and without UI mode before
using that configuration's annual sediment report for parameter fitting. Its current
known failure is confined to the simplified study; this package does not establish
a production defect. Distinguish lithic bedrock, low-conductivity mineral
horizons and missing restriction information. A universal /1000 removal or deepest
horizon substitution is not physically established.

The assumed underlying thickness, generated depth rounding, native 1.8 m cap, and
missing local geological/hydrologic observations remain unresolved. For silt, the
source endpoint is taken from an emitted horizon below the computational cap, so it
is not a literal no-throttle boundary. Keep the 200 mm normalization. Any future
production rule requires a parameterization ADR and writer/consumer validation.

Validation gates and final review are recorded in [validation](artifacts/validation.md).
