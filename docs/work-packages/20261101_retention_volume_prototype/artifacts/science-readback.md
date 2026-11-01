# Scientific readback

Disposition: the twelve completed histories and versioned v3 readback support the declared initialization/observed-conductivity checkpoint. They do not support production promotion, freeze/thaw coverage or complete dynamic closure. No model rerun was needed or performed for the reader corrections.

## Corrected reader and actual support

The v3 reader reconstructs binary32 input weighting for the declared uniform two-horizon fixtures instead of widening the retention/mass tolerance. Pinned INPUT caps and converts density and fragment mass before resampling. The tiny deviation of bottom-cell consumed mass from nominal 0.85 is a weighting effect, not a changed cap. This specialized remapper is not a general INPUT implementation.

All twelve v3 cases pass with 17,532 daily calendar rows each. There are 174 initialized layer/OFE records: five pairs have four layers per OFE and 600 mm native support from 400 mm emitted support; chkey 85179901 has nine layers per OFE and 1600 mm native support from 1400 mm emitted support. Paired support is identical. Original failed readers, declarations and aggregate-hashing failure remain evidence. The v3 receipt verifies the original campaign inventory unchanged.

## Native interpretation

All 174 initialized expression-domain checks pass. FC/UL ranges from approximately 0.0666016 to 0.5292501; the smallest reconstructed UL-DRFC is 0.009783946 m. This denominator is initialization arithmetic, not an observed drainage division across the history.

The reconstructed SM20 ceiling is active in both zero-rock lanes and the baseline low-density 85179904 lane, twelve records each. No reconstructed FC/SM20 pair or FC/POR ratio adjustment occurs. Therefore 'no guards' would be incorrect, although these observed SM20-only interventions do not alter final FC/WP. Guard labels remain reconstructed from observed operands.

For chkey 85179904, original source BD is 0.78 g/cm3 while observed input/native density is 800 kg/m3 after the native floor. Its inverse was computed with source density, so native source round-trip is not exact even before retention guards. Keep original, emitted, remapped and realized density distinct.

I independently read the raw SCON records for all twelve histories. Representative OFE1 top-layer final volumetric FC values are:

| Source chkey | Baseline | Candidate |
| --- | ---: | ---: |
| 84543623 | 0.2800000012 | 0.2800000012 |
| 84543461 | 0.1757790297 | 0.1359850764 |
| 84543462 | 0.1461248696 | 0.1570144296 |
| 87913598 | 0.1176144928 | 0.1400032490 |
| 85179904 | 0.3314606249 | 0.2238373309 |
| 85179901 | 0.0649280772 | 0.0879849270 |

The opposing directions are expected from the conditional mass-versus-volume algebra. These are realized controlled native parameters, not measured physical accuracy.

## Stock coordinates and frost coverage

Initialized ST and UL changes must not be described directly as added/removed absolute water. I independently computed each OFE's initialized absolute stock from raw SO_SCON_UL as sum(ST + dry*DG). Across the six pairs and all three OFEs, the largest absolute candidate-minus-baseline difference is 7.868065310390193e-9 m. In contrast, the 85179904 OFE1 ST coordinate rises by approximately 29.25634 mm. The changed dry reference accounts for that distinction; small absolute differences reflect separately rounded native arithmetic. This is an initialization comparison, not a dynamic conservation closure.

I independently summed both payloads of every raw WFR_SUM_CALL record in each history. All twelve report 84,331 weather-eligible gate events and 84,331 KSFLAG skips. Pinned WINTER increments the first counter before the KSFLAG test and the second on the skip branch. Therefore actual frostN calls are zero in this panel. Both WFR_SUM_GUAR counters total zero. Counting summary log lines as frost calls would be incorrect. This experiment does not exercise the needed active freeze/thaw validation.

The zero-rock pair has identical seven ordinary outputs. The five changed pairs differ in four or seven ordinary outputs, as retained in v3. Such differences demonstrate sensitivity, not improvement or calibration. Production admission remains blocked on source-assumption compatibility and the separately required dynamic-domain, active freeze/thaw, accepted-flux and overflow-ownership evidence.

## Bound evidence

- `docs/work-packages/20261101_retention_volume_prototype/artifacts/read_native_v3.py`: `1f90052ad369330ee674145169622ef22c7a7ebf2918b8a4388b80bed350912c`
- `docs/work-packages/20261101_retention_volume_prototype/artifacts/read_campaign_v3.py`: `e5417ff93b45380f73bdc4ef3f3b21f04b5ad988d4f036f4ad30e1e8cd32c220`
- `out/retention-volume-prototype-20261101/reader-controls-v5/receipt.json`: `31dffb6ad095da191dc8d4327739c706cc7b7bfae200bc7f0058ae4dd1de6880`
- `out/retention-volume-prototype-20261101/fixtures-v1/receipt.json`: `7e7197e1f4455075e8d177560a8a313720c408b17b70e165f26769ecc3ae7f7d`
- `out/retention-volume-prototype-20261101/campaign-v1/receipt.json`: `54f542ad6d5892c29fdd0f4fd3539674f229eebe0f415a9b7cf75264cf950354`
- `out/retention-volume-prototype-20261101/readback-v3/receipt.json`: `940ef768260c849f8f8dfdc29ebf3229758de80c83be669de41c3a35332cce73`
- `out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/native-probe/build/src/input.for`: `362a328510298eb86f682b248256ae43c8b36ca15b6cf2d6dd1887999ae275df`
- `out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/native-probe/build/src/winter.for`: `6dca46e762611ddd93e030d7fcc619af92922d614a4ddc1c44576b90ee9d86ff`

Review complete. Reviewer writers are clear; prior frozen roots were not modified.
