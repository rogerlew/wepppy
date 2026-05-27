from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import wepppy.nodb.mods.rusle.rusle as rusle_module
from wepppy.nodb.mods.rusle.c_integration import RusleCResult
from wepppy.nodb.mods.rusle.k_integration import RusleKResult
from wepppy.nodb.mods.rusle.ls_integration import RusleLsResult
from wepppy.nodb.mods.rusle.r_modes import RusleRModeSelection


pytestmark = pytest.mark.unit


def _write_raster(path: Path, data: np.ndarray, *, nodata: float = -9999.0) -> None:
    profile = {
        "driver": "GTiff",
        "height": int(data.shape[0]),
        "width": int(data.shape[1]),
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_origin(0.0, float(data.shape[0]), 1.0, 1.0),
        "nodata": nodata,
    }
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data.astype(np.float32), 1)


def _write_constant_from_dem(dem_path: Path, output_path: Path, value: float) -> None:
    with rasterio.open(dem_path) as dataset:
        profile = dict(dataset.profile)
        shape = (int(dataset.height), int(dataset.width))
        nodata = dataset.nodata if dataset.nodata is not None else -9999.0
    data = np.full(shape, float(value), dtype=np.float32)
    _write_raster(output_path, data, nodata=float(nodata))


def _read_valid_value(path: Path) -> float:
    with rasterio.open(path) as dataset:
        data = dataset.read(1)
        nodata = dataset.nodata
    if nodata is not None:
        data = np.where(np.isclose(data, nodata), np.nan, data)
    value = data[0, 0]
    assert np.isfinite(value)
    return float(value)


def test_ensure_polaris_layers_passes_explicit_rusle_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = rusle_module.Rusle(str(tmp_path), "disturbed9002.cfg")
    captured: dict[str, object] = {}

    class DummyPolaris:
        def acquire_and_align(self, payload):
            captured["payload"] = dict(payload)
            return {"layers_requested": 12, "layers_written": 12}

    monkeypatch.setattr(controller, "_ensure_polaris_controller", lambda: DummyPolaris())

    summary = controller._ensure_polaris_layers(force_refresh=True)

    assert summary["fetched"] is True
    assert summary["payload"] == {
        "force_refresh": True,
        "properties": ["sand", "silt", "clay", "om", "bd", "ksat"],
        "statistics": ["mean"],
        "depths": ["0_5", "5_15"],
    }
    assert captured["payload"] == summary["payload"]


def test_ensure_polaris_layers_bootstraps_missing_polaris_nodb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = rusle_module.Rusle(str(tmp_path), "disturbed9002.cfg")
    captured: dict[str, object] = {}

    class DummyRon:
        def __init__(self) -> None:
            self._mods = ["disturbed", "rusle"]
            self.config_stem = "disturbed9002"

        @property
        def mods(self):
            return self._mods

        @contextmanager
        def locked(self):
            yield self

    ron = DummyRon()

    class DummyPolaris:
        instance = None

        def __init__(self, wd: str, cfg_fn: str, run_group=None, group_name=None) -> None:
            captured["constructed_wd"] = wd
            captured["constructed_cfg_fn"] = cfg_fn
            self._payloads: list[dict[str, object]] = []
            DummyPolaris.instance = self

        @classmethod
        def tryGetInstance(cls, wd: str):
            return cls.instance

        def acquire_and_align(self, payload):
            captured["payload"] = dict(payload)
            return {"layers_requested": 12, "layers_written": 12}

    monkeypatch.setattr(rusle_module.Ron, "getInstance", lambda wd: ron)
    monkeypatch.setattr(rusle_module, "Polaris", DummyPolaris)

    summary = controller._ensure_polaris_layers(force_refresh=True)

    assert summary["fetched"] is True
    assert summary["reason"] == "force_refresh"
    assert captured["constructed_wd"] == str(tmp_path)
    assert captured["constructed_cfg_fn"] == "disturbed9002.cfg"
    assert captured["payload"] == summary["payload"]
    assert "polaris" in ron.mods


