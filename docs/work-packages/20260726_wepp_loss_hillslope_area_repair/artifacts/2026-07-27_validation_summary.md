# Validation Summary

## WEPPpyo3

- `cargo fmt --check`: passed.
- `cargo test -p wepp_interchange_rust`: 105 passed (88 unit and 17
  integration).
- Containerized native-writer suite against the release tree: 5 passed.
- Standalone Python 3.12 release-tree import: passed.
- Release artifact SHA256:
  `faa9173665aee64e92ce077488121cc21b7a1cc06cb771b280df81c7862299f1`.
- `git diff --check`: passed.

## WEPPpy

- Interchange and sediment-report suite: 72 passed, 1 skipped.
- Expanded consumer suite covering native facade/schema, sediment reporting,
  features export, and GL dashboard: 95 passed.
- Independent QA consumer gate: 128 passed.
- Documentation lint: passed with zero errors and warnings.
- UK-to-US spelling previews: no changes.
- `git diff --check`: passed.

## Generated-Output Evidence

The rebuilt release extension converted the historical fixture with a true
null annual area and converted a uniform current-format fixture with
`Hillslope Area=1.539`, schema version 2, and pollutant values retained in
their named columns. Exact 10/13-field and mixed-layout failures remain
explicit.
