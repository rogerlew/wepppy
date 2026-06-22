from __future__ import annotations

from pathlib import Path

import pytest

import wepppy.soils.ssurgo.ssurgo as ssurgo_module
from wepppy.soils.ssurgo import SurgoSoilCollection

pytestmark = pytest.mark.unit

FAIRPOINT_MUKEYS = {3294459, 3294460, 3294461}


def _major_cokey(mukey: int) -> int:
    return mukey * 10 + 1


def _minor_cokey(mukey: int) -> int:
    return mukey * 10 + 2


def _horizon_chkey(cokey: int, horizon_index: int) -> int:
    return cokey * 10 + horizon_index


def _component_row(
    mukey: int,
    cokey: int,
    compname: str,
    comppct_r: float,
    muname: str,
) -> tuple[object, ...]:
    return (
        mukey,
        cokey,
        compname,
        comppct_r,
        0.15,
        0.0,
        0.0,
        muname,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    )


def _horizon_row(
    cokey: int,
    chkey: int,
    hzname: str,
    hzdept_r: float,
    hzdepb_r: float,
    dbthirdbar_r: float,
    ksat_r: float,
    sandtotal_r: float,
    claytotal_r: float,
    om_r: float,
    cec7_r: float,
    wthirdbar_r: float,
    wfifteenbar_r: float,
    sandvf_r: float,
) -> tuple[object, ...]:
    return (
        cokey,
        chkey,
        hzname,
        hzdepb_r,
        hzdept_r,
        hzdepb_r - hzdept_r,
        dbthirdbar_r,
        ksat_r,
        sandtotal_r,
        claytotal_r,
        om_r,
        cec7_r,
        0.08,
        0.0,
        0.0,
        hzname[:1],
        85.0,
        wthirdbar_r,
        wfifteenbar_r,
        sandvf_r,
        None,
    )


def _install_reclaimed_fairpoint_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    def fetch_components(keys: set[int]) -> list[tuple[object, ...]]:
        rows: list[tuple[object, ...]] = []
        for mukey in sorted(keys):
            assert mukey in FAIRPOINT_MUKEYS
            rows.append(
                _component_row(
                    mukey,
                    _major_cokey(mukey),
                    "Fairpoint",
                    95.0,
                    "Fairpoint reclaimed mine land",
                )
            )
            rows.append(
                _component_row(
                    mukey,
                    _minor_cokey(mukey),
                    "Bethesda",
                    5.0,
                    "Bethesda silt loam",
                )
            )
        return rows

    def fetch_chorizon(keys: set[int]) -> list[tuple[object, ...]]:
        rows: list[tuple[object, ...]] = []
        for mukey in sorted(FAIRPOINT_MUKEYS):
            major_cokey = _major_cokey(mukey)
            minor_cokey = _minor_cokey(mukey)
            if major_cokey in keys:
                rows.extend(
                    [
                        _horizon_row(
                            major_cokey,
                            _horizon_chkey(major_cokey, 1),
                            "A",
                            0.0,
                            9.0,
                            1.76,
                            0.1,
                            17.0,
                            24.0,
                            1.0,
                            8.0,
                            24.0,
                            12.0,
                            2.0,
                        ),
                        _horizon_row(
                            major_cokey,
                            _horizon_chkey(major_cokey, 2),
                            "C",
                            9.0,
                            152.0,
                            1.86,
                            0.014,
                            26.6,
                            22.4,
                            0.5,
                            5.0,
                            18.0,
                            9.0,
                            3.0,
                        ),
                    ]
                )
            if minor_cokey in keys:
                rows.extend(
                    [
                        _horizon_row(
                            minor_cokey,
                            _horizon_chkey(minor_cokey, 1),
                            "A",
                            0.0,
                            14.0,
                            1.81,
                            0.1,
                            22.0,
                            22.0,
                            1.0,
                            7.0,
                            22.0,
                            11.0,
                            2.5,
                        ),
                        _horizon_row(
                            minor_cokey,
                            _horizon_chkey(minor_cokey, 2),
                            "C",
                            14.0,
                            203.0,
                            1.92,
                            0.014,
                            21.0,
                            28.0,
                            0.5,
                            5.0,
                            20.0,
                            10.0,
                            3.0,
                        ),
                    ]
                )
        return rows

    def fetch_corestrictions(keys: set[int]) -> list[tuple[object, ...]]:
        return [(cokey, "densic material") for cokey in sorted(keys)]

    def fetch_chfrags(keys: set[int]) -> list[tuple[object, ...]]:
        return [(chkey, 0.0) for chkey in sorted(keys)]

    def fetch_chtexturegrp(keys: set[int]) -> list[tuple[object, ...]]:
        return [(chkey, "silt loam") for chkey in sorted(keys)]

    monkeypatch.setattr(ssurgo_module, "_fetch_components", fetch_components)
    monkeypatch.setattr(ssurgo_module, "_fetch_chorizon", fetch_chorizon)
    monkeypatch.setattr(ssurgo_module, "_fetch_corestrictions", fetch_corestrictions)
    monkeypatch.setattr(ssurgo_module, "_fetch_chfrags", fetch_chfrags)
    monkeypatch.setattr(ssurgo_module, "_fetch_chtexturegrp", fetch_chtexturegrp)


