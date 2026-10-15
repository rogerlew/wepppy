# Committed binary and seed-generator inputs

Byte-for-byte snapshots captured on 2026-10-15 from Forest's formerly ignored
`tests/wepp/interchange/fixtures/deductive-futurist/wepp/runs/`. SHA256SUMS records
the original bytes. Git preserves line endings and trailing spaces; these files
are stored directly in Git, not LFS.

- `p1` and the six shared parameter files support the registered watershed and
  hillslope binary smoke tests. The run requests four simulation years.
- `p1` and `pw0` supply the existing single- and multiple-OFE parser, mutation,
  and preflight cases. `pw0` is seed input for those tests, not a complete
  executable watershed fixture; its other watershed inputs are not included.

The tests retain their original assertions and actual model execution. Keep
these fixtures committed; do not rely on local interchange output or tests
running in a particular order. Outputs are generated in pytest temporary paths.
