import pytest
from types import SimpleNamespace

from wepppy.nodb.mods.polaris import polaris

pytestmark = pytest.mark.unit


def test_parse_polaris_layer_id() -> None:
    assert polaris.parse_polaris_layer_id("clay_mean_0_5") == ("clay", "mean", "0_5")


def test_parse_polaris_layer_id_rejects_invalid_property() -> None:
    with pytest.raises(polaris.PolarisConfigError):
        polaris.parse_polaris_layer_id("foo_mean_0_5")


def test_fetch_polaris_catalog_layer_ids_parses_index(monkeypatch: pytest.MonkeyPatch) -> None:
    html = """
    <html><body>
      <a href="sand_mean_0_5.vrt">sand_mean_0_5.vrt</a>
      <a href="clay_mean_0_5.vrt">clay_mean_0_5.vrt</a>
      <a href="clay_mean_0_5.vrt">clay_mean_0_5.vrt</a>
    </body></html>
    """

    monkeypatch.setattr(polaris, "_fetch_url_text", lambda url, timeout_seconds: html)

    layers = polaris.fetch_polaris_catalog_layer_ids("http://example.test/")

    assert layers == ["clay_mean_0_5", "sand_mean_0_5"]


def test_axis_from_value_accepts_all() -> None:
    values = polaris._axis_from_value(
        ["all"],
        allowed=polaris.POLARIS_PROPERTIES,
        default=("sand",),
        label="properties",
    )
    assert values == list(polaris.POLARIS_PROPERTIES)


def test_acquire_and_align_skips_existing_and_respects_force_refresh(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wd = str(tmp_path)
    dem_fn = tmp_path / "dem.tif"
    dem_fn.write_bytes(b"dem")

    controller = polaris.Polaris(wd, "disturbed9002.cfg")
    output_fn = tmp_path / "polaris" / "clay_mean_0_5.tif"

    raster_calls: list[tuple[str, str, str, str]] = []
    catalog_updates: list[str] = []

    monkeypatch.setattr(
        polaris,
        "fetch_polaris_catalog_layer_ids",
        lambda base_url, timeout_seconds: ["clay_mean_0_5"],
    )
    monkeypatch.setattr(
        polaris.Ron,
        "getInstance",
        lambda _wd: SimpleNamespace(dem_fn=str(dem_fn)),
    )
    monkeypatch.setattr(
        polaris,
        "update_catalog_entry",
        lambda _wd, relpath: catalog_updates.append(relpath),
    )
    monkeypatch.setattr(polaris.RedisPrep, "tryGetInstance", lambda _wd: None)

    def _fake_raster_stacker(source_ref: str, dem_path: str, output_path: str, *, resample: str) -> None:
        raster_calls.append((source_ref, dem_path, output_path, resample))
        with open(output_path, "wb") as stream:
            stream.write(b"aligned")

    monkeypatch.setattr(polaris, "raster_stacker", _fake_raster_stacker)

    payload = {"properties": ["clay"], "statistics": ["mean"], "depths": ["0_5"]}

    first = controller.acquire_and_align(payload=payload)
    assert first["layers_requested"] == 1
    assert first["layers_written"] == 1
    assert first["layers_skipped"] == 0
    assert output_fn.exists()
    assert len(raster_calls) == 1
    assert catalog_updates == ["polaris/clay_mean_0_5.tif"]

    second = controller.acquire_and_align(payload=payload)
    assert second["layers_requested"] == 1
    assert second["layers_written"] == 0
    assert second["layers_skipped"] == 1
    assert len(raster_calls) == 1

    third = controller.acquire_and_align(
        payload={"properties": ["clay"], "statistics": ["mean"], "depths": ["0_5"], "force_refresh": True}
    )
    assert third["layers_requested"] == 1
    assert third["layers_written"] == 1
    assert third["layers_skipped"] == 0
    assert len(raster_calls) == 2
    assert catalog_updates == ["polaris/clay_mean_0_5.tif", "polaris/clay_mean_0_5.tif"]
