"""Native-format admission and preservation, including hostile parser differentials."""
from pathlib import Path

import pytest

from wepppy.wepp.single_input import SingleInputError, validate_soil_text
from wepppy.wepp.soils.utils import WeppSoilUtil

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / 'tests/data/single_input_soils'


def _records(version):
    return [line for line in (SOURCES / f'{version}.sol').read_text().splitlines()
            if line.strip() and not line.startswith('#')]


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
def test_preserved_soil_roundtrip_and_modifiers(tmp_path, monkeypatch, version):
    import wepppy.wepp.soils.utils.wepp_soil_util as module
    def no_prediction(_version):
        raise AssertionError('Uploaded soil serialization must not predict hydraulic values')
    monkeypatch.setattr(module, '_require_rosetta3_for_serialization', no_prediction)
    raw = (SOURCES / f'{version}.sol').read_bytes()
    source = tmp_path / 'source.sol'; source.write_bytes(raw)
    soil = WeppSoilUtil(str(source), preserve_input_format=True)
    original = soil.obj['ofes'][0]
    if version in ('2006', '2006.2'):
        assert original['avke'] == 37.25
    elif version == '9002':
        assert original['horizons'][0]['native_hydraulics'] == dict(
            theta_r=0.05, theta_s=0.45, alpha=0.0123, npar=1.61, ks=12.345, wp=0.1134, fc=0.2876)
    target = tmp_path / 'roundtrip.sol'
    soil.write(str(target))
    assert WeppSoilUtil(str(target), preserve_input_format=True).obj['ofes'] == soil.obj['ofes']
    soil.modify_initial_sat(0.42)
    soil.modify_kslast(0.012345)
    soil.ensure_minimum_soil_depth(1000)
    assert soil.obj['ofes'][0]['horizons'][-1]['solthk'] == 1000
    soil.clip_soil_depth(400)  # Exact horizon boundary must not duplicate depth.
    soil.write(str(target))
    reopened = WeppSoilUtil(str(target), preserve_input_format=True)
    ofe = reopened.obj['ofes'][0]
    assert ofe['sat'] == 0.42
    assert ofe['res_lyr']['kslast'] == 0.012345  # Including developed label in 9002.
    assert ofe['nsl'] == 1 and ofe['horizons'][0]['solthk'] == 400
    assert source.read_bytes() == raw


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
@pytest.mark.parametrize('label', ['/', ',', 'x,y', 'x!comment', "'O''Brien'", '"a\\"b"', "'a'junk"])
def test_native_label_differentials_rejected(version, label):
    records = _records(version)
    row = 4 if version == '9002' else 3
    records[row] = records[row].replace("'User loam'", label)
    with pytest.raises(SingleInputError):
        validate_soil_text('\n'.join(records))


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
@pytest.mark.parametrize('mutation', ['header_short', 'header_extra', 'layer_short', 'layer_extra',
                                       'restrictive_short', 'restrictive_extra', 'trailing', 'quoted_number',
                                       'unicode_separator', 'bad_cec', 'bad_depth', 'eleven_layers', 'two_ofes'])
def test_native_record_shape_and_semantics_rejected(version, mutation):
    records = _records(version)
    header = 4 if version == '9002' else 3
    layer = header + 1
    if mutation == 'header_short':
        records[header] = records[header].rsplit(' ', 1)[0]
    elif mutation == 'header_extra':
        records[header] += ' 42'
    elif mutation == 'layer_short':
        records[layer] = records[layer].rsplit(' ', 1)[0]
    elif mutation == 'layer_extra':
        records[layer] += ' 42'
    elif mutation == 'restrictive_short':
        records.pop()
    elif mutation == 'restrictive_extra':
        records[-1] += ' 42'
    elif mutation == 'trailing':
        records.append('42')
    elif mutation == 'quoted_number':
        records[header] = records[header].replace(' 2 ', " '2' ", 1)
    elif mutation == 'unicode_separator':
        records[layer] = records[layer].replace(' ', '\u00a0', 1)
    elif mutation == 'bad_cec':
        fields = records[layer].split(); fields[9 if version == '9002' else 8 if version == '7777' else 4] = '-1'
        records[layer] = ' '.join(fields)
    elif mutation == 'bad_depth':
        records[layer + 1] = records[layer + 1].replace('800 ', '400 ', 1)
    elif mutation == 'eleven_layers':
        records[header] = records[header].replace(' 2 ', ' 11 ', 1)
    elif mutation == 'two_ofes':
        records[2] = '2 1'
    with pytest.raises(SingleInputError):
        validate_soil_text('\n'.join(records))


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
@pytest.mark.parametrize('value', ['nan', 'inf', '1e999', '1e-999', '1e-46', '1_000', '1,' , '1/'])
def test_native_layer_numbers_rejected(version, value):
    records = _records(version)
    layer = 5 if version == '9002' else 4
    # Exercise every numeric field, including the seven 9002 appended values.
    fields = records[layer].split()
    for index in range(len(fields)):
        bad = fields.copy(); bad[index] = value
        modified = records.copy(); modified[layer] = ' '.join(bad)
        with pytest.raises(SingleInputError):
            validate_soil_text('\n'.join(modified))


