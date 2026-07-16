# Forest full-corpus acceptance evidence

Acceptance run: `/wc1/runs/sa/sacral-self-discipline`
Browser project: `sacral-self-discipline/disturbed9002_wbt`

## Direct conversion

The finalized orchestrator received 6,626 coupled
`(path, field_id, sub_field_id)` descriptors for each of the six native calls.
It published the complete bundle twice, proving initial publication and
replacement of a prior complete generation. The hardened rerun completed in
7m48.63s, used 751,956 KiB peak RSS (including the one-time deep footer/schema
completion check), and used no swap.

An earlier acceptance assertion required all 6,626 identities in every output.
The first conversion disproved that assumption after 2m10s: 111 valid EBE
reports contain exactly the three report-header lines and no scientific rows.
The final contract independently classifies only those header-only EBE sources,
records them in the manifest, and never invents a measurement row. Missing
identities in any other family fail publication.

| Family | Raw descriptors | Rows | Row groups / identities | Header-only sources | Extra or invalid identities |
| --- | ---: | ---: | ---: | ---: | ---: |
| PASS | 6,626 | 41,147,460 | 6,626 | 0 | 0 |
| EBE | 6,626 | 873,396 | 6,515 | 111 | 0 |
| ELEMENT | 6,626 | 3,517,273 | 6,626 | 0 | 0 |
| LOSS | 6,626 | 33,130 | 6,626 | 0 | 0 |
| SOIL | 6,626 | 41,147,460 | 6,626 | 0 | 0 |
| WAT | 6,626 | 41,147,460 | 6,626 | 0 | 0 |

The mapping contains 6,626 unique sub-fields across 2,169 fields. A separate
metadata pass asserted that every emitted `(field_id, sub_field_id)` pair
anti-joins to zero extra rows against `fields.parquet`, identities are unique,
row groups are in numeric `sub_field_id` order, and the manifest's 111 EBE ids
exactly equal the independently observed three-line EBE reports. Deep bundle
validation returned `true`, and no stage or backup debris remained.

Published sizes were 38,934,186 bytes (EBE), 221,506,257 (ELEMENT), 14,312,260
(LOSS), 386,943,196 (PASS), 721,951,996 (SOIL), and 794,097,821 (WAT).

## Reproducible protected-scope hashes

Tree hashes are the SHA-256 of the sorted stream of absolute-path `sha256sum`
records. The direct conversion produced exact pre/post equality for all five
protected scopes:

```sh
root=/wc1/runs/sa/sacral-self-discipline
find "$root/wepp/output" -type f -print0 | sort -z | xargs -0 -r sha256sum | sha256sum
find "$root/wepp/ag_fields/watershed" -type f -path '*/manifest/*' -print0 | sort -z | xargs -0 -r sha256sum | sha256sum
find "$root" -maxdepth 1 -type f -name '*.nodb' -print0 | sort -z | xargs -0 -r sha256sum | sha256sum
sha256sum "$root/ag_fields/sub_fields/fields.parquet"
find "$root/wepp/ag_fields/output" -maxdepth 1 -type f \
  \( -name 'H*.pass.dat' -o -name 'H*.ebe.dat' \
  -o -name 'H*.element.dat' -o -name 'H*.loss.dat' \
  -o -name 'H*.soil.dat' -o -name 'H*.wat.dat' \) \
  -print0 | sort -z | xargs -0 -r sha256sum | sha256sum
```

| Scope | Pre/post SHA-256 |
| --- | --- |
| Ordinary `wepp/output` | `29717712558656084f81b7935961f0c35a9cfd0dc6feaf5ebe23ba8360196020` |
| AgFields watershed `*/manifest/*` | `ffa24a9c75d52d06eb72d24f6a42a8e025ec4bade6c36888c152c10ac21a5422` |
| Root `*.nodb` | `b1fb7386b4bfd632aea11becef5202474b19090db3de7aef6e1291d39ab00910` |
| `fields.parquet` | `7adc2df6b1fa36537c784507e62a2b85ed38ddc51842712d9611cbc32e9d8c99` |
| Six raw families | `6a0d3b3e582a43a93ad0ba132f442fb1b3981b0f119e646b060ed54a3bba5e6e` |

The authenticated RQ acceptance intentionally rewrites raw AgFields reports and
updates AgFields NoDb/preflight state. Its post-run immutability comparison is
therefore limited to ordinary `wepp/output`, watershed manifests, and the source
mapping; expected raw/NoDb mutations are recorded separately.

## Service and RQ acceptance

The default and batch queues reported zero queued/executing jobs before the
coordinated restart. `weppcloud`, `query-engine`, `rq-engine`, `rq-worker`,
`rq-worker-batch`, and `scheduler` were force-recreated together. Every process
then imported:

- module origin
  `/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/__init__.py`;
- shared-object SHA-256
  `8c42edd0a8e1b03bdaf423355a12414180c709efaac3e379e5dd23e6cc77214e`;
- all six `ag_fields_hillslope_*_files_to_parquet` functions with their expected
  signatures.

Authenticated rq-engine setup and run-scoped discovery used a bearer token with
audience `rq-engine`, token class `service`, the required read/status/enqueue
scopes, and access limited to `sacral-self-discipline`. The generic endpoint
catalogs do not currently expose the preexisting AgFields route family, so the
operation-specific schema/default/error URLs were unavailable. Acceptance used
an empty JSON request and therefore relied only on server defaults.

`POST /api/runs/sacral-self-discipline/disturbed9002_wbt/agfields/run-wepp`
returned HTTP 202 and job
`9ff0f757-3ec4-4d48-ae1c-f3f6de2c8e84`. The job ran from
`2026-07-16 20:41:52.653282` through `2026-07-16 21:12:03.296576` (30m11s) and
finished without exception. Its result was:

```json
{"interchange_relpath":"wepp/ag_fields/output/interchange","run_count":6626}
```

The post-job AgFields state reported 6,626 runs, no active AgFields job,
non-stale sub-fields/raw runs, and `wepp.complete=true`. Independent deep bundle
validation returned true. The published rerun contained the same 6,626 mapping
identities and 2,169 fields, no staging/backup debris, and these summaries:

| Family | Rows | Row groups / identities | Size (bytes) | Explicit zero-row sources |
| --- | ---: | ---: | ---: | ---: |
| PASS | 41,147,460 | 6,626 | 386,991,531 | 0 |
| EBE | 874,734 | 6,515 | 38,925,051 | 111 |
| ELEMENT | 3,518,535 | 6,626 | 230,242,338 | 0 |
| LOSS | 33,130 | 6,626 | 14,311,451 | 0 |
| SOIL | 41,147,460 | 6,626 | 906,927,729 | 0 |
| WAT | 41,147,460 | 6,626 | 1,054,458,121 | 0 |

The three post-RQ protected scopes remained byte-identical: ordinary output
`29717712558656084f81b7935961f0c35a9cfd0dc6feaf5ebe23ba8360196020`,
watershed manifests
`ffa24a9c75d52d06eb72d24f6a42a8e025ec4bade6c36888c152c10ac21a5422`,
and source mapping
`7adc2df6b1fa36537c784507e62a2b85ed38ddc51842712d9611cbc32e9d8c99`.
As expected for an actual rerun, the raw-family tree changed from `6a0d3b...`
to `bba2553647a7de55f83363ca397d6c45c3ddf030407c2f0ee5b40aca7e664e76`,
and the root NoDb tree changed from `b1fb73...` to
`d8f290f511af4a8998c4eba39417f5e24e03fa80b4c305e652cc036a9b5cf95f`.
