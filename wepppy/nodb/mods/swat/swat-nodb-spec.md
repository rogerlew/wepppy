# SWAT NoDb Module Specification (WEPPpy / WEPPcloud)

> Define the NoDb module, configuration surface, and integration strategy for running SWAT+ routing on top of WEPP hillslope outputs. This spec complements `wepppy/nodb/mods/swat/wepp-swat-spec.md` (data mapping and SWAT+ IO details) and `wepppyo3/docs/wepp-hill-pass-to-swat-rec-spec.md` (Rust recall conversion).

## Purpose
Provide a concrete, implementation-ready contract for a SWAT NoDb mod that:
- Is enabled only through run configuration (not via the mods menu).
- Uses WEPP hillslope pass outputs to populate SWAT+ recall inputs.
- Produces a runnable SWAT+ `TxtInOut` directory with consistent routing connectivity.
- Integrates with WEPPcloud UI in a staged way without breaking existing runs.

## Goals
- Define the NoDb class surface, state, and file layout.
- Specify configuration keys and defaults that match existing WEPPpy conventions.
- Establish a deterministic build pipeline for SWAT+ inputs.
- Keep Rust (wepppyo3) focused on recall file generation; keep run assembly in Python unless a compelling reason exists.
- Capture a phased plan for UI and execution integration.

## Current implementation status (2026-01)
- `Swat` NoDb class implemented with recall generation, connectivity build, template patching, and run orchestration.
- Recall generation prefers Rust (`wepppyo3.swat_utils`) and falls back to Python conversion with calendar-aware date lookup.
- Recall filenames are flattened (no `/` in `recall.rec`), and recall files are copied into `TxtInOut/` even when `recall_subdir` is used.
- `recall.con` AREA_HA is patched from `watershed/hillslopes.parquet`.
- `time.sim` alignment uses recall bounds; `force_time_start_year` forces recall/time alignment when needed.
- Channel connectivity emits `chandeg.con`, `channel-lte.cha`, and `hyd-sed-lte.cha` with width/geometry derived from Peridot/WBT inputs.
- WST validation enforces `weather-sta.cli` entries; `recall_wst=auto` picks the first available station.
- Template safety patches: generate `om_water.ini` and `plant.ini` if missing; set `hru-data.hru` `surf_stor` to `null` to avoid wetland init failures.
- Aquifer outputs are disabled by default (`disable_aquifer=true`) unless aquifer connectivity is provided.
- SWAT+ numeric guards are maintained in `rogerlew/swatplus` `wepppy/guards` and the guarded binary is bundled under `wepppy/nodb/mods/swat/bin/`.

## Non-goals (Phase 1)
- Full calibration workflows or parameter estimation beyond channel defaults.
- A mod menu toggle (SWAT remains config-only until UI is ready).
- A general SWAT+ project generator from scratch.

## Constraints and conventions
- SWAT is a NoDb mod and follows `NoDbBase` lifecycle (lock, mutate, `dump_and_unlock`).
- Mod enablement is config-only: `nodb.mods` must include `swat`.
- Do not add `swat` to the mods menu registries (`MOD_DISPLAY_NAMES`, etc.). SWAT is surfaced through the WEPP control only.
- SWAT-DEG (`channel_sd` / `chandeg.con` / `channel-lte.cha` / `hyd-sed-lte.cha`) is the canonical channel object set.
- MVP bundles a Linux-only SWAT+ binary; other platforms can be added later.
- Avoid hidden fallbacks. Missing templates or binaries should fail fast with explicit errors.
- Keep doc text dense; avoid verbose prose.

## Run layout (proposed)
All SWAT artifacts live under the run working directory (`wd`).

```
<wd>/swat/
  TxtInOut/                 # runnable SWAT+ project
    recall/                 # recall files (recall_subdir)
  outputs/                  # archived SWAT+ outputs + index.json
  manifests/
    recall_manifest.json
  logs/
    swat_build.log
```

Notes:
- `TxtInOut` must be self-contained and runnable by the SWAT+ binary.
- Recall files live under `TxtInOut/recall/` (or `recall_subdir`) and are referenced by `recall.rec`.
- `recall.rec` filenames must be basenames (no path separators); copy recall files into `TxtInOut/` for SWAT execution.