@pytest.mark.parametrize('index,value', [(0, '2'), (3, '0'), (4, '-1')])
def test_9002_adjustment_header_rejected(index, value):
    records = _records('9002')
    fields = records[3].split(); fields[index] = value
    records[3] = ' '.join(fields)
    with pytest.raises(SingleInputError):
        validate_soil_text('\n'.join(records))


@pytest.mark.parametrize('index,value', [(11, '0.5'), (12, '0'), (13, '0'), (14, '1'),
                                       (15, '0'), (16, '0'), (17, '0.1')])
def test_9002_hydraulic_bounds_rejected(index, value):
    records = _records('9002')
    fields = records[5].split(); fields[index] = value
    records[5] = ' '.join(fields)
    with pytest.raises(SingleInputError):
        validate_soil_text('\n'.join(records))


@pytest.mark.parametrize('index,value', [(14, '1.000000001'), (11, '0.4499999999'),
                                       (16, '0.28759999999')])
def test_9002_bounds_must_survive_native_real_rounding(index, value):
    records = _records('9002')
    fields = records[5].split(); fields[index] = value
    records[5] = ' '.join(fields)
    with pytest.raises(SingleInputError):
        validate_soil_text('\n'.join(records))


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
def test_increasing_depth_must_survive_native_real_rounding(version):
    records = _records(version)
    layer = 5 if version == '9002' else 4
    records[layer + 1] = records[layer + 1].replace('800 ', '400.00000001 ', 1)
    with pytest.raises(SingleInputError):
        validate_soil_text('\n'.join(records))


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
def test_native_rounding_must_not_hide_invalid_original_texture(version):
    records = _records(version)
    layer = 5 if version == '9002' else 4
    fields = records[layer].split()
    start = 6 if version == '9002' else 5 if version == '7777' else 1
    fields[start:start + 2] = ['60.00000001', '40']
    records[layer] = ' '.join(fields)
    with pytest.raises(SingleInputError):
        validate_soil_text('\n'.join(records))


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
def test_valid_texture_sum_survives_native_rounding(version):
    records = _records(version)
    layer = 5 if version == '9002' else 4
    fields = records[layer].split()
    start = 6 if version == '9002' else 5 if version == '7777' else 1
    fields[start:start + 2] = ['30.1', '69.9']
    records[layer] = ' '.join(fields)
    validate_soil_text('\n'.join(records))


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
@pytest.mark.parametrize('layers', [10, 11])
def test_complete_profiles_at_native_layer_limit(version, layers):
    records = _records(version)
    header = 4 if version == '9002' else 3
    records[header] = records[header].replace(' 2 ', f' {layers} ', 1)
    fields = records[header + 1].split()
    horizons = [' '.join([str(100 * (index + 1))] + fields[1:]) for index in range(layers)]
    text = '\n'.join(records[:header + 1] + horizons + [records[-1]])
    if layers == 10:
        validate_soil_text(text)
    else:
        with pytest.raises(SingleInputError):
            validate_soil_text(text)


@pytest.mark.parametrize('index,value', [(1, '0'), (1, '-1'), (2, '-1'),
                                       (3, '1.01'), (4, '-0.01'), (4, '0.31')])
def test_7777_hydraulic_bounds_rejected(index, value):
    records = _records('7777')
    fields = records[4].split(); fields[index] = value
    records[4] = ' '.join(fields)
    with pytest.raises(SingleInputError):
        validate_soil_text('\n'.join(records))


def test_supplied_7777_preserves_exact_native_fields(tmp_path):
    from wepppy.wepp.single_input import decode_source
    source = SOURCES / 'boulderck_mica_1_7777.sol'
    raw = source.read_bytes()
    assert b'\r\n' in raw
    validate_soil_text(decode_source(raw))
    soil = WeppSoilUtil(str(source), preserve_input_format=True)
    target = tmp_path / 'prepared.sol'
    soil.write(str(target))
    records = [line for line in target.read_text().splitlines() if not line.startswith('#')]
    assert records[0] == '7777' and records[2] == '1 1'
    import shlex
    assert len(shlex.split(records[3])) == 8
    assert list(map(float, records[4].split())) == [500, 1.29, 29.3, .35, .09, 27.4, 11.5, 3.5, 14.3, 3]
    assert list(map(float, records[5].split())) == [2400, 1.5, 91.7, .22, .09, 75, 3.5, .39, 2.5, 40]
    assert list(map(float, records[6].split())) == [1, 10, .46]
    assert source.read_bytes() == raw
