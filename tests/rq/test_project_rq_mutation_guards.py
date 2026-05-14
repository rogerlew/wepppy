from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.project_rq as project_rq
from wepppy.runtime_paths.errors import NoDirError

pytestmark = pytest.mark.unit


def _stub_rq_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    run_wd = tmp_path / "run"
    run_wd.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(project_rq, "get_wd", lambda _runid: str(run_wd))
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-guard"))
    monkeypatch.setattr(project_rq.StatusMessenger, "publish", lambda *_args, **_kwargs: None)
    archive_roots: set[str] = set()
    call_roots: list[str] = []

    def _set_archive_roots(*roots: str) -> None:
        archive_roots.clear()
        archive_roots.update(roots)

    def _resolve(_wd: str, root: str, view: str = "effective"):
        call_roots.append(root)
        if root in archive_roots:
            raise NoDirError(
                http_status=409,
                code="NODIR_ARCHIVE_RETIRED",
                message=f"{root}.nodir exists but archive-backed runtime access is retired",
            )
        return SimpleNamespace(form="dir")

    monkeypatch.setattr(project_rq, "nodir_resolve", _resolve)

    @contextmanager
    def _lock(_wd: str, _root: str, *, purpose: str):
        yield

    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)
    return run_wd, _set_archive_roots, call_roots


def _record_cache_clears(monkeypatch: pytest.MonkeyPatch, events: list[tuple]) -> None:
    def _clear(runid: str, pup_relpath: str | None = None) -> None:
        events.append(("clear", runid, pup_relpath))

    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", _clear)


def _record_prep_timestamps(monkeypatch: pytest.MonkeyPatch, events: list[tuple]) -> None:
    class DummyPrep:
        def timestamp(self, task) -> None:
            events.append(("timestamp", task))

        def get_rq_job_id(self, _key: str):
            return "job-guard"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())


@pytest.mark.parametrize(
    ("mods", "expected_scope"),
    [
        (["disturbed"], "disturbed.nodb"),
        (["baer"], "baer.nodb"),
    ],
)
def test_init_sbs_map_rq_clears_sbs_mod_cache_before_mod_hydration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mods: list[str],
    expected_scope: str,
) -> None:
    run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)
    _record_prep_timestamps(monkeypatch, events)

    class DummyRon:
        def __init__(self) -> None:
            self.mods = mods
            self._sbs_controller = object()

        @property
        def disturbed(self):
            assert events[-1] == ("clear", "demo", expected_scope)
            events.append(("hydrate_sbs_mod", expected_scope))
            return self._sbs_controller

        def init_sbs_map(self, sbs_map: str, controller) -> None:
            assert controller is self._sbs_controller
            events.append(("init_sbs_map", sbs_map))

    def _get_ron(wd: str) -> DummyRon:
        events.append(("hydrate_ron", wd))
        return DummyRon()

    monkeypatch.setattr(project_rq.Ron, "getInstance", _get_ron)

    project_rq.init_sbs_map_rq("demo", "sbs-map.tif")

    assert events == [
        ("hydrate_ron", str(run_wd)),
        ("clear", "demo", expected_scope),
        ("hydrate_sbs_mod", expected_scope),
        ("init_sbs_map", "sbs-map.tif"),
        ("timestamp", project_rq.TaskEnum.init_sbs_map),
    ]


def test_fetch_dem_rq_clears_ron_cache_before_hydration_and_fetch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)

    class DummyRon:
        max_map_dimension_px = 10_000

        def set_map(self, extent, center, zoom) -> None:
            events.append(("set_map", tuple(extent), tuple(center), zoom))
            self.map = SimpleNamespace(num_cols=128, num_rows=64)

        def fetch_dem(self) -> None:
            events.append(("fetch_dem", None))

    def _get_ron(wd: str) -> DummyRon:
        assert events == [("clear", "demo", "ron.nodb")]
        events.append(("hydrate_ron", wd))
        return DummyRon()

    monkeypatch.setattr(project_rq.Ron, "getInstance", _get_ron)

    project_rq.fetch_dem_rq("demo", [0.0, 2.0, 10.0, 12.0], None, None)

    assert events == [
        ("clear", "demo", "ron.nodb"),
        ("hydrate_ron", str(run_wd)),
        ("set_map", (0.0, 2.0, 10.0, 12.0), (5.0, 7.0), project_rq.DEFAULT_ZOOM),
        ("fetch_dem", None),
    ]


