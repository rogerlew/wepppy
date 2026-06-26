# Strategic Eloquence OMNI Grassland Soil Inversion Investigation

## Summary

On `2026-06-25`, we investigated why some hillslopes in
`/wc1/runs/st/strategic-eloquence` on `wepp1` reported higher annual sediment
yield in the OMNI `undisturbed` scenario than in the `sbs_map` base scenario.

The affected rows are **not burned fire-severity hillslopes**. All 101
inversions are `Grasslands/Herbaceous` in both `sbs_map` and `undisturbed`.
The project has `_burn_grass = false`, so the SBS burn class is recorded for
these hillslopes but is not applied to grassland landuse, management, PMET, or
soil-use labels. The burned severity classes have zero inversions.

The inversion is real in raw WEPP output, not an OMNI aggregation bug. The raw
`loss_pw0.hill.parquet` files match the OMNI hillslope summary.

The root cause is mixed-generation soil inputs:

- The base `sbs_map` run reused root grassland soil files built on
  `2026-05-21`, before the restricting-layer behavior used by the current soil
  builder.
- The OMNI `undisturbed` scenario regenerated grassland soils on
  `2026-06-24` with the current builder.
- For the affected grassland soils, the base files leave the lithic bedrock
  unrecognized as a restricting layer (`res_lyr_i None`) and include it as an
  active lower layer. The regenerated undisturbed files recognize the
  restricting layer (`res_lyr_i 2`, `3`, or `4`) and usually set the final
  restricting-layer conductivity to `0.0 mm/hr`.
- The soil-generation difference shifts water away from baseflow and into surface runoff in the
  undisturbed scenario. For the inverted grassland subset, average baseflow is
  `82.3 mm/yr` in `sbs_map` and `0.0 mm/yr` in `undisturbed`; average runoff is
  `53.3 mm/yr` in `sbs_map` and `75.3 mm/yr` in `undisturbed`.

A local scratch reproduction of representative H562 with the production WEPP
binary confirms that the `.sol` file alone controls the flip: swapping only
the undisturbed soil into the base run reproduces the undisturbed runoff and
sediment; swapping only `pmetpara.txt` has no effect for H562.

## Scope

- Host checked: `wepp1`
- Host timestamp: `2026-06-25 09:09:01 PDT`
- Run path, host view: `/geodata/wc1/runs/st/strategic-eloquence`
- Run path, container view: `/wc1/runs/st/strategic-eloquence`
- Base scenario: root `sbs_map` run under `wepp/`
- Unburned scenario: `_pups/omni/scenarios/undisturbed/`
- WEPP binary recorded in `.err` files:
  `/workdir/wepppy/wepp_runner/bin/wepp_dcc52a6_hill`
- WEPP binary SHA-256:
  `365d44d643f70c5eee54e0ea81e74a125003799df8c912bab9ff267c476308a8`
- WEPP output model version: `2020.500`

Production files were read only. No production run files were modified.

## Affected Hillslopes

Comparing `sbs_map` against `undisturbed` in
`omni/scenarios.hillslope_summaries.parquet`:

| Cohort | Hillslopes | Inversions | `sbs_map` sediment (t/yr) | `undisturbed` sediment (t/yr) | Delta (t/yr) |
| --- | ---: | ---: | ---: | ---: | ---: |
| All hillslopes | 1908 | 101 | 162167.4402 | 1067.8845 | +161099.5557 |
| Grasslands/Herbaceous | 137 | 101 | 298.5408 | 403.4896 | -104.9488 |
| Inverted grassland subset | 101 | 101 | 235.3993 | 366.5823 | -131.1830 |
| Burned severity classes | 1771 | 0 | 161868.8994 | 664.3949 | +161204.5045 |

The largest affected rows are:

