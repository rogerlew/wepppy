# Independent native water-accounting review

Status: source audit and scalar-probe prerequisites; no build, model execution,
source change or new physical correction. Source root is
`/workdir/wepp-forest-release-20261009/src`. Exact identities are retained in
[native-water-science-source-bindings.json](native-water-science-source-bindings.json).
Line references below apply to those files, not earlier instrumented copies.
The reviewer is an independent AI agent; this is not external scientific peer review.

## Finding

A UL-only replacement needs more than the prior 586-layer dry/field-capacity
ordering check. UL enters drainage denominators, plant stress, fine-grid frost
capacity and conditional overflow rules. The native model deliberately permits
some ice-adjusted lower-layer excess when incoming water is negligible. Those
choices require explicit interpretation before claiming a universal capacity
invariant. No annual sediment cause follows from this audit.

## Stocks, coordinates and units

All depths below are meters of water per unit ground area unless identified as
soil thickness; volumetric fractions are dimensionless. `DG` is layer soil
thickness, `THETDR` the corrected dry/wilting reference, `POR` air-corrected
fine-earth porosity, and `CPM` the native mass/density-derived fine-earth volume
share. SCON is the active CPM writer (`scon.for:233–235`). Multiplying POR globally
would apply CPM twice in initialization and infiltration.

For a coherent frozen state, let `F` be frozen soil thickness, `d=THETDR`, and
`h=DG`. The reporting reconstruction is liquid `L=ST+d*(h-F)` and ice water
equivalent `I=FRZW+d*F`; total `T=ST+FRZW+d*h`. `FRZW` is adjusted ice, not absolute
ice, and `ST` includes liquid held in the frozen zone. `NWFRZZ` must not be added
again to ST. These definitions come from `frwatc.for:104–132` and
`watbal_hourly.for:1074–1082,1143–1153` (daily equivalents957–961,1023–1033).
In the unfrozen limit, `T=ST+d*h`; the common-coordinate headroom identity is
`UL-ST=(UL+d*h)-T`. A change of coordinate at fixed absolute stock moves both
ST and UL; it does not independently free physical pore space.

The fine-grid stock to compare independently is the sum of `SLSIC` plus
`SLSW*(fine thickness-SLFSD)` plus coarse-layer `NWFRZZ`. `SLSIC` is water-equivalent
ice depth, `SLSW` an unfrozen volumetric liquid fraction, and `SLFSD` frozen soil
thickness. FRWATC ignores unfrozen fine supports at or below 0.001 m, carries
water shortages through `WLCK`/`LACKW`, and has additional small-change thresholds.
Consequently the algebraic coarse identity does not prove a conservative
fine-to-coarse round trip across threshold crossings. Count residuals explicitly.

## Actual writers and consumers

