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
