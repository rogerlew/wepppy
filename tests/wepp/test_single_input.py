from pathlib import Path

import pytest

from wepppy.wepp.single_input import (
    SingleInputError, canonical_management, decode_source,
    read_uploaded_management, validate_filename, validate_soil_text,
)

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
MAN = ROOT / 'wepppy/wepp/management/data/GeoWEPP/grass.man'
SOL = ROOT / 'wepppy/wepp/soils/soilsdb/data/Forest/Forest loam.sol'


def test_management_real_source_roundtrip(tmp_path):
    source = tmp_path / 'source.man'
    source.write_text(decode_source(MAN.read_bytes()))
    management = read_uploaded_management(source)
    target = tmp_path / 'canonical.man'
    target.write_text(canonical_management(management))
    reopened = read_uploaded_management(target)
    assert reopened.nofe == 1
    assert reopened.inis[0].data.cancov == management.inis[0].data.cancov
    assert reopened.sim_years == management.sim_years


@pytest.mark.parametrize('mutation', [
    lambda text: text.replace('98.4', '2016.3', 1),
    lambda text: text + '\n999\n',
    lambda text: text.replace('98.4', 'nan', 1),
])
def test_management_rejects_unsupported_and_trailing(tmp_path, mutation):
    source = tmp_path / 'source.man'
    source.write_text(mutation(decode_source(MAN.read_bytes())))
    with pytest.raises(SingleInputError):
        read_uploaded_management(source)


def test_soil_source_is_not_repaired():
    text = decode_source(SOL.read_bytes())
    validate_soil_text(text)
    for malformed in [text + '1 2 3\n', text.replace('45.0', '99.0'),
                      text.replace('7778', '9005', 1), text.replace('1.4', 'nan')]:
        with pytest.raises(SingleInputError):
            validate_soil_text(malformed)


@pytest.mark.parametrize('name', ['../evil.man', '/evil.man', 'x\\evil.man', 'a\x00.man', 'x.sol'])
def test_bad_management_names(name):
    with pytest.raises(SingleInputError):
        validate_filename(name, 'landuse')


def test_uppercase_extensions_and_plain_text():
    assert validate_filename('My management.MAN', 'landuse') == 'My management.MAN'
    assert validate_filename('My soil.SOL', 'soils') == 'My soil.SOL'
    assert decode_source(b'\xef\xbb\xbf7778\r\n') == '7778\n'
    for raw in [b'', b'\x00', b'\xff', b'NaN\n', b'1e999\n']:
        with pytest.raises(SingleInputError):
            decode_source(raw)


@pytest.mark.parametrize("token", ["8_00.0", "1e300", "1e-300", "1e-999", "-1e-999"])
def test_native_numeric_values_rejected(token):
    with pytest.raises(SingleInputError):
        decode_source((token + "\n").encode())
    text = decode_source(SOL.read_bytes())
    lines = text.splitlines()
    index = next(i for i, line in enumerate(lines) if len(line.split()) == 11)
    fields = lines[index].split(); fields[0] = token
    lines[index] = " ".join(fields)
    with pytest.raises(SingleInputError):
        validate_soil_text("\n".join(lines))


def test_uploaded_summary_uses_active_initial_and_applies_cover(tmp_path):
    from copy import deepcopy
    from wepppy.wepp.management.managements import ManagementSummary
    source = tmp_path / 'source.man'
    source.write_text(decode_source(MAN.read_bytes()))
    management = read_uploaded_management(source)
    second = deepcopy(management.inis[0])
    second.name = 'SecondInitial'
    second.data.cancov = 0.23
    management.inis.append(second)
    management.man.ofeindx[0].loop_name = second.name
    management.setroot()
    source.write_text(canonical_management(management))
    read_uploaded_management(source)
    summary = ManagementSummary(Key='single-user-defined', ManagementFile=source.name,
                                ManagementDir=str(tmp_path), Description='source', Color=(0, 0, 0, 255))
    assert summary.cancov == pytest.approx(0.23)
    for field, value in [('cancov', 0.3), ('inrcov', 0.4), ('rilcov', 0.5)]:
        setattr(summary, field + '_override', value)
    prepared = summary.get_management()
    active = prepared.inis[int(str(prepared.man.ofeindx[0])) - 1]
    assert (active.data.cancov, active.data.inrcov, active.data.rilcov) == pytest.approx((0.3, 0.4, 0.5))
    assert read_uploaded_management(source).inis[1].data.cancov == pytest.approx(0.23)


