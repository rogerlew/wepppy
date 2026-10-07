# Methods and claim boundary

This is a corrected-build repeat of the Topanga small-mutation experiment on
`hand-to-mouth-drought`, not an additional independent site. Baseline and mutant
within every pair use the same corrected executable. Burned and undisturbed
are separate strata. Apart from the declared Ksat/cover probes in isolated
copies, no model parameter is changed: rrinit, depression storage, rill-width
settings, source scenarios and production outputs remain untouched.

## Design

There are 140 single-OFE hillslopes in each stratum. Each baseline is run from
initial conditions through all 45 configured years (1980–2024). Each mutation
also runs its own complete history, retaining dynamic erosion/rill-width and
antecedent-state feedback. The original design is unchanged: first-horizon
Ksat times 0.99/1.01; initial interrill and rill cover jointly -0.01/+0.01.
If either cover direction would leave [0,1], both directions are excluded.
The frozen matrix is 1,120 requested, 1,088 eligible, 32 excluded mutations.
There are additionally 280 scenario/hillslope baselines.

Input files shared with the August snapshot are byte-identical. The new
staging also includes `chan.inp`, `chntyp.txt` and `tc.txt` when present, per
current replay requirements. Climate and terrain match between strata. Full
input, source-difference and mutation manifests are retained externally.

## Observation and compatibility

The fixed canonical binary is SHA256
`440fcebbeb2c51c2da46e258a53dce7ad609b783551ee2f5a6b1e18b368b2307`.
It lacks the old census observer. A companion build adds a write-only call at
the end of IRS, after final peak/duration bookkeeping; no extra solver call or
model-state mutation occurs. Seven canonical output files are byte-identical
with the fixed binary for burned and undisturbed H106, each through 45 years.
The diagnostic logs calendar year/day, OFE, runoff (m), peak (m/s) and raw
surface-return depth (m), with enough decimal digits to retain the native REAL.
All positive reported events must be represented; matching runoff and peak
must agree within printed report precision (0.001 mm and 0.001 mm/h).

This changes the observation grain from the August solver-call trace to final
IRS day/OFE values. A model event is a positive final runoff or peak. All raw
IRS observations, including zeros, are retained. Event pairs are outer joins
by scenario, hillslope, calendar year/day and OFE. Missing events are explicitly
distinguished from numerical zero. No solver-switch candidate prevalence is
claimed: this observer deliberately does not adjudicate solver mechanisms.
Figure 3 colors indicate positive raw surface return in either paired run,
not that every colored point used the correction (which has a small tolerance).

Figure 1 requires paired presence, baseline runoff ≥0.01 mm and positive
mutant runoff. Figure 3 requires paired presence, baseline peak ≥0.36 mm/h
and positive mutant peak. Figure 2 uses the original EBE event sediment
delivery (kg/m), requiring positive values on both sides. Its 0.1 kg/m printed
quantization is intentionally retained. Figures retain the original logarithmic
scales, 1:1 and twofold/fivefold guides, mutation markers, and inverse-response
opacity. Exact ties are dark under the original convention; statistics report
ties separately because they are not necessarily anomalous.

## Scientific limits

The correction is a bounded peak approximation, not combined kinematic-wave
routing or observed-flow validation. These project inputs use hourly water
balance; this experiment does not test the non-hourly 24-hour assumption.
Residual responses can include solver-boundary effects and accumulated
antecedent/erosion feedback. A candidate is not automatically a confirmed defect.
No per-mutation watershed routing is executed; no outlet or return-period claim
follows from these figures. August-to-current comparisons also cross source
lineages and observer definitions, so they are descriptive, not a strictly
isolated estimate of this patch's causal effect.

## Reproduction and retained failures

Authoritative evidence is on forest:
`/workdir/hand-to-mouth-fixed-census-20261006-v2`.
Use `/workdir/wepppy/.venv/bin/python` and the retained scripts. The frozen
`inputs.json`, `plan.json`, `build.json`, `observer.patch`, and `parity.json`
identify execution inputs and binaries. `repeat_census_analysis.py aggregate --root ROOT`
produces event and sediment Parquet ledgers and report readback checks.
That retained final aggregator matches the repository repeat_census.py.
`plot_figures.py --root ROOT --output ROOT/figures` produces Figures 1–3 and
their machine-readable statistics.

The invalid initial campaign is retained separately at
`/workdir/hand-to-mouth-fixed-census-20261006`, excluded from all figures.
It exposed an initial build-order race and a zero-based-array observation error;
the second campaign passes index one explicitly and verifies diagnostics against
canonical reports. A historical census integration test also fails because its
old executable path no longer matches its pinned hash; this is not suppressed.
The ordinary mutation-engine unit subset passes (16 tests).
