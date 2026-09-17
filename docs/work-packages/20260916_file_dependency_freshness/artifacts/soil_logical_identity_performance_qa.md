# PF-R01 logical soil identity performance discovery

Independent bounded discovery, no production/test edits. This measures the
existing coherent snapshot primitive and current soil inventory. It approves
neither a new currentness contract nor polling-time snapshots or a persistent
logical cache. PF-R01 remains open for a reviewed design.

## Evidence and source protection

Script: `benchmark_soil_logical_identity.py`; results:
`soil_logical_performance.json` and `.log`. The JSON retains the complete
54-cache survey, source states and byte hashes, timing samples, profile counters,
logical identities, file inventory, and all SQLite connection paths.

Actual outputs: [batch manifest](/wc1/batch/qa-soil-logical-perf-d7ea2e582667/benchmark-manifest.json)
and its three named case directories. These retain 21 complete snapshot attempts
(first, five warmed repeats, one profiled each), totaling 19,041,932 bytes plus
the benchmark manifest. Large SQLite copies remain outside Git. Every snapshot
has its actual `manifest.json`, main database, and any copy-side WAL/SHM.

The maintained `weppcloud` container ran as UID 1000/GID 993. A Python audit
guard prohibited named-run writes and permitted SQLite connections only under
this new disposable batch root. All 21 actual SQLite connections were to copies;
no source connection/checkpoint, acquisition, schema migration, soil builder or
NoDb controller was invoked. No guard was triggered. Source main/WAL/SHM
SHA-256 values and device/inode/mode/size/mtime/ctime, plus rollback-journal
absence, agreed before and after each case. Read access times are not an
immutability assertion.

The actual snapshot still rejects journals/symlinks, uses `open_local` copying,
opens a read transaction on the copy, disables trusted schema/extensions, applies
table bounds, and rechecks the complete source state. Inventory calls the actual
`production_soils.inventory`, including real prepared-source validation.

## Representative selection and sizes

Survey scope was `/wc1/runs/*/*/soils/ssurgo_tabular_cache.sqlite`: 54 databases,
51 with WAL, none with rollback journals at discovery. Combined main/WAL/SHM
sizes ranged from 12,288 to 1,285,256 bytes. This is a local representative
sample, not a claim about all projects or the 512-MiB-per-file supported limit.

| Case | Actual run | Main / WAL / SHM bytes | Component / horizon rows | Consumed canonical JSON bytes |
| --- | --- | ---: | ---: | ---: |
| Largest observed WAL set | `improvident-dyslexia` | 4,096 / 1,248,392 / 32,768 | 763 / 4,895 | 621,360 |
| Largest main without WAL | `curable-program` | 159,744 / absent / absent | 146 / 376 | 53,510 |
| Largest prepared M3 set | `thespian-cleanness` | 4,096 / 1,203,072 / 32,768 | 708 / 2,337 | 319,916 |

The prepared case has ten inventoried dependency paths and four prepared file
hash declarations. The other two have six dependency paths and no prepared
metadata. All three actual schemas use INTEGER keys, TEXT names/designations,
and REAL numeric columns. Repeated snapshots returned identical consumed schema
and logical table hashes.

## Measured costs

All times below are means in milliseconds. Inventory uses 30 calls; source-state
and settled physical checks use 100; warmed snapshots use five independent fresh
output directories. Source byte verification before timing primes filesystem
cache. “First” means the first measured operation, not physically cold storage.

| Operation | Largest WAL | Main only | Prepared M3 |
| --- | ---: | ---: | ---: |
| Existing source-state check | 0.529 | 0.238 | 0.207 |
| Existing production soil inventory | 2.364 | 1.509 | 14.534 |
| Physical main/WAL/SHM digest, helper-cold | 5.760 | 1.000 | 5.824 |
| Physical digest set, during admission | 5.291 | 1.014 | 5.192 |
| Physical digest set, admitting | 7.964 | 0.906 | 6.986 |
| Physical digest set, settled | 0.607 | 0.290 | 0.640 |
| Actual logical snapshot, first | 317.474 | 58.565 | 129.855 |
| Actual logical snapshot, warmed | 209.095 | 46.133 | 134.254 |
| Actual logical snapshot, profiled | 225.345 | 40.590 | 133.984 |

