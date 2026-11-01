# Resolve frozen-water zero-storage reset accounting

This ExecPlan follows docs/prompt_templates/codex_exec_plans.md. Starting commits
are WEPPpy b39f59066 and native c56c331eb. The operator's latest “proceed”
authorizes continuation of the reviewed clearing–hydrology–zero-ST/YST question.
The preceding work package and out/frozen-water-history-20261101 are immutable.

## Purpose and scope

Determine what the zero-ST branch actually does to fine-grid water, which part
of its apparent residual already exists at entry, and which intervening changes
are attributable from executed observations. ST is coarse available water; YST
is its mapping reference. Fine-grid liquid includes unfrozen-cell liquid and
NWFRZZ, liquid held in frozen support. A stock difference is not an external flux.
No production formulas, thresholds, capacity defaults, deployment or surface-rock
interpretation changes belong here. Do not use the withheld Roads materials.

## Progress

- [x] Read preceding findings, source branch and repository/retention instructions.
- [x] M1: bind retained evidence and declare reset arithmetic/sequence comparisons.
- [x] M2: read all zero-ST mappings and all 58 clearing sequences; derive exact reset ownership and explicit producer/flux gaps.
- [x] M3: execute independently reviewed multilevel full-routine controls for the reset mechanism, preserving original routines.
- [x] M3b: retarget the existing hourly observer for three declared reset extrema, requiring complete-history and full-trace parity.
- [x] M4: independent scientific/implementation readback, documentation, archive and source-free checkpoint.

## Context and Orientation

The three completed KSFLAG1 histories have 36,230 mappings; original KSFLAG0
histories have no actual frost calls. The source-free prior summaries live in
docs/work-packages/20261101_frozen_water_history_ownership/artifacts. Full traces
and builds are private under out/frozen-water-history-20261101/campaign-v1.
The all-clearing-v3 receipts identify all 58 clears, next initialization and the
25 earlier next-mapping endpoints. Thirty-three next-map endpoints are censored
by initialization. Retain these identities without treating them as annual loss.

The unchanged FRWATC direction-1 zero-ST branch sets NWFRZZ to zero and all SLSW
to THETDR. It does not calculate VARWAT. Its nominal requested coarse difference
must therefore remain explicitly reconstructed. Source inspection identifies
PURK and EVAP/EVAPPM as possible zero-ST writers; their presence in source alone
does not establish which writer executed for a historical event.

## Plan of Work

M1 predeclares an observational algebraic decomposition. For each actual zero-ST
layer, compute fine liquid before, exact dry-support target after, ice change,
coarse-reference available stock YST, and the difference between that reference
and fine available stock at entry. Compare the actual reset change against its
assigned target, and separate the already-existing representation difference
from numerical reconstruction error. Include all layers and all actual zero-ST
calls, not only the three positive profile extremes. Preserve negative component
and geometry flags rather than erasing observed assignments.

M2 joins every clearing and its later boundaries by scenario/OFE/layer/map/clock.
Read every relevant retained coarse WIN/WATBAL/IRS boundary and mapping endpoint.
State exactly which net changes are observed; do not apportion aggregate changes
to ET, drainage or runoff without actual accepted flux evidence. All nonzero-ST
mapping layers and the inactive controls remain comparison coverage. Create a
source-owner/gap table distinguishing executed observations from static inference.

M3 declares a finite multilevel FRWATC panel before any model invocation. Use
unchanged full-routine source/includes in a fresh private build with pinned
compiler/runtime provenance. Controls bracket ST=0 versus a positive value below
the native absolute-change threshold, coherent versus deliberately mismatched
fine/coarse references, nonzero NWFRZZ, partial/full frost and multiple layers.
They must verify assigned stocks and untouched inactive support, not only return
codes. Obtain scientific and implementation prereview before building/running.
Any further full-history observer requires its own reviewed finite declaration
and seven-output parity; do not silently expand this mechanism campaign into
unclosed drainage or energy validation.

M4 independently reviews raw readback and interpretations, including malformed
reader controls and original-file nonmutation. Use scoped doc lint; no application
production changes means no repeat full application suite. Publish authored
analysis/driver and compact findings only. Keep native source, patches, objects
and full traces private. Archive only after every writer clears, verify every
member and inventory, and check staged bytes before committing on current
branches. Update this plan and tracker before handoff.

## Acceptance and recovery

All source/build/input/helper identities must match declared hashes. Use python
-B and fresh destinations. Keep failed attempts, never edit executed declarations
or frozen earlier roots. For native arithmetic comparisons report REAL rounding
explicitly, distinguish reconstruction bounds from physical acceptance, and do
not tune a bound to make a discrepancy disappear. The observed reset must equal
its actual assignment semantics; an unclosed intervening flux budget remains a
named limitation. No new dependency or branch is needed.

## Surprises & Discoveries

High has intervening allocated input: its final-hour gross removal exceeds net
coarse endpoint depletion. The independent no-input premise failed on high and
was retained, then generalized without changing model evidence. Repeated reset
stock idempotence does not imply an identical nominal residual when YST is stale.


The zero-ST branch bypasses native request calculation entirely. Interpreting
its difference as a skipped VARWAT update would be incorrect. Existing coarse
snapshots bracket WATBAL, but do not by themselves identify internal accepted
fluxes or which of several zero-setting writers executed.

## Decision Log

2026-11-01: first separate inherited representation mismatch from the reset's
own stock change using complete retained coverage and compiled multilevel
controls. This is necessary before deciding whether a larger flux observer or
behavioral ablation has a precise scientific target. Independent review agents
remain authorized by the original study prompt. No native correction is presumed.

## Outcomes & Retrospective

Bounded execution complete: all 15 declared model processes and independent readbacks pass. All 268 archive members and the full inventory verified; all 3,242 prior files unchanged. Source-free checkpoint publication follows final staged-byte verification. No physical correction is justified by the reset evidence.

2026-11-01: all 16,753 retained zero-ST layers exactly match the reset target;
no observed reset increases fine water. All 58 chains and 107,037 nonzero-layer
comparisons retained. Twelve prereviewed native controls pass. A necessary
producer gap can be narrowed using the existing buffer_observe.on two-day window
without new source instrumentation: declare three complete histories at the
preselected maximum layer residuals. See artifacts/targeted-declaration.md.
This adds three observation-only invocations, independently reviewed before
execution, not a parameter sweep. Total phase budget is 12 controls plus 3
retargeted histories. Inner ET/drainage flux ownership may remain unresolved.

2026-11-01: all three retargeted histories preserve seven ordinary outputs and
the full frost trace exactly. High receives intervening input; its net endpoint
depletion must not be substituted for gross final-hour removal. Independent
reviews accept the narrowed composite interval and leave accepted ET attribution
open. Next work requires authoritative stock/clock ownership and a separately
reviewed internal flux observer; do not patch the reset or sum residuals as losses.

2026-11-01 outcome: the finite phase is complete. All 15 model invocations,
independent actual readbacks, malformed reader controls, scoped lint and native
artifact policy pass. Archive SHA256 is recorded in artifacts/archive-receipt.json.
No physical correction or accepted external-flux closure follows from this phase.
See artifacts/findings.md for the next scientific decision and limitations.
