# Frozen-water history execution declaration

## Scope and finite panel

Observation only, against the pinned private build identified in the active
ExecPlan. No native model equation, state assignment, precision, threshold,
COMMON layout or parameter default changes. Fresh copies only; all prior study
roots remain immutable. No deployment or Roads holdout use.

Exactly 29 prior synthetic fixtures precede histories. Require identical
ordinary stdout against all 29 retained controls and observation of F, G, H,
I-small and I-middle signatures before interpreting absence in histories.
Standalone compiler flags remain the prior checked, unoptimized flags.

Exactly six 16-year configurations: zero, normal and high SIFT rock contexts,
each with the original soil header KSFLAG 0 and a diagnostic KSFLAG 1 copy.
The latter changes only the unique soil header `3 0` to `3 1`. All other
16 source input files and all other soil bytes remain unchanged. Add the same
empty observation marker to both members of each pair. Run one pinned baseline
and one new observer per configuration: 12 history processes, 41 total model
processes including synthetic controls. No adaptive case additions or tuning.

KSFLAG 0 is an intended inactive control, not proof of inactivity: SCON can
change runtime KSFLAG. Actual runtime gate and FROST_CALL observations determine
activation. KSFLAG also affects conductivity; the enabled panel does not isolate
a frost treatment effect and cannot quantify original-history water loss.

## Process and parity gates

Freeze source, all 978 pinned build members, preparation, authored helpers,
runner, reader, reader controls, declaration, compiler tools, runtime libraries,
original histories, synthetic evidence and accepted prior readback. Review the
exact freeze before execution. Preserve build logs, before/after inventories,
process stdout/stderr, timeout status and failed attempts. Full builds have a
300-second bound, synthetic processes 60 seconds, full histories 900 seconds.
A failed synthetic panel stops history execution. History failures are retained;
complete the declared finite panel without changing model inputs or thresholds.

Every accepted pair requires identical runtime inputs and seven byte-identical
ordinary output files, normal completion, finite outputs and all 17,532 daily
keys (three OFEs, years 1–16, leap years every fourth year), depth 1,800 mm.
Original-header fresh baselines must also equal their previous accepted outputs.
No observer result is interpreted when its pair fails parity. Require final
source/build/input inventory verification. The complete application test suite
is not relevant to this observational-only phase; run reader controls and docs
lint, followed by independent scientific and implementation readback reviews.

## Trace schema and availability

Unit 971 writes `FH_SCHEMA 1`, contiguous event records and terminal
`FH_END event_count map_count`. An E record has tag followed by ten integers:
sequence, map, year, day, OFE, hour, direction, layer count, frost-parent sequence,
initialization epoch. Epoch on INIT_PRE identifies the destination initialization
attempt, not provenance of its pre-initialization state.

C records contain event, layer, fine count, availability, then DG, THETDR, UL,
ST, FRZW, FROZEN, SOILW, YST, NWFRZZ and SAXFC. F records contain event, layer,
fine index, SLFSD, SLSW, SLSIC and native REAL unfrozen support. V records contain
event and integer marker value. B records contain event, layer, fine index and
six native branch operands. G contains event, layer and fine index: operands
are unavailable and were not dereferenced. Coarse-only/unavailable C records
have fine count zero and SAXFC zero as a placeholder, never a measured value.

Only complete no-frost initialization and the fully initialized synthetic driver
establish fine readiness. Initial-frost and continuing paths require previous
per-OFE readiness with unchanged NFINE. No field is repaired to make it readable.
Reader rejection includes malformed shapes, missing/duplicate support, nonfinite
observations, invalid clocks, sequence/parent/map drift and missing footer.
Unavailable data cannot count as zero discrepancy or observed branch absence.

MAP_PRE/POST surround actual FRWATC calls. Markers distinguish WINTER weather
eligibility from actual KSFLAG-dependent FROST_CALL/DONE. Daily coarse boundaries
surround WINTER and WATBAL, including IRS; WB_PATH records actual ui_run.
FROST_BLOCK_PRE/POST bracket a composite frost-phase block, not its individual
internal routines or a proved first consumer. INIT_PRE/POST observe a later fine
initialization when pending. GRNA entry is not observed. These boundaries cannot
close all intervening fluxes or attribute causal recovery.

## Accounting and limits

Fine liquid is sum(SLSW times native unfrozen support) plus NWFRZZ; fine ice is
sum(SLSIC). Coarse liquid is ST + THETDR times (DG minus FROZEN); coarse ice is
FRZW + THETDR times FROZEN. SOILW remains a separate diagnostic. Direction 0
reports coarse-after minus fine-before and fine stock change. Direction 1
reports fine-after minus fine-before minus actual ST-minus-YST request; layer
residuals can include transfers to neighboring layers, so profile ranges are
also retained. Final VARWAT is not unapplied water: native distribution does not
necessarily decrement it.

Report branch recurrence and signed ranges without a universal model-conservation
tolerance. The 2e-8 m previous synthetic fixture bound is not a history acceptance
criterion. Native REAL thresholds are 0.0010000000474974513 m,
1.0000000116860974e-7 m and 9.999999747378752e-6 (context determines depth versus
volumetric units). Retain negative geometry/stocks as invalid observations,
never clip them. Fine-grid stock arithmetic uses emitted native support rather
than silently recomputing support in double precision.

Every positive NWFRZZ clearing receives its own map/layer ledger identity.
Carry all pending identities across later maps. Retain up to twelve subsequent
boundary observations per clearing, plus its next initialization endpoint or
end-of-history unresolved status. This bound limits repeated storage, not the
number of pending events. A later larger fine stock does not prove causal
restoration of that specific clearing. Do not add these snapshots or repeated
representation residuals into annual water loss. F/G/I tags identify observed
threshold exposure; their signed physical residuals determine effect, not tag
counts alone. Unobserved internal ownership stays unresolved.

## Reproduction

From WEPPpy root, run the authored reader controls with `python -B` into a fresh
raw destination. Run `run_history_campaign.py freeze`, retain two independent
reviews binding that freeze, then write the execution approval receipt with
status, freeze SHA-256 and review hashes. Run `run_history_campaign.py run` once.
The runner refuses existing campaign destinations and dependency drift. Preserve
failures; any correction requires a separately identified, reviewed attempt.
Publish only authored analysis/helpers, compact receipts and prose; legacy
native source, patch, executables, objects and full histories stay private.

## Prereview corrections before first invocation

H detection uses paired actual D0_CLEAR_PRE/POST operands; entry FROZEN may be
stale because direction 0 recalculates it. Direction 1 uses D1_REQUEST when
present and retains double reconstruction and its rounding difference. The
zero-ST branch has no native request calculation: its comparison uses an
explicitly labeled float32 reconstruction. Reject branch clock/direction drift,
missing start/layer/finish evidence and incomplete full-history daily gates.
Any G gap suppresses that layer's physical interpretation. Negative physical
components or invalid geometry are retained separately from valid-state signed
ranges and excluded from threshold signatures. Every synthetic transfer stock
must match the independent prior STATE/FINE reader within a floating-point
reconstruction bound, 2 gamma_k times the two stock magnitudes, k = 16n + 64,
u = 2^-53. This bounds reader arithmetic only, never native conservation error.
Complete the finite history panel, then exit unsuccessfully if any pair fails.
