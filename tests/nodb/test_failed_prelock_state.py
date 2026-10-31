"""Failed artifact preparation must not publish proposed controller flags."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb import base
from wepppy.nodb.core import Landuse, Ron, Soils, Watershed
from tests.nodb.test_base_boundary_characterization import _RedisStub

pytestmark = pytest.mark.unit


@pytest.fixture
def controllers(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    wd = str(tmp_path)
    config = "canada-wbt-mofe.cfg"
    ron = Ron(wd, config, initialize_components=False)
    watershed = Watershed(wd, config)
    soils = Soils(wd, config)
    landuse = Landuse(wd, config)
    try:
        yield ron, watershed, soils, landuse
    finally:
        for cls in (Ron, Watershed, Soils, Landuse):
            cls.cleanup_run_instances(wd)


def _fail(*args, **kwargs):
    raise OSError("prepared artifact failure")


@pytest.mark.parametrize("kind", ["soils", "landuse", "dem", "channels"])
def test_failed_map_preparation_preserves_accepted_flag(controllers, tmp_path, monkeypatch, kind):
    import wepppy.nodb.core.landuse as landuse_module
    import wepppy.nodb.core.ron as ron_module
    import wepppy.nodb.core.soils as soils_module
    import wepppy.nodb.core.watershed_mixins as watershed_module

    ron, watershed, soils, landuse = controllers
    controller, field = {
        "soils": (soils, "_soils_is_vrt"),
        "landuse": (landuse, "_landuse_is_vrt"),
        "dem": (ron, "_dem_is_vrt"),
        "channels": (watershed, "_flovec_netful_relief_chnjnt_are_vrt"),
    }[kind]
    with controller.locked():
        setattr(controller, field, True)
    held = type(controller).getInstance(str(tmp_path))
    source = tmp_path / "source.tif"
    source.write_bytes(b"not read before injected failure")
    if kind == "soils":
        monkeypatch.setattr(soils_module, "request_catalog_refresh", _fail)
        operation = lambda: held.symlink_soils_map(str(source), as_cropped_vrt=False)
    elif kind == "landuse":
        monkeypatch.setattr(landuse_module, "request_catalog_refresh", _fail)
        operation = lambda: held.symlink_landuse_map(str(source), as_cropped_vrt=False)
    elif kind == "dem":
        monkeypatch.setattr(ron_module, "RasterDatasetInterpolator", _fail)
        operation = lambda: held.symlink_dem(str(source), as_cropped_vrt=False)
    else:
        monkeypatch.setattr(watershed_module, "polygonize_netful", _fail)
        operation = lambda: held.symlink_channels_map(str(source), str(source), as_cropped_vrt=False)
    with pytest.raises(OSError, match="prepared artifact failure"):
        operation()
    assert getattr(held, field) is True
    assert type(held).getInstance(str(tmp_path)) is held
    with held.locked():
        held._nfms_unrelated = "accepted"
    assert getattr(type(held).load_detached(str(tmp_path)), field) is True


@pytest.mark.parametrize("kind", ["soils", "landuse"])
def test_failed_spatial_api_retrieval_preserves_accepted_flag(controllers, tmp_path, monkeypatch, kind):
    import wepppy.nodb.core.landuse as landuse_module
    import wepppy.nodb.core.soils as soils_module

    ron, _, soils, landuse = controllers
    controller = soils if kind == "soils" else landuse
    field = "_soils_is_vrt" if kind == "soils" else "_landuse_is_vrt"
    with controller.locked():
        setattr(controller, field, True)
    held = type(controller).getInstance(str(tmp_path))
    monkeypatch.setattr(Ron, "map", property(lambda self: SimpleNamespace(extent=[0, 0, 1, 1], cellsize=30)))
    monkeypatch.setattr(soils_module if kind == "soils" else landuse_module, "wmesque_retrieve", _fail)
    with pytest.raises(OSError, match="prepared artifact failure"):
        held._build_spatial_api()
    assert getattr(held, field) is True
    with held.locked():
        held._nfms_unrelated = "accepted"
    assert getattr(type(held).load_detached(str(tmp_path)), field) is True


@pytest.mark.parametrize("kind", ["soils", "landuse"])
def test_clean_busy_owner_does_not_publish_flag(controllers, tmp_path, kind):
    _, _, soils, landuse = controllers
    controller = soils if kind == "soils" else landuse
    field = "_soils_is_vrt" if kind == "soils" else "_landuse_is_vrt"
    with controller.locked():
        setattr(controller, field, True)
    held = type(controller).getInstance(str(tmp_path))
    owner = type(held).load_detached(str(tmp_path))
    owner.lock()
    try:
        with pytest.raises(base.NoDbAlreadyLockedError):
            held.clean()
        assert getattr(held, field) is True
        owner._assert_lock_owned_for_dump()
    finally:
        owner.unlock()


@pytest.mark.parametrize("kind", ["soils", "landuse"])
def test_clean_inside_owned_scope_retains_outer_commit(controllers, tmp_path, kind):
    _, _, soils, landuse = controllers
    controller = soils if kind == "soils" else landuse
    field = "_soils_is_vrt" if kind == "soils" else "_landuse_is_vrt"
    with controller.locked():
        setattr(controller, field, True)
    held = type(controller).getInstance(str(tmp_path))
    with held.locked():
        held._nfms_unrelated = "outer accepted"
        held.clean()
        assert getattr(held, field) is False
        assert getattr(type(held).load_detached(str(tmp_path)), field) is True
    durable = type(held).load_detached(str(tmp_path))
    assert getattr(durable, field) is False
    assert durable._nfms_unrelated == "outer accepted"
