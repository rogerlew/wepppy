# Python Comparator Discovery (2026-04-27)

## Summary

- `confirmed`: The legacy WEPPpy Python comparator implementation is `wepppy/topo/watershed_abstraction/watershed_abstraction.py::WatershedAbstraction`.
- `confirmed`: The NoDb orchestration wrapper is `wepppy/nodb/core/watershed.py::_topaz_abstract_watershed`, reached from `wepppy/nodb/core/watershed_mixins.py::abstract_watershed` only when `abstraction_backend != "peridot"` and the delineation backend is TOPAZ.
- `confirmed`: The lower-level runnable comparator surface is `WatershedAbstraction(topaz_wd, wat_dir)`, followed by `abstract(...)` and slope writers. This avoids mutating persisted NoDb state while exercising the stale Python abstraction code.
- `confirmed`: The Python comparator failed on the copied in-repo fixture before full output generation.
- `inference`: The NoDb wrapper would hit the same failure because `_topaz_abstract_watershed()` delegates channel and subcatchment work to the same `WatershedAbstraction` methods.

## Invocation Requirements

The lower-level Python comparator requires an existing TOPAZ working directory and an existing watershed output directory:

```text
topaz_wd = <isolated-run>/dem/topaz
wat_dir = <isolated-run>/watershed
```

Required input files confirmed from constructor and smoke execution:

- `BOUND.ARC`
- `FLOPAT.ARC`
- `FLOVEC.ARC`
- `FVSLOP.ARC`
- `SUBWTA.ARC`
- `RELIEF.ARC`
- `TASPEC.ARC`
- `DNMCNT.INP`
- `NETW.TAB` is required later by `abstract_structure()`.

Smoke command used:

```bash
/usr/bin/time -v .venv/bin/python - <<'PY'
from pathlib import Path
from wepppy.topo.watershed_abstraction.watershed_abstraction import WatershedAbstraction
wd = Path('/tmp/peridot-python-benchmark-20260427-0138/python-smoke-fail')
absw = WatershedAbstraction(str(wd / 'dem' / 'topaz'), str(wd / 'watershed'))
absw.abstract(clip_hillslopes=False, verbose=False)
absw.write_slps(channels=1, subcatchments=0, flowpaths=1)
PY
```

## Failure Signature

`confirmed`: Exit status was `1`. The traceback is:

```text
File "/home/workdir/wepppy/wepppy/topo/watershed_abstraction/watershed_abstraction.py", line 792, in abstract_flowpath
  distance_p = cummnorm_distance(distance)
File "/home/workdir/wepppy/wepppy/topo/watershed_abstraction/support.py", line 84, in cummnorm_distance
  distance_p /= distance_p[-1]
numpy.core._exceptions._UFuncOutputCastingError: Cannot cast ufunc 'divide' output from dtype('float64') to dtype('int64') with casting rule 'same_kind'
```

`confirmed`: The comparator produced only partial native output before failure: six `hill_*.slp` files in `/tmp/peridot-python-benchmark-20260427-0138/python-smoke-fail/watershed/`.

## Peridot Comparator Discovery

`confirmed`: The comparable TOPAZ Peridot command is:

```bash
./wepppy/topo/peridot/bin/abstract_watershed <isolated-run> --ncpu 4
```

`confirmed`: The WEPPpy vendored binary reports:

```text
peridot 0.1.0 (built 2026-04-22T19:27:24.335709839-07:00)
```

`confirmed`: `/home/workdir/peridot` is at commit `e09f54c6f729192320e0e14a972d927f996aec9b`, and its local `target/release/abstract_watershed` binary is dirty and has a different SHA256 from the vendored WEPPpy binary. It was not staged or used for the smoke comparison.

## Remediation Follow-Up

`confirmed`: The package cannot produce valid Python-vs-Peridot timing claims because the Python comparator does not complete.

`inference`: A scoped comparator-remediation package should start at `wepppy/topo/watershed_abstraction/support.py::cummnorm_distance()` and validate that distance arrays are normalized as floating point before in-place division. The remediation package should include a regression test that reproduces this fixture failure without changing benchmark scope.

`hypothesis`: After that narrow fix, the next likely compatibility gap may be native output parity, because the Python path historically writes slope files and NoDb summary state while Peridot writes parquet tables and structured slope bundles.
