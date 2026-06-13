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

The evidence points to a WEPP saturation-excess event-threshold behavior on one
storm, `1992-06-16`: canopy-suppressed soil evaporation leaves the unburned
*surface layer* near saturation entering the storm, while the exposed burned
surface retains storage. It is not an OMNI aggregation error, and the
*full-profile* antecedent soil water is nearly identical between scenarios.

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

## Binary Version Reproduction

The inversion was reproduced executionally on the dev container (not on
`wepp1`) on `2026-06-12` by re-running the preserved fixture inputs under two
WEPP builds:

| Binary | SHA-256 (prefix) | Unburned H118/H122/H264 sediment (kg) |
| --- | --- | ---: |
| `wepp_dcc52a6_hill` (production, recorded in `.err`) | `365d44d6` | 0.765 / 0.159 / 61.179 |
| `wepp_260606_hill` (current release) | `1fb763b0` | 0.765 / 0.159 / 61.179 |

Burned sediment is `0.000 kg` on all three hillslopes under both builds. The
`wepp_dcc52a6_hill` run reproduced the production `loss.dat` files
byte-for-byte. The `wepp_260606_hill` run produced identical sediment totals;
its only differences are cosmetic output formatting (column widths and a
last-digit rounding in the particle-class table).

The inversion is therefore version-stable across the `dcc52a6` to `260606`
release range. It is neither a regression introduced by, nor a defect fixed
in, the current release.

Reproduction depends on the per-run sidecar inputs (`gwcoeff.txt`,
`pmetpara.txt`, `snow.txt`, and the empty `wepp_ui.txt` flag). Without
`wepp_ui.txt` the hourly seepage/melt path is disabled and every hillslope
reports zero sediment, which masks the inversion. These sidecars are committed
with the fixture for this reason.

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

The inversion comes from the `1992-06-16` event. Two soil-water quantities must
be kept distinct. Antecedent *total-profile* soil water at the end of
`1992-06-15` (J167) was nearly equal between scenarios:

| WEPP ID | Burned J167 total soil water (mm) | Unburned J167 total soil water (mm) | Difference (mm) |
| --- | ---: | ---: | ---: |
| 118 | 342.86 | 342.73 | -0.13 |
| 122 | 343.21 | 343.16 | -0.05 |
| 264 | 347.10 | 348.00 | +0.90 |

This near-convergence is misleading. Infiltration and runoff are governed by
the *surface layer*, not the full profile, and the surface layers had not
converged. The `soil.dat` top-layer relative saturation entering the storm
(J167) shows the burned surface materially drier:

| WEPP ID | Burned J167 surface saturation | Unburned J167 surface saturation |
| --- | ---: | ---: |
| 118 | 0.83 | 0.95 |
| 122 | 0.83 | 0.95 |
| 264 | 0.84 | 0.98 |

The unburned surface enters the storm near saturation; the burned surface
retains several times more air-filled storage. The cause of that gap is
developed under Surface Evaporation and Saturation-Excess Runoff below.

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

## Driver Isolation (Parameter Swap)

To find which generated input drives the split, the `1992-06-16` response on
H264 was re-run under the current release with the burned and unburned
`p264.man` / `p264.sol` files mixed, and with individual `.man` sections
swapped in isolation:

| H264 input combination | Storm runoff (mm) | Storm sediment (kg/m) |
| --- | ---: | ---: |
| Unburned man + unburned soil (baseline unburned) | 7.445 | 0.202 |
| Burned man + burned soil (baseline burned) | 0.056 | 0.000 |
| Unburned man + burned soil | 8.379 | 8.739 |
| Unburned man, burned plant-growth section only | 0.241 | 0.000 |
| Unburned man, burned initial-condition section only | 6.291 | 0.891 |

The soil file is not the driver: pairing the unburned management with the
burned soil leaves the inversion intact, and in fact larger. The flip is
controlled by the plant-growth section of the management file. Substituting
only the burned plant-growth block collapses the unburned storm to burned-like
runoff and zero sediment, even on the unburned soil (`Keff = 50 mm/h`);
substituting only the burned initial-condition block does not. The
low-severity-fire plant-growth parameters (canopy, cover, biomass, surface
roughness) — not soil conductivity or initial conditions — govern whether this
storm crosses the peak-runoff and rill-detachment thresholds.

## Surface Evaporation and Saturation-Excess Runoff

