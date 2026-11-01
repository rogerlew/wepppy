# Twelve reset controls: scientific execution prereview

Status: approved for the exact finite twelve-process declaration bound below, subject to independent implementation approval and the runner's declared gates. No native compilation or model execution was performed by this reviewer.

The exact fixtures cover coherent unfrozen/partial/full-frost references, a dry baseline, both signs of imposed reference mismatch, the exact-zero versus 2^-25 positive-ST discontinuity, positive submillimeter support, multilevel carry bypass, and a clearing followed by prescribed zero storage and repeated reset. Decimal inputs introduce ordinary REAL rounding; acceptance appropriately uses actual emitted values, not ideal decimal identities. Full frost has zero fine unfrozen support and positive NW; partial/full water allocations fit the declared pore geometry. Signed reference mismatches and imposed coarse depletion are explicit interface experiments, not reconstructed historical fluxes.

The carry fixtures have a nominal 5 mm first-layer request against approximately 1 mm available fine water. Native shortages accumulate to approximately 4 mm after that layer. The zero middle layer resets itself and leaves the shortage for the bottom layer; the positive middle layer has enough liquid to absorb it. Paired checks compare downstream stocks. The driver does not emit the native final carry variable, so no zero-final-carry observation may be claimed. Inspect quantitative changes in final readback before treating a direction-only paired assertion as a complete carry budget.

The last case prescribes ST=0 in both active layers after direction 0, then calls direction 1 twice without advancing YST. Exact equality of the last two states is the appropriate idempotence condition. A repeated nonzero nominal residual is expected when the old YST remains; it is not a second loss. The top-layer direction-0 NW clear must be visible independently of subsequent reset changes.

Driver initialization covers every consumed active stock and geometric input, initializes fine cells, and retains inactive whole-array sentinel checks. The exact-zero checks establish dry assignments, cleared NW, unchanged ice/geometry and unchanged coarse/reference fields. The decomposition uses sums of absolute primitive terms for its double-precision reconstruction bound; this is not a physical water-closure tolerance. The additive v2 reader now retains per-cell negativity, negative NW and invalid geometry flags, resolving the earlier diagnostic omission. Its coordinate offset still includes ice-coordinate disagreement as well as support geometry, and must be described accordingly.

The complete unchanged native routine and twelve includes match their frozen source hashes. All declared file/tool/runtime bindings were verified directly. This approval covers twelve fresh processes only, no adaptive fixture changes, native correction, full-history rerun or parameter default change. Preserve any failed build/process and obtain a new binding before altering execution dependencies.

## Exact bindings

- `control-freeze.json`: `44285312355ea8586da91db5d6e4adcb7df5d8367f1041b9d5a10af157a2634b`.
- `reset_driver.for`: `6557fce8d8efa84d7ff0fb48a470b579a180fcbb282cc83faebc1727b40e250c`.
- `reset-cases.json`: `76ca8b887b89c7cbae46b106413543c45464f1697ddeeb23f822bd69f8c64ad7`.
- `run_reset_controls.py`: `ecf47419c4adcb6d372b91b0ed7024b74660e7d82a742f206675c0feb624f5b7`.
- `audit_resets_v2.py`: `c035b0698573508cfa7e84f34c6db5d864ce81f584efce05e6a91e133dc521aa`.
- `control-declaration.md`: `e17f8e3e5537a13bb42919c232018c7eb4df4720c25abbc872e207ecbdd1a9d4`.

Writer status: clear; no prior root or native source writes.

## Pre-execution runtime-binding amendment

Scientific approval also applies to the refreshed freeze below. Cases and driver are unchanged. Runner changes retain process timing and inspect actual linked runtime libraries against all five pinned library identities; they do not alter model inputs or scientific expectations. All refreshed dependencies verified before this approval; no native invocation by this reviewer.

- `control-freeze.json`: `44285312355ea8586da91db5d6e4adcb7df5d8367f1041b9d5a10af157a2634b`.
- `run_reset_controls.py`: `ecf47419c4adcb6d372b91b0ed7024b74660e7d82a742f206675c0feb624f5b7`.
