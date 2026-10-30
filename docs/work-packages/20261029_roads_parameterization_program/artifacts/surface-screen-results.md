# Development screen results and next decision

2026-10-30 UTC. The previous goal turn made concrete progress by launching a frozen
screen and implementing scope tests. This continuation completed that screen,
rehashed all cases, ran a runtime diagnostic, and obtained a parity-verified native
trace. No model has been accepted.

## Completed surface screen

`surface-screen-v4`: 576 declared cases, all retained, including native failures.
Portable case results: `surface-screen-v4.json`; independent scoring:
`surface-screen-score.json`. The scoring verifier checks declaration membership,
case uniqueness, native hashes, reference records and audit/result agreement.

| Treatment | Magnitude-rule passes / 96 | Native failures | Cases failing physical/accounting gate |
| --- | ---: | ---: | ---: |
| Generated roles | 88 | 8 | 16 |
| Road erosion parameters | 85 | 8 | 13 |
| Erosion plus upper-layer rock | 89 | 6 | 10 |
| Rock plus fixed Ksat 1 mm/hour | 75 | 20 | 20 |
| Rock plus fixed Ksat 3 mm/hour | 78 | 18 | 18 |
| Rock plus fixed Ksat 10 mm/hour | 86 | 6 | 11 |

All six fail. Native failures remain in coverage denominators and independently
veto acceptance. The original roles/erosion failures are Flagstaff, sand/clay,
no-traffic configurations. All recorded stops are `HOURLY_WATER_UNMET`; changing
road parameters is not sufficient evidence that this is a soil-only issue.
The screen uses UI mode but omits project PMET/snow/GW settings, so its rejections
apply to these exact treatments **and runtime**, not every possible faithful model.

The score applies the 95% overall / 90% per group gates separately to meaningful
and small-load strata. It cannot let a populated failing small-load stratum hide
inside the overall average. Seven new scoring tests pass; the scope and scoring
suite passes 14 tests (the separate runtime/negative-flux suite has seven tests).

## Twenty-run runtime diagnostic

`runtime-diagnostic-v1` holds five selected development configurations, each with
PMET only, snow only, PMET+snow, or all project shared files. See
`runtime-diagnostic.json`. No soil parameters changed.

- Sand/site control completes and reconciles under all four settings.
- Loam/site roles completes but retains one EBE mismatch under all four.
- Loam/site paved Ksat 3 failure resolves with snow, including the full bundle;
  PMET alone still fails.
- Clay/Birmingham gravel rock treatment resolves with snow alone but fails with
  PMET, PMET+snow and full project settings.
- Sand/Birmingham gravel Ksat 1 fails under all four settings.

PMET-enabled completed cases report three crop-name fallback notices: the copied
forest coefficients are applied to the three road-profile crop names. These settings
are explicit experimental model choices, not calibrated regional climates. This
prevents interpreting full-file copying as neutral execution plumbing.

## One explained sediment-accounting discrepancy

For `site-loam-inbare-gravel-high-roles-ui-only`, exact-binary debugger trace v7
observes, on 2003-01-05, terminal OFE `ofelod = 3.23706 kg/m`, `qout = 0`, and
reported `avsole = 0`. Pinned source `sloss.for:267–277` makes that distinction:
the noncontoured terminal load enters reported export only when `qout > 0`.

The unadjusted annual ELEMENT/report discrepancy is 0.7996725 kg/year. The observed
branch accounts for 0.80117235 kg/year (3.23706 × 3.96 / 16). Residual is
-0.00149985 kg/year, within the unchanged 0.17715780324 kg/year precision bound.
The dated EBE mismatch is the same event. This explains this particular report
comparison; it does not turn the unexported OFE load into observed sediment export
or prove every other discrepancy has the same cause. No values were clipped or
native outputs rewritten.

`report-trace.json` retains provenance and byte parity for **all seven** original
native output files. The host debugger uses snapshotted container loader/libraries
and source extracted from pinned commit `b73e93b19a724d1991d341d38a18d11e742231bd`.
The host checkout has advanced; its current source must not substitute for pinned
source. Earlier trace attempts are retained: missing cwd/optimized local, host
library rounding drift, wrapper without tracing, and symbol/language setup errors.
Only v7 provides the complete clean trace plus exact output parity.

## Next experiment

`project-runtime-screen-v2` runs the same 96 development configurations for roles,
erosion and rock (288 cases), with the complete existing project runtime bundle.
No fixed-Ksat treatment is being promoted. This isolates the runtime omission before
considering changes to generated subsurface material. All three climates explicitly
receive the same project model settings as a controlled sensitivity panel, not an
assertion of regional calibration. Full production builders and independent validation
remain subsequent gates.

Command: `wctl exec weppcloud python docs/work-packages/20261029_roads_parameterization_program/artifacts/project_runtime_screen.py`.
Log: `/tmp/roads-project-runtime-screen-v2.log`. V1's importlib worker pickling failure
occurred before native execution; v2 uses a module-level worker entry point.

## Completed full-runtime screen and boundary diagnostic

All 288 full-runtime cases completed or produced retained native failures;
`project-runtime-score.json` verifies them with the same gates. Roles passes 80/96
magnitude comparisons with 16 native failures and 24 physical/accounting failures;
erosion passes 77/96 with 16 and 21; rock passes 89/96 with six and ten. No treatment
passes. All scope/scoring/runtime tests pass together: 21 tests.

The next 18-run `boundary-diagnostic-v1` separates fill, buffer and both lower
boundaries across six development profiles. It uses the prior declared source
conductivities (sand 1.512, clay 3.276, loam source-bottom Ksat in mm/hour), never
values selected from sediment fit. Road inputs and all horizons remain identical.
This is a sensitivity hypothesis, not evidence that soil Ksat equals effective
fractured-bedrock drainage.

Both site controls complete and reconcile for all three targets. Birmingham/sand
erosion completes when fill or both boundaries change; buffer alone still fails.
Birmingham/clay rock and Flagstaff/sand/clay erosion fail under every target.
Thus lower-boundary impedance explains some sensitivity but is not a general fix.
All cases and failure diagnostics are in `boundary-diagnostic.json`.

## Next supported mechanism

Pinned `infpar.for:617–631` describes a forest saturation-dependent conductivity
adjustment enabled by `ksatadj=1`. For 9002 soils it uses the Saxton/Rawls relation;
`ksatfac` and `ksatrec` are used in the separate 9001 branch, not this 9002 branch.
The generated bare/bare/forest surrogate inherits `ksatadj=1` even on the engineered
road and fill. The next diagnostic should isolate disabling this forest adjustment
on fill, road+fill and buffer, while keeping horizons and lower boundaries intact.
This tests whether transferring a disturbed-forest hydraulic rule to engineered
surfaces is appropriate; it is not yet justification to change the default.
Exact pinned sources and hashes are retained in scratch `pinned-source-audit/`.
