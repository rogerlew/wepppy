# Reasonableness Checks - SSURGO Corestrictions `kslast` Viability

Generated: 2026-05-23 00:54:49 UTC

## Field and Structural Checks

Reasonableness checks are computed on the sampled component set captured in `component_sample.csv`.

| Ecoregion | Structural failures (`resdepb<resdept`, thickness mismatch, negative depth/thickness) | Bedrock mean depth (cm) | Non-bedrock mean depth (cm) | Semantic direction pass |
|---|---:|---:|---:|---:|
| Marine West Coast Forest | 0 | 99.24691358024691 | 88.21739130434783 | fail |
| Cascades | 0 | 99.83185840707965 | 88.0 | fail |
| Sierra Nevada | 0 | 103.17460317460318 | 113.8695652173913 | pass |
| Mediterranean California | 1 | 67.03125 | 34.54545454545455 | fail |
| Columbia Plateau / Intermountain Basins | 0 | 45.2970297029703 | 69.47058823529412 | pass |
| High Plains / Northern Great Plains | 0 | 65.03333333333333 | 51.925 | fail |
| Central Corn Belt Plains | 1 | 115.4 | 65.87654320987654 | fail |
| Ridge and Valley / Blue Ridge | 0 | 76.26573426573427 | 74.0 | fail |
| Southeastern Plains | 0 | 93.5 | 76.0 | fail |
| Southern Coastal Plain | 0 | 79.61111111111111 | 71.44444444444444 | fail |
| Mississippi Alluvial Plain | 0 | n/a | 58.642857142857146 | pass |
| Mojave/Chihuahuan Basin and Range | 1 | 42.470588235294116 | 48.041666666666664 | pass |

## Pass/Fail Summary

- Regions with unresolved anomalies: 9 / 12
- Detailed anomaly counts are in `reasonableness_anomalies.csv`.

## Unresolved Anomalies

- Any region with non-zero structural failures is flagged for guardrails and fallback-first behavior.
- Regions where bedrock mean depth is not shallower than non-bedrock mean depth are treated as semantic-risk regions.
- Regions with restrictive-present sample shortfalls are treated as infrastructure-constrained investigation signals (SDA extraction/runtime limits), not rejection-only evidence about dataset completeness.
