# Independent scientific design: full unchanged FRWATC

Disposition: finite design proposed for a separate frozen declaration and
implementation prereview. No execution/build or native-source change by this
reviewer. This is a mapping experiment, not a frost-energy simulation, hydraulic
capacity correction or complete water-balance validation. Preserve previous
studies. Do not silently repair a failing state or convert a measured residual
into an invented flux.

## Exact routine and operands

Use the complete unchanged `frwatc.for`, including both WBTOFS branches. It has
no external routine calls. Snapshot its five parameter includes (`pmxtil.inc`,
`pmxtls.inc`, `pmxpln.inc`, `pmxhil.inc`, `pmxnsl.inc`) and seven common includes
(`cstruc.inc`, `cupdate.inc`, `cwint.inc`, `cflgfs.inc`, `cpfrst.inc`, `csaxp.inc`,
`cwater.inc`). Compile the separate driver against those exact same declarations;
do not resize COMMON arrays, silently change precision or substitute a Python
mapping. The companion [source bindings](frozen-design-source-bindings.json)
identify the reviewed files. Pin compiler, PATH, flags, command, include search
order, source/object/binary hashes, stdout/stderr and each process result.

Set IPLANE=1, NSL(1), and NFINE(i) explicitly; valid fine counts are1–10. For
every active coarse layer initialize DG, THETDR, UL, ST, YST, FROZEN, FRZW,
NWFRZZ, SOILW and SAXFC. For every active fine layer initialize SLSW, SLSIC
and SLFSD. Initialize unused active-array slots deterministically and retain
unchanged sentinels outside active support. Set bookkeeping YEAR/SDATE and
other driver-observed values explicitly. No unavailable external history should
be represented as a physically derived state. FRWATC does not read POR/CPM:
retain any nominal capacity used to construct UL as driver provenance only.

Each fixture starts in a fresh process or completely resets all shared state.
No state may leak between cases. Direction1 starts from an independently
constructed coherent fine/coarse pair, not from direction0's potentially
lossy output. Subsequent calls are separate observation checkpoints.

## Independent stock definitions

For layer i, let h=DG, n=NFINE, f_j=SLFSD_j and u_j=h/n-f_j. Use only physically
valid0<=f_j<=h/n and positive h. Absolute fine-grid liquid is
Lfine=sum(SLSW_j*u_j)+NWFRZZ; ice water equivalent is Ifine=sum(SLSIC_j).
Tfine=Lfine+Ifine. NWFRZZ is liquid water in the frozen zone, already included
in the corresponding coarse ST; do not add it twice.

For coherent coarse state F=sum(f_j), d=THETDR:

- ST=Lfine-d*(h-F), YST=ST before a water-balance increment.
- FRZW=Ifine-d*F; adjusted FRZW need not be interpreted as absolute ice.
- Lcoarse=ST+d*(h-F); Icoarse=FRZW+d*F.
- Tcoarse=ST+FRZW+d*h. SOILW is an additional independent output, not an alias
  to assume equal to Lcoarse when supports are skipped.
- A direction1 input delta is a declared external water-balance stock change:
  set ST=YST+delta before the call. Expected final fine stock is initial
  Tfine+delta. FRWATC itself does not receive or emit a routed external flux.

Record Rmap=Tcoarse_after-Tfine_before for direction0, Rfine=Tfine_after-
Tfine_before for its own fine-state mutation, and Rback=Tfine_after-
(Tfine_before+delta) for direction1. Also record SOILW-Lcoarse, ice changes,
per-layer versus profile totals, and final minus requested ST after a subsequent
return mapping. Report actual before/after states at every call; no aggregate
absolute-value balance that can hide offsetting errors.

Compute the independent reference from emitted native REAL operands using
explicit float32 operation order where matching expressions, and use double
summation for physical stock diagnostics. Retain actual geometry residual
sum(u_j)+sum(f_j)-h. Print enough digits to round-trip native REAL values.
Separate rounding residual from deliberate thresholds; a single broad closure
bound must not absorb the latter.

## Coherent base states

The following are synthetic finite states, not samples from prior histories.
One coarse layer has h=.1m, n=2, d=.05, nominal initialized effective pore
fraction p=.45, UL=(p-d)*h=.04m and SAXFC=.25. SAXFC is an absolute volumetric
liquid threshold, not FC depth. Use the analytically reconstructed coarse
variables above, with final native REAL operand values recorded.

| Base | Fine frozen thicknesses f | Fine SLSW | Fine SLSIC | NWFRZZ |
| --- | --- | --- | --- | --- |
| U: unfrozen | (0,0) | (.2,.3) | (0,0) | 0 |
| P: partial | (.025,.025) | (.2,.3) | (.00625,.00625) | .002m |
| F: full frost | (.05,.05) | (.2,.3), physically unsupported values retained | (.0125,.0125) | .002m |

Absolute liquid/ice amounts are nonnegative, initial stock is below p*h, and
ice plus NWFRZZ fits nominal frozen support. Unsupported SLSW at full frost is
not additional water. All proposed direction1 targets below remain nonnegative
and below the nominal total capacity. Do not silently replace p with POR*CPM
inside native source; it is only a coherent fixture construction value.

## Finite matrix: 29 isolated fixtures

A call sequence1→0 means snapshot before1, after1 and after0; a sequence0→0
similarly keeps both outputs. Each fixture has fresh initial state.