def _bounded_management():
    from wepppy.wepp.management.managements import OpLoop, SurfLoop, ContourLoop, DrainLoop
    model = read_uploaded_management(MAN)
    prefix = ['Boundary', '(null)', '(null)', '(null)', '1']
    model.ops.append(OpLoop(prefix.copy() + ['0 0 1', '1', '1 1 0 0 .01 0 .1'], model))
    model.surfs.append(SurfLoop(prefix.copy() + ['1', '100', '1', '.1', '1'], model))
    model.contours.append(ContourLoop(prefix.copy() + ['.01 .1 10 .5'], model))
    model.drains.append(DrainLoop(prefix.copy() + ['1 .1 .1 10'], model))
    return model


def _repeat(items, count, model, *, names=False):
    from copy import deepcopy
    seed = items[0]
    items.clear()
    for index in range(count):
        clone = deepcopy(seed, {id(model): model, id(model.man): model.man,
                                **{id(rotation): rotation for rotation in model.man.loops}})
        if names:
            clone.name = f'Boundary{index}'
        items.append(clone)


@pytest.mark.parametrize('section,maximum', [
    ('plants', 20), ('ops', 32), ('inis', 32), ('surfs', 30),
    ('contours', 32), ('drains', 32), ('years', 32),
])
def test_management_section_native_boundaries(tmp_path, section, maximum):
    from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
    for count in (maximum, maximum + 1):
        model = _bounded_management()
        entries = getattr(model, section)
        # Preserve the referenced first scenario name; additional definitions are unique.
        original_name = entries[0].name
        _repeat(entries, count, model, names=True)
        entries[0].name = original_name
        model.setroot()
        source = tmp_path / f'{section}-{count}.man'
        source.write_text(canonical_management(model))
        if count > maximum:
            with pytest.raises(SingleInputError):
                read_uploaded_management(source)
            continue
        accepted = read_uploaded_management(source)
        assert len(getattr(accepted, section)) == maximum
        combined = tmp_path / 'combined.man'
        ManagementMultipleOfeSynth([accepted, accepted], deduplicate_scenarios=True).write(str(combined))
        assert read_uploaded_management(combined, max_ofes=32).nofe == 2


@pytest.mark.parametrize('event,maximum', [('tillage', 20), ('cutting', 25), ('grazing', 10), ('crops', 6)])
def test_management_event_native_boundaries(tmp_path, event, maximum):
    from wepppy.wepp.management.managements import YearLoopCroplandPerennial
    from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
    for count in (maximum, maximum + 1):
        model = _bounded_management()
        if event == 'tillage':
            _repeat(model.surfs[0].data, count, model)
            model.surfs[0].ntill = count
        elif event == 'crops':
            crop = model.man.loops[0].years[0][0]
            _repeat(crop.manindx, count, model)
            crop.nycrop = count
        else:
            # Build a valid one-event schedule, then serialize the requested boundary.
            lines = ['0', '0', '0', '0', '1' if event == 'cutting' else '2', '1']
            lines += ['100'] if event == 'cutting' else ['1 1 500 .5', '100', '120']
            perennial = YearLoopCroplandPerennial(lines, model)
            if event == 'cutting':
                _repeat(perennial.cut, count, model); perennial.ncut = count
            else:
                _repeat(perennial.graze, count, model); perennial.ncycle = count
            model.years[0].data.perennial = perennial
        model.setroot()
        source = tmp_path / f'{event}-{count}.man'
        source.write_text(canonical_management(model))
        if count > maximum:
            with pytest.raises(SingleInputError):
                read_uploaded_management(source)
            continue
        accepted = read_uploaded_management(source)
        combined = tmp_path / 'combined.man'
        ManagementMultipleOfeSynth([accepted, accepted], deduplicate_scenarios=True).write(str(combined))
        assert read_uploaded_management(combined, max_ofes=32).nofe == 2


