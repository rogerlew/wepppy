"""Exercise ledger precedence and native PASS composition without spatial inputs."""
from pathlib import Path

import pytest
import wepppyo3.wepp_interchange as native

from wepppy.wepp.interchange.roads_accounting import compose, load

pytestmark = pytest.mark.integration


def _pass(path, area):
    path.parent.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).parent / 'test_project/output/H1.pass.dat'
    lines = source.read_text().splitlines()
    lines[2] = f'{area:.5E}'
    path.write_text('\n'.join(lines) + '\n')


def _record(source, replacement=False):
    return {'status': 'completed', 'segment_run_id': source, 'target_hillslope_wepp_id': 1,
            'segment_pass_relpath': f'wepp/roads/output/H{source}.pass.dat',
            'routing_mode': 'outslope_unrutted_replacement' if replacement else 'channel_associated'}


@pytest.mark.parametrize('road_area', [25., 100., 150.])
def test_full_footprint_and_expansion(tmp_path, road_area):
    _pass(tmp_path / 'wepp/output/H1.pass.dat', 100.)
    _pass(tmp_path / 'wepp/roads/output/H901.pass.dat', road_area)
    before = (tmp_path / 'wepp/output/H1.pass.dat').read_bytes()
    ledger = compose(tmp_path, [1], [_record(901)], single_storm=True)
    assert ledger['sources'][1]['represented_area_m2'] == road_area
    assert ledger['sources'][1]['pass_scale'] == 1.
    assert native.roads_pass_geometry(str(tmp_path / 'wepp/roads/output/H1.pass.dat'))[0] == max(100., road_area)
    assert (tmp_path / 'wepp/output/H1.pass.dat').read_bytes() == before
    assert load(tmp_path)['state'] == 'composed'


def test_replacement_supersedes_additive_and_keeps_remainder(tmp_path):
    _pass(tmp_path / 'wepp/output/H1.pass.dat', 100.)
    for source, area in [(901, 50.), (902, 30.), (903, 70.)]:
        _pass(tmp_path / f'wepp/roads/output/H{source}.pass.dat', area)
    ledger = compose(tmp_path, [1], [_record(901), _record(902, True), _record(903, True)], single_storm=True)
    assert [s['native_id'] for s in ledger['sources']] == [902, 903]
    assert ledger['targets'][0]['area_m2'] == 100.


def test_unchanged_bytes_and_stale_source_detection(tmp_path):
    _pass(tmp_path / 'wepp/output/H1.pass.dat', 100.)
    (tmp_path / 'wepp/roads/output').mkdir(parents=True)
    compose(tmp_path, [1], [], single_storm=True)
    base = tmp_path / 'wepp/output/H1.pass.dat'
    assert base.read_bytes() == (tmp_path / 'wepp/roads/output/H1.pass.dat').read_bytes()
    base.write_bytes(base.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='source changed'):
        load(tmp_path)


def test_collision_fails_before_composition(tmp_path):
    _pass(tmp_path / 'wepp/output/H1.pass.dat', 100.)
    with pytest.raises(ValueError, match='collision'):
        compose(tmp_path, [1], [_record(1)], single_storm=True)


def test_destination_alias_cannot_unlink_baseline(tmp_path):
    baseline = tmp_path / 'wepp/output/H1.pass.dat'
    _pass(baseline, 100.)
    original = baseline.read_bytes()
    roads = tmp_path / 'wepp/roads'
    roads.mkdir(parents=True)
    (roads / 'output').symlink_to(baseline.parent, target_is_directory=True)
    with pytest.raises(ValueError, match='alias'):
        compose(tmp_path, [1], [], single_storm=True)
    assert baseline.read_bytes() == original


def test_retained_corrected_artifact_without_ledger_cannot_fallback(tmp_path):
    from wepppy.wepp.interchange.roads_accounting import has_accounting, accounting_source
    source = tmp_path / 'wepp/roads/output/interchange/H.accounting.wat.parquet'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'retained corrected artifact')
    assert has_accounting(tmp_path)
    with pytest.raises(FileNotFoundError):
        accounting_source(tmp_path)


