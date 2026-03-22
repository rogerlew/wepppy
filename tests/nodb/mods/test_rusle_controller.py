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
    cli_path = wd / "climate.cli"
    landuse_path = wd / "landuse.tif"
    rusle_dir = wd / "rusle"
    rusle_dir.mkdir(parents=True, exist_ok=True)

    _write_raster(dem_path, np.ones((2, 2), dtype=np.float32))
    _write_raster(landuse_path, np.ones((2, 2), dtype=np.float32))
    cli_path.write_text("cli", encoding="utf-8")

    controller = rusle_module.Rusle(str(wd), "disturbed9002.cfg")
    c_call: dict[str, object] = {}

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
        lambda _wd: SimpleNamespace(netful=None),
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
    monkeypatch.setattr(rusle_module, "update_catalog_entry", lambda _wd, _relpath: None)

    def _fake_ls(_wd: str, _dem: str, *, channel_mask=None):
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
    assert manifest["rusle"]["options"]["c_mode"] == "scenario_sbs"
    assert manifest["rusle"]["options"]["k_modes"] == ["polaris_nomograph"]
