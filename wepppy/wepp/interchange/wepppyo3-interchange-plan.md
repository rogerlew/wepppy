# wepppyo3 Interchange Plan (Phase 1 + 2 Complete)
> Phase 1 + Phase 2 implementation plan for Rust/PyO3 interchange acceleration (watershed + hillslope + catalog scan).
> **Primary spec:** `/workdir/wepppy/wepppy/wepp/interchange/wepppyo3-interchange-spec.md`

## Status
- Phase 1 + Phase 2 complete (January 30, 2026).
- Rust is the default path; Python fallback logs explicit reasons.

## Validation (January 30, 2026)
- `pytest tests/wepp/interchange` (default fixture: `tests/wepp/interchange/test_project/output`): 39 passed, 3 skipped (pass/soil fixtures absent).
- `WEPPPY_RUST_INTERCHANGE_TESTS=1 WEPPPY_INTERCHANGE_FIXTURE=tests/wepp/interchange/fixtures/deductive-futurist/wepp/output pytest tests/wepp/interchange/test_watershed_interchange_rust_parity.py`: 13 passed.

## Spec Review: Gaps, Risks, Unclear Items
- **Fallback policy vs. core directive:** Spec wants a “safe fallback” to Python, but AGENTS.md forbids silent fallback wrappers. Policy: default to Rust, log Rust usage, and on Rust failure fall back to Python with explicit logging consistent with existing wepppyo3 usage (no env flags).
- **Schema version source of truth:** Rust needs the `INTERCHANGE_VERSION` values from `/workdir/wepppy/wepppy/wepp/interchange/versioning.py`. Use Python to pass version metadata into Rust.
- **Water-year semantics with CLI calendar:** Python uses Gregorian month (via julian) even when CLI calendar lookup is provided. Rust must mirror this, even if the CLI calendar is non-Gregorian, to preserve parity.
- **PASS float parsing parity:** Rust should treat Fortran overflow “*****” as NaN, even if Python currently does not.
- **`start_year` on PASS:** Spec shows a `start_year` arg for PASS but Python derives `start_year` from PASS metadata (`begin_year`). Decide whether to keep a hidden Rust arg or ignore external `start_year`.
- **Loss table enrichment:** Python adds derived `wepp_id` for channel tables (`_enrich_loss_tables`). Ensure Rust matches this logic (and any type casts) exactly.
- **Dictionary encoding parity:** Python uses `use_dictionary=True`. Rust must match schema and encoding; treat encoding as part of compatibility.
- **CLI parquet location:** `_build_cli_calendar_lookup` searches parent folders for a `climate/` directory. Rust should be handed the `wepp_cli.parquet` path from Python (assume a single CLI parquet).
- **Error types + Python wrappers:** Spec says “surface parse failures as Python exceptions.” Determine which exceptions to raise and ensure messages include file + line; avoid swallowing in wrappers.

## Phase 1 Implementation Plan (Step-by-Step)

### 0) Preflight Inventory (Read Before Coding)
- `/workdir/wepppy/wepppy/wepp/interchange/wepppyo3-interchange-spec.md`
- `/workdir/wepppy/wepppy/wepp/interchange/README.md`
- `/workdir/wepppy/wepppy/wepp/interchange/versioning.py`
- `/workdir/wepppy/wepppy/wepp/interchange/_utils.py`
- `/workdir/wepppy/wepppy/wepp/interchange/schema_utils.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_pass_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_soil_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_loss_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_chan_peak_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_interchange.py`
- `/workdir/wepppy/wepppy/all_your_base/hydro/hydro.py`
- `/workdir/wepppy/tests/wepp/interchange/test_watershed_pass_interchange.py`
- `/workdir/wepppy/tests/wepp/interchange/test_watershed_soil_interchange.py`
- `/workdir/wepppy/tests/wepp/interchange/test_watershed_loss_interchange.py`
- `/workdir/wepppy/tests/wepp/interchange/test_watershed_chan_peak_interchange.py`
- `/workdir/wepppyo3/Cargo.toml`
- `/workdir/wepppyo3/README.md`
- `/workdir/wepppyo3/sbs_map/Cargo.toml` (PyO3 pattern)
- `/workdir/wepppyo3/release/linux/py312/wepppyo3/__init__.py`

### 1) Rust Crate Layout and Responsibilities
Create a new PyO3 crate under `/workdir/wepppyo3/wepp_interchange` and add it to the workspace in `/workdir/wepppyo3/Cargo.toml`.

