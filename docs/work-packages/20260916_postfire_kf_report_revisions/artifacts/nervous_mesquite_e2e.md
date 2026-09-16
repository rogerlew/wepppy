# nervous-mesquite end-to-end acceptance

PASS after the forest restart, 2026-09-16 UTC. Normal authenticated browser Run
submitted real RQ job `b5232960-674f-4468-ba0f-a67588bed59d`; accepted attempt
`0ea9c1f5b0964b22ba7f1b457c1a6c9f` completed at 23:10:07 UTC. New source policy:
`statsgo_kffact_1995_cog2025_v1`, predictor schema 3. No manual Kf preparation.

## Independent numerical result

| Quantity | Previous acceptance | New acceptance |
| --- | ---: | ---: |
| Mean K / Kf | 0.3371615965 | 0.1393960062 |
| T | 0.7412672049 | 0.7412672049 |
| Normalized dNBR F | 0.5410453360 | 0.5410453360 |
| I15=24 mm/hour probability | 85.63% | 72.19% |
| Common valid cells | 77,667 / 77,669 | 77,667 / 77,669 |

P50 intensities are 19.0053, 15.2502 and 12.1182 mm/hour for 15/30/60 minutes.
The historical USGS value is not an equality target: delineation/other inputs
still differ. Kf is obtained from the approved bounded source, not a fitted scalar.

`validate_live.py` independently recomputed T/F/S from retained rasters and all
8,067 event probabilities, 12 design values, three inverse values and every
exported curve point. Source request/artifact hashes match; seven bounded requests transferred
327,680 bytes for a 340 × 326 native window. See
[numeric evidence](nervous-mesquite_numeric_validation.json).

## Browser and records

`browser/nervous-mesquite/` contains PASS evidence, actual job tree, all three
window payloads, SI/English curve CSV, actual downloaded CSV, report/control/mobile
screenshots and attachment SHA-256s. P50 focus, keyboard marker selection,
expanded numeric table, unit changes, ordinary source browsing and reload to the
same accepted identity passed. NOAA is labeled statistical design rainfall;
GridMetPRISM event peaks are labeled modeled/disaggregated despite calendar dates.

Shared Unitizer uses the existing mm/hour → in/hour factor 0.0393701; this is an
approximate display conversion, not an exact reciprocal of 25.4. Independent
checks use that recorded factor; scientific tables/curves stay in canonical units.
No global conversion or calibration change was introduced.

## Preservation and archive

[Preservation evidence](nervous_preservation.json) covers 387 protected files.
All scientific input content is unchanged. One NoDb byte difference is solely
`climate.nodb`'s existing `_nodb_mtime` serialization timestamp; its settings are
identical. All earlier attempt bytes are unchanged. Public result copies are
expected to advance to the new acceptance; their before-state is archived.

The canonical archive/restore engine round-tripped all 137 generated module
records on an isolated copy, including actual request bodies, native/aligned Kf,
metadata and both source manifests. [Archive evidence](nervous_archive_roundtrip.json)
records the disposable restore path and every file hash. The live project was
never restored or rolled back.

## Retained intermediate diagnostics

The first harness listened for legacy `/run-m1`, while the UI correctly submitted
`/run`. The model succeeded; subsequent browser verification resumed that exact
job without another model run. A later harness tried downloading from collapsed
native details; opening the details fixed the test. Both failed harness records
remain under `browser_failed_startup/` and `browser_failed_harness/`; neither
required a product change or replacement of the accepted model result.