@pytest.mark.parametrize('count', [1000, 1001])
def test_management_simulation_year_boundary(tmp_path, count):
    model = read_uploaded_management(MAN)
    _repeat(model.man.loops[0].years, count, model)
    source = tmp_path / 'years.man'
    source.write_text(canonical_management(model))
    if count == 1001:
        with pytest.raises(SingleInputError):
            read_uploaded_management(source)
    else:
        assert read_uploaded_management(source).sim_years == count


@pytest.mark.parametrize('count', [32, 33])
def test_management_combined_ofe_boundary(tmp_path, count):
    from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
    source = read_uploaded_management(MAN)
    combined = tmp_path / 'combined.man'
    ManagementMultipleOfeSynth([source] * count, deduplicate_scenarios=True).write(str(combined))
    if count == 33:
        with pytest.raises(SingleInputError):
            read_uploaded_management(combined, max_ofes=32)
    else:
        assert read_uploaded_management(combined, max_ofes=32).nofe == count


@pytest.mark.parametrize('count', [10, 11])
def test_soil_horizon_boundary(count):
    import shlex
    lines = [line for line in decode_source(SOL.read_bytes()).splitlines() if line and not line.startswith('#')]
    header = shlex.split(lines[3]); header[2] = str(count)
    layer = lines[4].split()
    horizons = []
    for index in range(count):
        fields = layer.copy(); fields[0] = str((index + 1) * 100)
        horizons.append(' '.join(fields))
    text = '\n'.join(lines[:3] + [shlex.join(header)] + horizons + [lines[-1]]) + '\n'
    if count == 11:
        with pytest.raises(SingleInputError): validate_soil_text(text)
    else:
        validate_soil_text(text)


@pytest.mark.parametrize('count', [1000, 1001])
def test_management_rotation_boundary(tmp_path, count):
    model = read_uploaded_management(MAN)
    text = canonical_management(model)
    text = text.replace('1 # sim_years', '1000 # sim_years', 1)
    text = text.replace('1 # number of times the rotation is repeated', f'{count} # number of times the rotation is repeated', 1)
    prefix, schedule = text.split('1 # number of years in a single rotation\n', 1)
    source = tmp_path / 'rotations.man'
    source.write_text(prefix + '1 # number of years in a single rotation\n' + schedule * count)
    if count == 1001:
        with pytest.raises(SingleInputError): read_uploaded_management(source)
    else:
        accepted = read_uploaded_management(source)
        assert accepted.man.nrots == count
        source.write_text(canonical_management(accepted))
        assert read_uploaded_management(source).sim_years == count


def test_management_years_per_rotation_rejects_max_plus_one(tmp_path):
    model = read_uploaded_management(MAN)
    _repeat(model.man.loops[0].years, 1001, model)
    model.sim_years = 1000  # Valid outer bound; reject the inner 1001-year count.
    source = tmp_path / 'rotation-years.man'
    source.write_text(str(model))
    with pytest.raises(SingleInputError): read_uploaded_management(source)


@pytest.mark.parametrize('count', [32, 33])
def test_soil_combined_ofe_boundary(tmp_path, count):
    from wepppy.wepp.soils.utils.multi_ofe import SoilMultipleOfeSynth
    combined = tmp_path / 'combined.sol'
    SoilMultipleOfeSynth([str(SOL)] * count).write(str(combined))
    if count == 33:
        with pytest.raises(SingleInputError): validate_soil_text(combined.read_text(), max_ofes=32)
    else:
        validate_soil_text(combined.read_text(), max_ofes=32)
    with pytest.raises(SingleInputError): validate_soil_text(combined.read_text())
