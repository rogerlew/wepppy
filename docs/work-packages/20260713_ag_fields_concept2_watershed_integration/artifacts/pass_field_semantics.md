# AgFields Concept 2 PASS Field Semantics

**Contract version**: `ag_fields_pass_semantics_v1`

**Algorithm**: `ag_fields_v1`

**Decision authority**:
[ADR-0018](../../../adrs/ADR-0018-agfields-weighted-pass-accounting.md)

This table defines every transformation performed by the weighted legacy-ASCII
PASS combiner. It is grounded in the WEPP producer at
`/home/workdir/wepp-forest/src/wshpas.f90`, the watershed consumer at
`/home/workdir/wepp-forest/src/wshred.for`, the binary PASS contract at
`/home/workdir/wepp-forest/docs/contracts/hillslope-binary-pass-format.md`, and the
owned parser at
`/home/workdir/wepppyo3/wepp_interchange/src/hill_pass.rs`. No unlisted numeric
fallback is permitted.

For source `i`, let `r_i` be represented raster area, `a_i` be modeled area from
PASS header line 3, and `s_i = r_i / a_i`. The target parent area is `A`. A source
with `r_i = 0` remains in provenance and header/calendar validation but contributes
zero to row reconstruction.

## Header Semantics

| Line / field | WEPP meaning and unit | Class | Validation | Output transformation |
| --- | --- | --- | --- | --- |
| 1: `wshcli` | Climate-file token | Identity | WEPPpy proves all tokens resolve to the same climate content before calling the kernel. | Write the caller-owned, run-relative target token; never copy or edit a source path blindly. |
| 2: `nyear` | Simulation length, years | Identity | Parse as a positive integer and require equality across sources. | Copy the validated value. |
| 2: `ibyear` | Simulation start year | Identity | Parse as an integer and require equality across sources and calendars. | Copy the validated value. |
| 3: `harea` | Modeled hillslope area, m2 | Extensive geometry | Require finite `a_i > 0`; derive `s_i`; require finite `A > 0` and `sum(r_i) = A` within the floating-point area budget below. | Serialize `A` with legacy `E10.5`; reparse and diagnose its quantization residual. |
| 4: `npart` | Particle-class count | Identity | Require the supported value `5` and equality across sources. | Copy the validated value. |
| 4: `dia[1..5]` | Representative particle diameters, m | Shape / identity | Parse finite nonnegative values and require equality across sources after parsing. | Copy the target-parent values unchanged. |
| 5: `srp` | Surface-runoff phosphorus concentration, mg/L | Intensive identity | Parse finite nonnegative values and require equality across sources. | Copy the target-parent value unchanged. |
| 5: `slfp` | Subsurface-lateral-flow phosphorus concentration, mg/L | Intensive identity | Parse finite nonnegative values and require equality across sources. | Copy the target-parent value unchanged. |
| 5: `bfp` | Baseflow phosphorus concentration, mg/L | Intensive identity | Parse finite nonnegative values and require equality across sources. | Copy the target-parent value unchanged. |
| 5: `scp` | Sediment phosphorus concentration, mg/kg | Intensive identity | Parse finite nonnegative values and require equality across sources. | Copy the target-parent value unchanged. |

Header particle and phosphorus values are not area-averaged in v1. WEPP stores one
static set per hillslope in the master watershed PASS, so accepting heterogeneous
values would collapse a source distinction without an approved chemistry rule.

## Record and Calendar Semantics

| Field | WEPP meaning | Class | Transformation |
| --- | --- | --- | --- |
| `event` | `EVENT`, `SUBEVENT`, or `NO EVENT` | Shape | For positive-area sources, precedence is `EVENT` over `SUBEVENT` over `NO EVENT`. Zero-area sources do not change the label. Reject any other label. |
| `year` | Calendar year | Identity | Require the complete ordered `(year, julian)` sequence to match across sources; copy it. |
| `julian` | Julian day | Identity | Require the complete ordered `(year, julian)` sequence to match across sources; copy it. |
| `sim_day_index` | Parser-derived, one-based simulation day | Derived identity | Recompute while parsing; require alignment through the ordered day keys. It is not serialized in legacy PASS. |
| `month`, `day_of_month`, `water_year` | Parser-derived calendar fields | Derived identity | Recompute from `year` and `julian`; not serialized in legacy PASS. |

