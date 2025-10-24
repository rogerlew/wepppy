# WEPP Management Agent Guide

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Mission Snapshot
- Maintain the management file toolchain that turns landcover metadata into runnable `.man` scenarios for WEPP and channel simulations.
- Keep template libraries (`data/*.json`, `channels.defs`, `*.man`) internally consistent so CLI, web, and batch workflows resolve the same management keys.
- Protect backwards compatibility with historic WEPP 95.7 and 98.4 file formats while extending support for new disturbance catalogues.

## Primary Assets
- `managements.py` – parser/writer for management files plus helpers like `get_management`, `merge_managements`, `get_management_summary`, and `get_disturbed_classes`.
- `channels.py` – channel template loader (`load_channels`, `get_channel`) and D50/Cs lookup support.
- `pmetpara.py` – `pmetpara_prep` writer that emits `pmetpara.txt` with canopy coefficients per plant loop.
- `utils/` – synthesis tooling (`ManagementMultipleOfeSynth`, `ManagementRotationSynth`, `downgrade_to_98_4_format`) for multi-OFE and legacy scenarios.
- `data/` – canonical management assets (map JSON, disturbed catalogues, regional `.man` files, `channel_d50_cs.csv`).
- `tests/` – regression fixtures (`test_multiple_ofe.py`, `test_rotation_stack.py`, CSV/GeoJSON datasets).
- Type stubs: `channels.pyi`, `managements.pyi`, `utils/*.pyi` (must stay in sync with runtime modules).

## Standard Workflow
1. **Scope** – identify which assets change (map JSON entries, template `.man`, Python parsers, or synthesis utilities). Touch the smallest surface to avoid invalidating cached management directories.
2. **Edit** – prefer absolute imports inside the package. When adding public helpers, extend `__all__` in the module and update the matching `.pyi`.
3. **Data updates** – validate JSON/CSV integrity (keys used elsewhere, numeric coercion). Keep descriptions under 55 characters to satisfy the parser’s `desc` truncation logic.
4. **Compatibility** – confirm new management records still serialize under both WEPP 95.7 and 98.4 expectations (`downgrade_to_98_4_format` when required). Avoid breaking `ScenarioReference` indexes.
5. **Document** – update the relevant README or domain docs if payload schemas or data contracts change.
6. **Validate** – run targeted tests and optional manual inspections (see below). Regenerate derived files (e.g., `pmetpara.txt`) only through provided helpers.

## Validation Checklist
- `wctl run-pytest tests/wepp/management/test_multiple_ofe.py`
- `wctl run-pytest tests/wepp/management/test_rotation_stack.py`
- Spot-check new or modified `.man` files with `python -m wepppy.wepp.management.managements <path>` (prints parsed summary).
- For disturbed catalog updates, ensure keys line up with `map.json` and any downstream NoDb consumers before committing.

## Implementation Notes
- Management parsing relies on sentinel comments (for example `#landuse` markers). Preserve comment structure when editing templates.
- `Management.__setitem__` accepts dotted attribute paths (e.g. `plant.data.rtyp`); keep setter logic updated when new attributes become mutable.
- `ManagementMultipleOfeSynth` rewrites scenario names with `OFE{n}_` prefixes—when introducing new sections ensure renaming and `ScenarioReference` updates are covered.
- `pmetpara_prep` accepts scalars or mappings. Validate new call sites supply entries for every plant loop or handle missing keys gracefully.
- When extending channel definitions, keep `channels.defs` blocks separated by blank lines and ensure `_format_value` formatting rules remain valid for new numeric ranges.

## Data Maintenance Workflow
1. **New management key** – add the key to the appropriate map (`map.json`, `disturbed.json`, regional variants) and point `ManagementFile` to a `.man` stored inside `data/<collection>/`.
2. **Template authoring** – derive new `.man` files from vetted sources (FSWEPP, GeoWEPP, BAER). Keep descriptions within 55 characters and match `landuse` enumerations used by `ManagementLoop`.
3. **CSV mirrors** – if the key surfaces in `weppcloud_managements.csv`, `weppcloud_AU_managements.csv`, or disturbance exports, regenerate them via `tests/wepp/management/export_covers.py` and stage the resulting CSV for review.
4. **Disturbance alignments** – when editing disturbance maps, sync lookup tables in `wepppy/nodb/mods/disturbed/data/` (for example `disturbed_land_soil_lookup.csv`) so severity classes keep valid management references.
5. **Channel assets** – update `channel_d50_cs.csv` and `channels.defs` together; verify that `load_channel_d50_cs()` continues to coerce numeric columns and that `get_channel()` renders overrides correctly.

## Catalog Quick Reference
- `data/map.json` – default landcover-to-management lookup consumed by `NoDb` controllers.
- `data/disturbed.json`, `data/c3s-disturbed*.json`, regional `*_map.json` – overrides for disturbance scenarios and partner datasets; keys must align with NoDb mods.
- `weppcloud_managements.csv`, `weppcloud_AU_managements.csv`, `disturbed_weppcloud_managements.csv` – curated exports consumed by web UIs; regenerate via `tests/wepp/management/export_covers.py`.
- `tests/wepp/management/validate.py` – scaffolding used during data migrations; adapt when introducing new map flavors.
- `tests/wepp/management/mofe_dir/` – fixture bundle for multi-OFE synthesis regression checks.

## Coordination Points
- `wepppy/nodb/core/wepp.py` and `wepppy/nodb/core/landuse.py` expect map keys and summaries to stay stable; update the controllers’ validation messages if new classes are introduced.
- `wepppy/nodb/mods/disturbed` relies on consistent `DisturbedClass` strings—document any renames in `docs/disturbance_*` notes before shipping.
- `wepppy/export/export.py` references `_management_dir` when packaging runs; ensure new assets live under the canonical directory tree to avoid missing file errors.
- `wepppy/microservices/browse.py` may read management files directly; test browse flows if altering public APIs such as `get_management_summary`.

## Utilities & QA
- `python tests/wepp/management/export_covers.py` – regenerate management CSV mirrors and extended disturbance lookups.
- `python tests/wepp/management/validate.py` – smoke-check that every management key resolves and round-trips.
- `python -m wepppy.wepp.management.managements data/<collection>/<file>.man` – print parsed summaries for manual inspection.
- `python -m wepppy.wepp.management.utils.multi_ofe <args>` (or targeted unit tests) – confirm multi-OFE syntheses still annotate OFE prefixes and scenario references.

## Troubleshooting
- **KeyError reading management** – confirm the requested key exists in `map.json`, the referenced file is present under `data/`, and disturbed overrides fall back correctly.
- **Malformed output** – run `Management(str_path)` round trips to ensure read/write parity; trailing whitespace in `.man` files often causes misaligned loops.
- **Stub mismatches** – after adding or renaming public methods update `channels.pyi`, `managements.pyi`, and `utils/*.pyi`; run `wctl run-stubtest wepppy.wepp.management` when available.
- **Channel calibration drift** – if `get_channel` overrides fail, double-check that `chnnbr` and `chnn` stay numeric strings and that `_format_value` does not swallow significant digits.

## References
- Root guidance: `AGENTS.md`
- Interchange docs: `wepppy/wepp/interchange/README.md`
- Disturbance datasets: `wepppy/wepp/management/data/`
- Template synthesis how-to: `tests/wepp/management/test_multiple_ofe.py`