| WEPP ID | Topaz ID | Area (ha) | Slope | Soil key | `sbs_map` sediment (t/yr) | `undisturbed` sediment (t/yr) | Delta (t/yr) |
| ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 562 | 2563 | 13.9 | 0.627 | `3114506-silt loam-tall grass` | 16.5402 | 29.6076 | -13.0674 |
| 197 | 863 | 23.2 | 0.588 | `3120797-silt loam-tall grass` | 15.6349 | 26.3714 | -10.7365 |
| 453 | 2053 | 10.9 | 0.569 | `3114506-silt loam-tall grass` | 9.0921 | 15.9073 | -6.8152 |
| 769 | 3483 | 7.4 | 0.695 | `3120797-silt loam-tall grass` | 7.4232 | 13.9667 | -6.5435 |
| 809 | 3663 | 7.3 | 0.646 | `3114506-silt loam-tall grass` | 6.5698 | 11.7634 | -5.1936 |
| 246 | 1103 | 14.7 | 0.639 | `3120797-silt loam-tall grass` | 6.4604 | 11.3057 | -4.8453 |
| 526 | 2401 | 4.3 | 0.642 | `3114506-silt loam-tall grass` | 5.3955 | 10.0911 | -4.6956 |
| 419 | 1891 | 4.4 | 0.611 | `3120797-silt loam-tall grass` | 5.3188 | 9.6501 | -4.3313 |
| 362 | 1641 | 4.3 | 0.614 | `3120797-silt loam-tall grass` | 4.8704 | 9.0537 | -4.1833 |
| 272 | 1223 | 4.5 | 0.619 | `3120797-silt loam-tall grass` | 5.9169 | 9.9288 | -4.0119 |

All affected rows are listed in
`artifacts/affected_grassland_inversions.csv`. The full grassland cohort is in
`artifacts/grassland_soil_generation_cohort.csv`.

## Raw WEPP Confirmation

The OMNI summaries agree with the raw WEPP annual loss tables:

- Base: `/wc1/runs/st/strategic-eloquence/wepp/output/interchange/loss_pw0.hill.parquet`
- Undisturbed:
  `/wc1/runs/st/strategic-eloquence/_pups/omni/scenarios/undisturbed/wepp/output/interchange/loss_pw0.hill.parquet`

For H562, raw annual output is:

| Scenario | Runoff volume (m3/yr) | Baseflow volume (m3/yr) | Sediment yield (kg/yr) |
| --- | ---: | ---: | ---: |
| `sbs_map` | 24970.5 | 12455.5 | 16540.2 |
| `undisturbed` | 32782.4 | 0.0 | 29607.6 |

The same pattern holds across the affected grassland subset:

| Metric | `sbs_map` mean | `undisturbed` mean |
| --- | ---: | ---: |
| Runoff depth (mm/yr) | 53.3 | 75.3 |
| Lateral flow depth (mm/yr) | 550.4 | 602.9 |
| Baseflow depth (mm/yr) | 82.3 | 0.0 |

## Input Comparison

Representative H562 uses the same generated management, slope, climate, and
core sidecar controls except for the regenerated soil profile:

| Input | H562 finding |
| --- | --- |
| `p562.man` | Identical SHA-256 in base and undisturbed |
| `p562.slp` | Undisturbed `.run` references the root base slope file |
| `p562.cli` | Undisturbed `.run` references the root base climate file |
| `gwcoeff.txt` | Identical SHA-256 |
| `snow.txt` | Identical SHA-256 |
| `wepp_ui.txt` | Identical empty file |
| `pmetpara.txt` | Matching `silt_loam-tall_grass` entry for H562/topaz 2563 |
| `p562.sol` | Different; this difference controls the result |

The H562 soil diff is the decisive input difference. The base soil was derived
from the root soil file built on `2026-05-21`; the undisturbed soil was
regenerated in the OMNI scenario on `2026-06-24`:

| H562 soil attribute | Base `sbs_map` | OMNI `undisturbed` |
| --- | --- | --- |
| Source soil file | `/wc1/runs/st/strategic-eloquence/soils/3114506.sol` | `/wc1/runs/st/strategic-eloquence/_pups/omni/scenarios/undisturbed/soils/3114506.sol` |
| Source build date | `2026-05-21` | `2026-06-24` |
| Restricting layer note | `res_lyr_i None` | `res_lyr_i 3` |
| WEPP soil layers | 5 | 4 |
| Final restricting-layer record | `1 10000.0 0.01` | `1 10000.0 0.0` |

