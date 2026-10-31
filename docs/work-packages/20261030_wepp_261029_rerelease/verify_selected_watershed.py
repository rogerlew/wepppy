"""Validate actual selected hill/watershed execution and channel Rust readback.

Inputs are staged by the committed native physical_water_case.py generator;
inputs.json records its source and every generated input hash. Run only after
vendoring the accepted revision2 pair, inside the WEPPpy runtime container.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pyarrow.parquet as pq

from wepp_runner.wepp_runner import (
    get_linux_wepp_bin_role_paths, run_hillslope, run_watershed,
)
from wepppy.wepp.interchange.watershed_chnwb_interchange import (
    MEASUREMENT_COLUMNS, run_wepp_watershed_chnwb_interchange,
)
from wepppy.wepp.interchange.watershed_ebe_interchange import (
    run_wepp_watershed_ebe_interchange,
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    root = Path(sys.argv[1])
    runs, output = root / 'runs', root / 'output'
    inputs = json.loads((root / 'inputs.json').read_text())
    assert all(digest(runs / name) == expected for name, expected in inputs['inputs'].items())
    release = 'wepp_261029'
    roles = list(map(Path, get_linux_wepp_bin_role_paths(release)))
    sidecars = [json.loads(Path(str(p)+'.json').read_text()) for p in roles]
    assert all(x['artifact_revision'] == 2 for x in sidecars)
    assert all(digest(p) == x['sha256'] for p, x in zip(roles, sidecars))
    assert not list(output.iterdir()), 'Use freshly staged inputs without prior outputs'
    assert run_hillslope(1, str(runs), wepp_bin=release, timeout=300, timeout_retries=0)
    assert digest(roles[1]) in (runs / 'p1.err').read_text()
    pass_sha = digest(output / 'H1.pass.dat')
    assert run_watershed(str(runs), wepp_bin=release)
    assert digest(roles[0]) in (runs / 'pw0.err').read_text()
    assert pass_sha == digest(output / 'H1.pass.dat')
    raw = []
    for line in (output / 'chnwb.txt').read_text().splitlines():
        fields = line.split()
        if fields and fields[0].isdigit():
            values = list(map(float, fields))
            # Current CHNWB adds five native profile diagnostics; the existing
            # Rust schema deliberately projects the original 22 fields.
            assert len(values) == 27
            raw.append(values)
    native = np.array(raw)
    assert len(native) > 0 and np.isfinite(native).all()
    assert (native[:, 3:] >= 0).all()
    channel = run_wepp_watershed_chnwb_interchange(output, start_year=1980)
    events = run_wepp_watershed_ebe_interchange(output, start_year=1980)
    frame = pq.read_table(channel).to_pandas()
    assert len(frame) == len(native)
    columns = ['OFE', 'J', 'Y'] + [x[0] for x in MEASUREMENT_COLUMNS]
    assert np.array_equal(frame[columns].to_numpy(), native[:, :len(columns)])
    # Calendar validation follows actual CLI years1980–1981, including leap day.
    dates = frame[['year', 'julian']].drop_duplicates()
    expected = {(1980, d) for d in range(1, 367)} | {(1981, d) for d in range(1, 366)}
    assert set(map(tuple, dates.to_numpy())) == expected
    assert not frame.duplicated(['wepp_id', 'year', 'julian']).any()
    event_frame = pq.read_table(events).to_pandas()
    numeric = event_frame.select_dtypes(include='number').to_numpy()
    assert len(event_frame) and np.isfinite(numeric).all()
    for name in ['runoff_volume', 'peak_runoff', 'sediment_yield']:
        assert (event_frame[name] >= 0).all()
    receipt = dict(release=release, artifact_revision=2,
                   binary_sha256={p.name: digest(p) for p in roles},
                   input_receipt_sha256=digest(root / 'inputs.json'),
                   fresh_same_build_pass_sha256=pass_sha,
                   native_output_sha256={p.name: digest(p) for p in output.iterdir() if p.is_file()},
                   channel_rows=len(frame), channel_calendar_days=len(dates),
                   channel_native_projected_parquet_exact=True,
                   native_fields=27, parquet_native_fields=len(columns),
                   native_profile_diagnostics_finite_nonnegative=True,
                   event_rows=len(event_frame),
                   runner_log_sha256={name: digest(runs / name) for name in ['p1.err', 'pw0.err']})
    (root / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
