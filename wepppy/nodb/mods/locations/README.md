# Location Mods (NoDb)

> Location-specific adjustments to land cover and soils during NoDb run preparation.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb operational quirks and testing guidance.

## Overview

This package implements *location mods*: small, location-specific behaviors that run during the NoDb build workflow when specific `TriggerEvents` fire (for example, after landuse domains are computed or after soils are built).

The core mechanism is `LocationMixin` (`location_mixin.py`), which is mixed into `NoDbBase`-backed mods (for example, `GeneralMod` and `LakeTahoe`). These mods are invoked from `NoDbBase.trigger()` based on the run configuration’s `nodb.mods` list.

Note: the bundled location mods in `general/` and `lt/` are currently marked `@deprecated` in code. They remain useful as reference implementations of the mixin pattern and as legacy behaviors where still enabled in configs.

## Architecture

### `LocationMixin`

`LocationMixin` provides reusable, location-aware helpers that operate on core NoDb controllers:

- **Inputs/assumptions from the host class**
  - `self.wd`: working directory for the run (provided by `NoDbBase`)
  - `self.data_dir`: directory containing location-specific lookup data files
  - `self.lc_lookup_fn`: CSV filename used by `read_lc_file(...)`
  - `self.default_wepp_type`: default WEPP soil “type” string when a mukey is not mapped
- **Controllers touched**
  - `Landuse.getInstance(self.wd)` (mutates `Landuse.domlc_d`)
  - `Soils.getInstance(self.wd)` (mutates `Soils.domsoil_d` and `Soils.soils`)
  - `Watershed.getInstance(self.wd)` (used for area-based recalculation)

Key behaviors:

- `location_doms`: reads the landcover/soil lookup CSV (via `read_lc_file(...)`) and returns the set of land cover IDs (`LndcvrID`) supported by the location.
- `remap_landuse()`: remaps `Landuse.domlc_d` for any hillslope whose land cover domain is *not* supported by the location. The remapping table is read from `data/landcover_map.json`.
- `modify_soils(default_wepp_type=None, lc_lookup_fn=None)`:
  - reads replacement parameters from the landcover/soil lookup CSV and soil-type mapping from `data/lc_soiltype_map.json`
  - for each hillslope (`topaz_id`), chooses a `wepp_type` based on the mukey mapping (falling back to `default_wepp_type`)
  - writes a derived `.sol` file (via `WeppSoilUtil(...).to_7778disturbed(...)`) into the run’s soils directory and updates `Soils.domsoil_d` to point at the derived soil key
  - recomputes each derived soil’s area and percent coverage using `Watershed.hillslope_area(...)` and `Watershed.wsarea`
  - special-cases “water” soils (`soil_is_water(...)`) by forcing the hillslope to retain the original mukey and setting its in-memory area to `0.0`

### Location mod classes (`general/`, `lt/`)

Each location mod is a small `NoDbBase` subclass that:

1. stores per-location settings (`data_dir`, `lc_lookup_fn`, `default_wepp_type`, and any extras)
2. responds to specific `TriggerEvents` by calling mixin methods

Current modules:

- `general/general.py`: `GeneralMod` (deprecated)
  - on `TriggerEvents.LANDUSE_DOMLC_COMPLETE`: calls `remap_landuse()`
  - on `TriggerEvents.SOILS_BUILD_COMPLETE`: calls `modify_soils()` and then `modify_soils_kslast()`
  - `modify_soils_kslast()` writes per-hillslope soil variants with a configured `kslast` value (via `wepppy.wepp.soils.utils.modify_kslast`) and updates `Soils.domsoil_d`
- `lt/lt.py`: `LakeTahoe` (deprecated; “Use Disturbed instead”)
  - on `TriggerEvents.LANDUSE_DOMLC_COMPLETE`: calls `remap_landuse()`
  - on `TriggerEvents.SOILS_BUILD_COMPLETE`: calls `modify_soils()`