All parsed row numbers must be finite. Negative volumes, depths, rates,
concentrations, masses, durations, time-of-concentration values, or particle
fractions are rejected. `tdep` is the nonnegative total-deposition magnitude used
by the producer and consumer, not a signed balance term.

## EVENT Numeric Semantics

In the formulas below, `x_i` is a parsed source value for the aligned day. Sums
include positive-area sources only.

| Field | Unit | Class | `ag_fields_v1` transformation | Zero-volume behavior and closure |
| --- | --- | --- | --- | --- |
| `dur` | s | Hydrograph shape | `max(dur_i)` over contributing `EVENT` sources. | Zero if no contributing `EVENT`; shape diagnostic only. |
| `tcs` | h | Hydrograph shape | Build a triangular hydrograph for each source from scaled `runvol_i`, scaled `peakro_i`, and `tcs_i`; superimpose them and use the time of the combined peak. If no triangle exists, use `max(tcs_i)` over contributing `EVENT` sources. | Zero if no contributing `EVENT`; shape diagnostic only. |
| `oalpha` | unitless | Derived hydrograph shape | If combined runoff volume is positive, `max(tcs / 24, 3600 * tcs * peakro / runvol)`, matching the WEPP producer. Otherwise `tcs / 24`. | Never divide by zero; shape diagnostic only. |
| `runoff` | m for the daily record | Intensive depth | `runvol / A`. | Zero when `runvol = 0`; validate the serialized depth-volume identity. |
| `runvol` | m3 | Extensive | `sum(s_i * runvol_i)`. | Conserved directly event-by-event and over the full run. |
| `sbrunf` | m for the daily record | Intensive depth | `sbrunv / A`. | Zero when `sbrunv = 0`; validate the serialized depth-volume identity. |
| `sbrunv` | m3 | Extensive | `sum(s_i * sbrunv_i)`. | Conserved directly event-by-event and over the full run. |
| `drainq` | m for the daily record | Intensive daily depth | `drrunv / A`. The producer computes `drrunv = drainq * area`; the value is a daily depth even though older Arrow metadata calls it `m/day`. | Zero when `drrunv = 0`; validate the serialized depth-volume identity. |
| `drrunv` | m3 | Extensive | `sum(s_i * drrunv_i)`. | Conserved directly event-by-event and over the full run. |
| `peakro` | m3/s | Extensive rate plus timing shape | Scale each source peak by `s_i`; superimpose source triangular hydrographs and serialize their maximum summed rate. | Zero when no valid positive-volume/positive-peak triangle exists; not a mass-closure quantity. |
| `tdet` | kg | Extensive | `sum(s_i * tdet_i)`. | Conserved directly event-by-event and over the full run. |
| `tdep` | kg | Extensive | `sum(s_i * tdep_i)`. | Conserved directly event-by-event and over the full run. |
| `sedcon_1..5` | kg/m3 | Intensive concentration | For class `k`, compute `M_k = sum(s_i * sedcon_ik * runvol_i)` and write `M_k / runvol`. | Write zero when `runvol = 0`; conserve each `M_k` through serialized concentration and volume. |
| `clot`, `slot`, `saot`, `laot`, `sdot` | unitless fraction | Sediment shape | For class fraction `f_ik`, weight by source total class mass `M_i = runvol_i * sum_k(sedcon_ik)`: `sum(s_i * M_i * f_ik) / sum(s_i * M_i)`. | Write all five as zero when total sediment mass is zero; validate their sum against one when mass is positive, but do not treat the fractions themselves as extensive mass. |
| `gwbfv` | m3 | Extensive | `sum(s_i * gwbfv_i)`. The WEPP binary contract names it baseflow volume. | Conserved on every record type and over the full run. |
| `gwdsv` | m3 | Extensive | `sum(s_i * gwdsv_i)`. The WEPP binary contract names it dissolved-storage volume; legacy reports also call it deep seepage. | Conserved on every record type and over the full run. |

