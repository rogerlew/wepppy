# Forest historic PRISM acceptance

Date: 2026-10-08 UTC. Run: [chemotherapeutic-scope](https://wc.bearhive.duckdns.org/weppcloud/runs/chemotherapeutic-scope/disturbed9002_wbt/).
The user authorized implementation, end-to-end execution and dev Compose restart.

## Outcome

Both multiple methods completed the authenticated menu → RQ climate → prepared
WEPP inputs → hillslope/watershed WEPP workflow. Each WEPP job tree finished all
18 jobs. The run is left on observed PRISM 800 m, nearest-cell mode, 2019–2021,
station `wy481175`, explicit seed `84568`, binary `wepp_260430`, and no additional
precipitation scaling. These are bounded acceptance settings, not changed defaults.

| Check | Multiple / PRISM revision | Multiple / nearest cell |
| --- | --- | --- |
| Hillslopes | 104 | 104 |
| Calendar | 1,096 days, including 2020 leap day | Same |
| Daily source cells | 1 centroid cell | 24 cells |
| Distinct wet-day calendars | 1 | 24 |
| Hillslope three-year rainfall range | 1,860.8–2,271.5 mm | 1,875.5–2,224.6 mm |
| Hillslope wet-day count range | 628 | 625–653 |
| Daily model water-balance rows checked | 113,984 | 113,984 |
| RQ jobs finished | 18 | 18 |

Every prepared `wepp/runs/p*.cli` was byte-identical to its assigned generated
climate. Every hillslope's WEPP daily precipitation matched that CLI. Checks
covered calendar completeness, finite/nonnegative weather and model variables,
monthly precipitation ratios/temperature offsets for revision, native-cell PRN
quantization for nearest mode, identical unscaled same-cell weather, solar units,
shared GRIDMET wind and `Tdew=max(rawTd, finalTmin)` after revision. Both watershed
loss tables contained finite results. This establishes functioning integration;
it does not establish predictive skill or physical water-balance closure.

The nearest-cell staged acquisition/conversion/publication took 43.2 seconds
(`23:01:39.488`–`23:02:22.718` UTC), including 24 cell CLIGEN conversions and wind
retrieval. Of 72 cell/year partitions, 69 were newly extracted and 3 reused the
centroid cache. The centroid stage took 31.8 seconds with 3 uncached partitions.
These are one-workload timings, not a provider latency guarantee; revision and
post-build exports are outside these stage measurements.

## Source visibility and portability

Authenticated browser reload preserved dataset/mode and the nearest-cell label.
The source directory listing and gzip download returned HTTP 200; downloaded
bytes matched the retained source exactly. A ZIP of the live climate directory
restored **993 byte-identical files**, resolved **72 cell/year source partitions**,
and read all 24 source cells and 104 hillslope CLIs with `PRISM_CACHE_DIR` pointing
to a nonexistent path. No cache was deleted or moved. Canonical project
`archive_rq`/`restore_archive_rq` tests separately verify working/failed/complete
attempt retention; the live portability probe is explicitly a climate ZIP.

An isolated current Builder config selecting PRISM was persisted and reopened
using the exact reader-floor `e25299022` graph reader/catalog. The target project's
graph was not migrated. Earlier live reader-floor evidence also preserves old
writer/new-reader coexistence and historical schema-v2 validity.

The broad suite subsequently exposed a missing reader entry for the existing
single-input Builder variant. The append-only correction advances the aggregate
reader floor to `6781de988`. All four ordinary/single-input × single-/multiple-OFE
config cases then persisted and reopened with that exact committed reader,
without byte changes. Retain this aggregate floor for rollback; the earlier
ordinary-only floor is insufficient after a single-input variant is persisted.
Creation and explicit-refresh regressions passed; no climate numerical code or
completed watershed result changed.

## Runtime and recovery

Affected forest dev services were recreated through `wctl`, preserving Compose
identities and mounts. Workers were idle before recreation. Actual execution and
readback used worker UID 1000/GID 993 and `PRISM_CACHE_DIR=/wc1/cache/prism`.
The frontend bundle was built inside the configured container.

Snapshots under `/wc1/runs/ch/chemotherapeutic-scope/archives/`:

- `prism-integration-original-20261008`: original 788-file climate/WEPP/state backup
  and checksum inventory; stochastic PRISM, single, 50 years, seed override unset.
- `prism-integration-mode1-2019-2021`: accepted revision case.
- `prism-integration-mode2-2019-2021`: accepted nearest-cell case.
- `prism-integration-climate-portable.zip`: source portability evidence.

Do not restore NoDb snapshots while jobs are active. Normal rebuild is the first
recovery path. If runtime integration is rolled back, retain the capability reader
floor so newly stored graphs remain readable.

## Limits and observed diagnostics

The run's existing silent-pass CLIGEN quality-guard option is enabled. CLIGEN
reported convergence warnings, and the warning remains in persisted climate
state and the UI. Accepted source/CLI/WEPP readback does not certify generated
storm-shape quality. PRISM supplies daily aggregates; selected-station CLIGEN
still synthesizes within-day storm structure. No option/default was changed to
suppress these warnings.

PRN precipitation rounds to 0.254 mm and temperatures to whole Fahrenheit degrees;
trace rain can disappear. Release-manifest checks detect advertised revisions
but cannot prove atomic consistency between provider bulk and grid backends.
This three-year watershed test does not establish reliability for every CONUS
cell/year. OpenET and AgFields mode 16 eligibility remains separate follow-up.

Across the 24 native series, raw mean dewpoint was below raw Tmin on 890–967 of
1,096 days per cell. The derived floor changed 890–971 days, reflecting final
quantized Tmin. These are retained source/model distinctions, not automatically
classified source defects. No positive rain day rounded to zero in this live
sample; the native adapter regression explicitly exercises that trace-rain case.
Maximum raw daily rainfall ranged 27.98–38.41 mm between cells. Counts are retained
in `forest-source-diagnostics.json`; neighboring series are not independent samples.

## Evidence

- `forest-climate-{1,2}.json`, `forest-wepp-{1,2}.json`: actual browser-submitted jobs.
- `forest-wepp-{1,2}-jobtree.json`: full RQ trees.
- `forest-readback-{1,2}.json`: per-hillslope hashes and numerical/model checks.
- `forest-evidence-2.json`: authenticated menu/browser/download checks.
- `forest-portability.json`: live-source ZIP restoration.
- `reader-floor-live.json`, `reader-floor-reopen.json`, `new-writer-project.cfg`:
  compatibility and persisted config evidence.
- `aggregate-reader-floor-reopen.json`, `new-writer-single-*.cfg`: both structural
  variants and both watershed representations reopened with reader `6781de988`.
- `forest_ui.cjs`, `forest_readback.py`, `forest_portability.py`,
  `reader_floor_reopen.py`: reproducible acceptance probes; credentials are read
  from the existing ignored secret file and are not retained in evidence.

Repository validation and final independent review are recorded in the tracker
and `correctness-review.md`.
