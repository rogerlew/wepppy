# Honeyed Marathoner OMNI Sediment Inversion Investigation

## Summary

On `2026-06-12`, we investigated why three hillslopes in
`/wc1/runs/ho/honeyed-marathoner` on `wepp1` report higher annual sediment
yield in the unburned OMNI `undisturbed` scenario than in the burned
`sbs_map` base scenario.

The inversion is real in the raw WEPP output, but it is very small and
isolated. Only 3 of 471 hillslopes invert, with a combined difference of
`0.0622 t/yr`. All three are `Low Severity Fire` base hillslopes on
`620333-loam`.

The evidence points to a WEPP event-threshold behavior on one storm,
`1992-06-16`, rather than an OMNI aggregation error or a materially wetter
unburned antecedent soil profile.

## Scope

- Host checked: `wepp1`
- Host timestamp: `2026-06-12 16:31:43 PDT`
- Run path, host view: `/geodata/wc1/runs/ho/honeyed-marathoner`
- Run path, container view: `/wc1/runs/ho/honeyed-marathoner`
- Burned scenario: root `sbs_map` run under `wepp/`
- Unburned scenario: `_pups/omni/scenarios/undisturbed/`
- Hillslopes: WEPP IDs `118`, `122`, and `264`
- WEPP runner binary recorded in copied `.err` files:
  `/workdir/wepppy/wepp_runner/bin/wepp_dcc52a6_hill`
- WEPP runner SHA-256:
  `365d44d643f70c5eee54e0ea81e74a125003799df8c912bab9ff267c476308a8`
- WEPP output model version: `2020.500`

The project had been forked, so `.err` files retaining older source paths were
treated as provenance noise and not as the root cause.

## Affected Hillslopes

| WEPP ID | Topaz ID | Area (ha) | Burned landuse | Unburned landuse | Burned sediment (t/yr) | Unburned sediment (t/yr) |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| 118 | 543 | 3.6 | Low Severity Fire | Evergreen Forest | 0.0000 | 0.0008 |
| 122 | 562 | 4.3 | Low Severity Fire | Evergreen Forest | 0.0000 | 0.0002 |
| 264 | 1153 | 42.8 | Low Severity Fire | Evergreen Forest | 0.0000 | 0.0612 |

The raw WEPP `loss.dat` files show the same pattern:

| WEPP ID | Burned kg leaving profile | Unburned kg leaving profile |
| --- | ---: | ---: |
| 118 | 0.000 | 0.765 |
| 122 | 0.000 | 0.159 |
| 264 | 0.000 | 61.179 |

## Related Low-Severity Forest Hillslopes

A follow-up read-only query on `2026-06-12 16:44:11 PDT` checked the full
`omni/scenarios.hillslope_summaries.parquet` table for other base
low-severity forest hillslopes. Interpreting low-severity forest as base
`Low Severity Fire` hillslopes with a base soil key containing
`forest low sev fire`, the project has 56 such hillslopes:

| Base soil key | Count | Inversions | No inversion |
| --- | ---: | ---: | ---: |
| `620333-loam-forest low sev fire` | 27 | 3 | 24 |
| `620349-loam-forest low sev fire` | 29 | 0 | 29 |
| Total | 56 | 3 | 53 |

The defect is therefore not universal across low-severity forest hillslopes,
and it is not universal within the same `620333` soil key as the affected
hillslopes. The broader low-severity forest subset totals `3.1304 t/yr` of
burned base sediment yield versus `0.0670 t/yr` of unburned sediment yield.

Examples of same-soil `620333-loam-forest low sev fire` hillslopes that do not
invert:

| WEPP ID | Topaz ID | Base sediment (t/yr) | Unburned sediment (t/yr) | Result |
| ---: | ---: | ---: | ---: | --- |
| 256 | 1122 | 1.6230 | 0.0048 | burned > unburned |
| 119 | 552 | 0.0000 | 0.0000 | equal |
| 123 | 563 | 0.0000 | 0.0000 | equal |
| 133 | 612 | 0.0000 | 0.0000 | equal |
| 148 | 672 | 0.0000 | 0.0000 | equal |

## Root Cause Evidence

