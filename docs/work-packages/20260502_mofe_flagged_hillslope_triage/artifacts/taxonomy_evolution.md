# Taxonomy Evolution (v1 to v2)

## What changed
v2 replaced the broad v1 sink with rule families that explicitly separate outlet severe saturation (D1), outlet mismatch (D2b), storage-pressure rows (D3), short-duration spikes (D4/D6a), medium-duration bands (D6b), and persistent severe rows (D6c). D2 was split into D2a and D2b, D3 removed the dead `soilwater_gt_porositycap_days` gate, and persistent severe rows were separated from v1 D5 logic. This converts the prior 114-row ambiguity into actionable buckets.

## Coverage delta
| family | v1 count | v2 count |
|---|---:|---:|
| D1 | 13 | 13 |
| D2 | 3 | 0 |
| D2b | 0 | 99 |
| D3 | 0 | 7 |
| D4 | 2 | 2 |
| D6b | 0 | 5 |
| D6c | 0 | 6 |
| D_UNCLASSIFIED | 114 | 0 |

## Disposition of v1 D_UNCLASSIFIED
| v1 family | v2 family | row count |
|---|---|---:|
| D_UNCLASSIFIED | D2b | 99 |
| D_UNCLASSIFIED | D3 | 6 |
| D_UNCLASSIFIED | D6c | 5 |
| D_UNCLASSIFIED | D6b | 4 |
