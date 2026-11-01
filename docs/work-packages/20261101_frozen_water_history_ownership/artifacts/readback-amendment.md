# Complete the clearing ledger without rerunning native histories

The frozen execution reader excludes invalid coarse/fine states from physical
signature interpretation. Actual history review showed that this also excluded
observed positive NWFRZZ clearings from its ownership ledger. In zero-ks1,
independent paired native branch operands establish 20 actual clearings, while
only six appear in the original valid-state ledger. Negative coarse liquid or
ice at a mapping boundary can reflect a stale coordinate representation; it
does not establish negative fine-grid physical liquid or ice.

Preserve the executed reader, its receipts and every native history unchanged.
The supplementary reader `read_clearing_ownership_v3.py` is read-only and requires
an accepted pair and the exact previously validated trace hash. It records all
positive pre-clear NWFRZZ values that become zero under the actual recalculated
FROZEN gate, independent of coarse validity. It retains separate coarse/fine
component signs, geometry validity, mapping entry/exit stocks, every clearing
identity, and the first later observed mapping plus next initialization.

Next-mapping tracking is bounded by the next initialization: if initialization
occurs first, its endpoint closes the pending record. Multiple pending clearings
remain distinct through intervening mappings. Twelve ordinary later boundaries
per event limit redundant storage; initialization endpoints and the first next
mapping remain explicit. Numeric matches do not establish causal recovery or an
annual external water-loss flux.

Supplement v1 tracked all clearings and initialization; v2 additionally retains
the intervening first mapping and its zero-ST branch. Both attempts remain in
private evidence. No native rerun or altered native parameter follows from this
analysis correction. Authored controls verify inconsistent coarse state does not
suppress a clearing, two pending identities survive, and the next-map join is
correct. Independent branch extraction must reproduce every clearing identity
and magnitude before acceptance.

V3 explicitly labels next-map endpoints censored by earlier initialization and
binds its own source, imported reader, accepted pair receipt and original ledger
before/after reading. An initialization-before-next-map control verifies the
censor label. V1/V2 attempts remain retained; V3 is the final supplemental reader.