Each full physical digest set reads all present main/WAL/SHM bytes; settled
checks read zero content bytes. These diagnostic physical hashes are **not a
scientific identity or a proposed replacement for source-state guards**. A
4-KiB main-file digest alone would omit almost all current WAL content in two
cases. Hashing the entire physical set would still differ across the known
checkpoint/VACUUM/unrelated-table equivalences.

Each snapshot copies main plus WAL, totaling 1,252,488 / 159,744 / 1,207,168 bytes
respectively. It does not copy the source SHM. Copy-side SQLite may create its
own WAL/SHM: the main-only case actually gained a zero-byte WAL and 32-KiB SHM
beside every **copy**, while both companions remained absent beside the named
source. Even a read-only SQLite connection is therefore not equivalent to a
side-effect-free source-file inspection.

Digest and inventory operations recorded zero physical `read_bytes`. Snapshot
operations recorded 4,096 bytes per WAL case and 163,840 bytes per main-only
case at process level, including disposable-copy SQLite I/O. They do not isolate
physical source reads. There was no cache drop or cold-storage/NFS experiment;
do not present these numbers as cold-source performance.

## Where the logical cost goes

| Profile component | Largest WAL | Main only | Prepared M3 |
| --- | ---: | ---: | ---: |
| Guarded source copying | 16.53 ms | 5.00 ms | 15.07 ms |
| Bounded table parsing and size serialization | 69.13 ms | 13.10 ms | 39.13 ms |
| Per-row canonical hash used for sorting | 89.20 ms | 8.54 ms | 48.73 ms |
| Final two canonical table hashes | 29.18 ms | 2.74 ms | 15.19 ms |

The largest case executes 5,658 row-sort hashes plus two table hashes. Row-sort
hashing is about 40% of profiled time; parsing is 31%, final hashing 13%, and
copying 7%. The prepared case has the same pattern. This is the existing typed
logical protocol, including duplicate-row ordering and nonfinite-value encoding;
the benchmark does not normalize source values or substitute scientific output
equivalence for input identity.

## Compatible design constraints

- The existing `source_schema` plus logical component/chorizon hashes are the
  available coherent scientific core. A raw file hash is cheaper but cannot fix
  the demonstrated false-stale physical-storage cases. The source-state tuple is
  cheaper again and remains a transaction/coherence guard, not scientific content.
- A fresh logical snapshot currently costs roughly 46–209 ms after warming on
  this local sample, versus 1.5–14.5 ms for existing inventory. It also retains
  roughly 0.19–1.29 MB per observation. That cost must be accounted for before
  adding any state-read validation frequency or artifact-write behavior. No such
  change, polling cache, watcher, service or source connection is proposed here.
- Keep main/WAL/SHM presence and complete state, rollback-journal rejection,
  no-follow copying, limits, permission failures, and source rechecks around
  snapshots, receipt promotion and locked publication. A reusable observation,
  if later designed, must first originate from this complete coherent source set;
  a main-only hash or old receipt cannot establish it.
- Keep scientific equality separate from execution authority: collection/MUKEY
  evidence, selected paths, optional-source presence, source policy, soil masks,
  THICK identity/units/grid/bounds and the rest of accepted dependency closure
  remain required. Reusing a logical core does not validate those inputs.
- Copy optimization alone cannot remove most observed cost. Any later optimization
  of canonicalization must preserve declared consumed schema, SQLite value types,
  nonfinite handling, deterministic duplicate ordering and exact logical hashes;
  filtering to selected MUKEYs or sorting only by identifier would change the
  current identity protocol unless separately justified and versioned.
- Do not infer a general collision guarantee or arbitrary-writer isolation from
  this unchanged-source benchmark. Preserve committed-WAL, rollback-journal,
  mutation-during-read, symlink, absent/empty and retained-failure tests. Legacy
  accepted results cannot acquire past logical provenance from today's source.

The retained snapshot primitive is sufficient for explicit bounded logical
revalidation experiments. These measurements identify its costs and constraints;
they do not yet establish the cheapest compatible state-poll design or authorize
discarding raw execution guards. Near-limit table/database sizes, state refresh
bursts, physical storage/NFS behavior and full numerical accepted-result
propagation remain unmeasured.