The surface-saturation gap is produced by soil evaporation, which the
plant-growth block modulates through canopy. Across the entire antecedent
run-up (J120-J167, 1992) both scenarios produce zero runoff, so the surface
divergence is evaporative, not runoff-driven. Transpiration is also zero in
both runs — this management is static cover with no active growth — leaving
soil evaporation as the only active ET pathway:

| WEPP ID | Burned antecedent soil evap (mm) | Unburned antecedent soil evap (mm) |
| --- | ---: | ---: |
| 118 | 30.6 | 0.5 |
| 122 | 30.7 | 0.5 |
| 264 | 28.6 | 0.5 |

The reduced burned canopy (`75%` cover, LAI `2.320`) exposes the surface and
evaporates roughly `28-31 mm` more over the six antecedent weeks than the
undisturbed canopy (`90%` cover, LAI `11.875`), which suppresses evaporation to
near zero. That extra drying is what holds the burned surface layer below
saturation.

On the storm day the partition then runs counter to the steady conductivity
ordering. The `1992-06-16` burst is short and intense (H264: `24.6 mm` over
`1.4 h`, peak intensity near `44 mm/h`):

- Unburned (`Keff = 50 mm/h`): peak rainfall is below `Keff`, so there is no
  infiltration-excess driver — but the surface is already saturated, and on
  J168 the wetting-front suction collapses to about `1 mm`. The profile cannot
  accept more water and sheds it as saturation-excess runoff: `7.445 mm`
  concentrated in about one hour, peak near `7.4 mm/h`.
- Burned (`Keff = 20 mm/h`): peak rainfall exceeds `Keff`, so infiltration
  excess would be expected — but the drier surface still has storage and a
  strong wetting-front suction (about `40 mm` on J167) that draws the burst in.
  Runoff is only `0.056 mm`.

The lower-conductivity burned soil therefore infiltrates more of this
particular burst because antecedent evaporation had emptied its surface
storage, while the higher-conductivity unburned soil runs off because it was
saturated. The concentrated unburned peak puts rill flow shear above the
critical value (`Tauc = 2.0`), detaching `0.202 kg/m`; the burned trickle
stays far below threshold at zero.

This is defensible physics rather than a routing, infiltration, or erosion code
defect: it reproduces identically under `wepp_260606`. The only link open to
challenge is whether WEPP's bare-soil evaporation response to reduced canopy
(the `0.5` vs `~30 mm` antecedent split) is correctly parameterized — a
calibration question, not a code bug.

## Interpretation

The root cause is a nonlinear WEPP saturation-excess and erosion-threshold edge
case created by the generated low-severity-fire plant-growth management
parameters (see Driver Isolation and Surface Evaporation and Saturation-Excess
Runoff). It is not driven by the soil file or the initial-condition parameters.

It *is* an antecedent-moisture effect, but in the surface layer rather than the
full profile. Total-profile soil water converged to within about `1 mm` by the
day before the storm, which earlier framing read as evidence that antecedent
moisture was not involved; the infiltration-governing surface layer, however,
had not converged (burned saturation about `0.84`, unburned about `0.98`),
because canopy-suppressed evaporation kept the unburned surface near saturation
while the exposed burned surface dried. The full-profile convergence is a red
herring for this storm.

This should not be interpreted as the unburned scenario being practically more
erosive. Annual runoff remains higher in the burned scenario, and the observed
inversion is trace-scale because the burned base sediment is exactly zero on
these hillslopes, so any nonzero unburned sediment appears higher in annual
comparisons.

## Fixture

The three hillslopes were preserved as static test fixtures under:

`tests/omni/fixtures/honeyed_marathoner_sediment_inversion/`

The fixture preserves the production-relative WEPP layout below `run_root/` so
the unburned `.run` files continue to resolve their shared slope and climate
inputs through `../../../../../../wepp/runs/...`.

Each `wepp/runs/` directory also carries the per-run sidecar inputs
(`gwcoeff.txt`, `pmetpara.txt`, `snow.txt`, `wepp_ui.txt`) required to re-run
WEPP and reproduce the inversion; see Binary Version Reproduction. The current
regression test asserts against the preserved output files and does not
re-execute the binary.

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

Reproduction command shape (run on a scratch copy, never in the fixture, to
avoid overwriting the preserved outputs):

```bash
cd <scratch>/_pups/omni/scenarios/undisturbed/wepp/runs \
  && /workdir/wepppy/wepp_runner/bin/wepp_260606_hill < p264.run
```

No production files were modified.
