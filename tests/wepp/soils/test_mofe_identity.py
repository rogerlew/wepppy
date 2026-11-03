from copy import deepcopy
from pathlib import Path

import pytest

from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture_enum

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('reverse', [False, True])
def test_9005_texture_is_per_ofe_in_real_serializers(tmp_path, reverse):
    source = (Path(__file__).resolve().parents[2] / 'wepp_runner/fixtures/hillslope_smoke/runs/p1.sol')
    soil = WeppSoilUtil(str(source)).to_over9000(replacements={}, version=9005)
    second = deepcopy(soil.obj['ofes'][0])
    soil.obj['ofes'].append(second)
    for ofe, (clay, sand) in zip(soil.obj['ofes'], [(10.0, 80.0), (40.0, 20.0)]):
        ofe['horizons'][0]['clay'] = clay
        ofe['horizons'][0]['sand'] = sand
    if reverse:
        soil.obj['ofes'].reverse()
    soil.obj['ntemp'] = 2
    expected = [simple_texture_enum(clay=ofe['horizons'][0]['clay'], sand=ofe['horizons'][0]['sand']) for ofe in soil.obj['ofes']]
    path = tmp_path / 'p1.sol'
    soil.write(str(path))
    parsed = WeppSoilUtil(str(path))
    assert [int(ofe['texid_enum']) for ofe in parsed.obj['ofes']] == expected
    debug = repr(soil)
    assert [int(line.split('texid_enum:')[1].split()[0]) for line in debug.splitlines() if 'texid_enum:' in line] == expected


def test_multi_ofe_source_cannot_be_one_stack_member(tmp_path):
    from wepppy.wepp.soils.utils.multi_ofe import SoilMultipleOfeSynth
    source = str((Path(__file__).resolve().parents[2] / 'wepp_runner/fixtures/hillslope_smoke/runs/p1.sol'))
    stacked = tmp_path / 'two.sol'
    SoilMultipleOfeSynth([source, source]).write(str(stacked))
    assert len(WeppSoilUtil(str(stacked)).obj['ofes']) == 2
    output = tmp_path / 'bad.sol'
    with pytest.raises(ValueError, match='exactly one OFE'):
        SoilMultipleOfeSynth([str(stacked)]).write(str(output))
    assert not output.exists()