Slope and climate are shared. The unburned `.run` files reference the same
root `p<ID>.slp` and `p<ID>.cli` files used by the burned base scenario. The
meaningful differences are generated management and soil parameters.

The inversion comes from the `1992-06-16` event. Antecedent total soil water at
the end of `1992-06-15` was nearly equal between scenarios:

| WEPP ID | Burned J167 soil water (mm) | Unburned J167 soil water (mm) | Difference (mm) |
| --- | ---: | ---: | ---: |
| 118 | 342.86 | 342.73 | -0.13 |
| 122 | 343.21 | 343.16 | -0.05 |
| 264 | 347.10 | 348.00 | +0.90 |

On `1992-06-16`, the storm precipitation was identical between burned and
unburned runs: `23.9 mm` on H118 and H122, and `24.6 mm` on H264. The
scenarios split sharply in runoff and sediment response:

| WEPP ID | Precipitation (mm) | Burned runoff (mm) | Unburned runoff (mm) | Burned sediment leaving profile | Unburned sediment leaving profile |
| --- | ---: | ---: | ---: | ---: | ---: |
| 118 | 23.9 | 0.0000 | 4.9954 | 0.000 kg | 0.765 kg |
| 122 | 23.9 | 0.0000 | 4.7153 | 0.000 kg | 0.159 kg |
| 264 | 24.6 | 0.0559 | 7.4450 | 0.000 kg | 61.179 kg |

For H264, the unburned event row in `H264.element.dat` reports `7.445 mm`
runoff, `7.445 mm/h` peak runoff, and `0.202 kg/m` sediment leaving the OFE.
The burned row for the same event reports only `0.056 mm` runoff and
`0.000 kg/m` sediment.

## Parameter Context

The generated runtime parameters seen in `element.dat` differ as expected for
low-severity burned forest versus undisturbed forest:

| Parameter | Burned low-severity base | Unburned undisturbed |
| --- | ---: | ---: |
| Effective conductivity (`Keff`) | 20 mm/h | 50 mm/h |
| Leaf area index | 2.320 | 11.875 |
| Canopy cover | 75% | 90% |
| Interrill cover | about 85% | 99.9% |
| Rill cover | about 85% | 99.9% |
| `Ki` | 0.030 | 0.012 |
| `Kr` | 0.377 | 0.004 |
| Critical shear | 2.000 | 2.000 |

Annual runoff is still higher in the burned scenario for these hillslopes.
The surprising result is localized to one storm where WEPP routes enough
unburned runoff to cross a sediment threshold while the burned scenario does
not.

## Interpretation

The root cause is a nonlinear WEPP event-routing and erosion-threshold edge
case created by the generated soil and management parameter differences. It is
not explained by materially wetter antecedent soil moisture in the unburned
scenario. By the day before the storm, the soil-water states had converged to
within about `1 mm`.

This should not be interpreted as the unburned scenario being practically more
erosive. The observed inversion is trace-scale because the burned base
sediment is exactly zero on these hillslopes, so any nonzero unburned sediment
appears higher in annual comparisons.

## Fixture

The three hillslopes were preserved as static test fixtures under:

`tests/omni/fixtures/honeyed_marathoner_sediment_inversion/`

The fixture preserves the production-relative WEPP layout below `run_root/` so
the unburned `.run` files continue to resolve their shared slope and climate
inputs through `../../../../../../wepp/runs/...`.

The focused regression test is:

`tests/omni/test_honeyed_marathoner_sediment_inversion_fixture.py`

## Commands Used

Representative read-only investigation commands:

```bash
ssh wepp1 'hostname; date +"%Y-%m-%d %H:%M:%S %Z"'
ssh wepp1 'cd /workdir/wepppy && wctl docker compose ps --services --filter status=running'
ssh wepp1 'cd /workdir/wepppy && wctl docker compose exec -T rq-worker python -'
```

Fixture copy command shape:

```bash
ssh wepp1 'cd /geodata/wc1/runs/ho/honeyed-marathoner && tar -cf - <targeted files>' \
  | tar -C tests/omni/fixtures/honeyed_marathoner_sediment_inversion/run_root -xf -
```

No production files were modified.
