# WEPP Interchange Fixtures

The interchange suite validates the required `wepppyo3.wepp_interchange`
implementation through WEPPpy's public facades. It does not maintain a Python
parser baseline.

## Fixtures

The small general fixture is:

```text
/workdir/wepppy/tests/wepp/interchange/test_project/output
```

The compact all-format fixture is assembled from `test_project/output` and:

```text
/workdir/wepppy/tests/wepp/interchange/fixtures/decimal-pleasing/wepp/output
```

An optional large local fixture may be selected with
`WEPPPY_INTERCHANGE_FIXTURE`; large fixtures are not committed.

## Test Commands

Run the focused suite through the canonical wrapper:

```bash
wctl run-pytest tests/wepp/interchange
```

The suite covers all public hillslope and watershed formats, schema metadata,
calendar behavior, native catalog scanning, one-row-group-per-hillslope-source,
missing native symbols, propagated native failures, and atomic target
non-publication.

Run the release package's native API tests from the WEPPpyo3 repository:

```bash
PYTHONPATH=release/linux/py312 \
  /home/workdir/wepppy/.venv/bin/pytest -q tests/wepp_interchange
```

## Manual Facade Smoke

Use a copied run directory; interchange generation writes or replaces files
under `output/interchange/`. Copy the run's `climate/wepp_cli.parquet` with the
output tree, or pass the correct `start_year`; simulation-year dates such as
February 29 cannot be resolved faithfully without one of those calendar inputs.

```bash
wctl exec weppcloud bash -lc 'cd /workdir/wepppy && /opt/venv/bin/python - <<"PY"
from pathlib import Path

from wepppy.wepp.interchange.hill_interchange import (
    run_wepp_hillslope_interchange,
)
from wepppy.wepp.interchange.watershed_interchange import (
    run_wepp_watershed_interchange,
)

output = Path("/tmp/copied-run/wepp/output")
run_wepp_hillslope_interchange(output)
run_wepp_watershed_interchange(output)
PY'
```

If the paired extension is missing, incomplete, or fails, the facade raises a
`WeppInterchangeNativeError` subtype with the original failure chained as its
cause. That is the expected deployment contract.
