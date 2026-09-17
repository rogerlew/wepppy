# C08/C09 report dependency performance discovery

Disposition: sufficient local evidence for the proposed provenance design and
budgets below. This is a preimplementation baseline, not report freshness or live
runtime acceptance. No production/test files or named run data were edited.

## Retained evidence and scope

- `benchmark_report_dependencies.py`; successful
  `reports_performance_baseline_revision3.json` and `.log` are the final evidence.
- Revision 2 is a successful earlier measurement. The initial JSON/log retain a
  harness failure: the disposable H.wat output parent had not been created. Its
  completed measurements and unchanged named-file generations remain valid.
- Actual source: `/wc1/runs/th/thespian-cleanness`, read through the maintained
  `weppcloud` container as UID 1000/GID 993. Python audit guards reject writes to
  that run. Native summaries write only to the retained artifact output directory.
- `reports_performance_outputs/09b0f891f7e7/` retains actual native H.wat output
  and actual DuckDB landuse output. H.wat rows exactly equal the existing cache
  (10,199 rows, eight columns); landuse output has nine rows/nine columns.
- Detached Watershed loading uses the actual disk decoder with Redis disabled
  only in this benchmark process. The run already has the current NoDb version;
  no migration or logger initialization was invoked. This measures disk acquisition,
  not the normal singleton/Redis hit path.
- C08 timing uses the actual existing cached report constructor with a guard
  that fails if it tries to rebuild. C09 has no existing cache on this run: its
  actual query is measured with catalog activation prohibited, then its actual
  constructor reads a newly generated disposable cache. No synthetic report rows
  stand in for either report.

All ten measured named source, catalog, version and cache generations retained
device/inode/size/mtime/ctime. No OS page-cache drop occurred. Every operation
recorded zero `/proc/self/io` physical `read_bytes`: **helper-cold is not
cold-storage evidence**. Python binary-read counters measure digest content bytes
exactly; native logical reads are whole-process `rchar` deltas, not unique bytes.
Audit/instrumentation overhead is included in timings.

## Actual dependencies and measured cost

| Input | Bytes | Selection |
| --- | ---: | --- |
| H.wat | 81,150,978 | Actual baseline report path |
| H.wat compact cache | 292,036 | Existing version-1 cache |
| Watershed NoDb | 8,994 | Actual hydrated summary keys: 217 hills, 87 channels |
| Hillslope table | 32,414 | Actual translator fallback and C09 catalog path |
| Channel table | 17,710 | Actual translator fallback path |
| Loss hill table | 13,059 | Actual C09 catalog path |
| Landuse table | 13,977 | Actual C09 catalog path |
| Query-engine catalog | 136,693 | Fresh C09 resolution and alias metadata |

The three C09 files total 59,450 bytes. The actual catalog chooses the direct run
files here; permitted parent selection is not a performance claim from this run.
The JSON records the exact selected paths and effective identifier alias SQL.

| Operation | Mean elapsed | Content/logical reads per operation |
| --- | ---: | --- |
| H.wat first digest observation | 273.04 ms | 81,150,978 digest bytes |
| H.wat during admission | 266.73 ms | 81,150,978 digest bytes |
| H.wat admitting digest | 284.76 ms | 81,150,978 digest bytes |
| H.wat settled digest, 100 calls | 0.224 ms | Zero digest bytes |
| Native H.wat distinct-ID scan, three calls | 139.14 ms | About 4.26 MB process logical reads; 217 IDs |
| Actual Watershed detached disk load | 3.79 ms | About 9 KB logical reads |
| Actual summary-key translator factory | 0.204 ms | No source content reads |
| Effective mapping for retained 217 IDs | 0.184 ms | No source content reads |
| Mapping canonical JSON | 0.072 ms | No source content reads |
| C08 complete proposed settled observation | 4.10 ms | Zero digest bytes; actual NoDb disk hydration |
| Isolated actual Parquet translator fallback | 14.88 ms | Actual two-table DuckDB acquisition |
| Existing C08 full cached report, 20 warmed calls | 10.32 ms | Compact cache only |
| Existing C08 compact Parquet read alone | 2.89 ms | Compact cache only |
| Native summary into disposable cache | 936.72 ms | About 46.84 MB process logical reads |
| Fresh C09 catalog, selected paths and aliases | 2.54 ms | 136.7 KB catalog logical reads |
| Three C09 first/admitting digests | 3.91 / 3.85 ms | 59,450 digest bytes |
| Three C09 settled digests, 100 calls | 1.391 ms | Zero digest bytes |
| C09 complete proposed settled observation | 4.08 ms | Zero digest bytes; fresh catalog read |
| Actual C09 DuckDB report query | 33.02 ms | About 170 KB process logical reads |
| Actual C09 disposable cached report | 2.73 ms | 7,450-byte compact cache |