def test_fetch_dem_and_build_channels_rq_clears_watershed_cache_before_enqueue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)

    class DummyWatershed:
        def __init__(self) -> None:
            self.uploaded_dem_filename = "uploaded.tif"

    dummy_watershed = DummyWatershed()

    def _get_watershed(wd: str) -> DummyWatershed:
        assert events == [("clear", "demo", "watershed.nodb")]
        events.append(("hydrate_watershed", wd))
        return dummy_watershed

    monkeypatch.setattr(project_rq.Watershed, "getInstance", _get_watershed)

    class DummyRedis:
        def __init__(self, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

    class DummyQueue:
        def __init__(self, connection) -> None:
            self.connection = connection

        def enqueue_call(self, func, args, depends_on=None, timeout=None):
            child_id = f"child-{len([event for event in events if event[0] == 'enqueue'])}"
            events.append(("enqueue", func.__name__, args, getattr(depends_on, "id", None), timeout))
            return SimpleNamespace(id=child_id)

    current_job = SimpleNamespace(id="job-guard", meta={}, save=lambda: events.append(("save", dict(current_job.meta))))
    monkeypatch.setattr(project_rq, "get_current_job", lambda: current_job)
    monkeypatch.setattr(project_rq.redis, "Redis", DummyRedis)
    monkeypatch.setattr(project_rq, "Queue", DummyQueue)

    project_rq.fetch_dem_and_build_channels_rq(
        "demo",
        [0.0, 0.0, 1.0, 1.0],
        None,
        None,
        csa=10.0,
        mcl=50.0,
        stream_pruning_method=None,
        wbt_fill_or_breach=None,
        wbt_blc_dist=None,
        set_extent_mode=1,
        map_bounds_text="bounds",
    )

    assert events[:2] == [
        ("clear", "demo", "watershed.nodb"),
        ("hydrate_watershed", str(run_wd)),
    ]
    assert [event[0] for event in events if event[0] == "enqueue"] == ["enqueue", "enqueue"]
    enqueue_events = [event for event in events if event[0] == "enqueue"]
    assert [event[4] for event in enqueue_events] == [
        project_rq.FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT,
        project_rq.FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT,
    ]
    assert current_job.meta["jobs:0,func:fetch_dem_rq"] == "child-0"
    assert current_job.meta["jobs:1,func:build_channels_rq"] == "child-1"
    assert dummy_watershed.uploaded_dem_filename is None


def test_fetch_dem_and_build_channels_rq_preserves_uploaded_dem_for_upload_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)

    class DummyWatershed:
        def __init__(self) -> None:
            self.uploaded_dem_filename = "uploaded.tif"

    dummy_watershed = DummyWatershed()

    def _get_watershed(wd: str) -> DummyWatershed:
        assert events == [("clear", "demo", "watershed.nodb")]
        events.append(("hydrate_watershed", wd))
        return dummy_watershed

    monkeypatch.setattr(project_rq.Watershed, "getInstance", _get_watershed)

    class DummyRedis:
        def __init__(self, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

    class DummyQueue:
        def __init__(self, connection) -> None:
            self.connection = connection

        def enqueue_call(self, func, args, depends_on=None, timeout=None):
            child_id = f"child-{len([event for event in events if event[0] == 'enqueue'])}"
            events.append(("enqueue", func.__name__, args, getattr(depends_on, "id", None), timeout))
            return SimpleNamespace(id=child_id)

    current_job = SimpleNamespace(id="job-guard", meta={}, save=lambda: events.append(("save", dict(current_job.meta))))
    monkeypatch.setattr(project_rq, "get_current_job", lambda: current_job)
    monkeypatch.setattr(project_rq.redis, "Redis", DummyRedis)
    monkeypatch.setattr(project_rq, "Queue", DummyQueue)

    project_rq.fetch_dem_and_build_channels_rq(
        "demo",
        None,
        None,
        None,
        csa=10.0,
        mcl=50.0,
        stream_pruning_method=None,
        wbt_fill_or_breach=None,
        wbt_blc_dist=None,
        set_extent_mode=3,
        map_bounds_text="bounds",
    )

    assert events[:2] == [
        ("clear", "demo", "watershed.nodb"),
        ("hydrate_watershed", str(run_wd)),
    ]
    assert [event[0] for event in events if event[0] == "enqueue"] == ["enqueue"]
    enqueue_event = next(event for event in events if event[0] == "enqueue")
    assert enqueue_event[4] == project_rq.FETCH_DEM_AND_BUILD_CHANNELS_CHILD_TIMEOUT
    assert current_job.meta["jobs:0,func:build_channels_rq"] == "child-0"
    assert dummy_watershed.uploaded_dem_filename == "uploaded.tif"


def test_build_channels_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("watershed")
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Archive-backed watershed roots should be rejected before cache clear")
        ),
    )
    monkeypatch.setattr(
        project_rq.Watershed,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Watershed should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_channels_rq(
            "demo",
            csa=10.0,
            mcl=50.0,
            stream_pruning_method=None,
            wbt_fill_or_breach=None,
            wbt_blc_dist=None,
        )

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["watershed"]


def test_build_landuse_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("landuse")
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Archive-backed landuse roots should be rejected before cache clear")
        ),
    )
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Landuse should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_landuse_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["landuse"]


def test_build_landuse_rq_clears_scoped_cache_before_hydration_and_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)
    _record_prep_timestamps(monkeypatch, events)

    class DummyLanduse:
        def build(self) -> None:
            events.append(("build", None))

    def _get_landuse(wd: str) -> DummyLanduse:
        assert events == [("clear", "demo", "landuse.nodb")]
        events.append(("hydrate_landuse", wd))
        return DummyLanduse()

    monkeypatch.setattr(project_rq.Landuse, "getInstance", _get_landuse)

    project_rq.build_landuse_rq("demo")

    assert call_roots == ["landuse", "landuse"]
    assert events == [
        ("clear", "demo", "landuse.nodb"),
        ("hydrate_landuse", str(run_wd)),
        ("build", None),
        ("timestamp", project_rq.TaskEnum.build_landuse),
    ]


def test_build_landuse_rq_preserves_original_exception_when_current_job_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq, "get_current_job", lambda: None)

    def _raise_original(*_args, **_kwargs):
        raise RuntimeError("lock boom")

    monkeypatch.setattr(project_rq, "_run_with_directory_root_lock", _raise_original)
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    with pytest.raises(RuntimeError, match="lock boom"):
        project_rq.build_landuse_rq("demo")

    assert published == [
        ("demo:landuse", "rq:unknown-job STARTED build_landuse_rq(demo)"),
        ("demo:landuse", "rq:unknown-job EXCEPTION build_landuse_rq(demo)"),
    ]


def test_build_landuse_rq_preserves_original_exception_when_exception_publish_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq, "get_current_job", lambda: None)

    def _raise_original(*_args, **_kwargs):
        raise RuntimeError("lock boom")

    monkeypatch.setattr(project_rq, "_run_with_directory_root_lock", _raise_original)
    published: list[tuple[str, str]] = []

    def _publish(channel: str, message: str) -> None:
        published.append((channel, message))
        if " EXCEPTION " in message:
            raise RuntimeError("status bus down")

    monkeypatch.setattr(project_rq.StatusMessenger, "publish", _publish)

    with pytest.raises(RuntimeError, match="lock boom"):
        project_rq.build_landuse_rq("demo")

    assert published == [
        ("demo:landuse", "rq:unknown-job STARTED build_landuse_rq(demo)"),
        ("demo:landuse", "rq:unknown-job EXCEPTION build_landuse_rq(demo)"),
    ]


