# Dead Horse Creek: earlier-storm correspondence

2026-09-17 UTC. Read-only follow-up; no live climate rebuild or model changes.

## Assessment

**July 31 and August 2 are strong candidate triggering storms. July 31 is the leading working hypothesis for correspondence with the regional debris-flow episode.** The proposed July 30–August 2 sequence is supported by both saved climate products, a spatial Daymet screen, and—most decisively—measured rainfall at the East Fork Deadhorse gauge inside the modeled watershed.

This is stronger evidence than the previous centroid-only comparison. The remaining uncertainty is which storm produced the specific mapped deposit, rather than whether capable storms occurred in the earlier sequence. The paper's August 5–12 imagery bracket remains counterevidence to resolve, not a reason to abandon the candidate investigation.

## Newly retrieved observations

The canonical ScienceBase metadata and its file/get links worked. Earlier investigations had failed against direct S3 URLs; those failures did not establish that the gauge data were unavailable. This investigation retained the public USGS storm matrix, response inventory and gauge coordinates, with download receipts and hashes. No contact with authors or access-control changes were needed.

The gauge is GCEC2_EastForkDeadHorse, at 39.628533, -107.197311. Sampling the accepted domain raster confirms it is inside the modeled basin. Its values come from the 2021 storm matrix, not from CLIGEN or a figure digitization. [USGS data release](https://doi.org/10.5066/P9Z7RROL)

| Date | Gauge I15 (mm/h) | Daymet CLI I15 | GridMET CLI I15 | M3 using gauge I15 |
| --- | ---: | ---: | ---: | ---: |
| 2021-07-29 | 52.832 | 20.61 | 13.76 | 94.26% |
| 2021-07-30 | not supplied | 37.38 | 10.36 | — |
| 2021-07-31 | 77.216 | 24.75 | 9.84 | 99.70% |
| 2021-08-01 | 5.080 | 11.87 | 14.47 | 4.38% |
| 2021-08-02 | 78.232 | 14.14 | 2.14 | 99.73% |
| 2021-08-03 | 33.782 | 0.00 | 4.17 | 61.10% |
| 2021-08-06 | 4.064 | 0.00 | 0.00 | 3.88% |

The last column substitutes measured gauge intensity into the saved whole-basin M3 equation, with unchanged T/F/S and I15 P50 = 30.1168 mm/h. It is an illustrative rainfall-forcing comparison, not a new live assessment or a measured probability. The accepted basin is 26.8329 km², outside the displayed model study range, and SBS support remains 54.47%. Gauge rainfall is local; spatially uniform rainfall across the basin is not established.

For July 31, the saved Daymet and GridMET likelihoods are only 34.06% and 7.60%; the same equation with measured I15 gives 99.70%. For August 2, the corresponding values are 12.26%, 3.09% and 99.73%. Thus the low saved likelihoods on these candidate dates are largely a forcing mismatch, not evidence that the M3 equation cannot respond to the observed storm intensities.

The Daymet CLI's July 30 peak gives 70.99%, but no East Fork gauge value is supplied for that date in the storm matrix. Do not promote July 30 over July 31 merely because its synthetic peak is larger. July 29 and August 3 also have substantial measured peaks and should remain context for a sequence with potentially multiple sediment-mobilization episodes.

## Rainfall across the basin

The July 30–August 2 saved daily totals are 50.0 mm for Daymet CLI and 42.9 mm for GridMET CLI. The original Daymet centroid publisher total is 50.16 mm; the small CLI difference is consistent with the already-audited quantization path.

Five additional spatial-screen locations were chosen from basin cells nearest the 20/80-percent bounding-box positions and center. Their Daymet totals for the candidate window are 35.68–53.12 mm. This is a sampled screen, not extraction of every Daymet pixel. Over August 5–12, four locations have zero precipitation and the southeast location has 0.16 mm. At the actual East Fork gauge coordinate, Daymet has 0.13 mm on August 6, when the gauge storm matrix records I15 = 4.064 mm/h. The centroid's zero therefore cannot stand for every pixel or prove no rain anywhere in the watershed.

On August 3, the matrix records gauge I15 = 33.782 mm/h while Daymet reports zero daily rain at the gauge coordinate. This is a concrete same-date discrepancy worth following in an occurrence/timing evaluation. Daily reporting boundaries must still be aligned before labeling all such differences true misses. The matrix contains selected storms and unspecified gauge entries, not a complete continuous gauge wet/dry series; do not calculate a general occurrence-error rate from it.

## Timing and imagery evidence

The paper reports five of six outlet fans with known timing on July 31, and identifies that date as the likely Grizzly Creek episode. Dead Horse Creek's deposit is separately assigned approximately August 5–12 using Planet imagery, with no unique triggering storm. Figure 5 is a lidar-difference map, not a dated before/after Planet pair. The post-event lidar was acquired August 24, so its change map cannot discriminate these July/August candidates. The downloaded supplement contains gauge comparisons (Figure S7), other figures and a French Creek video; it does not supply a dated Dead Horse Creek Planet image pair or scene IDs that independently establish the bracket. [Paper](https://nhess.copernicus.org/articles/24/2093/2024/)

The 2021 storm matrix marks regional debris-flow response on July 29, July 31 and August 3, and zero on August 2. That regional flag is not a basin-specific negative observation at Dead Horse Creek. It makes July 31 the stronger regional match, while the East Fork gauge's August 2 peak keeps August 2 a serious local candidate. [USGS data release](https://doi.org/10.5066/P9Z7RROL)

The strongest discriminator would be the actual Planet scenes and deposit footprint: a clear unchanged deposit area after August 2 would reject those earlier dates for that deposit; obscured or inconclusive imagery would leave them viable. Neither condition was demonstrated in the assets available here. No event date has been silently reassigned.

## Evidence, validation and next step

- [Gauge/CLI comparison](gauge_cli_comparison.csv) and [plot](gauge_cli_comparison.png).
- [All saved candidate durations](candidate_all_durations.csv); independently recomputed M3 probabilities agree within 1e-12.
- [Spatial sampling receipt](spatial_receipt.json) and [daily matrix](spatial_daily_pivot.csv).
- [Gauge downloads](gauge_downloads.json), canonical metadata response and raw CSVs; [supplement receipt](supplement_receipt.json).
- [Preservation check](preservation.json): both saved event tables retain their original manifest hashes.

Working ranking: July 31 first; August 2 second; retain July 29/August 3 as adjacent alternatives or contributing episodes. Pursue the dated Planet evidence and, if obtainable, continuous gauge timestamps to decide between storm dates. The current evidence supports treating the earlier sequence as a leading candidate and using observed storm intensity for further M3 correspondence work.
