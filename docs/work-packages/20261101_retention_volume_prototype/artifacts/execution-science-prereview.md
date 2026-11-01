# Native execution scientific prereview

Disposition: pending two reader corrections below and the final execution declaration/fixture bindings. No native execution is approved by this version. No native build or run was performed during review.

## Accepted design and corrected items

The plan now describes freeze/thaw coverage as requiring actual runtime evidence. The producer adds a masked text comparison permitting only horizon FC/WP tokens to change. These close the two design-review items.

The six fixed pairs, unchanged observation binary, retained full histories and explicit limits on dynamic drainage/accepted-flux claims are scientifically appropriate. Copying the controlled horizon to three OFEs is clearly an experimental context. Zero-rock ordinary-output identity remains a useful control.

The reader's binary32 implementation follows the pinned SCON guard sequence: SM20 ceiling, pair adjustment and floors, FC/POR ratio adjustment, and final floors. Reconstructed conditions are correctly distinguished from observed branch flags. The CPM and UL reconstructions are consistent with the native expressions. Initialized UL-DRFC is correctly labeled as a reconstructed denominator, not an executed drainage division.

## Corrections needed

1. The reader requires SO_WBH_UL but ignores its operands, then compares executed hourly HK ratios to SCON-derived initialization quantities. This conflates clocks unless equivalence is demonstrated. Validate the actual SO_WBH_UL snapshot and derive the hourly comparison from its POR, dry reference and thickness, together with observed WBH_HK_FCUL. If FC theta is assumed unchanged, establish that against the pinned intervening source and cross-check observed FC. Preserve both SCON and hourly domain results when operands differ. Validate FCUL support and clock joins as well as ratios.
2. The reader records initialized ST without reconstructing it. The source updates the shared per-OFE SAT sequentially using the dry/(POR*CPM) lower bound, then computes ((SAT*POR)*CPM-dry)*DG and zeroes values below 1e-10. Reconstruct this using the actual parsed starting SAT and native arithmetic/order. Do not assume all layers retain the input SAT. This needs no added observation and substantiates initialized-stock claims.

The exact producer receipt/admission, final runner/reader and execution declaration still need binding before approval. A failed reader comparison must remain evidence rather than motivate an unreviewed native rerun. Static valid-domain flags must not be presented as complete-history physical admissibility.

## Reviewed bytes

- `docs/work-packages/20261101_retention_volume_prototype/artifacts/read_native.py`: `050cf8ec9d2a99f5ce23fd1e870f079d1ea973fbabf433f73a1bb82a606cae6d`
- `docs/work-packages/20261101_retention_volume_prototype/artifacts/run_native.py`: `0402ccbc2cb99a8a86147cbd99c6a051c3141f77adb4244429bfb9d124dd2753`
- `docs/work-packages/20261101_retention_volume_prototype/artifacts/produce_prototype.py`: `4047c307659964a401da242681ae81c48b5cf7d67ee06fc30d085fd1a38fa980`
- `docs/work-packages/20261101_retention_volume_prototype/prompts/active/prototype_execplan.md`: `b7dca0efbc2f7b640c14548dd146ef266b38f88032f356fbbdfc8e422100273e`