## NoDb module contract

### Module location
- `wepppy/nodb/mods/swat/swat.py`
- `__all__` must include the public class(es) and helpers.

### Class
- Class name: `Swat` (preferred) or `SwatPlus` (if name collision occurs).
- Base class: `NoDbBase`
- `filename = 'swat.nodb'`

### State (minimum)
- `enabled: bool`
- `template_dir: str` (SWAT+ TxtInOut template root)
- `txtinout_dir: str` (output directory)
- `recall_dir: str` (output/staging directory)
- `outputs_dir: str` (SWAT+ outputs archive root)
- `recall_manifest: list[dict] | None`
- `channel_params: dict`
- `build_summary: dict | None`
- `last_build_at: str | None` (ISO-8601)
- `run_summary: dict | None`
- `last_run_at: str | None` (ISO-8601)
- `status: str` (idle/building/ready/error)

### Key methods
- `build_inputs()`
  - Orchestrates recall generation, connectivity build, and template patching.
- `build_recall()`
  - Calls `wepppyo3.swat_utils.wepp_hillslope_pass_to_swat_recall(...)` with `wepp_output_dir`, `swat_txtinout_dir`, `recall_connections`, `recall_wst`, and `recall_object_type`, and stores manifest.
- `build_recall_connections()`
  - Derives `wepp_id -> chn_enum` from `watershed/hillslopes.parquet` and `watershed/channels.parquet`.
- `build_connectivity()`
  - Writes `recall.con` (and `chandeg.con` if channel objects are emitted).
- `patch_txtinout()`
  - Copies a template and applies changes to `file.cio`, `time.sim`, channel parameter files, and `print.prt` if required.
- `validate()`
  - Lightweight checks (file existence, count alignment, summary totals).

All mutations must run inside `with self.locked():` and finish with `dump_and_unlock()`.

## Configuration surface (proposed)
Config is read from the run config file (for example `config.cfg`).

```
[nodb]
mods = ['swat']

[swat]
enabled = true
swatplus_version_major = 1
swatplus_version_minor = 4

# SWAT+ binary (bundled by default; keep original build name)
swat_bin = wepppy/nodb/mods/swat/bin/swatplus-61.0.2.61-17-g834fad2-gnu-lin_x86_64

# Template selection (bundled)
swat_template_dir = wepppy/nodb/mods/swat/templates/ref_1hru

# Recall generation
recall_filename_template = hill_{wepp_id:05d}.rec
recall_subdir = recall
include_subsurface = true
include_tile = true
cli_calendar_path =
recall_wst = auto
recall_object_type = sdc

# Time alignment
time_start_year = 1
force_time_start_year = false

# Channel routing + geometry
width_method = bieger2015   # or qswat
width_fallback = error      # or qswat
netw_area_units = auto      # auto | m2 | km2
qswat_wm = 1.0
qswat_we = 0.5
qswat_dm = 0.5
qswat_de = 0.4

# Channel parameter overrides (SWAT-DEG)
channel_mann = 0.05
channel_fpn =
channel_erod_fact = 0.01
channel_cov_fact = 0.01
channel_d50_mm = 12.0
disable_aquifer = true

[wepp]
# Controls whether the WEPP watershed run executes and whether WEPP channel options are shown.
run_wepp_watershed = true
```

Notes:
- Use `nodb.mods` for enablement (config-only).
- `swatplus_version_*` should mirror WEPPpy/WEPPcloud versioning conventions used by `wepppyo3`.
- Any blank values mean "use template default" (do not insert empty strings into SWAT files).
- `wepp.run_wepp_watershed` controls whether the WEPP watershed run executes and whether WEPP channel options are shown.
- Bundled templates: `wepppy/nodb/mods/swat/templates/ref_1hru` (derived from `Osu_1hru`), `Ames_sub1`, and `Osu_1hru`.
- `disable_aquifer=true` removes aquifer objects from `object.cnt` and strips aquifer outflows from `rout_unit.con`.

## Data flow overview

