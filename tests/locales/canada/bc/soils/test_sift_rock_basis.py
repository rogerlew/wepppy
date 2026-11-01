"""BC source volume must reach native soil fields as density-based dry mass."""
import json
import math

import pytest

from wepppy.locales.canada.bc.soils.sift.sift import SIFT, SiftHorizon
from wepppy.wepp.soils.utils import WeppSoilUtil

pytestmark = pytest.mark.unit


def source_layers(volume=20.0, density=1.3):
    layers = {}
    for index, depth in enumerate([5, 15, 30, 60, 100, 200]):
        layers[str(index)] = dict(
            SOILNAME='synthetic-rock', SOIL_CODE='RCK', LAYER_NO=index+1,
            HZN_MAS='B', LU='F', UDEPTH=0 if index == 0 else [5, 15, 30, 60, 100][index-1],
            LDEPTH=depth, TSAND=50., TCLAY=20., TSILT=30., VFSAND=0.,
            ORGCARB=1., WOOD=0., COFRAG=volume, KSAT=10., BD=density,
            CEC=10., KP33=20., KP1500=10.)
    return layers


def build_fixture(outdir, volume=20.0, density=1.3, *, water=False):
    """Run actual construction, Rosetta and file writer from declared source records."""
    records = {'rock': {'Shape_Area (Real)': 100., 'SOILSYM_1 (String)': 'RCK',
        'SOILNAME_1 (String)': 'synthetic-rock', 'SOILSYM_2 (String)': None,
        'SOILNAME_2 (String)': None, 'SOILSYM_3 (String)': None,
        'SOILNAME_3 (String)': None, 'Layers': {'RCK': source_layers(volume, density)}}}
    if water:
        for layer in records['rock']['Layers']['RCK'].values():
            layer['SOILNAME'] = 'water'
    return SIFT()._build_wepp_soils(records, str(outdir))


@pytest.mark.parametrize('volume', [0., 5., 20., 80., 100.])
@pytest.mark.parametrize('density', [.8, 1.3, 2.])
def test_volume_uses_explicit_mass_inventory(volume, density):
    h = SiftHorizon(source_layers(volume, density)['0'])
    rock_mass = volume*2.65
    fine_mass = (100-volume)*density
    assert h.rfg == pytest.approx(100*rock_mass/(rock_mass+fine_mass))


@pytest.mark.parametrize('volume,density', [(None,1.3),(-9,1.3),(20,None),(20,-9),(0,None),(0,-9),(None,None),(-9,-9),(None,float('nan')),(float('nan'),None)])
def test_missing_basis_stays_unavailable(volume, density):
    assert SiftHorizon(source_layers(volume, density)['0']).rfg is None


@pytest.mark.parametrize('volume,density', [(float('nan'),1.3),(float('inf'),1.3),(-1,1.3),(101,1.3),(20,0),(20,-1),(20,float('nan')),(20,float('inf'))])
def test_invalid_present_basis_fails(volume, density):
    with pytest.raises(ValueError):
        _ = SiftHorizon(source_layers(volume, density)['0']).rfg


@pytest.mark.parametrize('volume', [0.,20.,80.])
def test_actual_writer_preserves_raw_and_emits_mass(tmp_path, volume):
    stats = build_fixture(tmp_path, volume)
    assert stats['valid_cnt'] == 1
    raw = json.loads((tmp_path/'rock.json').read_text())
    assert raw['Layers']['RCK']['0']['COFRAG'] == volume
    parsed = WeppSoilUtil(str(tmp_path/'rock.sol'))
    assert parsed.obj['ofes'][0]['sat'] == .75
    text = (tmp_path/'rock.sol').read_text()
    rows = [list(map(float,line.split())) for line in text.splitlines()
            if not line.startswith('#') and len(line.split()) == 11]
    assert [r[0] for r in rows] == [50,150,200,300,600,1000,2000]
    mass = 100*(volume*2.65)/(volume*2.65+(100-volume)*1.3)
    assert all(r[-1] == float(f'{mass:.1f}') for r in rows)
    assert all(math.isfinite(v) for row in rows for v in row)
    assert '# Rock basis:' in text
    assert 'COFRAG volume%; RFG dry mass%; rock density 2.65 g/cm3' in text


@pytest.mark.parametrize('volume,density', [(None,1.3),(20,None)])
def test_missing_source_horizons_do_not_publish_soil(tmp_path, volume, density):
    stats = build_fixture(tmp_path, volume, density)
    assert stats['valid_cnt'] == 0
    assert (tmp_path/'rock.json').exists()
    assert not (tmp_path/'rock.sol').exists()


def test_invalid_source_retains_json_without_soil(tmp_path):
    with pytest.raises(ValueError):
        build_fixture(tmp_path, 101)
    assert (tmp_path/'rock.json').exists()
    assert not (tmp_path/'rock.sol').exists()


@pytest.mark.parametrize('volume,density', [(101,0),(None,None),(-9,-9)])
def test_open_water_keeps_canned_writer(tmp_path, volume, density):
    stats = build_fixture(tmp_path, volume, density, water=True)
    assert stats['valid_cnt'] == 1
    text = (tmp_path/'rock.sol').read_text()
    assert "'water_7778_2'" in text
    rows = [list(map(float,line.split())) for line in text.splitlines()
            if not line.startswith('#') and len(line.split()) == 11]
    assert [r[0] for r in rows] == [200,210]
    assert all(r[-1] == 0 for r in rows)


def test_source_summary_keeps_multiline_values_commented():
    layers = source_layers()
    layers['0']['SOIL_CODE'] = 'first\nsecond'
    soil = SIFT()._build_horizons(layers)
    summary = soil.summary()
    assert 'first\n# second' in summary
    assert all(line.startswith('# ') for line in summary.splitlines())