def test_build_scenario_sbs_without_sbs_writes_mode_specific_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    dem_path = wd / "dem.tif"
    relief_path = wd / "dem" / "wbt" / "relief.tif"
    cli_path = wd / "climate.cli"
    landuse_path = wd / "landuse.tif"
    rusle_dir = wd / "rusle"
    rusle_dir.mkdir(parents=True, exist_ok=True)
    relief_path.parent.mkdir(parents=True, exist_ok=True)

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32))
    _write_raster(relief_path, np.ones((2, 2), dtype=np.float32))
    _write_raster(landuse_path, np.ones((2, 2), dtype=np.float32))
    cli_path.write_text("cli", encoding="utf-8")

    controller = rusle_module.Rusle(str(wd), "disturbed9002.cfg")
    c_call: dict[str, object] = {}
    ls_call: dict[str, object] = {}

    monkeypatch.setattr(
        rusle_module.Ron,
        "getInstance",
        lambda _wd: SimpleNamespace(dem_fn=str(dem_path), map=None),
    )
    monkeypatch.setattr(
        rusle_module.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(cli_path=str(cli_path)),
    )
    monkeypatch.setattr(
        rusle_module.Landuse,
        "getInstance",
        lambda _wd: SimpleNamespace(lc_fn=str(landuse_path)),
    )
    monkeypatch.setattr(
        rusle_module.Watershed,
        "getInstance",
        lambda _wd: SimpleNamespace(
            netful=None,
            delineation_backend_is_wbt=True,
            relief=str(relief_path),
        ),
    )
    monkeypatch.setattr(
        rusle_module.Disturbed,
        "tryGetInstance",
        lambda _wd: SimpleNamespace(has_map=False, disturbed_path=None),
    )
    monkeypatch.setattr(
        rusle_module,
        "cli_calculate_static_r",
        lambda _cli: {"mean_annual_r": 6.0},
    )
    monkeypatch.setattr(
        controller,
        "_ensure_polaris_layers",
        lambda force_refresh=False: {
            "fetched": False,
            "reason": "aligned",
            "payload": {
                "force_refresh": bool(force_refresh),
                "properties": ["sand", "silt", "clay", "om", "bd", "ksat"],
                "statistics": ["mean"],
                "depths": ["0_5", "5_15"],
            },
            "summary": {"layers_requested": 12},
        },
    )
    catalog_updates: list[str] = []

    def _fake_update_catalog_entry(_wd: str, relpath: str):
        catalog_updates.append(relpath)
        if relpath.endswith("README.md"):
            raise ValueError("Unsupported asset type for '/tmp/rusle/README.md'")
        return None

    monkeypatch.setattr(rusle_module, "update_catalog_entry", _fake_update_catalog_entry)

    def _fake_ls(
        _wd: str,
        _dem: str,
        *,
        channel_mask=None,
        blocking_mask=None,
        max_slope_length_m=304.8,
    ):
        assert _dem == str(relief_path)
        ls_call["channel_mask"] = channel_mask
        ls_call["blocking_mask"] = blocking_mask
        ls_call["max_slope_length_m"] = max_slope_length_m
        ls_path = rusle_dir / "ls.tif"
        l_path = rusle_dir / "l.tif"
        s_path = rusle_dir / "s.tif"
        sca_path = rusle_dir / "sca.tif"
        eff_path = rusle_dir / "effective_slope_length.tif"
        manifest_path = rusle_dir / "manifest.json"
        _write_constant_from_dem(dem_path, ls_path, 2.0)
        _write_constant_from_dem(dem_path, l_path, 2.0)
        _write_constant_from_dem(dem_path, s_path, 2.0)
        _write_constant_from_dem(dem_path, sca_path, 2.0)
        _write_constant_from_dem(dem_path, eff_path, 2.0)
        manifest_path.write_text("{}", encoding="utf-8")
        return RusleLsResult(
            ls=str(ls_path),
            l=str(l_path),
            s=str(s_path),
            sca=str(sca_path),
            effective_slope_length=str(eff_path),
            manifest=str(manifest_path),
        )

    def _fake_k(
        _wd: str,
        *,
        statistic: str,
        selected_modes,
        default_k_mode: str,
        write_default_k: bool,
        **_kwargs,
    ):
        assert statistic == "mean"
        assert list(selected_modes) == ["polaris_nomograph"]
        assert default_k_mode == "polaris_nomograph"
        assert write_default_k is False

        nomograph_path = rusle_dir / "k_polaris_nomograph.tif"
        manifest_path = rusle_dir / "manifest.json"
        _write_constant_from_dem(dem_path, nomograph_path, 3.0)
        if not manifest_path.exists():
            manifest_path.write_text("{}", encoding="utf-8")
        return RusleKResult(
            nomograph=str(nomograph_path),
            epic=None,
            k_default=None,
            manifest=str(manifest_path),
            reference_samples=None,
            comparison_summary=None,
        )

    def _fake_c(
        _wd: str,
        _dem: str,
        *,
        c_mode: str,
        c_output_filename: str,
        landuse: str | None = None,
        sbs: str | None = None,
        **_kwargs,
    ):
        c_call["mode"] = c_mode
        c_call["output"] = c_output_filename
        c_call["landuse"] = landuse
        c_call["sbs"] = sbs

        c_path = rusle_dir / c_output_filename
        manifest_path = rusle_dir / "manifest.json"
        disturbed_class_path = rusle_dir / "disturbed_class.tif"
        lookup_copy_path = rusle_dir / "c_lookup_used.csv"
        _write_constant_from_dem(dem_path, c_path, 4.0)
        _write_constant_from_dem(dem_path, disturbed_class_path, 1.0)
        lookup_copy_path.write_text("disturbed_class,sbs_class,c_value\n", encoding="utf-8")
        if not manifest_path.exists():
            manifest_path.write_text("{}", encoding="utf-8")
        return RusleCResult(
            c=str(c_path),
            manifest=str(manifest_path),
            fg=None,
            disturbed_class=str(disturbed_class_path),
            sbs_4class=None,
            lookup_copy=str(lookup_copy_path),
        )

    monkeypatch.setattr(rusle_module, "run_rusle_ls_factor", _fake_ls)
    monkeypatch.setattr(rusle_module, "run_rusle_k_factors", _fake_k)
    monkeypatch.setattr(rusle_module, "run_rusle_c_factor", _fake_c)

    summary = controller.build(
        payload={
            "c_mode": "scenario_sbs",
            "k_modes": ["polaris_nomograph"],
            "default_k_mode": "polaris_nomograph",
            "p_value": 5.0,
        }
    )

    assert c_call == {
        "mode": "scenario_sbs",
        "output": "c_scenario_sbs.tif",
        "landuse": str(landuse_path),
        "sbs": None,
    }
    assert ls_call["max_slope_length_m"] == pytest.approx(304.8)
    assert ls_call["blocking_mask"] is None

    artifacts = summary["artifacts"]
    assert artifacts["c_relpath"] == "rusle/c_scenario_sbs.tif"
    assert artifacts["a_relpath"] == "rusle/a_scenario_sbs_polaris_nomograph.tif"
    assert not (rusle_dir / "sbs_4class.tif").exists()

    a_path = wd / artifacts["a_relpath"]
    assert a_path.exists()
    assert _read_valid_value(a_path) == pytest.approx(720.0)

    manifest_path = rusle_dir / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    assert manifest["rusle"]["options"]["r_mode"] == "cligen_static"
    assert manifest["rusle"]["options"]["c_mode"] == "scenario_sbs"
    assert manifest["rusle"]["options"]["k_modes"] == ["polaris_nomograph"]
    assert manifest["rusle"]["r_factor"]["r_source_label"] == "WEPP Climate-Derived R"
    assert "rusle/README.md" in catalog_updates

    readme_path = rusle_dir / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8")
    assert "## Intermediate raster products" in readme_text
    assert "## Provenance" in readme_text
    assert "## Raster specifications" in readme_text
    assert "| `rusle/ls.tif` |" in readme_text
    assert "| `rusle/effective_slope_length.tif` |" in readme_text
    assert "| `rusle/disturbed_class.tif` |" in readme_text


