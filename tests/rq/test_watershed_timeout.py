"""WRT-01 arithmetic, actual native-file reads and compatibility boundaries."""
from types import SimpleNamespace

import pytest

from wepppy.rq.watershed_timeout import watershed_timeout_options
from wepp_runner.wepp_runner import make_watershed_run

pytestmark = pytest.mark.unit


def options(years=100, hillslopes=2, base=43200):
    wepp = SimpleNamespace(wepp_bin='wepp_260803', watershed_instance=SimpleNamespace(sub_n=hillslopes))
    return watershed_timeout_options(wepp, SimpleNamespace(input_years=years, is_single_storm=False), base)


@pytest.mark.parametrize('years,hills,expected', [
    (1, 1, 43200), (100, 2149, 43200), (500, 1908, 50400),
    (1000, 1908, 97200), ('1000', '1908', 97200),
    (1000, 864, 43200), (1000, 865, 46800),
    (1, 936000, 46800), (1, 936001, 50400),
])
def test_workload_budget_and_exact_hour_boundaries(years, hills, expected):
    result = options(years, hills)
    assert result['timeout'] == expected
    assert result['meta']['watershed_timeout'] == dict(
        policy='WRT-01', years=int(years), hillslopes=int(hills),
        seconds_per_hillslope_year=.05, timeout_seconds=expected,
        workload_source='controllers', wepp_bin='wepp_260803')


def test_larger_base_allowance_is_preserved():
    assert options(base=100001)['timeout'] == 100001


@pytest.mark.parametrize('bad', [None, True, False, 0, -1, 1.2, 100.0, '0', '-1', '1.5', 'nan', float('inf'), '1e3', '9'*100])
@pytest.mark.parametrize('field', ['years', 'hillslopes', 'base'])
def test_invalid_workload_or_base_is_not_silently_defaulted(field, bad):
    with pytest.raises(ValueError):
        options(**{field: bad})


@pytest.mark.parametrize('args', [dict(years=10**12), dict(hillslopes=10**10), dict(base=2**31)])
def test_alarm_range_is_finite(args):
    with pytest.raises(ValueError, match='alarm range'):
        options(**args)


@pytest.mark.parametrize('binary', ['wepp_dcc52a6', 'wepp_260803', 'wepp_260525'])
def test_owned_legacy_and_modern_inputs_override_stale_controllers(tmp_path, binary):
    make_watershed_run(1000, list(range(1, 1909)), str(tmp_path), wepp_bin=binary)
    source = tmp_path / 'pw0.run'
    raw = source.read_bytes()
    wepp = SimpleNamespace(runs_dir=str(tmp_path), wepp_bin=binary,
                           watershed_instance=SimpleNamespace(sub_n=1))
    climate = SimpleNamespace(is_single_storm=False, input_years=1)
    result = watershed_timeout_options(wepp, climate, 43200, prepared_inputs=True)
    assert result['timeout'] == 97200
    assert result['meta']['watershed_timeout']['hillslopes'] == 1908
    assert result['meta']['watershed_timeout']['years'] == 1000
    assert result['meta']['watershed_timeout']['workload_source'] == 'prepared_run_file'
    assert source.read_bytes() == raw


@pytest.mark.parametrize('mutation', ['missing', 'empty', 'oversize', 'bad_count', 'zero_years', 'bad_mode', 'binary'])
def test_invalid_prepared_input_fails_explicitly(tmp_path, mutation):
    make_watershed_run(100, [1, 2], str(tmp_path), wepp_bin='wepp_260803')
    path = tmp_path / 'pw0.run'
    if mutation == 'missing':
        path.unlink()
    elif mutation == 'empty':
        path.write_bytes(b'')
    elif mutation == 'oversize':
        path.write_bytes(b' ' * (1024*1024+1))
    elif mutation == 'binary':
        path.write_bytes(b'\xff')
    else:
        lines = path.read_text().splitlines()
        count_index = 4 if lines[4].strip().isdigit() else 5
        lines[{'bad_count':count_index, 'zero_years':-1, 'bad_mode':2}[mutation]] = {'bad_count':'bad','zero_years':'0','bad_mode':'2'}[mutation]
        path.write_text('\n'.join(lines))
    with pytest.raises((ValueError, FileNotFoundError)):
        watershed_timeout_options(SimpleNamespace(runs_dir=str(tmp_path)),
                                  SimpleNamespace(is_single_storm=False), 43200, prepared_inputs=True)


def test_single_storm_needs_no_unused_continuous_inputs():
    assert watershed_timeout_options(object(), SimpleNamespace(is_single_storm=True), 43200,
                                     prepared_inputs=True) == {'timeout': 43200}


@pytest.mark.parametrize('mutation', ['truncated', 'extra_year', 'inflated_count'])
def test_prepared_workload_requires_intact_record_layout(tmp_path, mutation):
    make_watershed_run(100, [1, 2], str(tmp_path), wepp_bin='wepp_260525')
    path = tmp_path / 'pw0.run'
    if mutation == 'truncated':
        path.write_text('M\nYes\n1\n2\n1908\ngarbage\n1000\n')
    elif mutation == 'extra_year':
        path.write_text(path.read_text() + '\n1000\n')
    else:
        lines = path.read_text().splitlines()
        lines[4] = '1908'
        path.write_text('\n'.join(lines))
    with pytest.raises(ValueError, match='intact'):
        watershed_timeout_options(SimpleNamespace(runs_dir=str(tmp_path)),
                                  SimpleNamespace(is_single_storm=False), 43200, prepared_inputs=True)
