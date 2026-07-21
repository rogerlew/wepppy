from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

import wepppy.soils.ssurgo.ssurgo as ssurgo_module
from rosetta import Rosetta2, Rosetta3
from wepppy.soils.ssurgo.ssurgo import Horizon, WeppSoil

pytestmark = pytest.mark.unit

AFFECTED_MUKEYS = (1385512, 2711215, 78280)


class _FakeRosetta3:
    def predict_kwargs(self, **_kwargs):
        return {
            "theta_r": 0.02,
            "theta_s": 0.44,
            "alpha": 0.018,
            "npar": 1.45,
            "ks": 12.0,
            "wp": 0.12,
            "fc": 0.31,
        }


class _InvalidRosetta3:
    def predict_kwargs(self, **_kwargs):
        return {
            "theta_r": 0.02,
            "theta_s": 0.44,
            "alpha": 0.018,
            "npar": 1.45,
            "ks": 12.0,
            "wp": 0.42,
            "fc": 0.31,
        }


def _affected_layer(mukey: int) -> dict[str, object]:
    return {
        "cokey": mukey * 10,
        "chkey": mukey * 100 + 1,
        "hzname": "A",
        "hzdepb_r": 20.0,
        "hzdept_r": 0.0,
        "hzthk_r": 20.0,
        "dbthirdbar_r": 1.52,
        "ksat_r": 12.0,
        "sandtotal_r": 55.0,
        "claytotal_r": 20.0,
        "om_r": 2.0,
        "cec7_r": 10.0,
        "fraggt10_r": 0.0,
        "frag3to10_r": 0.0,
        "desgnmaster": "A",
        "sieveno10_r": 85.0,
        "wthirdbar_r": -9.9,
        "wfifteenbar_r": float("nan"),
        "sandvf_r": 5.0,
        "ll_r": None,
        "texture": "loam",
        "reskind": None,
        "fragvol_r": 0.0,
    }


def _soil_for_horizon(mukey: int, horizon) -> WeppSoil:
    soil = WeppSoil.__new__(WeppSoil)
    soil.log = []
    soil.mukey = mukey
    soil.description = f"# affected mukey {mukey}"
    soil.num_ofes = 1
    soil.ksflag = 0
    soil.is_urban = False
    soil.is_water = False
    soil.initial_sat = 0.75
    soil.majorComponent = SimpleNamespace(
        muname=f"Affected mukey {mukey}",
        albedodry_r=0.16,
    )
    soil.horizons = [horizon]
    soil.horizons_mask = [1]
    soil.num_layers = 1
    soil.res_lyr_i = None
    soil.res_lyr_ksat = None
    return soil


@pytest.mark.parametrize("mukey", AFFECTED_MUKEYS)
def test_affected_mukey_horizon_sanitizes_invalid_fc_wp_before_7778_write(
    monkeypatch: pytest.MonkeyPatch,
    mukey: int,
) -> None:
    monkeypatch.setattr(ssurgo_module, "Rosetta3", _FakeRosetta3)

    horizon = ssurgo_module.Horizon(
        _affected_layer(mukey)["chkey"],
        _affected_layer(mukey),
        defaults={},
    )

    assert horizon.field_cap == pytest.approx(0.31)
    assert horizon.wilt_pt == pytest.approx(0.12)
    assert math.isfinite(horizon.field_cap)
    assert math.isfinite(horizon.wilt_pt)
    assert any("field_cap/wilt_pt sanitized" in note for note in horizon.horizon_build_notes)

    sol_text = _soil_for_horizon(mukey, horizon).build_file_contents()
    assert "nan" not in sol_text.lower()
    assert "-9.9" not in sol_text

    horizon_line = next(line for line in sol_text.splitlines() if line.startswith("\t"))
    fields = horizon_line.split()
    assert float(fields[4]) == pytest.approx(0.31)
    assert float(fields[5]) == pytest.approx(0.12)


def test_affected_mukey_horizon_rejects_invalid_rosetta_fc_wp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ssurgo_module, "Rosetta3", _InvalidRosetta3)

    with pytest.raises(ValueError, match="Invalid SSURGO-derived fc/wp"):
        ssurgo_module.Horizon(
            _affected_layer(1385512)["chkey"],
            _affected_layer(1385512),
            defaults={},
        )


def test_horizon_derives_rosetta_silt_instead_of_using_very_fine_sand() -> None:
    layer = _affected_layer(1385512)
    expected = Rosetta3().predict_kwargs(sand=55.0, silt=25.0, clay=20.0, bd=1.52)

    horizon = Horizon(layer["chkey"], layer, defaults={})

    assert horizon.field_cap == pytest.approx(expected["fc"])
    assert horizon.wilt_pt == pytest.approx(expected["wp"])


def test_horizon_defaults_derive_rosetta_silt_for_missing_ssurgo_texture() -> None:
    layer = _affected_layer(1385512)
    layer.update(
        sandtotal_r=None,
        claytotal_r=None,
        sandvf_r=None,
        dbthirdbar_r=None,
        wthirdbar_r=None,
        wfifteenbar_r=None,
    )
    defaults = {
        "sandtotal_r": 66.8,
        "claytotal_r": 7.0,
        "sandvf_r": 10.0,
        "smr": 55.5,
    }
    expected = Rosetta2().predict_kwargs(sand=66.8, silt=26.2, clay=7.0)

    horizon = Horizon(layer["chkey"], layer, defaults=defaults)

    assert horizon.field_cap == pytest.approx(expected["fc"])
    assert horizon.wilt_pt == pytest.approx(expected["wp"])
