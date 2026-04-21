from __future__ import annotations

from typing import Any

import pytest

from wepppy.nodb.core.wepp_prep_service import WeppPrepService

pytestmark = pytest.mark.unit


class _DummyLogger:
    def info(self, _message: str) -> None:
        return None


class _DummyWatershed:
    def __init__(self) -> None:
        self.centroid = (-117.123, 46.987)

    def translator_factory(self) -> object:
        return object()


class _DummyWepp:
    def __init__(self, *, critical_shear: float, critical_shear_map: str | None) -> None:
        self.logger = _DummyLogger()
        self.watershed_instance = _DummyWatershed()
        self.channel_critical_shear_map = critical_shear_map
        self._channel_critical_shear = critical_shear
        self.run_tcr = False
        self.channel_chn_critical_shear: float | None = None
        self.channel_soils_critical_shear: float | None = None
        self.trigger_events: list[Any] = []

    @property
    def channel_critical_shear(self) -> float:
        return float(self._channel_critical_shear)

    def _prep_structure(self, _translator: object) -> None:
        return None

    def _prep_channel_slopes(self) -> None:
        return None

    def _prep_channel_chn(
        self,
        _translator: object,
        _erodibility: float | None,
        critical_shear: float | None,
        **_kwargs: object,
    ) -> None:
        self.channel_chn_critical_shear = critical_shear

    def _prep_impoundment(self) -> None:
        return None

    def _prep_channel_soils(
        self,
        _translator: object,
        _erodibility: float | None,
        critical_shear: float | None,
        _avke: float | None = None,
    ) -> None:
        self.channel_soils_critical_shear = critical_shear

    def _prep_channel_climate(self, _translator: object) -> None:
        return None

    def _prep_channel_input(self) -> None:
        return None

    def _prep_tc(self) -> None:
        return None

    def _prep_tcr(self) -> None:
        return None

    def _prep_watershed_managements(self, _translator: object) -> None:
        return None

    def _make_watershed_run(self, _translator: object) -> None:
        return None

    def trigger(self, event: Any) -> None:
        self.trigger_events.append(event)


class _DummyWeppPrepHillslopes:
    def __init__(self) -> None:
        self.class_name = "Wepp"
        self.logger = _DummyLogger()
        self.wd = "/tmp/test-wd"
        self.multi_ofe = True
        self.run_frost = False
        self.run_baseflow = False
        self.run_wepp_ui = False
        self.run_pmet = False
        self.run_snow = False

        self.watershed_instance = _DummyWatershed()
        self.multi_ofe_calls: list[tuple[object, int | None]] = []

    def _prep_multi_ofe(self, translator: object, max_workers: int | None = None) -> None:
        self.multi_ofe_calls.append((translator, max_workers))

    def _prep_climates(self, _translator: object) -> None:
        return None

    def _make_hillslope_runs(
        self,
        _translator: object,
        *,
        reveg: bool = False,
        man_relpath: str = "",
        cli_relpath: str = "",
        slp_relpath: str = "",
        sol_relpath: str = "",
    ) -> None:
        _ = (reveg, man_relpath, cli_relpath, slp_relpath, sol_relpath)
        return None

    def _remove_frost(self) -> None:
        return None

    def _check_and_set_phosphorus_map(self) -> None:
        return None

    def _prep_phosphorus(self) -> None:
        return None

    def _remove_baseflow(self) -> None:
        return None

    def _remove_wepp_ui(self) -> None:
        return None

    def _remove_pmet(self) -> None:
        return None

    def _remove_snow(self) -> None:
        return None


def test_prep_watershed_uses_critical_shear_map_when_no_user_override(monkeypatch: pytest.MonkeyPatch) -> None:
    service = WeppPrepService()
    wepp = _DummyWepp(critical_shear=19.0, critical_shear_map="/tmp/critical_shear.tif")

    calls: list[tuple[Any, ...]] = []

    class _FakeRasterDatasetInterpolator:
        def __init__(self, dataset_path: str) -> None:
            calls.append(("init", dataset_path))

        def get_location_info(self, lng: float, lat: float, method: str = "nearest") -> float:
            calls.append(("sample", lng, lat, method))
            return 77.7

    monkeypatch.setattr(
        "wepppy.nodb.core.wepp_prep_service.RasterDatasetInterpolator",
        _FakeRasterDatasetInterpolator,
    )

    service.prep_watershed(wepp)

    assert wepp.channel_chn_critical_shear == pytest.approx(77.7)
    assert wepp.channel_soils_critical_shear == pytest.approx(77.7)
    assert calls == [
        ("init", "/tmp/critical_shear.tif"),
        ("sample", -117.123, 46.987, "nearest"),
    ]


def test_prep_watershed_prefers_user_override_over_critical_shear_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WeppPrepService()
    wepp = _DummyWepp(critical_shear=55.5, critical_shear_map="/tmp/critical_shear.tif")
    wepp._channel_critical_shear_overridden = True

    class _FailingRasterDatasetInterpolator:
        def __init__(self, _dataset_path: str) -> None:
            raise AssertionError("critical shear map should not be sampled when override is set")

    monkeypatch.setattr(
        "wepppy.nodb.core.wepp_prep_service.RasterDatasetInterpolator",
        _FailingRasterDatasetInterpolator,
    )

    service.prep_watershed(wepp)

    assert wepp.channel_chn_critical_shear == pytest.approx(55.5)
    assert wepp.channel_soils_critical_shear == pytest.approx(55.5)


def test_prep_hillslopes_passes_max_workers_to_multi_ofe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WeppPrepService()
    wepp = _DummyWeppPrepHillslopes()

    monkeypatch.setattr(
        "wepppy.nodb.core.wepp.Disturbed.getInstance",
        classmethod(lambda _cls, _wd, allow_nonexistent=True: None),
    )

    service.prep_hillslopes(wepp, max_workers=7)

    assert len(wepp.multi_ofe_calls) == 1
    _translator, max_workers = wepp.multi_ofe_calls[0]
    assert max_workers == 7
