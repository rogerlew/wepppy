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

Pending final gates and the coordinated forest restart.
