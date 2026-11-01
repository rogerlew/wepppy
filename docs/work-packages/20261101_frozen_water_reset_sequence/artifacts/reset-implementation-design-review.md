# Reset-sequence implementation design review

Disposition: **PASS for the bounded design, conditional on the requirements below; native execution is not approved.** Reviewed the active reset ExecPlan, prior frozen observer/reader interfaces and actual FRWATC branch source. No new reader, finite case declaration, driver or runner existed at this review snapshot. Their concrete implementation requires prereview before compilation or execution. No earlier evidence was modified.

## Exact reset semantics

Direction 1 initializes the shortage flag/carry once before its layer loop. A layer with NFINE below one is skipped. For a supported layer whose native ST compares equal to zero, FRWATC clears NWFRZZ and assigns THETDR to every SLSW cell in that layer, including cells with zero unfrozen support. It leaves fine ice and geometry unchanged. It bypasses VARWAT calculation and the D1_END observation. Therefore the reader must select actual D1_ZERO events, not infer branch execution from a rounded display or missing request record. A zero-ST request is explicitly reconstructed as minus YST; it is never an observed native VARWAT value.

For observed support u, use fine liquid L = sum(SLSW*u) + NWFRZZ, target T = THETDR*sum(u), and entry available stock A = L-T. The assigned liquid change is minus A; its difference from reconstructed minus YST is YST-A, before reconstruction rounding. Report ice change, actual post-state assignment agreement and geometry validity separately. Do not call YST-A a flux or producer contribution. Use recorded native REAL support; if independently reconstructing support, round DG/NFINE and its subtraction to binary32 in native operation order. Preserve exact native operands and distinguish binary64 stock reconstruction from native single-precision arithmetic. Bounds must be declared before inspecting residuals.

## Sequence and coverage requirements

Bind every accepted pair receipt, trace, original ownership ledger, supplemental v3 receipt/ledger and imported reader by actual hash. Match all 58 clearing IDs and magnitudes; include all actual zero-ST layers and nonzero-ST comparison layers across all 36,230 maps. Identity includes scenario, OFE, coarse layer, map, event sequence, clock, parent invocation and initialization epoch. Validate complete framing/support, finite payloads and MAP entry/exit identity before analysis. A stale last-map context on an ordinary boundary is not an ownership ID: use chronological event sequence and the explicit OFE/layer pending identities.

Keep multiple pending clearing IDs, each endpoint and its censoring state. The prior 25 earlier next maps and 33 initialization-censored next maps must remain explicit; looking beyond initialization would require a declared new endpoint definition. Availability, negative components and invalid geometry are separate flags, not reasons to suppress an observed assignment. Aggregate WIN/WATBAL/IRS stock changes may be reported as net boundary changes only. Static PURK/EVAP/EVAPPM zero-setting sites identify candidates; existing observations do not select an executed internal producer or accepted ET/drainage/runoff contribution.

## Required multilevel controls

A concrete source/fixture/driver/runner declaration must precede native invocation. Include ST zero and representable positive controls around the absolute threshold, coherent and mismatched YST, nonzero NWFRZZ, partial/full frost and several layers. A necessary cross-layer case is shortage generated in an earlier layer, a zero-ST middle layer, then a later active layer: the zero-ST branch does not clear incoming shortage flag/carry. Compare with an otherwise matched nonzero middle layer. Layer-independent resets alone cannot validate this behavior.

Initialize every consumed COMMON scalar and active array explicitly; use actual includes, dimensions and noncolliding helper names. Check all inactive OFEs/layers/fine cells with sentinels, including NFINE-zero skipped support. Do not dereference unavailable historical fine arrays or consume stale native locals such as VARWAT in the zero branch. Assert unchanged ice/geometry and actual assigned SLSW/NWFRZZ, alongside ordinary output/state readback and finite results. Preserve source/include/compiler/linker/runtime identities, process output, failures and nonmutation evidence in a fresh destination. The build recipe must distinguish the pinned instrumented routine from pristine native source and demonstrate unchanged native arithmetic/control flow for whichever exact source it compiles.

## Reviewed identities

SHA-256 bindings:

- Prior compiled observer FRWATC: `f580544b80ef091edd87478ef8fb5f0a75632261c36c0d5828a28b2438f366ed`.
- Canonical native FRWATC: `a834dbe62497989e8f99945acc880cdb31ced4ccc88d31f215c91738a0a0f1c1`.
- Frozen history reader: `10fdf713328edda69c16659a3ea43799a9e2c40f314bcb87035efd416d61140e`.
- Frozen all-clearing v3 reader: `ce528ea0277194ca3e2adfc85fa0836022c6676e81f70fff265842863826f72e`.

No producer attribution, native correction or broader history campaign is approved by this design review. Reviewer writers are clear after scoped documentation lint.