This does not mean the WEPP binary or deployed code necessarily changed
between the base WEPP execution and the OMNI undisturbed WEPP execution on
`2026-06-24`. The base H562 WEPP run executed at `2026-06-24 10:01 PDT`, and
the undisturbed H562 WEPP run executed at `2026-06-24 15:28 PDT`; both recorded
the same production binary. The mismatch is older: base WEPP reused a root
source soil artifact generated on `2026-05-21`, while OMNI regenerated its
scenario source soil on `2026-06-24` under the then-current soil builder.

The old base file treats the Lithic bedrock horizon as an active lower layer
and leaves it available to WEPP hydrology. The regenerated undisturbed file
recognizes the Lithic bedrock as the restricting layer and truncates the active
profile above it. That change removes the groundwater/baseflow response and
raises runoff enough to raise sediment yield on steep grassland hillslopes.

Note on PMET: the fourth field in `pmetpara.txt` is the sequential PMET entry
number, not the WEPP hillslope ID. The H562/topaz 2563 PMET entry is line 375
in both base and undisturbed, and both entries are `silt_loam-tall_grass`.

## Cohort Soil Pattern

All 101 inverted grassland hillslopes have different base and undisturbed
`.sol` files. Their soil-generation pattern is:

| Base soil pattern | Undisturbed soil pattern | Affected hillslopes |
| --- | --- | ---: |
| 5 layers, `kslast = 0.01`, `res_lyr_i None` | 4 layers, `kslast = 0.0`, `res_lyr_i 3` | 84 |
| 5 layers, `kslast = 0.01`, `res_lyr_i None` | 4 layers, `kslast = 0.0`, `res_lyr_i 4` | 3 |
| 4 layers, `kslast = 0.01`, `res_lyr_i None` | 3 layers, `kslast = 0.0`, `res_lyr_i 2` | 14 |

Affected soil keys:

| Soil key | Affected hillslopes | `sbs_map` sediment (t/yr) | `undisturbed` sediment (t/yr) | Delta (t/yr) |
| --- | ---: | ---: | ---: | ---: |
| `3114506-silt loam-tall grass` | 30 | 86.3054 | 142.0407 | -55.7353 |
| `3120797-silt loam-tall grass` | 12 | 54.5449 | 94.7715 | -40.2266 |
| `3120805-silt loam-tall grass` | 9 | 24.7843 | 32.4685 | -7.6842 |
| `3114490-silt loam-tall grass` | 7 | 6.9824 | 11.4911 | -4.5087 |
| `3114468-silt loam-tall grass` | 1 | 5.2045 | 9.0246 | -3.8201 |
| `3114505-silt loam-tall grass` | 11 | 15.9381 | 19.0890 | -3.1509 |
| `3114518-silt loam-tall grass` | 6 | 15.4824 | 18.4895 | -3.0071 |
| `3114660-silt loam-tall grass` | 3 | 2.9865 | 5.7846 | -2.7981 |
| `3114489-silt loam-tall grass` | 4 | 3.2248 | 5.9070 | -2.6822 |
| `3114512-silt loam-tall grass` | 8 | 7.1739 | 9.3820 | -2.2081 |
| `3114517-silt loam-tall grass` | 5 | 8.5165 | 10.6392 | -2.1227 |
| `3114474-silt loam-tall grass` | 2 | 1.2859 | 2.8272 | -1.5413 |
| `3120491-silt loam-tall grass` | 1 | 1.6438 | 2.9936 | -1.3498 |
| `3120807-silt loam-tall grass` | 1 | 1.1522 | 1.4970 | -0.3448 |
| `3114662-silt loam-tall grass` | 1 | 0.1737 | 0.1768 | -0.0031 |

Not every grassland hillslope inverts because slope, area, runoff threshold,
and sediment transport response still matter. The soil-generation mismatch is
the necessary driver for the unexpected scenario ordering; local topography
and runoff magnitude determine whether the extra undisturbed runoff produces a
negative annual sediment delta.

## Driver Isolation

The H562 inputs were copied to a local scratch directory preserving production
relative paths, then rerun with the same production binary:

`/workdir/wepppy/wepp_runner/bin/wepp_dcc52a6_hill`