def test_allocation_edit_invalidates_pass_lineage(tmp_path):
    import json
    from wepppy.wepp.interchange.roads_accounting import LEDGER
    _pass(tmp_path / 'wepp/output/H1.pass.dat', 100.)
    (tmp_path / 'wepp/roads/output').mkdir(parents=True)
    compose(tmp_path, [1], [], single_storm=True)
    path = tmp_path / LEDGER
    ledger = json.loads(path.read_text())
    ledger['sources'][0]['represented_area_m2'] = 200.
    ledger['targets'][0]['area_m2'] = 200.
    path.write_text(json.dumps(ledger))
    with pytest.raises(ValueError, match='allocation differs'):
        load(tmp_path)


def test_new_ledger_respects_umask_and_updates_preserve_mode(tmp_path):
    import os
    import stat
    from wepppy.wepp.interchange.roads_accounting import LEDGER, mark_routed
    _pass(tmp_path / 'wepp/output/H1.pass.dat', 100.)
    (tmp_path / 'wepp/roads/output').mkdir(parents=True)
    previous = os.umask(0o007)
    try:
        compose(tmp_path, [1], [], single_storm=True)
    finally:
        os.umask(previous)
    ledger = tmp_path / LEDGER
    assert stat.S_IMODE(ledger.stat().st_mode) == 0o660
    ledger.chmod(0o640)
    mark_routed(tmp_path)
    assert stat.S_IMODE(ledger.stat().st_mode) == 0o640


def test_continuous_products_and_same_mtime_change(tmp_path):
    import os
    from types import SimpleNamespace
    import pyarrow as pa
    import pyarrow.parquet as pq
    from wepppy.wepp.interchange.roads_accounting import mark_routed, regenerate, accounting_source
    baseline = tmp_path / 'wepp/output'
    baseline.mkdir(parents=True)
    raw = baseline / 'H1.pass.dat'
    raw.write_text('p1.cli\n1 2020\n1.00000E+02\n5 0.000002 0.00001 0.00003 0.000306 0.0002\n0 0 0 0\n' +
                   ''.join(f'NO EVENT{2020:6d}{day:6d} 0.00000E+00 0.00000E+00\n' for day in (1, 2, 3)))
    metrics = ['P','RM','Q','Dp','latqcc','QOFE','Ep','Es','Er','UpStrmQ','SubRIn',
               'Total-Soil Water','frozwt','Snow-Water','Tile','Irr']
    rows = [dict(wepp_id=1, ofe_id=1, year=2020, sim_day_index=d, julian=d,
                 month=1, day_of_month=d, water_year=2020, Area=100., **{n: 1. for n in metrics}) for d in (1, 2, 3)]
    (baseline/'interchange').mkdir()
    pq.write_table(pa.Table.from_pylist(rows), baseline/'interchange/H.wat.parquet')
    output = tmp_path / 'wepp/roads/output/interchange'
    output.mkdir(parents=True)
    compose(tmp_path, [1], [], single_storm=False)
    native.hillslope_pass_files_to_parquet([str(output.parent/'H1.pass.dat')], str(output/'H.pass.parquet'), 1, 2)
    mark_routed(tmp_path)
    regenerate(tmp_path, SimpleNamespace(gwstorage=0., bfcoeff=.04, dscoeff=0.))
    source = accounting_source(tmp_path)
    assert pq.read_table(source)['Area'].to_pylist() == [100.] * 3
    original_stat = source.stat()
    table = pq.read_table(source)
    table = table.set_column(table.schema.get_field_index('P'), 'P', pa.array([2.,2.,2.]))
    pq.write_table(table, source)
    os.utime(source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    with pytest.raises(ValueError, match='product changed'):
        accounting_source(tmp_path)
