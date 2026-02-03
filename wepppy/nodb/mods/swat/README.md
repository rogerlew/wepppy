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
- `print.prt` is managed via `Swat.print_prt` (template-seeded `PrintPrtConfig`) and rendered during build; defaults enable daily `basin_wb`, `channel_sd`, and `hyd` with `recall` off unless explicitly enabled.
- Outputs are archived under `swat/outputs/run_<timestamp>/` with an `index.json` summary.
- When `swat_interchange_enabled=true`, SWAT output files are converted to Parquet in `swat/outputs/run_<timestamp>/interchange/` and the summary is added to `index.json` as `interchange_summary`.
- SWAT-DEG (`channel_sd`, `chandeg.con`, `channel-lte.cha`, `hyd-sed-lte.cha`) is canonical.
