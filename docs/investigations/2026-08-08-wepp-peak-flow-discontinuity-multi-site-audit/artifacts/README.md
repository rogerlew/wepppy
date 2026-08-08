# Multi-Site Peak-Flow Audit Artifacts

This directory holds reproducible inputs, manifests, event ledgers, summaries,
figures, and frozen regression fixtures produced by the
[WEPP peak-flow discontinuity multi-site audit](../README.md).

## Conventions

- Preserve raw diagnostic output separately from derived tables.
- Record units in column names or an accompanying schema.
- Include site, scenario, mutation, hillslope, OFE, model day, and solver-call
  ordinal identifiers in event-level records.
- Record the source commit and executable SHA-256 in every run manifest.
- Label observational, legacy-input replay, and harmonized-forcing replay
  results explicitly.
- Do not commit credentials, access tokens, or machine-specific run paths.

## Storage

Git stores schemas, manifests, compact fixtures, summaries, figures, and
content hashes. Large event ledgers, interval series, and hydrographs remain in
the authoritative storage location declared by the artifact-storage manifest.
That manifest must record the URI or run-relative locator, format, byte size,
content hash, schema version, producer run, and retention status.

One full baseline ledger is retained per frozen scenario stratum. Ordinary
mutation runs retain the target hillslope, its downstream closure, outlet
response, and checksums for elements expected to remain unchanged. Full-run
output is retained for flagged cases and combined watershed experiments.

Site-specific subdirectories will be added when the corresponding phase
begins. Topanga will be the first site.
