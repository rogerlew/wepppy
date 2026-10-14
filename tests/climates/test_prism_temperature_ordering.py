"""Exact PRISM writers, shared numerical rule, and visible repair records."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from wepppy.climates.edde.cligen import read_cli, revise_prism
from wepppy.climates.edde.client import DataQualityError
from wepppy.climates.prism.temperature import repair_temperature_ordering


def write_source(path, *, breakpoint=False, bad=None):
    header = (Path(__file__).parents[1] / 'wepp_runner/fixtures/hillslope_smoke/runs/p1.cli').read_text().splitlines()[:15]
    if breakpoint:
        header[1] = '1 1 0'
        header[13] = 'da mo year nbrkpt tmax tmin rad w-vl w-dir tdew'
    rows = []
    for i, (day, month, tmax) in enumerate([(30, 1, .2), (31, 1, .5), (1, 2, 0.), (2, 2, 10.)]):
        tmin = bad if i == 0 and bad is not None else 0.
        if breakpoint:
            rows += [f'{day} {month} 2000 2 {tmax} {tmin} 100 2 180 -5', '0.0 0.0', '1.0 4.0']
        else:
            rows += [f'{day} {month} 2000 4.0 1.0 0.5 2.0 {tmax} {tmin} 100 2 180 -5']
    path.write_text('\n'.join(header + rows) + '\n')
    return path


def normals(target=False):
    maximum = [19., 18.5] + [20.] * 10 if target else [20.] * 12
    return dict(ppt=[100.] * 12, tmax=maximum, tmin=[9.5] * 12 if target else [10.] * 12,
                provenance=dict(period='1991-2020', sha256='fixture', units={'ppt': 'mm/month', 'tmax': 'C', 'tmin': 'C'}))


@pytest.mark.unit
def test_midpoint_and_valid_value_invariance():
    maximum = np.array([3., 0., -2., 1., -5., -.1])
    minimum = np.array([1., 0., -5., 1.5, -4.5, .1])
    upper, lower, result = repair_temperature_ordering(maximum, minimum)
    np.testing.assert_array_equal(upper[:3], maximum[:3])
    np.testing.assert_array_equal(lower[:3], minimum[:3])
    np.testing.assert_allclose(upper[3:], [1.25, -4.75, 0.])
    np.testing.assert_array_equal(upper[3:], lower[3:])
    np.testing.assert_array_equal(maximum, [3., 0., -2., 1., -5., -.1])
    assert result['corrected_days'] == 3
    assert result['maximum_adjustment_c'] == .25
    for value in [float('nan'), float('inf')]:
        with pytest.raises(ValueError, match='finite'):
            repair_temperature_ordering([value], [0.])


@pytest.mark.integration
@pytest.mark.parametrize('writer', ['native', 'public', 'breakpoint', 'edde'])
def test_real_writers_repair_and_preserve_weather(tmp_path, monkeypatch, writer):
    source = write_source(tmp_path / 'source.cli', breakpoint=writer == 'breakpoint')
    output = tmp_path / 'revised.cli'
    reference, target = normals(), normals(True)
    if writer == 'native':
        from wepppyo3.climate import cli_revision
        cli_revision(str(source), str(output), reference['ppt'], reference['tmax'], reference['tmin'],
                     target['ppt'], target['tmax'], target['tmin'])
    elif writer == 'public':
        import wepppy.climates.prism as module
        for name in ['ppt', 'tmax', 'tmin']:
            monkeypatch.setattr(module, f'get_prism_monthly_{name}',
                                lambda lon, lat, units, key=name: (reference if lon == 0 else target)[key])
        module.prism_revision(str(source), 0., 0., 1., 1., str(output))
    elif writer == 'breakpoint':
        from wepppy.nodb.core import climate_build_helpers as module
        # Normal acquisition is the mocked boundary; actual breakpoint writer is exercised.
        monkeypatch.setattr(module, 'get_monthlies', lambda filename, *_: target[filename])
        module.cli_revision(str(source), True, reference['ppt'], reference['tmax'], reference['tmin'],
                            'ppt', 'tmin', 'tmax', 1., 1., str(output))
    else:
        result = revise_prism(source, output, reference, target)
        assert result['temperature_ordering']['corrected_days'] == 2
        assert result['temperature_ordering']['monthly_mean_adjustment_c'][2]['tmax'] is None
    original, revised = read_cli(source), read_cli(output)
    assert (revised.tmin <= revised.tmax).all()
    np.testing.assert_array_equal(revised.tmin.iloc[[0, 2]], revised.tmax.iloc[[0, 2]])
    np.testing.assert_allclose(revised.tmax.iloc[[1, 3]], [-.5, 8.5])
    for name in ['prcp', 'dur', 'rad', 'w-vl', 'w-dir', 'tdew']:
        np.testing.assert_array_equal(revised[name], original[name])
    assert revised.index.equals(original.index)
    log = Path(str(output) + '.temperature-ordering.log').read_text()
    assert 'status=working' in log and 'status=complete' in log and 'corrected_days=2' in log
    if writer == 'breakpoint':
        # Existing breakpoint serialization normalizes spacing and depth precision.
        assert [tuple(map(float, line.split())) for line in output.read_text().splitlines() if len(line.split()) == 2] == [
            tuple(map(float, line.split())) for line in source.read_text().splitlines() if len(line.split()) == 2]


@pytest.mark.integration
@pytest.mark.parametrize('value', ['nan', '1.0'])
def test_invalid_source_is_not_repaired(tmp_path, value):
    from wepppyo3.climate import cli_revision
    source = write_source(tmp_path / 'source.cli', bad=value)
    ref = normals()
    for writer in ['native', 'edde']:
        output = tmp_path / f'{writer}.cli'
        with pytest.raises((OSError, DataQualityError)):
            if writer == 'native':
                cli_revision(str(source), str(output), ref['ppt'], ref['tmax'], ref['tmin'], ref['ppt'], ref['tmax'], ref['tmin'])
            else:
                revise_prism(source, output, ref, ref)
        assert 'status=complete' not in Path(str(output) + '.temperature-ordering.log').read_text()


@pytest.mark.integration
def test_historic_dewpoint_floor_uses_repaired_minimum(tmp_path):
    from wepppy.climates.prism.wepp_adapter import floor_dewpoint
    source = write_source(tmp_path / 'source.cli')
    output = tmp_path / 'repaired.cli'
    revise_prism(source, output, normals(), normals(True))
    before = read_cli(output)
    raw = pd.Series(-2., index=before.index)
    floor_dewpoint(output, raw, tmp_path / 'dewpoint.csv')
    np.testing.assert_array_equal(read_cli(output).tdew, np.maximum(raw, before.tmin))
    assert read_cli(output).tdew.iloc[0] < -.5  # The unrepaired Tmin must not survive downstream.


@pytest.mark.unit
def test_edde_preserves_existing_repair_log(tmp_path):
    output = tmp_path / 'out.cli'
    log = Path(str(output) + '.temperature-ordering.log')
    log.write_text('prior evidence')
    with pytest.raises(ValueError, match='new file'):
        revise_prism('unused', output, normals(), normals())
    assert log.read_text() == 'prior evidence'


@pytest.mark.unit
def test_edde_diagnostic_failure_does_not_publish_complete_manifest(tmp_path, monkeypatch):
    import wepppy.climates.edde.cligen as module
    source = write_source(tmp_path / 'source.cli')
    output = tmp_path / 'out.cli'

    def fail_diagnostic(*args):
        raise OSError('diagnostic write failed')

    monkeypatch.setattr(module, 'complete_temperature_revision', fail_diagnostic)
    with pytest.raises(OSError, match='diagnostic write failed'):
        revise_prism(source, output, normals(), normals(True))
    assert not output.with_suffix('.prism.json').exists()
    assert 'status=complete' not in Path(str(output) + '.temperature-ordering.log').read_text()


@pytest.mark.unit
def test_diagnostics_measure_actual_float_adjustment():
    maximum, minimum = 1., np.nextafter(1., np.inf)
    upper, lower, result = repair_temperature_ordering([maximum], [minimum])
    assert result['maximum_adjustment_c'] == max(abs(upper[0] - maximum), abs(lower[0] - minimum))
    with pytest.raises(ValueError, match='magnitude must be finite'):
        repair_temperature_ordering([-1e308], [1e308])


@pytest.mark.integration
@pytest.mark.parametrize('writer', ['native', 'edde'])
def test_nonrepresentable_diagnostics_fail_before_completion(tmp_path, writer):
    from wepppyo3.climate import cli_revision
    source = write_source(tmp_path / 'source.cli')
    output = tmp_path / 'out.cli'
    reference, target = normals(), normals()
    reference.update(tmax=[1e308] * 12, tmin=[-1e308] * 12)
    target.update(tmax=[0.] * 12, tmin=[0.] * 12)
    with pytest.raises((OSError, DataQualityError), match='magnitude must be finite'):
        if writer == 'native':
            cli_revision(str(source), str(output), reference['ppt'], reference['tmax'], reference['tmin'],
                         target['ppt'], target['tmax'], target['tmin'])
        else:
            revise_prism(source, output, reference, target)
    assert not output.with_suffix('.prism.json').exists()
    assert 'status=complete' not in Path(str(output) + '.temperature-ordering.log').read_text()
