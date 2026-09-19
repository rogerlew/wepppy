# Manual low-severity rerun: remediation and executable comparison

Read-only verification of the user's Forest `equestrian-bonheur` rerun.
Parent `c68b4a68-39f4-40f1-9eac-4d32a791af71` and all 14 recorded child jobs
finished. Completion job ended 2026-09-18 22:31:43 UTC. Saved binary selection
and fresh execution logs identify `wepp_260803`. No run mutations were performed
by this verification.

## Artifact acceptance

Reused the prior package's `artifacts/readback_mofe.py`, passing
`/wc1/runs/eq/equestrian-bonheur`. All 455 hillslopes / 1065 OFEs passed with
zero failures. Every segment is class 406; expected canopy/interrill/rill cover
is 0.75/0.85/0.85. Parsed generated `landuse/hill_*.mofe.man` and prepared
`wepp/runs/p*.man` agree with that intent. Prepared soils pass scientific-token
and full serialization checks with initial saturation 0.75 and kslast 0.0001.
All hillslope plot files have zero asterisk overflow rows.

The complete numeric columns of the 455-row hillslope summary equal the fresh
Omni `uniform_low` summary after sorting by WEPP ID. The complete outlet-summary
table also equals Omni's. This establishes same-binary low-severity agreement
for this fully remapped selection, not all scenario types or selections.

## Whole-project results

Old comparison: repaired wepp1 `equestrian-bonheur` outputs using dcc52a6.
New comparison: the user rerun on Forest using 260803. Both average 22 years.

| Metric | dcc52a6 | 260803 manual (also Omni low) | Change |
| --- | --- | --- | --- |
| Area-weighted hillslope runoff, mm/year | 941.757189 | 942.001705 | +0.026% |
| Sum hillslope sediment yield, tonnes/year | 771.6286 | 3497.9702 | +353.32% |
| Outlet water discharge, m3/year | 22867721 | 22867820 | +0.000433% |
| Outlet sediment discharge, tonnes/year | 927.3 | 3195.7 | +244.62% |
| Gross hillslope soil loss, tonnes/year | 112924210.6726 | 3558.9182 | -99.99685% |

Gross soil loss is not delivered sediment. The enormous old gross erosion /
deposition cancellation is no longer present at that magnitude in the new
summary. Numerical plausibility still requires scientific interpretation;
successful execution is not proof of physical accuracy.

## Isolating executable effects from the changed selection

The older manual run has 1052 class-406 and 13 class-431 OFEs; the new selection
has 1065 class-406 OFEs. Thus whole-project differences alone are not a pure
binary experiment.

Compared SHA256 of actual prepared hillslope inputs on wepp1 with Forest:

| Input | Identical hillslopes | Changed hillslopes |
| --- | --- | --- |
| Management `.man` | 447 | 8 |
| Soil `.sol` | 447 | 8 |
| Slope `.slp` | 455 | 0 |
| Climate `.cli` | 455 | 0 |
| Run-control `.run` | 455 | 0 |

Changed management/soil WEPP IDs: 195, 196, 197, 208, 333, 341, 343, 345.
Read the old live parquet over SSH and compared with the new local parquet,
filtering both to the 447 hillslopes whose inputs all match byte-for-byte:

| Metric, unchanged-input subset | dcc52a6 | 260803 | Change |
| --- | --- | --- | --- |
| Runoff volume, m3/year | 16565144.1 | 16565655.1 | +0.003085% |
| Sediment yield, kg/year | 762204.8 | 3413607.7 | +347.86% |
| Gross soil loss, kg/year | 110844742854.6 | 3474385.6 | -99.99687% |

This is strong evidence that executable/runtime-version differences materially
affect sediment while barely affecting runoff in this project; the eight
remapped hillslopes cannot explain the sediment divergence. This is not an
ablation of individual Fortran changes, nor a same-host controlled replay of
both executables. Do not claim a specific source fix caused it without that
additional experiment.

## Disposition

Selected-hillslope landuse remediation passes generated/prepared input and
same-binary low-severity output verification. The earlier low-severity manual
versus Omni sediment discrepancy disappears when both current selections use
260803. Do not extrapolate that result to moderate/high/thinning without their
same-binary checks. No further rerun was submitted.