| Owner and source lines | Write/read and clock | Accounting consequence |
| --- | --- | --- |
| `inidat.for:563–564,1141`; `tilage.for:519,610–664,673` | Zero adjusted ice/new frozen-zone liquid; initial profile remapping writes POR, dry/FC fractions, geometry and ST while TILFLG=0. | TILAGE initially uses SAT*POR without CPM. This is not a demonstrated daily reset: CONTIN444 calls TILAGE before SCON491; TILFLG is then1. Keep this predecessor in an initialization probe, not a claim of later water creation. |
| `scon.for:233–235,296–345,510–518` | Computes CPM and air-corrected POR; rock-corrects retention fractions then guards them; writes initial ST and UL for each layer. | Absolute initial liquid uses SAT*POR*CPM, while absolute UL uses POR. SAT is shared across layers and may be raised to the dry floor; do not reset SAT per layer in a profile reproduction. |
| `watbal.for:258–314`; `watbal_hourly.for:262–318` | Initialization repeats UL and computes FC and HK. FC=(THETFC-THETDR)*DG, with no OFE dimension in this common array. | Preserve OFE execution context. HK uses log10(FC/UL); the positive-ratio guard does not exclude ratio1 or ratios above1. |
| `soil.for:579–582,822`; `infpar.for:247–296,576–586,606–609` | SOIL updates POR and invokes INFPAR. INFPAR reads ST, ice-adjusted UL, current POR and initialized CPM; writes AVSAT/DTHETA and conductivity proxies. | Product of weighted mean POR and mean CPM differs from mean(POR*CPM). The .98/.99 AVSAT caps do not remove water from ST. Do not use them as conserved fluxes. |
| `grna.for:196–204,224–245` | Saves current local first-two-layer ST in STOLD; combines saved upstream STOLD with upstream UL and live FRZW for connected storage. | This is an infiltration/storage limiter, not an ST writer or instantaneous complete-profile stock. Snapshot owner and clock matter; mixed upstream clocks must remain visible. |
| `watbal.for:443–460,481–492`; `watbal_hourly.for:483–579,597–616` | Adds/removes incoming water; invokes PURK, then ET. Hourly version loops24 steps and calls ET at the last step. | Hourly negative input uses a stock-removal path. Full accounting must include exact accepted FIN and upstream return/lateral inputs, not precipitation alone. |
| `purk.for:148–194`; `perc.for:135–154,227–228` | Bottom-up PURK transfers ST between layers; PERC computes SEP from saturation proxies and conductivity. | Internal percolation cancels between layer stocks. Only bottom seepage is external. PERC computes a daily-equivalent rate-depth, PURK divides by UI_LFTSTP in hourly mode; do not divide twice. |
| `evap.for:568–666`; `evappm.for:455–523`; `swu.for:163–200` | Evaporation and plant extraction reduce ST; interception/residue terms are separately handled. SWU uses UL to set water stress. | A capacity change also changes extraction response. EP/ES can include intercepted/residue sources; soil-stock closure needs source partition, not indiscriminate subtraction of total ET. Small ST floors/zeroing need residual reporting. |
| `watbal.for:500–520,794–835`; `watbal_hourly.for:623–643,899–957` | Redistributes lower-layer excess upward; removes top excess to SURDRA and adds surface return to RUNOFF, scaled by length where applicable. | Active code exports return water despite obsolete comments suggesting discard. The lower-layer limit depends on FIN; surface removal uses an ice-adjusted limit. Hourly top removal has a1e-6m threshold; daily uses strict positive excess. |
| `watbal.for:530–546,565–765`; `watbal_hourly.for:652–672,690–884` | Computes drainage threshold DRFC, lateral flux and ST debits; accumulates SBRUNF and hourly return arrays. | DRFC adds entrapped-air allowance to FC. Hourly lateral conductivity uses denominator UL-DRFC; it needs its own feasibility gate. Unremoved requested lateral flux is subtracted back from the output accumulator. |
| `drain.for:119–144,195–205,217–271` | Computes tile-drain demand; debits accessible ST and corrects DRAINQ for unmet demand. | DRFC here uses COCA of layer1 for every layer, unlike per-layer COCA in water balance. DHOURS scales tile flux (1 hourly,24 daily). Preserve this actual distinction before judging it. |
| `frwatc.for:89–137,139–265` | Converts frost-grid stocks to coarse ST/FRZW/SOILW/YST and maps changes in ST back into fine-grid liquid/NWFRZZ. | Thresholds, dry floors, carried shortages and frozen-zone capacity must be observed separately; round-trip conservation is not established by a coarse identity. |
| `frostn.for:249–336,660–686`; `frzng.for:155–161,205–219,556–619`; `frznw.for:123–164` | Initializes fine states; freezes water and transfers NWFRZZ to SLSIC; calls FRWATC at designated boundaries. | FRZNW and FRZNG compare UL scaled to frozen support with absolute fine-grid ice. That mixes reference conventions relative to coarse FRWATC; a dry-reference invariance probe is necessary before lowering UL. |
| `mlttp.for:444–457,560–594`; `mltbtm.for:415–428,535–561`; `watdst.for:160–277` | Thaw converts SLSIC to SLSW, redistributes NWFRZZ and fine-grid liquid. | Include liquid in frozen zones and moving support in each stock sum. UL-based fine-grid available space again subtracts absolute ice. Freeze/thaw is not simply ST+FRZW exchange at fixed support. |

Execution order is also evidence: CONTIN initialization is SCON, SOIL, WATBAL
(`contin.for:484–499`). Daily SOIL/INFPAR precedes WINTER (`811,848`), with later
WATBAL (`1091`). WINTER calls FROSTN by hour (`winter.for:340`); FROSTN exports at
hour24 or the thaw flag (`686`). WATBAL dispatches to the hourly implementation
only when UI_RUN=1 (`watbal.for:252–255`). Plant uptake SWU occurs later in WATBAL (daily916/hourly1037), after the overflow
block; an overflow-only residual cannot certify the final daily stock. The current source map must not inherit
line numbers or simultaneous-clock assumptions from earlier observed studies.

## Counterexamples and prerequisites