def test_build_landuse_rq_preserves_original_exception_when_job_lookup_and_exception_publish_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)

    def _raise_job_lookup() -> None:
        raise RuntimeError("job lookup boom")

    monkeypatch.setattr(project_rq, "get_current_job", _raise_job_lookup)

    published: list[tuple[str, str]] = []

    def _publish(channel: str, message: str) -> None:
        published.append((channel, message))
        raise RuntimeError("status bus down")

    monkeypatch.setattr(project_rq.StatusMessenger, "publish", _publish)

    with pytest.raises(RuntimeError, match="job lookup boom"):
        project_rq.build_landuse_rq("demo")

    assert published == [
        ("demo:landuse", "rq:unknown-job EXCEPTION build_landuse_rq(demo)"),
    ]


def test_build_landuse_rq_uses_unknown_job_id_when_current_job_has_no_id_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq, "get_current_job", lambda: object())
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)
    _record_prep_timestamps(monkeypatch, events)

    class DummyLanduse:
        def build(self) -> None:
            events.append(("build", None))

    monkeypatch.setattr(project_rq.Landuse, "getInstance", lambda _wd: DummyLanduse())
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    project_rq.build_landuse_rq("demo")

    assert events == [
        ("clear", "demo", "landuse.nodb"),
        ("build", None),
        ("timestamp", project_rq.TaskEnum.build_landuse),
    ]
    assert published == [
        ("demo:landuse", "rq:unknown-job STARTED build_landuse_rq(demo)"),
        ("demo:landuse", "rq:unknown-job COMPLETED build_landuse_rq(demo)"),
        ("demo:landuse", "rq:unknown-job TRIGGER   landuse LANDUSE_BUILD_TASK_COMPLETED"),
    ]


def test_build_landuse_rq_logs_when_exception_publish_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq, "get_current_job", lambda: None)

    def _raise_original(*_args, **_kwargs):
        raise RuntimeError("lock boom")

    monkeypatch.setattr(project_rq, "_run_with_directory_root_lock", _raise_original)

    def _publish(channel: str, message: str) -> None:
        if " EXCEPTION " in message:
            raise RuntimeError("status bus down")

    monkeypatch.setattr(project_rq.StatusMessenger, "publish", _publish)
    logged: list[tuple[str, dict[str, object]]] = []

    def _capture_exception(message: str, *args, **kwargs) -> None:
        logged.append((message, kwargs))

    monkeypatch.setattr(project_rq._logger, "exception", _capture_exception)

    with pytest.raises(RuntimeError, match="lock boom"):
        project_rq.build_landuse_rq("demo")

    assert any(
        message == "Failed to publish landuse exception status update"
        and kwargs.get("extra") == {"runid": "demo", "job_id": "unknown-job"}
        for message, kwargs in logged
    )


def test_modify_landuse_mapping_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("landuse")
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd, ignore_lock=False: (_ for _ in ()).throw(
            AssertionError("Landuse should not be loaded when root is archive-backed")
        ),
    )

    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return "job-guard"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())

    with pytest.raises(NoDirError) as exc_info:
        project_rq.modify_landuse_mapping_rq("demo", [{"dom": "44", "newdom": "71"}])

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["landuse"]


def test_modify_landuse_mapping_rq_publishes_trigger_and_mutates_landuse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-latest"))

    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return "job-latest"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())
    cleared_cache: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda runid, pup_relpath=None: cleared_cache.append((runid, pup_relpath)),
    )

    class DummyLanduse:
        def __init__(self):
            self.managements: dict[str, object] = {
                "44": object(),
                "55": object(),
                "71": object(),
                "42": object(),
            }
            self.domlc_d = {"100": "44", "200": "55", "300": "71"}
            self.domlc_mofe_d = {"100": {"1": "44", "2": "71"}}
            self.build_managements_calls = 0

        @contextmanager
        def locked(self):
            yield

        def build_managements(self) -> None:
            self.build_managements_calls += 1

    landuse = DummyLanduse()

    def _get_landuse(_wd: str, ignore_lock: bool = False):
        assert ignore_lock is True
        assert cleared_cache == [("demo", "landuse.nodb")]
        return landuse

    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        _get_landuse,
    )
    monkeypatch.setattr(
        project_rq.Landuse,
        "load_detached",
        lambda _wd, allow_nonexistent=True: (_ for _ in ()).throw(
            AssertionError("modify_landuse_mapping_rq should not use load_detached")
        ),
    )

    project_rq.modify_landuse_mapping_rq(
        "demo",
        [
            {"dom": "44", "newdom": "71"},
            {"dom": "71", "newdom": "42"},
            {"dom": "44", "newdom": "55"},
        ],
    )

    assert cleared_cache == [("demo", "landuse.nodb")]
    assert landuse.domlc_d == {"100": "55", "200": "55", "300": "42"}
    assert landuse.domlc_mofe_d == {"100": {"1": "55", "2": "42"}}
    assert landuse.build_managements_calls == 1
    assert call_roots == ["landuse", "landuse"]
    assert any("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED" in message for _channel, message in published)


def test_modify_landuse_mapping_rq_skips_stale_job_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-stale"))

    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return "job-latest"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd, ignore_lock=False: (_ for _ in ()).throw(
            AssertionError("Stale jobs should not mutate landuse")
        ),
    )

    project_rq.modify_landuse_mapping_rq("demo", [{"dom": "44", "newdom": "71"}])

    assert call_roots == []
    assert any("SKIPPED" in message for _channel, message in published)
    assert all("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED" not in message for _channel, message in published)


def test_modify_landuse_mapping_rq_skips_stale_job_at_lock_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-latest"))
    cleared_cache: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda runid, pup_relpath=None: cleared_cache.append((runid, pup_relpath)),
    )

    class DummyPrep:
        def __init__(self):
            self._calls = 0

        def get_rq_job_id(self, key: str):
            self._calls += 1
            if self._calls == 1:
                return "job-latest"
            return "job-newer"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd, ignore_lock=False: (_ for _ in ()).throw(
            AssertionError("Lock-gate stale jobs should not mutate landuse")
        ),
    )

    project_rq.modify_landuse_mapping_rq("demo", [{"dom": "44", "newdom": "71"}])

    assert call_roots == ["landuse", "landuse"]
    assert cleared_cache == []
    assert any("SKIPPED" in message and "lock gate" in message for _channel, message in published)
    assert all("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED" not in message for _channel, message in published)


