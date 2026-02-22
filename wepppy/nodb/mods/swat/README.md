# SWAT NoDb Mod
> SWAT+ routing integration for WEPP hillslope outputs (config-only module).
> **See also:** `wepppy/nodb/mods/swat/swat-nodb-spec.md` for the contract and `wepppy/nodb/mods/swat/wepp-swat-spec.md` for IO mapping.

## Overview
This module wires SWAT+ recall inputs and routing connectivity onto WEPP hillslope pass outputs. It is enabled only through the run config (`nodb.mods` includes `swat`) and is not exposed in the mods menu.

## Quick start
Add a SWAT section to your run config and include `swat` in the mods list:

```ini
[nodb]
mods = ["disturbed", "swat"]

[swat]
enabled = true
swat_bin = wepppy/nodb/mods/swat/bin/swatplus-61.0.2.61-17-g834fad2-gnu-lin_x86_64
swat_template_dir = wepppy/nodb/mods/swat/templates/ref_1hru
swat_interchange_enabled = true

[wepp]
run_wepp_watershed = true
```

## Developer notes
- Build/run logic is implemented in `Swat.build_inputs()` and `Swat.run_swat()`.
- Internal code layout:
  - `swat.py`: facade/controller entrypoints (`build_inputs`, `run_swat`, interchange orchestration, config/state wiring).
  - `swat_txtinout_mixin.py`: TxtInOut preparation plus climate/recall file normalization helpers.
  - `swat_recall_mixin.py`: recall conversion/alignment and `time.sim`/object-count patching helpers.
  - `swat_connectivity_mixin.py`: channel loading and SWAT-DEG connectivity writers.
  - `_helpers.py`: shared internal utility helpers.
- `print.prt` is managed via `Swat.print_prt` (template-seeded `PrintPrtConfig`) and rendered during build; defaults enable daily `basin_wb`, `channel_sd`, and `hyd` with `recall` off unless explicitly enabled.
- Outputs are archived under `swat/outputs/run_<timestamp>/` with an `index.json` summary.
- When `swat_interchange_enabled=true`, SWAT output files are converted to Parquet in `swat/outputs/run_<timestamp>/interchange/` and the summary is added to `index.json` as `interchange_summary`.
- SWAT-DEG (`channel_sd`, `chandeg.con`, `channel-lte.cha`, `hyd-sed-lte.cha`) is canonical.

### SWAT interchange configuration
```ini
[swat]
swat_interchange_enabled = true
swat_interchange_chunk_rows = 100000
swat_interchange_compression = snappy
swat_interchange_ncpu =
swat_interchange_write_manifest = true
swat_interchange_delete_manifest = false
swat_interchange_delete_after_interchange = false
swat_interchange_dry_run = false
swat_interchange_fail_fast = false
swat_interchange_overwrite = false
swat_interchange_stale_after_hours =
swat_interchange_include = []
swat_interchange_exclude = []

[interchange]
delete_after_interchange = false
```

State fields stored in `swat.nodb`:
- `swat_interchange_summary`
- `swat_interchange_status`
- `last_swat_interchange_at`