Proposed crate/modules (Phase 1):
- `src/lib.rs`
  - PyO3 module definition: `wepp_interchange_rust`
  - Exports: `watershed_pass_to_parquet`, `watershed_soil_to_parquet`, `watershed_loss_to_parquet`, `watershed_chan_peak_to_parquet`
  - Converts Rust errors to Python exceptions
- `src/errors.rs`
  - `InterchangeError` enum with variants for IO, parse, schema, calendar
  - Includes `path`, `line_number`, `line_preview` (truncated)
- `src/calendar.rs`
  - Read `wepp_cli.parquet` via `parquet2`
  - Build `{year -> Vec<(month, day)>}` lookup
  - Implement `_julian_to_calendar`, `_compute_sim_day_index`, and water-year logic to match Python
- `src/floats.rs`
  - Fast float parser (fast_float), handles concatenated exponent tokens; treat “*****” as NaN
- `src/schema.rs`
  - Arrow2 schemas + field metadata for PASS (events + metadata), soil, loss (8 tables), chan peak
  - Encodes dataset version metadata from Python-provided values
- `src/parquet.rs`
  - Chunked writer with row groups per `chunk_rows`
  - Temp file + atomic rename logic to mirror Python
  - Snappy compression by default
- `src/pass.rs`, `src/soil.rs`, `src/loss.rs`, `src/chan_peak.rs`
  - File-specific parsers + streaming writers
  - Maintain row ordering and field ordering as in Python

