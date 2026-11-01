# Reset sequence: independent scientific design review

Design accepted for read-only accounting and preparation of a separately reviewed finite control declaration. This is not execution approval. No native build, execution, source edit or earlier-study mutation was performed. The following five native files match their counterparts in the prior pinned storage-observer build exactly.

## Assignment semantics and algebra

FRWATC lines 139–158 initialize shortage carry once per call, skip layers with NFINE below one, and test exact ST equality to zero. The zero branch assigns NWFRZZ zero and every active SLSW to THETDR. It does not calculate a native request, update YST, modify coarse ST/SOILW/FRZW/FROZEN, change fine geometry or change SLSIC. These untouched fields must be checked, not assumed from normal return. Direction 0 lines 127–134 assign ST/SOILW/YST before potentially clearing NWFRZZ; this ordering can create the reference discrepancy later observed at reset.

For one supported layer let u_j be the emitted native REAL unfrozen support, d = THETDR, U = sum(u_j), N = NWFRZZ, L = sum(SLSW_j u_j) + N, and I = sum(SLSIC_j). Compute all derived values from actual emitted inputs, retaining their clocks. Fine available liquid is A = L - dU, equivalently sum((SLSW_j-d)u_j) + N; report numerical differences between these reconstructions rather than silently treating arithmetic order as identical.

The reset target is L_target = dU, I_target = I. Therefore the total fine-stock change is -A plus assignment/readback error. With the explicitly reconstructed request q = float32(ST-YST) and exact ST zero, q is -YST (negating a finite REAL is exact). The observed mapping residual decomposes as:

`R = (T_after - T_before) - q = (YST - A) + assignment/readback error`.

This identifies inherited disagreement between the reference available stock and current fine available stock; it does not identify when or why that disagreement arose. A nonzero reset change is not itself a defect: a valid coarse removal can require the fine grid to catch up. A nonzero residual is not an accepted external flux.

If comparisons use coarse support DG-FROZEN instead, retain the additional term `d * (U - (DG-FROZEN))` explicitly. Do not silently replace native per-cell support with a double-precision coarse difference. Fine ice cancels only after verifying that SLSIC is unchanged. Comparing coarse total reference stocks additionally introduces coarse/fine ice disagreement and potentially mismatched clocks; YST alone does not supply a synchronized historical total-water state.

Exact assignment checks should require active SLSW equal the actual input d, NWFRZZ equal zero, and untouched state equal its pre-call values. Floating-point stock reconstruction bounds apply only to derived arithmetic. Use a forward-error bound based on sums of absolute terms, including dry-support subtraction and NW, rather than a relative tolerance on a nearly cancelling residual. No universal physical tolerance follows from the prior 2e-8 m synthetic bound.

## Complete observational coverage

Count every actual D1_ZERO marker and join it to one matching pre/post layer with scenario, map, OFE, layer, parent, epoch and clock. Include coarse-inconsistent states, marking individual geometry/stock availability and validity separately. Reject duplicate or missing joins. Reconcile marker counts against retained trace/readback counts for all three enabled histories; preserve all nonzero-ST layers as comparison coverage and the inactive controls as activation controls. A zero-ST case with unavailable fine support is unavailable accounting, never a zero discrepancy.

Retain all 58 paired clearing identities, their next initialization and any intervening mapping before initialization. Preserve explicit censoring of the 33 cases whose initialization occurs before a later map. Cover all intervening recorded WIN/WATBAL/IRS and composite frost boundaries, but distinguish net stock changes from individual accepted fluxes. The current trace cannot attribute a historical zero setter solely from routine presence in source. PURK lines 165–173 decrement ST using seepage with time-step handling and then floor small ST to zero. EVAP lines 639–659 and EVAPPM lines 492–516 also decrement/floor or exhaust ST. FROSTN lines 266, 303 and 332 write YST during initialization. These are static possible owners, not execution receipts identifying the responsible writer for a given event.

## Minimal finite multilevel panel proposal

