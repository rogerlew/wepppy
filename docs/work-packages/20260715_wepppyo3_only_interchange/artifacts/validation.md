# Validation Evidence

## Native Source and Release

- WEPPpyo3 source commit: `5819cb3d124cb65e253445cb1b2e83d22df9b4e2`.
- Release refresh commit: `4d3c060`.
- Installed Python 3.12 extension SHA-256:
  `7419203c8b91db1b595590b7c9a28040662d5fad9fdf8b182a17c85a76d518e4`.
- `cargo fmt --check -p wepp_interchange_rust`: passed.
- `cargo check -p wepp_interchange_rust`: passed.
- `cargo test -p wepp_interchange_rust`: 68 unit and 16 integration tests
  passed.
- Release-tree Python suite: 22 passed.

## WEPPpy

- Focused interchange plus startup contract: 55 passed, one skipped.
- Post-production-origin startup contract: 9 passed.
- `wctl check-test-stubs`: passed.
- `wctl check-rq-graph`: passed.
- Changed-file broad-exception enforcement: passed, net delta `-8`.
- Code-quality observability: completed in observe-only mode.
- Full repository pytest: 4,895 passed, 58 skipped, and 411 warnings in
  891.19 seconds.

Package-wide `stubtest wepppy.wepp.interchange` remains blocked during mypy
construction by preexisting HEC-RAS typing errors in `hec_ras_boundary.py` and
`hec_ras_buffer.py`. Focused `_rust_interchange` stubtest and the canonical test
stub gate passed.

## Generated Concept 2 Smoke

The smoke copied all six `H1.*.dat` reports plus
`climate/wepp_cli.parquet` from
`/wc1/runs/sa/sacral-self-discipline` into an isolated container temp tree and
ran the public hillslope aggregate with `start_year=2000`.

| Output | Rows | Physical row groups |
| --- | ---: | ---: |
| `H.pass.parquet` | 6,210 | 1 |
| `H.ebe.parquet` | 110 | 1 |
| `H.element.parquet` | 510 | 1 |
| `H.loss.parquet` | 5 | 1 |
| `H.soil.parquet` | 6,210 | 1 |
| `H.wat.parquet` | 6,210 | 1 |

Native catalog scanning returned seven entries and resolved the installed
extension at the exact SHA above.

## Restarted Local Stack

The authorized local services were force-recreated after the atomic extension
refresh. All six Python service families logged the exact installed SHA. RQ
reported zero queued or executing jobs and ten idle workers after restart.

## Independent Reviews

- [Code review](code-review.md): zero unresolved high/medium findings.
- [QA/runtime review](qa-runtime-review.md): zero unresolved high/medium
  findings.