def test_modify_landuse_mapping_rq_rejects_unknown_dom_without_partial_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-latest"))

    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return "job-latest"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())
    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda *_args, **_kwargs: None)

    class DummyLanduse:
        def __init__(self):
            self.managements: dict[str, object] = {"44": object(), "55": object()}
            self.domlc_d = {"100": "44", "200": "55"}
            self.domlc_mofe_d = {"100": {"1": "44"}}
            self.build_managements_calls = 0

        @contextmanager
        def locked(self):
            yield

        def build_managements(self) -> None:
            self.build_managements_calls += 1

    landuse = DummyLanduse()
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd, ignore_lock=False: landuse,
    )

    with pytest.raises(ValueError) as exc_info:
        project_rq.modify_landuse_mapping_rq(
            "demo",
            [
                {"dom": "44", "newdom": "71"},
                {"dom": "999", "newdom": "55"},
            ],
        )

    assert "Unknown mapping dom value(s)" in str(exc_info.value)
    assert landuse.domlc_d == {"100": "44", "200": "55"}
    assert landuse.domlc_mofe_d == {"100": {"1": "44"}}
    assert landuse.build_managements_calls == 0
    assert call_roots == ["landuse", "landuse"]
    assert all("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED" not in message for _channel, message in published)


def test_modify_landuse_mapping_rq_rolls_back_state_when_build_managements_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-latest"))

    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return "job-latest"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())
    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda *_args, **_kwargs: None)

    class DummyLanduse:
        def __init__(self):
            self.managements: dict[str, dict[str, str]] = {
                "44": {"name": "source"},
                "71": {"name": "target"},
            }
            self.domlc_d = {"100": "44"}
            self.domlc_mofe_d = {"100": {"1": "44"}}
            self.build_managements_calls = 0

        @contextmanager
        def locked(self):
            yield

        def build_managements(self) -> None:
            self.build_managements_calls += 1
            self.managements = {"mutated": {"name": "bad"}}
            raise RuntimeError("management rebuild failed")

    landuse = DummyLanduse()
    original_managements = dict(landuse.managements)
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd, ignore_lock=False: landuse,
    )

    with pytest.raises(RuntimeError) as exc_info:
        project_rq.modify_landuse_mapping_rq("demo", [{"dom": "44", "newdom": "71"}])

    assert str(exc_info.value) == "management rebuild failed"
    assert landuse.domlc_d == {"100": "44"}
    assert landuse.domlc_mofe_d == {"100": {"1": "44"}}
    assert landuse.managements == original_managements
    assert landuse.build_managements_calls == 1
    assert call_roots == ["landuse", "landuse"]
    assert all("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED" not in message for _channel, message in published)


def test_modify_landuse_mapping_rq_accepts_legacy_three_argument_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq.StatusMessenger, "publish", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-latest"))

    class DummyPrep:
        def get_rq_job_id(self, key: str):
            return "job-latest"

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())
    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda *_args, **_kwargs: None)

    class DummyLanduse:
        def __init__(self):
            self.managements: dict[str, object] = {"44": object(), "71": object()}
            self.domlc_d = {"100": "44", "200": "71"}
            self.domlc_mofe_d = {}
            self.build_managements_calls = 0

        @contextmanager
        def locked(self):
            yield

        def build_managements(self) -> None:
            self.build_managements_calls += 1

    landuse = DummyLanduse()
    monkeypatch.setattr(
        project_rq.Landuse,
        "getInstance",
        lambda _wd, ignore_lock=False: landuse,
    )

    project_rq.modify_landuse_mapping_rq("demo", "44", "71")

    assert landuse.domlc_d == {"100": "71", "200": "71"}
    assert landuse.build_managements_calls == 1
    assert call_roots == ["landuse", "landuse"]


def test_build_treatments_rq_rejects_archive_form_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("landuse", "soils")
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Archive-backed treatment roots should be rejected before cache clear")
        ),
    )
    monkeypatch.setattr(
        project_rq.Treatments,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Treatments should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_treatments_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["landuse"]


def test_build_treatments_rq_clears_landuse_and_soils_before_hydration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)
    _record_prep_timestamps(monkeypatch, events)

    class DummyTreatments:
        def build_treatments(self) -> None:
            events.append(("build_treatments", None))

    def _get_treatments(wd: str) -> DummyTreatments:
        assert events[:2] == [
            ("clear", "demo", "landuse.nodb"),
            ("clear", "demo", "soils.nodb"),
        ]
        events.append(("hydrate_treatments", wd))
        return DummyTreatments()

    monkeypatch.setattr(project_rq.Treatments, "getInstance", _get_treatments)

    project_rq.build_treatments_rq("demo")

    assert call_roots == ["landuse", "soils", "landuse", "soils"]
    assert events == [
        ("clear", "demo", "landuse.nodb"),
        ("clear", "demo", "soils.nodb"),
        ("hydrate_treatments", str(run_wd)),
        ("build_treatments", None),
        ("timestamp", project_rq.TaskEnum.build_treatments),
    ]


