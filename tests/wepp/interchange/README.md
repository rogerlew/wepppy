# WEPP Interchange Fixtures
> Terse notes for running the interchange modules against local fixtures.

## Fixture Output Paths
Default (small) fixture used by the interchange tests:
`/workdir/wepppy/tests/wepp/interchange/test_project/output`

Large fixture for parity/perf checks (not in git):
`/workdir/wepppy/tests/wepp/interchange/fixtures/deductive-futurist/wepp/output`

To point tests at the large fixture:
```bash
WEPPPY_INTERCHANGE_FIXTURE=tests/wepp/interchange/fixtures/deductive-futurist/wepp/output
```

## Test Runs
Default suite:
```bash
./wctl/wctl.sh exec weppcloud bash -lc \
  "cd /workdir/wepppy && /opt/venv/bin/pytest tests/wepp/interchange"
```

## Rust Parity Tests (dev-only)
```bash
WEPPPY_RUST_INTERCHANGE_TESTS=1 ./wctl/wctl.sh exec weppcloud bash -lc \
  "cd /workdir/wepppy && /opt/venv/bin/pytest tests/wepp/interchange/test_watershed_interchange_rust_parity.py"
```

With the large fixture:
```bash
WEPPPY_INTERCHANGE_FIXTURE=tests/wepp/interchange/fixtures/deductive-futurist/wepp/output \
WEPPPY_RUST_INTERCHANGE_TESTS=1 ./wctl/wctl.sh exec weppcloud bash -lc \
  "cd /workdir/wepppy && /opt/venv/bin/pytest tests/wepp/interchange/test_watershed_interchange_rust_parity.py"
```

## Schema Snapshot Generation
```bash
./wctl/wctl.sh exec weppcloud bash -lc \
  "cd /workdir/wepppy && /opt/venv/bin/python -m tests.wepp.interchange.schema_snapshot"
```

## Manual Module Run
```bash
./wctl/wctl.sh exec weppcloud bash -lc "cd /workdir/wepppy && /opt/venv/bin/python - <<'PY'
from pathlib import Path
from wepppy.wepp.interchange.watershed_pass_interchange import run_wepp_watershed_pass_interchange
from wepppy.wepp.interchange.watershed_soil_interchange import run_wepp_watershed_soil_interchange
from wepppy.wepp.interchange.watershed_loss_interchange import run_wepp_watershed_loss_interchange
from wepppy.wepp.interchange.watershed_chan_peak_interchange import run_wepp_watershed_chan_peak_interchange
from wepppy.wepp.interchange.watershed_ebe_interchange import run_wepp_watershed_ebe_interchange
from wepppy.wepp.interchange.watershed_chanwb_interchange import run_wepp_watershed_chanwb_interchange
from wepppy.wepp.interchange.watershed_chnwb_interchange import run_wepp_watershed_chnwb_interchange
from wepppy.wepp.interchange.hill_pass_interchange import run_wepp_hillslope_pass_interchange
from wepppy.wepp.interchange.hill_ebe_interchange import run_wepp_hillslope_ebe_interchange
from wepppy.wepp.interchange.hill_element_interchange import run_wepp_hillslope_element_interchange
from wepppy.wepp.interchange.hill_loss_interchange import run_wepp_hillslope_loss_interchange
from wepppy.wepp.interchange.hill_soil_interchange import run_wepp_hillslope_soil_interchange
from wepppy.wepp.interchange.hill_wat_interchange import run_wepp_hillslope_wat_interchange

output_dir = Path('/workdir/wepppy/tests/wepp/interchange/fixtures/deductive-futurist/wepp/output')
run_wepp_watershed_pass_interchange(output_dir)
run_wepp_watershed_soil_interchange(output_dir)
run_wepp_watershed_loss_interchange(output_dir)
run_wepp_watershed_chan_peak_interchange(output_dir)
run_wepp_watershed_ebe_interchange(output_dir)
run_wepp_watershed_chanwb_interchange(output_dir)
run_wepp_watershed_chnwb_interchange(output_dir)
run_wepp_hillslope_pass_interchange(output_dir)
run_wepp_hillslope_ebe_interchange(output_dir)
run_wepp_hillslope_element_interchange(output_dir)
run_wepp_hillslope_loss_interchange(output_dir)
run_wepp_hillslope_soil_interchange(output_dir)
run_wepp_hillslope_wat_interchange(output_dir)
PY"
```

## Manual Perf Check (deductive-futurist)
```bash
./wctl/wctl.sh exec weppcloud bash -lc "cd /workdir/wepppy && /usr/bin/time -v /opt/venv/bin/python - <<'PY'
from pathlib import Path
from wepppy.wepp.interchange.watershed_pass_interchange import (
    _run_wepp_watershed_pass_interchange_python,
    run_wepp_watershed_pass_interchange,
)

output_dir = Path('/workdir/wepppy/tests/wepp/interchange/fixtures/deductive-futurist/wepp/output')

# Python baseline
_run_wepp_watershed_pass_interchange_python(output_dir)

# Rust path (default)
run_wepp_watershed_pass_interchange(output_dir)
PY"
```