def test_reclaimed_fairpoint_mukeys_build_valid_wepp_soils(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_reclaimed_fairpoint_fixture(monkeypatch)
    soils_dir = tmp_path / "soils"
    soils_dir.mkdir()

    collection = SurgoSoilCollection(
        sorted(FAIRPOINT_MUKEYS),
        cache_db_path=str(tmp_path / "ssurgo_tabular_cache.sqlite"),
    )
    try:
        collection.makeWeppSoils(max_workers=1)
        summaries = collection.writeWeppSoils(wd=str(soils_dir), write_logs=True)
    finally:
        collection._disconnect()

    assert set(collection.getValidWeppSoils()) == FAIRPOINT_MUKEYS
    assert set(summaries) == FAIRPOINT_MUKEYS
    for mukey in FAIRPOINT_MUKEYS:
        assert (soils_dir / f"{mukey}.sol").is_file()
        assert "Fairpoint reclaimed mine land" in summaries[mukey].desc


def test_first_restrictive_fairpoint_horizon_is_retained_as_wepp_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_reclaimed_fairpoint_fixture(monkeypatch)

    collection = SurgoSoilCollection(
        [3294459],
        cache_db_path=str(tmp_path / "ssurgo_tabular_cache.sqlite"),
    )
    try:
        collection.makeWeppSoils(max_workers=1, verbose=True)
        wepp_soil = collection.weppSoils[3294459]
    finally:
        collection._disconnect()

    assert wepp_soil.valid() is True
    assert wepp_soil.num_layers == 1
    assert wepp_soil.res_lyr_i == 1
    assert "Validity: no horizons" not in "\n".join(wepp_soil.log)


def test_invalid_low_ksat_horizon_does_not_trigger_zero_layer_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_reclaimed_fairpoint_fixture(monkeypatch)

    collection = SurgoSoilCollection(
        [3294459],
        cache_db_path=str(tmp_path / "ssurgo_tabular_cache.sqlite"),
    )
    try:
        collection.makeWeppSoils(max_workers=1)
        wepp_soil = collection.weppSoils[3294459]
    finally:
        collection._disconnect()

    wepp_soil.horizons_mask = [False, True]
    wepp_soil.res_lyr_i = None
    wepp_soil.res_lyr_ksat = None
    wepp_soil.num_layers = 0

    wepp_soil._analyze_restrictive_layer()

    assert wepp_soil.num_layers == 1
    assert wepp_soil.res_lyr_i is None