def test_build_climate_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("climate")
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Archive-backed climate roots should be rejected before cache clear")
        ),
    )
    monkeypatch.setattr(
        project_rq.Climate,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Climate should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_climate_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["climate"]


def test_build_climate_rq_applies_enqueued_payload_before_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    observed_calls: list[tuple[str, object]] = []
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)

    class DummyClimate:
        def parse_inputs(self, payload) -> None:
            observed_calls.append(("parse_inputs", payload))

        def build(self) -> None:
            observed_calls.append(("build", None))

    def _get_climate(wd: str) -> DummyClimate:
        assert events == [("clear", "demo", "climate.nodb")]
        events.append(("hydrate_climate", wd))
        return DummyClimate()

    monkeypatch.setattr(project_rq.Climate, "getInstance", _get_climate)

    payload = {
        "climate_mode": 9,
        "observed_start_year": "1985",
        "observed_end_year": "2024",
        "metadata": {"source": "ui"},
    }
    monkeypatch.setattr(
        project_rq,
        "get_current_job",
        lambda: SimpleNamespace(id="job-guard", meta={"build_payload": payload}),
    )
    project_rq.build_climate_rq("demo")

    assert call_roots
    assert all(root == "climate" for root in call_roots)
    assert events == [
        ("clear", "demo", "climate.nodb"),
        ("hydrate_climate", str(run_wd)),
    ]
    assert observed_calls[0][0] == "parse_inputs"
    parsed_payload = observed_calls[0][1]
    assert parsed_payload == payload
    assert parsed_payload is not payload
    assert parsed_payload["metadata"] is not payload["metadata"]
    assert observed_calls[1] == ("build", None)


def test_build_climate_rq_warns_when_observed_start_year_is_emptied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda *_args, **_kwargs: None)
    warning_calls: list[tuple[str, object]] = []

    class DummyClimate:
        _observed_start_year = ""
        _climate_mode = 9

        def parse_inputs(self, _payload) -> None:
            # Reproduce the original fault signature: payload is non-empty
            # but climate state still contains an empty observed start year.
            self._observed_start_year = ""

        def build(self) -> None:
            return None

    monkeypatch.setattr(project_rq.Climate, "getInstance", lambda _wd: DummyClimate())
    monkeypatch.setattr(
        project_rq,
        "get_current_job",
        lambda: SimpleNamespace(
            id="job-warn",
            meta={
                "build_payload": {
                    "climate_mode": 9,
                    "observed_start_year": "1985",
                    "observed_end_year": "2024",
                }
            },
        ),
    )

    def _capture_warning(message: str, *args, **kwargs) -> None:
        warning_calls.append((message, kwargs.get("extra")))

    monkeypatch.setattr(project_rq._logger, "warning", _capture_warning)

    project_rq.build_climate_rq("demo")

    assert warning_calls
    message, extra = warning_calls[0]
    assert message == "build_climate_rq: observed_start_year emptied after payload replay"
    assert isinstance(extra, dict)
    assert extra["runid"] == "demo"
    assert extra["job_id"] == "job-warn"
    assert extra["payload_observed_start_year"] == "1985"
    assert extra["climate_observed_start_year"] == ""


def test_build_soils_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("soils")
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Archive-backed soils roots should be rejected before cache clear")
        ),
    )
    monkeypatch.setattr(
        project_rq.Soils,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Soils should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_soils_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["soils"]


def test_build_soils_rq_clears_scoped_cache_before_hydration_and_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple[str, object]] = []
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    def _clear_cache(runid: str, pup_relpath: str | None = None) -> None:
        events.append(("clear", runid, pup_relpath))

    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", _clear_cache)

    class DummySoils:
        def build(self) -> None:
            events.append(("build", None))

    def _get_soils(wd: str) -> DummySoils:
        events.append(("hydrate", wd))
        return DummySoils()

    monkeypatch.setattr(project_rq.Soils, "getInstance", _get_soils)

    class DummyPrep:
        def timestamp(self, task) -> None:
            events.append(("timestamp", task))

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: DummyPrep())

    project_rq.build_soils_rq("demo")

    assert call_roots == ["soils", "soils"]
    assert events == [
        ("clear", "demo", "soils.nodb"),
        ("hydrate", str(run_wd)),
        ("build", None),
        ("timestamp", project_rq.TaskEnum.build_soils),
    ]
    assert published == [
        ("demo:soils", "rq:job-guard STARTED build_soils_rq(demo)"),
        ("demo:soils", "rq:job-guard COMPLETED build_soils_rq(demo)"),
        ("demo:soils", "rq:job-guard TRIGGER   soils SOILS_BUILD_TASK_COMPLETED"),
    ]


