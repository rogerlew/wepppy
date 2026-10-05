"""Real-file Daymet/Multiple ownership, artifact, and consumer regressions."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core.climate import Climate, ClimateMode
from wepppy.nodb.core import climate_build_helpers as helpers
from tests.nodb.test_batch_climate_rap_contention import controllers, _same_size_rewrite
from tests.rq.test_project_rq_archive import archive_rq_environment
from tests.microservices.test_browse_routes import load_browse, load_run_browse, TestClient

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("phase", ["daymet", "prism"])
def test_daymet_multiple_same_size_rewrite_survives(controllers, monkeypatch, phase):
    """Exercise the observed Multiple router with real serializer interleavings."""
    from wepppy.nodb.core import climate as module
    from wepppy.nodb.core.climate import ClimateSpatialMode

    climate, _ = controllers
    _prepare_observed_router(climate, monkeypatch)
    with climate.locked():
        climate._climate_mode = ClimateMode.Observed
        climate._climate_spatialmode = ClimateSpatialMode.Multiple
    monkeypatch.setattr(module, "CligenStationsManager", lambda **_: SimpleNamespace(
        get_station_fromid=lambda _: SimpleNamespace(par="station.par")))
    monkeypatch.setattr(module, "Cligen", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(module, "ClimateFile", lambda _: SimpleNamespace(calc_monthlies=lambda: [1.0]))

    def collect(*args, **kwargs):
        if phase == "daymet":
            _same_size_rewrite(climate, "_test_unrelated", "KEEP")
        Path(args[5], "wepp.cli").write_text("collected climate")

    monkeypatch.setattr(module, "build_observed_daymet", collect)
    monkeypatch.setattr(helpers, "_retrieve_prism_revision_tiles", lambda *args: None)
    monkeypatch.setattr(helpers, "_collect_prism_revision_monthlies", lambda *args: ([], [], []))
    monkeypatch.setattr(helpers, "ClimateFile", lambda path: SimpleNamespace(cli_fn=path, breakpoint=False))

    def revise(*args):
        if phase == "prism":
            _same_size_rewrite(climate, "_test_unrelated", "KEEP")
        Path(args[-1]).write_text("new hillslope")

    monkeypatch.setattr(helpers, "cli_revision", revise)
    from wepppy.nodb import base, batch_runner
    from wepppy.runtime_paths import thaw_freeze
    monkeypatch.setattr(thaw_freeze, "_runtime_lock_redis_client", lambda: base.redis_lock_client)
    monkeypatch.setattr(batch_runner, "clear_nodb_file_cache", lambda runid, **kwargs:
        base.clear_nodb_file_cache(runid, wd_override=climate.wd, **kwargs))
    batch_runner._run_with_climate_leaf_lock(climate.wd,
        lambda: batch_runner._build_climate_at_mutation_boundary(climate.runid, climate.wd),
        purpose="batch-wiring-test")
    current = Climate.load_detached(climate.wd)
    assert current._test_unrelated == "KEEP"
    assert current.monthlies == [1.0]
    assert Path(current.cli_path).read_text() == "collected climate"
    assert Path(current.cli_dir, "_1.cli").read_text() == "new hillslope"


def _prepare_observed_router(climate, monkeypatch):
    from wepppy.nodb.core import climate as module
    from wepppy.nodb.core.climate_build_router import ClimateBuildRouter
    from wepppy.nodb.core.climate_mode_build_services import ClimateModeBuildServices
    from wepppy.nodb.core.climate import ClimateSpatialMode

    with climate.locked():
        climate._climate_mode = ClimateMode.Observed
        climate._climate_spatialmode = ClimateSpatialMode.Single
    climate.watershed_instance.is_abstracted = True
    noop = SimpleNamespace(validate_scaling_inputs=lambda _: None, apply_scaling=lambda _: None)
    router = ClimateBuildRouter(
        mode_build_services=ClimateModeBuildServices(), scaling_service=noop,
        artifact_export_service=SimpleNamespace(export_post_build_artifacts=lambda _: None),
    )
    monkeypatch.setattr(module, "_CLIMATE_BUILD_ROUTER", router)
    monkeypatch.setattr(Climate, "trigger", lambda *_: None)
    monkeypatch.setattr(module, "CligenStationsManager", lambda **_: SimpleNamespace(
        get_station_fromid=lambda _: SimpleNamespace(par="station.par")))
    monkeypatch.setattr(module, "Cligen", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(module, "ClimateFile", lambda _: SimpleNamespace(calc_monthlies=lambda: [1.0]))
    return module


@pytest.mark.parametrize("failure", ["collection", "relevant", "malformed", "dump"])
def test_daymet_build_failure_retains_previous_and_attempted_artifacts(controllers, monkeypatch, failure):
    climate, _ = controllers
    module = _prepare_observed_router(climate, monkeypatch)
    before = Path(climate._nodb).read_bytes()
    previous = Path(climate.cli_path).read_bytes()
    original_replace = os.replace

    def collect(*args, **kwargs):
        assert not climate.islocked()
        assert kwargs == {
            "gridmet_wind": True,
            "adjust_mx_pt5": False,
            "silent_pass_observed_quality_guard": True,
            "randseed": None,
        }
        Path(args[5], "wepp.cli").write_text("attempted climate")
        Path(args[5], "ws.prn").write_text("attempted source")
        if failure == "collection":
            raise ValueError("injected acquisition failure")
        if failure in ("relevant", "malformed"):
            _same_size_rewrite(climate, "_observed_end_year", None if failure == "malformed" else 2002)

    def replace(source, destination):
        if failure == "dump" and str(destination) == climate._nodb:
            raise OSError("injected NoDb replace failure")
        return original_replace(source, destination)

    monkeypatch.setattr(module, "build_observed_daymet", collect)
    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises((ValueError, RuntimeError, OSError), match="injected|superseded"):
        climate.build()
    current = Climate.load_detached(climate.wd)
    assert current.cli_fn == "old.cli"
    assert Path(current.cli_path).read_bytes() == previous
    assert not Path(current.cli_dir, "wepp.cli").exists()
    attempts = list(Path(climate.cli_dir).glob("daymet-build-*"))
    assert len(attempts) == 1
    assert (attempts[0] / "wepp.cli").read_text() == "attempted climate"
    assert (attempts[0] / "ws.prn").read_text() == "attempted source"
    assert json.loads((attempts[0] / "build-status.json").read_text())["state"] == "failed"
    if failure in ("collection", "dump"):
        assert Path(climate._nodb).read_bytes() == before


@pytest.mark.parametrize("years", [(2001, 2001), ("2001", "2001")])
def test_daymet_direct_preserves_sidecars_and_normalizes_legacy_years(controllers, monkeypatch, years):
    climate, _ = controllers
    module = _prepare_observed_router(climate, monkeypatch)
    with climate.locked():
        climate._observed_start_year, climate._observed_end_year = years
    marker = Path(climate.cli_dir, "legacy-sidecar.txt")
    marker.write_text("retain")
    def collect(*args, **_):
        Path(args[5], "wepp.cli").write_text("new climate")
    monkeypatch.setattr(module, "build_observed_daymet", collect)
    climate._build_climate_observed_daymet()
    current = Climate.load_detached(climate.wd)
    assert current._observed_start_year == current._observed_end_year == 2001
    assert current.sub_cli_fns == {"1": "old.cli"}
    assert marker.read_text() == "retain"
    assert not list(Path(climate.cli_dir).glob("daymet-build-*"))


@pytest.mark.parametrize("failure", ["worker", "dump"])
def test_observed_prism_retains_failed_attempt(controllers, monkeypatch, failure):
    climate, _ = controllers
    with climate.locked():
        climate._climate_mode = ClimateMode.Observed
    before = Path(climate._nodb).read_bytes()
    monkeypatch.setattr(helpers, "_retrieve_prism_revision_tiles", lambda *args: Path(args[2]).write_text("tile"))
    monkeypatch.setattr(helpers, "_collect_prism_revision_monthlies", lambda *args: ([], [], []))
    monkeypatch.setattr(helpers, "ClimateFile", lambda path: SimpleNamespace(cli_fn=path, breakpoint=False))
    def revise(*args):
        Path(args[-1]).write_text("attempted hillslope")
        if failure == "worker":
            raise ValueError("injected worker failure")
    monkeypatch.setattr(helpers, "cli_revision", revise)
    original_replace = os.replace
    def replace(source, destination):
        if failure == "dump" and str(destination) == climate._nodb:
            raise OSError("injected NoDb replace failure")
        return original_replace(source, destination)
    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises((ValueError, OSError), match="injected"):
        climate._prism_revision()
    assert Path(climate._nodb).read_bytes() == before
    assert not Path(climate.cli_dir, "_1.cli").exists()
    attempt, = Path(climate.cli_dir).glob("prism-build-*")
    assert (attempt / "_1.cli").read_text() == "attempted hillslope"
    assert json.loads((attempt / "build-status.json").read_text())["state"] == "failed"


@pytest.mark.parametrize("projection", [False, True])
def test_batch_leaf_guard_excludes_duplicate_before_and_after_root_reset(controllers, monkeypatch, projection):
    from wepppy.nodb import base, batch_runner
    from wepppy.runtime_paths import thaw_freeze
    from wepppy.runtime_paths.errors import NoDirError
    climate, _ = controllers
    monkeypatch.setattr(thaw_freeze, "_runtime_lock_redis_client", lambda: base.redis_lock_client)
    monkeypatch.setattr(batch_runner, "_BATCH_LOCK_RETRY_ATTEMPTS", 1)
    root = Path(climate.cli_dir)
    if projection:
        root.rename(root.with_name("projected-climate"))
        root.symlink_to(root.with_name("projected-climate"), target_is_directory=True)
    before_key = thaw_freeze.maintenance_lock_key(climate.wd, "climate", scope="effective_root_path")
    calls = []
    def duplicate():
        with pytest.raises(NoDirError, match="already held"):
            batch_runner._run_with_climate_leaf_lock(
                climate.wd, lambda: calls.append("duplicate"), purpose="duplicate",
            )
    def owned():
        calls.append("owner")
        duplicate()
        if projection:
            root.unlink()
            root.mkdir()
            assert thaw_freeze.maintenance_lock_key(climate.wd, "climate", scope="effective_root_path") != before_key
            duplicate()
    batch_runner._run_with_climate_leaf_lock(climate.wd, owned, purpose="test-owner")
    assert calls == ["owner"]
    batch_runner._run_with_climate_leaf_lock(climate.wd, lambda: calls.append("next"), purpose="next")
    assert calls == ["owner", "next"]


def test_batch_leaf_guard_does_not_replay_callback_lock_failure(controllers, monkeypatch):
    from wepppy.nodb import base, batch_runner
    from wepppy.runtime_paths import thaw_freeze
    from wepppy.runtime_paths.errors import NoDirError
    climate, _ = controllers
    monkeypatch.setattr(thaw_freeze, "_runtime_lock_redis_client", lambda: base.redis_lock_client)
    calls = []
    def owned():
        calls.append("startup")
        raise NoDirError(http_status=409, code="NODIR_LOCKED", message="nested lock failure")
    with pytest.raises(NoDirError, match="nested lock failure"):
        batch_runner._run_with_climate_leaf_lock(climate.wd, owned, purpose="test-owner")
    assert calls == ["startup"]


def test_batch_startup_preserves_live_standalone_climate_token(controllers, monkeypatch):
    from wepppy.nodb import base, batch_runner
    climate, _ = controllers
    monkeypatch.setattr(batch_runner, "clear_nodb_file_cache",
        lambda runid: base.clear_nodb_file_cache(runid, wd_override=climate.wd))
    with climate.locked():
        batch_runner._clear_batch_leaf_nodb_state(climate.runid, climate.logger)
        climate._assert_lock_owned_for_dump()
        climate._test_unrelated = "KEEP"
    assert Climate.load_detached(climate.wd)._test_unrelated == "KEEP"


@pytest.mark.parametrize("legacy", [False, True])
def test_batch_climate_resync_hydrates_under_lock_and_preserves_unrelated_edit(controllers, monkeypatch, tmp_path, legacy):
    from wepppy.nodb import batch_runner
    climate, _ = controllers
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    document = json.loads(Path(climate._nodb).read_text())
    document.get("py/state", document)["_observed_end_year"] = 2002
    if legacy:
        import sys
        monkeypatch.delitem(sys.modules, "wepppy.nodb.climate", raising=False)
        document["py/object"] = "wepppy.nodb.climate.Climate"
        document.get("py/state", document)["_climate_spatialmode"] = {
            "py/reduce": [{"py/type": "wepppy.nodb.climate.ClimateSpatialMode"}, {"py/tuple": [0]}],
        }
    (base_dir / "climate.nodb").write_text(json.dumps(document))
    runner = batch_runner.BatchRunner.__new__(batch_runner.BatchRunner)
    runner.wd = str(tmp_path / "batch")
    monkeypatch.setattr(batch_runner.BatchRunner, "base_wd", property(lambda _: str(base_dir)))
    monkeypatch.setattr(runner, "BASE_PROJECT_RESYNC_RULES", {
        "climate.nodb": {"attributes": ["_observed_end_year", "_climate_spatialmode"], "invalidate_tasks": []},
    })
    original_lock = Climate.lock
    def lock(self, *args, **kwargs):
        original_lock(self, *args, **kwargs)
        _same_size_rewrite(self, "_test_unrelated", "KEEP")
    monkeypatch.setattr(Climate, "lock", lock)
    runner.resync_base_project_attributes(climate.wd, SimpleNamespace(), climate.logger)
    current = Climate.load_detached(climate.wd)
    assert current._test_unrelated == "KEEP"
    assert current._observed_end_year == 2002
    if legacy:
        from wepppy.nodb.core.climate import ClimateSpatialMode
        assert current._climate_spatialmode is ClimateSpatialMode.Single


@pytest.mark.integration
@pytest.mark.slow
def test_daymet_real_cligen_artifact_parity_and_downstream_copy(controllers, monkeypatch, tmp_path):
    """Real numerical builder/CLIGEN/parser, with only acquisition supplied offline."""
    import hashlib
    from contextlib import nullcontext
    import numpy as np
    import pandas as pd
    import rasterio
    from rasterio.transform import from_origin
    from wepppy.nodb.core import climate as module
    from wepppy.climates import daymet
    from wepppy.nodb.core.wepp_prep_service import WeppPrepService
    climate, _ = controllers
    station = module.CligenStationsManager(version="2015").stations[0]
    with climate.locked():
        climate._observed_start_year = climate._observed_end_year = 2001
        climate._cligen_db = "2015"
        climate._climatestation = station.id
        climate._use_gridmet_wind_when_applicable = False
        climate._climate_mode = ClimateMode.Observed
        climate.sub_cli_fns = climate.sub_par_fns = None
    source = pd.DataFrame({
        "prcp(mm/day)": 2.54, "tmax(degc)": 15.0, "tmin(degc)": 5.0,
        "srad(l/day)": 200.0, "tdew(degc)": 3.0,
    }, index=pd.date_range("2001-01-01", "2001-12-31"))
    monkeypatch.setattr(daymet, "retrieve_historical_timeseries", lambda *_, **__: source.copy(deep=True))
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    module.build_observed_daymet(
        module.Cligen(station, wd=str(baseline)), -116.5, 45.5, 2001, 2001,
        str(baseline), "ws.prn", "wepp.cli", gridmet_wind=False,
        adjust_mx_pt5=False, silent_pass_observed_quality_guard=True,
    )
    climate._build_climate_observed_daymet()
    current = Climate.load_detached(climate.wd)
    parsed = module.ClimateFile(current.cli_path).as_dataframe()
    pd.testing.assert_frame_equal(parsed, module.ClimateFile(str(baseline / "wepp.cli")).as_dataframe())
    assert len(parsed) == 365
    pd.testing.assert_frame_equal(pd.read_parquet(Path(current.cli_dir, "daymet_2001-2001.parquet")), source, check_freq=False)
    pd.testing.assert_frame_equal(
        pd.read_csv(Path(current.cli_dir, "ws.prn"), sep=r"\s+", header=None),
        pd.read_csv(baseline / "ws.prn", sep=r"\s+", header=None),
    )
    # Only remote tile retrieval is supplied offline; GDAL sampling and
    # PRISM numeric CLI revision run unchanged on real twelve-band rasters.
    def retrieve(_climate, _map, ppt, tmin, tmax):
        for path, value in ((ppt, 100.0), (tmin, 5.0), (tmax, 15.0)):
            with rasterio.open(path, "w", driver="GTiff", height=4, width=4,
                    count=12, dtype="float32", crs="EPSG:4326",
                    transform=from_origin(-117, 46, 0.25, 0.25)) as dataset:
                dataset.write(np.full((12, 4, 4), value, dtype="float32"))
    monkeypatch.setattr(helpers, "_retrieve_prism_revision_tiles", retrieve)
    baseline_climate = SimpleNamespace(
        climate_mode=ClimateMode.Vanilla, wd=climate.wd, cli_dir=str(baseline),
        cli_path=str(baseline / "wepp.cli"), logger=climate.logger,
        watershed_instance=climate.watershed_instance, ron_instance=climate.ron_instance,
        wmesque_version=climate.wmesque_version, wmesque_endpoint=climate.wmesque_endpoint,
        locked=lambda: nullcontext(),
    )
    helpers.run_prism_revision(baseline_climate)
    climate._prism_revision()
    current = Climate.load_detached(climate.wd)
    revised = module.ClimateFile(str(Path(current.cli_dir, "_1.cli"))).as_dataframe()
    pd.testing.assert_frame_equal(revised,
        module.ClimateFile(str(baseline / "_1.cli")).as_dataframe())
    runs = tmp_path / "wepp" / "runs"
    runs.mkdir(parents=True)
    wepp = SimpleNamespace(wd=climate.wd, climate_instance=current,
        watershed_instance=SimpleNamespace(sub_n=1, _subs_summary={"1": {}}),
        runs_dir=str(runs), logger=climate.logger, class_name="Wepp")
    WeppPrepService().prep_climates(wepp, SimpleNamespace(wepp=lambda **_: 1))
    consumed = runs / "p1.cli"
    pd.testing.assert_frame_equal(module.ClimateFile(str(consumed)).as_dataframe(), revised)
    assert consumed.read_bytes() == Path(current.cli_dir, "_1.cli").read_bytes()
    manifest = {str(path.relative_to(Path(current.cli_dir))): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in Path(current.cli_dir).iterdir() if path.is_file()}
    assert {"wepp.cli", "ws.prn", "daymet_2001-2001.parquet", station.par} <= manifest.keys()


@pytest.mark.parametrize("state", ["working", "failed"])
@pytest.mark.parametrize("kind", ["daymet", "prism"])
def test_observed_attempt_browser_archive_restore(controllers, monkeypatch, archive_rq_environment, load_run_browse, state, kind):
    import zipfile
    climate, _ = controllers
    module = _prepare_observed_router(climate, monkeypatch)
    project, _, _, _ = archive_rq_environment
    monkeypatch.setattr(project, "get_wd", lambda _: climate.wd)
    with climate.locked():
        climate._climate_mode = ClimateMode.Observed
    captured = []
    def retain_and_fail(stage):
        Path(stage, "attempt.cli").write_bytes(b"inspectable attempted climate")
        if state == "working":
            project.archive_rq("demo", comment="working observed attempt")
            captured.append(next(Path(climate.wd, "archives").glob("*.zip")))
        raise ValueError("injected attempt failure")
    if kind == "daymet":
        monkeypatch.setattr(module, "build_observed_daymet", lambda *args, **_: retain_and_fail(args[5]))
        operation = climate._build_climate_observed_daymet
    else:
        monkeypatch.setattr(helpers, "_retrieve_prism_revision_tiles", lambda *args: retain_and_fail(Path(args[2]).parent))
        operation = climate._prism_revision
    with pytest.raises(ValueError, match="injected attempt"):
        operation()
    attempt, = Path(climate.cli_dir).glob(f"{kind}-build-*")
    relative = attempt.relative_to(Path(climate.wd)).as_posix()
    browse = load_run_browse({"demo": Path(climate.wd)}, SITE_PREFIX="/weppcloud")
    with TestClient(browse.create_app()) as client:
        listing = client.get("/weppcloud/runs/demo/cfg/browse/climate/")
        download = client.get(f"/weppcloud/runs/demo/cfg/browse/{relative}/attempt.cli?download")
        status = client.get(f"/weppcloud/runs/demo/cfg/browse/{relative}/build-status.json?raw")
    assert listing.status_code == download.status_code == status.status_code == 200
    assert attempt.name in listing.text
    assert download.content == b"inspectable attempted climate"
    assert status.json()["state"] == "failed"
    if state == "failed":
        project.archive_rq("demo", comment="failed observed attempt")
        captured.append(next(Path(climate.wd, "archives").glob("*.zip")))
    archive = captured[0]
    with zipfile.ZipFile(archive) as z:
        assert z.read(f"{relative}/attempt.cli") == b"inspectable attempted climate"
        assert json.loads(z.read(f"{relative}/build-status.json"))["state"] == state
    (attempt / "attempt.cli").write_bytes(b"later edit")
    project.restore_archive_rq("demo", archive.name)
    assert (attempt / "attempt.cli").read_bytes() == b"inspectable attempted climate"
    assert json.loads((attempt / "build-status.json").read_text())["state"] == state


@pytest.mark.parametrize("root_state", ["absent", "empty", "populated"])
@pytest.mark.parametrize("mode", [ClimateMode.Observed, ClimateMode.ObservedPRISM])
@pytest.mark.parametrize("multiple", [False, True])
def test_observed_build_valid_state_matrix(controllers, monkeypatch, root_state, mode, multiple):
    import shutil
    from wepppy.nodb.core.climate import ClimateSpatialMode
    from wepppy.nodb.core import climate_build_router
    climate, _ = controllers
    module = _prepare_observed_router(climate, monkeypatch)
    with climate.locked():
        climate._climate_mode = mode
        climate._climate_spatialmode = ClimateSpatialMode.Multiple if multiple else ClimateSpatialMode.Single
    root = Path(climate.cli_dir)
    if root_state != "populated":
        shutil.rmtree(root)
        if root_state == "empty":
            root.mkdir()
    timestamps = []
    def timestamp(task):
        assert Path(climate.cli_path).read_text() == "accepted climate"
        if multiple:
            assert Path(climate.cli_dir, "_1.cli").read_text() == "accepted hillslope"
        timestamps.append(task)
    monkeypatch.setattr(climate_build_router.RedisPrep, "getInstance", lambda _: SimpleNamespace(timestamp=timestamp))
    def collect(*args, **_):
        Path(args[5], "wepp.cli").write_text("accepted climate")
    monkeypatch.setattr(module, "build_observed_daymet", collect)
    monkeypatch.setattr(helpers, "_retrieve_prism_revision_tiles", lambda *args: None)
    monkeypatch.setattr(helpers, "_collect_prism_revision_monthlies", lambda *args: ([], [], []))
    monkeypatch.setattr(helpers, "ClimateFile", lambda path: SimpleNamespace(cli_fn=path, breakpoint=False))
    monkeypatch.setattr(helpers, "cli_revision", lambda *args: Path(args[-1]).write_text("accepted hillslope"))
    climate.build()
    current = Climate.load_detached(climate.wd)
    assert current.has_climate
    assert current.cli_fn == "wepp.cli"
    assert (current.sub_cli_fns is not None) == multiple
    assert not (root / "old.cli").exists()
    assert len(timestamps) == 1


def test_unknown_commit_recovery_records_remain_visible_and_archivable(controllers, monkeypatch, archive_rq_environment, load_run_browse):
    import zipfile
    climate, _ = controllers
    module = _prepare_observed_router(climate, monkeypatch)
    old = Path(climate.cli_path).read_bytes()
    def collect(*args, **_):
        Path(args[5], "wepp.cli").write_text("attempted climate")
    monkeypatch.setattr(module, "build_observed_daymet", collect)
    original_replace, original_read = os.replace, Path.read_text
    failed = False
    def replace(source, destination):
        nonlocal failed
        if str(destination) == climate._nodb:
            failed = True
            raise OSError("injected NoDb failure")
        return original_replace(source, destination)
    def read(path, *args, **kwargs):
        if failed and str(path) == climate._nodb:
            raise OSError("injected commit readback failure")
        return original_read(path, *args, **kwargs)
    with monkeypatch.context() as fault:
        fault.setattr(os, "replace", replace)
        fault.setattr(Path, "read_text", read)
        with pytest.raises(RuntimeError, match="commit outcome unknown"):
            climate.build()
    backup, = Path(climate.cli_dir).glob("derived-backup-*")
    assert (backup / "old.cli").read_bytes() == old
    relative = backup.relative_to(Path(climate.wd)).as_posix()
    browse = load_run_browse({"demo": Path(climate.wd)}, SITE_PREFIX="/weppcloud")
    with TestClient(browse.create_app()) as client:
        listing = client.get("/weppcloud/runs/demo/cfg/browse/climate/")
        response = client.get(f"/weppcloud/runs/demo/cfg/browse/{relative}/old.cli?download")
    assert listing.status_code == response.status_code == 200
    assert backup.name in listing.text
    assert response.content == old
    project, _, _, _ = archive_rq_environment
    monkeypatch.setattr(project, "get_wd", lambda _: climate.wd)
    project.archive_rq("demo", comment="unknown commit recovery")
    archive = next(Path(climate.wd, "archives").glob("*.zip"))
    with zipfile.ZipFile(archive) as z:
        assert z.read(f"{relative}/old.cli") == old
    (backup / "old.cli").write_bytes(b"later overwrite")
    project.restore_archive_rq("demo", archive.name)
    assert (backup / "old.cli").read_bytes() == old


def test_multiple_prism_failure_retains_committed_daymet_and_blocks_wepp(controllers, monkeypatch):
    from wepppy.nodb.core.climate import ClimateSpatialMode
    from wepppy.nodb.core import climate_build_router, wepp_prep_service
    climate, _ = controllers
    module = _prepare_observed_router(climate, monkeypatch)
    with climate.locked():
        climate._climate_spatialmode = ClimateSpatialMode.Multiple
    timestamps, exported, events = [], [], []
    monkeypatch.setattr(climate_build_router.RedisPrep, "getInstance", lambda _: SimpleNamespace(timestamp=timestamps.append))
    monkeypatch.setattr(module._CLIMATE_BUILD_ROUTER._artifact_export_service,
        "export_post_build_artifacts", lambda _: exported.append("export"))
    monkeypatch.setattr(Climate, "trigger", lambda *args: events.append(args))
    def collect(*args, **_):
        Path(args[5], "wepp.cli").write_text("committed channel")
    monkeypatch.setattr(module, "build_observed_daymet", collect)
    monkeypatch.setattr(helpers, "_retrieve_prism_revision_tiles", lambda *args: None)
    monkeypatch.setattr(helpers, "_collect_prism_revision_monthlies", lambda *args: ([], [], []))
    monkeypatch.setattr(helpers, "ClimateFile", lambda path: SimpleNamespace(cli_fn=path, breakpoint=False))
    def revise(*args):
        Path(args[-1]).write_text("failed hillslope attempt")
        raise ValueError("injected PRISM failure")
    monkeypatch.setattr(helpers, "cli_revision", revise)
    with pytest.raises(ValueError, match="injected PRISM"):
        climate.build()
    current = Climate.load_detached(climate.wd)
    assert Path(current.cli_path).read_text() == "committed channel"
    assert current.sub_cli_fns is current.sub_par_fns is None
    assert not current.has_climate
    assert current.sub_summary("1") is None
    assert not Path(current.cli_dir, "old.cli").exists()
    attempt, = Path(current.cli_dir).glob("prism-build-*")
    assert (attempt / "_1.cli").read_text() == "failed hillslope attempt"
    assert timestamps == exported == events == []
    clock = iter([0, 31])
    monkeypatch.setattr(wepp_prep_service, "time", SimpleNamespace(time=lambda: next(clock), sleep=lambda _: None))
    wepp = SimpleNamespace(climate_instance=current, logger=climate.logger, class_name="Wepp")
    with pytest.raises(ValueError, match="Climate inputs are not ready"):
        wepp_prep_service.WeppPrepService().prep_climates(wepp, None)
