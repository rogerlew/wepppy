# D-Tale large-Parquet performance QA

Date: 2026-09-16. Scope: read-only representative native baseline and initial
implementation comparison. No named project or live D-Tale dataset was mutated.

**Disposition:** the measured source meets the checkpoint's settled per-file
digest budget and exact page check-count bound. Admission and eviction introduce
a material, explicitly measured cold-page cost. This is local accessor evidence,
not full service/browser performance acceptance or NFS validation.

## Source and reproducibility

Source: `/wc1/runs/th/thespian-cleanness/wepp/output/interchange/H.wat.parquet`.
It is the largest Parquet below the existing 512 MiB limit among 74 files in
the two existing representative runs inspected: **81,150,978 bytes (77.39 MiB),
3,646,034 rows, 32 columns, 217 row groups**. Source device/inode/size/mtime/ctime
were unchanged across both runs. Container identity: UID 1000/GID 993.

- `benchmark_dtale_large_parquet.py`: reusable probe using actual lazy accessors,
  PyArrow/DuckDB, the shared digest helper, and 512 distinct disposable pressure
  paths. It never requests an unbounded DataFrame.
- `dtale_large_parquet_baseline.json` / `.log`: true pre-implementation native
  baseline loaded from `dtale_native_baseline_snapshot.py`, copied with
  `git show fbac92404:wepppy/webservices/dtale/dtale.py`.
- `dtale_large_parquet_implementation_initial.json` / `.log`: initial guarded
  working-tree implementation, source SHA recorded in JSON. Implementation
  landed before the first import; that run was relabeled explicitly rather
  than presented as old-code baseline.

Repeat current implementation:

```bash
wctl exec dtale python docs/work-packages/20260916_file_dependency_freshness/artifacts/benchmark_dtale_large_parquet.py dtale_large_parquet_current
```

For the old-code comparison, append the retained baseline module path. All
instances are isolated inside the benchmark process; the live worker's datasets
and caches are untouched. Pressure files are generated deterministically and
removed only from their own temporary directory.

## Actual native and guarded costs

Values are elapsed milliseconds. Normal page means cached row count followed
by one bounded 100-row read of all grid columns. Means use the repetitions
recorded in JSON; cold constructor/count are single observations.

| Operation | Native baseline | Initial guarded code | Guard evidence |
| --- | ---: | ---: | --- |
| Constructor/schema | 11.16 | 545.21 | 2 checks; 162,301,956 hash bytes |
| First native row count | 11.65 | 535.13 | 2 checks; 162,301,956 hash bytes |
| First one-row sample | 67.07 | 63.90 | 2 settled checks; zero hash bytes |
| First-page bounded query | 55.90 | 55.67 | 2 settled checks per query; zero hash bytes |
| Middle-page bounded query | 542.37 | 570.19 | 2 settled checks per query; zero hash bytes |
| Sorted bounded query | 243.46 | 244.53 | 2 settled checks per query; zero hash bytes |
| Normal page after helper-cache clear | 62.50 | 858.95 | 3 checks; 243,452,934 hash bytes |
| Settled normal page | 55.16 | 55.13 | 3 checks per page; zero hash bytes |
| Normal page after 512 other paths | 59.52 | 886.26 | 3 checks; 243,452,934 hash bytes |
| Normal page settled after eviction | 53.38 | 57.04 | 3 checks per page; zero hash bytes |

No excess validation nesting was observed: a normal page makes one cached-count
check plus before/after query checks. Standalone cached count/sample checks remain
present. The `cached_count` sweep includes one admission hash before settling;
its 5.47 ms aggregate mean must not be described as settled count latency.

## Digest admission and bounded pressure

Single full-file hashes cost approximately **263–301 ms** on this source.
Each reads exactly 81,150,978 content bytes, including during the first-second
observation interval. The first admitted value is freshly hashed. After admission,
100 warm calls averaged **0.112–0.116 ms**, with **zero content bytes read**;
this meets the existing less-than-1-ms per-file budget.

Observing and then admitting 512 other real four-byte files filled both caches
to exactly 512 entries. Revisiting the target rehashed all 81,150,978 bytes in
approximately 273–274 ms despite unchanged target metadata. The subsequent
normal page remained in admission and made its three expected full reads.
Once readmitted, five normal pages again read no content for hashing.

Exact hash byte counts come from instrumenting real binary stream reads, without
replacing their data. Fingerprint invocations are counted around the real helper
or D-Tale fingerprint function. `/proc/self/io` separately records whole-process
native/read telemetry; it is not misrepresented as exact per-file native reads.
For example, a settled normal query consumed approximately 1.016 MB of process
read characters while cold validation added 243.45 MB of known hash reads.

No OS page-cache drop was attempted. Physical `read_bytes` stayed zero in these
runs; “cold” therefore means application digest-cache cold, not cold storage.
The benchmark records Python/read instrumentation overhead and normal scheduling
variation; sub-millisecond differences in native query means are not regressions.

## Acceptance implications

- Confirmed cost: admission/eviction adds roughly 0.8 seconds to a normal page
  for this 77.39 MiB input, compared with roughly 55 ms settled. This matches the
  ratified native-query-plus-three-hashes bound, not an unexpected extra guard.
  A large active working set can repeatedly incur that cost even for unchanged
  sources. Preserve this visibility in shipping evidence.
- Settled unchanged-source performance passes locally: checks remain bounded
  and perform zero content rereads. No fallback to full pandas materialization,
  new cache, or watcher is needed to meet the measured settled budget.
- Retain actual restarted-service loader/page/browser timing, NFS behavior,
  filtered and multiple-range requests, and inputs nearer 512 MiB as explicit
  remaining performance coverage. Do not infer those results by scaling this
  one file or from helper timings alone. Reuse this probe for final code review.
