# Observer reader scientific prereview

Disposition: pending corrections below before observer execution approval. Source-v3 observation additions are scientifically sound: first-invalid records now retain hour and event sequence, and selected lateral details retain raw ST/UL/DRFC for native subtraction reconstruction. No implementation edits, native builds or model runs were performed by this reviewer.

## Confirmed issues

1. Domain summary calendar validation requires year/day >=1 for every slot. Actual pinned HK initialization uses year/day 0/0, passed unchanged by the logger. Admit exactly the initialization clock for HK slots 1/5 and validate their support separately from runtime slots 2–4. Do not relabel initialization as day one. Existing logger controls use 1/1 and do not exercise this actual clock.
2. The logger's invalid count includes nonfinite a/b/c/d, but the domain reader equates any bad count with a finite numerator/denominator extrema violation, and rejects all nonfinite summary values. In particular a nonfinite c/d witness with otherwise valid a/b cannot be represented by this rule. Preserve nonfinite observations as explicit domain/physical-support failure evidence, distinguishing them from malformed records. Define and test reconciliation between invalid counters, first-bad witnesses and extrema without assuming all invalidity is a nonpositive denominator. HK guard slot 5 also needs its own nonfinite-only semantics.
3. Selected detail/summary reconciliation checks counts and numerator/denominator extrema but not positive frozen exposure or maximum frozen thickness. Compare sum(c>0) and max(c) to the summary and reconcile invalid-domain counts where supported. Otherwise corrupted frozen labels can silently change the central active-frost coverage claim.
4. The flux reader does not compare BP_WBH_BEFORE to BP_WBH_PURK using ALLOC/SEEP, although the plan promises input/percolation validation. Either implement a separately source-bound equation and controls or narrow the declared claim explicitly, retaining this as an unresolved stage. Merely requiring operand records is not an accounting check.

## Accepted accounting with limits

The retained ET method distinction, accepted uptake/interception treatment, reference/geometry flags and separate arithmetic/zeroing allowances preserve prior reviewed semantics for four and nine layers. Signed relative coordinates remain distinct from absolute liquid/ice validity. These ST comparisons support a water-accounting interpretation only where ice, dry reference and geometry remain appropriately unchanged; flagged comparisons must not be promoted as physical closure solely because their arithmetic residual is small.

The initial domain controls exercise enabled/disabled logging, invalid witnesses, ordering/framing rejection and raw lateral subtraction. The flux controls cover both layer counts, seventeen malformed cases, physical/reference flags and four nonzero arithmetic comparisons. They do not close the domain initialization-clock or full-history support path: add a synthetic complete slot-2 calendar and initialization support test for the declared layer counts, with malformed coverage controls. This need not invoke a model.

The domain reader's passed flag denotes successful parsing/reconciliation, not domain validity: retain site bad counts and missing execution separately. Likewise flux parsing success can coexist with outside-allowance residuals or unsupported-state flags. The forthcoming campaign runner and public interpretation must preserve these distinctions.

## Reviewed bindings

- `docs/work-packages/20261101_retention_frost_consumers/artifacts/read_domains.py`: `fb71fb68201f02cd487bd78da8645a718606267c577ca32be8cb7c1c2739f74d`
- `docs/work-packages/20261101_retention_frost_consumers/artifacts/read_flux.py`: `e1d6a755cd9d881def3d07e67db4dbb4f300a28de3b4a38c8894a3ead038e4da`
- `docs/work-packages/20261101_retention_frost_consumers/artifacts/check_domains.py`: `1739f1f846aebb78fe3ef36c3827939272282046f2a1df3390fe7bfe213ae6d8`
- `docs/work-packages/20261101_retention_frost_consumers/artifacts/check_flux.py`: `8e296ad688a8f2fa33716a6b0da706340a9c51ed66f9c571f6b3e72e4e67363f`
- `docs/work-packages/20261101_retention_frost_consumers/artifacts/domain_logger.for`: `a84d15e17dda1e8ad337abf21d6836ff226e0c97d30eed56f59a7691887ee678`
- `out/retention-frost-consumers-20261101/observer-source-v3/receipt.json`: `84fc0f65b6a5ad91d1e0500ef1944c8cdaf5b2383c0a531d39365acf74295099`
- `out/retention-frost-consumers-20261101/domain-controls-v1/receipt.json`: `fa9a95aebf03e71ddef787168ad1474218a050c61b166e043a24106fff827473`
- `out/retention-frost-consumers-20261101/flux-controls-v1/4/receipt.json`: `6d0238415ba145e59a3e00f426cbae4ac4dd36f50e686ebff44ec887dfae8865`
- `out/retention-frost-consumers-20261101/flux-controls-v1/9/receipt.json`: `6d0238415ba145e59a3e00f426cbae4ac4dd36f50e686ebff44ec887dfae8865`
