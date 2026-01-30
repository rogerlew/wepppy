# wepppyo3 Interchange Spec
> Draft specification for a Rust/PyO3 interchange module that accelerates large WEPP watershed conversions.
> **See also:** `wepppy/wepp/interchange/README.md`, `wepppy/wepp/interchange/versioning.py`, `wepppy/wepp/interchange/schema_utils.py`

## Status
- Implemented (January 30, 2026)
- Owner: wepppy + wepppyo3
- Phase 1 + Phase 2 complete; Rust is default with explicit Python fallback logging.

## Problem Statement
`run_wepp_watershed_pass_interchange` takes 10+ hours on large watersheds (15 GB `pass_pw0.txt`) because parsing and Parquet writing are fully Python-bound. Similar bottlenecks exist in watershed soil, loss, and channel peak interchange. These routines perform heavy regex/token work, allocate Python lists, and flush Arrow tables via PyArrow, keeping the GIL hot for the entire conversion.

We need a Rust/PyO3 implementation that streams directly from WEPP text outputs into Parquet, reuses typed buffers, and optionally parallelizes CPU-heavy steps. This should preserve existing schemas/metadata while reducing wall clock time and memory churn for large projects.

## Goals
- Deliver a Rust/PyO3 module (`wepppyo3.wepp_interchange`) that accelerates watershed interchange outputs by at least 5-10x on 10+ GB files.
- Preserve output fidelity: schema names/types, metadata (`units`, `description`, dataset version), and row ordering.
- Maintain compatibility with existing Python orchestration and versioning (`interchange_version.json`).
- Default to Rust; when Rust is unavailable or fails, fall back to Python with explicit logging.
- Provide a large test fixture and validation harness for parity checks.

## Non-goals
- Changing column names, units, or dataset versions.
- Removing the existing Python interchange implementations.
- Phase 3 work beyond the interchange modules described here.
- Introducing a new public API for downstream consumers (the Python wrapper stays stable).

## Scope
### Phase 1 (delivered)
1. Watershed PASS interchange (`pass_pw0.txt`)
2. Watershed soil interchange (`soil_pw0.txt` / `.gz`)
3. Watershed loss interchange (`loss_pw0.txt`)
4. Watershed channel peak interchange (`chan.out`)

### Phase 2 (delivered)
- Watershed EBE (`ebe_pw0.txt`) and channel water balance (`chanwb.out`, `chnwb.txt`).
- Catalog scan acceleration (`query_engine.activate._build_catalog` + `_iter_catalog_files`).
- Hillslope interchange (PASS/EBE/ELEMENT/LOSS/SOIL/WAT).

## Test Fixture
Default unit/integration fixture:
- `tests/wepp/interchange/test_project/output`

Large watershed run directory (not in git) for parity/perf:
- `tests/wepp/interchange/fixtures/deductive-futurist/wepp`

Set `WEPPPY_INTERCHANGE_FIXTURE=tests/wepp/interchange/fixtures/deductive-futurist/wepp/output` to point tests at the large fixture. Rust parity tests are dev-only and require `WEPPPY_RUST_INTERCHANGE_TESTS=1`.

## Proposed Python Integration
### Selection policy
- Default to Rust; log Rust usage.
- On Rust failure, fall back to Python with explicit logging.
- No environment flags for interchange selection.

### Integration pattern
Each Python interchange function should attempt to import and call the Rust implementation first:

```python
from wepppy.wepp.interchange._rust_interchange import load_rust_interchange

rust_interchange, rust_err = load_rust_interchange()

try:
    rust_interchange.watershed_pass_to_parquet(...)
except Exception:
    # fall back to Python implementation
```

The Rust implementation should return output paths or a summary dict but must not change the existing return types exposed by the Python function.

## Rust Module Design
### Workspace layout
Add a new crate to `/workdir/wepppyo3`:
- `wepp_interchange/` (PyO3 extension crate)

Expected release layout:
```
release/linux/py312/wepppyo3/
  wepp_interchange/wepp_interchange_rust.so
```

### Crate structure
```
wepp_interchange/
  src/
    lib.rs
    calendar.rs
    floats.rs
    schema.rs
    pass.rs
    soil.rs
    loss.rs
    chan_peak.rs
    parquet.rs
    errors.rs
```

### Dependencies
- `pyo3` (extension-module)
- `arrow2` + `parquet2` (pure Rust, avoids C++ linking; aligns with packaging constraints)
- `fast-float` (fast float parsing, handles exponent logic)
- `memchr` (fast token boundary scans)
- `flate2` (gzip input support)
- `thiserror` (error handling)
- `time` (date formatting)

### Public Python API (Phase 1)
Current Rust/PyO3 entrypoints used by wepppy wrappers:

