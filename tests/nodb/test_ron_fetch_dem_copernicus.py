from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.ron as ron_module
from wepppy.nodb.core.ron import Ron

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


class _DummyPrep:
    def timestamp(self, _task: object) -> None:
        return None


class _DummyRedisPrep:
    @staticmethod
    def getInstance(_wd: str) -> _DummyPrep:
        return _DummyPrep()


def _make_detached_ron(tmp_path: Path, dem_db: str) -> Ron:
    dem_dir = tmp_path / "dem"
    dem_dir.mkdir(parents=True, exist_ok=True)

    ron = object.__new__(Ron)
    ron.wd = str(tmp_path)
    ron._dem_db = dem_db
    ron._dem_is_vrt = False
    ron.config_get_str = lambda *_args, **_kwargs: dem_db
    ron._map = SimpleNamespace(
        extent=[-120.5, 38.5, -120.4, 38.6],
        cellsize=30.0,
    )

    logger = logging.getLogger(f"tests.ron.fetch_dem.copernicus.{tmp_path.name}")
    logger.handlers = []
    logger.addHandler(logging.NullHandler())
    ron.logger = logger
    return ron


def _patch_post_fetch_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ron_module, "RedisPrep", _DummyRedisPrep)
    monkeypatch.setattr(ron_module, "update_catalog_entry", lambda *_args, **_kwargs: None)


def test_fetch_dem_uses_copernicus_backend_when_scheme_is_copernicus(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path, dem_db="copernicus://dem_cop_30")
    _patch_post_fetch_dependencies(monkeypatch)

    calls: dict[str, object] = {}

    def _fake_copernicus_retrieve(
        extent: tuple[float, float, float, float],
        dst_fn: str,
        cellsize: float,
        dataset: str = "dem_cop_30",
        resample: str = "bilinear",
    ) -> None:
        calls["extent"] = extent
        calls["dataset"] = dataset
        calls["cellsize"] = cellsize
        calls["resample"] = resample
        Path(dst_fn).write_bytes(b"dem")

    monkeypatch.setattr(ron_module, "copernicus_retrieve", _fake_copernicus_retrieve)
    monkeypatch.setattr(
        ron_module,
        "opentopo_retrieve",
        lambda *_args, **_kwargs: pytest.fail("OpenTopography fallback should not run for successful Copernicus fetch."),
    )
    monkeypatch.setattr(
        ron_module,
        "wmesque_retrieve",
        lambda *_args, **_kwargs: pytest.fail("WMEsque should not run for copernicus:// DEM selection."),
    )

    ron.fetch_dem()

    assert calls["dataset"] == "copernicus://dem_cop_30"
    assert calls["resample"] == "bilinear"
    assert Path(ron.dem_fn).exists()


def test_fetch_dem_falls_back_to_opentopo_when_copernicus_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path, dem_db="copernicus://dem_cop_30")
    _patch_post_fetch_dependencies(monkeypatch)

    def _failing_copernicus(*_args, **_kwargs) -> None:
        raise ron_module.CopernicusRetryableError("copernicus unavailable")

    fallback_calls: list[str | None] = []

    def _fake_fetch_opentopo(self: Ron, dem_db_override: str | None = None) -> None:
        fallback_calls.append(dem_db_override)
        Path(self.dem_fn).write_bytes(b"dem")

    monkeypatch.setattr(ron_module, "copernicus_retrieve", _failing_copernicus)
    monkeypatch.setattr(Ron, "_fetch_opentopo_dem", _fake_fetch_opentopo)

    ron.fetch_dem()

    assert fallback_calls == ["opentopo://srtmgl1_e"]
    assert Path(ron.dem_fn).exists()


def test_fetch_dem_uses_env_override_for_copernicus_fallback_dataset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path, dem_db="copernicus://dem_cop_30")
    _patch_post_fetch_dependencies(monkeypatch)

    def _failing_copernicus(*_args, **_kwargs) -> None:
        raise ron_module.CopernicusRetryableError("copernicus unavailable")

    fallback_calls: list[str | None] = []

    def _fake_fetch_opentopo(self: Ron, dem_db_override: str | None = None) -> None:
        fallback_calls.append(dem_db_override)
        Path(self.dem_fn).write_bytes(b"dem")

    monkeypatch.setenv("COPERNICUS_OPENTOPO_FALLBACK_DATASET", "COP30")
    monkeypatch.setattr(ron_module, "copernicus_retrieve", _failing_copernicus)
    monkeypatch.setattr(Ron, "_fetch_opentopo_dem", _fake_fetch_opentopo)

    ron.fetch_dem()

    assert fallback_calls == ["opentopo://COP30"]


def test_fetch_dem_does_not_fallback_on_copernicus_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path, dem_db="copernicus://dem_cop_30")
    _patch_post_fetch_dependencies(monkeypatch)

    def _configuration_error(*_args, **_kwargs) -> None:
        raise ron_module.CopernicusConfigurationError("unsupported dataset")

    monkeypatch.setattr(
        ron_module,
        "copernicus_retrieve",
        _configuration_error,
    )
    monkeypatch.setattr(
        Ron,
        "_fetch_opentopo_dem",
        lambda *_args, **_kwargs: pytest.fail("OpenTopography fallback must not run on configuration errors."),
    )

    with pytest.raises(ron_module.CopernicusConfigurationError, match="unsupported dataset"):
        ron.fetch_dem()


def test_fetch_dem_raises_combined_error_when_fallback_also_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path, dem_db="copernicus://dem_cop_30")
    _patch_post_fetch_dependencies(monkeypatch)

    def _failing_copernicus(*_args, **_kwargs) -> None:
        raise ron_module.CopernicusRetryableError("copernicus unavailable")

    def _failing_opentopo(*_args, **_kwargs) -> None:
        raise RuntimeError("opentopo throttled")

    monkeypatch.setattr(ron_module, "copernicus_retrieve", _failing_copernicus)
    monkeypatch.setattr(Ron, "_fetch_opentopo_dem", _failing_opentopo)

    with pytest.raises(RuntimeError, match="Copernicus DEM retrieval failed and OpenTopography fallback failed"):
        ron.fetch_dem()


def test_fetch_dem_opentopo_scheme_still_uses_opentopo_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path, dem_db="opentopo://srtmgl1_e")
    _patch_post_fetch_dependencies(monkeypatch)

    fallback_calls: list[str | None] = []

    def _fake_fetch_opentopo(self: Ron, dem_db_override: str | None = None) -> None:
        fallback_calls.append(dem_db_override)
        Path(self.dem_fn).write_bytes(b"dem")

    monkeypatch.setattr(Ron, "_fetch_opentopo_dem", _fake_fetch_opentopo)
    monkeypatch.setattr(
        ron_module,
        "wmesque_retrieve",
        lambda *_args, **_kwargs: pytest.fail("WMEsque should not run for opentopo:// DEM selection."),
    )

    ron.fetch_dem()

    assert fallback_calls == [None]
    assert Path(ron.dem_fn).exists()
