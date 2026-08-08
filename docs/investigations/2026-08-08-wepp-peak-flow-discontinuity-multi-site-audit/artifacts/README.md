# Multi-Site Peak-Flow Audit Artifacts

This directory holds reproducible inputs, manifests, event ledgers, summaries,
figures, and frozen regression fixtures produced by the
[WEPP peak-flow discontinuity multi-site audit](../README.md).

## Conventions

- Preserve raw diagnostic output separately from derived tables.
- Record units in column names or an accompanying schema.
- Include site, scenario, mutation, hillslope, OFE, and date identifiers in
  event-level records.
- Record the source commit and executable SHA-256 in every run manifest.
- Label observational, forced-`APPMTH`, and forced-`HDRIVE` results explicitly.
- Do not commit credentials, access tokens, or machine-specific run paths.

Site-specific subdirectories will be added when the corresponding phase
begins. Topanga will be the first site.
