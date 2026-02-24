from __future__ import annotations

from pathlib import Path

import pytest

import wepppy.locales.earth.copernicus as copernicus_module

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("No JSON payload configured")
        return self._payload


def test_copernicus_retrieve_rejects_unsupported_dataset(tmp_path: Path) -> None:
    with pytest.raises(copernicus_module.CopernicusConfigurationError, match="Unsupported Copernicus dataset"):
        copernicus_module.copernicus_retrieve(
            (-117.1, 43.9, -115.9, 45.1),
            str(tmp_path / "dem.tif"),
            30.0,
            dataset="copernicus://unsupported",
        )


def test_copernicus_retrieve_raises_when_no_public_tiles_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        copernicus_module.requests,
        "get",
        lambda *_args, **_kwargs: _FakeResponse(404),
    )

    with pytest.raises(copernicus_module.CopernicusConfigurationError, match="no public tiles"):
        copernicus_module.copernicus_retrieve(
            (-117.1, 43.9, -116.9, 44.1),
            str(tmp_path / "dem.tif"),
            30.0,
            dataset="copernicus://dem_cop_30",
        )


def _single_tile_payload(href: str) -> dict:
    return {"assets": {"elevation": {"href": href}}}


def _single_tile_href() -> str:
    return (
        "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
        "Copernicus_DSM_COG_10_N44_00_W117_00_DEM/"
        "Copernicus_DSM_COG_10_N44_00_W117_00_DEM.tif"
    )


def _fake_get_factory(payload: dict):
    def _fake_get(url: str, timeout: int = 30):
        if url.endswith("/items/Copernicus_DSM_COG_10_N44_00_W117_00.json"):
            return _FakeResponse(200, payload)
        return _FakeResponse(404)

    return _fake_get


def test_copernicus_retrieve_builds_vrt_and_transforms(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tile_payload = _single_tile_payload(_single_tile_href())

    buildvrt_calls: list[list[str]] = []
    warp_calls: list[tuple] = []

    def _fake_run(cmd: list[str], capture_output: bool, check: bool, text: bool):
        del capture_output, check, text
        buildvrt_calls.append(cmd)
        vrt_path = Path(cmd[-1])
        vrt_path.write_text("<VRTDataset/>", encoding="utf-8")

        class _Completed:
            returncode = 0
            stderr = ""

        return _Completed()

    def _fake_utm_raster_transform(
        extent,
        src_fn: str,
        dst_fn: str,
        cellsize: float,
        resample: str = "bilinear",
    ):
        warp_calls.append((tuple(extent), src_fn, dst_fn, cellsize, resample))
        Path(dst_fn).write_bytes(b"dem")

    monkeypatch.setattr(copernicus_module.requests, "get", _fake_get_factory(tile_payload))
    monkeypatch.setattr(copernicus_module.subprocess, "run", _fake_run)
    monkeypatch.setattr(copernicus_module, "utm_raster_transform", _fake_utm_raster_transform)

    dst = tmp_path / "dem.tif"
    copernicus_module.copernicus_retrieve(
        (-117.1, 43.9, -116.9, 44.1),
        str(dst),
        30.0,
        dataset="copernicus://dem_cop_30",
    )

    assert buildvrt_calls
    assert buildvrt_calls[0][0] == "gdalbuildvrt"
    assert warp_calls
    assert warp_calls[0][4] == "bilinear"
    assert dst.exists()


def test_copernicus_retrieve_rejects_unexpected_elevation_href_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = _single_tile_payload("https://example.org/bad.tif")
    monkeypatch.setattr(copernicus_module.requests, "get", _fake_get_factory(payload))

    with pytest.raises(copernicus_module.CopernicusConfigurationError, match="unexpected elevation host"):
        copernicus_module.copernicus_retrieve(
            (-117.1, 43.9, -116.9, 44.1),
            str(tmp_path / "dem.tif"),
            30.0,
            dataset="copernicus://dem_cop_30",
        )


def test_copernicus_retrieve_rejects_missing_elevation_asset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = {"assets": {}}
    monkeypatch.setattr(copernicus_module.requests, "get", _fake_get_factory(payload))

    with pytest.raises(copernicus_module.CopernicusConfigurationError, match="no elevation asset"):
        copernicus_module.copernicus_retrieve(
            (-117.1, 43.9, -116.9, 44.1),
            str(tmp_path / "dem.tif"),
            30.0,
            dataset="copernicus://dem_cop_30",
        )


def test_copernicus_retrieve_raises_retryable_when_gdalbuildvrt_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = _single_tile_payload(_single_tile_href())

    monkeypatch.setattr(copernicus_module.requests, "get", _fake_get_factory(payload))

    def _raise_missing(*_args, **_kwargs):
        raise FileNotFoundError("gdalbuildvrt")

    monkeypatch.setattr(copernicus_module.subprocess, "run", _raise_missing)

    with pytest.raises(copernicus_module.CopernicusRetryableError, match="execute gdalbuildvrt"):
        copernicus_module.copernicus_retrieve(
            (-117.1, 43.9, -116.9, 44.1),
            str(tmp_path / "dem.tif"),
            30.0,
            dataset="copernicus://dem_cop_30",
        )


def test_copernicus_retrieve_raises_retryable_when_gdalbuildvrt_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = _single_tile_payload(_single_tile_href())

    monkeypatch.setattr(copernicus_module.requests, "get", _fake_get_factory(payload))

    class _Completed:
        returncode = 1
        stderr = "boom"

    monkeypatch.setattr(copernicus_module.subprocess, "run", lambda *_args, **_kwargs: _Completed())

    with pytest.raises(copernicus_module.CopernicusRetryableError, match="gdalbuildvrt failed"):
        copernicus_module.copernicus_retrieve(
            (-117.1, 43.9, -116.9, 44.1),
            str(tmp_path / "dem.tif"),
            30.0,
            dataset="copernicus://dem_cop_30",
        )