| H562 input combination | Total runoff (mm/yr) | Sediment (t/yr) |
| --- | ---: | ---: |
| Base `sbs_map` | 179.80 | 16.5812 |
| OMNI `undisturbed` | 235.99 | 29.6406 |
| Base run + undisturbed `p562.sol` | 235.99 | 29.6406 |
| Undisturbed run + base `p562.sol` | 179.80 | 16.5812 |
| Base run + undisturbed `pmetpara.txt` | 179.80 | 16.5812 |
| Undisturbed run + base `pmetpara.txt` | 235.99 | 29.6406 |

The inversion follows the soil file exactly. The `pmetpara.txt` swap does not
change H562 because the relevant PMET entry is already `silt_loam-tall_grass`
in both scenarios. The same conclusion is supported by H769, which inverts
with matching base and undisturbed `silt_loam-tall_grass` PMET entries.

The reproduction table is in
`artifacts/h562_soil_swap_reproduction.csv`.

## Interpretation

Grassland did not burn in the WEPP parameterization for this run. The run is
comparing two different generations of the same nominal grassland soil
contract. The base `sbs_map` side was rerun through WEPP on `2026-06-24`, but
it used root soil source files left from `2026-05-21`. The OMNI `undisturbed`
side rebuilt soils on `2026-06-24` and therefore used the newer
restricting-layer handling.

For the affected grassland soils, the newer profile is shallower and blocks the
bedrock exit. That reduces groundwater/baseflow and increases runoff. Because
the affected hillslopes are steep enough and already erosive grassland
hillslopes, the extra runoff increases sediment yield enough for
`undisturbed` to exceed `sbs_map`.

This should not be read as "unburned fire-severity hillslopes are more erosive
than burned hillslopes" for this project. The burned classes behave in the
expected direction at the annual summary level. The surprising rows are
grassland rows whose labels stayed the same while their soil-generation
version changed between base and OMNI.

## Conclusion

The strategic-eloquence inversion is an input-generation consistency issue, not
a WEPP binary regression and not an OMNI aggregation error:

- 101 of 1908 hillslopes have `undisturbed` sediment greater than `sbs_map`.
- All 101 are `Grasslands/Herbaceous`; no burned severity class inverts.
- Raw WEPP annual loss tables match the OMNI summary.
- The representative H562 swap test proves the result follows the `.sol` file,
  not `pmetpara.txt`, management, slope, climate, burn-severity grass handling,
  or sidecar flags.
- The base run uses stale root grassland soil source files from `2026-05-21`;
  OMNI undisturbed regenerated soils on `2026-06-24`.

The smallest safe operational next step is to rerun the base project inputs
from soils through WEPP with the current soil builder, then rerun OMNI so the
base and scenario comparisons use the same soil-generation contract.

## Artifacts

`artifacts/` contains derived evidence only:

- `affected_grassland_inversions.csv` - all 101 inverted grassland rows with
  scenario sediment, runoff, baseflow, soil metadata, and PMET metadata.
- `grassland_soil_generation_cohort.csv` - all 137 base grassland rows,
  including non-inverted rows, with the same metadata.
- `h562_soil_swap_reproduction.csv` - local scratch rerun results for H562
  baseline and swapped-input variants.

## Commands Used

Representative read-only production commands:

```bash
ssh wepp1 'hostname; pwd; date +"%Y-%m-%d %H:%M:%S %Z"'
ssh wepp1 'ls -la /geodata/wc1/runs/st/strategic-eloquence'
ssh wepp1 'cd /workdir/wepppy && wctl docker compose ps --services --filter status=running'
ssh wepp1 'cd /workdir/wepppy && wctl docker compose exec -T rq-worker python -'
```

Representative local scratch reproduction shape:

```bash
ssh wepp1 'cd /geodata/wc1/runs/st/strategic-eloquence && tar -cf - <targeted H562 inputs>' \
  | tar -C /tmp/strategic_eloquence_h562/run_root -xf -

cd /tmp/strategic_eloquence_h562/variants/<variant>/wepp/runs
/workdir/wepppy/wepp_runner/bin/wepp_dcc52a6_hill < p562.run
```

No production files were modified.
