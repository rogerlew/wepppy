# Scientific execution prereview

Initial disposition: not approved for the first freeze. The bounded six-scenario
scope, parity gates and unresolved-ownership language are scientifically sound,
but the history reader needs the corrections below before invocation. This is
a preexecution review; no native build or run was performed by this reviewer.

## Required reader corrections

1. H detection must use actual D0_CLEAR_PRE/POST branch operands. Direction0
   recomputes FROZEN from fine support before clearing NWFRZZ; entry FROZEN can
   be stale following phase evolution. Testing entry FROZEN can therefore miss
   a real positive clearing or classify the wrong gate. Require a matched
   available branch pair, positive pre-clear NWFRZZ, zero post-clear NWFRZZ and
   the actual recomputed frozen-support condition. Keep entry state separately.
2. Distinguish the physical double ST-minus-YST difference from the native REAL
   request. Use the observed D1_REQUEST operand where executed, independently
   check it against float32 subtraction, and retain both values and their
   rounding difference. The zero-ST branch has no D1_REQUEST; its physical
   request remains inferable from the input state and must be labeled separately.
   Do not present double subtraction as an observed native-local operand.
3. Retain invalid physical coarse stocks and geometry as invalid, including
   negative reconstructed liquid/ice, negative NWFRZZ, nonpositive DG and frozen
   support outside its layer. Current fine-only negative checks do not fulfill
   the declaration. Never clip values or infer validity from a positive total
   that hides a negative component. Invalid state ranges may be reported but
   must not become physically valid loss estimates.
4. Validate required branch support per map/direction/layer and complete daily
   observation support before interpreting branch absence. Missing or G-marked
   required operands must suppress that layer's inferred signature/absence and
   receive an explicit unavailable disposition. Preserve the distinction between
   omitted evidence and a correctly observed zero request or branch count.

Add meaningful controls for stale entry FROZEN versus actual clearing support,
missing required branch records, unavailable gate operands, native-versus-double
request accounting and invalid physical components. Existing12 malformed-trace
controls are useful structural checks but do not establish these semantic cases.
Freeze the amended reader/controls/declaration separately; do not replace the
original freeze or previous control receipt.

## Scope and accounting accepted in principle

F and G are threshold-exposure signatures, not automatic water-loss events.
Signed physical stock residuals and the valid branch path establish their
observed effect. The explicit warning that final VARWAT is not necessarily
unapplied water is correct. Unavailable snapshot support is not filled with
zeros. Profile residuals are only computed with complete available layer support.

The H ledger retains independent clearing identities through later maps and
limits repeated boundary storage without summing those observations. A next
INIT_POST endpoint is an observed subsequent state, not causal recovery. Composite
frost blocks and coarse WINTER/WATBAL boundaries cannot close all intervening
changes; that unresolved language must remain. No annual lost-water, original-run
frost causality, GRNA delivery or full physical acceptance is justified.

The six complete scenario baselines/observers, runtime KSFLAG observations,
29 synthetic parity controls and mandatory recovery of all five signatures are
appropriate gates. Synthetic signature recovery alone will not catch stale
FROZEN history detection, because the synthetic initial state is coherent;
the additional semantic reader control is therefore necessary.

## Initial reviewed bindings

- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/history-declaration.md` SHA256 `3892a75f28b01db27878e02bfefccc60361e8647ee14f7280fc6f174d7afe508`.

- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/read_history.py` SHA256 `5dae4936f6ce6ef53867ed91ad43095cb17f23001c2af1f32d0d9f6987fefe6d`.

- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/run_history_campaign.py` SHA256 `13c726ef215d13d0b431f5ad79bf18e66da967fd37c8fceac44ebd733999546f`.

- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/check_history_reader.py` SHA256 `1b2c88f57c2ce24be48c9a1e5396144b7cb73bd59ab4477990d83c4486bf0a4a`.

- `out/frozen-water-history-20261101/freeze.json` SHA256 `048fca314d536f9bfa5477443400367faca2c35d54d0b9508a6d3a8ad7931669`.

- `out/frozen-water-history-20261101/reader-controls-v1/receipt.json` SHA256 `c51a178e0d492dca5af615e3f94188e2ed9a6f1e3e0a0f40c6ddd88d4d2e9794`.
