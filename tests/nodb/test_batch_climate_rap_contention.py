"""Real-file interleavings; injected writers do not identify the Kubernetes writer."""

from pathlib import Path
from types import SimpleNamespace
import json
import os
import re
import threading

import pytest

from tests.nodb.lock_contention_utils import ensure_climate_stub
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core.climate import Climate, ClimateMode
from wepppy.nodb.core import climate_build_helpers as helpers
from wepppy.nodb.mods.rap import rap_ts as rap_module
from wepppy.nodb.mods.rap.rap_ts import RAP_TS
from wepppy.landcover.rap import RangelandAnalysisPlatformV3

pytestmark = pytest.mark.unit


def _same_size_rewrite(controller, field, value):
    path = Path(controller._nodb)
    before = path.stat()
    old, new = json.dumps(getattr(controller, field)), json.dumps(value)
    assert len(old) == len(new)
    text, count = re.subn(
        rf'({re.escape(json.dumps(field))}\s*:\s*){re.escape(old)}',
        lambda match: match[1] + new, path.read_text(),
    )
    assert count == 1
    replacement = path.with_suffix(".replacement")
    replacement.write_text(text)
    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
    os.replace(replacement, path)
    assert path.stat().st_size == before.st_size
    assert path.stat().st_mtime != before.st_mtime


@pytest.fixture
def controllers(tmp_path, monkeypatch):
    ensure_climate_stub(str(tmp_path))
    climate = Climate.getInstance(str(tmp_path))
    with climate.locked():
        climate._observed_start_year = 2001
        climate._observed_end_year = 2001
        climate._climatestation = "station-x"
        climate._cligen_db = "legacy"
        climate._climate_mode = ClimateMode.GridMetPRISM
        climate._climate_spatialmode = 1
        climate._test_unrelated = "BASE"
        climate.cli_fn = "old.cli"
        climate.par_fn = "old.par"
        climate.sub_cli_fns = {"1": "old.cli"}
        climate.sub_par_fns = {"1": "old.par"}
        climate.monthlies = [0.0]
    Path(climate.cli_dir).mkdir(exist_ok=True)
    Path(climate.cli_dir, "old.cli").write_text("old climate")
    rap = RAP_TS(str(tmp_path), "test.cfg")
    rap = RAP_TS.getInstance(str(tmp_path))
    manager = RangelandAnalysisPlatformV3(rap.rap_dir, [-117, 45, -116, 46], 30)
    raster = Path(rap.rap_dir, "_rap_v3_2001.tif")
    raster.write_bytes(b"source raster")
    manager.ds = {"2001": str(raster)}
    with rap.locked():
        rap._rap_start_year = rap._rap_end_year = 2001
        rap._rap_mgr = manager
        rap._test_unrelated = "BASE"
    watershed = SimpleNamespace(
        centroid=(-116.5, 45.5), require_centroid=lambda: (-116.5, 45.5),
        subwta=str(tmp_path / "subwta.tif"), mofe_map=str(tmp_path / "mofe.tif"),
        centroid_hillslope_iter=lambda: iter([(1, (-116.5, 45.5))]),
        hillslope_centroid_lnglat=lambda _: (-116.5, 45.5),
    )
    Path(watershed.subwta).write_bytes(b"watershed")
    monkeypatch.setattr(NoDbBase, "watershed_instance", property(lambda _: watershed))
    monkeypatch.setattr(NoDbBase, "ron_instance", property(lambda _: SimpleNamespace(
        map=SimpleNamespace(extent=[-117, 45, -116, 46], cellsize=30))))
    monkeypatch.setattr(NoDbBase, "multi_ofe", property(lambda _: False))
    monkeypatch.setattr(rap_module.Watershed, "getInstance", lambda _: watershed)
    monkeypatch.setattr(rap_module.Ron, "getInstance", lambda _: climate.ron_instance)
    for controller in (climate, rap):
        with controller.locked():
            pass
    yield climate, rap
    Climate._instances.pop(str(tmp_path), None)
    RAP_TS._instances.pop(str(tmp_path), None)


