"""Exercise installed release discovery, runner selection and real Rust readers.

Run inside the WEPPpy container with the committed native fixture archive and
a new scratch directory as the two positional arguments. No project is mutated.
"""
import calendar
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import pyarrow.parquet as pq

from wepp_runner.wepp_runner import (
    get_linux_wepp_bin_opts, get_linux_wepp_bin_role_paths,
    infer_pass_family_for_wepp_bin, run_hillslope,
)
from wepp_runner.wepp_binary_capabilities import get_binary_capabilities
from wepppy.wepp.interchange.hill_element_interchange import run_wepp_hillslope_element_interchange
from wepppy.wepp.interchange.hill_wat_interchange import run_wepp_hillslope_wat_interchange


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    archive_path, root = map(Path, sys.argv[1:])
    assert digest(archive_path) == '64eb68c9a408b36abd5658aea68a039014620f7340236b0aa518b9e4a72677fc'
    release = 'wepp_261029'
    assert release in get_linux_wepp_bin_opts()
    assert get_binary_capabilities(release) == dict(mofe_supported=True, single_user_defined_inputs_supported=True)
    assert infer_pass_family_for_wepp_bin(release) == 'legacy_ascii'
    roles = get_linux_wepp_bin_role_paths(release)
    assert [Path(p).name for p in roles] == [release, release + '_hill']
    root.mkdir(parents=True, exist_ok=False)
    runs, output = root / 'runs', root / 'output'
    runs.mkdir()
    output.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assert set(archive.namelist()) == set(manifest['inputs']) | {'manifest.json'}
        for name, expected in manifest['inputs'].items():
            assert Path(name).name == name and name not in ('.', '..')
            data = archive.read(name)
            assert hashlib.sha256(data).hexdigest() == expected
            (runs / name).write_bytes(data)
    assert run_hillslope(1, str(runs), wepp_bin=release, timeout=300, timeout_retries=0)
    log = (runs / 'p1.err').read_text()
    assert digest(roles[1]) in log and str(roles[1]) in log
    keys = []
    for line in (output / 'H1.wat.dat').read_text().splitlines():
        fields = line.split()
        if fields and fields[0].isdigit():
            row = np.array(list(map(float, fields)))
            assert len(row) == 25 and np.isfinite(row).all() and (row[3:] >= 0).all()
            keys.append(tuple(map(int, row[:3])))
    expected = {(ofe, day, year) for year in range(1, 17)
                for day in range(1, 366 + calendar.isleap(year)) for ofe in (1, 2, 3)}
    assert len(keys) == len(expected) and set(keys) == expected
    native_hashes = {p.name: digest(p) for p in output.iterdir() if p.is_file()}
    element = run_wepp_hillslope_element_interchange(output, expected_hillslopes=1)
    water = run_wepp_hillslope_wat_interchange(output, expected_hillslopes=1)
    # ELEMENT records selected events; WAT records every element/day.
    element_rows = sum(bool(line.split()) for line in
                       (output / 'H1.element.dat').read_text().splitlines()[2:])
    counts = {}
    for path in (element, water):
        frame = pq.read_table(path).to_pandas()
        counts[path.name] = len(frame)
        assert len(frame) == (element_rows if path == element else len(expected))
        if path == water:
            # This 25-column producer does not emit the reader's optional
            # interception-storage field. Preserve unknown as null, never zero.
            assert frame['InterceptionStorage'].isna().all()
            frame = frame.drop(columns=['InterceptionStorage'])
        assert np.isfinite(frame.select_dtypes(include='floating').to_numpy()).all()
    receipt = dict(release=release, binary_sha256={Path(p).name: digest(p) for p in roles},
                   fixture_source_commit='631aed1d1c89ed8fa76c5dc3f2e4258a8f199504',
                   fixture_sha256=digest(archive_path), native_output_sha256=native_hashes,
                   complete_water_rows=len(keys), parquet_rows=counts,
                   absent_optional_water_columns=['InterceptionStorage'],
                   runner_log_sha256=digest(runs / 'p1.err'))
    (root / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
