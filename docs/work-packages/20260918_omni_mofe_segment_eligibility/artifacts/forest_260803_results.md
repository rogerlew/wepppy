# Forest 260803 results

Parent `ef226e0f-a5f7-4daf-bee6-9db5f420c7aa`: all six scenario leaves and both
compilation/finalization jobs finished. Finalizer
`66b13972-07f0-4e03-ac05-7fba3760ba63` finished 2026-09-18 21:21:41 UTC.
All six saved child binary selections and hillslope/watershed execution logs
identify `wepp_260803`.

All six `H*.plot.dat` collections have zero asterisk overflow rows. All six
`loss_pw0.hill.parquet` tables contain 455 unique hillslopes, finite area/runoff/
sediment/soil-loss values and 22-year averaging metadata.

| Scenario | Area-weighted runoff (mm/year) | Sum of hillslope sediment yield (tonnes/year) |
| --- | --- | --- |
| uniform_low | 942.002 | 3497.9702 |
| uniform_moderate | 950.157 | 3850.1545 |
| uniform_high | 1047.930 | 16722.4385 |
| prescribed_fire | 905.584 | 1139.6947 |
| thinning_40_75 | 827.751 | 811.1821 |
| thinning_65_85 | 820.456 | 653.5012 |

These are summed hillslope yields, not watershed outlet delivery. Calculations
use the existing production summary formulas: sum runoff volume divided by
sum area in hectares times ten; sum sediment kilograms divided by 1000.

## Segment eligibility evidence

Base OFE assignments: 1052 forest (90), 13 bare (200). Base scalar labels are
434 thinning (424) and 21 forest (90), demonstrating why scalar labels cannot
serve as segment truth. Prescribed fire maps all 1052 forest segments to 410;
thinning 40/75 maps them to 424; thinning 65/85 maps them to 426. All three retain
every one of the 13 bare segments as 200.

Parsed both generated combined managements and prepared WEPP managements for
all six mixed forest/bare hillslopes (TOPAZ 1563, 1601, 1611, 911, 913, 971;
23 OFEs per scenario). Canopy, interrill and rill cover match the intended
per-segment source managements in prescribed fire and both thinning scenarios.
All checks pass, including unchanged bare-neighbor cover.

Existing full `readback_mofe.py` checks were also started for all six scenarios,
including complete soil serialization and manifests. All six completed
455 hillslopes each with zero failures. This does not supersede pending broad
regression gates.

## Limits and dispositions

The 260803 run resolves the observed execution/plot-overflow failure for these
inputs; it does not isolate the underlying numerical change between binaries.
The Rust malformed-token panic remains an independently identified defect.

Uniform-fire scenarios map all 1065 segments to their respective forest-fire
classes (406/418/405), including the 13 baseline bare segments. This is separate
from treatment eligibility and remains a parameterization-comparison finding.
Manual fire scenarios retained different grass/bare remappings. No adjustment
to either workflow was made during readback.

Do not claim the manual 20% comparison passed: manual runs and baseline outputs
still use the older binary, and thinning selections differ. The observed Omni
rank order is high > moderate > low > prescribed > thinning 40/75 > thinning
65/85 for both reported metrics, not proof of cross-workflow rank agreement.