### 2) Python Wrapper Changes (Preserve Public API)
Keep existing Python signatures and return types in these files; add a thin Rust dispatch layer that mirrors outputs:
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_pass_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_soil_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_loss_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_chan_peak_interchange.py`

Wrapper behavior:
- Centralize Rust import + fallback logging in a new private helper (suggested): `/workdir/wepppy/wepppy/wepp/interchange/_rust_interchange.py`
  - Attempts import `from wepppyo3 import wepp_interchange` (or `wepppyo3.wepp_interchange`)
  - Logs “Rust path” vs “Python path” explicitly and logs any fallback to Python
  - No environment-variable toggles for interchange selection
- For PASS + chan peak: ensure `cli_calendar_path` is computed from `_ensure_cli_parquet` and passed into Rust; do **not** pass full calendar tables.
- For soil: prefer passing `.gz` path directly to Rust; remove temp “.src” file usage in Rust path only.
- For loss: return mapping keys identical to current Python (`average_hill`, `all_years_out`, etc.).
- Keep `interchange_version.json` management in Python (no change to `/workdir/wepppy/wepppy/wepp/interchange/versioning.py`).

### 3) Parquet Schema Parity Strategy (Exact Match)
Goal: Rust output must match Python schemas and metadata exactly.

Approach:
- **Canonical schema snapshot:** Add a small Python utility (test-only) that serializes each PyArrow schema (fields + metadata) to JSON. Store under `tests/wepp/interchange/fixtures/schema_snapshots/*.json`.
- **Parity tests:** For each converter, run Python output and Rust output, then assert:
  - `schema.equals(expected, check_metadata=True)`
  - Schema metadata contains `dataset_version`, `dataset_version_major`, `dataset_version_minor`, `schema_version`
  - Field metadata includes `units` and `description` keys where defined
- **PASS metadata schema metadata:** Must include `version`, `nhill`, `max_years`, `begin_year`, `npart` with string values.
- **Loss tables:** Confirm schema metadata includes `schema_version` and version keys from `schema_with_version`.
- **Type parity:** Use Arrow2 types that map cleanly to PyArrow (`Int16`, `Int32`, `Float64`, `Utf8`).

### 4) CLI Calendar Lookup in Rust (wepp_cli.parquet)
- Python wrapper calls `_ensure_cli_parquet` and passes `cli_calendar_path` into Rust.
- Rust reads only the needed columns:
  - Prefer `year`, `month`, `day_of_month`
  - Fallback to `year`, `mo`, `da`
- Build per-year day lists sorted by `(year, month, day)`.
- Implement:
  - `_julian_to_calendar(year, julian, lookup)` with CLI lookup override
  - `_compute_sim_day_index` that mirrors `/workdir/wepppy/wepppy/wepp/interchange/_utils.py`
- **Water year** must match `determine_wateryear` in `/workdir/wepppy/wepppy/all_your_base/hydro/hydro.py` (Gregorian month from `julian`), even when using CLI lookup for `month`/`day_of_month`.

### 5) Error Handling and Logging
- Rust errors must include: file path, line number, and a truncated line preview.
- Convert Rust errors to Python exceptions (`ValueError` for parse, `IOError` for file I/O).
- Default to Rust, log Rust usage, and log any fallback to Python (no env-flag gating).

### 6) Performance Considerations
- Stream inputs with `BufRead` and avoid full-file reads.
- Use `fast_float` + `memchr` token scans for numeric parsing.
- Pre-allocate column buffers; reuse between row groups.
- Row groups: one per `chunk_rows` (match Python defaults: PASS/soil 250k, chan peak 500k).
- Use snappy compression; maintain order of rows (chronological + WEPP id ordering).

### 7) Testing Plan (Parity + Performance)
**New tests (pytest):**
- Add parity tests that run both Python and Rust converters on `tests/wepp/interchange/test_project`.
- Mark with `@pytest.mark.integration` (and `@pytest.mark.slow` if needed).
- Skip tests gracefully if `wepppyo3.wepp_interchange` is not importable.
- Compare:
  - Output paths
  - Schema + metadata
  - Row counts
  - Column values (float tolerance + NaN equality)

**Manual perf validation:**
- Run on `/workdir/wepppy/tests/wepp/interchange/fixtures/deductive-futurist/wepp` (15 GB PASS file).
- Capture wall clock + peak RSS; compare to Python baseline.

**Regression checks:**
- Ensure existing tests in `/workdir/wepppy/tests/wepp/interchange/` still pass when Rust is disabled.

### 8) Build / Release (wepppyo3)
- Add crate to `/workdir/wepppyo3/Cargo.toml` workspace.
- Build:
  - `cargo build -p wepp_interchange_rust --release`
- Copy artifacts into canonical release:
  - `target/release/libwepp_interchange_rust.so` → `/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so`
- Add Python package:
  - `/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/__init__.py` exporting functions
- Bump `/workdir/wepppyo3/release/linux/py312/wepppyo3/__init__.py` `__version__` for deployment tracking.

### 9) Deployment (wepppy)
- Sync updated release tree into the Python environment used by wepppy (see `/workdir/wepppyo3/README.md`).
- Verify `import wepppyo3.wepp_interchange` inside the wepppy runtime (container or host venv).
- Run parity tests; then run a targeted watershed interchange job to confirm logging and output paths.

## Expected Change List (Phase 1)
**New (wepppyo3):**
- `/workdir/wepppyo3/wepp_interchange/Cargo.toml`
- `/workdir/wepppyo3/wepp_interchange/src/lib.rs`
- `/workdir/wepppyo3/wepp_interchange/src/errors.rs`
- `/workdir/wepppyo3/wepp_interchange/src/calendar.rs`
- `/workdir/wepppyo3/wepp_interchange/src/floats.rs`
- `/workdir/wepppyo3/wepp_interchange/src/schema.rs`
- `/workdir/wepppyo3/wepp_interchange/src/parquet.rs`
- `/workdir/wepppyo3/wepp_interchange/src/pass.rs`
- `/workdir/wepppyo3/wepp_interchange/src/soil.rs`
- `/workdir/wepppyo3/wepp_interchange/src/loss.rs`
- `/workdir/wepppyo3/wepp_interchange/src/chan_peak.rs`
- `/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/__init__.py`

**Modify (wepppyo3):**
- `/workdir/wepppyo3/Cargo.toml` (workspace member)
- `/workdir/wepppyo3/Cargo.lock`
- `/workdir/wepppyo3/release/linux/py312/wepppyo3/__init__.py` (version)

**Modify (wepppy):**
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_pass_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_soil_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_loss_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_chan_peak_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/__init__.pyi` (only if public signatures change)
- `/workdir/wepppy/wepppy/wepp/interchange/_rust_interchange.py` (new private helper, if adopted)

**Tests:**
- `/workdir/wepppy/tests/wepp/interchange/test_watershed_pass_interchange_rust.py` (new parity test)
- `/workdir/wepppy/tests/wepp/interchange/test_watershed_soil_interchange_rust.py`
- `/workdir/wepppy/tests/wepp/interchange/test_watershed_loss_interchange_rust.py`
- `/workdir/wepppy/tests/wepp/interchange/test_watershed_chan_peak_interchange_rust.py`
- `/workdir/wepppy/tests/wepp/interchange/fixtures/schema_snapshots/` (new schema JSON snapshots)

## Decisions Locked In
1. **Fallback policy:** Default to Rust; log Rust usage and log any fallback to Python (no env flags for interchange selection).
2. **PASS overflow tokens:** Treat “*****” as NaN in Rust.
3. **Version metadata source:** Python passes version metadata to Rust via arguments.
4. **Dictionary encoding:** Encoding is part of compatibility; Rust must match schema and encoding.
5. **CLI calendar file:** Assume a single `wepp_cli.parquet`; Python supplies its path to Rust.
6. **Test gating:** Rust parity tests are development-only (not required in CI).

## Phase 2 Implementation Plan (Watershed EBE/ChanWB/ChnWB + Catalog + Hillslope)

### Phase 2 Scope (Required)
Status: **Completed** (January 30, 2026; Rust parsers, Python wrappers, catalog scan hook, tests).

- [x] Watershed EBE (`ebe_pw0.txt`)
- [x] Channel water balance (`chanwb.out`) and channel OFE water balance (`chnwb.txt`)
- [x] Catalog scan acceleration (`wepppy.query_engine.activate._build_catalog` + `_iter_catalog_files`)
- [x] Hillslope interchange (PASS/EBE/ELEMENT/LOSS/SOIL/WAT)

### Phase 2 Step-by-Step Plan

#### 2.1 Rust crate extensions (wepppyo3)
- Add new parsers + writers:
  - `src/ebe.rs` (watershed EBE)
  - `src/chanwb.rs` (chanwb)
  - `src/chnwb.rs` (chnwb)
  - `src/hill_pass.rs`, `src/hill_ebe.rs`, `src/hill_element.rs`, `src/hill_loss.rs`, `src/hill_soil.rs`, `src/hill_wat.rs`
- Extend `src/schema.rs` for all new schemas (fields + metadata) matching Python.
- Extend `src/lib.rs` PyO3 exports:
  - `watershed_ebe_to_parquet`
  - `watershed_chanwb_to_parquet`
  - `watershed_chnwb_to_parquet`
  - `hillslope_pass_to_parquet`
  - `hillslope_ebe_to_parquet`
  - `hillslope_element_to_parquet`
  - `hillslope_loss_to_parquet`
  - `hillslope_soil_to_parquet`
  - `hillslope_wat_to_parquet`
- Reuse existing `calendar.rs`, `floats.rs`, and `parquet.rs` helpers; do not duplicate logic.

#### 2.2 Python wrapper updates (wepppy)
- Add Rust dispatch to:
  - `/workdir/wepppy/wepppy/wepp/interchange/watershed_ebe_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/watershed_chanwb_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/watershed_chnwb_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/hill_pass_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/hill_ebe_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/hill_element_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/hill_loss_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/hill_soil_interchange.py`
  - `/workdir/wepppy/wepppy/wepp/interchange/hill_wat_interchange.py`
- Use `/workdir/wepppy/wepppy/wepp/interchange/_rust_interchange.py` for import + fallback logging (same policy as Phase 1).
- Pass `INTERCHANGE_VERSION` args into Rust, and `cli_calendar_path` where applicable (EBE/chanwb/chnwb).
- Preserve existing return types and file naming conventions.

#### 2.3 Watershed EBE parser details
- Mirror `run_wepp_watershed_ebe_interchange` behavior:
  - Event labeling, legacy outlet element inference
  - `start_year` handling and CLI calendar lookups
  - Same row ordering + schema metadata
- Ensure special cases (blank lines, section headers) match Python parsing rules.

#### 2.4 Channel water balance parsers (chanwb/chnwb)
- Mirror existing Python column layouts exactly.
- Preserve `start_year` logic and water-year fields.
- Match schema metadata (units/description).

#### 2.5 Hillslope interchange parsers
- Match Python behaviors per report:
  - PASS: multi-line numeric blocks, `EVENT`/`SUBEVENT` handling, per-hillslope ordering.
  - EBE: legacy outlet element inference rules.
  - ELEMENT: fixed-width parsing + carry-forward value logic.
  - LOSS: per-hillslope class data parsing.
  - SOIL + WAT: daily records per OFE, calendar lookups.
- Preserve Python temp file behavior and `WEPP_INTERCHANGE_FORCE_SERIAL` semantics in wrappers (Rust should not override orchestration).
- For hillslope parallelism, keep Python’s process-pool orchestration; Rust runs per-file parser only.

#### 2.6 Catalog scan acceleration (Rust optional)
- Add a Rust helper to scan interchange dir for known Parquet outputs, returning:
  - file list, sizes, schema metadata (dataset version), and timestamps
- Wire into `wepppy.query_engine.activate`:
  - Replace `Path.glob` + repeated schema reads with Rust scan where available
  - Fall back to Python scan with explicit logging on Rust failure

#### 2.7 Schema parity strategy (Phase 2)
- Expanded schema snapshot utility:
  - `ebe`, `chanwb`, `chnwb`
  - Hillslope outputs (`hill_pass`, `hill_ebe`, `hill_element`, `hill_loss`, `hill_soil`, `hill_wat`)
- Parity tests (dev-only) consolidated in:
  - `tests/wepp/interchange/test_watershed_interchange_rust_parity.py`
- Assertions:
  - Schema equality + metadata
  - Row counts + stable ordering
  - Float tolerance + NaN equivalence
- Fixture selection:
  - Default fixture: `tests/wepp/interchange/test_project/output`
  - Override with `WEPPPY_INTERCHANGE_FIXTURE=tests/wepp/interchange/fixtures/deductive-futurist/wepp/output`

#### 2.8 Performance + memory targets (Phase 2)
- Streaming parse for all new converters; no full-file reads.
- Keep chunk sizes aligned with Python defaults (or configurable via Python wrappers).
- For hillslope outputs, ensure per-file parsing is fast; defer parallel orchestration to Python.

#### 2.9 Build + release (wepppyo3)
- Add new modules to workspace and rebuild:
  - `cargo build -p wepp_interchange_rust --release`
- Copy `.so` into `/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/`.
- Update `wepppyo3` `__version__` in `/workdir/wepppyo3/release/linux/py312/wepppyo3/__init__.py`.

#### 2.10 Deployment (wepppy)
- Sync release tree into the runtime environment (same procedure as Phase 1).
- Smoke-check `run_wepp_watershed_interchange` and `run_wepp_hillslope_interchange` on fixtures.

### Phase 2 Files to Inspect Before Coding
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_ebe_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_chanwb_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_chnwb_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_pass_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_ebe_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_element_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_loss_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_soil_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_wat_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/write_parquet_with_pool.py` (parallel orchestration)
- `/workdir/wepppy/wepppy/wepp/interchange/interchange_documentation.py` (schema previews)
- `/workdir/wepppy/wepppy/wepp/interchange/versioning.py` (schema metadata)
- `/workdir/wepppy/wepppy/wepp/interchange/_utils.py` (calendar + CLI helpers)
- `/workdir/wepppy/wepppy/query_engine/activate.py` (catalog scan targets)

### Phase 2 Expected Change List
**New (wepppyo3):**
- `/workdir/wepppyo3/wepp_interchange/src/ebe.rs`
- `/workdir/wepppyo3/wepp_interchange/src/catalog.rs`
- `/workdir/wepppyo3/wepp_interchange/src/chanwb.rs`
- `/workdir/wepppyo3/wepp_interchange/src/chnwb.rs`
- `/workdir/wepppyo3/wepp_interchange/src/hill_pass.rs`
- `/workdir/wepppyo3/wepp_interchange/src/hill_ebe.rs`
- `/workdir/wepppyo3/wepp_interchange/src/hill_element.rs`
- `/workdir/wepppyo3/wepp_interchange/src/hill_loss.rs`
- `/workdir/wepppyo3/wepp_interchange/src/hill_soil.rs`
- `/workdir/wepppyo3/wepp_interchange/src/hill_wat.rs`

**Modify (wepppyo3):**
- `/workdir/wepppyo3/wepp_interchange/src/lib.rs`
- `/workdir/wepppyo3/wepp_interchange/src/schema.rs`
- `/workdir/wepppyo3/wepp_interchange/src/parquet.rs` (if shared writer needs tweaks)
- `/workdir/wepppyo3/Cargo.toml`
- `/workdir/wepppyo3/Cargo.lock`
- `/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/__init__.py`
- `/workdir/wepppyo3/release/linux/py312/wepppyo3/__init__.py` (version)

**Modify (wepppy):**
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_ebe_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_chanwb_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/watershed_chnwb_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_pass_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_ebe_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_element_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_loss_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_soil_interchange.py`
- `/workdir/wepppy/wepppy/wepp/interchange/hill_wat_interchange.py`
- `/workdir/wepppy/wepppy/query_engine/activate.py` (catalog scan hook)

**Tests (dev-only):**
- `/workdir/wepppy/tests/wepp/interchange/test_watershed_interchange_rust_parity.py`
- `/workdir/wepppy/tests/wepp/interchange/fixtures/schema_snapshots/` (new snapshots)

### Phase 2 Open Decisions (If Any)
- Catalog scan API surface is locked: Rust must return the exact list of dicts that `_build_entry()` produces today (same keys, value formats, and ordering) so `activate.py` can consume it directly with no translation layer.
- File ordering guarantees are not required beyond the existing Python behavior.