Use two active coarse layers for ordinary controls and three for shortage-carry controls. Use binary-exact baseline inputs where possible: layer depths 0.125 and 0.25 m, two fine cells each, d=0.125, liquid content 0.25, porosity 0.5, and SAXFC=0.25. Partial frozen depth can be 0.03125 m in the first fine cell; full frost uses each complete fine-cell thickness. Ice water of 0.25 times frozen support and NW=2^-12 m leave room under the stated porosity. Construct YST from the initialized fine available stock unless a case explicitly declares a mismatch. ST=0 represents the new coarse state awaiting remapping; the fine grid and YST can legitimately retain their previous positive stock.

| Case | Purpose and declared expectation |
| --- | --- |
| C1 | Dry unfrozen, ST=YST=0; reset is idempotent. |
| C2 | Wet unfrozen, coherent previous YST; reset removes fine available liquid and residual is arithmetic error. |
| C3 | Partial frost plus positive NW, coherent previous YST; liquid reaches dry support, NW disappears, ice is unchanged. |
| C4 | Fully frozen plus NW, coherent previous YST; liquid after is zero, ice unchanged, removal equals NW. |
| C5 | C3 with YST increased by binary-exact delta; residual equals the positive inherited mismatch. |
| C6 | C3 with YST decreased by the same delta, keeping YST nonnegative; residual equals the negative inherited mismatch. |
| C7 | Wet partial-frost state with YST=0 and ST=0; explicitly mismatched reset comparison. |
| C8 | Same fine state and YST as C7, ST=2^-25 m; request is below the absolute gate and no incoming carry exists, so the nonzero branch leaves fine stock unchanged. |
| C9 | Positive fine unfrozen support below 1 mm; zero branch still resets every active SLSW, without applying the normal update-support gate. |
| C10 | Three layers: first creates shortage, middle ST=0, last has enough available liquid; inspect carry passage across the reset layer and final recipient. |
| C11 | Matched C10 with a small positive middle ST; distinguishes zero-branch bypass from ordinary carry handling. |
| C12 | Explicit direction-0 clearing followed by assigned coarse ST=0 and direction-1 reset, then repeat direction 1; label the prescribed coarse intervention, test inherited mismatch and reset idempotence. |

This twelve-case proposal needs exact fixture values, stages and expected native branch paths frozen before invocation. C10/C11 require a reviewed budget sufficient to create and consume shortage; do not tune them after seeing results. FRWATC lines 239–255 consume/generate carry inside the nonzero branch, while the zero branch leaves that local carry untouched. Consequently multilevel cases are necessary even though single-layer reset algebra is simple. Distinguish an untouched carry from external water creation or loss.

Initialize every consumed COMMON input and every active fine cell; retain whole-array sentinels for other OFEs, inactive coarse layers and fine indices above NFINE. Include the full unchanged routine and its original includes. Check dimensional limits before input assignment. Keep observer locals distinct from native COMMON names. Read back all coarse stocks, YST, dry reference, native fine support, SLSW, SLSIC, SLFSD and NW before/after every call. No capacity formula change is part of this panel. Complete declarations, driver, runner, dependency freeze and independent implementation review are required before execution.

## Source bindings

Paths are relative to the private canonical source root `/workdir/wepp-forest-release-20261009/src`; identical hashes were checked in the previous pinned build. No native source text is published here.

- `frwatc.for`: `a834dbe62497989e8f99945acc880cdb31ced4ccc88d31f215c91738a0a0f1c1`.
- `purk.for`: `681d99b1793c757aeb072d374af3d31e14b3d38a9e39c5fc48b08d3cf678aab3`.
- `evap.for`: `6bf78e113cc413131f3feb3516070cf233c6c16e3c0f86b3e78eaa4ba86afdbc`.
- `evappm.for`: `bfd6607f8a0033b5b779bb1830cddda52652316b1e77fafe9640b4c691647d23`.
- `frostn.for`: `cdf107e59cd9a24e3e1898deb1f0791925c8a14de8fc3638e966a5f19628c5df`.

Writers clear. Only this new review artifact was written.
