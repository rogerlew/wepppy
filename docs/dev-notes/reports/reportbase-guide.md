# ReportBase & Helper Infrastructure

This guide captures the current contract for report implementations under
`wepppy.wepp.reports` and the shared helpers that keep report code
consistent.

## ReportBase shortcuts

All tabular reports inherit from `ReportBase`. Implementations are expected
to populate:

- `header`: ordered list of display column labels.
- `units_d`: optional map of display labels → units (defaults to
  parenthesis parsing via `RowData`).
- Iteration protocol: `__iter__` should yield `RowData` instances.

`ReportBase.write()` and `ReportBase.to_dataframe()` remain the canonical
export helpers and expect the iterator to yield `(value, units)` pairs.

## Shared helpers

Located in `wepppy.wepp.reports.helpers`.

### ReportQueryContext

A thin wrapper around the query engine bootstrap. Report code calls:

- `ReportQueryContext(run_directory, run_interchange=False)` to
  initialise.
- `context.ensure_datasets(path, ...)` to assert required parquet assets
  are present.
- `context.query(payload)` to execute a `QueryRequest` with the shared
  DuckDB engine.

The helper memoises the resolved run context and keeps catalogue access in
one place, which simplifies testing stubs.

### ReportCacheManager

The cache manager standardises the cache location to
`<run>/wepp/reports/cache/`. Reports call `read_parquet(key, version=...)`
and `write_parquet(key, dataframe, version=...)`. Version strings are stored
in a sidecar JSON file so schema changes automatically invalidate stale
artefacts.

### extract_units_from_schema

Utility to translate parquet field metadata (`b"units"`) into display units
without embedding unit strings in column labels. Reports pass a mapping of
"display label" → "source field(s)" and receive a dictionary ready to merge
into `units_d`.

## Patterns to follow

1. **Cache first**: read via `ReportCacheManager` before performing any
   expensive work. If the cache misses or version mismatches, rebuild and
   rewrite with the same manager.
2. **Context guardrails**: call `context.ensure_datasets()` early and let it
   surface missing parquet assets with a consistent error message.
3. **Schema-aware units**: prefer `extract_units_from_schema` over manual
   string parsing when parquet metadata is available.

Keeping these patterns aligned greatly reduces boilerplate across reports
and allows the future harness to substitute fake contexts/caches for fast
unit tests.