def test_build_with_momm2025_r_mode_uses_external_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    dem_path = wd / "dem.tif"
    relief_path = wd / "dem" / "wbt" / "relief.tif"
    landuse_path = wd / "landuse.tif"
    rusle_dir = wd / "rusle"
    rusle_dir.mkdir(parents=True, exist_ok=True)
    relief_path.parent.mkdir(parents=True, exist_ok=True)

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32))
    _write_raster(relief_path, np.ones((2, 2), dtype=np.float32))
    _write_raster(landuse_path, np.ones((2, 2), dtype=np.float32))

    controller = rusle_module.Rusle(str(wd), "disturbed9002.cfg")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        rusle_module.Ron,
        "getInstance",
        lambda _wd: SimpleNamespace(dem_fn=str(dem_path), map=None),
    )
    monkeypatch.setattr(
        rusle_module.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(
            cli_path=str(wd / "missing.cli"),
            cli_dir=str(wd / "climate"),
            par_fn="localized.par",
            climatestation_meta=SimpleNamespace(annual_ppt=22.4),
        ),
    )
    monkeypatch.setattr(
        rusle_module.Landuse,
        "getInstance",
        lambda _wd: SimpleNamespace(lc_fn=str(landuse_path)),
    )
    monkeypatch.setattr(
        rusle_module.Watershed,
        "getInstance",
        lambda _wd: SimpleNamespace(
            centroid=(-120.5, 46.5),
            netful=None,
            delineation_backend_is_wbt=True,
            relief=str(relief_path),
        ),
    )
    monkeypatch.setattr(
        rusle_module.Disturbed,
        "tryGetInstance",
        lambda _wd: SimpleNamespace(has_map=False, disturbed_path=None),
    )
    monkeypatch.setattr(
        controller,
        "_ensure_polaris_layers",
        lambda force_refresh=False: {
            "fetched": False,
            "reason": "aligned",
            "payload": {
                "force_refresh": bool(force_refresh),
                "properties": ["sand", "silt", "clay", "om", "bd", "ksat"],
                "statistics": ["mean"],
                "depths": ["0_5", "5_15"],
            },
            "summary": {"layers_requested": 12},
        },
    )
    monkeypatch.setattr(rusle_module, "update_catalog_entry", lambda _wd, relpath: relpath)
    monkeypatch.setattr(rusle_module, "_resolve_momm2025_annual_precip_in", lambda _climate: 43.6)

    def _fake_select_momm(centroid_lnglat, *, annual_precip_in=None):
        captured["centroid_lnglat"] = centroid_lnglat
        captured["annual_precip_in"] = annual_precip_in
        return RusleRModeSelection(
            r_mode="momm2025_county_region",
            r_source_label="Momm 2025 County Climatology",
            r_source_purpose="test-purpose",
            r_selection_method="watershed_centroid_county",
            r_scalar_value=73.5,
            r_scalar_units="MJ*mm/(ha*h*yr)",
            annual_source_field="annual_r",
            annual_dataset_value=73.5,
            annual_dataset_units="MJ*mm/(ha*h*yr)",
            centroid_lng=-120.5,
            centroid_lat=46.5,
            selected_fips="53009",
            selected_county="Clallam",
            selected_region=None,
            monthly_dataset_values={"jan": 1.0},
            dataset_artifacts={"momm_table": "fake.parquet"},
        )

    monkeypatch.setattr(rusle_module, "select_momm2025_county_region_r", _fake_select_momm)
    def _fake_ls(
        _wd: str,
        _dem: str,
        *,
        channel_mask=None,
        blocking_mask=None,
        max_slope_length_m=304.8,
    ):
        captured["max_slope_length_m"] = float(max_slope_length_m)
        ls_path = rusle_dir / "ls.tif"
        l_path = rusle_dir / "l.tif"
        s_path = rusle_dir / "s.tif"
        sca_path = rusle_dir / "sca.tif"
        eff_path = rusle_dir / "effective_slope_length.tif"
        manifest_path = rusle_dir / "manifest.json"
        _write_constant_from_dem(dem_path, ls_path, 2.0)
        _write_constant_from_dem(dem_path, l_path, 2.0)
        _write_constant_from_dem(dem_path, s_path, 2.0)
        _write_constant_from_dem(dem_path, sca_path, 2.0)
        _write_constant_from_dem(dem_path, eff_path, 2.0)
        manifest_path.write_text("{}", encoding="utf-8")
        return RusleLsResult(
            ls=str(ls_path),
            l=str(l_path),
            s=str(s_path),
            sca=str(sca_path),
            effective_slope_length=str(eff_path),
            manifest=str(manifest_path),
        )

    monkeypatch.setattr(rusle_module, "run_rusle_ls_factor", _fake_ls)

    def _fake_k(
        _wd: str,
        *,
        statistic: str,
        selected_modes,
        default_k_mode: str,
        write_default_k: bool,
        **_kwargs,
    ):
        nomograph_path = rusle_dir / "k_polaris_nomograph.tif"
        _write_constant_from_dem(dem_path, nomograph_path, 3.0)
        manifest_path = rusle_dir / "manifest.json"
        if not manifest_path.exists():
            manifest_path.write_text("{}", encoding="utf-8")
        return RusleKResult(
            nomograph=str(nomograph_path),
            epic=None,
            k_default=None,
            manifest=str(manifest_path),
            reference_samples=None,
            comparison_summary=None,
        )

    def _fake_c(
        _wd: str,
        _dem: str,
        *,
        c_mode: str,
        c_output_filename: str,
        **_kwargs,
    ):
        c_path = rusle_dir / c_output_filename
        _write_constant_from_dem(dem_path, c_path, 4.0)
        manifest_path = rusle_dir / "manifest.json"
        if not manifest_path.exists():
            manifest_path.write_text("{}", encoding="utf-8")
        disturbed_class_path = rusle_dir / "disturbed_class.tif"
        _write_constant_from_dem(dem_path, disturbed_class_path, 1.0)
        lookup_copy_path = rusle_dir / "c_lookup_used.csv"
        lookup_copy_path.write_text("disturbed_class,sbs_class,c_value\n", encoding="utf-8")
        return RusleCResult(
            c=str(c_path),
            manifest=str(manifest_path),
            fg=None,
            disturbed_class=str(disturbed_class_path),
            sbs_4class=None,
            lookup_copy=str(lookup_copy_path),
        )

    monkeypatch.setattr(rusle_module, "run_rusle_k_factors", _fake_k)
    monkeypatch.setattr(rusle_module, "run_rusle_c_factor", _fake_c)

    summary = controller.build(
        payload={
            "r_mode": "momm2025_county_region",
            "c_mode": "scenario_sbs",
            "k_modes": ["polaris_nomograph"],
            "default_k_mode": "polaris_nomograph",
            "max_slope_length_m": 220.0,
            "p_value": 1.0,
        }
    )

    assert captured["centroid_lnglat"] == (-120.5, 46.5)
    assert captured["annual_precip_in"] == pytest.approx(43.6)
    assert captured["max_slope_length_m"] == pytest.approx(220.0)
    assert summary["r_mode"] == "momm2025_county_region"
    assert _read_valid_value(wd / summary["artifacts"]["r_relpath"]) == pytest.approx(73.5)

    manifest_path = rusle_dir / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    assert manifest["rusle"]["options"]["r_mode"] == "momm2025_county_region"
    assert manifest["rusle"]["options"]["max_slope_length_m"] == pytest.approx(220.0)
    assert manifest["rusle"]["r_factor"]["selected_fips"] == "53009"
    assert manifest["rusle"]["r_factor"]["r_source_label"] == "Momm 2025 County Climatology"
    assert manifest["rusle"]["static_r"]["source_mode"] == "momm2025_county_region"


