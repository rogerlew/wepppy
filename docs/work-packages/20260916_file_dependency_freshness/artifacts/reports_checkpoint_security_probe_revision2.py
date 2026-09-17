"""Disposable report dependency/native boundary characterization; no named runs."""
import hashlib
import json
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory

import pandas as pd

from wepppy.wepp.interchange._rust_interchange import require_wepppyo3_interchange
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport


def write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(path, index=False)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catalog_aliases(root):
    sources = [root / name for name in (
        'wepp/output/interchange/loss_pw0.hill.parquet',
        'watershed/hillslopes.parquet', 'landuse/landuse.parquet')]
    write(sources[0], [{'WeppID': 1, 'Runoff Volume': 100., 'Subrunoff Volume': 20.,
        'Baseflow Volume': 10., 'Soil Loss': 5., 'Sediment Yield': 3.,
        'Sediment Deposition': 2.}])
    write(sources[1], [{'WeppID': 1, 'TopazID': 101, 'area': 1000.}])
    write(sources[2], [{'TopazID': 101, 'key': 100, 'desc': 'Forest'}])
    report = AverageAnnualsByLanduseReport(root)
    before = [dict(row.row) for row in report]
    hashes = [digest(path) for path in sources]
    catalog_path = root / '_query_engine/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    for entry in catalog['files']:
        if entry['path'] == 'wepp/output/interchange/loss_pw0.hill.parquet':
            entry['schema'] = None
    catalog_path.write_text(json.dumps(catalog))
    cached = [dict(row.row) for row in AverageAnnualsByLanduseReport(root)]
    try:
        report._build_dataframe()
    except Exception as error:
        failure = {'type': type(error).__name__, 'message': str(error)}
    else:
        raise AssertionError('Expected missing catalog alias to affect the actual query')
    assert hashes == [digest(path) for path in sources]
    assert before == cached
    assert 'wepp_id' in failure['message']
    return {'source_hashes_unchanged': True, 'selected_paths_unchanged': True,
            'catalog_change': 'loss schema set to supported optional None',
            'cached_rows': cached, 'actual_query_failure': failure}


def native_destination(root):
    source = root / 'H.wat.parquet'
    write(source, [{'wepp_id': 1, 'ofe_id': 1, 'water_year': 2001,
        'P': 1., 'Dp': .5, 'QOFE': .2, 'latqcc': .1, 'Ep': .05,
        'Es': .03, 'Er': .02, 'Area': 1000.}])
    native = require_wepppyo3_interchange('security characterization',
                                        'hillslope_watbal_to_parquet')
    target = root / 'prior.parquet'
    target.write_bytes(b'prior canonical bytes')
    alias = root / 'summary.parquet'
    alias.symlink_to(target.name)
    try:
        native.hillslope_watbal_to_parquet(str(source), str(alias), {1: 101})
    except OSError as error:
        symlink_failure = type(error).__name__
    else:
        raise AssertionError('Native canonical symlink guard did not reject')
    assert alias.is_symlink() and target.read_bytes() == b'prior canonical bytes'
    target.chmod(0o640)
    native.hillslope_watbal_to_parquet(str(source), str(target), {1: 101})
    assert stat.S_IMODE(target.stat().st_mode) == 0o640
    candidate = root / 'native-candidate.parquet'
    previous_umask = os.umask(0o022)
    try:
        native.hillslope_watbal_to_parquet(str(source), str(candidate), {1: 101})
    finally:
        os.umask(previous_umask)
    candidate_mode = stat.S_IMODE(candidate.stat().st_mode)
    assert candidate_mode == 0o644
    assert pd.read_parquet(target).equals(pd.read_parquet(candidate))
    return {'symlink_error': symlink_failure, 'alias_and_prior_target_preserved': True,
            'regular_existing_mode_preserved': '0640',
            'new_candidate_mode_with_0022_umask': oct(candidate_mode),
            'same_report_payload': True}


with TemporaryDirectory(prefix='reports-security-checkpoint-') as temporary:
    root = Path(temporary)
    result = {'uid': os.getuid(), 'gid': os.getgid(),
              'catalog_alias_dependency': catalog_aliases(root / 'landuse'),
              'native_destination': native_destination(root / 'native')}
    print(json.dumps(result, indent=2))