def test_prism_unrelated_rewrite_survives(controllers, monkeypatch):
    climate, _ = controllers
    monkeypatch.setattr(helpers, "_retrieve_prism_revision_tiles", lambda *args: None)
    monkeypatch.setattr(helpers, "_collect_prism_revision_monthlies", lambda *args: ([], [], []))
    monkeypatch.setattr(helpers, "ClimateFile", lambda path: SimpleNamespace(cli_fn=path, breakpoint=False))

    def revise(*args):
        _same_size_rewrite(climate, "_test_unrelated", "KEEP")
        Path(args[-1]).write_text("new hillslope")

    monkeypatch.setattr(helpers, "cli_revision", revise)
    climate._prism_revision()
    current = Climate.load_detached(climate.wd)
    assert current._test_unrelated == "KEEP"
    assert current.sub_cli_fns == {"1": "_1.cli"} or current.sub_cli_fns == {1: "_1.cli"}


def test_rap_unrelated_rewrite_survives(controllers, monkeypatch):
    _, rap = controllers
    gate = threading.Lock()
    rewritten = False

    def analyze(**kwargs):
        nonlocal rewritten
        with gate:
            if not rewritten:
                _same_size_rewrite(rap, "_test_unrelated", "KEEP")
                rewritten = True
        return {"1": 25.0}

    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", analyze)
    rap.analyze()
    current = RAP_TS.load_detached(rap.wd)
    assert current._test_unrelated == "KEEP"
    assert current.get_cover("1", "2001") == 1.0
    frame = rap_module.pd.read_parquet(Path(rap.rap_dir, "rap_ts.parquet"))
    assert set(frame.band) == {1, 2, 3, 4, 5, 6}


@pytest.mark.parametrize("field,value", [("_rap_start_year", 2002), ("_rap_start_year", None)])
def test_rap_relevant_rewrite_preserves_existing_parquet(controllers, monkeypatch, field, value):
    _, rap = controllers
    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 25.0})
    rap.analyze()
    parquet = Path(rap.rap_dir, "rap_ts.parquet")
    previous = parquet.read_bytes()
    gate = threading.Lock()
    changed = False

    def rewrite(**_):
        nonlocal changed
        with gate:
            if not changed:
                _same_size_rewrite(rap, field, value)
                changed = True
        return {"1": 75.0}

    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", rewrite)
    with pytest.raises(RuntimeError, match="superseded"):
        rap.analyze()
    assert parquet.read_bytes() == previous
    assert RAP_TS.load_detached(rap.wd)._rap_start_year == value


@pytest.mark.parametrize("empty", [False, True])
def test_rap_collection_and_empty_results(controllers, monkeypatch, empty):
    _, rap = controllers
    before = Path(rap._nodb).read_bytes()

    def collect(**_):
        assert not rap.islocked()
        if empty:
            return {}
        raise ValueError("injected raster failure")

    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", collect)
    if empty:
        rap.analyze()
        assert rap_module.pd.read_parquet(Path(rap.rap_dir, "rap_ts.parquet")).empty
        assert RAP_TS.load_detached(rap.wd).data == {}
    else:
        with pytest.raises(ValueError, match="injected raster"):
            rap.analyze()
        assert Path(rap._nodb).read_bytes() == before
        assert not Path(rap.rap_dir, "rap_ts.parquet").exists()


def test_rap_dump_failure_restores_parquet(controllers, monkeypatch):
    _, rap = controllers
    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 25.0})
    rap.analyze()
    previous_nodb = Path(rap._nodb).read_bytes()
    parquet = Path(rap.rap_dir, "rap_ts.parquet")
    previous_parquet = parquet.read_bytes()
    original_replace = os.replace

    def fail_nodb(source, destination):
        if str(destination) == rap._nodb:
            raise OSError("injected NoDb replace failure")
        return original_replace(source, destination)

    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 75.0})
    monkeypatch.setattr(os, "replace", fail_nodb)
    with pytest.raises(OSError, match="injected NoDb"):
        rap.analyze()
    assert Path(rap._nodb).read_bytes() == previous_nodb
    assert parquet.read_bytes() == previous_parquet
    assert not rap.islocked()
    assert RAP_TS.getInstance(rap.wd).get_cover("1", "2001") == 1.0


