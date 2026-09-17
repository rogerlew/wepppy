# PF-R02 CLI lineage contract QA and performance discovery

Disposition: **PASS for the proposed checkpoint**, with implementation and runtime
acceptance pending. Reviewed the revised [canonical contract](../../../schemas/climate-parquet-lineage-contract.md)
and [decision](cli_lineage_contract_decision.md). No production/test files or named
project data were changed by this review.

## Retained measurement evidence

[Primary script](benchmark_cli_lineage.py), [JSON](cli_lineage_performance.json),
[log](cli_lineage_performance.log); [eviction script](benchmark_cli_readiness_eviction.py),
[JSON](cli_lineage_readiness_eviction.json), [log](cli_lineage_readiness_eviction.log).
Disposable copies, actual generated Parquet and private snapshot attempts remain
under `/wc1/batch/qa-cli-lineage-perf-45563276ac4c`; its manifest and the JSON records
identify files and sizes. Execution used the maintained weppcloud container,
UID 1000/GID 993. Both named sources retained identical bytes and filesystem
generation; an audit hook rejected named-run writes during the primary probe.

The selected real CLI files represent 46 years/16,802 rows (1,177,082 bytes,
`thespian-cleanness`) and 120 years/43,829 rows (3,112,776 bytes,
`plastic-bundling`). The latter was the largest of the 149 surveyed run-level
`climate/wepp.cli` files. These are representative local workloads, not universal
input limits. The actual Climate service and interchange producers parsed copied
CLI files, preserving equal rows/types. Their respective output sizes were
854,333 and 2,438,520 bytes. Prototype metadata added 574 bytes.

| Mean elapsed time | 46 years | 120 years |
| --- | ---: | ---: |
| Actual CLI parse with peak intensities, 3 calls | 290.77 ms | 689.79 ms |
| Actual Climate export entrypoint, 3 calls | 337.70 ms | 810.31 ms |
| Actual interchange generation, 3 calls | 327.80 ms | 789.19 ms |
| Existing interchange legacy fast path, 100 calls | 0.048 ms | 0.053 ms |
| Coherent snapshot copy plus three verified digests, 3 calls | 23.55 ms | 58.63 ms |
| Composed snapshot/export/metadata/publication, 3 calls | 389.71 ms | 911.22 ms |
| Coherent Parquet metadata only, 100 calls | 0.73 ms | 0.77 ms |
| Composed readiness, helper cold | 5.70 ms | 12.01 ms |
| Composed readiness, during admission, 2 calls | 5.60 ms | 12.12 ms |
| Composed readiness, first admitted digest | 14.30 ms | 22.68 ms |
| Composed readiness, settled, 100 calls | 1.44 ms | 1.25 ms |
| Composed readiness, actual cache eviction, 3 cycles | 5.44 ms | 11.83 ms |

The composed paths are explicitly **probe-only**, not a production implementation
or conformance proof. Their miniature metadata object is labeled as such; it is
not the final strict contract schema. They parse a verified private snapshot,
use the actual producer, add metadata to freshly generated rows, recheck the
source and replace the disposable output. Composition conservatively rereads and
rewrites generated Parquet to attach metadata; production can attach metadata in
its native write. Added mean cost over actual Climate export was 52.01/100.91 ms.
The snapshot used three full digest calls and one copy; composed publication added
one final source digest. Parser I/O is included in elapsed/process I/O measurements
but is not intercepted by the Path.open byte counter.

Readiness composition includes coherent footer acquisition, JSON decoding,
selected-name comparison and one verified CLI digest check. Every measured call
read 65,536 Parquet footer bytes. Cold/admission/evicted checks additionally read
exactly one CLI payload; settled checks read zero CLI payload bytes. Three actual
512-path pressure/admission cycles per input populated both shared caches to
their existing bounds and forced source rereads. No CLI parsing, Parquet row
loading or full Parquet hashing occurred during readiness.

No OS cache was dropped. Copying primes the page cache, and helper-cold means
empty process digest caches. The first parse had some physical reads, while
subsequent measured paths reported none; these results do not establish cold
storage or NFS latency.

## Proposed local acceptance budgets

For these representative inputs with OS cache warm, accept mean lineage
readiness at **<=5 ms settled / <=40 ms cold, admitting or evicted**, including
footer reads. Require zero settled full CLI payload rereads and one CLI digest
check per composed readiness observation. Do not replace bounded coherent
footer reads with metadata-only trust merely to achieve zero total read bytes.

Accept complete snapshot/parse/export/metadata/publication at **<=1.5 seconds** for
the 120-year case and **<=200 ms added lineage overhead** versus its native
producer baseline. Repeat the actual implemented paths before acceptance; owner
reload, proof validation, authorization and retained diagnostics must be included.
Retain byte/check counts alongside timings so extra payload work cannot hide
inside a generous latency budget.

These readiness timings cover the lineage component, **not full
`postfire.sources`**, which also acquires owners and checks global/raster sources;
its existing full-state acceptance remains separate. Export timings cover
`export_cli_parquet`, not climate generation or `export_post_build_artifacts`'s
existing one-second delay, frequency CSV and NOAA work.

## Quality and valid-state review

- Legacy recovery fits the existing workflow: the post-fire prerequisites already
  offer “Build climate” linked to the Climate control, and normal build/upload
  paths invoke export. Readiness may reject proofless legacy without forcing
  automatic regeneration or blocking existing calendar/report/history reads.
  The actual existing interchange fast path returned its legacy file unchanged
  across 100 calls per case. UI/native integration acceptance must still prove
  that ordinary regeneration establishes readiness; this probe is not that test.
- Embedded metadata binds one output generation and avoids a second receipt
  publication protocol. Keep common snapshot/publication/proof mechanics cohesive
  across the two producers while preserving their distinct selection and error
  contracts. Avoid using interchange's calendar fast path as readiness evidence.
- Snapshot access constraints are concrete: the probe created snapshots as 0600
  inside 0700 attempt directories before writing. This demonstrates a cheap safe
  mode, not ACL/runtime conformance. Production must exercise source/output modes,
  existing output authorization, symlink targets and creation-time restrictions
  under the actual worker identity; copying then chmod is insufficient.
- The revised visible `climate_artifacts/cli_parquet/attempts/` location resolves
  the ordinary climate-directory cleanup conflict. Canonical archive exclusions
  currently target `archives` and transaction files, but skeleton preservation
  needs the explicit allowlist change. Actual cleanup, skeletonize and archive/
  restore tests remain required, including failed attempts and accepted metadata.
  The previous output retention guarantee correctly begins at export entrypoint.
- Failure observability is specified without broadening existing parser error
  suppression. Native partial candidate files and explicit attempt outcomes must
  remain accessible. Test post-publication diagnostic failure separately so an
  accepted output is not reported as uncommitted or removed.

No unresolved contract-level QA blocker remains. Residual implementation debt is
the existing duplicated transformation pipeline; this wave need only share the
new lineage mechanics, not refactor scientific calculations. Required next gates
are native compatibility/race/failure tests, actual implemented performance,
artifact retention and production-equivalent workflow acceptance. Full-package
inventory and live runtime acceptance remain outside this scoped PASS.
