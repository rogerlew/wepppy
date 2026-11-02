# R05 ET demand, carried growth stress and source history

Read-only investigation, 2026-11-01. No source changes or model executions. The mirrored Denver witnesses establish a shared call-gate/state-assignment discontinuity. They do not establish a scientifically accepted replacement for growth stress. Release HOLD remains.

## Actual source contract

Native references below use canonical final source `a8e008135f82e6a071acd836672d829e8e9e8e8d`. Private `R05-et-stress-contract-history-v1/source-bindings.json` binds inspected files and their r4/final Git versions; no legacy listings are reproduced here.

| Stage | Meaning and ownership | Source reference |
| --- | --- | --- |
| Method selection | Both daily and hourly callers select EVAP when `iflget=1`, otherwise EVAPPM. | `watbal.for:490`; `watbal_hourly.for:613` |
| EVAP demand | EP is EO scaled by LAI below LAI 3, otherwise EO; this demand formula does not multiply by EVAPPM's root-zone availability factor. | `evap.for:583` |
| EVAPPM demand | Reference ET `etorc` is combined with canopy coefficient `kcbcon` and root-zone availability factor `etks`. EP is their product converted from mm to m. TAW, RAW and current rooted-layer stock determine etks; this EP is already soil-water limited. | `evappm.for:263`, `298`, `382–428`, `460` |
| Growth | PTGRA/PTGRP or RANGE reach GROW before that day's SWU call. GROW uses the smaller of the carried water- and temperature-stress complements. | `watbal.for:881–918`; `watbal_hourly.for:1002–1039`; `grow.for:395–414` |
| SWU canopy priority | Subtract available canopy interception from EP first, retaining unused canopy as PINTLV. Only residual EP requests root withdrawal. | `swu.for:110–122` |
| SWU root stress | Actual root uptake divided by residual requested uptake becomes watstr. Root uptake is further limited by layer availability and crop tolerance; thus this is a second limitation after EVAPPM's etks. | `swu.for:122–188` |
| SWU zero residual | If canopy covers the request, residual EP is zero and watstr becomes 1 even with zero root withdrawal. Reported EP then includes consumed canopy water. | `swu.for:189–207` |
| Skipped SWU | If incoming EP or root depth fails the positive call gate, the canopy-present fallback updates canopy carry/EP but does not assign watstr. The no-canopy fallback instead sets EP 0 and watstr 1. | `watbal.for:916–936`; `watbal_hourly.for:1037–1057` |

Consequently, **zero EP does not universally preserve stress**: preservation is specific to the canopy-present fallback. Nor does zero EP identify zero atmospheric demand. It can arise from the reference demand, canopy coefficient, root availability factor, or their arithmetic. A zero residual after canopy evaporation is another distinct state. EP reported after SWU is neither exclusively root transpiration nor the original atmospheric request.

The source labels watstr as a growth parameter ranging from 0 to 1 (`cwater.inc:65`) and initializes it to 1 (`inidat.for:478`). GROW treats it as the complement of stress. SWU's description of its ratio as actual/potential uptake is only locally accurate for its received residual request: under EVAPPM, the denominator is already availability-limited and reduced by canopy water. No inspected authoritative local document reconciles that denominator with an overall plant physiological stress ratio. That missing agreement is a contract gap, not permission to replace watstr with etks, multiply factors, or reset it unconditionally.

## Observed relevance and limits

The hash-bound [Denver mechanism readback](R05-denver-et-mechanism.md) shows both directions of the same year-7/day-130/OFE-3 gate. Inbare baseline receives EP 0 and retains opening watstr 0; candidate receives approximately 3.617e-11 m, enters SWU, has zero root debit and receives watstr 1. Outunrut reverses the lanes: baseline receives approximately 1.573e-10 m and reaches watstr 1, while candidate EP 0 retains 0. Canopy interception is present. Same-day growth uses the old stress in both lanes; next-day growth responds to the changed carry. Subsequent millimeter-scale visible water gaps predominantly reflect changed canopy carry and later uptake, as separately joined in that readback.

These observations confirm the discontinuous assignment mechanism and downstream amplification. They do not identify the first global perturbation, make the two cases identical-state counterfactuals, or prove that either final stress value is physiologically correct. Additional initialized EVAPPM operands are required to distinguish atmospheric demand from availability-limited demand at the actual events. Existing source-operation observations must also retain the earlier EVAPPM plant state versus the later post-growth roots used by SWU.

The retained [Flagstaff readback](R05-flagstaff-mechanism.md) independently establishes snow exhaustion/support/runoff branch amplification. It is not, by itself, evidence for this ET stress contract. Any secondary Flagstaff ET gate must be admitted with its own exact demand/canopy/root/stress epochs before extending the Denver diagnosis to it.

## History and local authority

- The imported Git baseline `c70bad57b704b0b607ee30cc251439b9bbf8d0ed` (2020-08-25) already contains SWU's policy, the WATBAL canopy-present fallback and EVAPPM's availability-limited demand. SWU has no subsequent source commits in this repository. Embedded 1993/2003 comments describe canopy handling and a harvest-day workaround; those annotations are historical attribution, not independently verified original design rationale.
- The September 2020 EVAPPM changes `87fab30fd` and `2e4957256` affect a startup message/encoding; September 2021 `57943e529` suppresses that message. They do not introduce this stress coupling.
- `362feb427` (2026-04-28) adds explicit protection for the nonpositive TAW-minus-RAW denominator. `631aed1d1` (2026-10-30) corrects root-stock integration and removes re-addition of already allocated FIN. Both precede r4. Neither establishes a new canopy-to-growth stress agreement.
- EVAPPM, SWU and GROW are byte-identical between r4 `b01a739957bef5aacf35b4a89bc13eddc9d94804` and final `a8e008135f82e6a071acd836672d829e8e9e8e8d`. The daily/hourly call-gate policy is also retained. R05 exposes sensitivity in a shared pre-existing consumer policy; it does not show that r5 introduced that policy.
- Native `docs/specs/source/evappm.for.md` establishes current-stock/root-integral ownership and explicitly leaves alternative EVAP unchanged. Native `docs/science-contracts/contracts/SC-EVAP-001.md` remains **open/proposed, version 0**. Its boundary guidance concerns denominator collapse and inactive crop/root classification; it explicitly withholds authority for source promotion. It does not resolve SWU-to-GROW stress semantics.

## Disposition

Confirmed: both water-balance implementations share a path-dependent stress assignment, and EVAP versus EVAPPM deliver differently conditioned requests to the same SWU consumer. An unconditional interpretation of watstr as actual/unconstrained potential transpiration is unsupported. The mirrored observations establish material consequences of the branch boundary.

Unresolved: the intended physical treatment of positive atmospheric demand with depleted roots but available intercepted canopy water; how growth stress should relate to the already reduced EVAPPM demand; and whether the preserved prior stress in the harvest fallback was intended outside its original context. Existing source comments even question the no-ET neutral assignment; they cannot settle the alternative policy.

The next bounded decision needs the already planned demand-factor witnesses, exact root/canopy consumption and carried-state epochs, followed by an explicit scientific contract for these distinct states. Preserve the baseline behavior as evidence during that review. No epsilon, new threshold, blanket reset, crop recalibration, or ET-method substitution is recommended by this investigation.