def test_observed_gridmet_unrelated_rewrite_survives(controllers, monkeypatch):
    from wepppy.nodb.core import climate as module

    climate, _ = controllers
    with climate.locked():
        climate._observed_start_year = "2001"
        climate._observed_end_year = "2001"
    Path(climate.cli_dir, "wepp_cli.parquet").write_bytes(b"obsolete calendar")
    Path(climate.cli_dir, "atlas14_intensity.csv").write_text("obsolete location")
    monkeypatch.setattr(module, "CligenStationsManager", lambda **_: SimpleNamespace(
        get_station_fromid=lambda _: SimpleNamespace(par="station.par")))
    monkeypatch.setattr(module, "Cligen", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(module, "ClimateFile", lambda _: SimpleNamespace(calc_monthlies=lambda: [1.0]))

    def build(*args, **kwargs):
        assert not climate.islocked()
        assert args[1:5] == (-116.5, 45.5, 2001, 2001)
        assert args[6:8] == ("ws.prn", "wepp.cli")
        assert kwargs == {"adjust_mx_pt5": False, "silent_pass_observed_quality_guard": True}
        _same_size_rewrite(climate, "_test_unrelated", "KEEP")
        Path(args[5], "wepp.cli").write_text("collected climate")

    monkeypatch.setattr(module, "build_observed_gridmet", build)
    climate._build_climate_observed_gridmet()
    current = Climate.load_detached(climate.wd)
    assert current._test_unrelated == "KEEP"
    assert current.monthlies == [1.0]
    assert current._observed_start_year == current._observed_end_year == 2001
    assert Path(climate.cli_dir, current.cli_fn).read_text() == "collected climate"
    assert not Path(climate.cli_dir, "wepp_cli.parquet").exists()
    assert not Path(climate.cli_dir, "atlas14_intensity.csv").exists()


@pytest.mark.parametrize("conflict", [False, "source", "year"])
def test_prism_failure_does_not_publish(controllers, monkeypatch, conflict):
    climate, _ = controllers
    before = Path(climate._nodb).read_bytes()
    monkeypatch.setattr(helpers, "_retrieve_prism_revision_tiles", lambda *args: None)
    monkeypatch.setattr(helpers, "_collect_prism_revision_monthlies", lambda *args: ([], [], []))
    monkeypatch.setattr(helpers, "ClimateFile", lambda path: SimpleNamespace(cli_fn=path, breakpoint=False))

    def revise(*args):
        assert not climate.islocked()
        Path(args[-1]).write_text("new hillslope")
        if conflict == "source":
            Path(climate.cli_path).write_text("new upstream climate")
        elif conflict == "year":
            _same_size_rewrite(climate, "_observed_end_year", 2002)
        else:
            raise ValueError("injected hillslope failure")

    monkeypatch.setattr(helpers, "cli_revision", revise)
    with pytest.raises((RuntimeError, ValueError), match="superseded|injected hillslope"):
        climate._prism_revision()
    if conflict != "year":
        assert Path(climate._nodb).read_bytes() == before
    else:
        assert Climate.load_detached(climate.wd)._observed_end_year == 2002
    assert not Path(climate.cli_dir, "_1.cli").exists()


def test_rap_acquisition_collects_before_finalizing(controllers, monkeypatch):
    _, rap = controllers

    def retrieve(manager, years):
        assert not rap.islocked()
        _same_size_rewrite(rap, "_test_unrelated", "KEEP")
        filename = Path(manager.wd, f"_rap_v3_{years[0]}.tif")
        filename.write_bytes(b"collected raster")
        manager.ds[str(years[0])] = str(filename)
        return 0

    # This is the remote collection seam, not a mocked GDAL integration test.
    monkeypatch.setattr(RangelandAnalysisPlatformV3, "retrieve", retrieve)
    rap.acquire_rasters()
    current = RAP_TS.load_detached(rap.wd)
    assert current._test_unrelated == "KEEP"
    assert Path(current._rap_mgr.ds["2001"]).read_bytes() == b"collected raster"
    assert current._rap_mgr.wd == rap.rap_dir


def test_post_commit_error_keeps_first_parquet_and_reports_failure(controllers, monkeypatch):
    from wepppy.nodb import base

    _, rap = controllers
    timestamps = []
    monkeypatch.setattr(rap_module.RedisPrep, "getInstance", lambda _: SimpleNamespace(timestamp=timestamps.append))
    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 25.0})

    def fail_version(*_):
        raise OSError("injected post-replace version failure")

    monkeypatch.setattr(base, "write_version", fail_version)
    with pytest.raises(OSError, match="post-replace"):
        rap.analyze()
    assert Path(rap.rap_dir, "rap_ts.parquet").is_file()
    assert RAP_TS.load_detached(rap.wd).get_cover("1", "2001") == 1.0
    assert timestamps == []
    assert not rap.islocked()


