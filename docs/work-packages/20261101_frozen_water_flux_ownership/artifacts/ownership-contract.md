# Executed stock and accepted-flux observation contract

This is a bounded diagnostic contract, not a new production water-balance rule.
Native variables and algorithms remain unchanged. Prior selected windows define
three diagnostic KSFLAG1 histories; no annual or general field closure follows.

## Stores and clocks

ST is coarse available liquid per layer (m). Coarse liquid including dry support
is ST + THETDR*(DG-FROZEN); coarse ice is FRZW + THETDR*FROZEN.
The corresponding coarse total is ST + FRZW + THETDR*DG.
YST is a fine/coarse mapping reference, not another reservoir. Fine liquid and
ice are alternate representations; do not add them to coarse stocks. Existing
full frost trace and exact trace parity preserve clearing/reset endpoints and
fine-support provenance. New snapshots use unchanged BPO W/K records, including
ST/UL/FRZW/THETDR/DG/SOLTHK and SSC/SSCV/POR/FROZEN/FRDP/THDP.

Within hourly WATBAL, sequence is allocation → PURK → ET (final hour only) →
upward capacity redistribution → tile drainage → lateral flow → surface overflow.
Plant growth and conditional SWU occur after the hourly loop. Snapshot gaps must
remain explicit. Retain all 144 two-day/hour/OFE groups, all ten layers and both
W/K supports; six daily OFE groups bracket later uptake. Every FX tag is new and
must disappear cleanly when comparing old BPO content against accepted history.

## ET boundary semantics

ET_PRE follows caller initialization of EP/ES/ERES and records those values,
RESINT, PLAINT and method flag. REQUEST inside the actual ET routine records XX,
ES, ERES, RESINT, EP, ET after residue handling, before the XX<0 branch. RETURN
at label60 records the same initialized quantities after exhaustion correction.
The routine ID is 1=EVAP, 2=EVAPPM; it is not a layer or hourly index.
ET_POST follows the actual call and records EP/ES/ERES/RESINT, reserved zero
and method flag. ET is local to each evaporation routine and is recorded only
in REQUEST/RETURN there. ET stage snapshots follow the enclosing IF.

EVAP returns soil-only ES and residue ERES. EVAPPM returns ES inclusive of residue
and does not assign ERES. For nonnegative interception, compare profile ST change
plus RESINT change plus returned ES+ERES (EVAP), or plus ES (EVAPPM). Preserve
negative-residue flags and do not claim this equation on unsupported branches.
Returned EP is demand before plant uptake, not an accepted root sink. ET is a
reported intermediate and need not equal final accepted daily extraction.
XX may be negative (residue pushed into soil) or positive unmet demand; neither
is an independent external sink. Never log uninitialized J2/RTO/XITFLG at shared
exit, or SWU XX/U outside their valid positive-demand branch.

## Other boundaries

Capacity redistribution should conserve profile ST algebraically, subject to
native REAL rounding. Tile drainage compares its stage profile change against
hourly DRAINQ; a DCALL record identifies actual calls, while DFLUX records the
initialized hourly DRAINQ on every step. The daily sum is separate. DFLUX does
not log branch-only drainage operands. Lateral flow compares assigned profile
change with corrected hourly UI_LFCRF; final LATQCC is an unfulfilled remainder.
Surface overflow compares LAT→AFTER profile change with UI_SCRUNF. SEP belongs
to PURK and is repeated in existing FLUX; it is not another later export.

UP_IN/OUT and W/K snapshots bracket the entire uptake decision. SWCALL appears
only after an actual SWU call. Compute accepted canopy water from PLAINT-PINTLV
under the actual branch; for a positive-root SWU call, compare final EP minus
canopy water with profile removal. No-call interception branch and no-demand
branch remain distinct; missing SWCALL is not automatically zero root uptake
without the decision operands and unchanged stocks. Growth interval between
hour24 AFTER and UP_PRE is separately retained and assessed.

## Arithmetic and strict acceptance

All printed operands are DOUBLE conversions of native REAL or integers. Evaluate
stock sums/differences with Python math.fsum. Report reader reconstruction bound
gamma128*sum(abs(primitive operands)) with unit roundoff 2^-53. Separately report
a native arithmetic allowance using unit roundoff 2^-24 and the same gamma128
formula, gamma128=128*u/(1-128*u). Only ET and uptake intervals with nonnegative
entry and exit ST receive a separate 10*1e-10 m allowance for at most ten native
zeroing operations; unsupported negative-coordinate cases receive none and are
flagged. These are declared comparison allowances, not physical tolerances or
fitted closure criteria. Report signed residual and all allowances for every
comparison, including zeros and failures. Nonfinite input, incomplete/duplicate
support, wrong clocks, method/order mismatch and original-output/trace drift
fail acceptance. Negative components or changed support are retained flags and
block an unqualified physical interpretation rather than being silently removed.
