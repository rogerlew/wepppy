# Observe accepted final-hour water fluxes and store ownership

This active ExecPlan follows docs/prompt_templates/codex_exec_plans.md. Starting
checkpoints are WEPPpy f22ada98c and native 0c44b8b27. The user's “proceed”
authorizes the next bounded stage stated in reset-sequence findings. Earlier
packages and raw roots are immutable. No native physics change is presumed.

## Purpose and scope

Resolve the accepted water fluxes that actually reduce coarse available water
ST to zero before a fine-grid reset. Establish which store/reference is current
at each executed boundary. Stock differences alone do not identify external
fluxes; source presence alone does not establish execution. The selected high
rock case has input between clearing and reset, requiring gross/net distinction.

## Progress

- [x] Read reset findings, source owners, repository and retention instructions.
- [x] M1: declare store/clock ownership and precise observation gaps; independent design review.
- [x] M2: prepare minimally invasive private observer and strict reader/control tests; exact prereviews.
- [x] M3: execute three complete 16-year histories, require seven-output and full frost-trace parity.
- [x] M4: independent actual readback, bounded conclusions, archive, native/source-free checkpoints.

## Context and Orientation

Private base build: out/frozen-water-history-20261101/campaign-v1/build, observer
SHA256 fb885d126413b3f19488c640ef3e7fb8d7d9a872f0f8b08b48a207092a956c0f.
Accepted targeted inputs/output/traces are under
out/frozen-water-reset-20261101/targeted-v1/{zero,normal,high}-ks1.
Each is a complete 16-year three-OFE native hillslope history. The logging marker
selects year3/day19–20 for zero/normal, year7/day343–344 for high. Existing BPO
logging exposes 144 hourly groups per history, ten layers each. No new forcing,
parameter or selected dates are allowed. KSFLAG1 is diagnostic and not an
isolated frost treatment. Native canonical source remains unchanged.

ST is coarse available liquid, YST the mapping reference, FRZW coarse ice-related
storage, SLSW/SLSIC fine water/ice and NWFRZZ liquid held on frozen support.
The reset checkpoint establishes exact zero-ST assignments and an inherited
reference mismatch. Fine and coarse stores must not be summed as independent
physical water reservoirs. ET output categories can differ between EVAP and
EVAPPM; final EP may be changed by SWU after hourly processing.

## Plan of Work

M1 inspects the exact compiled watbal_hourly, evap, evappm, swu and FRWATC paths,
records source hashes and a source-free owner/clock table. Declare observed
versus inferred values, valid-state guards, units, arithmetic and stop rules.
Obtain scientific and implementation design reviews. Do not generalize a selected
window to an annual budget, all frost behavior or production rock effects.

M2 copies the pinned complete build into a fresh private destination, retaining
all original identities and a private observation-only patch. Add read-only
snapshots around actual ET, redistribution, drainage, lateral and surface stages,
and post-hourly uptake. Record actual ET method and accepted return operands,
residue interception and per-call coarse state changes. Only initialized values
may be logged; no guessed zeros for absent calls. Preserve mathematical operation
order and old observer records. Strict reader requires complete unique clocks,
ordered stages and finite values, separates requested/reported/assigned water,
and rejects malformed support. Bind source/includes/objects, compiler PATH/FC,
assembler/linker, runtime, inputs, reader and declarations before exact prereviews.

M3 finite budget: three new complete histories only, 900 seconds each. Reuse all
17 accepted targeted runtime inputs unchanged. Require all seven ordinary outputs,
17,532 daily keys and entire frost trace to match the accepted case; require
old BPO records to remain exactly identical after filtering new tags. A failure
is retained and stops acceptance; do not tune equations/tolerances or silently
expand the campaign. Build failure does not authorize a model parameter change.

M4 independently checks actual observations, stock/flux comparisons and the
remaining gaps. Retain source-free summaries, authored analysis and exact
provenance. Native routines, patches, binaries and full traces stay private.
Archive only after all writers clear; verify every member and raw inventory.
Verify earlier roots unchanged. Final native artifact policy, scoped docs lint
and staged Git byte checks precede commits on existing branches. Update this
plan, tracker and initiative board. No app suite rerun for observation-only work.

## Validation and Acceptance

