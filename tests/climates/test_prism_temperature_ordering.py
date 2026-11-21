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
    from wepppyo3.climate import cli_revision
    source = write_source(tmp_path / 'source.cli')
    output = tmp_path / 'repaired.cli'
    ref, target = normals(), normals(True)
    raw = pd.Series(-2., index=read_cli(source).index)
    dates = raw.index.strftime('%Y%m%d').to_numpy(dtype=np.int32)
    cli_revision(str(source), str(output), ref['ppt'], ref['tmax'], ref['tmin'],
                 target['ppt'], target['tmax'], target['tmin'], raw_tdmean_c=(dates, raw.to_numpy()))
    before = read_cli(output)
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


@pytest.mark.integration
def test_native_dated_dewpoint_matches_full_python_revision(tmp_path):
    from wepppyo3.climate import cli_revision
    from wepppy.climates.cligen import ClimateFile
    from wepppy.climates.prism.wepp_adapter import read_cli

    source = write_source(tmp_path / 'source.cli')
    # Exercise the legacy rewrite of storm fields as well as a cooler hillslope.
    source.write_text(source.read_text().replace('4.0 1.0 0.5 2.0', '4.0 1.25 0.54 2.06')
                      .replace('100 2 180 -5', '100 2 180 5'))
    reference, target = normals(), normals(True)
    target['tmin'][0] = 9.46
    args = [group[var] for group in (reference, target) for var in ('ppt', 'tmax', 'tmin')]
    raw = pd.Series([-3.0, -.555, 0.033, 1.123], index=read_cli(source).index)
    dates = raw.index.strftime('%Y%m%d').to_numpy(dtype=np.int32)
    old, new = tmp_path / 'old.cli', tmp_path / 'new.cli'
    cli_revision(str(source), str(old), *args)
    assert not Path(str(old) + '-dewpoint.csv').exists()
    assert (read_cli(old).tdew == 5.).all()
    tmin = read_cli(old).tmin
    derived = np.maximum(raw, tmin)
    legacy = ClimateFile(str(old))
    legacy.replace_var('tdew', raw.index, derived)
    legacy.write(str(old))
    cli_revision(str(source), str(new), *args, raw_tdmean_c=(dates, raw.to_numpy()))
    pd.testing.assert_frame_equal(read_cli(old), read_cli(new))
    expected = pd.DataFrame({'date': raw.index.strftime('%Y-%m-%d'), 'raw_tdmean_C': raw.to_numpy(),
                             'final_tmin_C': tmin.to_numpy(), 'derived_tdmean_C': derived.to_numpy()})
    pd.testing.assert_frame_equal(expected, pd.read_csv(str(new) + '-dewpoint.csv'))
    log = Path(str(new) + '.temperature-ordering.log').read_text()
    assert f'dewpoint_changed_days={(expected.raw_tdmean_C < expected.final_tmin_C).sum()}' in log
    with pytest.raises(TypeError):
        cli_revision(str(source), str(new), *args, (dates, raw.to_numpy()))


@pytest.mark.integration
@pytest.mark.parametrize('fault', ['shift', 'short', 'extra', 'nan', 'unordered', 'negative_wind', 'bad_month'])
def test_native_dated_dewpoint_rejects_invalid_candidate(tmp_path, fault):
    from wepppyo3.climate import cli_revision

    source = write_source(tmp_path / 'source.cli')
    dates = np.array([20000130, 20000131, 20000201, 20000202], dtype=np.int32)
    if fault == 'shift':
        dates[0] -= 1
    elif fault == 'short':
        dates = dates[:-1]
    elif fault == 'extra':
        dates = np.append(dates, np.int32(20000203))
    elif fault == 'unordered':
        dates = dates[::-1].copy()
    elif fault == 'negative_wind':
        source.write_text(source.read_text().replace('100 2 180', '100 -2 180'))
    elif fault == 'bad_month':
        source.write_text(source.read_text().replace('30 1 2000', '30 0 2000'))
    values = np.zeros(len(dates))
    if fault == 'nan':
        values[-1] = np.nan
    out = tmp_path / 'candidate.cli'
    with pytest.raises(OSError):
        cli_revision(str(source), str(out), *([[1.] * 12] * 6), raw_tdmean_c=(dates, values))
    assert 'status=complete' not in Path(str(out) + '.temperature-ordering.log').read_text()


@pytest.mark.integration
def test_native_dewpoint_signed_zero_matches_serialized_minimum(tmp_path):
    from wepppyo3.climate import cli_revision

    source = write_source(tmp_path / 'source.cli')
    output = tmp_path / 'signed-zero.cli'
    days = np.array([20000130, 20000131, 20000201, 20000202], dtype=np.int32)
    cli_revision(str(source), str(output), *([[0.] * 12] * 6),
                 raw_tdmean_c=(days, np.full(4, -0.0)))
    assert all(row.split()[-1] == '0.0' for row in output.read_text().splitlines()[15:])
    assert ',0.0,0.0' in Path(str(output) + '-dewpoint.csv').read_text()