def test_competing_precommit_rewrite_rolls_back_parquet(controllers, monkeypatch):
    import jsonpickle

    _, rap = controllers
    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 25.0})
    rap.analyze()
    previous = Path(rap.rap_dir, "rap_ts.parquet").read_bytes()
    encode = jsonpickle.encode
    count = 0

    def concurrent_write(obj, *args, **kwargs):
        nonlocal count
        if obj is rap:
            count += 1
            if count == 1:
                _same_size_rewrite(rap, "_test_unrelated", "KEEP")
        return encode(obj, *args, **kwargs)

    monkeypatch.setattr(jsonpickle, "encode", concurrent_write)
    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 75.0})
    from wepppy.nodb.base import NoDbStaleWriteError
    with pytest.raises(NoDbStaleWriteError):
        rap.analyze()
    assert Path(rap.rap_dir, "rap_ts.parquet").read_bytes() == previous
    assert RAP_TS.load_detached(rap.wd)._test_unrelated == "KEEP"


def test_old_publication_cannot_rollback_new_owner(controllers):
    from wepppy.nodb._derived_build import publish_files

    _, rap = controllers
    target = Path(rap.rap_dir, "artifact.txt")
    target.write_text("original")
    first_stage = Path(rap.rap_dir, ".first")
    second_stage = Path(rap.rap_dir, ".second")
    first_stage.mkdir()
    second_stage.mkdir()
    (first_stage / target.name).write_text("first")
    (second_stage / target.name).write_text("second")
    rap.lock()
    with pytest.raises(RuntimeError, match="unlocked|owning|token"):
        with publish_files(first_stage, rap.rap_dir, rap):
            rap.unlock()
            successor = RAP_TS.load_detached(rap.wd)
            successor._init_logging()
            with successor.locked():
                with publish_files(second_stage, rap.rap_dir, successor):
                    pass
            raise ValueError("old publisher failed")
    assert target.read_text() == "second"
    assert list(Path(rap.rap_dir).glob(".derived-backup-*/artifact.txt"))


def test_rap_missing_source_fails_before_publication(controllers):
    _, rap = controllers
    before = Path(rap._nodb).read_bytes()
    Path(rap._rap_mgr.ds["2001"]).unlink()
    with pytest.raises(FileNotFoundError):
        rap.analyze()
    assert Path(rap._nodb).read_bytes() == before
    assert not Path(rap.rap_dir, "rap_ts.parquet").exists()


def test_rap_legacy_integer_dataset_keys(controllers, monkeypatch):
    _, rap = controllers
    with rap.locked():
        rap._rap_mgr.ds = {2001: rap._rap_mgr.ds["2001"]}
    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 25.0})
    rap.analyze()
    assert RAP_TS.load_detached(rap.wd).get_cover("1", "2001") == 1.0


def test_rap_multi_ofe_output_and_reload(controllers, monkeypatch):
    _, rap = controllers
    Path(rap.wd, "mofe.tif").write_bytes(b"mofe map")
    monkeypatch.setattr(NoDbBase, "multi_ofe", property(lambda _: True))
    monkeypatch.setattr(rap_module, "identify_median_intersecting_raster_keys", lambda **_: {"1": {"2": 25.0}})
    rap.analyze()
    current = RAP_TS.load_detached(rap.wd)
    assert current.data[rap_module.RAP_Band.TREE]["2001"]["1"]["2"] == 25.0
    frame = rap_module.pd.read_parquet(Path(rap.rap_dir, "rap_ts.parquet"))
    assert set(frame.mofe_id) == {2}


@pytest.mark.parametrize("managed", [False, True])
def test_direct_climate_build_directory_containment(controllers, managed):
    from wepppy.nodb.core.climate_observed_build import _require_climate_directory
    import shutil

    climate, _ = controllers
    root = Path(climate.cli_dir)
    shutil.rmtree(root)
    target = (Path(climate.wd) / ".nodir/lower/climate") if managed else (Path(climate.wd) / "soils")
    target.mkdir(parents=True)
    sentinel = target / "keep.txt"
    sentinel.write_text("keep")
    root.symlink_to(target, target_is_directory=True)
    if managed:
        _require_climate_directory(climate)
    else:
        with pytest.raises(ValueError, match="Unmanaged"):
            _require_climate_directory(climate)
    assert sentinel.read_text() == "keep"