```
WEPP run -> hillslope pass files
   -> wepppyo3 swat_utils (recall files + recall.rec + recall.con when connections are provided + manifest)
   -> Python assembly (file.cio/time.sim patch + channel params)
   -> SWAT+ TxtInOut
   -> SWAT+ run + outputs
```

## TxtInOut build strategy

### Recommended approach: template + patch
Use a curated SWAT+ template directory and patch only the pieces WEPPpy owns:
- `recall/` files + `recall.rec` (written by Rust) + `recall.con` (when recall connections are provided)
- `file.cio` entries for recall and connectivity
- `time.sim` start/end alignment
- `print.prt` outputs for verification (optional)
- `channel-lte.cha` / `hyd-sed-lte.cha` when channel overrides are enabled

This avoids re-implementing SWAT+ project assembly and keeps SWAT version drift localized to the template.

### Full TxtInOut generation in Rust (assessment + gotchas)
Using `wepppyo3.swat_utils` to create an entire `TxtInOut` directory is possible but risky. Major gotchas:
- **Template parity**: SWAT+ expects many files to be consistent with each other (object counts, file.cio lists, print.prt objects). Recreating all of them in Rust duplicates SWAT+ template logic.
- **Version drift**: SWAT+ input file schemas change across minor versions. Hard-coding file formats in Rust is high maintenance.
- **Channel inputs**: `channel-lte.cha`, `hyd-sed-lte.cha`, and `chandeg.con` depend on Peridot/WEPPpy-derived geometry and overrides. Python already owns that context.
- **Config coupling**: WEPPcloud config and UI defaults live in Python; duplicating that logic in Rust risks divergence.
- **Error surface**: A single missing file in TxtInOut can make SWAT+ fail with opaque errors; template-based patching is safer and easier to validate.

**Recommendation**: keep Rust focused on recall file generation + manifest. Assemble TxtInOut in Python from a versioned template.

### Rust vs Python output ownership
- Rust (wepppyo3) writes per-hillslope recall files and returns a manifest.
- Rust writes `recall.rec` always and `recall.con` when `recall_connections` are provided; Python supplies the mapping.
- Python patches `file.cio`/`time.sim` and applies channel parameter overrides.

## Recall generation contract (summary)
- Inputs: `wepp/output/H<wepp_id>.pass.dat` files.
- Output: per-hillslope recall daily files (default: `hill_{wepp_id:05d}.rec`) plus `recall.rec` (always) and `recall.con` when recall connections are provided.
- FLO: `runvol + sbrunv + drrunv` (flags control inclusion).
- SED: sum of per-class loads from `sedcon_i * runvol`.
- Class mapping: `CLA, SIL, SAG, LAG, SAN` from WEPP class 1..5; `GRV = 0`.
- All other recall fields are `0` until explicitly supported.

See `wepppyo3/docs/wepp-hill-pass-to-swat-rec-spec.md` for the canonical conversion rules.

## Connectivity construction
- `recall.rec` entries must match the recall filenames.
- `recall.con` must connect each recall object to its immediate downstream channel.
- Channel IDs should be derived from `watershed/channels.parquet` (`chn_enum`).
- Use Peridot `network.txt` to build channel connectivity (SWAT-DEG via `chandeg.con`).
- Provide the `wepp_id -> chn_enum` mapping to `wepp_hillslope_pass_to_swat_recall` as `recall_connections` so Rust can emit `recall.con`.

## MVP channel parameter strategy
For MVP, apply a single set of channel parameters uniformly to all SWAT-DEG channels. Parametric/channel-by-order strategies can be added later once the end-to-end pipeline is stable.

## WEPPcloud integration (reuse `wepp_pure.htm`)

### Control/UI behavior
- Keep `wepp_pure.htm` as the base control; add a SWAT section that renders only when `swat` is in `nodb.mods`.
- Add a toggle in the WEPP control: **Run WEPP watershed** (`wepp.run_wepp_watershed`).
  - `true`: run WEPP watershed as usual and show WEPP channel advanced options.
  - `false`: skip WEPP watershed execution and hide WEPP channel advanced options (`chan.inp`, channel parameters).
