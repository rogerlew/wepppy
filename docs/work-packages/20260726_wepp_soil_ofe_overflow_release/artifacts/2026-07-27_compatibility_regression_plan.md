# Compatibility and Regression Plan

## Contracts

- WEPP SOIL measurements and parquet schema remain unchanged.
- WEPP text OFE width increases without changing token order.
- WEPPpyo3 supports ordinary numeric files plus deterministic historical
  overflow recovery.
- Existing WEPP binary versions remain vendored and selectable.

## Required Evidence

- Exact lines around OFE 99, 100, and 238 from generated `wepp_260726` output.
- Exact reconstructed boundaries and daily row counts from the synced incident.
- Failures for early `**`, numeric-after-star, gaps, mixed day counts, and
  malformed measurement rows.
- Binary hashes, ELF interpreter checks, smoke tests, and release imports.
- WEPPpy runner selection and interchange integration tests.

## Rollback

Revert each repository release commit and select the prior WEPP binary. Existing
text and parquet data require no migration; interchange artifacts can be
regenerated after restoring the prior native extension.