Both mods keep their lookup data under their package `data/` directories (for example, `general/data/` and `lt/data/`).

### How location mods are invoked

`NoDbBase.trigger(evt)` explicitly checks the configured `mods` list and invokes the corresponding mod’s `.on(evt)` method.

For location mods:

- if `'lt'` is present, it instantiates `wepppy.nodb.mods.locations.LakeTahoe` and calls `lt.on(evt)`
- if `'general'` is present, it instantiates `wepppy.nodb.mods.locations.GeneralMod` and calls `general.on(evt)`

This wiring is currently manual (a TODO in `NoDbBase.trigger()` notes a future reflection-based refactor).

## Quick Start / Examples

### Enable an existing location mod

Location mods are selected by name via the NoDb config. The `mods` value is parsed via `ast.literal_eval`, so it is typically stored as a Python-literal list in the config file:

```ini
[nodb]
mods = "['general']"
```

Once enabled, the mod will run automatically when `NoDbBase.trigger(...)` fires the relevant events during the build pipeline.

### Write a new location mod using `LocationMixin`

Create a new package under `wepppy/nodb/mods/locations/<my_location>/` with a `data/` directory containing:

- `landcover_map.json` (remaps unsupported land cover IDs)
- `lc_soiltype_map.json` (maps mukey → WEPP type)
- your lookup CSV (commonly `landSoilLookup.csv`)

Then implement a small `NoDbBase` + `LocationMixin` class:

```python
import os
from os.path import join as _join

from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter
from wepppy.nodb.mods.locations.location_mixin import LocationMixin

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, "data")


class MyLocation(NoDbBase, LocationMixin):
    __name__ = "MyLocation"
    filename = "my_location.nodb"

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)
        with self.locked():
            self._data_dir = _data_dir
            self._lc_lookup_fn = "landSoilLookup.csv"
            self._default_wepp_type = "MyDefaultWeppType"

    def on(self, evt: TriggerEvents):
        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()

    @property
    def data_dir(self):
        return self._data_dir

    @property
    def lc_lookup_fn(self):
        return self._lc_lookup_fn

    @lc_lookup_fn.setter
    @nodb_setter
    def lc_lookup_fn(self, value):
        self._lc_lookup_fn = value

    @property
    def default_wepp_type(self):
        return self._default_wepp_type

    @default_wepp_type.setter
    @nodb_setter
    def default_wepp_type(self, value):
        self._default_wepp_type = value
```

To make the mod runnable, it must also be wired into the trigger path (today this is done by adding an import + `if '<name>' in self.mods:` block in `NoDbBase.trigger()`), and it must be enabled via `nodb.mods` in the run config.

### Override lookup inputs at runtime

`LocationMixin.modify_soils(...)` accepts optional parameters, which can be useful in experiments or one-off workflows:

```python
mod.modify_soils(default_wepp_type="Granitic", lc_lookup_fn="my_lookup.csv")
```

## Developer Notes

- `LocationMixin` mutates other controllers (`Landuse`, `Soils`) under their own `.locked()` contexts; avoid holding additional unrelated locks while calling into it unless you have a specific reason.
- `modify_soils(...)` writes derived `.sol` files into the run’s soils directory and updates in-memory soil catalog entries (`Soils.soils`). If you are debugging unexpected soil keys, start by checking `Soils.domsoil_d` and the soils directory contents.
- The legacy location mods in this package are deprecated in code; prefer newer, non-deprecated mods (for example, `wepppy.nodb.mods.disturbed`) where available, but keep these as references for the mixin-driven pattern.

## Further Reading

- `wepppy/nodb/base.py`: `NoDbBase.trigger(...)` and `TriggerEvents`
- `wepppy/nodb/core/`: `Landuse`, `Soils`, `Watershed`
- `wepppy/wepp/soils/utils.py`: `read_lc_file(...)`, `soil_is_water(...)`, `WeppSoilUtil`