- Add a checkbox in the SWAT section: **Use SWAT-DEG channel objects** (checked by default; SWAT-DEG remains canonical for MVP).
- Add SWAT channel override inputs under the SWAT section (mann, fpn, erod_fact, cov_fact, d50).
- Keep WEPP hillslope options (subsurface/tile inclusion) in place; they feed SWAT recall generation.

### Execution flow
- Clicking **Run WEPP** follows the existing WEPP control flow.
- If `swat` is present, enqueue SWAT prep + run after WEPP completes.
- The WEPP watershed run is conditional on `wepp.run_wepp_watershed`.

## Logging and observability
- Log build steps using the NoDb logger (status pipeline to Redis DB 2).
- Store a `build_summary` with counts, dates, and paths.
- Capture errors and store `status = error` with a short message.

## Validation checks
- Recall count matches number of hillslope pass files.
- `recall_day.txt` outputs match generated recall rows.
- `SED == sum(class loads)` within tolerance.
- `time.sim` matches recall date span (start year + NBYR).
- `file.cio` includes recall and connect files.

## Risks and open questions
- Source of channel parameters beyond geometry (roughness, erodibility, cover).
- Which SWAT+ channel object to standardize on (SWAT-DEG vs legacy).
- Recall file scaling for large watersheds (file count, runtime).
- Alignment of SWAT+ and WEPP calendar conventions under non-Gregorian calendars.

## Implementation plan (multi-phase)

### Phase 0: Alignment + scaffolding
- [x] Add `swat-nodb-spec.md` to the mods/swat folder (this doc).
- [x] Bundle SWAT+ binary under `wepppy/nodb/mods/swat/bin` and set `swat_bin` default.
- [x] Bundle SWAT+ templates under `wepppy/nodb/mods/swat/templates` and set `swat_template_dir` default.
- [x] Canonicalize SWAT-DEG channel object set (`channel_sd`, `chandeg.con`, `channel-lte.cha`, `hyd-sed-lte.cha`).

### Phase 1: NoDb module + config plumbing
- [x] Add `wepppy/nodb/mods/swat/__init__.py` with `__all__` exports.
- [x] Add `wepppy/nodb/mods/swat/swat.py` with `Swat(NoDbBase)`.
- [x] Ensure `nodb.mods = ['swat']` enables the mod without UI toggles.
- [x] Add config parsing helpers for the `[swat]` section.
- [x] Move `run_wepp_watershed` to `[wepp]` and wire it through `Wepp` and RQ.

### Phase 2: Recall generation integration
- [x] Add Python wrapper to call `wepppyo3.swat_utils.wepp_hillslope_pass_to_swat_recall`.
- [x] Pass `swat_txtinout_dir`, `recall_connections`, `recall_wst`, and `recall_object_type` so Rust can emit `recall.rec` and `recall.con`.
- [x] Store recall manifest and summary in `swat.nodb`.
- [x] Add a validation helper to compare totals with WEPP hillslope outputs.

### Phase 3: Connectivity + TxtInOut assembly
- [x] Copy template `TxtInOut` into the run `swat/` directory.
- [x] Ensure `recall.rec`, `recall.con`, and `chandeg.con` are generated (Rust for recall files + recall.{rec,con}; Python for channel connectivity).
- [x] Patch `time.sim`, `object.cnt`, and channel parameter files (keep `file.cio` aligned with template defaults).
- [x] Write build logs and a `build_summary` payload.

### Phase 4: Execution hook
- [x] Add an RQ task to run SWAT+ (binary invocation + stdout/stderr capture).
- [x] Persist SWAT+ outputs into `swat/outputs/` with a minimal index.

### Phase 5: UI integration (future)
- [ ] Extend `wepp_pure.htm` with a SWAT section and the **Run WEPP watershed** toggle.
- [ ] Hide WEPP channel advanced options when `wepp.run_wepp_watershed` is `false`.
- [ ] Surface SWAT channel overrides in the SWAT section.
- [ ] Keep SWAT hidden from the mods menu until UX is stable.

### Phase 6: QA + docs
- [ ] Add pytest coverage for config parsing and NoDb state transitions.
- [ ] Add end-to-end smoke fixture for recall + connectivity build (small watershed).
- [ ] Document SWAT output locations and troubleshooting notes.
