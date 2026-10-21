# Physical water audit findings

## Conclusion

The calendar fixes do not establish watershed hydrologic correctness. Fresh
261021 execution confirms the tested OFE volume conversions and PASS loading,
but exposes four reproducible defects. Watershed correctness cannot be certified
until the defects are repaired and the affected accounting is repeated.
This is a completed diagnostic audit, not a corrected-model or deployment claim.

The operator’s concerns are Dp, lateral flow, ET and Q/QOFE through the last OFE
and into routing. Ash is excluded. Ayush’s original decks and executable were
not supplied, so these findings establish current-release behavior rather than
attributing his historical workbook to a particular model defect.

## What the field-by-field accounting establishes

For constant-width, ordinary hillslopes in this release, multiply each local
Ep, Es, Er and Dp depth by that OFE’s area. Sum volumes, then divide by full
hillslope area if reporting equivalent depth. ET is a local atmospheric loss;
it is not routed through PASS. Dp leaves the soil and recharges groundwater,
so counting both Dp and later baseflow as external combined-domain losses
would double-count water.

QOFE is outgoing runoff normalized over the local OFE area, including upstream
water. Q is normalized over cumulative contributing length. Consequently
QOFE × local area equals Q × cumulative area for the tested constant widths.
The next OFE’s UpStrmQ × receiving area matches the preceding outgoing volume.
Summing all QOFE volumes would count the same routed water repeatedly.
Terminal lateral export is latqcc × terminal OFE area, not full hillslope area;
upstream lateral contributions are internal transfers, not additional outlets.

All ten single-hillslope cases pass these surface/lateral transfer checks and
selected EVENT surface/SUBEVENT lateral comparisons within declared writer and
binary32 precision bounds. Each case contains 16,071 complete days (1980–2023).
The channel probe confirms PASS surface + lateral + eligible baseflow reaches
channel runon accounting: maximum single-hill discrepancy is 0.000106 m³;
maximum tested tributary discrepancy is 0.000599 m³. These are much smaller
than the subsequent rate-routing discrepancies.

PASS event filtering remains a distinct physical-versus-delivered boundary.
For 60/40, surface runoff omitted by event selection totals 426.561 m³ in daily
mode and 259.832 m³ in hourly mode over 44 years. These measured omissions are
not silently assigned to channel transmission loss. Rounded WAT reports zero
omitted lateral volume in these cases; sub-rounding lateral omissions are not
thereby proven absent.

## WPA-01: channel-local water missing from the inflow hydrograph

**Confirmed, unresolved.** `src/wshchr.for:154–193` adds channel-local net water
to the daily volume `volint`. When that water is positive, the surface-rate
branch distributes it through side-hillslope hydrographs. If there are no side
hillslopes, no such calls occur and the positive local contribution is absent
from `qlat`. Related zero-side-surface-volume cases also require coverage in repair.

In the original 1,144.3 m channel with a top-connected 60/40 hillslope, this
occurs on 6,249 daily-mode days (90,071.446 m³) and 6,485 hourly-mode days
(92,591.248 m³). These are observed positive local net volumes with zero lateral
inflow-rate integral. On 1996 day 37, the daily run accounts for 803.219 m³
upstream inflow plus 192.832 m³ local runoff and a net transmission term of
−4.099 m³, but its lateral inflow hydrograph is zero. The local-minus-loss
contribution of 196.931 m³ has no rate-series representation.

The published outflow/routed-hydrograph difference is not exactly this missing
term: source reconstruction, time integration and channel storage also matter.
Across 44 years, published daily outflow exceeds the independently integrated
native hydrograph by 89,991.335 m³ (12.32%) in daily mode and 92,857.616 m³
(12.17%) in hourly mode for this channel. This percentage is case-specific,
not a statement about every watershed.

Shorter 100 m channels, unequal tributaries, side placement and a two-channel
cascade also show rate/volume disagreement. At the final cascade outlet,
daily published outflow is 2,289,026.005 m³ versus integrated 2,272,144.166 m³;
hourly published outflow is 2,427,527.368 m³ versus integrated 2,409,376.539 m³.
The cascade transports upstream `tmpvol` in daily accounting but upstream `q1`
in rate routing; their disagreement propagates downstream.

