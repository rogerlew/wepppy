# Revised public-controller geometry sensitivity

All four declared contexts completed with generated-input, native and current-report
readback. [Independent project numeric readback](revised-project-independent-science-readback.json)
and the [joint scientific review](revised-sensitivity-science-review.md)
pass for all four contexts.
This is a production legacy-template controller study, separate from the generated
conditioned-U12 capsule study. No model default, generated-soil policy, production
view, browser/RQ parity or field calibration is adopted by this experiment.

## Reproduction and retained attempts

[Protocol](revised-project-sensitivity-protocol.md),
[initial driver](revised_project_sensitivity.py),
[continuation driver](revised_project_sensitivity_continue.py), and
[additive diagnostic readback](revised_project_sensitivity_readback.py) retain the
full execution design. Raw root is
`/wc1/runs/ro/roads-parameterization-program-20261103/revised-project-sensitivity-v1`.
Run commands use `wctl exec -T weppcloud python` with the driver path followed by
`declare` or `run`; the additive reader takes no arguments. Completed declarations
and contexts refuse overwrite. The initial run used the retained same-process
UID/GID/umask wrapper recorded verbatim in `dependency-stop.log`.

Original declaration SHA256:
`d45818657bb9e5c2ca809365fb8f88966e57341061f51f90d76f1558265f720e`.
Additive continuation declaration SHA256:
`02f6752a4dd2ec6eb9af61e654a09ba77655b1f5a7daa6734a6977f3772b3a57`.
Both received independent execution review. Service identity was UID 1000,
GID 993, umask 022, the existing local weppcloud container. This is bounded local
controller evidence, not production-deployment parity.

Retained attempt history is deliberate: an initial runpy wrapper omitted the
artifact import directory and failed before execution; its log remains in
`failed-wrapper-import.log`. After the first complete context, the dependency
guard stopped before context two because a concurrently finalized matrix helper
removed an unused optional execute argument. Independent review reconstructed the
exact old hash and verified that this project path does not call that helper.
The additive continuation binds the first raw artifacts and receipt and executes
only the remaining three contexts, preserving `dependency-stop.log`.

The original invariant-input comparator includes `chntyp.txt`, but exact r7
`wshdrv.for:516–519` deletes/recreates this file and `wshcqi.for:139–154` writes
contributing-area/channel-type diagnostics. Source inspection found no read
consumer. Its geometry-dependent contents are output, not an invariant input.
The original comparator failure and every diagnostic hash remain retained;
the additive readback excludes only that source-proven output from input parity.
This does not relax numeric tolerances or rerun model histories.

## Results and interpretation

| Width / fill length (m) | Full Roads profile area (m2) | Mean annual profile export (kg) | Export density (kg/m2/year) | Mean annual profile runoff (m3) |
| --- | ---: | ---: | ---: | ---: |
| 4 / 30 | 10,737.70 | 9,025.41668 | 0.84053537 | 2,311.08895 |
| 8 / 30 | 21,475.29 | 18,050.81688 | 0.84053891 | 4,622.17929 |
| 4 / 60 | 14,937.70 | 9,394.05240 | 0.62888212 | 3,142.15215 |
| 8 / 60 | 29,875.29 | 18,788.09245 | 0.62888402 | 6,284.30711 |

These are summed original road/fill/buffer profile exports, not isolated road-prism
erosion or watershed-outlet yield. Full modeled mixed Roads+baseline reports are
retained separately in each receipt. All 35 corresponding profiles have four
distinct emitted slopes and unchanged soil, management and climate bytes.

Doubling width approximately doubles all three OFE areas, runoff and export while
leaving export density effectively unchanged. Width is a shared-profile geometry
control, not isolated road erodibility. Doubling fill length increases absolute
profile export by about 4.08% and runoff by about 35.96%, while lowering export per
modeled area by about 25.18%. Added fill area and routing both participate; a longer
fill is not a guaranteed reduction in total sediment. These are one-site sensitivity
responses, not calibrated predictions or monotonicity requirements.

The additive interaction on mean annual profile-export scale is 368.639845 kg/year; the interaction on export-density scale is -0.0000016363 kg/m2/year. The first is expected to include width scaling of the fill response and is
not evidence of a new independent erosion mechanism.

Every context successfully saves and reloads width/fill defaults through the real
Roads controller, prepares 39 segments, executes 35 profiles and a 16-year watershed,
and publishes current Roads resources. All 55 original upload features lack
recognized width/fill aliases, so fallback changes are effective in this site.
The separate synthetic valid-attribute control retains width 6 m and fill 20 m
under either default pair. Separate preparation-only resolver controls show malformed/nonfinite attributes
falling back with correct source labels after the conformance repair. The four
executed uploads use valid fallback settings; these controls are not native trials
of invalid uploaded features. No project-wide override mode is implied.

## Validation and limits

All 144 native calls have retained matching r7 binary identity, successful 16-year
traces, groundwater/hourly-UI activation and hillslope PMET consumer evidence.
Each of 420 profile OFE groups retains all 5,844 distinct daily dates; generated
width/fill values agree with emitted slopes and native WAT areas under the existing
serialization allowance. Role-boundary sediment, water runon/lateral outflow,
percolation, annual totals and largest sediment days remain in per-context receipts
and full native tables. This project lane checks calendars, finite values,
nonnegative sediment boundary flux and canonical accounting; it does not run the
strict EVENT particle-fraction audit. The companion capsule study owns that audit. Nonterminal Q remains explicitly diagnostic. Profile-fragment
and soil-policy controls were not varied; no six reserved materials were selected.

All 3,537 source entries and all 907 baseline files in each context remain intact.
The 520 invariant runtime files per context match after project-root normalization;
all generated products remain hash-bound. Four output trees contain 4,012 bound
artifacts in total. Actual current lifecycle admission and canonical daily water
accounting pass. Query refresh occurs through the existing controller, but this
lane does not certify complete browser/RQ/archive/restore/deployment parity.

[Machine-readable outcome](revised-project-sensitivity-results.json) and raw
`qualified-readback.json` share SHA256
`56c0d8456d51185e901667395cfea576cc5e452b7999e5163edbfd677d1aff01`.
The initial guard stop and final diagnostic-classification failure remain visible;
this is qualified complete evidence, not an uninterrupted original runner pass.
