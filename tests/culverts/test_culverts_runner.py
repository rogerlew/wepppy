import json
import os
from pathlib import Path

import numpy as np
import pytest

import wepppy.nodb.culverts_runner as culverts_runner_module
from wepppy.all_your_base.geo import get_raster_extent
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodb.core import Landuse, Ron, Watershed
from wepppy.weppcloud.utils import helpers as wepp_helpers
from wepppy.weppcloud.utils.helpers import get_wd


pytestmark = [pytest.mark.nodb, pytest.mark.integration]

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin


def _write_raster(path: Path, data: np.ndarray, transform, crs: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width = data.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(data, 1)


def _make_topo_files(topo_dir: Path, *, crs: str = "EPSG:32611") -> dict[str, Path]:
    transform = from_origin(500000.0, 4100000.0, 10.0, 10.0)
    dem_data = np.arange(9, dtype=np.float32).reshape((3, 3))
    flovec_data = np.ones((3, 3), dtype=np.uint8)
    netful_data = np.zeros((3, 3), dtype=np.uint8)
    netful_data[1, 1] = 1
    streams_data = netful_data.copy()
    chnjnt_data = np.zeros((3, 3), dtype=np.uint8)

    dem_path = topo_dir / "hydro-enforced-dem.tif"
    flovec_path = topo_dir / "flovec.tif"
    netful_path = topo_dir / "netful.tif"
    streams_path = topo_dir / "streams.tif"
    chnjnt_path = topo_dir / "chnjnt.tif"

    _write_raster(dem_path, dem_data, transform, crs)
    _write_raster(flovec_path, flovec_data, transform, crs)
    _write_raster(netful_path, netful_data, transform, crs)
    _write_raster(streams_path, streams_data, transform, crs)
    _write_raster(chnjnt_path, chnjnt_data, transform, crs)

    return {
        "dem": dem_path,
        "flovec": flovec_path,
        "netful": netful_path,
        "streams": streams_path,
        "chnjnt": chnjnt_path,
    }


def _write_watersheds(path: Path, point_ids: list[object] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if point_ids is None:
        point_ids = [1, "2"]
    features = []
    for idx, point_id in enumerate(point_ids):
        offset = idx * 10.0
        features.append(
            {
                "type": "Feature",
                "properties": {"Point_ID": point_id},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [500000.0 + offset, 4099980.0],
                            [500020.0 + offset, 4099980.0],
                            [500020.0 + offset, 4100000.0],
                            [500000.0 + offset, 4100000.0],
                            [500000.0 + offset, 4099980.0],
                        ]
                    ],
                },
            }
        )
    payload = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:32611"}},
        "features": features,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _init_base_project(path: Path, *, nlcd_db: str | None = None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    Ron(str(path), "culvert.cfg")
    if nlcd_db is not None:
        landuse = Landuse.getInstance(str(path))
        landuse.nlcd_db = nlcd_db


def test_ron_symlink_dem_sets_map_and_symlink(tmp_path: Path) -> None:
    topo_dir = tmp_path / "topo"
    topo = _make_topo_files(topo_dir)
    run_wd = tmp_path / "run"
    run_wd.mkdir()

    ron = Ron(str(run_wd), "culvert.cfg")
    ron.symlink_dem(str(topo["dem"]))

    assert os.path.islink(ron.dem_fn)
    assert os.path.realpath(ron.dem_fn) == os.path.abspath(topo["dem"])
    assert ron.map is not None
    expected_extent = get_raster_extent(str(topo["dem"]), wgs=True)
    assert ron.map.extent == pytest.approx(list(expected_extent))


def test_watershed_symlink_channels_map_creates_links(tmp_path: Path) -> None:
    topo_dir = tmp_path / "topo"
    topo = _make_topo_files(topo_dir)
    run_wd = tmp_path / "run"
    run_wd.mkdir()

    ron = Ron(str(run_wd), "culvert.cfg")
    ron.symlink_dem(str(topo["dem"]))

    watershed = Watershed.getInstance(str(run_wd))
    watershed.symlink_channels_map(str(topo["flovec"]), str(topo["netful"]))

    flovec_link = Path(watershed.wbt_wd) / "flovec.tif"
    netful_link = Path(watershed.wbt_wd) / "netful.tif"
    assert flovec_link.is_symlink()
    assert netful_link.is_symlink()
    assert watershed.netful_utm_shp is not None
    assert watershed.netful_shp is not None
    assert Path(watershed.netful_utm_shp).exists()
    assert Path(watershed.netful_shp).exists()


def test_culverts_runner_creates_runs_and_get_wd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    monkeypatch.setattr(wepp_helpers, "redis_wd_cache_client", None)

    base_runid = "batch;;culvert_base;;_base"
    base_src = tmp_path / "batch" / "culvert_base" / "_base"
    _init_base_project(base_src)
    (base_src / "README.txt").write_text("base-default", encoding="utf-8")

    override_runid = "batch;;culvert_override;;_base"
    override_src = tmp_path / "batch" / "culvert_override" / "_base"
    _init_base_project(override_src, nlcd_db="nlcd/2021")
    (override_src / "README.txt").write_text("base-override", encoding="utf-8")

    def _fake_get_wd(runid: str, *args, **kwargs) -> str:
        if runid == base_runid:
            return str(base_src)
        if runid == override_runid:
            return str(override_src)
        return wepp_helpers.get_wd(runid, *args, **kwargs)

    monkeypatch.setattr(culverts_runner_module, "get_wd", _fake_get_wd)

    batch_uuid = "batch-1234"
    batch_root = culverts_root / batch_uuid
    topo_dir = batch_root / "topo"
    culverts_dir = batch_root / "culverts"
    batch_root.mkdir(parents=True)

    topo = _make_topo_files(topo_dir)
    watersheds_path = culverts_dir / "watersheds.geojson"
    _write_watersheds(watersheds_path)

    payload_metadata = {
        "dem": {"path": "topo/hydro-enforced-dem.tif"},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }

    model_parameters = {
        "schema_version": "culvert-model-params-v1",
        "base_project_runid": override_runid,
        "nlcd_db": "nlcd/2021",
    }

    runner = CulvertsRunner(str(batch_root), "culvert.cfg")
    run_ids = runner.create_runs(
        batch_uuid,
        str(batch_root),
        payload_metadata,
        model_parameters=model_parameters,
    )

    assert run_ids == ("1", "2")
    base_copy = batch_root / "_base" / "README.txt"
    assert base_copy.read_text(encoding="utf-8") == "base-override"
    for run_id in run_ids:
        run_wd = batch_root / "runs" / run_id
        dem_link = run_wd / "dem" / "dem.tif"
        flovec_link = run_wd / "dem" / "wbt" / "flovec.tif"
        netful_link = run_wd / "dem" / "wbt" / "netful.tif"

        assert dem_link.is_symlink()
        assert os.path.realpath(dem_link) == os.path.abspath(topo["dem"])
        assert flovec_link.is_symlink()
        assert netful_link.is_symlink()

        ron = Ron.getInstance(str(run_wd))
        assert ron.run_group == "culvert"
        assert ron.group_name == batch_uuid
        assert ron.runid == f"culvert;;{batch_uuid};;{run_id}"

        landuse = Landuse.getInstance(str(run_wd))
        assert landuse.nlcd_db == "nlcd/2021"

        runid = f"culvert;;{batch_uuid};;{run_id}"
        assert get_wd(runid) == str(run_wd)


def test_culverts_runner_cleanup_relief_and_chnjnt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    monkeypatch.setattr(wepp_helpers, "redis_wd_cache_client", None)

    base_runid = "batch;;culvert_cleanup;;_base"
    base_src = tmp_path / "batch" / "culvert_cleanup" / "_base"
    _init_base_project(base_src)
    wbt_dir = base_src / "dem" / "wbt"
    wbt_dir.mkdir(parents=True, exist_ok=True)
    (wbt_dir / "relief.tif").write_text("old-relief", encoding="utf-8")
    (wbt_dir / "chnjnt.tif").write_text("old-chnjnt", encoding="utf-8")

    def _fake_get_wd(runid: str, *args, **kwargs) -> str:
        if runid == base_runid:
            return str(base_src)
        return wepp_helpers.get_wd(runid, *args, **kwargs)

    monkeypatch.setattr(culverts_runner_module, "get_wd", _fake_get_wd)

    batch_uuid = "batch-5678"
    batch_root = culverts_root / batch_uuid
    topo_dir = batch_root / "topo"
    culverts_dir = batch_root / "culverts"
    batch_root.mkdir(parents=True)

    topo = _make_topo_files(topo_dir)
    watersheds_path = culverts_dir / "watersheds.geojson"
    _write_watersheds(watersheds_path, point_ids=[1])

    payload_metadata = {
        "dem": {"path": "topo/hydro-enforced-dem.tif"},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }

    model_parameters = {
        "schema_version": "culvert-model-params-v1",
        "base_project_runid": base_runid,
    }

    runner = CulvertsRunner(str(batch_root), "culvert.cfg")
    run_ids = runner.create_runs(
        batch_uuid,
        str(batch_root),
        payload_metadata,
        model_parameters=model_parameters,
    )

    assert run_ids == ("1",)
    run_wd = batch_root / "runs" / "1"
    relief_link = run_wd / "dem" / "wbt" / "relief.tif"
    chnjnt_link = run_wd / "dem" / "wbt" / "chnjnt.tif"
    assert relief_link.is_symlink()
    assert os.path.realpath(relief_link) == os.path.abspath(topo["dem"])
    assert chnjnt_link.is_symlink()
    assert os.path.realpath(chnjnt_link) == os.path.abspath(topo["chnjnt"])


def test_culverts_runner_rejects_path_traversal(tmp_path: Path) -> None:
    batch_root = tmp_path / "culverts" / "batch-9999"
    topo_dir = batch_root / "topo"
    culverts_dir = batch_root / "culverts"
    batch_root.mkdir(parents=True)

    _make_topo_files(topo_dir)
    watersheds_path = culverts_dir / "watersheds.geojson"
    _write_watersheds(watersheds_path, point_ids=["../escape"])

    payload_metadata = {
        "dem": {"path": "topo/hydro-enforced-dem.tif"},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }

    runner = CulvertsRunner(str(batch_root), "culvert.cfg")
    with pytest.raises(ValueError, match="Point_ID"):
        runner.create_runs("batch-9999", str(batch_root), payload_metadata)