The existing `hill_pass_schema` metadata that labels `clot` as `m^3/s`, labels the
other four fractions as percentages, and omits the `m^3` units from `gwbfv` and
`gwdsv` is incorrect. The implementation updates those metadata descriptions
without changing column names or physical values.

## SUBEVENT and NO EVENT Semantics

For `SUBEVENT`, reconstruct `sbrunv`, `drrunv`, `gwbfv`, and `gwdsv` with the
extensive formulas above, then derive `sbrunf = sbrunv / A` and
`drainq = drrunv / A`. All EVENT-only fields are zero and are not serialized.

For `NO EVENT`, reconstruct and serialize only the extensive `gwbfv` and `gwdsv`
volumes. All other fields are zero in the parsed representation. When event
precedence promotes a day, quantities available on less-active source records are
still included; for example, baseflow from a `NO EVENT` source contributes to a
combined `EVENT` day.

## Serialization-Derived Closure Budget

Legacy row numbers use Fortran `E11.5` and header area uses `E10.5`. Both retain
five significant decimal digits because the Fortran mantissa is written as
`0.ddddd`. Define the half-unit-in-last-place budget for a
finite expected value `x` as:

```text
ulp_half(x) = 0                                      when x = 0
ulp_half(x) = 0.5 * 10^(floor(log10(abs(x))) - 4)   otherwise
fp(x)       = 16 * machine_epsilon * max(abs(x), 1)
direct(x)   = ulp_half(x) + fp(x)
```

The kernel accepts a reparsed directly serialized extensive quantity `x'` only
when `abs(x' - x) <= direct(x)`. This is a value-specific serialization bound, not
a tunable relative tolerance.

For sediment class mass, let expected concentration be `C = M / V`, with
`dC = direct(C)` and `dV = direct(V)`. The serialized/reparsed mass `C' * V'` must
satisfy:

```text
abs(C' * V' - M) <= abs(V) * dC + abs(C) * dV + dC * dV + fp(M)
```

The same product bound is used for the diagnostic identities `runoff * A`,
`sbrunf * A`, and `drainq * A`, with the direct serialization budget for the
corresponding volume added because both sides are serialized. A full-run residual
budget is the sum of its event budgets plus `fp(full_run_expected)`; it is not a
fixed percentage of the run total.

Before serialization, represented source areas must sum to the target area within
`64 * machine_epsilon * max(sum(r_i), A, 1)`. Raster planning normally makes this
identity exact; the bound admits only floating-point summation noise. Header-area
reparse uses `direct(A)`.

Diagnostics record expected value, reparsed value, residual, and calculated budget
for every conserved water volume, groundwater volume, sediment mass, and class
mass. Any residual beyond its calculated budget fails the parent combine before
atomic replacement.

## Evidence Notes

- `wshpas.f90` writes `peakro * harea`, `tdet`, `tdep`, class concentrations,
  particle fractions, `gwbfv`, and `gwdsv`; it derives runoff, lateral-flow, and
  tile volumes from their depths and area.
- `wshred.for` consumes `runvol` as volume, derives average runoff depth as
  `runvol / wsarea`, accumulates `gwbfv` and `gwdsv` as volumes, and computes each
  sediment-class mass as `sedcon_i * runvol`.
- `sloss.for` computes `sedcon_i` from total sediment concentration times
  `frcflw_i`, confirming that `frcflw_i` is a unitless class fraction.
- The HBP contract independently names `gwbfv` and `gwdsv` as
  `baseflow_volume_m3` and `dissolved_storage_volume_m3`.