@pytest.mark.integration
def test_rap_real_rasters_propagate_to_parquet_and_cover_files(controllers, monkeypatch, tmp_path):
    import numpy as np
    from osgeo import gdal, osr

    _, rap = controllers
    projection = osr.SpatialReference()
    projection.ImportFromEPSG(32611)
    for filename, values in [(str(tmp_path / "subwta.tif"), [11]),
                             (rap._rap_mgr.ds["2001"], [10, 20, 30, 40, 50, 60])]:
        ds = gdal.GetDriverByName("GTiff").Create(filename, 3, 3, len(values), gdal.GDT_Float32)
        ds.SetGeoTransform((500000, 30, 0, 5100000, 0, -30))
        ds.SetProjection(projection.ExportToWkt())
        for index, value in enumerate(values, 1):
            ds.GetRasterBand(index).WriteArray(np.full((3, 3), value, dtype=np.float32))
        ds.FlushCache()
        ds = None
    rap.analyze()
    current = RAP_TS.load_detached(rap.wd)
    assert current.get_cover("11", "2001") == pytest.approx(1.6)
    frame = rap_module.pd.read_parquet(Path(rap.rap_dir, "rap_ts.parquet"))
    assert frame.sort_values("band").value.tolist() == [10, 20, 30, 40, 50, 60]
    from wepppy.nodb.mods.disturbed import Disturbed
    from wepppy.nodb.mods.revegetation import Revegetation
    monkeypatch.setattr(Disturbed, "getInstance", lambda _: SimpleNamespace(fire_date=None))
    monkeypatch.setattr(Revegetation, "tryGetInstance", lambda _: None)
    monkeypatch.setattr(rap_module.Watershed, "getInstance", lambda _: SimpleNamespace(
        translator_factory=lambda: SimpleNamespace(iter_wepp_sub_ids=lambda: iter([1]), top=lambda **_: 11)))
    runs = tmp_path / "wepp/runs"
    runs.mkdir(parents=True)
    current._init_logging()
    current.prep_cover(str(runs))
    lines = (runs / "p1.cov").read_text().splitlines()
    assert lines[0] == "2001"
    assert [float(line) for line in lines[1:]] == [60, 50, 40, 10, 30, 20]


@pytest.mark.parametrize("data", [None, {}, {"<RAP_Band.TREE: 6>": {"2001": {"1": 25.0}}}])
def test_rap_legacy_embedded_state(controllers, data):
    _, rap = controllers
    with rap.locked():
        rap.data = data
    loaded = RAP_TS.load_detached(rap.wd)
    if data:
        assert loaded.data[rap_module.RAP_Band.TREE]["2001"]["1"] == 25.0
    else:
        assert loaded.data == data


