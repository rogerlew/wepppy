# Fixture Selection (2026-04-27)

## Selected Fixture

- `confirmed`: The benchmark used the in-repo fixture at `/workdir/wepppy/wepppy/_tests/feverish-lamp/`.
- `confirmed`: The selected TOPAZ inputs are under `/workdir/wepppy/wepppy/_tests/feverish-lamp/dem/topaz/`.
- `confirmed`: Production-derived run roots were not used for benchmark execution.

## Isolated Workspace

The source fixture was copied into an isolated scratch workspace:

```text
/tmp/peridot-python-benchmark-20260427-0138/
```

Comparator-specific copies were created under:

- `/tmp/peridot-python-benchmark-20260427-0138/python-smoke-fail/`
- `/tmp/peridot-python-benchmark-20260427-0138/peridot-smoke-log/`

`confirmed`: Commands were run only against these copied directories. The source fixture and canonical run roots under `/wc1/runs`, `/geodata/weppcloud_runs`, and `/geodata/wc1` were not mutated.

## Copied Inputs

The copied TOPAZ fixture contained the required comparator inputs:

```text
BOUND.ARC
BOUND.PRJ
CHNJNT.ARC
CHNJNT.PRJ
DNMCNT.INP
FLOPAT.ARC
FLOPAT.PRJ
FLOVEC.ARC
FLOVEC.PRJ
FVSLOP.ARC
FVSLOP.PRJ
NETFUL.ARC
NETFUL.PRJ
NETW.ARC
NETW.PRJ
NETW.TAB
NETWE.OUT
RELIEF.ARC
RELIEF.PRJ
SUBWTA.ARC
SUBWTA.PRJ
TASPEC.ARC
TASPEC.PRJ
```

## Fixture Size Summary

`confirmed`: The source run fixture size is about `13M`.

`confirmed`: Raster characteristics from the copied TOPAZ files:

| File | Shape | Nonzero Cells | Unique Values | Min | Max | Cell Size |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `BOUND.ARC` | `153 x 152` | `650` | `2` | `0` | `1` | `30.0` |
| `SUBWTA.ARC` | `153 x 152` | `650` | `12` | `0` | `44` | `30.0` |
| `FLOPAT.ARC` | `153 x 152` | `23256` | `3` | `1` | `4` | `30.0` |
| `FLOVEC.ARC` | `153 x 152` | `23256` | `8` | `1` | `9` | `30.0` |
| `FVSLOP.ARC` | `153 x 152` | `23236` | `519` | `-1.0` | `0.9051` | `30.0` |
| `RELIEF.ARC` | `153 x 152` | `23256` | `5620` | `841.4` | `1519.2` | `30.0` |
| `TASPEC.ARC` | `153 x 152` | `23125` | `360` | `0.0` | `359.0` | `30.0` |

`confirmed`: TOPAZ ID coverage in `SUBWTA.ARC`:

- All nonzero IDs: `22, 23, 24, 31, 32, 33, 34, 41, 42, 43, 44`
- Hillslope IDs: `22, 23, 31, 32, 33, 41, 42, 43`
- Channel IDs: `24, 34, 44`

## Fixture Decision

`confirmed`: This in-repo fixture is adequate for comparator health discovery and Peridot smoke testing.

`inference`: It is not adequate for representative performance claims because the Python comparator fails before parity can be established, and the fixture is a small smoke workload.

`hypothesis`: A future benchmark package may need one or more curated fixtures that include both legacy Python-compatible TOPAZ inputs and current Peridot table-output expectations.
