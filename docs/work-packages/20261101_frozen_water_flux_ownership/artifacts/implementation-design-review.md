# Accepted-flux observer implementation design review

Disposition: **PASS for the bounded observation design, subject to the requirements below. No compilation or model execution is approved yet.** Reviewed the active flux ExecPlan and actual pinned source for hourly water balance, both ET methods, drainage, plant uptake and existing logging. No implementation or model run was performed; all earlier roots remain unchanged.

## Placement and ownership

In the selected hourly routine, PURK precedes ET; ET executes only on the final configured hour. Capacity redistribution, tile drainage, lateral flow and surface overflow follow ET. Snapshot immediately before/after each distinct block and record actual method/call presence. A nonexecuted routine is unavailable, not an inferred zero flux. A stage delta of zero remains a valid observed stock result. Preserve the before/after state for every active layer; profile redistribution must not be mistaken for an external export.

Plant uptake occurs after the hourly loop, plant-growth/range calls and daily accumulator updates. Record an actual SWU call separately from the interception-only and no-uptake alternatives. At SWU entry EP is a demand operand; its return includes plant interception adjustments as well as accepted soil uptake. Observe PLAINT/PINTLV and actual soil changes before identifying transpiration. Later SOILW refresh does not create a second reservoir: ST, YST, SOILW and fine stores represent different coordinates/clocks, not independent additive stores.

Hourly SEP is accumulated in deepSeep, then overwritten with that daily sum. DRAINQ likewise becomes tileDrainage after the loop. Lateral LATQCC is reduced while consuming layer water and may end as an unmet remainder; accepted hourly flow is the corrected UI_LFCRF and daily SBRUNF increment after shortage adjustment. Surface UI_SCRUNF and cumulative SURDRA overlap. Label these clocks explicitly and do not sum repeated reports of the same export. Record both accepted return operands and assigned stock deltas, retaining rounding/floor differences rather than asserting their identity in advance.

## Concrete initialized-read hazards

- Calling BPO does not guard argument evaluation: its date selector runs inside the callee. Never pass an uninitialized local on the assumption that BPO will skip output. Guard at the valid assignment/call site.
- Both ET routines assign XX from ES, then adjust residue interception. A negative XX adds water to the top layer, resets XX and jumps to label 60 before the evaporation loop initializes J2/XITFLG/RTO. XX is valid at the common exit; loop-local diagnostics are not universally valid there. RTO is only assigned on the partial-depth path. EVAPPM's BPOTES/KECON and other branch locals must not be read outside their assignment paths.
- EVAP explicitly separates ERES from returned ES; EVAPPM follows a different category convention. Capture actual method and residue operands before mutation. Do not impose one common ES-plus-ERES interpretation without source-owned reconciliation.
- SWU assigns XX and U(k) only on its positive-EP uptake path. The whole U array is not universally initialized, particularly when roots initially reach the profile bottom. Record U(k) only inside the executed assignment loop, or restrict observations to initialized COMMON state at caller boundaries. Root-depth clipping and interception-only paths must remain visible.
- Drainage is conditional on IDRAIN and water-table depth. Observe its actual branch flag and assigned DRAINQ; do not read routine-local drainage operands when no call occurred. Lateral hydraulic intermediates are conditional on FCDEP and other branches. Broad dumps of these locals are unsafe.

ET routines also serve callers outside the hourly routine. Associate internal ET records with an explicit enclosing invocation/caller and scenario/OFE/day/hour, rather than inferring ownership solely from a date-gated tag. If observer bookkeeping supplies context, initialize it explicitly, delimit entry/exit, check native identifier collisions and keep it separate from model COMMON state.

## Required prereview and gates

Before execution, retain the exact additive private patch and prove native lines, mathematical order, labels and branch structure remain unchanged. Check fixed-form columns, new helper/local/include collisions and all inserted argument validity. Bind the complete original/prepared build, included source, objects, compiler/subtools, flags, runtime libraries, all seventeen unchanged inputs, reader and declaration. A new executable requires actual linked-runtime verification.

The finite scope remains three existing complete sixteen-year scenarios with unchanged selected dates and forcings. Require seven ordinary outputs, 17,532 daily keys and the entire FH trace to match accepted histories. Filter only an explicit inventory of new tags and require the remaining old BPO bytes to match exactly; a broad prefix filter must not erase unintended old records. Retain process and diagnostic-log hashes, failures and post-execution source/input nonmutation.

The strict reader must validate unique ordered invocation/stage identities, complete support, method-specific payloads, finite primitives/derived values, component/geometry flags and explicit skipped branches. Include malformed controls for duplicates, missing stage/layer, wrong parent/method/hour, reordered stages, unguarded/unavailable payloads and nonfinite values. Prespecify reconstruction bounds from actual REAL operands and absolute primitive terms. Accepted observer parity is not proof of a closed annual budget or field validity.

## Source identities

SHA-256 values from the pinned private build:

- watbal_hourly.for: `dbfeed35c303c54037d130bc62852b59fcd76946e62addc30ff5ed5910abf986`.
- evap.for: `6bf78e113cc413131f3feb3516070cf233c6c16e3c0f86b3e78eaa4ba86afdbc`.
- evappm.for: `bfd6607f8a0033b5b779bb1830cddda52652316b1e77fafe9640b4c691647d23`.
- swu.for: `060b0ea0710ffba720624bb595eb63df0010dc665b71a2287c4e21be9e60f901`.
- drain.for: `3ef320c282b941f9e7e2c2f08db2547e7a8d88d0dce89eff94cca653ebfc73f9`.
- contin.for: `4e419620fb1fd5203c2d532a4fa61b9b97349bfd35f4f8c215373e5226238604`.
- frwatc.for: `f580544b80ef091edd87478ef8fb5f0a75632261c36c0d5828a28b2438f366ed`.

Concrete instrumenter, observer, reader and runner approval remains pending. Reviewer writers are clear after scoped documentation lint.