def test_unknown_commit_keeps_recovery_copies(controllers, monkeypatch):
    from wepppy.nodb import base

    _, rap = controllers
    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 25.0})
    rap.analyze()
    previous = Path(rap.rap_dir, "rap_ts.parquet").read_bytes()
    committed = False
    read_text = Path.read_text

    def fail_version(*_):
        nonlocal committed
        committed = True
        raise OSError("postcommit metadata failure")

    def unreadable(path, *args, **kwargs):
        if committed and str(path) == rap._nodb:
            raise OSError("commit readback unavailable")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(base, "write_version", fail_version)
    monkeypatch.setattr(Path, "read_text", unreadable)
    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 75.0})
    with pytest.raises(RuntimeError, match="outcome unknown"):
        rap.analyze()
    backups = list(Path(rap.rap_dir).glob(".derived-backup-*/rap_ts.parquet"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == previous
    assert Path(rap.rap_dir, "rap_ts.parquet").read_bytes() != previous
    assert not rap.islocked()


def test_artifact_postrename_stat_is_not_required(controllers, monkeypatch):
    from wepppy.nodb import _derived_build as derived

    _, rap = controllers
    stage = Path(rap.rap_dir, ".stage")
    stage.mkdir()
    (stage / "result.txt").write_text("new result")
    identity = derived._identity

    def fail_canonical_stat(path):
        if Path(path) == Path(rap.rap_dir, "result.txt"):
            raise OSError("injected postrename ESTALE")
        return identity(path)

    monkeypatch.setattr(derived, "_identity", fail_canonical_stat)
    with rap.locked():
        with derived.publish_files(stage, rap.rap_dir, rap):
            pass
    assert Path(rap.rap_dir, "result.txt").read_text() == "new result"


def test_rap_malformed_embedded_data_is_rejected(controllers):
    _, rap = controllers
    # Write a legacy payload directly: validation of a normal setter would reject it.
    path = Path(rap._nodb)
    document = json.loads(path.read_text())
    document.get("py/state", document)["data"] = ["invalid"]
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="band mapping"):
        RAP_TS.load_detached(rap.wd)


@pytest.mark.parametrize("changed", ["map", "multi", "source"])
def test_rap_spatial_rewrite_rejects_publication(controllers, monkeypatch, changed):
    _, rap = controllers
    gate = threading.Lock()
    mutated = False
    before = Path(rap._nodb).read_bytes()

    def collect(**_):
        nonlocal mutated
        with gate:
            if not mutated:
                if changed == "map":
                    monkeypatch.setattr(rap_module.Ron, "getInstance", lambda _: SimpleNamespace(
                        map=SimpleNamespace(extent=[-118, 45, -116, 46], cellsize=30)))
                elif changed == "multi":
                    Path(rap.wd, "mofe.tif").write_bytes(b"mofe map")
                    monkeypatch.setattr(NoDbBase, "multi_ofe", property(lambda _: True))
                else:
                    Path(rap._rap_mgr.ds["2001"]).write_bytes(b"changed raster")
                mutated = True
        return {"1": 25.0}

    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", collect)
    with pytest.raises(RuntimeError, match="superseded"):
        rap.analyze()
    assert Path(rap._nodb).read_bytes() == before
    assert not Path(rap.rap_dir, "rap_ts.parquet").exists()


@pytest.mark.parametrize("failure", ["collection", "relevant", "malformed"])
def test_gridmet_failure_preserves_previous_results(controllers, monkeypatch, failure):
    from wepppy.nodb.core import climate as module

    climate, _ = controllers
    before = Path(climate._nodb).read_bytes()
    old_cli = Path(climate.cli_dir, "old.cli").read_bytes()
    monkeypatch.setattr(module, "CligenStationsManager", lambda **_: SimpleNamespace(
        get_station_fromid=lambda _: SimpleNamespace(par="station.par")))
    monkeypatch.setattr(module, "Cligen", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(module, "ClimateFile", lambda _: SimpleNamespace(calc_monthlies=lambda: [1.0]))

    def build(*args, **_):
        Path(args[5], "wepp.cli").write_text("collected")
        if failure == "collection":
            raise ValueError("injected collection failure")
        value = None if failure == "malformed" else 2002
        _same_size_rewrite(climate, "_observed_end_year", value)

    monkeypatch.setattr(module, "build_observed_gridmet", build)
    with pytest.raises((ValueError, RuntimeError), match="injected collection|superseded"):
        climate._build_climate_observed_gridmet()
    current = Climate.load_detached(climate.wd)
    assert current.cli_fn == "old.cli"
    assert Path(climate.cli_dir, "old.cli").read_bytes() == old_cli
    assert not Path(climate.cli_dir, "wepp.cli").exists()
    if failure == "collection":
        assert Path(climate._nodb).read_bytes() == before


@pytest.mark.parametrize("conflict", [False, True])
def test_rap_acquisition_failure_preserves_previous_rasters(controllers, monkeypatch, conflict):
    _, rap = controllers
    before = Path(rap._nodb).read_bytes()
    raster = Path(rap._rap_mgr.ds["2001"])
    previous = raster.read_bytes()

    def retrieve(manager, years):
        filename = Path(manager.wd, f"_rap_v3_{years[0]}.tif")
        filename.write_bytes(b"uncommitted raster")
        manager.ds[str(years[0])] = str(filename)
        if conflict:
            _same_size_rewrite(rap, "_rap_end_year", 2002)
            return 0
        raise ValueError("injected retrieval failure")

    monkeypatch.setattr(RangelandAnalysisPlatformV3, "retrieve", retrieve)
    with pytest.raises((ValueError, RuntimeError), match="injected retrieval|superseded"):
        rap.acquire_rasters()
    assert raster.read_bytes() == previous
    if not conflict:
        assert Path(rap._nodb).read_bytes() == before


def test_rap_collection_logs_year_band_and_progress(controllers, monkeypatch, caplog):
    import logging

    _, rap = controllers
    rap.logger = logging.getLogger("tests.rap.progress")
    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", lambda **_: {"1": 25.0})
    with caplog.at_level(logging.INFO, logger="tests.rap.progress"):
        rap.analyze()
    assert "analysis year 2001 band TREE complete" in caplog.text
    assert "(6/6)" in caplog.text
    rap.logger = logging.getLogger("tests.rap.progress")

    def fail(**_):
        raise ValueError("injected backend failure")

    monkeypatch.setattr(rap_module, "identify_median_single_raster_key", fail)
    with caplog.at_level(logging.INFO, logger="tests.rap.progress"):
        with pytest.raises(ValueError, match="injected backend"):
            rap.analyze()
    assert "RAP collection failed: analysis year 2001 band" in caplog.text