def test_build_observed_rap_forwards_rock_fraction_and_records_manifest_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    dem_path = wd / "dem.tif"
    relief_path = wd / "dem" / "wbt" / "relief.tif"
    landuse_path = wd / "landuse.tif"
    rap_path = wd / "rusle" / "rap" / "rap.tif"
    cli_path = wd / "climate.cli"
    rusle_dir = wd / "rusle"
    rusle_dir.mkdir(parents=True, exist_ok=True)
    relief_path.parent.mkdir(parents=True, exist_ok=True)
    rap_path.parent.mkdir(parents=True, exist_ok=True)

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32))
    _write_raster(relief_path, np.ones((2, 2), dtype=np.float32))
    _write_raster(landuse_path, np.ones((2, 2), dtype=np.float32))
    _write_raster(rap_path, np.ones((2, 2), dtype=np.float32))
    cli_path.write_text("cli", encoding="utf-8")

    controller = rusle_module.Rusle(str(wd), "disturbed9002.cfg")
    c_call: dict[str, object] = {}

    monkeypatch.setattr(
        rusle_module.Ron,
        "getInstance",
        lambda _wd: SimpleNamespace(
            dem_fn=str(dem_path),
            map=SimpleNamespace(extent=(-121.0, 45.0, -120.0, 46.0)),
        ),
    )
    monkeypatch.setattr(
        rusle_module.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(cli_path=str(cli_path)),
    )
    monkeypatch.setattr(
        rusle_module.Landuse,
        "getInstance",
        lambda _wd: SimpleNamespace(lc_fn=str(landuse_path)),
    )
    monkeypatch.setattr(
        rusle_module.Watershed,
        "getInstance",
        lambda _wd: SimpleNamespace(
            netful=None,
            delineation_backend_is_wbt=True,
            relief=str(relief_path),
        ),
    )
    monkeypatch.setattr(rusle_module.Disturbed, "tryGetInstance", lambda _wd: None)
    monkeypatch.setattr(rusle_module, "cli_calculate_static_r", lambda _cli: {"mean_annual_r": 6.0})
    monkeypatch.setattr(
        controller,
        "_ensure_polaris_layers",
        lambda force_refresh=False: {
            "fetched": False,
            "reason": "aligned",
            "payload": {
                "force_refresh": bool(force_refresh),
                "properties": ["sand", "silt", "clay", "om", "bd", "ksat"],
                "statistics": ["mean"],
                "depths": ["0_5", "5_15"],
            },
            "summary": {"layers_requested": 12},
        },
    )
    monkeypatch.setattr(controller, "_resolve_observed_rap", lambda extent, rap_year: str(rap_path))
    monkeypatch.setattr(rusle_module, "update_catalog_entry", lambda _wd, relpath: relpath)

    def _fake_ls(
        _wd: str,
        _dem: str,
        *,
        channel_mask=None,
        blocking_mask=None,
        max_slope_length_m=304.8,
    ):
        ls_path = rusle_dir / "ls.tif"
        l_path = rusle_dir / "l.tif"
        s_path = rusle_dir / "s.tif"
        sca_path = rusle_dir / "sca.tif"
        eff_path = rusle_dir / "effective_slope_length.tif"
        manifest_path = rusle_dir / "manifest.json"
        _write_constant_from_dem(dem_path, ls_path, 2.0)
        _write_constant_from_dem(dem_path, l_path, 2.0)
        _write_constant_from_dem(dem_path, s_path, 2.0)
        _write_constant_from_dem(dem_path, sca_path, 2.0)
        _write_constant_from_dem(dem_path, eff_path, 2.0)
        manifest_path.write_text("{}", encoding="utf-8")
        return RusleLsResult(
            ls=str(ls_path),
            l=str(l_path),
            s=str(s_path),
            sca=str(sca_path),
            effective_slope_length=str(eff_path),
            manifest=str(manifest_path),
        )

    def _fake_k(
        _wd: str,
        *,
        statistic: str,
        selected_modes,
        default_k_mode: str,
        write_default_k: bool,
        **_kwargs,
    ):
        nomograph_path = rusle_dir / "k_polaris_nomograph.tif"
        manifest_path = rusle_dir / "manifest.json"
        _write_constant_from_dem(dem_path, nomograph_path, 3.0)
        if not manifest_path.exists():
            manifest_path.write_text("{}", encoding="utf-8")
        return RusleKResult(
            nomograph=str(nomograph_path),
            epic=None,
            k_default=None,
            manifest=str(manifest_path),
            reference_samples=None,
            comparison_summary=None,
        )

    def _fake_c(
        _wd: str,
        _dem: str,
        *,
        c_mode: str,
        c_output_filename: str,
        rap: str | None = None,
        rock_fraction_of_rap_bare: float | str = "auto",
        **_kwargs,
    ):
        c_call["mode"] = c_mode
        c_call["rap"] = rap
        c_call["rock_fraction_of_rap_bare"] = rock_fraction_of_rap_bare
        c_path = rusle_dir / c_output_filename
        fg_path = rusle_dir / "c_fg.tif"
        manifest_path = rusle_dir / "manifest.json"
        _write_constant_from_dem(dem_path, c_path, 4.0)
        _write_constant_from_dem(dem_path, fg_path, 60.0)
        manifest_path.write_text(
            json.dumps(
                {
                    "c": {
                        "mode": "observed_rap",
                        "rock_fraction_of_rap_bare": {
                            "requested": float(rock_fraction_of_rap_bare),
                            "effective": float(rock_fraction_of_rap_bare),
                            "source": "user",
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        return RusleCResult(
            c=str(c_path),
            manifest=str(manifest_path),
            fg=str(fg_path),
            disturbed_class=None,
            sbs_4class=None,
            lookup_copy=None,
        )

    monkeypatch.setattr(rusle_module, "run_rusle_ls_factor", _fake_ls)
    monkeypatch.setattr(rusle_module, "run_rusle_k_factors", _fake_k)
    monkeypatch.setattr(rusle_module, "run_rusle_c_factor", _fake_c)

    summary = controller.build(
        payload={
            "c_mode": "observed_rap",
            "k_modes": ["polaris_nomograph"],
            "default_k_mode": "polaris_nomograph",
            "rock_fraction_of_rap_bare": 0.75,
        }
    )

    assert c_call["mode"] == "observed_rap"
    assert c_call["rap"] == str(rap_path)
    assert c_call["rock_fraction_of_rap_bare"] == pytest.approx(0.75)
    assert summary["rock_fraction_of_rap_bare"] == pytest.approx(0.75)

    with open(rusle_dir / "manifest.json", "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    assert manifest["rusle"]["options"]["rock_fraction_of_rap_bare"] == pytest.approx(0.75)
    assert manifest["rusle"]["observed_rap_rock_fraction"]["source"] == "user"


def test_build_rejects_topaz_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    dem_path = wd / "dem.tif"
    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32))

    controller = rusle_module.Rusle(str(wd), "disturbed9002.cfg")

    monkeypatch.setattr(
        controller,
        "parse_inputs",
        lambda payload=None: {
            "r_mode": "cligen_static",
            "c_mode": "scenario_sbs",
            "rap_year": 2025,
            "k_modes": ["polaris_nomograph"],
            "default_k_mode": "polaris_nomograph",
            "max_slope_length_m": 304.8,
            "p_value": 1.0,
            "force_polaris_refresh": False,
            "rock_fraction_of_rap_bare": "auto",
        },
    )
    monkeypatch.setattr(
        rusle_module.Ron,
        "getInstance",
        lambda _wd: SimpleNamespace(dem_fn=str(dem_path), map=None),
    )
    monkeypatch.setattr(rusle_module.Climate, "getInstance", lambda _wd: SimpleNamespace())
    monkeypatch.setattr(rusle_module.Landuse, "getInstance", lambda _wd: SimpleNamespace())
    monkeypatch.setattr(
        rusle_module.Watershed,
        "getInstance",
        lambda _wd: SimpleNamespace(delineation_backend_is_wbt=False),
    )
    monkeypatch.setattr(rusle_module.Disturbed, "tryGetInstance", lambda _wd: None)

    with pytest.raises(ValueError, match="WBT delineation backend"):
        controller.build(payload={})


def test_parse_inputs_accepts_max_slope_length_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = rusle_module.Rusle(str(tmp_path), "disturbed9002.cfg")
    monkeypatch.setattr(controller, "available_rap_years", lambda: [])

    parsed = controller.parse_inputs(payload={"max_slope_length_m": "250.5"})

    assert parsed["max_slope_length_m"] == pytest.approx(250.5)
    assert parsed["rock_fraction_of_rap_bare"] == "auto"


def test_parse_inputs_accepts_auto_and_numeric_rock_fraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = rusle_module.Rusle(str(tmp_path), "disturbed9002.cfg")
    monkeypatch.setattr(controller, "available_rap_years", lambda: [])

    parsed_auto = controller.parse_inputs(payload={"rock_fraction_of_rap_bare": "auto"})
    parsed_numeric = controller.parse_inputs(payload={"rock_fraction_of_rap_bare": "0.35"})

    assert parsed_auto["rock_fraction_of_rap_bare"] == "auto"
    assert parsed_numeric["rock_fraction_of_rap_bare"] == pytest.approx(0.35)


def test_parse_inputs_rejects_non_positive_max_slope_length(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = rusle_module.Rusle(str(tmp_path), "disturbed9002.cfg")
    monkeypatch.setattr(controller, "available_rap_years", lambda: [])

    with pytest.raises(ValueError, match="max_slope_length_m must be greater than 0"):
        controller.parse_inputs(payload={"max_slope_length_m": 0})


def test_parse_inputs_rejects_invalid_rock_fraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = rusle_module.Rusle(str(tmp_path), "disturbed9002.cfg")
    monkeypatch.setattr(controller, "available_rap_years", lambda: [])

    with pytest.raises(ValueError, match="rock_fraction_of_rap_bare"):
        controller.parse_inputs(payload={"rock_fraction_of_rap_bare": 1.2})


def test_available_rap_years_uses_rap_manager_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = rusle_module.Rusle(str(tmp_path), "disturbed9002.cfg")
    manager_cls = rusle_module.RangelandAnalysisPlatformV3

    assert callable(getattr(manager_cls, "available_years", None))
    assert callable(getattr(manager_cls, "latest_completed_year", None))

    monkeypatch.setattr(
        manager_cls,
        "latest_completed_year",
        classmethod(lambda cls, *, today=None: 1990),
    )

    years = controller.available_rap_years()

    assert years == sorted(years)
    assert years[0] == 1986
    assert years[-1] == 1990
