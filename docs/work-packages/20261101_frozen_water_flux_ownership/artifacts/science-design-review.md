# Accepted flux ownership: independent scientific design review

Design accepted for preparation of a separately prereviewed observational build. Exactly the three previously selected histories/windows remain sufficient for this bounded ownership question. No implementation, compilation, native execution or prior-root write was performed by this reviewer. An observation result requires seven-output, complete frost-trace and filtered previous-BPO parity; source reasoning alone does not identify an executed producer.

## Stores, units and clocks

All native water depths below are meters. ST is coarse liquid above its dry reference, FRZW is coarse ice minus dry water on frozen support, and YST is the last mapping reference. At synchronized geometry, absolute profile water is sum(ST+FRZW+THETDR*DG). Record dry reference, geometry, frozen support and FRZW with each ST profile; use an ST-only delta as total water change only after verifying those other terms unchanged. Fine states are an alternate representation and must not be added as a second reservoir.

RESINT is the residue-interception quantity consumed by ET; PLAINT and PINTLV participate in canopy evaporation and its remainder. ET-return EP is not yet accepted root uptake. Output categories differ between ET methods, and final daily output occurs after additional uptake handling. Preserve exact year/day/OFE/hour and actual method/call identity. A potential or stale initialized output is not an accepted flux simply because it is finite.

## Method-specific ET accounting

EVAP lines 568–613 first includes residue in evaporation demand, assigns ERES, then separates it from ES and clears nonnegative RESINT. If the residue amount exceeds evaporative demand, surplus is added to top ST and ERES adjusted. EVAP lines 633–667 deplete soil and subtract unmet demand from ES/ET. On supported nonnegative residue paths, return ES is soil evaporation and ERES is the separately represented residue component.

EVAPPM lines 435–475 includes residue in ES demand, subtracts RESINT from the amount to remove from soil, and clears RESINT. A residue surplus can likewise enter top ST. EVAPPM lines 492–524 subtract unmet soil demand from ES/ET, but do not separate residue into ERES. This routine has no ERES assignment; the hourly caller initializes ERES to zero. Return ES therefore includes the residue contribution. Treating it as soil-only can falsely infer missing water or double-count residue.

For profile coarse change ΔS across the actual ET call and residue change ΔR, test the following bookkeeping identities under their valid branch conditions, retaining arithmetic/clamp discrepancy explicitly:

- EVAP: ΔS + ΔR + ES_return + ERES_return.
- EVAPPM: ΔS + ΔR + ES_return.

An ET call can increase soil ST by returning surplus residue. That is an internal transfer, not negative atmospheric evaporation. ES_return alone cannot measure soil removal on the PM path. Record residue before and after, return ES/ERES/EP/ET, method, and all profile snapshots. Negative residue inputs or component/geometry anomalies require separate flags; do not silently apply the nonnegative-store identity to them. These identities test reported categories against assigned stocks, not field accuracy of the ET model.

## Plant uptake after hourly stages

WATBAL_HOURLY lines 1084–1103 selects SWU only when EP and root depth are positive; alternative branches adjust canopy-related output or zero EP. Observe the complete caller selection, including explicit no-call outcomes, not just SWU returns. SWU lines 111–120 first allocates intercepted canopy water. Lines 144–187 cap per-layer uptake by available water, apply a small-uptake floor, reduce ST, apply the ST floor, and replace EP with accumulated root uptake. Lines 197–203 add the accepted canopy part back into EP.

For the ordinary nonnegative interception path, accepted canopy evaporation at return is PLAINT minus PINTLV_return, and root uptake is EP_return minus that term. Compare root uptake against the independently observed coarse-profile reduction across SWU, with rounding/floor corrections separated. Record PLAINT/PINTLV on both sides and do not assume canopy acceptance equals initial PLAINT. If exact accepted per-layer U is logged, emit it only inside executed initialized iterations. SWU local XX is initialized only when its post-interception EP is positive; logging XX at every return is unsafe. Some U entries are not initialized on all root-depth paths. Missing execution must be marked unavailable, never replaced with guessed zeros.

## Minimal ordered observation boundaries