Reconstruct stage profile deltas in meters; compare accepted routine-return
operands with independently observed assigned stocks, explicitly accounting for
residue water and rounding. Do not equate potential EP with accepted uptake or
count overlapping seepage reports twice. A zero effect is valid; unavailable
execution is not zero. Preserve per-layer negative/geometry/component checks.
Declare numerical reconstruction bounds before reading new model evidence.
Acceptance of an observer is output/trace parity plus complete supported new
records and independent review, not proof of full physical conservation.

## Concrete Steps

Work from /home/workdir/wepppy with python -B. New public helpers are under this
package's artifacts; raw root is out/frozen-water-flux-20261101. Native incident
will be docs/ablation/20261101_frozen_water_flux_ownership in
/workdir/wepp-forest-release-20261009. Exact preparation/build/run/read commands
and hashes will be recorded before invocation in the declaration and receipts.

## Idempotence and Recovery

All result destinations are fresh and exclusive. Never write caches, regenerated
outputs or patches into frozen roots. Keep failed preparations and version
corrected readers/declarations explicitly. Preserve unrelated dirty SSURGO docs
and generated docs_index.json. Do not consume withheld Roads materials or add
dependencies, branches, defaults, release binaries or deployment actions.

## Surprises & Discoveries

The actual ET routine changes ST before later capacity/drainage blocks, while
plant uptake can run after all hourly stages. Observing ET return alone does not
establish accepted transpiration or the final daily stock.

## Decision Log

2026-11-01: retain exactly the three previously selected windows and histories;
add internal boundaries because the existing composite interval cannot identify
accepted flux ownership. Review agents remain authorized by the original study
prompt. This is observation-only, not a reset repair or broad sensitivity sweep.

## Outcomes & Retrospective

All three selected transitions are attributed to executed EVAPPM removal.
Independent readbacks validate all2,196stage comparisons, method/call counts,
physical-reference flags and the high residual. All 2,292 archive members and the full inventory verify; prior 3,510 files
remain unchanged. Final source-free commits follow staged-byte checks. This completes a bounded question, not the Roads program.

2026-11-01 preparation: source-only observation placements and store equations
reviewed. Corrected coarse total to ST+FRZW+THETDR*DG; separated relative
coordinates from physical components, native arithmetic from reader rounding,
and explicit zeroing allowances. Reader v3/controls v4 preserve previous attempts
and reject14malformed cases. Final freeze identity is
925eb71538a22fddba99ee143e27607f245dbd4a328ad302681eca833cd1ae5f.
No model equations changed. Scientific exact prereview approves this declaration.

2026-11-01 build correction: first private build failed at link because ET is
routine-local in EVAP/EVAPPM, not shared with WATBAL_HOURLY. No model process
ran. Retain campaign-v1 intact; prepared-v3 uses a reserved zero at the caller
and retains ET inside the routines. Reader v4/controls v5 and runner v2 bind
fresh freeze b64ef3722da2e5909858a4c48e3bce895564739940fb56b3ec910ff7b542478e
for campaign-v2. Three-history model budget and all comparison equations remain
unchanged. Logger operand declaration checks must include caller scope explicitly.

2026-11-01 actual execution: exactly three complete histories ran successfully
under the corrected observer. Zero/normal pass the original reader. High's
original readback fails on an existing global BP_IRS_ENTER OFE0/index0 record,
not on model output. Source confirms that global caller; read_flux_v5 permits
only that legacy context while retaining strict layer/OFE and full old-stream
parity. Controls v7 reject17malformed cases. Independently reviewed reread_flux.py
revalidates all three histories into readback-v2 without new model execution or
changing original receipts. This is a validation correction, not native recovery.

2026-11-01 actual outcome: all three full histories preserve seven outputs,
17,532 daily keys, full frost traces and old BPO content. Supplemental readback
is accepted after narrow legacy-global context correction; original campaign
inventory and all frozen dependencies remain unchanged. Selected coarse ST
removal equals returned ES; high residue-inclusive residual is -2.01907e-11 m.
All2,196comparisons lie within declared numerical allowances. Twelve actual SWU
calls across the windows must not be generalized from the selected no-call OFE1.
No physical/model repair follows. Findings document the next capacity/retention
and separate surface-observation decisions. All raw writers cleared for archive.

2026-11-01 completion: scoped docs lint and native artifact policy pass. Archive
contains2,292verified files (5,954,449,692 uncompressed bytes), SHA256
4c8a4a81e61b54539adc8fde6c0a862cb2b8c5ca08c36ffbe7642cbbeca1f286.
Independent final scientific review accepts findings without changes. Public
checkpoint contains authored analysis, compact results and source-free native
receipts; native implementation and full traces remain private.