“Proposed observation” measures the actual resolver/hash/translator components
composed by the probe; it is not a yet-implemented report cache-hit path. C08's
observation includes a source digest, actual detached hydration, actual effective
mapping over retained source IDs and canonical JSON. C09 includes fresh catalog,
selected paths, effective aliases, three source digests and canonical JSON.

The Parquet fallback measurement clears summary fields only on an isolated
hydrated in-memory object. It exercises the actual existing translator method
against real selected tables and produces exactly the same mapping. It does not
claim the named run selects that branch. The persisted-key branch is the actual
run behavior.

## Proposed local acceptance budgets

Use means of at least 20 warmed cache-hit operations on this same workload; these
are engineering regression budgets, not latency guarantees or storage SLAs.

1. Settled digest checks retain the shared submillisecond per-file mean and read
   zero dependency content bytes. C08 performs no native H.wat ID rescan on a
   matching cache hit. Its effective mapping is reevaluated against retained IDs
   already bound to matching source content.
2. Added settled C08 observation work: at most 10 ms mean for the persisted-summary
   branch and 30 ms mean for the existing Parquet fallback branch. The latter
   preserves the real native/DuckDB translator cost instead of introducing a
   separate mapping implementation. Proposed warmed end-to-end cache-hit targets
   are 30 ms and 50 ms respectively, against a measured 10.32 ms current baseline.
3. Added settled C09 observation work: at most 10 ms mean, including a fresh catalog
   and effective alias selection. Proposed warmed end-to-end cache-hit target:
   15 ms mean against the measured 2.73 ms current cache baseline. Matching hits
   should not execute the aggregation query.
4. On this warm filesystem, budget about 0.30 seconds per full 81.15 MB H.wat
   digest, with a 0.35-second local mean ceiling before investigating regression.
   Count full digest passes explicitly: two pre/post build observations cost up
   to 162,301,956 content bytes and roughly 0.60 seconds here. A redundant third
   observation adds another complete source read and should be explained. Do not
   confuse helper admission with a settled hit: new observations rehash during
   the one-second admission period.
5. A warmed helper-cold matching C08 hit should fit about 0.40 seconds with one
   full source hash, retained-ID mapping and compact report construction. A new
   C08 build has roughly 1.08 seconds native scan/summary baseline plus pre/post
   hashing, mapping and compact provenance attachment; use a provisional 2-second
   local mean target and verify the implemented path. C09's three small files
   do not justify another cache layer; its real query remains about 33 ms.

These budgets allow local scheduling noise: the first C08 constructor was 142 ms
in revision 3 versus 46 ms in revision 2, while warmed means were 10–15 ms. They
must not be treated as per-request maxima. After implementation, rerun the same
source comparison and add actual provenance hit/build instrumentation rather
than relabeling this composition as end-to-end implementation evidence.

## Remaining acceptance boundaries

Measure implemented compact provenance annotation/publication and actual guard
counts. Verify Roads mapping changes, legacy/cache-only states, catalog parent
selection, archive relocation and producer errors in regression/runtime work.
No Roads-sized performance workload, cold storage/NFS behavior, concurrent
writers or browser report request was measured here. The existing baseline
freshness failures remain documented in `reports_freshness_baseline_review.md`;
these timings do not close them.
