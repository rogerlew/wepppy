from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.wepp as wepp_module
from wepppy.nodb.core.climate import ClimateMode
from wepppy.nodb.core.wepp_run_service import WeppRunService

pytestmark = pytest.mark.unit


@contextmanager
def _noop_timed(*_args, **_kwargs):
    yield


class _DummyTranslator:
    def wepp(self, top: int) -> int:
        return top


class _DummyWatershed:
    def __init__(self, topaz_ids: list[str]) -> None:
        self._subs_summary = topaz_ids
        self.sub_n = len(topaz_ids)

    def translator_factory(self) -> _DummyTranslator:
        return _DummyTranslator()


def _build_landuse(topaz_ids: list[str], disturbed_class: str) -> SimpleNamespace:
    domlc_d: dict[str, str] = {}
    managements: dict[str, SimpleNamespace] = {}
    for topaz_id in topaz_ids:
        dom = f"dom-{topaz_id}"
        domlc_d[topaz_id] = dom
        managements[dom] = SimpleNamespace(disturbed_class=disturbed_class)
    return SimpleNamespace(domlc_d=domlc_d, managements=managements)


def test_run_hillslopes_keeps_configured_bin_for_agriculture_crops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topaz_ids = ["1271", "3507"]
    landuse = _build_landuse(topaz_ids, disturbed_class="agriculture crops")
    climate = SimpleNamespace(climate_mode=ClimateMode.Observed, ss_batch_storms=[])
    wepp = SimpleNamespace(
        class_name="Wepp",
        logger=logging.getLogger("tests.nodb.wepp_run_service.hillslopes"),
        watershed_instance=_DummyWatershed(topaz_ids),
        climate_instance=climate,
        landuse_instance=landuse,
        runs_dir=str(tmp_path / "runs"),
        wepp_bin="wepp_260421b",
        wd=str(tmp_path),
    )

    captured_bins: list[str | None] = []

    def _fake_run_hillslope(**kwargs):
        captured_bins.append(kwargs["wepp_bin"])
        return True, kwargs["wepp_id"], 0.01

    monkeypatch.setattr("wepppy.nodb.core.wepp_run_service.run_hillslope", _fake_run_hillslope)
    monkeypatch.setattr(
        wepp_module.RedisPrep,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(FileNotFoundError()),
    )

    WeppRunService().run_hillslopes(wepp)

    assert captured_bins == ["wepp_260421b", "wepp_260421b"]


def test_run_hillslopes_ss_batch_keeps_configured_bin_for_agriculture_crops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topaz_ids = ["1271", "3507"]
    landuse = _build_landuse(topaz_ids, disturbed_class="agriculture crops")
    climate = SimpleNamespace(
        climate_mode=ClimateMode.SingleStormBatch,
        ss_batch_storms=[{"ss_batch_id": "ss1"}, {"ss_batch_id": "ss2"}],
    )
    wepp = SimpleNamespace(
        class_name="Wepp",
        logger=logging.getLogger("tests.nodb.wepp_run_service.hillslopes_ss_batch"),
        watershed_instance=_DummyWatershed(topaz_ids),
        climate_instance=climate,
        landuse_instance=landuse,
        runs_dir=str(tmp_path / "runs"),
        wepp_bin="wepp_260421b",
        wd=str(tmp_path),
    )

    captured_bins: list[str | None] = []

    def _fake_run_ss_batch_hillslope(**kwargs):
        captured_bins.append(kwargs["wepp_bin"])
        return True, kwargs["wepp_id"], 0.01

    monkeypatch.setattr(
        "wepppy.nodb.core.wepp_run_service.run_ss_batch_hillslope",
        _fake_run_ss_batch_hillslope,
    )
    monkeypatch.setattr(
        wepp_module.RedisPrep,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(FileNotFoundError()),
    )

    WeppRunService().run_hillslopes(wepp)

    assert captured_bins == [
        "wepp_260421b",
        "wepp_260421b",
        "wepp_260421b",
        "wepp_260421b",
    ]


def test_run_watershed_does_not_rewrite_wepp_50k_bin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "output"
    interchange_dir = tmp_path / "interchange"
    runs_dir.mkdir()
    output_dir.mkdir()
    interchange_dir.mkdir()

    climate = SimpleNamespace(
        climate_mode=ClimateMode.Observed,
        is_single_storm=False,
        calendar_start_year=2024,
        getInstance=lambda _wd: climate,
    )
    wepp = SimpleNamespace(
        logger=logging.getLogger("tests.nodb.wepp_run_service.watershed"),
        run_wepp_watershed=True,
        wd=str(tmp_path),
        climate_instance=climate,
        wepp_bin="wepp_50k_ifx",
        output_dir=str(output_dir),
        runs_dir=str(runs_dir),
        timed=_noop_timed,
        _status_channel=None,
        is_omni_contrasts_run=True,
        _contrast_output_options={},
        delete_after_interchange=False,
        wepp_interchange_dir=str(interchange_dir),
    )

    captured: dict[str, str | None] = {}

    def _fake_run_watershed(runs_dir: str, *, wepp_bin: str | None, status_channel) -> bool:
        captured["runs_dir"] = runs_dir
        captured["wepp_bin"] = wepp_bin
        return True

    monkeypatch.setattr(wepp_module, "run_watershed", _fake_run_watershed)
    monkeypatch.setattr(
        wepp_module.RedisPrep,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(FileNotFoundError()),
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.watershed_interchange.run_wepp_watershed_interchange",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.interchange_documentation.generate_interchange_documentation",
        lambda *_args, **_kwargs: None,
    )

    WeppRunService().run_watershed(wepp)

    assert captured["runs_dir"] == str(runs_dir)
    assert captured["wepp_bin"] == "wepp_50k_ifx"