```python
# pass_pw0
watershed_pass_to_parquet(
    pass_path: str,
    events_path: str,
    metadata_path: str,
    version_major: int,
    version_minor: int,
    *,
    cli_calendar_path: str | None = None,
    chunk_rows: int | None = None,
    compression: str = "snappy",
) -> dict

# soil_pw0
watershed_soil_to_parquet(
    soil_path: str,
    output_path: str,
    version_major: int,
    version_minor: int,
    *,
    cli_calendar_path: str | None = None,
    chunk_rows: int | None = None,
    compression: str = "snappy",
) -> dict

# loss_pw0
watershed_loss_to_parquet(
    loss_path: str,
    output_dir: str,
    version_major: int,
    version_minor: int,
    *,
    compression: str = "snappy",
) -> dict

# chan.out
watershed_chan_peak_to_parquet(
    chan_path: str,
    output_path: str,
    version_major: int,
    version_minor: int,
    *,
    start_year: int | None = None,
    cli_calendar_path: str | None = None,
    chunk_rows: int | None = None,
    compression: str = "snappy",
) -> dict
```

`cli_calendar_path` points to `wepp_cli.parquet` (generated by `_ensure_cli_parquet` + `_build_cli_calendar_lookup`). Rust should read the calendar lookup directly from this parquet to avoid passing large tables over the FFI boundary.

### Public Python API (Phase 2)
```python
watershed_ebe_to_parquet(
    ebe_path: str,
    output_path: str,
    version_major: int,
    version_minor: int,
    *,
    start_year: int | None = None,
    cli_calendar_path: str | None = None,
    chunk_rows: int | None = None,
    compression: str = "snappy",
) -> dict

watershed_chanwb_to_parquet(
    chanwb_path: str,
    output_path: str,
    version_major: int,
    version_minor: int,
    *,
    start_year: int | None = None,
    cli_calendar_path: str | None = None,
    chunk_rows: int | None = None,
    compression: str = "snappy",
) -> dict

watershed_chnwb_to_parquet(
    chnwb_path: str,
    output_path: str,
    version_major: int,
    version_minor: int,
    *,
    start_year: int | None = None,
    cli_calendar_path: str | None = None,
    chunk_rows: int | None = None,
    compression: str = "snappy",
) -> dict
```

### Hillslope + Catalog API (Phase 2)
Hillslope parsers return column dicts for Python to assemble/write Parquet with existing orchestration.

```python
hillslope_pass_to_columns(
    pass_path: str,
    version_major: int,
    version_minor: int,
    *,
    cli_calendar_path: str | None = None,
) -> dict

hillslope_ebe_to_columns(
    ebe_path: str,
    version_major: int,
    version_minor: int,
    *,
    cli_calendar_path: str | None = None,
    start_year: int | None = None,
) -> dict

hillslope_element_to_columns(
    element_path: str,
    version_major: int,
    version_minor: int,
    *,
    start_year: int | None = None,
) -> dict

hillslope_loss_to_columns(
    loss_path: str,
    version_major: int,
    version_minor: int,
) -> dict

hillslope_soil_to_columns(
    soil_path: str,
    version_major: int,
    version_minor: int,
    *,
    cli_calendar_path: str | None = None,
    start_year: int | None = None,
) -> dict

hillslope_wat_to_columns(
    wat_path: str,
    version_major: int,
    version_minor: int,
    *,
    cli_calendar_path: str | None = None,
) -> dict

catalog_scan(base_path: str) -> list[dict]
```

`catalog_scan` returns the exact list of dicts produced by `_build_entry()` in
`wepppy/query_engine/activate.py` (keys: `path`, `extension`, `size_bytes`, `modified`, `schema`).

### Return payload
Each function returns a small dict with summary stats:
- `rows_written`
- `row_groups`
- `elapsed_ms`
- `schema_version` (string)
- `output_paths` (list)

Python wrappers may log these metrics for diagnostics but do not alter public return types.

## Schema and Metadata Parity
- All schemas must match the current Python writers in `wepppy/wepp/interchange/*_interchange.py`.
- Preserve field metadata keys: `units`, `description`.
- Preserve schema metadata keys written by `schema_with_version`:
  - `dataset_version`, `dataset_version_major`, `dataset_version_minor`, `schema_version`.
- PASS metadata parquet must include `version`, `nhill`, `max_years`, `begin_year`, `npart` in schema metadata.
- Row ordering must remain identical to Python output (chronological order + per-entity ordering).

## Parsing Rules (Phase 1)
### PASS (`pass_pw0.txt`)
- Handle header and `HILLSLOPE` metadata lines exactly as Python.
- Tokenization must support concatenated numbers (e.g., `0.97059-100`).
- Fortran overflow placeholders (`*****`) become `NaN`.
- Use `_julian_to_calendar` and `_compute_sim_day_index` semantics, plus `determine_wateryear` logic: water year = `year + 1` if month > 9, else `year`.
- Write two outputs: `pass_pw0.events.parquet` and `pass_pw0.metadata.parquet`.

