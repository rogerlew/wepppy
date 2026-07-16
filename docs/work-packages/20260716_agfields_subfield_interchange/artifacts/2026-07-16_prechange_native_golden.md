# Pre-change ordinary native interchange golden

Captured before Rust edits on 2026-07-16 from the canonical Python 3.12
release. The complete machine-readable capture, including every field's type,
nullability and metadata plus selected logical values, was retained during
implementation at
`/tmp/agfields_native_baseline_20260716/ordinary_golden.json` (capture SHA-256
`769d180a05ee15c3ce71c7f182a8d3212092fba09950fae27bf1c46140ca38f1`).

## Release provenance

- Shared object:
  `/home/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so`
- Pre-change SHA-256:
  `7419203c8b91db1b595590b7c9a28040662d5fad9fdf8b182a17c85a76d518e4`
- Ordinary public signatures were recorded for all six
  `hillslope_*_files_to_parquet` functions and are unchanged by contract.
- Every ordinary file carried exactly `dataset_version=1.2`,
  `dataset_version_major=1`, `dataset_version_minor=2`, and
  `schema_version=1`.

## Three-source golden summary

| Family | Rows | Row-group rows | File SHA-256 | Logical IPC SHA-256 |
| --- | ---: | --- | --- | --- |
| PASS | 18,630 | 6,210 / 6,210 / 6,210 | `4c3e6c396d85ca2a847f6f69a5f87d90f131b02874caf8a9c8388d6dfbe8026c` | `66fc5c1d5679a45458894d6937e36622da87e23738f3db9146a13a92c17b36cf` |
| EBE | 556 | 187 / 177 / 192 | `cfec60983bc8eacbfdf1bdd28f87f0b00f05c69672819e5814c847522c4ba544` | `2d7d72bb1b13caeab04198699730c638a30271a86890641c78078949beabd5d3` |
| ELEMENT | 1,747 | 586 / 571 / 590 | `8411e430447358f7928f8504d5b2c7ea954c7c160bce358be97d33288b0cc943` | `4880f1c42863e3bab51f10cfa67334e2a0865e5f5141092c58416519b5e6551f` |
| LOSS | 15 | 5 / 5 / 5 | `97b1fea6c6839ea65fd619d9ae1ec950cc7f11a231fc992c259d1f00fc94f4ae` | `05fad6edd61f05b9b5929ad2f50fde976db4f1e2308d2475460fe195e97cf7d1` |
| SOIL | 18,630 | 6,210 / 6,210 / 6,210 | `f3b7cc7bbdd3b280d6053446384cba667891fc3a469bc3bd553cfc980be0e444` | `5d9c7d21c2d38582a032eeb43c289a2f2ff741d2745a0d0934db3a17c0bc2d68` |
| WAT | 18,630 | 6,210 / 6,210 / 6,210 | `65a129a78b1d76f9590a1e20f9c630aa85a29bf0afe4da0f7db08ff0240a46cf` | `6420c22c95caa7da4416b73305b840bd94250430eac766c00166b274b8496ca9` |

Each file had exactly three row groups in input order and identity values
`[1, 2, 3]`. Logical hashes cover the complete Arrow values, including null and
NaN representation, independently of Parquet encoding bytes. The as-built
native tests must reproduce these logical summaries for ordinary APIs and prove
AgFields tail-column equality after replacing only the identity column.
