"""Generated soil boundary contract: physical preservation and publication safety."""
from copy import deepcopy

import pytest

from wepppy.wepp.soils.horizon_boundary import ensure_200mm_boundary
from wepppy.wepp.soils.utils import SoilMultipleOfeSynth, WeppSoilUtil

pytestmark = pytest.mark.unit


def soil_text(version=7778, depths=(150, 400), count=1):
    lines = [str(version), '# retain provenance']
    if version >= 95.3:
        lines.append('Any comments:')
    lines.append(f'{count} 0')
    for ofe in range(count):
        if version>9000:lines.append("0 'forest' 'sand loam' 1.5 0.3" if version<9003 else "0 'forest' 300 'sand loam' -9999")
        lines.append(f"'Soil {ofe}' 'sand loam' {len(depths)} 0.16 0.75 400000 0.00008 2" + (' 8.1' if version<7777 else ''))
        for i,depth in enumerate(depths):
            rest=('67.9 12.5 2.5 15 48' if version<7777 else
                  f"1.4 {100.8 if i==0 else 9.72} "+('10 ' if version>=7778 else '')+'0.314 0.198 35.4 31 2.5 15 68.5')
            if version>=9002:rest+=' 0.0123456789 0.45 0.0012 1.4 7.654321 0.13 0.30'
            lines.append(f'  {depth}  {rest}')
        if version>=2006:lines.append('1 10000 0.01')
    return '\n'.join(lines)+'\n'


def meaningful(text):
    return [s for s in text.splitlines() if s.strip() and not s.startswith('#')]


@pytest.mark.parametrize('version',[94.1,95.1,95.3,97.3,97.5,98.4,2006.2,7777,7778,9001,9002,9003,9005])
@pytest.mark.parametrize('count',[1,3])
def test_every_ofe_copies_crossing_material_verbatim(version,count):
    source=soil_text(version,count=count)
    result=ensure_200mm_boundary(source)
    assert ensure_200mm_boundary(result)==result
    original_layers=[s for s in source.splitlines() if s.startswith('  ')]
    added=[s for s in result.splitlines() if s.startswith('  200.0 ')]
    assert len(added)==count
    assert all(s.split()[1:]==original_layers[1].split()[1:] for s in added)
    for line in original_layers:assert line in result.splitlines()
    assert result.count('1 10000 0.01')==source.count('1 10000 0.01')
    assert len(result.splitlines())==len(source.splitlines())+count
    assert all(f"'Soil {i}' 'sand loam' 3 " in result for i in range(count))


@pytest.mark.parametrize('depths',[(100,200,400),(200,400),(100,180),(200,)])
def test_existing_boundaries_and_shallow_profiles_are_byte_identical(depths):
    text=soil_text(depths=depths).replace('\n','\r\n')
    assert ensure_200mm_boundary(text)==text


def test_first_horizon_split_preserves_final_depth_and_missing_final_newline():
    source=soil_text(98.4,depths=(400,)).rstrip('\n')
    result=ensure_200mm_boundary(source)
    assert result.endswith(source.splitlines()[-1])
    assert "'sand loam' 2 " in result
    assert '  200.0 ' in result


@pytest.mark.parametrize('depths',[(150,float('nan')),(150,100),(0,400)])
def test_invalid_depths_fail(depths):
    with pytest.raises(ValueError,match='depth'):
        ensure_200mm_boundary(soil_text(depths=depths))


def test_required_eleventh_layer_fails_before_output_is_opened(tmp_path):
    source=tmp_path/'source.sol';source.write_text(soil_text(depths=(150,300,400,500,600,700,800,900,1000,1100)))
    dest=tmp_path/'output.sol';dest.write_text('prior successful artifact')
    with pytest.raises(ValueError,match='10-layer limit'):
        WeppSoilUtil(str(source)).write(str(dest))
    assert dest.read_text()=='prior successful artifact'
    with pytest.raises(ValueError,match='10-layer limit'):
        SoilMultipleOfeSynth([str(source)]).write(str(dest))
    assert dest.read_text()=='prior successful artifact'


def test_serialization_preserves_source_object_and_upload_topology(tmp_path):
    source=tmp_path/'source.sol';source.write_text(soil_text())
    generated=WeppSoilUtil(str(source));before=deepcopy(generated.obj)
    dest=tmp_path/'generated.sol';generated.write(str(dest))
    assert generated.obj==before
    assert [h['solthk'] for h in WeppSoilUtil(str(dest)).obj['ofes'][0]['horizons']]==[150,200,400]
    uploaded=WeppSoilUtil(str(source),preserve_input_format=True)
    upload_dest=tmp_path/'uploaded.sol';uploaded.write(str(upload_dest))
    assert [h['solthk'] for h in WeppSoilUtil(str(upload_dest),preserve_input_format=True).obj['ofes'][0]['horizons']]==[150,400]
    combined=tmp_path/'combined.sol'
    SoilMultipleOfeSynth([str(source)]*2).write(str(combined),preserve_input_format=True)
    assert all(o['nsl']==2 for o in WeppSoilUtil(str(combined),preserve_input_format=True).obj['ofes'])
    SoilMultipleOfeSynth([str(source)]*2).write(str(combined))
    assert all(o['nsl']==3 for o in WeppSoilUtil(str(combined)).obj['ofes'])


def test_malformed_counts_do_not_silently_reinterpret_extra_horizons():
    source=soil_text().replace("'sand loam' 2 ","'sand loam' 1 ")
    with pytest.raises(ValueError,match='Trailing soil records'):
        ensure_200mm_boundary(source)


@pytest.mark.parametrize('conversion', ['to_7778disturbed', 'to9002'])
def test_disturbed_insertion_cannot_bypass_native_capacity(tmp_path, conversion):
    source = tmp_path / 'source.sol'
    source.write_text(soil_text(depths=(150,300,400,500,600,700,800,900,1000,1100)))
    soil = WeppSoilUtil(str(source))
    converted = getattr(soil, conversion)({})
    destination = tmp_path / 'prepared.sol'
    destination.write_text('prior successful artifact')
    with pytest.raises(ValueError, match='10-layer limit'):
        converted.write(str(destination))
    assert destination.read_text() == 'prior successful artifact'