### Soil (`soil_pw0.txt` / `.gz`)
- Support legacy header (no `Saturation`/`TSW`). Missing columns must be filled with `null`.
- Use CLI calendar when available; otherwise Gregorian calendar.
- Parse as streaming rows; flush every `chunk_rows`.

### Loss (`loss_pw0.txt`)
- Support all four table layouts (hill, channel, outlet, class data).
- Produce both `average` and `all_years` tables, matching Python filenames and schemas.
- Preserve type coercions and computed fields from Python.

### Channel peak (`chan.out`)
- Stream lines into column buffers; chunk at 500k rows.
- Compute date fields and water year.
- Match existing schema and metadata.

## Parsing Rules (Phase 2)
### Watershed EBE (`ebe_pw0.txt`)
- Follow existing Python parser behavior for event labeling, date handling, and water-year calculation.
- Preserve legacy outlet element inference logic when present.
- Match schema + metadata from `watershed_ebe_interchange.py`.

### Channel water balance (`chanwb.out`, `chnwb.txt`)
- Match Python column layouts and date handling.
- Preserve ordering, type coercions, and metadata from the existing parsers.

### Hillslope interchange (PASS/EBE/ELEMENT/LOSS/SOIL/WAT)
- Parity with hillslope parsers in `wepppy/wepp/interchange/` (schema, metadata, and row order).
- Respect `WEPP_INTERCHANGE_FORCE_SERIAL` and temp file behavior in Python wrappers.

## Parquet Writing Requirements
- Stream to a temp path then atomically rename (`.tmp` file), mirroring Python behavior.
- Use `snappy` compression by default (configurable).
- Honor the same dictionary encoding settings where possible.
- Ensure large files write in row groups sized for streaming (configurable `chunk_rows`).

## Error Handling
- Surface parse failures as Python exceptions with file name + line number.
- When possible, include a truncated line preview in the error message.
- Do not silently coerce errors (align with the "no fallback wrappers" directive).

## Observability
- Emit a per-run summary dict (rows, row groups, elapsed).
- Python wrappers may log the summary dict at debug level.
- Update Python loggers to record whether Rust or Python path was used.

## Validation Plan
1. **Golden parity tests**: Compare Rust outputs to Python outputs (schema + row-by-row values) on `tests/wepp/interchange/test_project`. Run with `WEPPPY_RUST_INTERCHANGE_TESTS=1`.
2. **Large fixture perf test** (manual): Run on `tests/wepp/interchange/fixtures/deductive-futurist/wepp` and capture runtime + memory. Set `WEPPPY_INTERCHANGE_FIXTURE` to target the large fixture when needed.
3. **Schema smoke tests**: Confirm `interchange_version.json` stays unchanged and catalog schema extraction still works.

Suggested parity approach:
- Write a utility that loads Rust and Python outputs, compares schema metadata, and checks column equality with a numeric tolerance for floats.

## Implementation Checklist (Complete)
- [x] Create `wepp_interchange` crate and add to `Cargo.toml` workspace.
- [x] Add PyO3 module entrypoint + packaging layout.
- [x] Implement common helpers: fast float scanning, CLI calendar lookup reader, water year logic, Julian/day conversions.
- [x] Implement PASS parser + Parquet writers.
- [x] Implement soil parser + Parquet writer (gzip support).
- [x] Implement loss parser + Parquet writers.
- [x] Implement channel peak parser + Parquet writer.
- [x] Add Python wrappers that dispatch to Rust when enabled.
- [x] Add parity tests + manual perf check instructions.

## Decisions
- **Arrow stack:** Standardize on `arrow2` + `parquet2` to keep builds pure-Rust and avoid C++ linking/packaging constraints. We only need Parquet output, not Arrow FFI integration.
- **Entry points:** Keep per-file entrypoints (mirrors current Python structure and allows targeted fallbacks).
- **CLI calendar:** Rust reads `wepp_cli.parquet` directly (avoid large FFI payloads).
- **Shared builders:** Use a small shared typed-builder layer (tokenization, date fields, chunked parquet writer) but keep file-specific parsers separate to avoid over-abstracting divergent schemas.
- **Catalog scanner:** Implemented in Phase 2 (Rust scan with Python fallback).

## Open Questions
- None (decisions captured above).

## Success Criteria
- 15 GB PASS file converts in under 1 hour on the current dev box.
- Peak memory stays under 4 GB for PASS/soil conversions.
- Parity tests pass for all Phase 1 + Phase 2 datasets.
- No schema or metadata regressions observed in query engine catalog scans.