def test_set_outlet_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("watershed")
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Archive-backed watershed roots should be rejected before cache clear")
        ),
    )
    monkeypatch.setattr(
        project_rq.Watershed,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Watershed should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.set_outlet_rq("demo", outlet_lng=-112.0, outlet_lat=44.0)

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["watershed"]


def test_build_subcatchments_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("watershed")
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Archive-backed watershed roots should be rejected before cache clear")
        ),
    )
    monkeypatch.setattr(
        project_rq.Watershed,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Watershed should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.build_subcatchments_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["watershed"]


def test_abstract_watershed_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("watershed")
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Archive-backed watershed roots should be rejected before cache clear")
        ),
    )
    monkeypatch.setattr(
        project_rq.Watershed,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Watershed should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.abstract_watershed_rq("demo")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["watershed"]


@pytest.mark.parametrize(
    ("operation", "expected_method", "expects_topaz_scope"),
    [
        ("build_channels", "build_channels", True),
        ("set_outlet", "set_outlet", True),
        ("build_subcatchments", "build_subcatchments", True),
        ("abstract_watershed", "abstract_watershed", False),
    ],
)
def test_watershed_mutation_rqs_clear_scoped_cache_before_hydration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    operation: str,
    expected_method: str,
    expects_topaz_scope: bool,
) -> None:
    run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)
    _record_prep_timestamps(monkeypatch, events)
    monkeypatch.setattr(project_rq, "wait_for_path", lambda *_args, **_kwargs: events.append(("wait_for_path", None)))

    @contextmanager
    def _lock(_wd: str, root: str, *, purpose: str):
        events.append(("lock_enter", root, purpose))
        yield
        events.append(("lock_exit", root, purpose))

    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    class DummyWatershed:
        delineation_backend_is_topaz = True
        delineation_backend_is_wbt = False
        subwta = "watershed/SUBWTA.ARC"
        logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)

        @contextmanager
        def locked(self):
            events.append(("locked", "enter"))
            yield
            events.append(("locked", "exit"))

        def build_channels(self, csa: float, mcl: float) -> None:
            events.append(("build_channels", csa, mcl))

        def set_outlet(self, outlet_lng: float, outlet_lat: float) -> None:
            events.append(("set_outlet", outlet_lng, outlet_lat))

        def build_subcatchments(self) -> None:
            events.append(("build_subcatchments", None))

        def abstract_watershed(self) -> None:
            events.append(("abstract_watershed", None))

        def require_centroid(self):
            events.append(("require_centroid", None))
            return (-116.2, 43.6)

    watershed = DummyWatershed()

    def _get_watershed(wd: str) -> DummyWatershed:
        events.append(("hydrate_watershed", wd))
        return watershed

    monkeypatch.setattr(project_rq.Watershed, "getInstance", _get_watershed)
    monkeypatch.setattr(
        project_rq.Watershed,
        "load_detached",
        lambda _wd, allow_nonexistent=True: SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    if operation == "build_channels":
        project_rq.build_channels_rq(
            "demo",
            csa=10.0,
            mcl=50.0,
            stream_pruning_method=None,
            wbt_fill_or_breach=None,
            wbt_blc_dist=None,
        )
    elif operation == "set_outlet":
        project_rq.set_outlet_rq("demo", outlet_lng=-112.0, outlet_lat=44.0)
    elif operation == "build_subcatchments":
        project_rq.build_subcatchments_rq("demo")
    else:
        project_rq.abstract_watershed_rq("demo")

    assert call_roots == ["watershed", "watershed"]
    watershed_clear_index = events.index(("clear", "demo", "watershed.nodb"))
    hydrate_index = events.index(("hydrate_watershed", str(run_wd)))
    method_index = next(idx for idx, event in enumerate(events) if event[0] == expected_method)
    assert watershed_clear_index < hydrate_index < method_index
    if expects_topaz_scope:
        topaz_clear_index = events.index(("clear", "demo", "topaz.nodb"))
        assert hydrate_index < topaz_clear_index < method_index


def test_abstract_watershed_rq_repairs_missing_persisted_centroid_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(project_rq, "wait_for_path", lambda *_args, **_kwargs: None)

    class _WatershedStub:
        def __init__(self) -> None:
            self.abstract_calls = 0
            self.repair_calls = 0
            self.subwta = "dem/topaz/SUBWTA.ARC"
            self.logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)

        def abstract_watershed(self) -> None:
            self.abstract_calls += 1

        def require_centroid(self):
            self.repair_calls += 1
            return (-116.2, 43.6)

    watershed = _WatershedStub()
    monkeypatch.setattr(project_rq.Watershed, "getInstance", lambda _wd: watershed)

    persisted_states = [
        SimpleNamespace(centroid=None),
        SimpleNamespace(centroid=(-116.2, 43.6)),
    ]
    monkeypatch.setattr(
        project_rq.Watershed,
        "load_detached",
        lambda _wd, allow_nonexistent=True: persisted_states.pop(0),
    )

    prep_timestamps: list[object] = []

    class _PrepStub:
        def timestamp(self, task):
            prep_timestamps.append(task)

    monkeypatch.setattr(project_rq.RedisPrep, "getInstance", lambda _wd: _PrepStub())

    project_rq.abstract_watershed_rq("demo")

    assert watershed.abstract_calls == 1
    assert watershed.repair_calls == 1
    assert prep_timestamps == [project_rq.TaskEnum.abstract_watershed]


def test_abstract_watershed_rq_fails_when_centroid_still_missing_after_repair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(project_rq, "wait_for_path", lambda *_args, **_kwargs: None)

    class _WatershedStub:
        def __init__(self) -> None:
            self.abstract_calls = 0
            self.repair_calls = 0
            self.subwta = "dem/topaz/SUBWTA.ARC"
            self.logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)

        def abstract_watershed(self) -> None:
            self.abstract_calls += 1

        def require_centroid(self):
            self.repair_calls += 1
            return (-116.2, 43.6)

    watershed = _WatershedStub()
    monkeypatch.setattr(project_rq.Watershed, "getInstance", lambda _wd: watershed)
    monkeypatch.setattr(
        project_rq.Watershed,
        "load_detached",
        lambda _wd, allow_nonexistent=True: SimpleNamespace(centroid=None),
    )

    with pytest.raises(project_rq.WatershedCentroidStateError):
        project_rq.abstract_watershed_rq("demo")

    assert watershed.abstract_calls == 1
    assert watershed.repair_calls == 1


def test_upload_cli_rq_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _run_wd, set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    set_archive_roots("climate")
    monkeypatch.setattr(
        project_rq,
        "clear_nodb_file_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Archive-backed climate roots should be rejected before cache clear")
        ),
    )
    monkeypatch.setattr(
        project_rq.Climate,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(AssertionError("Climate should not be instantiated")),
    )

    with pytest.raises(NoDirError) as exc_info:
        project_rq.upload_cli_rq("demo", "my.cli")

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert call_roots == ["climate"]


def test_upload_cli_rq_clears_climate_cache_before_hydration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_wd, _set_archive_roots, call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)
    _record_prep_timestamps(monkeypatch, events)

    class DummyClimate:
        def set_user_defined_cli(self, cli_filename: str) -> None:
            events.append(("set_user_defined_cli", cli_filename))

    def _get_climate(wd: str) -> DummyClimate:
        assert events == [("clear", "demo", "climate.nodb")]
        events.append(("hydrate_climate", wd))
        return DummyClimate()

    monkeypatch.setattr(project_rq.Climate, "getInstance", _get_climate)

    project_rq.upload_cli_rq("demo", "user.cli")

    assert call_roots == ["climate", "climate"]
    assert events == [
        ("clear", "demo", "climate.nodb"),
        ("hydrate_climate", str(run_wd)),
        ("set_user_defined_cli", "user.cli"),
        ("timestamp", project_rq.TaskEnum.build_climate),
    ]