| Boundary | Minimum state/operands | Scientific role |
| --- | --- | --- |
| Actual ET pre/post, final hour only | Full coarse profiles; method; RESINT, ES, ERES, EP, ET; relevant actual-call flag | Attribute assigned soil/residue change to that ET call without treating EP as uptake |
| Post-ET to post-capacity redistribution | Full profiles before/after; branch context | Separate interlayer redistribution, whose profile sum should cancel subject to arithmetic |
| Actual DRAIN pre/post or explicit skipped-call marker | Full profiles; returned DRAINQ; running tile total before/after | Distinguish reported accepted drain depth from potential conditions and daily accumulator |
| Lateral block pre/post | Full profiles; hourly lateral field and daily SBRUNF before/after | Compare accepted lateral amount after leftover-demand correction, not initial LATQCC |
| Surface block pre/post | Full profiles; hourly surface amount and SURDRA before/after | Separate final overflow from cumulative reporting |
| End-of-hour and post-hourly uptake pre/post | Full profiles; actual SWU/no-call branch, EP, PLAINT, PINTLV, root depth | Join the final coarse state to the subsequent fine reset and distinguish transpiration from demand |

Retain existing BEFORE/PURK and ALLOC/SEEP records; they already bracket allocation/percolation. Do not add repeated SEP operands as independent exports. DRAIN is conditional near lines 703–706. Lateral lines 866–919 initially accumulate a proposed LATQCC, then subtract any unavailable remainder from both daily SBRUNF and the hourly field. Therefore early LATQCC is not the accepted amount. Surface and cumulative totals similarly need explicit clocks. Hours without ET still need ordered stage boundaries or an explicit no-call record so absence is testable.

The high case must retain its intervening input and gross/net distinction. Its previously observed 0.400001183 mm top input is not part of the final-hour soil-removal amount. Extend the existing clear→coarse stages→reset joins without renaming endpoint depletion as gross ET or counting a representation mismatch twice.

## Precision and invalid-state policy

EVAP/EVAPPM and SWU floor ST below 1e-10 m to zero; SWU also floors very small U. Lateral assignment can instead raise a small ST to 1e-10. These are native assignments distinct from double reader roundoff. Prefer recording actual pre-floor/post-floor values at executed floor sites if exact residual attribution is needed; keep original operation order. A small accepted flux can coexist with a slightly larger stock removal due to the final ST floor.

Use separate budgets: double reconstruction based on sums of absolute primitive terms; native REAL arithmetic based on actual operation counts and operands; explicit measured threshold changes where observed. Do not use a relative tolerance on a near-zero cancellation or tune a fixed tolerance after seeing results. A bound of number-of-floors times 1e-10 applies only to nonnegative pre-floor stocks and excludes native arithmetic rounding; negative states must be flagged instead of being absorbed into that bound. A mismatch outside reconstruction/declared rounding remains a finding, not a reason to alter equations.

Snapshot availability must follow initialized paths. Newly introduced observer locals must not collide with native COMMON members. Require unique complete three-OFE/two-day/hour/layer coverage, actual ET method and SWU selection coverage, finite values, explicit negative/component/support flags and rejected malformed records. Exact source/helper/runner/reader/compiler/runtime/input bindings and independent implementation/scientific prereviews must precede the three runs. No production defaults, formula correction or expanded sensitivity sweep is approved here.

## Exact source bindings

Private source root is the accepted previous build identified above. Line references refer to these files; no native source is published in this review.

- `watbal_hourly.for`: `dbfeed35c303c54037d130bc62852b59fcd76946e62addc30ff5ed5910abf986`.
- `evap.for`: `6bf78e113cc413131f3feb3516070cf233c6c16e3c0f86b3e78eaa4ba86afdbc`.
- `evappm.for`: `bfd6607f8a0033b5b779bb1830cddda52652316b1e77fafe9640b4c691647d23`.
- `swu.for`: `060b0ea0710ffba720624bb595eb63df0010dc665b71a2287c4e21be9e60f901`.
- `frwatc.for`: `f580544b80ef091edd87478ef8fb5f0a75632261c36c0d5828a28b2438f366ed`.

Writer status: clear. Only this new public review artifact was written.
