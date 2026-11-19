"""Validate the I-CREWS snapshots and their native channel map artifacts."""

import json
from pathlib import Path

import numpy as np
from osgeo import gdal, osr
from pyproj import Transformer
import pytest

from wepppy.all_your_base.geo.locationinfo import RasterDatasetInterpolator
from wepppy.nodb.core import Ron, Watershed
from wepppy.nodb.core.channel_boundary import ChannelBoundaryError, validate_channel_extent
from wepppy.nodb.project_config_snapshot import load_preset_policies, materialize_preset_snapshot, resolve_preset_snapshot
from wepppy.project_config_serialization import parse_config_text

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("preset, source, multi_ofe", [
    ("i-crews", "disturbed9002_wbt", False),
    ("i-crews-mofe", "disturbed9002-wbt-mofe", True),
])
def test_i_crews_presets_prepare_native_channel_artifacts(tmp_path, preset, source, multi_ofe):
    policies = load_preset_policies()
    snapshot = resolve_preset_snapshot(preset, {}, source_revision="integration-test", policies=policies)
    source_snapshot = resolve_preset_snapshot(source, {}, source_revision="integration-test", policies=policies)
    config = parse_config_text(snapshot.config_bytes.decode())
    source_config = parse_config_text(source_snapshot.config_bytes.decode())
    assert policies[preset].overrides == policies[source].overrides
    assert config.pop("map") == {
        **source_config.pop("map"),
        "center0": [45.6, -114.15],
        "zoom0": 5,
        "boundary": "static/mods/i-crews/idaho-boundary.geojson",
        "boundary_check": "intersects",
    }
    assert config == source_config
    assert config["watershed"]["delineation_backend"] == "wbt"
    assert bool(config["wepp"].get("multi_ofe")) is multi_ofe

    materialize_preset_snapshot(tmp_path, snapshot)
    ron = Ron(str(tmp_path), snapshot.config_filename)
    watershed = Watershed.getInstance(str(tmp_path))
    assert watershed.delineation_backend_is_wbt
    assert ron.center0 == [45.6, -114.15] and ron.zoom0 == 5
    validate_channel_extent(ron, [-115.0, 41.95, -114.9, 42.05])
    # Inside Idaho's bounding box and outside the actual panhandle polygon.
    with pytest.raises(ChannelBoundaryError, match="intersects the project map boundary"):
        validate_channel_extent(ron, [-112.15, 48, -112, 48.15])

    side = 96
    dem = gdal.GetDriverByName("GTiff").Create(ron.dem_fn, side, side, 1, gdal.GDT_Float32)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(32611)
    dem.SetProjection(crs.ExportToWkt())
    west, north = Transformer.from_crs(4326, 32611, always_xy=True).transform(-116.75, 47.67)
    dem.SetGeoTransform((west, 30, 0, north, 0, -30))
    rows, columns = np.indices((side, side))
    elevation = 700 - 2 * rows + np.abs(columns - side // 2)
    dem.GetRasterBand(1).WriteArray(elevation.astype(np.float32))
    dem = None

    raster = RasterDatasetInterpolator(ron.dem_fn)
    extent = list(raster.extent)
    ron.set_map(extent, [(extent[0] + extent[2]) / 2, (extent[1] + extent[3]) / 2], 14)
    watershed.build_channels()

    channels = gdal.Open(watershed.netful).ReadAsArray()
    assert channels.shape == (side, side)
    assert np.any(channels == 1)
    overlay = json.loads(Path(watershed.netful_shp).read_text())
    assert overlay["type"] == "FeatureCollection" and overlay["features"]

    if multi_ofe:
        _read_prepared_mofe_inputs(tmp_path)


def _read_prepared_mofe_inputs(root):
    from wepppy.nodb.core.wepp import Wepp, prep_multi_ofe_hillslope
    from wepppy.wepp.management import Management, get_management_summary
    from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
    from wepppy.wepp.soils.utils.multi_ofe import SoilMultipleOfeSynth

    wepp = Wepp.getInstance(str(root))
    assert wepp.multi_ofe
    slope = root / "watershed/slope_files/hillslopes/hill_101.mofe.slp"
    slope.parent.mkdir(parents=True, exist_ok=True)
    slope.write_text("97.5\n2\n180 1\n" + "2 50\n0 0.2 1 0.2\n" * 2)

    landuse = root / "landuse"
    landuse.mkdir(exist_ok=True)
    stack = [get_management_summary(key, "c3s-disturbed").get_management()
             for key in ("424", "50")]
    ManagementMultipleOfeSynth(stack).write(str(landuse / "hill_101.mofe.man"))

    soils = root / "soils"
    soils.mkdir(exist_ok=True)
    soil_source = Path(__file__).resolve().parents[1] / "wepp_runner/fixtures/hillslope_smoke/runs/p1.sol"
    SoilMultipleOfeSynth([str(soil_source)] * 2).write(str(soils / "hill_101.mofe.sol"))

    runs = root / "wepp/runs"
    runs.mkdir(parents=True, exist_ok=True)
    prep_multi_ofe_hillslope((
        "101", 1, str(root), str(runs), 2, None, 0.5, False, None, False, None, False, None,
    ))
    prepared = Management(Key="test", ManagementFile="p1.man", ManagementDir=str(runs),
                          Description="Prepared I-CREWS management", Color=(0, 0, 0, 255))
    assert len(prepared.inis) == 2
    assert (runs / "p1.slp").read_text().splitlines()[1] == "2"
