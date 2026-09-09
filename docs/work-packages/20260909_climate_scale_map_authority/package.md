# Restore configuration-owned climate scale maps

## Scope and incident

The operator reports that Marta's Portland MOFE runs persist
`_precip_scale_factor_map: "1.1"` instead of the configured Daymet raster.
The deployed template displays the map property, but the deployed input parser
still assigns a submitted `precip_scale_factor_map` directly to persisted state.
The read-only input is serialized by `WCForms`; display-only markup is not
server-side immutability. Identify affected owner-associated `portland-10-mofe`
runs on wepp1, correct this mutation boundary, and reset corrupted values.

## Authority and authorization

The user's 2026-09-09 request explicitly authorizes investigating/fixing the
mutation and resetting affected configurations. The new canonical map contract
is `docs/schemas/climate-precipitation-scaling-contract.md`; the agent API
contract must stop instructing callers to set this field. NoDb persistence and
RQ response contracts otherwise remain unchanged. Complete the contract-first
ancestor checkpoint and two independent reviews before implementation.

## Compatibility and data repair plan

Keep NoDb keys, configuration files, mode/scalar settings, and all raster
values unchanged. Resolve the expected value from each run's configuration,
not a global literal substitution. Inventory database ownership/association,
canonical run path, stored value, expected value, config token, and active jobs.
Repair only the confirmed target family and mismatching field.

Before writes, save a bounded inventory and exact climate.nodb backups outside
public report exports. Use canonical NoDb locking, fresh hydration, atomic
dump, and cache publication/invalidation; never overwrite an active writer or
restore unrelated stale attributes. Read back disk and a fresh controller.
Record hashes of generated climate/model artifacts so a config repair cannot
be mistaken for a completed climate/model rebuild. Inspect failed job logs and
generated climate metadata to determine whether a rebuild is needed; do not
silently rerun completed model scenarios.

## Validation, signals, and precedent

Hypothesis: configuration-derived reads and ignoring submitted map values stop
the `"1.1"` overwrite, including from stale browser pages. Test configured,
unconfigured, missing/empty/stale persisted, malicious payload, invalid config,
and parser-rollback states; prove persistence/reload and spatial-scaling path
propagation without changing scientific values or precedence. Exercise the
production parser boundary under the actual service identity before live repair.

Related precedent: September 9 display fixes (`24a6e962b`, `6d5bd58e3`),
`docs/dev-notes/climate-control.md`, and the NoDb atomic persistence/cache
contract. Follow `docs/standards/hardening-lifecycle-standard.md`; use
recurrence-triggered observation. A future config-map mismatch opens a new
incident referencing this record. Retain recovery backups until verified
repair and any operator-required rebuild complete.

Security impact: low. The change removes client authority over a configured
path without adding filesystem/network authority. Independent correctness and
QA review are required; no high-impact security review gate is triggered.