| IDs/count | Fixture and sequence | Independent expectation or specifically measured risk |
| --- | --- | --- |
| A-U/P/F (3) | Base U/P/F; call0 | Ordinary aggregation should match fine stocks within evaluated REAL rounding. Full frost liquid is NWFRZZ, not SLSW*h. |
| B-U/P/F (3) | Base U/P/F; delta0; calls1→0 | Identity controls: no physical change. YST/ST agree before mapping. |
| C-U/P/F± (6) | Each base with delta+.001 or-.001m; calls1→0 | Tfine change equals declared delta. Partial/full negative change first drains NWFRZZ; no ice phase conversion is expected. |
| D-P-003/-011 (2) | P with delta-.003 and-.011m; calls1→0 | Larger drainage exercises NWFRZZ exhaustion, SAXFC-first removal and subsequent redistribution; second case exercises fine-layer dry-floor carry while profile water remains available. Compare profile and layer residuals, not just finite values. |
| E-P± (2) | C-P± physical stocks repeated at d=.10; calls1→0 | Coordinate control: same SLSW/SLSIC/NWFRZZ/SAXFC and physical delta; reconstruct ST/YST/FRZW and UL for new d. Stay above both dry floors. Fine outcomes should agree with C-P± apart from REAL rounding. |
| F-u-low/equal/high (3) | h=.1,n=2,d=.05,SLSW=(.2,.2), each unfrozen support u=.0009,.001,.0011 respectively; f=.05-u, SLSIC=.25*f,NWFRZZ=0; call0 | Threshold characterization: accepted support uses strict u>.001 after native subtraction. For skipped support, Tcoarse-Tfine is approximately sum((d-SLSW)*u), not zero. SOILW excludes its entire liquid, producing a different reporting residual. Record actual computed u, not nominal label. |
| G-u-low/equal/high (3) | Same support geometry as F, but NWFRZZ=(p-.25)*sum(f), so frozen support has zero spare capacity; delta+.00002m; calls1→0 | All targets still fit available unfrozen capacity. With no frozen spare and residual above1e-5, direction1 spreads delta by total unfrozen thickness; fine supports at/below1mm skip updates. Observe unapplied requested liquid explicitly. Exact-boundary classification follows native operands. |
| H-F-low/high (2) | h=.1,n=1,SLSW=.2,d=.05,f=.0009 or.0011,SLSIC=.25*f,NWFRZZ=.00005; calls0→0 | Both initial states fit frozen pore support. Below1mm, direction0 assigns ST/SOILW including NWFRZZ then clears NWFRZZ; first fine/coarse discrepancy and second mapping loss are separate observations. Above1mm control retains it. |
| I-delta-small/middle/large (3) | Base U; delta5e-8,5e-7,2e-6m; calls1→0 | Resolves two gates: abs(delta)>1e-7 and abs(varsw)>1e-5. Small changes may remain only in requested coarse ST and disappear on return mapping. Do not label that residual a runoff flux. |
| J-zero-U/F (2) | U with all SLSW=d,NWFRZZ0; F with NWFRZZ0, original ice; reconstructed ST=YST=0; calls1→0 | Explicit zero-ST branch control. Unfrozen liquid remains dry-reference water; full-frost liquid is zero and ice remains. |

The nominal equal1mm case is a branch-boundary probe, not guaranteed to equal
the literal threshold after float32 subtraction. Optionally add an exactly
representable adjacent-native-float pair only through an amended declaration;
do not move nominal geometry after observing the result.

## Source-based expected counterexamples

Direction0 (`frwatc.for:110–124`) skips thin unfrozen supports but reconstructs
FRZW using total frozen thickness (`127–132`). This yields different fine,
coarse-reconstructed and SOILW stocks near the threshold even for positive,
physically fitting inputs. Direction0 then clears NWFRZZ for F<.001 **after**
assigning coarse liquid (`130–134`), motivating H's two checkpoints.

Direction1 computes its uniform liquid change over total unfrozen support
(`225–229`) but applies it only on fine supports>.001 (`235–259`). This is
why G must eliminate frozen spare capacity: otherwise the frozen allocation
(`198–219`) can consume the intended increment and fail to exercise the target.
The remainder<1e-5 shortcut in that allocation can add liquid to NWFRZZ beyond
the immediately computed spare; this separate capacity-allocation edge is not
covered by the proposed G increment and must not be claimed tested.

Dry-reference invariance is specific: at fixed F and absolute water, change
ST/YST by -delta_d*(h-F), FRZW by -delta_d*F, UL by -delta_d*h. In FRWATC's
frozen capacity expression (`205–206`) these shifts cancel. Keep SAXFC and
absolute fine fractions unchanged. This does not prove invariance at dry floors
or for other frost routines that subtract absolute SLSIC from scaled UL.

WLCK and LACKW carry unresolved shortages between fine/coarse layers but have
no external residual output. The proposed admissible single-coarse-layer matrix
checks one fine carry but cannot certify all cross-layer shortage paths. If
extended later, distinguish physically possible below-wilting water from a
state admitted by the native nonnegative-ST contract. Never initialize negative
ST and call it an ordinary no-input control.

## Acceptance and limits

Before invocation, freeze exact operands, complete initialization, sequence,
reference arithmetic, tolerances and expected dispositions. Normal controls
must close at justified float32 scale. Threshold fixtures succeed as scientific
observations only if the measured discrepancy is retained and correctly owned;
they must not be labeled conservation passes. Finite execution alone is not
acceptance. If any expected branch is not entered, retain that result and declare
an additional fixture before rerunning; do not silently retune the matrix.

No drainable capacity formula, POR/CPM or UL behavior is changed. No transport,
plant extraction, surface routing, freezing energy or actual ice phase change
is executed by FRWATC alone. SIFT's dimensional repair and its native consumer
acceptance remain scientifically separate from these mapping results.
