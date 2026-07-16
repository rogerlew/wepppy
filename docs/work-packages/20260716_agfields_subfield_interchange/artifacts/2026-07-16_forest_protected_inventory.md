# Forest acceptance protected-file inventory

Read-only baseline captured before direct conversion on
`/wc1/runs/sa/sacral-self-discipline`. Tree hashes are SHA-256 hashes of the
sorted stream of per-file SHA-256 records, so the same commands can compare the
complete selected trees without committing large manifests.

| Protected scope | Baseline SHA-256 |
| --- | --- |
| Ordinary `wepp/output` tree | `29717712558656084f81b7935961f0c35a9cfd0dc6feaf5ebe23ba8360196020` |
| AgFields watershed scheme manifest/evidence files | `ffa24a9c75d52d06eb72d24f6a42a8e025ec4bade6c36888c152c10ac21a5422` |
| Root `*.nodb` state files | `b1fb7386b4bfd632aea11becef5202474b19090db3de7aef6e1291d39ab00910` |
| `ag_fields/sub_fields/fields.parquet` | `7adc2df6b1fa36537c784507e62a2b85ed38ddc51842712d9611cbc32e9d8c99` |
| Six AgFields raw report families | `6a0d3b3e582a43a93ad0ba132f442fb1b3981b0f119e646b060ed54a3bba5e6e` |

The raw-family scope includes only `H*.pass.dat`, `H*.ebe.dat`,
`H*.element.dat`, `H*.loss.dat`, `H*.soil.dat`, and `H*.wat.dat` directly under
`wepp/ag_fields/output`. The acceptance converter is authorized to write only
the sibling staging/backup paths and final `interchange/` directory beneath
that output root; the scopes above must compare byte-identically afterward.

The exact file selectors and hash commands are recorded in
[`2026-07-16_full_corpus_acceptance.md`](2026-07-16_full_corpus_acceptance.md#reproducible-protected-scope-hashes).
