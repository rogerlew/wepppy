# Report cache freshness baseline review

Independent correctness reviewer: `freshness_correctness`, 2026-09-17 UTC.
Scope: remaining inventory C08/C09 only. No production code/tests edited and no
named project mutated. **Both consumers have confirmed stale reported results;
neither inventory item is closed or approved for implementation by this review.**

## Actual report evidence

`reports_freshness_baseline_probe.py` creates disposable parquet fixtures and
executes actual report constructors. H.wat summaries use the installed required
native producer. Average annuals use real ReportQueryContext, catalog activation
and DuckDB queries. Only `Watershed.getInstance` acquisition is injected: an
isolated real Watershed object calls its real `translator_factory` against real
fixture tables. There are no mocked report rows, native summaries or query results.

The original JSON/log remain retained. The revision-2 JSON/log add the ordinary
newer-source C09 case. Both runs exit 0; revision 2 confirms **seven stale-report
cases plus three cache-only compatibility observations**. Cache invalidation is
used only on disposable fixtures as a control to obtain the correct rebuilt
result, never as a suggested operational repair.

| Finding | Severity | Actual stale result and rebuilt control |
| --- | --- | --- |
| C08 source bytes | High | Same-size/restored-mtime H.wat precipitation changes 1 to 9; a new report instance still returns 1 mm. Native rebuild returns 9 mm. |
| C08 translator | High | Real `watershed/hillslopes.parquet` Topaz mapping changes 101 to 301; cached report remains assigned to 101. Real translator plus native rebuild assigns 301. |
| C08 Roads manifest | High | Segment 900001 changes target WEPP hill 1 to 2 in a same-size/restored-time manifest. Cached result remains Topaz 101; native rebuild returns 201. Baseline cache/rows remain unchanged. |
| C09 loss bytes | High | Runoff changes 100 to 900 cubic meters for a 1,000-square-meter hill; report remains 100 mm/year, real DuckDB rebuild returns 900. Reproduced with restored timestamps and separately with source mtime explicitly newer than cache. |
| C09 area | High | Real hillslope area changes 1,000 to 2,000 square meters; report remains 0.1 ha and 100 mm runoff. Rebuild returns 0.2 ha and 50 mm. |
| C09 landuse mapping | Medium | Real landuse description changes Forest to Shrubs; cached rows remain Forest, DuckDB rebuild returns Shrubs. The joined landuse key/Topaz mapping are likewise consumed dependencies, not display-independent metadata. |

## Readers, actual dependencies and writers

`wepppy/wepp/reports/hillslope_watbal.py:__init__` reads version-1 cache rows and
rejects them only when H.wat mtime exceeds cache mtime. `_write_native_summary`
stores only `{"version": "1"}`; neither source bytes nor mapping identity is
recorded. `_build_summary` additionally consumes the effective WEPP-to-Topaz map
and, for unknown Roads segment IDs, the optional Roads manifest mapping.

`WatershedOperationsMixin.translator_factory` in
`wepppy/nodb/core/watershed_mixins.py:269` first uses persisted/in-memory
`_subs_summary` and `_chns_summary` keys, otherwise both hillslope and channel
parquets. It sorts IDs and constructs `WeppTopTranslator`; it does not simply
consume a `wepp_id` column from hillslopes.parquet. Fingerprinting only that one
parquet or only watershed.nodb would omit a supported translator source.

H.wat is produced by `run_wepp_hillslope_wat_interchange` in
`wepppy/wepp/interchange/hill_wat_interchange.py`, through native
`hillslope_wat_files_to_parquet`. `Wepp._run_hillslope_watbal` warms the report
after processing, and `Wepp.report_hill_watbal` serves it by output scope.
Roads writes `roads.segment.pass.manifest.json` in `roads.py` near line 5847;
the report's manifest reader intentionally tolerates absence/malformed entries
and falls back to raw segment IDs with logging. Those semantics must survive.

`average_annuals_by_landuse.py:40` accepts a cache solely by version and exact
display columns. `_build_dataframe` joins `loss_pw0.hill.parquet`,
`watershed/hillslopes.parquet` and `landuse/landuse.parquet`; every one changes
actual report results in the retained probe. `ReportCacheManager.read_parquet`
in `helpers.py:134` has no source-freshness gate. The Flask route
`report_wepp_avg_annual_by_landuse` serves both HTML and CSV from this report.
This report is currently baseline-only; adding Roads support is outside this fix.

