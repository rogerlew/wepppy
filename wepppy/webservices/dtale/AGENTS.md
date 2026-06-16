# D-Tale Microservice Notes

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Purpose
`wepppy.webservices.dtale` embeds the upstream D-Tale Flask app behind an internal
loader that understands WEPP Cloud run directories. The service lives behind
`/internal/load` and the Gunicorn entry point advertises the D‑Tale UI at the
usual `/dtale/...` routes.

## Loader Flow (`/internal/load`)
1. Resolve run working directory via `get_wd(runid)`.
2. Enforce allowed file types (Parquet/CSV/Feather/Pickle variants) and size
   limits (`DTALE_MAX_FILE_MB`, `DTALE_MAX_ROWS`).
3. Fingerprint the target and reuse an in-memory D-Tale instance when the file
   and cached state match; otherwise refresh the cache.
4. Register geojson assets (subcatchments, channels, ag fields) and remember
   per-dataset defaults.
5. For Parquet/GeoParquet/PQ files, register a lazy Parquet backend instead of
   reading the full file into pandas. The backend reads schema/row counts with
   PyArrow/DuckDB and returns only bounded pandas slices for D-Tale grid pages.
6. For CSV/TSV/Feather/Pickle files, load a pandas DataFrame through the eager
   D-Tale path.
7. Auto-create string alias columns (`WeppID`, `TopazID`, `ChannelID`, etc.) so
   D-Tale’s map dropdowns expose the identifiers even when the parquet stores
   numeric values.
8. Return the `dtale/main/<id>` URL to the caller.

## GeoJSON Support
- Geojson files are fingerprinted and registered once per dataset.
- Identifier aliases (`wepp_id` → `WeppID`, `topaz_id` → `TopazID`, …) are added
  to the feature properties, and everything is coerced to strings to satisfy
  D‑Tale’s map requirements.
- The service records preferred location columns and feature id keys so the map
  UI defaults to the correct layer.

## D-Tale Monkey Patches
The wrapper patches D-Tale at import time (idempotently) to:
- Expose identifier candidates in the map dropdown even when they are not
  originally string typed.
- Fit the viewport (`fitbounds="locations"`) for choropleth, scattergeo, and
  mapbox charts when using custom geojson.
- Intercept `/dtale/data/<id>` only for registered lazy Parquet datasets and
  serve requested row ranges from DuckDB/PyArrow. All non-lazy datasets delegate
  to the upstream D-Tale view.

`__init__.py` re-exports everything from `dtale.py`; external consumers can keep
importing `wepppy.webservices.dtale`.

## Lazy Parquet Backend
- The lazy backend is modeled on upstream D-Tale's ArcticDB paging path, but
  avoids adding ArcticDB as a runtime dependency.
- `LazyParquetDtaleInstance` must never load the full Parquet file as a pandas
  DataFrame. Its `data` property deliberately raises; use `load_data(row_range,
  columns)` for bounded grid reads.
- The D-Tale shell is seeded with a one-row sample only so upstream D-Tale can
  build settings, dtypes, and URLs. The authoritative row count and grid rows
  come from the lazy backend.
- Unsupported D-Tale actions for lazy Parquet datasets must fail explicitly or
  operate on bounded data. Do not add a fallback that calls `pd.read_parquet` or
  full Arrow `to_pandas()`.
- Keep upstream sync burden low: patch one Flask view endpoint
  (`dtale.get_data`) behind a `_wepppy_patched` guard and avoid copying large
  blocks of upstream D-Tale source.

## Environment Variables
- `DTALE_BASE_URL` – service URL used when D-Tale returns redirects.
- `DTALE_INTERNAL_TOKEN` – shared secret between browse microservice and the
  loader (`X-DTALE-TOKEN` header).
- `DTALE_MAX_FILE_MB`, `DTALE_MAX_ROWS` – guardrails for large loads.

## Service Entrypoint
Gunicorn command used in docker compose:
```
gunicorn --workers 1 --bind 0.0.0.0:9010 --log-level info wepppy.webservices.dtale:app
```
Keep workers at 1—D-Tale keeps state in-process.

## Extending
- Add new geojson assets by augmenting `_ensure_geojson_assets`.
- Update identifier alias tuples (`_IDENTIFIER_STRING_ALIASES`) when new id
  fields surface.
- When modifying D-Tale behavior, wrap patches with `_wepppy_patched` guards to
  avoid double-wrapping during reloads.