@pytest.mark.parametrize(
    ("rq_name", "controller_name", "scope", "method_name", "task"),
    [
        (
            "build_rangeland_cover_rq",
            "RangelandCover",
            "rangeland_cover.nodb",
            "build",
            project_rq.TaskEnum.build_rangeland_cover,
        ),
        (
            "fetch_and_align_polaris_rq",
            "Polaris",
            "polaris.nodb",
            "acquire_and_align",
            project_rq.TaskEnum.fetch_polaris,
        ),
        (
            "build_rusle_rq",
            "Rusle",
            "rusle.nodb",
            "build",
            project_rq.TaskEnum.build_rusle,
        ),
    ],
)
def test_priority1_direct_mod_rqs_clear_scoped_cache_before_hydration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rq_name: str,
    controller_name: str,
    scope: str,
    method_name: str,
    task,
) -> None:
    run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)
    _record_prep_timestamps(monkeypatch, events)

    def _target_method(self, *args, **kwargs):
        events.append(("method", controller_name, method_name, args, kwargs))
        return {"ok": True}

    dummy_cls = type(
        "DummyController",
        (),
        {
            method_name: _target_method,
            "logger": SimpleNamespace(info=lambda *_args, **_kwargs: None),
        },
    )

    def _get_controller(wd: str):
        assert events == [("clear", "demo", scope)]
        events.append(("hydrate", controller_name, wd))
        return dummy_cls()

    monkeypatch.setattr(getattr(project_rq, controller_name), "getInstance", _get_controller)

    if rq_name == "build_rangeland_cover_rq":
        project_rq.build_rangeland_cover_rq("demo", rap_year=2020, default_covers={"bunchgrass": 1.0})
    elif rq_name == "fetch_and_align_polaris_rq":
        project_rq.fetch_and_align_polaris_rq("demo", payload={"force_refresh": True})
    else:
        project_rq.build_rusle_rq("demo", payload={"force_polaris_refresh": True})

    assert events[0:2] == [
        ("clear", "demo", scope),
        ("hydrate", controller_name, str(run_wd)),
    ]
    method_index = next(idx for idx, event in enumerate(events) if event[0] == "method")
    timestamp_index = events.index(("timestamp", task))
    assert method_index < timestamp_index


@pytest.mark.parametrize(
    ("rq_name", "controller_name", "scope", "first_method"),
    [
        ("fetch_and_analyze_rap_ts_rq", "RAP_TS", "rap_ts.nodb", "acquire_rasters"),
        ("fetch_and_analyze_openet_ts_rq", "OpenET_TS", "openet_ts.nodb", "acquire_timeseries"),
    ],
)
def test_priority1_time_series_rqs_clear_scoped_cache_before_series_hydration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rq_name: str,
    controller_name: str,
    scope: str,
    first_method: str,
) -> None:
    run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)
    _record_prep_timestamps(monkeypatch, events)

    class DummyClimate:
        observed_start_year = 2001
        observed_end_year = 2003

    monkeypatch.setattr(
        project_rq.Climate,
        "getInstance",
        lambda wd: events.append(("hydrate_climate", wd)) or DummyClimate(),
    )

    class DummySeries:
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None)

        def acquire_rasters(self, **kwargs) -> None:
            events.append(("acquire_rasters", kwargs))

        def acquire_timeseries(self, **kwargs) -> None:
            events.append(("acquire_timeseries", kwargs))

        def analyze(self) -> None:
            events.append(("analyze", None))

    def _get_series(wd: str) -> DummySeries:
        events.append(("hydrate_series", controller_name, wd))
        return DummySeries()

    monkeypatch.setattr(getattr(project_rq, controller_name), "getInstance", _get_series)

    if rq_name == "fetch_and_analyze_rap_ts_rq":
        project_rq.fetch_and_analyze_rap_ts_rq("demo", payload={"note": "unit"})
    else:
        project_rq.fetch_and_analyze_openet_ts_rq("demo", payload={"force_refresh": True})

    assert events[0] == ("hydrate_climate", str(run_wd))
    clear_index = events.index(("clear", "demo", scope))
    hydrate_index = events.index(("hydrate_series", controller_name, str(run_wd)))
    method_index = next(idx for idx, event in enumerate(events) if event[0] == first_method)
    assert clear_index < hydrate_index < method_index


@pytest.mark.parametrize(
    ("rq_name", "controller_name", "scope", "method_name", "roots"),
    [
        (
            "run_ash_rq",
            "Ash",
            "ash.nodb",
            "run_ash",
            ("climate", "landuse", "watershed"),
        ),
        (
            "run_debris_flow_rq",
            "DebrisFlow",
            "debris_flow.nodb",
            "run_debris_flow",
            ("soils", "watershed"),
        ),
    ],
)
def test_priority1_root_checked_mod_rqs_clear_after_root_checks_before_hydration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rq_name: str,
    controller_name: str,
    scope: str,
    method_name: str,
    roots: tuple[str, ...],
) -> None:
    run_wd, _set_archive_roots, _call_roots = _stub_rq_context(monkeypatch, tmp_path)
    events: list[tuple] = []
    _record_cache_clears(monkeypatch, events)
    _record_prep_timestamps(monkeypatch, events)

    def _resolve(_wd: str, root: str, view: str = "effective"):
        events.append(("root", root, view))
        return SimpleNamespace(form="dir")

    @contextmanager
    def _lock(_wd: str, root: str, *, purpose: str):
        events.append(("lock_enter", root, purpose))
        yield
        events.append(("lock_exit", root, purpose))

    monkeypatch.setattr(project_rq, "nodir_resolve", _resolve)
    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    def _target_method(self, *args, **kwargs):
        events.append(("method", controller_name, method_name, args, kwargs))

    dummy_cls = type("DummyController", (), {method_name: _target_method})

    def _get_controller(wd: str):
        events.append(("hydrate", controller_name, wd))
        return dummy_cls()

    monkeypatch.setattr(getattr(project_rq, controller_name), "getInstance", _get_controller)

    class DummyWepp:
        wepp_interchange_dir = "wepp/interchange"
        baseflow_opts = {"enabled": False}

    monkeypatch.setattr(project_rq.Wepp, "getInstance", lambda wd: events.append(("hydrate_wepp", wd)) or DummyWepp())
    monkeypatch.setattr(
        project_rq,
        "run_totalwatsed3",
        lambda interchange_dir, baseflow_opts: events.append(("run_totalwatsed3", interchange_dir, baseflow_opts)),
    )

    if rq_name == "run_ash_rq":
        project_rq.run_ash_rq("demo", "8/4", 3.0, 5.0)
    else:
        project_rq.run_debris_flow_rq(
            "demo",
            payload={"clay_pct": 30.0, "liquid_limit": 40.0, "datasource": "NOAA"},
        )

    root_events_before_clear = [event for event in events if event[0] == "root"]
    assert [event[1] for event in root_events_before_clear[: len(roots)]] == list(roots)
    assert [event[1] for event in root_events_before_clear[len(roots): len(roots) * 2]] == list(roots)
    clear_index = events.index(("clear", "demo", scope))
    hydrate_index = events.index(("hydrate", controller_name, str(run_wd)))
    method_index = next(idx for idx, event in enumerate(events) if event[0] == "method")
    assert len([event for event in events[:clear_index] if event[0] == "root"]) == len(roots) * 2
    assert clear_index < hydrate_index < method_index