`wshchr.for:654–657` calculates published outflow from the volume/storage balance
and then resets storage using that identity. A printed zero channel balance is
therefore insufficient proof. Both rectangular and trapezoidal native-rate
integration were evaluated; changing the quadrature does not explain the large gap.
Full-domain storage conservation remains unproven, even after identifying this branch.

Repair target: explicitly represent channel-local net inputs/losses in rate
construction, independently of side-hillslope surface runoff, while preserving
source support and testing positive/negative contributions and zero-side-flow cases.
Do not merely force the printed balance to zero or rescale an unrelated source.

## WPA-02: flat source hydrograph fails to preserve requested volume

**Confirmed, unresolved.** `src/chrqin.for` uses a flat peak when
`rainvol >= qp * td - eps`. It adds the peak only at timesteps whose endpoint
is within the duration; it neither preserves a fractional final interval nor
reconciles a requested volume greater than peak × duration.

A compiled harness from the committed native test suite executes the actual
release routine, not an arithmetic surrogate. Both initial and continuing-day
paths produce:

| Requested volume | Peak | Duration | Step | Integrated volume |
| ---: | ---: | ---: | ---: | ---: |
| 1,200 m³ | 1 m³/s | 1,200 s | 600 s | 1,200 m³ (positive control) |
| 900 m³ | 1 m³/s | 900 s | 600 s | 600 m³ |
| 1,000 m³ | 1 m³/s | 600 s | 600 s | 600 m³ |

Actual-case operands also reproduce the deficits: daily 1983 day 182 requests
313.900 m³ and yields 281.702386 m³; hourly 2017 day 37 requests 177.170 m³
and yields 164.516045 m³. These match the separately observed top-inflow gaps
within serialized/native precision. The 261010 exponential-branch first-sample
repair does not cover this flat branch.

Repair target: specify a volume-conserving flat-source discretization, including
partial intervals and inconsistent peak/volume/duration operands, and validate
it alongside exponential and return-flow components. Changing dates cannot fix it.

## WPA-03: hourly infiltration leaves water unallocated

**Confirmed, unresolved.** `src/watbal_hourly.for:520–523` stops distributing
infiltration when remaining `xfin` is within 0.00001 m. The next hourly iteration
overwrites that remainder without placing it in soil storage or an exported flux.
Read-only probes capture the remainder at each of the 24 hourly steps.

| OFE layout | Unallocated water over 44 years | Equivalent annual depth |
| --- | ---: | ---: |
| Single | 145.319 m³ | 0.3303 mm/year |
| 60/40 | 525.526 m³ | 1.1944 mm/year |
| 20/30/50 | 731.815 m³ | 1.6632 mm/year |

Individual hourly remainders approach 0.01 mm; some daily soil screens reach
0.24 mm residual. Subtracting the independently measured remainder reduces the
worst screened daily residual to 0.0216–0.0314 mm, consistent with the retained
printed-field rounding budget. This is a real small allocation loss, not an
instruction to alter reported ET, Dp, lateral flow or Q to make the books balance.
Initial/interception stores still limit a universal soil-closure claim.

Repair target: retain/distribute the remainder while respecting available-water
constraints; validate positive and negative infiltration, frozen conditions,
single/multiple layers and both water-balance modes before release.

## WPA-04: initial groundwater uses only the last OFE area

**Confirmed, unresolved for nonzero initial storage.** In `contin.for:1098`,
`igwstrv` is assigned inside the OFE loop. The last assignment survives, so an
initial hillslope groundwater depth is converted using only terminal OFE area.
Daily Dp recharge immediately below is correctly accumulated over all local
OFE areas; these are separate mechanisms.

With 100 mm initial groundwater, 10,000 m² total area and baseflow coefficient
0.04/day, the expected initial volume is 1,000 m³ and day-one baseflow is 40 m³.
Actual PASS baseflow is 40 m³ for one OFE, 16 m³ for 60/40, and 20 m³ for
20/30/50. Day-one Dp is zero; all WAT rows are byte-identical to the corresponding
zero-initial-groundwater runs. Only the groundwater input was changed. The
primary zero-initial-storage matrix cannot expose this initialization defect.