Normal writers include native `run_wepp_watershed_loss_interchange`,
`topo/peridot/peridot_runner.py` hillslope/channel table publication, and
`Landuse.dump_landuse_parquet` (`landuse.py:2326`), which updates its catalog
entry but does not invalidate this report. Repository search found report-cache
directory removal in `rq/project_rq_fork.py:_clear_reports_cache`; that fork path
does not establish ordinary rerun invalidation. C09's newer-source probe confirms
this is not limited to unusual timestamp-preserving writes.

## Legacy and valid states requiring a checkpoint decision

- C08 current version-1 cache and baseline legacy cache under
  `wepp/output/interchange` remain readable with both source and watershed mapping
  removed. The real probe prevents rebuild to verify this behavior. Existing
  `test_hillslope_watbal_uses_cache` and
  `test_hillslope_watbal_reads_legacy_cache_without_native` also explicitly preserve
  legacy/cache-only access, including a legacy cache with source still present
  when the native API is unavailable. Do not erase that availability by a blanket
  cache-version bump or mandatory source/native lookup on every cache hit.
- C09 also reads version/schema-compatible cached results after all three sources
  disappear. The actual probe records this observed compatibility; there is not
  an equally explicit canonical cache-only requirement yet. Ratify its treatment
  before making source absence a new failure for existing caches.
- Sources present but changed, sources absent, valid empty sources, absent Roads
  manifest, malformed Roads manifest, and unknown baseline IDs are distinct
  states. Keep baseline unknown-ID failure and Roads manifest/raw-ID fallback.
  Preserve nullable native schema, native-only production and empty outputs.
- Existing caches have no historical source digest. Current bytes cannot prove
  the historical cache was built from them. Never attach a newly computed source
  digest to old cached rows and call that verified migration. One-time rebuild
  where dependencies/native producer are available is the minimal trustworthy
  upgrade; preserving legacy reads without those prerequisites needs an explicit
  historical/unverified compatibility decision, not an invented identity.

## Smallest compatible fix constraints

Use additive dependency provenance for these two cache keys. Keep the shared
ReportCacheManager's other consumers unchanged unless separately reviewed.
For C08 bind source scope/path/content, the effective translator mapping and
Roads manifest presence/effective mapping policy. For C09 bind all three actual
query inputs and relevant path selection. Query-engine catalogs can point through
`CatalogEntry.fs_path` to supported physical/parent-run locations; use the same
resolver as the real query rather than assuming `<wd>/<logical name>` is the
consumed file or introducing a new containment restriction.

Reuse the owned ordinary-file digest helper for compatible settled reads while
retaining a bounded cold/build verification path. Large H.wat inputs must stay
in the native streaming producer; do not introduce full-source pandas hashing
or Python aggregation. Mapping snapshots can use bounded translator data and
must preserve the actual selection precedence described above.

Bind provenance to the generation actually built: capture before work, verify
after it, and publish a matching cache/provenance pair. Appending a source digest
after native/query output publication can mislabel old rows as a new generation.
Retain native atomic cache publication, access bits/umask and prior bytes on
failure. Concurrent report requests and failure between parquet and JSON writes
need explicit handling; the current version-only sidecar is not sufficient
evidence of a matching newly introduced dependency manifest.

Canonical owner for C08 is `docs/schemas/output-scope-contract.md`, Hillslope
water-balance summary cache: it explicitly names version 1, legacy reads and
mtime-based rebuilding, so amend it before behavior changes. C09 currently has
module README/report-guide intent rather than a complete canonical freshness
policy; promote the specific dependency/legacy rules into a schema contract.
Its README's cache location is stale; actual storage and report catalog use
`wepp/reports/cache`. Update that provenance documentation with the eventual fix.

Final acceptance must exercise the seven real stale cases, unchanged-byte
metadata churn, legacy/cache-only states, malformed/missing dependency behavior,
baseline/Roads isolation, concurrent publication and warm/cold performance on
representative large H.wat. Named runs remain read-only for inventory; native
rebuild/route/archive acceptance belongs on disposable copied projects after
the independent contract checkpoint. No implementation is authorized by this
baseline artifact alone.