def test_run_with_directory_root_lock_executes_callback_for_directory_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve_calls: list[tuple[str, str]] = []
    lock_events: list[tuple[str, str, str]] = []

    def _resolve(_wd: str, root: str, view: str = "effective"):
        resolve_calls.append((root, view))
        return SimpleNamespace(form="dir")

    @contextmanager
    def _lock(_wd: str, root: str, *, purpose: str):
        lock_events.append(("enter", root, purpose))
        yield
        lock_events.append(("exit", root, purpose))

    monkeypatch.setattr(project_rq, "nodir_resolve", _resolve)
    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = project_rq._run_with_directory_root_lock(
        "/tmp/run",
        "watershed",
        lambda: callback_calls.append("called") or "ok",
        purpose="unit-root-lock",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert resolve_calls == [
        ("watershed", "effective"),
        ("watershed", "effective"),
    ]
    assert lock_events == [
        ("enter", "watershed", "unit-root-lock"),
        ("exit", "watershed", "unit-root-lock"),
    ]


def test_run_with_directory_root_lock_retries_nodir_locked_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(project_rq, "nodir_resolve", lambda _wd, _root, view="effective": SimpleNamespace(form="dir"))

    attempts = {"count": 0}

    @contextmanager
    def _lock(_wd: str, _root: str, *, purpose: str):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise NoDirError(http_status=503, code="NODIR_LOCKED", message=f"busy ({purpose})")
        yield

    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = project_rq._run_with_directory_root_lock(
        "/tmp/run",
        "watershed",
        lambda: callback_calls.append("called") or "ok",
        purpose="unit-root-lock-retry",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert attempts["count"] == 2


def test_run_with_directory_root_lock_does_not_retry_non_lock_nodir_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(project_rq, "nodir_resolve", lambda _wd, _root, view="effective": SimpleNamespace(form="dir"))

    attempts = {"count": 0}

    @contextmanager
    def _lock(_wd: str, _root: str, *, purpose: str):
        attempts["count"] += 1
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_RETIRED",
            message=f"archive-backed ({purpose})",
        )
        yield

    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    with pytest.raises(NoDirError) as exc_info:
        project_rq._run_with_directory_root_lock(
            "/tmp/run",
            "watershed",
            lambda: "ok",
            purpose="unit-root-lock-no-retry",
        )

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"
    assert attempts["count"] == 1


def test_run_with_directory_roots_lock_sorts_lock_order_and_rechecks_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve_calls: list[tuple[str, str]] = []
    lock_events: list[tuple[str, str, str]] = []

    def _resolve(_wd: str, root: str, view: str = "effective"):
        resolve_calls.append((root, view))
        return SimpleNamespace(form="dir")

    @contextmanager
    def _lock(_wd: str, root: str, *, purpose: str):
        lock_events.append(("enter", root, purpose))
        yield
        lock_events.append(("exit", root, purpose))

    monkeypatch.setattr(project_rq, "nodir_resolve", _resolve)
    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = project_rq._run_with_directory_roots_lock(
        "/tmp/run",
        ("soils", "landuse", "soils"),
        lambda: callback_calls.append("called") or "ok",
        purpose="unit-roots-lock",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert resolve_calls == [
        ("landuse", "effective"),
        ("soils", "effective"),
        ("landuse", "effective"),
        ("soils", "effective"),
    ]
    assert lock_events == [
        ("enter", "landuse", "unit-roots-lock/landuse"),
        ("enter", "soils", "unit-roots-lock/soils"),
        ("exit", "soils", "unit-roots-lock/soils"),
        ("exit", "landuse", "unit-roots-lock/landuse"),
    ]


def test_run_with_directory_roots_lock_retries_nodir_locked_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(project_rq, "DIRECTORY_ROOT_LOCK_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(project_rq, "nodir_resolve", lambda _wd, _root, view="effective": SimpleNamespace(form="dir"))

    lock_events: list[tuple[str, str]] = []
    contention_emitted = {"value": False}

    @contextmanager
    def _lock(_wd: str, root: str, *, purpose: str):
        lock_events.append((root, purpose))
        if not contention_emitted["value"]:
            contention_emitted["value"] = True
            raise NoDirError(http_status=503, code="NODIR_LOCKED", message="busy")
        yield

    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = project_rq._run_with_directory_roots_lock(
        "/tmp/run",
        ("soils", "landuse"),
        lambda: callback_calls.append("called") or "ok",
        purpose="unit-roots-lock-retry",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert lock_events == [
        ("landuse", "unit-roots-lock-retry/landuse"),
        ("landuse", "unit-roots-lock-retry/landuse"),
        ("soils", "unit-roots-lock-retry/soils"),
    ]
