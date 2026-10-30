from __future__ import annotations

from types import SimpleNamespace

import pytest

from wepppy.soils.ssurgo.ssurgo import WeppSoil
from wepppy.wepp.soils.utils import WeppSoilUtil

pytestmark = pytest.mark.unit


def _fake_horizon(texture: str = "GRX-COS") -> SimpleNamespace:
    return SimpleNamespace(
        texture=texture,
        interrill=3669290.0,
        rill=0.0162,
        shear=2.6458,
        hzdepb_r=5.0,
        dbthirdbar_r=1.53,
        ksat_r=423.0,
        conductivity=1522.8,
        anisotropy=10.0,
        field_cap=0.05,
        wilt_pt=0.016,
        sandtotal_r=92.1,
        claytotal_r=4.0,
        om_r=0.6,
        cec7_r=2.3,
        smr=84.0,
    )


def _fake_wepp_soil(muname: str) -> WeppSoil:
    soil = WeppSoil.__new__(WeppSoil)
    soil.mukey = 0
    soil.log = []
    soil.description = "# test soil"
    soil.num_ofes = 1
    soil.ksflag = 0
    soil.is_urban = False
    soil.is_water = False
    soil.initial_sat = 0.75
    soil.majorComponent = SimpleNamespace(muname=muname, albedodry_r=0.16)
    soil.horizons = [_fake_horizon()]
    soil.horizons_mask = [1]
    soil.num_layers = 1
    soil.res_lyr_i = None
    soil.res_lyr_ksat = None
    return soil


@pytest.mark.parametrize(
    "version,build_contents",
    [
        ("7778", lambda soil: soil.build_file_contents()),
        ("2006.2", lambda soil: soil.build_file_contents_v2006_2()),
    ],
)
def test_ssurgo_sol_generation_quotes_muname_apostrophes_for_roundtrip(
    tmp_path,
    version: str,
    build_contents,
) -> None:
    muname = "Kana'a-Cinder land complex, 1 to 15 percent slopes"
    sol_text = build_contents(_fake_wepp_soil(muname))

    assert f'"{muname}"' in sol_text
    assert f"'{muname}'" not in sol_text

    sol_path = tmp_path / f"apostrophe-{version}.sol"
    sol_path.write_text(sol_text)

    parsed = WeppSoilUtil(str(sol_path))
    assert parsed.obj["ofes"][0]["slid"] == muname


@pytest.mark.parametrize('legacy', [False, True])
def test_ssurgo_generated_crossing_horizon_preserves_material(tmp_path, legacy):
    soil = _fake_wepp_soil('Example soil')
    soil.horizons[0].hzdepb_r = 35.0
    text = (soil.build_file_contents_v2006_2() if legacy
            else soil.build_file_contents())
    path = tmp_path / 'generated.sol'
    path.write_text(text)
    parsed = WeppSoilUtil(str(path)).obj['ofes'][0]
    assert parsed['nsl'] == 2
    assert [h['solthk'] for h in parsed['horizons']] == [200, 350 if legacy else 400]
    assert {k: v for k, v in parsed['horizons'][0].items() if k != 'solthk'} == {
        k: v for k, v in parsed['horizons'][1].items() if k != 'solthk'}
    assert soil.num_layers == 1


@pytest.mark.parametrize('method,expected_depths', [
    ('_build_urban', [200, 210]),
    ('_build_water', [200, 210]),
    ('_build_urban_v2006_2', [200, 210]),
    ('_build_water_v2006_2', []),
])
def test_canned_ssurgo_profiles_keep_their_material_and_total_depth(method, expected_depths):
    import shlex
    from wepppy.wepp.soils.horizon_boundary import ensure_200mm_boundary
    text = getattr(_fake_wepp_soil('Canned soil'), method)()
    records = [line for line in text.splitlines() if line.strip() and not line.startswith('#')]
    count = int(shlex.split(records[3])[2])
    horizons = [line.split() for line in records[4:4 + count]]
    assert [float(row[0]) for row in horizons] == expected_depths
    assert len(records) == 5 + count
    if horizons:
        assert horizons[0][1:] == horizons[1][1:]
    assert ensure_200mm_boundary(text) == text