1. **Ordered limits do not ensure a valid lateral denominator.** As a synthetic
   exactly representable example, DG=1, POR=.5, CPM=.5, THETDR=.0625,
   THETFC=.1875, COCA=.9375 gives hypothetical rock-adjusted UL=.1875,
   FC=.125 and DRFC=.1875. Dry < field capacity < absolute effective ceiling
   (.25) holds, yet UL-DRFC=0. At bottom-layer ST=DRFC the hourly branch admits
   the0/0 expression. Native UL=.4375 avoids that denominator. This is a
   prospective expression-domain counterexample, not an observed history or
   executed candidate. A separate FC/UL=1 case targets HK's logarithm.
2. **No-input frozen excess is intentionally treated differently.** With two
   layers, UL=(.03,.03), FRZW=(0,.01), ST=(.029,.025), FIN=0, lower-layer ST is
   below UL so no upward transfer occurs, although ST+FRZW exceeds UL. With
   FIN=2e-6 and otherwise identical pre-overflow state, .005m moves upward and
   .004m leaves the surface. Both preserve summed stock plus exported flux.
   FIN is the branch selector here, not an additional injected stock in this
   isolated block. This disproves treating ice-adjusted capacity as an
   unconditional native invariant; it does not prove an erroneous mass balance.
3. **Overflow clocks differ at small excess.** Surface excess5e-7m is exported
   by daily WATBAL but retained by hourly WATBAL. Preserve the threshold rather
   than hiding it with a post-hoc acceptance tolerance.
4. **Frozen reference invariance needs a separate test.** Coarse occupied space
   subtracts adjusted FRZW; fine-grid routines subtract absolute SLSIC from a
   scaled UL. At fixed physical water and support, a dry-reference change can
   affect these proxies differently. No repair formula is endorsed here.
5. **Additional existing nonconservative-looking operations are risks, not
   established event defects.** ST tiny-value resets, carried shortages at the
   last fine layer, and1mm support truncations require branch-level residual
   observations. Do not infer their aggregate effect from source alone.

## Precise minimum next scalar probe

Freeze source hashes and exact slice bytes before compiling an isolated harness.
Keep native REAL order, fixed-form continuation and labels. Extract source
unchanged; no public native source excerpts. A wrapper may supply arrays and
observations but must not replace the arithmetic or silently supply missing
state. Pin compiler and PATH, includes, build inputs, flags and output hashes.

| Probe | Contiguous slices in current source | Setup and expected check |
| --- | --- | --- |
| Initial coordinates | `scon.for:510–518`; separately `tilage.for:615–620` | One layer with explicit SAT/POR/CPM/THETDR/DG and BD for TILAGE. Include CPM1 and high-rock cases; report TILAGE as predecessor, not equivalent finalized SCON. SCON stock+reference matches SAT*POR*CPM*DG up to native rounding/floors. |
| Initialization and drainage domains | `watbal_hourly.for:290–298`; optional complete HK IF305–311; DRFC652; lateral expression768–769 with its761 predicate explicitly recorded | Native UL/FC ratio plus separately labeled hypothetical capacity operands. Supply every array/index. Include ordered binary example above, zero-rock null, ratio1, and near-boundary cases. An observational stub for WEPP_OBSERVE must be declared if HK IF is extracted. No fabricated hydraulic outcome from inadmissible domains. |
| Lower-layer and surface overflow | Daily `watbal.for:500–520` then794–821; hourly `watbal_hourly.for:623–643` then899–931 | Two layers, IPLANE1, NSL2, II1, initialized SURDRA/return arrays/NORUN; FIN0 versus2e-6, unfrozen and frozen states, near top threshold. Retain per-layer before/after and surface increment. Internal transfer conserves sumST; surface removal equals stock loss. Record that intermediate drainage/ET are excluded. |
| Frozen mapping, later gate | Full `frwatc.for` with actual includes and explicit fine-grid state, not a rewritten identity | NFINE, SLSW, SLSIC, SLFSD, NWFRZZ, YST, ST, geometry and dry reference; both directions and coherent zero/partial/full frost, supports just below/above1mm. Compare fine stock, coarse reconstructed total and carried deficits at each call. This needs a separate reviewed declaration; it is not covered by overflow slices. |

The first three are bounded arithmetic/transfer observations only. They neither
validate PERC/tile/lateral/ET coupling nor the complete frost energy model.
Whole-routine freeze/thaw and later full-model experiments remain separate gates.
No production behavior, global POR correction, dynamic-porosity refresh or fitted
coefficient follows from passing them.