Repair target: initialize groundwater once from total contributing hillslope
area, preserving the existing recurrence timing and validating nonzero initial
storage and initial withdrawals across OFE layouts.

## Hydrologic partitioning in the controlled cases

Values below are mm/year over all 44 calendar years, with local ET/Dp weighted
by actual areas and terminal exports counted once. All cases receive the same
climate and use homogeneous 100 m × 100 m hillslopes; splitting can change
process predictions and is not required to produce identical partitioning.
The hourly-mode WAT file is a daily summary of an hourly seepage calculation.

| Mode / OFEs | P | ET | Dp | Terminal Q | Terminal lateral |
| --- | ---: | ---: | ---: | ---: | ---: |
| daily-equal | 2151.04 | 665.43 | 13.28 | 1348.87 | 119.04 |
| daily-lower60 | 2151.04 | 665.31 | 13.28 | 1349.20 | 118.85 |
| daily-single | 2151.04 | 666.31 | 13.28 | 1351.26 | 115.80 |
| daily-three | 2151.04 | 664.84 | 13.28 | 1348.96 | 119.55 |
| daily-upper60 | 2151.04 | 665.53 | 13.28 | 1348.64 | 119.47 |
| hourly-equal | 2151.04 | 572.16 | 6.79 | 490.65 | 1076.86 |
| hourly-lower60 | 2151.04 | 567.51 | 6.79 | 499.07 | 1072.80 |
| hourly-single | 2151.04 | 560.81 | 6.79 | 519.68 | 1059.75 |
| hourly-three | 2151.04 | 571.41 | 6.79 | 500.86 | 1067.29 |
| hourly-upper60 | 2151.04 | 576.17 | 6.79 | 484.88 | 1078.79 |

The large daily/hourly shift from surface runoff toward lateral flow is real
model behavior in these inputs. This audit establishes its accounting and finds
small hourly allocation loss; it does not independently calibrate either mode
or declare the size of the process difference scientifically correct.

## Evidence, diagnostics and limits

Eighteen complete watershed configurations were executed: ten OFE/mode cases,
six short-channel/tributary/cascade cases and two matched side-placement controls.
Three additional hillslope runs test nonzero initial groundwater. Every paired
watershed case uses release 261021 hillslope and watershed binaries. Native
observations cover ten watershed configurations, and hourly infiltration probes
cover three OFE layouts. All observed cases pass baseline/off/on byte parity for
scientific outputs; no simulation equation or vendored binary was changed.

`diagnostic-controls.json` records a balanced hand-computable control and detected
duplicate transfer, missing outflow, wrong area factor, reversed storage sign
and one-day shift. Transfer tolerances derive from WAT fixed/scientific formats,
PASS significant digits and binary32 scaling; they are not fitted to physical
residuals. Retained full ledgers include signed, absolute and worst-step errors,
so cancellation cannot masquerade as agreement.

Receipts: `release-matrix-audit.json`, `observer-v2-audit.json`,
`network-observer-audit.json`, `side-observer-audit.json`,
`hourly-observer-audit.json`, `initial-groundwater-audit.json` and
`flat-hydrograph-system-audit.json`. `retained-evidence.json` hashes external ledgers,
observations and manifests. `source-map.md` and `commands.md` document semantics
and reproduction. Large outputs remain under
`/workdir/watershed-physical-water-audit-20261021`; donor decks remain read-only.

Limits: controlled constant-width ordinary hillslopes; no contour/variable-width
certification, positive tile-flow validation, impoundment validation or independent
field calibration. Zero initial groundwater and zero deep-seepage coefficient
apply to the main matrix; the targeted initialization check explicitly varies
initial storage. Complete atmospheric/soil/groundwater/channel initial stores
and integrated domain closure are not claimed. The private donor input fixture
is supplementary scientific evidence, not a new mandatory release gate.
Repairs need portable bounded reproductions and fresh paired replay acceptance.

The audit identifies defects without fixing or deploying them. The correct
closeout is **diagnosis complete; watershed correctness not certified**.
