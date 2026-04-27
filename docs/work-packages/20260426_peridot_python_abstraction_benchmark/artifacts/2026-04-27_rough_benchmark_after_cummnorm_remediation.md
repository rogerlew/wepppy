# Rough Benchmark After `cummnorm_distance()` Remediation (2026-04-27)

## Scope

`confirmed`: This post-close addendum follows the user request to remediate the legacy Python `cummnorm_distance()` failure and collect rough benchmark numbers.

`confirmed`: Exact output parity is not required for these rough numbers. The benchmark still records output-shape differences and must not be used as a publication-grade parity or performance claim.

`confirmed`: Code remediation in this addendum:

- `wepppy/topo/watershed_abstraction/support.py::cummnorm_distance()` now normalizes a `float64` cumulative-distance array so integer distance inputs do not fail under NumPy in-place casting rules.
- `wepppy/topo/watershed_abstraction/watershed_abstraction.py::transform_px_to_wgs()` now returns GeoJSON-compatible coordinate lists instead of NumPy arrays, allowing the legacy channel-path GeoJSON writer to complete.

## Fixture and Environment

`confirmed`: Fixture source remained the in-repo TOPAZ fixture:

```text
/workdir/wepppy/wepppy/_tests/feverish-lamp/dem/topaz/
```

`confirmed`: Each repetition used a fresh copied fixture under:

```text
/tmp/peridot-python-benchmark-rough-20260427-0145/runs/
```

`confirmed`: Source fixture directories and canonical run roots were not mutated.

`confirmed`: Host context:

- WEPPpy commit at measurement time: `392201222ec4b2ace01d4171d1e30d24a8000239` with local working-tree edits from this remediation and package documentation.
- Peridot source repo commit: `e09f54c6f729192320e0e14a972d927f996aec9b`.
- CPU setting: Python `WEPPPY_NCPU=24`; Peridot `--ncpu 24`.
- WEPPpy vendored Peridot binary: `./wepppy/topo/peridot/bin/abstract_watershed`.

## Commands

Python comparator timed path:

```bash
WEPPPY_NCPU=24 /usr/bin/time -v .venv/bin/python - <<'PY'
from pathlib import Path
from wepppy.topo.watershed_abstraction.watershed_abstraction import WatershedAbstraction
wd = Path('<fresh-copied-run>')
absw = WatershedAbstraction(str(wd / 'dem' / 'topaz'), str(wd / 'watershed'))
absw.abstract(clip_hillslopes=False, verbose=False)
absw.write_slps(channels=1, subcatchments=0, flowpaths=1)
absw.write_channels_geojson(str(wd / 'dem' / 'topaz' / 'channel_paths.wgs.json'))
PY
```

Peridot comparator timed path:

```bash
/usr/bin/time -v ./wepppy/topo/peridot/bin/abstract_watershed <fresh-copied-run> --ncpu 24
```

## Smoke Output Shape

`confirmed`: Python repetition 1 produced:

- `8` hillslopes.
- `3` channels.
- `36` Python flowpath groups.
- `48` root-level `.slp` files under `watershed/`.
- `dem/topaz/channel_paths.wgs.json`.

`confirmed`: Peridot repetition 1 produced:

- `hillslopes.parquet`: `8` rows, topaz IDs `22, 23, 31, 32, 33, 41, 42, 43`.
- `channels.parquet`: `3` rows, topaz IDs `24, 34, 44`.
- `flowpaths.parquet`: `614` rows with parent topaz IDs `22, 23, 31, 32, 33, 41, 42, 43`.
- `watershed/network.txt`: `24|34,24,44`.
- Current Peridot slope bundle layout under `watershed/slope_files/`.

`inference`: These outputs are adequate for rough timing because both paths completed on the same TOPAZ inputs. They are not exact parity evidence because Python and Peridot represent flowpaths and slope outputs differently.

## Raw Results

| Comparator | Rep | Exit | Wall Time (s) | Max RSS (KB) |
| --- | ---: | ---: | ---: | ---: |
| Peridot | 1 | 0 | 0.170 | 63360 |
| Peridot | 2 | 0 | 0.160 | 63744 |
| Peridot | 3 | 0 | 0.160 | 62592 |
| Peridot | 4 | 0 | 0.160 | 64512 |
| Peridot | 5 | 0 | 0.160 | 63744 |
| Python | 1 | 0 | 2.330 | 262004 |
| Python | 2 | 0 | 2.370 | 263000 |
| Python | 3 | 0 | 2.400 | 262472 |
| Python | 4 | 0 | 2.300 | 262060 |
| Python | 5 | 0 | 2.440 | 261464 |

## Summary

| Comparator | Runs | Mean Wall Time (s) | Min (s) | Max (s) | Std Dev (s) | Mean Max RSS (KB) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Peridot | 5 | 0.162 | 0.160 | 0.170 | 0.004 | 63590 |
| Python | 5 | 2.368 | 2.300 | 2.440 | 0.055 | 262200 |

`confirmed`: On this small smoke fixture and these command paths, Peridot mean wall time was about `14.6x` faster than the remediated Python comparator (`2.368 / 0.162`).

`confirmed`: On this small smoke fixture and these command paths, Peridot mean max RSS was about `24%` of the Python comparator mean max RSS (`63590 / 262200`).

`inference`: The difference is large enough to justify a broader benchmark package after comparator and fixture cleanup.

`hypothesis`: Larger representative fixtures may show different ratios because this fixture is tiny and process startup, multiprocessing overhead, and output-format differences are material.

## Validation

`confirmed`: Targeted remediation tests passed:

```text
wctl run-pytest tests/topo/test_watershed_abstraction_support.py
2 passed, 2 warnings
```

`confirmed`: Both benchmark command families exited `0` for all five repetitions.

`confirmed`: This artifact does not assert exact schema, table, row, flowpath, or slope-file parity.
