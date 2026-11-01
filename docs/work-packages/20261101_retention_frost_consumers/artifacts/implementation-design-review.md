# Frost consumer observation implementation design review

Disposition: **the proposed finite factorial panel is reviewable; a minimal additional observer is justified for full-history executed-domain evidence.** Concrete instrumentation, reader, runner, declaration and controls still require execution review. No build, model invocation or old-package write occurred here.

## Reuse and scope

The existing flux observer binary hashes to `17fbcf4540e7d7a29980b4eccb0851652689160960663ae8140ed3cddb377b72`. Reuse its accepted source/build/runtime chain as comparator and preserve all existing observation streams. It already supplies initialization retention/stock records, full frozen-history mapping identities, and selected-window ET/capacity/drain/lateral/surface/SWU stage observations. Bind its entire build inventory and resolved libraries before any isolated observer build.

The three material cases, two retention lanes and two KS configurations define twelve physical histories. Comparator-versus-new-observer parity may require additional actual invocations; enumerate those separately in the declaration and process matrix. Do not call twelve parameter cells twelve total processes if each requires two binaries.

KSFLAG1 is not an isolated frost switch. It enables the actual FROSTN call in WINTER and changes rangeland conductivity handling in SOIL. Keep baseline/candidate retention comparisons within the same KS configuration; label cross-KS effects as a process-configuration contrast. Actual FROST_CALL/DONE identities and initialized mapping states are stronger evidence than climate duration or summary-line counts. Report empty/unreached branches explicitly.

## Actual division sites

In pinned watbal_hourly.for the conductivity ratio is computed only inside the existing UL-positive branch, and the logarithmic expression only inside the positive-ratio branch. Observe FC, UL and the actual ratio at those boundaries without evaluating a forbidden ratio merely to log it. A ratio of one reaches a zero logarithm despite the positive-ratio guard. Preserve actual operands, branch decision and result where produced; a diagnostic strict interval is not a model guard.

There are two distinct lower-layer ST/UL evaluations: the layer-eligibility loop and the later conductivity accumulation loop. Both bypass that expression for the bottom layer. Give them separate site identities. Never inspect layer+1 on the bottom branch or assume a Fortran boolean expression short-circuits safely.

The UL-DRFC expression is consumed by the lateral-conductivity weighting only after its actual storage/meblfc condition passes. Observe the signed numerator and denominator there, along with layer, clock, current ST/UL/DRFC and branch context. Record the computed result before its upper clamp separately if needed. Merely recomputing the denominator at a stage snapshot does not prove the expression was executed. Daily versus hourly implementation and skipped call paths must remain explicit.

A helper must not evaluate divisions/logs on behalf of the model, mutate COMMON/model arrays or reuse a native local name. Initialize all helper-owned state explicitly, audit included identifiers for collisions, keep fixed-form columns valid, and log a pre-operation event before a potentially failing operation so a trap cannot erase the causal evidence. Logs must retain actual REAL operands at round-trip precision.

## Full-history accounting versus selected windows

Existing bpactive is restricted to a declared year and target/preceding day, after its arm call. Existing selected FX/BPO groups therefore cannot establish full-history domain counts or full-history hourly closure. Preserve them for detailed replay, and add a separate explicitly initialized summary/event logger rather than silently changing their selection.

For domain summaries retain exact site/phase/OFE ownership, attempts and completed evaluations, branch skips, finite/zero/sign/range counts, extrema and exact witnesses, plus a terminal completeness record. Counts need an independent expected clock/stage ledger; a final summary alone can conceal missing initialization or omitted events. Distinct mapping/initialization epochs must not be collapsed merely because calendar/hour labels agree.

For accepted hourly flux audits, capture stocks at the existing actual stage boundaries and use returned/accepted fluxes in matching units. ET occurs only at the final hourly step; its requested demand is not accepted water removal. Drainage has per-step and accumulated quantities, while lateral and surface export have separate owners. Later SWU transfer is outside the hourly ET/drain block. Do not assign one aggregate daily delta to a particular producer.

Keep signed ST separate from absolute water and dry-reference/frozen-thickness terms. A closure residual must account for a changed reference or mapping epoch, rather than labeling it external flux. Use active nsl/nfine bounds and readiness guards; never read inactive or not-yet-initialized arrays merely to fill a record. Summaries must preserve negative/invalid outcomes and failed cases, not average them away. Full-history accepted-flux claims require the new stage ledger; selected-window replay alone supports only those windows.

## Execution gates

Prepare a private minimal patch and complete dependency/source/runtime freeze. Include synthetic controls for positive and zero denominators, ratio one, lower-layer/bottom branches, inactive-array sentinels, wrong clock/site joins, missing terminal records, and incomplete stage groups. Compare observer versus accepted comparator for each identical physical input cell: seven ordinary outputs and all old full observation streams must remain byte-identical. Input changes for retention, KS and any selected-window control must be declared independently. Preserve build/run/validation failures and process receipts before aggregate status. No production repair or new numerical floor is authorized.

The prior native depth extension and exact binary32 input remapping remain prerequisites: 400 mm emitted support becomes 600 mm/four computational layers, and 1400 mm becomes 1600 mm/nine layers in this pinned path. Initial SCON then WB ordering is per OFE. Carry the corrected accepted reader semantics into the new campaign rather than copying the earlier rejected assumptions.
