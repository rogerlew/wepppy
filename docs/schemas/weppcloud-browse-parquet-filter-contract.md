# WEPPcloud Browse Parquet Filter Contract

## Purpose
This document defines the canonical `pqf` filter contract shared by browse parquet quick-look surfaces:
- browse HTML preview (`/browse/{subpath}`)
- parquet download (`/download/{subpath}`)
- parquet CSV export (`/download/{subpath}?as_csv=1`)
- D-Tale launch (`/dtale/{subpath}`)

The contract is active only when `BROWSE_PARQUET_FILTERS_ENABLED=1`.

## Transport
- Query key: `pqf`
- Encoding: URL-safe base64 of UTF-8 JSON (unpadded is accepted)
- Empty or missing `pqf`: treated as no filter

## Filter Tree Schema
Root node must be an object with `kind` equal to `group` or `condition`.

### Group node
`{"kind":"group","logic":"AND"|"OR","children":[<node>, ...]}`

Rules:
- `children` must be a non-empty array
- `logic` is normalized to uppercase and must be `AND` or `OR`

### Condition node
`{"kind":"condition","field":"<string>","operator":"Equals|NotEquals|Contains|GreaterThan|LessThan","value":"<string>"}`

Rules:
- `field` is required and must exist in parquet schema
- `value` is required string

## Validation Limits
- Max depth: `6`
- Max total nodes: `50`
- Max field length: `128`
- Max value length: `512`

Validation failures return HTTP `422` with:
- `error.code = "validation_error"`
- optional `errors[0].path` describing failing node path

## Operator Semantics
- `Equals`: equality comparison
- `NotEquals`: inequality comparison
- `Contains`: case-insensitive substring search
- `GreaterThan`: numeric-only `>`
- `LessThan`: numeric-only `<`

Numeric-only behavior:
- Non-numeric field type with `GreaterThan`/`LessThan` is rejected (`422 validation_error`)
- Non-finite numeric literals (`NaN`, `inf`) are rejected (`422 validation_error`)
- Missing/null/`NaN` values are excluded from numeric comparison results

## Result Contracts by Surface

### Browse parquet HTML preview
- Applies filter when `pqf` is present and valid.
- On invalid filter: HTTP `422` JSON error payload.
- On zero matches: HTTP `200` with explicit filter feedback (`no_rows_matched_filter` message).

### Parquet download and CSV export
- With active valid `pqf`, outputs filtered rows only.
- Zero-row result: HTTP `422`, `error.code = "no_rows_matched_filter"`.
- Row cap exceeded (`BROWSE_PARQUET_EXPORT_MAX_ROWS`): HTTP `413`, `error.code = "parquet_filter_row_limit_exceeded"`.

### D-Tale load
- Browse bridge forwards `pqf` for parquet files.
- D-Tale loader applies same contract before DataFrame materialization.
- Invalid/empty/row-limit errors return structured JSON with the same codes/status semantics as above.

## Compatibility
- No-filter behavior remains unchanged for all routes.
- Auth/path traversal/security contracts remain unchanged; `pqf` only affects row selection after existing path/auth checks pass.
