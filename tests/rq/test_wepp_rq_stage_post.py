from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.wepp_rq_stage_post as stage_post
import wepppy.wepp.interchange as interchange_module

pytestmark = pytest.mark.unit


class _DummyLogger:
    def info(self, *_args, **_kwargs) -> None:
        return None


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


def test_post_watershed_interchange_times_out_when_expected_output_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_messages: list[tuple[str, str]] = []

    monkeypatch.setattr(stage_post, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(stage_post, "get_wd", lambda _runid: str(tmp_path))
    monkeypatch.setattr(stage_post.StatusMessenger, "publish", lambda channel, msg: status_messages.append((channel, msg)))
    monkeypatch.setattr(
        stage_post.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(
            delete_after_interchange=False,
            calendar_start_year=2000,
            is_single_storm=False,
        ),
    )
    monkeypatch.setattr(
        stage_post.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(
            output_dir=str(tmp_path / "wepp" / "output"),
            logger=_DummyLogger(),
            delete_after_interchange=False,
        ),
    )

    # Force immediate timeout in _wait_for_output without sleeping.
    clock = {"value": 0.0}

    def _monotonic() -> float:
        clock["value"] += 61.0
        return clock["value"]

    monkeypatch.setattr(stage_post.time, "monotonic", _monotonic)
    monkeypatch.setattr(stage_post.time, "sleep", lambda _poll: None)

    with pytest.raises(FileNotFoundError) as exc:
        stage_post._post_watershed_interchange_rq("run-1")

    assert "pass_pw0.txt" in str(exc.value)
    assert "pass_pw0.txt.gz" in str(exc.value)
    assert any(
        channel == "run-1:wepp" and "EXCEPTION _post_watershed_interchange_rq(run-1)" in message
        for channel, message in status_messages
    )


def test_post_watershed_interchange_accepts_gzip_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_messages: list[tuple[str, str]] = []
    wait_calls: list[str] = []
    interchange_calls: list[tuple[Path, int, bool, bool, bool]] = []
    deferred_cleanup_calls: list[tuple[Path, bool, bool, bool]] = []
    activation_calls: list[tuple[str, bool, bool]] = []

    wd = tmp_path
    output_dir = wd / "wepp" / "output"
    _touch(output_dir / "pass_pw0.txt.gz")
    _touch(output_dir / "soil_pw0.txt.gz")
    _touch(output_dir / "ebe_pw0.txt")
    _touch(output_dir / "loss_pw0.txt")
    _touch(output_dir / "chan.out")
    _touch(output_dir / "chanwb.out")
    _touch(output_dir / "chnwb.txt")

    monkeypatch.setattr(stage_post, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(stage_post, "get_wd", lambda _runid: str(wd))
    monkeypatch.setattr(stage_post.StatusMessenger, "publish", lambda channel, msg: status_messages.append((channel, msg)))
    monkeypatch.setattr(
        stage_post.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(
            delete_after_interchange=True,
            calendar_start_year=1998,
            is_single_storm=False,
        ),
    )
    monkeypatch.setattr(
        stage_post.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(
            output_dir=str(output_dir),
            logger=_DummyLogger(),
            delete_after_interchange=False,
        ),
    )
    monkeypatch.setattr(
        stage_post,
        "wait_for_path",
        lambda path, **_kwargs: wait_calls.append(str(path)),
    )
    monkeypatch.setattr(
        stage_post,
        "run_wepp_watershed_interchange",
        lambda path, *, start_year, run_soil_interchange, run_chnwb_interchange, delete_after_interchange: interchange_calls.append(
            (Path(path), start_year, run_soil_interchange, run_chnwb_interchange, delete_after_interchange)
        ),
    )
    monkeypatch.setattr(
        stage_post,
        "cleanup_hillslope_sources_for_completed_interchange",
        lambda path, *, run_loss_interchange, run_soil_interchange, run_wat_interchange: deferred_cleanup_calls.append(
            (Path(path), run_loss_interchange, run_soil_interchange, run_wat_interchange)
        ),
    )
    monkeypatch.setattr(stage_post, "generate_interchange_documentation", lambda _path: None)
    monkeypatch.setattr(
        stage_post,
        "activate_query_engine",
        lambda wd_path, *, run_interchange, force_refresh: activation_calls.append(
            (wd_path, run_interchange, force_refresh)
        ),
    )

    stage_post._post_watershed_interchange_rq("run-1")

    assert any(call.endswith("pass_pw0.txt.gz") for call in wait_calls)
    assert any(call.endswith("soil_pw0.txt.gz") for call in wait_calls)
    assert interchange_calls == [(output_dir, 1998, True, True, False)]
    assert deferred_cleanup_calls == []
    assert activation_calls == [(str(wd), False, True)]
    assert any(
        channel == "run-1:wepp" and "COMPLETED _post_watershed_interchange_rq(run-1)" in message
        for channel, message in status_messages
    )


def test_build_hillslope_interchange_prefers_wepp_delete_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_messages: list[tuple[str, str]] = []
    interchange_calls: list[tuple[Path, int, bool, bool, bool, bool]] = []

    wd = tmp_path

    monkeypatch.setattr(stage_post, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(stage_post, "get_wd", lambda _runid: str(wd))
    monkeypatch.setattr(
        stage_post.StatusMessenger,
        "publish",
        lambda channel, msg: status_messages.append((channel, msg)),
    )
    monkeypatch.setattr(
        stage_post.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(
            delete_after_interchange=True,
            calendar_start_year=2001,
            is_single_storm=False,
        ),
    )
    monkeypatch.setattr(
        stage_post.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(delete_after_interchange=False, run_wepp_watershed=False),
    )
    monkeypatch.setattr(
        stage_post,
        "run_wepp_hillslope_interchange",
        lambda path, *, start_year, run_loss_interchange, run_soil_interchange, run_wat_interchange, delete_after_interchange: interchange_calls.append(
            (
                Path(path),
                start_year,
                run_loss_interchange,
                run_soil_interchange,
                run_wat_interchange,
                delete_after_interchange,
            )
        ),
    )

    stage_post._build_hillslope_interchange_rq("run-1")

    assert interchange_calls == [
        (wd / "wepp" / "output", 2001, True, True, True, False),
    ]
    assert any(
        channel == "run-1:wepp" and "COMPLETED _build_hillslope_interchange_rq(run-1)" in message
        for channel, message in status_messages
    )


@pytest.mark.parametrize(
    ("run_wepp_watershed", "expected_delete_after_interchange"),
    [(True, False), (False, True)],
)
def test_build_hillslope_interchange_defers_delete_until_post_watershed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    run_wepp_watershed: bool,
    expected_delete_after_interchange: bool,
) -> None:
    interchange_calls: list[tuple[Path, int, bool, bool, bool, bool]] = []

    wd = tmp_path
    monkeypatch.setattr(stage_post, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(stage_post, "get_wd", lambda _runid: str(wd))
    monkeypatch.setattr(stage_post.StatusMessenger, "publish", lambda *_args: None)
    monkeypatch.setattr(
        stage_post.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(
            delete_after_interchange=False,
            calendar_start_year=2002,
            is_single_storm=False,
        ),
    )
    monkeypatch.setattr(
        stage_post.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(
            delete_after_interchange=True,
            run_wepp_watershed=run_wepp_watershed,
        ),
    )
    monkeypatch.setattr(
        stage_post,
        "run_wepp_hillslope_interchange",
        lambda path, *, start_year, run_loss_interchange, run_soil_interchange, run_wat_interchange, delete_after_interchange: interchange_calls.append(
            (
                Path(path),
                start_year,
                run_loss_interchange,
                run_soil_interchange,
                run_wat_interchange,
                delete_after_interchange,
            )
        ),
    )

    stage_post._build_hillslope_interchange_rq("run-1")

    assert interchange_calls == [
        (
            wd / "wepp" / "output",
            2002,
            True,
            True,
            True,
            expected_delete_after_interchange,
        ),
    ]


def test_post_watershed_interchange_runs_deferred_hillslope_cleanup_when_delete_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    output_dir = wd / "wepp" / "output"
    _touch(output_dir / "pass_pw0.txt")
    _touch(output_dir / "ebe_pw0.txt")
    _touch(output_dir / "loss_pw0.txt")
    _touch(output_dir / "chan.out")
    _touch(output_dir / "chanwb.out")
    _touch(output_dir / "chnwb.txt")
    _touch(output_dir / "soil_pw0.txt")

    cleanup_calls: list[tuple[Path, bool, bool, bool]] = []
    interchange_calls: list[tuple[Path, int, bool, bool, bool]] = []

    monkeypatch.setattr(stage_post, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(stage_post, "get_wd", lambda _runid: str(wd))
    monkeypatch.setattr(stage_post.StatusMessenger, "publish", lambda *_args: None)
    monkeypatch.setattr(
        stage_post.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(
            delete_after_interchange=False,
            calendar_start_year=2005,
            is_single_storm=False,
        ),
    )
    monkeypatch.setattr(
        stage_post.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(
            output_dir=str(output_dir),
            logger=_DummyLogger(),
            delete_after_interchange=True,
        ),
    )
    monkeypatch.setattr(stage_post, "wait_for_path", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        stage_post,
        "run_wepp_watershed_interchange",
        lambda path, *, start_year, run_soil_interchange, run_chnwb_interchange, delete_after_interchange: interchange_calls.append(
            (Path(path), start_year, run_soil_interchange, run_chnwb_interchange, delete_after_interchange)
        ),
    )
    monkeypatch.setattr(
        stage_post,
        "cleanup_hillslope_sources_for_completed_interchange",
        lambda path, *, run_loss_interchange, run_soil_interchange, run_wat_interchange: cleanup_calls.append(
            (Path(path), run_loss_interchange, run_soil_interchange, run_wat_interchange)
        ),
    )
    monkeypatch.setattr(stage_post, "generate_interchange_documentation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stage_post, "activate_query_engine", lambda *_args, **_kwargs: None)

    stage_post._post_watershed_interchange_rq("run-1")

    assert interchange_calls == [(output_dir, 2005, True, True, True)]
    assert cleanup_calls == [(output_dir, True, True, True)]


def test_build_totalwatsed3_rebuilds_interchange_readme(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_messages: list[tuple[str, str]] = []
    wait_for_paths_calls: list[list[Path]] = []
    wait_for_path_calls: list[Path] = []
    doc_calls: list[Path] = []
    build_calls: list[str] = []

    wd = tmp_path
    output_dir = wd / "wepp" / "output"
    interchange_dir = output_dir / "interchange"

    monkeypatch.setattr(stage_post, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(stage_post, "get_wd", lambda _runid: str(wd))
    monkeypatch.setattr(
        stage_post.StatusMessenger,
        "publish",
        lambda channel, msg: status_messages.append((channel, msg)),
    )
    monkeypatch.setattr(
        stage_post.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(
            output_dir=str(output_dir),
            logger=_DummyLogger(),
            _build_totalwatsed3=lambda: build_calls.append("built"),
        ),
    )
    monkeypatch.setattr(
        stage_post,
        "wait_for_paths",
        lambda paths, **_kwargs: wait_for_paths_calls.append([Path(path) for path in paths]),
    )
    monkeypatch.setattr(
        stage_post,
        "wait_for_path",
        lambda path, **_kwargs: wait_for_path_calls.append(Path(path)),
    )
    monkeypatch.setattr(
        stage_post,
        "generate_interchange_documentation",
        lambda path: doc_calls.append(Path(path)),
    )

    stage_post._build_totalwatsed3_rq("run-1")

    assert wait_for_paths_calls == [[interchange_dir / "H.pass.parquet", interchange_dir / "H.wat.parquet"]]
    assert wait_for_path_calls == [interchange_dir / "totalwatsed3.parquet"]
    assert build_calls == ["built"]
    assert doc_calls == [interchange_dir]
    assert any(
        channel == "run-1:wepp" and "COMPLETED _build_totalwatsed3_rq(run-1)" in message
        for channel, message in status_messages
    )


def test_post_dss_export_runs_full_artifact_and_timestamp_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_messages: list[tuple[str, str]] = []
    timestamped_tasks: list[object] = []
    wait_for_path_calls: list[str] = []
    wait_for_paths_calls: list[list[str]] = []
    partitioned_calls: list[tuple[str, list[int] | None, object, object]] = []
    chanout_calls: list[tuple[str, object, object]] = []
    geojson_filters: list[list[int] | None] = []
    parsed_dates: list[str] = []

    wd = tmp_path
    dss_export_dir = wd / "export" / "dss"

    monkeypatch.setattr(stage_post, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(stage_post, "get_wd", lambda _runid: str(wd))
    monkeypatch.setattr(stage_post.StatusMessenger, "publish", lambda channel, msg: status_messages.append((channel, msg)))
    monkeypatch.setattr(
        stage_post.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(
            dss_export_channel_ids=[42],
            dss_start_date="2000-01-01",
            dss_end_date="2000-12-31",
            logger=_DummyLogger(),
        ),
    )
    monkeypatch.setattr(
        stage_post.RedisPrep,
        "getInstance",
        lambda _wd: SimpleNamespace(timestamp=lambda task: timestamped_tasks.append(task)),
    )
    monkeypatch.setattr(stage_post, "parse_dss_date", lambda value: parsed_dates.append(value) or f"parsed:{value}")
    monkeypatch.setattr(
        stage_post,
        "wait_for_path",
        lambda path, **_kwargs: wait_for_path_calls.append(str(path)),
    )
    monkeypatch.setattr(
        stage_post,
        "wait_for_paths",
        lambda paths, **_kwargs: wait_for_paths_calls.append([str(path) for path in paths]),
    )
    monkeypatch.setattr(
        stage_post,
        "_cleanup_dss_export_dir",
        lambda _wd: None,
    )
    monkeypatch.setattr(
        stage_post,
        "_write_dss_channel_geojson",
        lambda _wd, channel_filter: geojson_filters.append(channel_filter)
        or _touch(dss_export_dir / "dss_channels.geojson"),
    )
    monkeypatch.setattr(
        stage_post,
        "_copy_dss_readme",
        lambda _wd, status_channel=None: _touch(dss_export_dir / "README.dss_export.md"),
    )
    monkeypatch.setattr(
        interchange_module,
        "totalwatsed_partitioned_dss_export",
        lambda wd_path, channel_filter, status_channel=None, start_date=None, end_date=None: partitioned_calls.append(
            (wd_path, channel_filter, start_date, end_date)
        )
        or _touch(dss_export_dir / "totalwatsed3_chan_42.dss"),
    )
    monkeypatch.setattr(
        interchange_module,
        "chanout_dss_export",
        lambda wd_path, status_channel=None, start_date=None, end_date=None: chanout_calls.append(
            (wd_path, start_date, end_date)
        )
        or _touch(dss_export_dir / "peak_chan_42.dss"),
    )
    monkeypatch.setattr(
        interchange_module,
        "archive_dss_export_zip",
        lambda wd_path, status_channel=None: _touch(Path(wd_path) / "export" / "dss.zip"),
    )

    stage_post.post_dss_export_rq("run-1")

    assert parsed_dates == ["2000-01-01", "2000-12-31"]
    assert geojson_filters == [[42]]
    assert partitioned_calls == [(str(wd), [42], "parsed:2000-01-01", "parsed:2000-12-31")]
    assert chanout_calls == [(str(wd), "parsed:2000-01-01", "parsed:2000-12-31")]
    assert timestamped_tasks == [stage_post.TaskEnum.dss_export]
    assert any(call.endswith("dss_channels.geojson") for call in wait_for_path_calls)
    assert any(call.endswith("README.dss_export.md") for call in wait_for_path_calls)
    assert any(call.endswith("export/dss.zip") for call in wait_for_path_calls)
    assert any(any("totalwatsed3_chan_42.dss" in path for path in call) for call in wait_for_paths_calls)
    assert any(any("peak_chan_42.dss" in path for path in call) for call in wait_for_paths_calls)
    assert any(
        channel == "run-1:dss_export" and "TRIGGER   dss_export DSS_EXPORT_TASK_COMPLETED" in message
        for channel, message in status_messages
    )


def test_post_dss_export_logs_when_redisprep_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_messages: list[tuple[str, str]] = []
    log_messages: list[str] = []

    wd = tmp_path
    dss_export_dir = wd / "export" / "dss"

    monkeypatch.setattr(stage_post, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(stage_post, "get_wd", lambda _runid: str(wd))
    monkeypatch.setattr(stage_post.StatusMessenger, "publish", lambda channel, msg: status_messages.append((channel, msg)))
    monkeypatch.setattr(
        stage_post.Wepp,
        "getInstance",
        lambda _wd: SimpleNamespace(
            dss_export_channel_ids=[42],
            dss_start_date="2000-01-01",
            dss_end_date="2000-12-31",
            logger=_DummyLogger(),
        ),
    )
    monkeypatch.setattr(
        stage_post.RedisPrep,
        "getInstance",
        lambda _wd: (_ for _ in ()).throw(FileNotFoundError("missing prep")),
    )
    monkeypatch.setattr(
        stage_post._LOGGER,
        "info",
        lambda message, *_args: log_messages.append(str(message)),
    )
    monkeypatch.setattr(stage_post, "parse_dss_date", lambda value: value)
    monkeypatch.setattr(stage_post, "wait_for_path", lambda _path, **_kwargs: None)
    monkeypatch.setattr(stage_post, "wait_for_paths", lambda _paths, **_kwargs: None)
    monkeypatch.setattr(stage_post, "_cleanup_dss_export_dir", lambda _wd: None)
    monkeypatch.setattr(
        stage_post,
        "_write_dss_channel_geojson",
        lambda _wd, _channel_filter: _touch(dss_export_dir / "dss_channels.geojson"),
    )
    monkeypatch.setattr(
        stage_post,
        "_copy_dss_readme",
        lambda _wd, status_channel=None: _touch(dss_export_dir / "README.dss_export.md"),
    )
    monkeypatch.setattr(
        interchange_module,
        "totalwatsed_partitioned_dss_export",
        lambda _wd, _channel_filter, status_channel=None, start_date=None, end_date=None: _touch(
            dss_export_dir / "totalwatsed3_chan_42.dss"
        ),
    )
    monkeypatch.setattr(
        interchange_module,
        "chanout_dss_export",
        lambda _wd, status_channel=None, start_date=None, end_date=None: _touch(
            dss_export_dir / "peak_chan_42.dss"
        ),
    )
    monkeypatch.setattr(
        interchange_module,
        "archive_dss_export_zip",
        lambda wd_path, status_channel=None: _touch(Path(wd_path) / "export" / "dss.zip"),
    )

    stage_post.post_dss_export_rq("run-1")

    assert any("Skipping dss_export prep timestamp" in msg for msg in log_messages)
    assert any(
        channel == "run-1:dss_export" and "TRIGGER   dss_export DSS_EXPORT_TASK_COMPLETED" in message
        for channel, message in status_messages
    )
